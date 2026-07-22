export type AgentName =
  | "orchestrator"
  | "repo_context"
  | "planning"
  | "coding"
  | "test"
  | "security"
  | "review"
  | "pr";

export type ApiFormat = "responses" | "chat_completions";

export type CallMode = "simulated" | "live";

export type UserRole = "admin" | "operator" | "reviewer" | "viewer";
export type UserStatus = "active" | "disabled";
export type Permission =
  | "task:read"
  | "task:write"
  | "task:chat"
  | "approval:decide"
  | "project:read"
  | "project:write"
  | "agent:read"
  | "agent:manage"
  | "credential:manage"
  | "operations:read"
  | "audit:read"
  | "user:manage";

export interface User {
  id: string;
  tenant_id: string;
  username: string;
  display_name: string;
  role: UserRole;
  status: UserStatus;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface AuthSession {
  user: User;
  auth_mode: "dev" | "local";
}

export interface SystemInfo {
  name: string;
  version: string;
  auth_mode: "dev" | "local";
  execution_mode: "simulated" | "mixed" | "live";
  model_calls_enabled: boolean;
  live_agent_count: number;
  simulated_agent_count: number;
  worker_running: boolean;
}

export type TaskStatus =
  | "created"
  | "queued"
  | "running"
  | "awaiting_approval"
  | "input_required"
  | "completed"
  | "canceled"
  | "failed";

export interface TaskRecord {
  id: string;
  trace_id: string;
  run_id: string | null;
  tenant_id: string;
  owner_id: string;
  repo_id: string;
  base_branch: string;
  prompt: string;
  issue_url: string | null;
  workspace_path: string | null;
  approval_policy: "auto" | "manual_plan" | "manual_all";
  priority: "low" | "normal" | "high";
  status: TaskStatus;
  current_step: string;
  branch_name: string | null;
  pr_url: string | null;
  failure_code: string | null;
  failure_reason: string | null;
  created_at: string;
  updated_at: string;
}

export interface WorkflowRun {
  id: string;
  task_id: string;
  status: string;
  attempt: number;
  started_at: string | null;
  completed_at: string | null;
}

export interface Approval {
  id: string;
  task_id: string;
  approval_type: string;
  status: string;
  reason: string;
  requested_at: string;
  comment: string | null;
}

export interface Artifact {
  id: string;
  task_id: string;
  run_id: string | null;
  kind: string;
  name: string;
  content: string;
  created_at: string;
}

export interface RunStep {
  id: string;
  task_id: string;
  run_id: string | null;
  name: AgentName | string;
  status: string;
  attempt: number;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export interface TaskView {
  task: TaskRecord;
  runs: WorkflowRun[];
  approvals: Approval[];
  artifacts: Artifact[];
  steps: RunStep[];
}

export interface Project {
  id: string;
  tenant_id: string;
  owner_id: string;
  name: string;
  path: string;
  summary: string;
  file_count: number;
  created_at: string;
}

export interface ProjectFile {
  path: string;
  name: string;
  kind: "directory" | "file";
  size_bytes: number | null;
}

export interface AgentConfiguration {
  agent_name: AgentName;
  provider_id: string;
  model: string;
  credential_ref: string | null;
  api_key_env: string | null;
  credential_available: boolean;
  base_url: string | null;
  api_format: ApiFormat;
  call_mode: CallMode;
  timeout_seconds: number;
  max_output_tokens: number;
  budget_limit: number | null;
  version: number;
  network_enabled: boolean;
}

export interface ProviderDefinition {
  id: string;
  display_name: string;
  description: string;
  default_api_format: ApiFormat;
  supported_api_formats: ApiFormat[];
  default_base_url: string | null;
  requires_base_url: boolean;
  requires_credential: boolean;
  default_model: string;
  models: string[];
  supports_model_discovery: boolean;
}

export interface AgentSummary {
  agent_name: AgentName;
  display_name: string;
  description: string;
  status: string;
  last_summary: string | null;
  handoff_to: AgentName | null;
  latency_ms: number | null;
  configuration: AgentConfiguration;
  capabilities?: CapabilityManifest;
}

export type CapabilityStatus = "untested" | "ready" | "error" | "blocked";
export type McpTransport = "streamable_http" | "stdio";

export interface McpTool {
  name: string;
  description: string;
  input_schema: Record<string, unknown>;
}

export interface McpServer {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  transport: McpTransport;
  url: string | null;
  command: string | null;
  args: string[];
  credential_ref: string | null;
  credential_header: string;
  credential_scheme: string;
  credential_env: string | null;
  tool_allowlist: string[];
  approval_policy: "always" | "never";
  enabled: boolean;
  timeout_seconds: number;
  status: CapabilityStatus;
  tools: McpTool[];
  last_error: string | null;
  last_validated_at: string | null;
  version: number;
  created_at: string;
  updated_at: string;
}

export interface Skill {
  id: string;
  tenant_id: string;
  name: string;
  description: string;
  version: string | null;
  source_path: string;
  instructions: string;
  content_hash: string;
  enabled: boolean;
  status: CapabilityStatus;
  last_error: string | null;
  last_loaded_at: string;
  created_at: string;
  updated_at: string;
}

export interface AgentCapabilitySet {
  agent_name: AgentName;
  mcp_servers: McpServer[];
  skills: Skill[];
}

export interface CapabilityManifest {
  skills: Array<{ id: string; name: string; enabled: boolean; status: CapabilityStatus }>;
  mcp_servers: Array<{ id: string; name: string; enabled: boolean; status: CapabilityStatus; tool_count: number }>;
}

export interface CapabilityPolicy {
  network_enabled: boolean;
  allowed_hosts: string[];
  stdio_enabled: boolean;
  stdio_allowed_commands: string[];
  skill_allowed_roots: string[];
  skill_max_bytes: number;
}

export interface McpValidation {
  valid: boolean;
  status: CapabilityStatus;
  message: string;
  tools: McpTool[];
  network_attempted: boolean;
}

export interface TraceEvent {
  id: string;
  task_id: string;
  trace_id: string;
  run_id: string | null;
  event_type: string;
  actor: string;
  payload: Record<string, unknown>;
  created_at: string;
}

export interface Trace {
  task: TaskRecord;
  events: TraceEvent[];
  agent_runs: Array<{
    id: string;
    agent_name: AgentName;
    input_summary: string;
    output_summary: string | null;
    handoff_to: AgentName | null;
    latency_ms: number | null;
    started_at: string;
    completed_at: string | null;
  }>;
  model_calls: Array<{
    id: string;
    agent_name: AgentName;
    provider: string;
    model: string;
    api_format: ApiFormat;
    simulated: boolean;
    prompt_tokens: number;
    completion_tokens: number;
    provider_request_id: string | null;
    error_message: string | null;
    latency_ms: number;
    created_at: string;
  }>;
  tool_calls: Array<{
    id: string;
    agent_name: AgentName;
    tool_name: string;
    allowed: boolean;
    exit_code: number | null;
    output_summary: string | null;
    created_at: string;
  }>;
  audit_logs: unknown[];
  artifacts: Artifact[];
  chat_messages: ChatMessage[];
}

export interface ChatMessage {
  id: string;
  task_id: string;
  trace_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  agent_name: AgentName | null;
  created_at: string;
}

export interface Credential {
  id: string;
  name: string;
  backend: string;
  fingerprint: string;
  available: boolean;
  created_at: string;
  updated_at: string;
}

export interface ApiErrorBody {
  error?: {
    code?: string;
    message?: string;
    request_id?: string;
  };
}

export interface PageResult<T> {
  items: T[];
  total: number;
}

export interface OperationsSummary {
  total_tasks: number;
  status_counts: Record<TaskStatus, number>;
  active_tasks: number;
  pending_approvals: number;
  model_calls: { total: number; live: number; simulated: number; cost: number };
  tool_calls: { total: number; denied: number };
}

export interface AuditLog {
  id: string;
  task_id: string | null;
  trace_id: string | null;
  tenant_id: string;
  actor_id: string | null;
  actor: string;
  action: string;
  details: Record<string, unknown>;
  created_at: string;
}
