from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


class TaskStatus(StrEnum):
    CREATED = "created"
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    INPUT_REQUIRED = "input_required"
    COMPLETED = "completed"
    CANCELED = "canceled"
    FAILED = "failed"


class StepStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"
    SKIPPED = "skipped"


class RunStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class WorkflowJobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class ApprovalPolicy(StrEnum):
    AUTO = "auto"
    MANUAL_PLAN = "manual_plan"
    MANUAL_ALL = "manual_all"


class ApprovalType(StrEnum):
    PLAN = "plan"
    PUSH_BRANCH = "push_branch"
    CREATE_PR = "create_pr"
    HIGH_RISK_CHANGE = "high_risk_change"


class Priority(StrEnum):
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"


class ChatRole(StrEnum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class CallMode(StrEnum):
    SIMULATED = "simulated"
    LIVE = "live"


class ApiFormat(StrEnum):
    RESPONSES = "responses"
    CHAT_COMPLETIONS = "chat_completions"


class ApprovalAction(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    CHANGES_REQUESTED = "changes_requested"


class UserRole(StrEnum):
    ADMIN = "admin"
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class Permission(StrEnum):
    TASK_READ = "task:read"
    TASK_WRITE = "task:write"
    TASK_CHAT = "task:chat"
    APPROVAL_DECIDE = "approval:decide"
    PROJECT_READ = "project:read"
    PROJECT_WRITE = "project:write"
    AGENT_READ = "agent:read"
    AGENT_MANAGE = "agent:manage"
    CREDENTIAL_MANAGE = "credential:manage"
    OPERATIONS_READ = "operations:read"
    AUDIT_READ = "audit:read"
    USER_MANAGE = "user:manage"


class AgentName(StrEnum):
    ORCHESTRATOR = "orchestrator"
    REPO_CONTEXT = "repo_context"
    PLANNING = "planning"
    CODING = "coding"
    TEST = "test"
    SECURITY = "security"
    REVIEW = "review"
    PR = "pr"


class CapabilityKind(StrEnum):
    MCP_SERVER = "mcp_server"
    SKILL = "skill"


class CapabilityStatus(StrEnum):
    UNTESTED = "untested"
    READY = "ready"
    ERROR = "error"
    BLOCKED = "blocked"


class McpTransport(StrEnum):
    STREAMABLE_HTTP = "streamable_http"
    STDIO = "stdio"


class McpApprovalPolicy(StrEnum):
    ALWAYS = "always"
    NEVER = "never"


class ToolName(StrEnum):
    GIT_CLONE = "git_clone"
    GIT_STATUS = "git_status"
    GIT_DIFF = "git_diff"
    GIT_COMMIT = "git_commit"
    RUN_TESTS = "run_tests"
    READ_FILE = "read_file"
    WRITE_FILE = "write_file"
    CODE_SEARCH = "code_search"
    SECRET_SCAN = "secret_scan"
    CREATE_PR = "create_pr"


class TaskCreate(BaseModel):
    repo_id: str = Field(min_length=1)
    base_branch: str = Field(default="main", min_length=1)
    prompt: str = Field(min_length=1)
    issue_url: str | None = None
    workspace_path: str | None = None
    approval_policy: ApprovalPolicy = ApprovalPolicy.MANUAL_ALL
    priority: Priority = Priority.NORMAL
    tenant_id: str = "default"
    owner_id: str = "local-admin"


class WorkspaceOpen(BaseModel):
    path: str = Field(min_length=1)
    tenant_id: str = "default"
    owner_id: str = "local-admin"


class WorkspaceFile(BaseModel):
    path: str
    name: str
    kind: str
    size_bytes: int | None = None


class WorkspaceRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("workspace"))
    tenant_id: str
    owner_id: str = "local-admin"
    name: str
    path: str
    summary: str
    file_count: int = 0
    created_at: datetime = Field(default_factory=utcnow)


class ChatMessageCreate(BaseModel):
    content: str = Field(min_length=1)
    agent_name: AgentName = AgentName.ORCHESTRATOR


class AgentModelUpdate(BaseModel):
    provider: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=140)
    api_key_env: str = Field(min_length=1, max_length=120)
    base_url: str | None = Field(default=None, max_length=300)
    calls_enabled: bool = False


class AgentConfigurationUpdate(BaseModel):
    provider_id: str = Field(min_length=1, max_length=80)
    model: str = Field(min_length=1, max_length=140)
    credential_ref: str | None = Field(default=None, max_length=140)
    api_key_env: str | None = Field(default=None, max_length=120)
    base_url: str | None = Field(default=None, max_length=300)
    api_format: ApiFormat = ApiFormat.CHAT_COMPLETIONS
    call_mode: CallMode = CallMode.SIMULATED
    timeout_seconds: int = Field(default=60, ge=5, le=600)
    max_output_tokens: int = Field(default=4096, ge=64, le=131072)
    budget_limit: float | None = Field(default=None, ge=0)


class AgentConfigurationRecord(AgentConfigurationUpdate):
    agent_name: AgentName
    version: int = 1
    updated_at: datetime = Field(default_factory=utcnow)


class McpToolDescriptor(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    input_schema: dict[str, Any] = Field(default_factory=dict)


class McpServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str = Field(default="", max_length=500)
    transport: McpTransport = McpTransport.STREAMABLE_HTTP
    url: str | None = Field(default=None, max_length=1000)
    command: str | None = Field(default=None, max_length=300)
    args: list[str] = Field(default_factory=list, max_length=32)
    credential_ref: str | None = Field(default=None, max_length=140)
    credential_header: str = Field(default="Authorization", min_length=1, max_length=100)
    credential_scheme: str = Field(default="Bearer", max_length=40)
    credential_env: str | None = Field(default=None, max_length=120)
    tool_allowlist: list[str] = Field(default_factory=list, max_length=128)
    approval_policy: McpApprovalPolicy = McpApprovalPolicy.ALWAYS
    enabled: bool = False
    timeout_seconds: int = Field(default=15, ge=2, le=120)


class McpServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    transport: McpTransport | None = None
    url: str | None = Field(default=None, max_length=1000)
    command: str | None = Field(default=None, max_length=300)
    args: list[str] | None = Field(default=None, max_length=32)
    credential_ref: str | None = Field(default=None, max_length=140)
    credential_header: str | None = Field(default=None, min_length=1, max_length=100)
    credential_scheme: str | None = Field(default=None, max_length=40)
    credential_env: str | None = Field(default=None, max_length=120)
    tool_allowlist: list[str] | None = Field(default=None, max_length=128)
    approval_policy: McpApprovalPolicy | None = None
    enabled: bool | None = None
    timeout_seconds: int | None = Field(default=None, ge=2, le=120)


class McpServerRecord(McpServerCreate):
    id: str = Field(default_factory=lambda: new_id("mcp"))
    tenant_id: str = "default"
    status: CapabilityStatus = CapabilityStatus.UNTESTED
    tools: list[McpToolDescriptor] = Field(default_factory=list)
    last_error: str | None = None
    last_validated_at: datetime | None = None
    version: int = 1
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class McpValidationResult(BaseModel):
    valid: bool
    status: CapabilityStatus
    message: str
    tools: list[McpToolDescriptor] = Field(default_factory=list)
    network_attempted: bool = False


class McpToolInvokeRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


class McpToolInvokeResult(BaseModel):
    server_id: str
    tool_name: str
    output: Any
    is_error: bool = False


class SkillImport(BaseModel):
    path: str = Field(min_length=1, max_length=2000)
    enabled: bool = True


class SkillUpdate(BaseModel):
    enabled: bool | None = None


class SkillRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("skill"))
    tenant_id: str = "default"
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=1000)
    version: str | None = Field(default=None, max_length=80)
    source_path: str
    instructions: str
    content_hash: str
    enabled: bool = True
    status: CapabilityStatus = CapabilityStatus.READY
    last_error: str | None = None
    last_loaded_at: datetime = Field(default_factory=utcnow)
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AgentCapabilitiesUpdate(BaseModel):
    mcp_server_ids: list[str] = Field(default_factory=list, max_length=128)
    skill_ids: list[str] = Field(default_factory=list, max_length=128)


class AgentCapabilityBindingRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("binding"))
    tenant_id: str = "default"
    agent_name: AgentName
    capability_kind: CapabilityKind
    capability_id: str
    enabled: bool = True
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class AgentCapabilitySet(BaseModel):
    agent_name: AgentName
    mcp_servers: list[McpServerRecord] = Field(default_factory=list)
    skills: list[SkillRecord] = Field(default_factory=list)


class CredentialCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    secret: str = Field(min_length=8, max_length=1000)


class CredentialMetadataRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("cred"))
    name: str
    backend: str = "macos-keychain"
    fingerprint: str
    available: bool = True
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class ChatMessageRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("msg"))
    task_id: str
    trace_id: str
    role: ChatRole
    content: str
    agent_name: AgentName | None = None
    created_at: datetime = Field(default_factory=utcnow)


class ApprovalDecision(BaseModel):
    approval_id: str
    approved: bool
    comment: str | None = None
    actor: str = "human-operator"


class ApprovalDecisionV1(BaseModel):
    action: ApprovalAction
    comment: str | None = None


class GitHubWebhookEvent(BaseModel):
    event_type: str
    repo_id: str
    base_branch: str = "main"
    prompt: str
    issue_url: str | None = None
    delivery_id: str | None = None


class ApprovalRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("appr"))
    task_id: str
    approval_type: ApprovalType
    status: StepStatus = StepStatus.AWAITING_APPROVAL
    reason: str
    requested_at: datetime = Field(default_factory=utcnow)
    decided_at: datetime | None = None
    decided_by: str | None = None
    comment: str | None = None


class ArtifactRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("art"))
    task_id: str
    kind: str
    name: str
    content: str
    run_id: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class RunStepRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("step"))
    task_id: str
    run_id: str | None = None
    name: str
    status: StepStatus = StepStatus.PENDING
    attempt: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error: str | None = None


class AgentRunRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("agent"))
    task_id: str
    trace_id: str
    run_id: str | None = None
    agent_name: AgentName
    input_summary: str
    output_summary: str | None = None
    handoff_to: AgentName | None = None
    started_at: datetime = Field(default_factory=utcnow)
    completed_at: datetime | None = None
    latency_ms: int | None = None


class ModelCallRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("model"))
    task_id: str
    trace_id: str
    run_id: str | None = None
    agent_name: AgentName
    provider: str
    model: str
    api_key_env: str
    api_key_present: bool = False
    base_url: str | None = None
    api_format: ApiFormat = ApiFormat.CHAT_COMPLETIONS
    simulated: bool = True
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_cost: float = 0.0
    latency_ms: int = 0
    provider_request_id: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class ToolCallRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("tool"))
    task_id: str
    trace_id: str
    run_id: str | None = None
    agent_name: AgentName
    tool_name: ToolName
    input_summary: str
    allowed: bool
    exit_code: int | None = None
    output_summary: str | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utcnow)


class AuditLogRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("audit"))
    task_id: str | None
    trace_id: str | None
    tenant_id: str = "default"
    actor_id: str | None = None
    actor: str
    action: str
    details: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=utcnow)


class TraceEvent(BaseModel):
    id: str = Field(default_factory=lambda: new_id("traceevt"))
    task_id: str
    trace_id: str
    run_id: str | None = None
    step_id: str | None = None
    event_type: str
    actor: str
    payload: dict[str, Any] = Field(default_factory=dict)
    schema_version: int = 1
    created_at: datetime = Field(default_factory=utcnow)


class WorkflowRunRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("run"))
    task_id: str
    trace_id: str
    status: RunStatus = RunStatus.QUEUED
    attempt: int = 1
    started_at: datetime | None = None
    completed_at: datetime | None = None
    error_code: str | None = None
    error_message: str | None = None
    context_version: int = 0
    context_snapshot: dict[str, Any] = Field(default_factory=dict)
    last_agent: AgentName | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class WorkflowJobRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("job"))
    task_id: str
    run_id: str
    status: WorkflowJobStatus = WorkflowJobStatus.PENDING
    start_agent: AgentName = AgentName.ORCHESTRATOR
    context: dict[str, Any] = Field(default_factory=dict)
    attempts: int = 0
    available_at: datetime = Field(default_factory=utcnow)
    lease_until: datetime | None = None
    error_message: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class TaskRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("task"))
    trace_id: str = Field(default_factory=lambda: new_id("trace"))
    run_id: str | None = None
    tenant_id: str
    owner_id: str = "local-admin"
    repo_id: str
    base_branch: str
    prompt: str
    issue_url: str | None = None
    workspace_path: str | None = None
    approval_policy: ApprovalPolicy
    priority: Priority
    status: TaskStatus = TaskStatus.CREATED
    current_step: str = "created"
    branch_name: str | None = None
    pr_url: str | None = None
    failure_code: str | None = None
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)


class TaskView(BaseModel):
    task: TaskRecord
    runs: list[WorkflowRunRecord] = Field(default_factory=list)
    approvals: list[ApprovalRecord] = Field(default_factory=list)
    artifacts: list[ArtifactRecord] = Field(default_factory=list)
    steps: list[RunStepRecord] = Field(default_factory=list)


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=8, max_length=1024)


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=120, pattern=r"^[a-zA-Z0-9._-]+$")
    display_name: str = Field(min_length=1, max_length=120)
    password: str = Field(min_length=12, max_length=1024)
    role: UserRole = UserRole.VIEWER


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=120)
    password: str | None = Field(default=None, min_length=12, max_length=1024)
    role: UserRole | None = None
    status: UserStatus | None = None


class UserRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("user"))
    tenant_id: str = "default"
    username: str
    display_name: str
    password_hash: str
    role: UserRole = UserRole.VIEWER
    status: UserStatus = UserStatus.ACTIVE
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_login_at: datetime | None = None


class UserPublic(BaseModel):
    id: str
    tenant_id: str
    username: str
    display_name: str
    role: UserRole
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None

    @classmethod
    def from_record(cls, user: UserRecord) -> "UserPublic":
        return cls.model_validate(user.model_dump(exclude={"password_hash"}))


class AuthSessionRecord(BaseModel):
    id: str = Field(default_factory=lambda: new_id("session"))
    user_id: str
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None = None
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    last_seen_at: datetime = Field(default_factory=utcnow)


class Principal(BaseModel):
    user_id: str
    tenant_id: str
    username: str
    display_name: str
    role: UserRole
    auth_mode: str


class AuthSessionView(BaseModel):
    user: UserPublic
    auth_mode: str
    token: str | None = None
