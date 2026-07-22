import type {
  AgentConfiguration,
  AgentCapabilitySet,
  AgentName,
  AgentSummary,
  AuditLog,
  AuthSession,
  ApiErrorBody,
  ChatMessage,
  CapabilityPolicy,
  Credential,
  OperationsSummary,
  PageResult,
  Project,
  ProjectFile,
  ProviderDefinition,
  McpServer,
  McpValidation,
  Skill,
  SystemInfo,
  TaskRecord,
  TaskView,
  Trace,
  User,
  UserRole,
  UserStatus,
} from "../types";

export class ApiError extends Error {
  code: string;
  requestId?: string;
  status: number;

  constructor(message: string, code = "REQUEST_FAILED", requestId?: string, status = 0) {
    super(message);
    this.code = code;
    this.requestId = requestId;
    this.status = status;
  }
}

async function performRequest(path: string, init?: RequestInit): Promise<Response> {
  const headers = new Headers(init?.headers);
  if (init?.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const response = await fetch(path, { credentials: "same-origin", ...init, headers });
  if (!response.ok) {
    let body: ApiErrorBody = {};
    try {
      body = (await response.json()) as ApiErrorBody;
    } catch {
      // The fallback below keeps non-JSON proxy errors readable.
    }
    throw new ApiError(
      body.error?.message ?? `Request failed (${response.status})`,
      body.error?.code,
      body.error?.request_id,
      response.status,
    );
  }
  return response;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await performRequest(path, init);
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

async function requestPage<T>(path: string): Promise<PageResult<T>> {
  const response = await performRequest(path);
  return {
    items: (await response.json()) as T[],
    total: Number(response.headers.get("X-Total-Count") ?? 0),
  };
}

function queryString(params: Record<string, string | string[] | number | undefined>): string {
  const search = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (Array.isArray(value)) value.forEach((item) => search.append(key, item));
    else if (value !== undefined && value !== "") search.set(key, String(value));
  });
  const encoded = search.toString();
  return encoded ? `?${encoded}` : "";
}

export const api = {
  me: () => request<AuthSession>("/api/v1/auth/me"),
  login: (username: string, password: string) =>
    request<AuthSession>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<void>("/api/v1/auth/logout", { method: "POST" }),
  users: () => request<User[]>("/api/v1/users"),
  createUser: (payload: { username: string; display_name: string; password: string; role: UserRole }) =>
    request<User>("/api/v1/users", { method: "POST", body: JSON.stringify(payload) }),
  updateUser: (id: string, payload: { display_name?: string; password?: string; role?: UserRole; status?: UserStatus }) =>
    request<User>(`/api/v1/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  system: () => request<SystemInfo>("/api/v1/system"),
  modelProviders: () => request<ProviderDefinition[]>("/api/v1/model-providers"),
  collaborationRules: () => request<{
    version: string;
    execution_mode: string;
    principles: string[];
    failure_policy: Record<string, string | number>;
    agents: Array<{
      agent_name: AgentName;
      objective: string;
      required_inputs: string[];
      required_outputs: string[];
      allowed_handoffs: AgentName[];
      tools: string[];
      failure_owner: AgentName;
    }>;
  }>("/api/v1/collaboration/rules"),
  tasks: (filters: { status?: string[]; priority?: string; q?: string; limit?: number; offset?: number } = {}) =>
    requestPage<TaskRecord>(`/api/v1/tasks${queryString(filters)}`),
  task: (id: string) => request<TaskView>(`/api/v1/tasks/${id}`),
  createTask: (payload: Record<string, unknown>) =>
    request<TaskView>("/api/v1/tasks", {
      method: "POST",
      body: JSON.stringify(payload),
      headers: { "Idempotency-Key": crypto.randomUUID() },
    }),
  cancelTask: (id: string) => request<TaskView>(`/api/v1/tasks/${id}/cancel`, { method: "POST" }),
  rerunTask: (id: string) =>
    request<TaskView>(`/api/v1/tasks/${id}/runs`, {
      method: "POST",
      body: JSON.stringify({ reason: "Started from workspace" }),
    }),
  decideApproval: (approvalId: string, action: "approve" | "reject" | "changes_requested", comment?: string) =>
    request<TaskView>(`/api/v1/approvals/${approvalId}/decisions`, {
      method: "POST",
      body: JSON.stringify({ action, comment }),
    }),
  projects: () => request<Project[]>("/api/v1/projects"),
  pickProject: () => request<Project | { status: string; path: string }>("/api/v1/projects/pick", { method: "POST" }),
  addProject: (path: string) =>
    request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify({ path }) }),
  projectFiles: (id: string, path = "") =>
    request<ProjectFile[]>(`/api/v1/projects/${id}/files?path=${encodeURIComponent(path)}`),
  projectFile: (id: string, path: string) =>
    request<{ path: string; content: string; truncated: boolean }>(
      `/api/v1/projects/${id}/file?path=${encodeURIComponent(path)}`,
    ),
  agents: (taskId?: string) => request<AgentSummary[]>(`/api/v1/agents${taskId ? `?task_id=${taskId}` : ""}`),
  capabilityPolicy: () => request<CapabilityPolicy>("/api/v1/capabilities/policy"),
  mcpServers: () => request<McpServer[]>("/api/v1/mcp-servers"),
  createMcpServer: (payload: Record<string, unknown>) =>
    request<McpServer>("/api/v1/mcp-servers", { method: "POST", body: JSON.stringify(payload) }),
  updateMcpServer: (id: string, payload: Record<string, unknown>) =>
    request<McpServer>(`/api/v1/mcp-servers/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteMcpServer: (id: string) =>
    request<McpServer>(`/api/v1/mcp-servers/${id}`, { method: "DELETE" }),
  validateMcpServer: (id: string) =>
    request<McpValidation>(`/api/v1/mcp-servers/${id}/validate`, { method: "POST" }),
  skills: () => request<Skill[]>("/api/v1/skills"),
  pickSkill: () => request<Skill | { status: string; path?: string }>("/api/v1/skills/pick", { method: "POST" }),
  importSkill: (path: string) =>
    request<Skill>("/api/v1/skills", { method: "POST", body: JSON.stringify({ path }) }),
  updateSkill: (id: string, enabled: boolean) =>
    request<Skill>(`/api/v1/skills/${id}`, { method: "PATCH", body: JSON.stringify({ enabled }) }),
  refreshSkill: (id: string) =>
    request<Skill>(`/api/v1/skills/${id}/refresh`, { method: "POST" }),
  deleteSkill: (id: string) =>
    request<Skill>(`/api/v1/skills/${id}`, { method: "DELETE" }),
  agentCapabilities: (name: AgentName) =>
    request<AgentCapabilitySet>(`/api/v1/agents/${name}/capabilities`),
  updateAgentCapabilities: (name: AgentName, payload: { mcp_server_ids: string[]; skill_ids: string[] }) =>
    request<AgentCapabilitySet>(`/api/v1/agents/${name}/capabilities`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  updateAgent: (name: AgentName, payload: Omit<AgentConfiguration, "agent_name" | "credential_available" | "version" | "network_enabled">) =>
    request<AgentConfiguration>(`/api/v1/agents/${name}/configuration`, {
      method: "PUT",
      body: JSON.stringify(payload),
    }),
  validateAgent: (name: AgentName) =>
    request<{
      valid: boolean;
      mode: "simulated" | "live";
      message: string;
      network_attempted: boolean;
      provider_id: string;
      model: string;
      models: string[];
    }>(`/api/v1/agents/${name}/validate`, {
      method: "POST",
    }),
  discoverAgentModels: (name: AgentName) =>
    request<{ agent_name: AgentName; models: string[] }>(`/api/v1/agents/${name}/models`),
  trace: (traceId: string) => request<Trace>(`/api/v1/traces/${traceId}`),
  messages: (taskId: string) => request<ChatMessage[]>(`/api/v1/tasks/${taskId}/messages`),
  sendMessage: (taskId: string, agentName: AgentName, content: string) =>
    request<ChatMessage[]>(`/api/v1/tasks/${taskId}/messages`, {
      method: "POST",
      body: JSON.stringify({ agent_name: agentName, content }),
    }),
  credentials: () => request<Credential[]>("/api/v1/credentials"),
  createCredential: (payload: { name: string; secret: string }) =>
    request<Credential>("/api/v1/credentials", { method: "POST", body: JSON.stringify(payload) }),
  deleteCredential: (credentialId: string) =>
    request<Credential>(`/api/v1/credentials/${credentialId}`, { method: "DELETE" }),
  operationsSummary: () => request<OperationsSummary>("/api/v1/operations/summary"),
  auditLogs: (filters: { action?: string; q?: string; limit?: number; offset?: number } = {}) =>
    requestPage<AuditLog>(`/api/v1/audit-logs${queryString(filters)}`),
};
