from __future__ import annotations

from collections import defaultdict
from threading import RLock

from agentsystem.domain import (
    AgentCapabilityBindingRecord,
    AgentConfigurationRecord,
    AgentModelUpdate,
    AgentName,
    AgentRunRecord,
    ApprovalRecord,
    ArtifactRecord,
    AuthSessionRecord,
    AuditLogRecord,
    CapabilityKind,
    ChatMessageRecord,
    CredentialMetadataRecord,
    McpServerRecord,
    ModelCallRecord,
    RunStepRecord,
    SkillRecord,
    StepStatus,
    TaskRecord,
    TaskView,
    ToolCallRecord,
    TraceEvent,
    UserRecord,
    UserStatus,
    WorkflowRunRecord,
    WorkspaceRecord,
    utcnow,
)


class NotFoundError(KeyError):
    """Raised when a requested in-memory record does not exist."""


class AlreadyExistsError(ValueError):
    """Raised when a unique business key is already registered."""


class InMemoryStore:
    """Thread-safe MVP store.

    The production replacement should keep this interface and move persistence to
    PostgreSQL plus object storage for larger artifacts.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self.tasks: dict[str, TaskRecord] = {}
        self.approvals: dict[str, ApprovalRecord] = {}
        self.artifacts: dict[str, ArtifactRecord] = {}
        self.steps: dict[str, RunStepRecord] = {}
        self.agent_runs: dict[str, AgentRunRecord] = {}
        self.model_calls: dict[str, ModelCallRecord] = {}
        self.tool_calls: dict[str, ToolCallRecord] = {}
        self.audit_logs: dict[str, AuditLogRecord] = {}
        self.trace_events: dict[str, TraceEvent] = {}
        self.workspaces: dict[str, WorkspaceRecord] = {}
        self.agent_model_overrides: dict[AgentName, AgentModelUpdate] = {}
        self.agent_configurations: dict[AgentName, AgentConfigurationRecord] = {}
        self.mcp_servers: dict[str, McpServerRecord] = {}
        self.skills: dict[str, SkillRecord] = {}
        self.agent_capability_bindings: dict[str, AgentCapabilityBindingRecord] = {}
        self._workspace_paths: dict[tuple[str, str], str] = {}
        self.chat_messages: dict[str, ChatMessageRecord] = {}
        self.workflow_runs: dict[str, WorkflowRunRecord] = {}
        self.credentials: dict[str, CredentialMetadataRecord] = {}
        self.idempotency_keys: dict[str, str] = {}
        self.users: dict[str, UserRecord] = {}
        self.auth_sessions: dict[str, AuthSessionRecord] = {}
        self._usernames: dict[tuple[str, str], str] = {}
        self._session_tokens: dict[str, str] = {}
        self._task_index: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))

    def create_task(self, task: TaskRecord) -> TaskRecord:
        with self._lock:
            self.tasks[task.id] = task
            return task

    def update_task(self, task: TaskRecord) -> TaskRecord:
        with self._lock:
            if task.id not in self.tasks:
                raise NotFoundError(task.id)
            task.updated_at = utcnow()
            self.tasks[task.id] = task
            return task

    def get_task(self, task_id: str) -> TaskRecord:
        with self._lock:
            try:
                return self.tasks[task_id]
            except KeyError as exc:
                raise NotFoundError(task_id) from exc

    def list_tasks(self) -> list[TaskRecord]:
        with self._lock:
            return sorted(self.tasks.values(), key=lambda task: task.created_at, reverse=True)

    def query_tasks(
        self,
        *,
        tenant_id: str,
        statuses: list[str] | None = None,
        priority: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[TaskRecord], int]:
        with self._lock:
            records = [item for item in self.tasks.values() if item.tenant_id == tenant_id]
            if statuses:
                allowed_statuses = set(statuses)
                records = [item for item in records if item.status.value in allowed_statuses]
            if priority:
                records = [item for item in records if item.priority.value == priority]
            if query:
                needle = query.casefold()
                records = [
                    item
                    for item in records
                    if needle in item.prompt.casefold() or needle in item.repo_id.casefold() or needle in item.id.casefold()
                ]
            records.sort(key=lambda item: item.created_at, reverse=True)
            return records[offset : offset + limit], len(records)

    def upsert_workspace(self, workspace: WorkspaceRecord) -> WorkspaceRecord:
        with self._lock:
            key = (workspace.tenant_id, workspace.path)
            existing_id = self._workspace_paths.get(key)
            if existing_id:
                existing = self.workspaces[existing_id]
                existing.summary = workspace.summary
                existing.file_count = workspace.file_count
                self.workspaces[existing_id] = existing
                return existing
            if any(item.path == workspace.path for item in self.workspaces.values()):
                raise AlreadyExistsError("The project path is already registered to another tenant")
            self.workspaces[workspace.id] = workspace
            self._workspace_paths[key] = workspace.id
            return workspace

    def get_workspace(self, workspace_id: str) -> WorkspaceRecord:
        with self._lock:
            try:
                return self.workspaces[workspace_id]
            except KeyError as exc:
                raise NotFoundError(workspace_id) from exc

    def list_workspaces(self) -> list[WorkspaceRecord]:
        with self._lock:
            return sorted(self.workspaces.values(), key=lambda workspace: workspace.created_at, reverse=True)

    def add_user(self, user: UserRecord) -> UserRecord:
        key = (user.tenant_id, user.username.casefold())
        with self._lock:
            if key in self._usernames:
                raise AlreadyExistsError(user.username)
            self.users[user.id] = user
            self._usernames[key] = user.id
            return user

    def update_user(self, user: UserRecord) -> UserRecord:
        with self._lock:
            current = self.users.get(user.id)
            if current is None:
                raise NotFoundError(user.id)
            old_key = (current.tenant_id, current.username.casefold())
            new_key = (user.tenant_id, user.username.casefold())
            if old_key != new_key and new_key in self._usernames:
                raise AlreadyExistsError(user.username)
            self._usernames.pop(old_key, None)
            self._usernames[new_key] = user.id
            user.updated_at = utcnow()
            self.users[user.id] = user
            return user

    def get_user(self, user_id: str) -> UserRecord:
        with self._lock:
            try:
                return self.users[user_id]
            except KeyError as exc:
                raise NotFoundError(user_id) from exc

    def find_user(self, tenant_id: str, username: str) -> UserRecord | None:
        with self._lock:
            user_id = self._usernames.get((tenant_id, username.casefold()))
            return self.users.get(user_id) if user_id else None

    def list_users(self, tenant_id: str) -> list[UserRecord]:
        with self._lock:
            return sorted(
                (item for item in self.users.values() if item.tenant_id == tenant_id),
                key=lambda item: (item.status != UserStatus.ACTIVE, item.username.casefold()),
            )

    def add_auth_session(self, session: AuthSessionRecord) -> AuthSessionRecord:
        with self._lock:
            self.auth_sessions[session.id] = session
            self._session_tokens[session.token_hash] = session.id
            return session

    def get_auth_session_by_token_hash(self, token_hash: str) -> AuthSessionRecord | None:
        with self._lock:
            session_id = self._session_tokens.get(token_hash)
            return self.auth_sessions.get(session_id) if session_id else None

    def update_auth_session(self, session: AuthSessionRecord) -> AuthSessionRecord:
        with self._lock:
            if session.id not in self.auth_sessions:
                raise NotFoundError(session.id)
            session.updated_at = utcnow()
            self.auth_sessions[session.id] = session
            self._session_tokens[session.token_hash] = session.id
            return session

    def revoke_user_sessions(self, user_id: str) -> None:
        with self._lock:
            now = utcnow()
            for session in self.auth_sessions.values():
                if session.user_id == user_id and session.revoked_at is None:
                    session.revoked_at = now
                    session.updated_at = now

    def set_agent_model_override(
        self,
        agent_name: AgentName,
        config: AgentModelUpdate,
    ) -> AgentModelUpdate:
        with self._lock:
            self.agent_model_overrides[agent_name] = config
            return config

    def get_agent_model_override(self, agent_name: AgentName) -> AgentModelUpdate | None:
        with self._lock:
            return self.agent_model_overrides.get(agent_name)

    def set_agent_configuration(self, config: AgentConfigurationRecord) -> AgentConfigurationRecord:
        with self._lock:
            self.agent_configurations[config.agent_name] = config
            return config

    def get_agent_configuration(self, agent_name: AgentName) -> AgentConfigurationRecord | None:
        with self._lock:
            return self.agent_configurations.get(agent_name)

    def list_agent_configurations(self) -> list[AgentConfigurationRecord]:
        with self._lock:
            return [self.agent_configurations[name] for name in AgentName if name in self.agent_configurations]

    def add_mcp_server(self, server: McpServerRecord) -> McpServerRecord:
        with self._lock:
            if any(
                item.tenant_id == server.tenant_id and item.name.casefold() == server.name.casefold()
                for item in self.mcp_servers.values()
            ):
                raise AlreadyExistsError(server.name)
            self.mcp_servers[server.id] = server
            return server

    def update_mcp_server(self, server: McpServerRecord) -> McpServerRecord:
        with self._lock:
            if server.id not in self.mcp_servers:
                raise NotFoundError(server.id)
            if any(
                item.id != server.id
                and item.tenant_id == server.tenant_id
                and item.name.casefold() == server.name.casefold()
                for item in self.mcp_servers.values()
            ):
                raise AlreadyExistsError(server.name)
            server.updated_at = utcnow()
            self.mcp_servers[server.id] = server
            return server

    def get_mcp_server(self, server_id: str) -> McpServerRecord:
        with self._lock:
            try:
                return self.mcp_servers[server_id]
            except KeyError as exc:
                raise NotFoundError(server_id) from exc

    def list_mcp_servers(self, tenant_id: str) -> list[McpServerRecord]:
        with self._lock:
            return sorted(
                (item for item in self.mcp_servers.values() if item.tenant_id == tenant_id),
                key=lambda item: item.created_at,
            )

    def delete_mcp_server(self, server_id: str) -> McpServerRecord:
        with self._lock:
            try:
                server = self.mcp_servers.pop(server_id)
            except KeyError as exc:
                raise NotFoundError(server_id) from exc
            self.agent_capability_bindings = {
                key: item
                for key, item in self.agent_capability_bindings.items()
                if not (
                    item.capability_kind == CapabilityKind.MCP_SERVER
                    and item.capability_id == server_id
                )
            }
            return server

    def add_skill(self, skill: SkillRecord) -> SkillRecord:
        with self._lock:
            if any(
                item.tenant_id == skill.tenant_id and item.source_path == skill.source_path
                for item in self.skills.values()
            ):
                raise AlreadyExistsError(skill.source_path)
            self.skills[skill.id] = skill
            return skill

    def update_skill(self, skill: SkillRecord) -> SkillRecord:
        with self._lock:
            if skill.id not in self.skills:
                raise NotFoundError(skill.id)
            skill.updated_at = utcnow()
            self.skills[skill.id] = skill
            return skill

    def get_skill(self, skill_id: str) -> SkillRecord:
        with self._lock:
            try:
                return self.skills[skill_id]
            except KeyError as exc:
                raise NotFoundError(skill_id) from exc

    def list_skills(self, tenant_id: str) -> list[SkillRecord]:
        with self._lock:
            return sorted(
                (item for item in self.skills.values() if item.tenant_id == tenant_id),
                key=lambda item: item.created_at,
            )

    def delete_skill(self, skill_id: str) -> SkillRecord:
        with self._lock:
            try:
                skill = self.skills.pop(skill_id)
            except KeyError as exc:
                raise NotFoundError(skill_id) from exc
            self.agent_capability_bindings = {
                key: item
                for key, item in self.agent_capability_bindings.items()
                if not (
                    item.capability_kind == CapabilityKind.SKILL
                    and item.capability_id == skill_id
                )
            }
            return skill

    def replace_agent_capability_bindings(
        self,
        tenant_id: str,
        agent_name: AgentName,
        bindings: list[AgentCapabilityBindingRecord],
    ) -> list[AgentCapabilityBindingRecord]:
        with self._lock:
            self.agent_capability_bindings = {
                key: item
                for key, item in self.agent_capability_bindings.items()
                if not (item.tenant_id == tenant_id and item.agent_name == agent_name)
            }
            for binding in bindings:
                self.agent_capability_bindings[binding.id] = binding
            return list(bindings)

    def list_agent_capability_bindings(
        self,
        tenant_id: str,
        agent_name: AgentName | None = None,
    ) -> list[AgentCapabilityBindingRecord]:
        with self._lock:
            records = [
                item
                for item in self.agent_capability_bindings.values()
                if item.tenant_id == tenant_id
                and (agent_name is None or item.agent_name == agent_name)
            ]
            return sorted(records, key=lambda item: item.created_at)

    def add_credential(self, credential: CredentialMetadataRecord) -> CredentialMetadataRecord:
        with self._lock:
            self.credentials[credential.id] = credential
            return credential

    def get_credential(self, credential_id: str) -> CredentialMetadataRecord:
        with self._lock:
            try:
                return self.credentials[credential_id]
            except KeyError as exc:
                raise NotFoundError(credential_id) from exc

    def list_credentials(self) -> list[CredentialMetadataRecord]:
        with self._lock:
            return sorted(self.credentials.values(), key=lambda item: item.created_at, reverse=True)

    def delete_credential(self, credential_id: str) -> CredentialMetadataRecord:
        with self._lock:
            try:
                return self.credentials.pop(credential_id)
            except KeyError as exc:
                raise NotFoundError(credential_id) from exc

    def remember_idempotency_key(self, key: str, task_id: str) -> None:
        with self._lock:
            self.idempotency_keys[key] = task_id

    def task_for_idempotency_key(self, key: str) -> TaskRecord | None:
        with self._lock:
            task_id = self.idempotency_keys.get(key)
            return self.tasks.get(task_id) if task_id else None

    def add_workflow_run(self, run: WorkflowRunRecord) -> WorkflowRunRecord:
        with self._lock:
            self.workflow_runs[run.id] = run
            self._task_index[run.task_id]["workflow_runs"].append(run.id)
            return run

    def update_workflow_run(self, run: WorkflowRunRecord) -> WorkflowRunRecord:
        with self._lock:
            if run.id not in self.workflow_runs:
                raise NotFoundError(run.id)
            run.updated_at = utcnow()
            self.workflow_runs[run.id] = run
            return run

    def get_workflow_run(self, run_id: str) -> WorkflowRunRecord:
        with self._lock:
            try:
                return self.workflow_runs[run_id]
            except KeyError as exc:
                raise NotFoundError(run_id) from exc

    def list_workflow_runs(self, task_id: str) -> list[WorkflowRunRecord]:
        with self._lock:
            self.get_task(task_id)
            return [self.workflow_runs[item] for item in self._task_index[task_id]["workflow_runs"]]

    def add_chat_message(self, message: ChatMessageRecord) -> ChatMessageRecord:
        with self._lock:
            if message.task_id not in self.tasks:
                raise NotFoundError(message.task_id)
            self.chat_messages[message.id] = message
            self._task_index[message.task_id]["chat_messages"].append(message.id)
            return message

    def list_chat_messages(self, task_id: str) -> list[ChatMessageRecord]:
        with self._lock:
            self.get_task(task_id)
            index = self._task_index[task_id]
            return [self.chat_messages[item] for item in index["chat_messages"]]

    def add_approval(self, approval: ApprovalRecord) -> ApprovalRecord:
        with self._lock:
            self.approvals[approval.id] = approval
            self._task_index[approval.task_id]["approvals"].append(approval.id)
            return approval

    def get_approval(self, approval_id: str) -> ApprovalRecord:
        with self._lock:
            try:
                return self.approvals[approval_id]
            except KeyError as exc:
                raise NotFoundError(approval_id) from exc

    def update_approval(self, approval: ApprovalRecord) -> ApprovalRecord:
        with self._lock:
            if approval.id not in self.approvals:
                raise NotFoundError(approval.id)
            self.approvals[approval.id] = approval
            return approval

    def decide_approval(self, approval: ApprovalRecord, expected_status) -> bool:
        with self._lock:
            current = self.approvals.get(approval.id)
            if current is None:
                raise NotFoundError(approval.id)
            if current.status != expected_status:
                return False
            self.approvals[approval.id] = approval
            return True

    def cancel_pending_approvals(self, task_id: str) -> None:
        with self._lock:
            for approval_id in self._task_index[task_id]["approvals"]:
                approval = self.approvals[approval_id]
                if approval.status == StepStatus.AWAITING_APPROVAL:
                    approval.status = StepStatus.CANCELED
                    approval.decided_at = utcnow()
                    approval.decided_by = "system"
                    approval.comment = "Task canceled"
                    self.approvals[approval.id] = approval

    def list_approvals(
        self,
        *,
        task_id: str | None = None,
        status: StepStatus | None = None,
    ) -> list[ApprovalRecord]:
        with self._lock:
            records = list(self.approvals.values())
            if task_id is not None:
                records = [item for item in records if item.task_id == task_id]
            if status is not None:
                records = [item for item in records if item.status == status]
            return sorted(records, key=lambda item: item.requested_at, reverse=True)

    def add_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        with self._lock:
            self.artifacts[artifact.id] = artifact
            self._task_index[artifact.task_id]["artifacts"].append(artifact.id)
            return artifact

    def get_artifact(self, artifact_id: str) -> ArtifactRecord:
        with self._lock:
            try:
                return self.artifacts[artifact_id]
            except KeyError as exc:
                raise NotFoundError(artifact_id) from exc

    def add_step(self, step: RunStepRecord) -> RunStepRecord:
        with self._lock:
            self.steps[step.id] = step
            self._task_index[step.task_id]["steps"].append(step.id)
            return step

    def update_step(self, step: RunStepRecord) -> RunStepRecord:
        with self._lock:
            if step.id not in self.steps:
                raise NotFoundError(step.id)
            self.steps[step.id] = step
            return step

    def add_agent_run(self, run: AgentRunRecord) -> AgentRunRecord:
        with self._lock:
            self.agent_runs[run.id] = run
            self._task_index[run.task_id]["agent_runs"].append(run.id)
            return run

    def update_agent_run(self, run: AgentRunRecord) -> AgentRunRecord:
        with self._lock:
            if run.id not in self.agent_runs:
                raise NotFoundError(run.id)
            self.agent_runs[run.id] = run
            return run

    def add_model_call(self, call: ModelCallRecord) -> ModelCallRecord:
        with self._lock:
            self.model_calls[call.id] = call
            self._task_index[call.task_id]["model_calls"].append(call.id)
            return call

    def add_tool_call(self, call: ToolCallRecord) -> ToolCallRecord:
        with self._lock:
            self.tool_calls[call.id] = call
            self._task_index[call.task_id]["tool_calls"].append(call.id)
            return call

    def add_audit_log(self, log: AuditLogRecord) -> AuditLogRecord:
        with self._lock:
            self.audit_logs[log.id] = log
            if log.task_id:
                self._task_index[log.task_id]["audit_logs"].append(log.id)
            return log

    def list_audit_logs(
        self,
        *,
        tenant_id: str,
        action: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLogRecord], int]:
        with self._lock:
            records = [item for item in self.audit_logs.values() if item.tenant_id == tenant_id]
            if action:
                records = [item for item in records if item.action == action]
            if query:
                needle = query.casefold()
                records = [
                    item
                    for item in records
                    if needle in item.actor.casefold()
                    or needle in item.action.casefold()
                    or needle in str(item.details).casefold()
                ]
            records.sort(key=lambda item: item.created_at, reverse=True)
            return records[offset : offset + limit], len(records)

    def add_trace_event(self, event: TraceEvent) -> TraceEvent:
        with self._lock:
            self.trace_events[event.id] = event
            self._task_index[event.task_id]["trace_events"].append(event.id)
            return event

    def list_trace_events(self, task_id: str, after: str | None = None) -> list[TraceEvent]:
        with self._lock:
            self.get_task(task_id)
            event_ids = self._task_index[task_id]["trace_events"]
            start = 0
            if after in event_ids:
                start = event_ids.index(after) + 1
            return [self.trace_events[item] for item in event_ids[start:]]

    def task_view(self, task_id: str) -> TaskView:
        with self._lock:
            task = self.get_task(task_id)
            index = self._task_index[task_id]
            return TaskView(
                task=task,
                runs=[self.workflow_runs[item] for item in index["workflow_runs"]],
                approvals=[self.approvals[item] for item in index["approvals"]],
                artifacts=[self.artifacts[item] for item in index["artifacts"]],
                steps=[self.steps[item] for item in index["steps"]],
            )

    def trace_for_task(self, task_id: str) -> dict[str, object]:
        with self._lock:
            task = self.get_task(task_id)
            index = self._task_index[task_id]
            return {
                "task": task,
                "events": [self.trace_events[item] for item in index["trace_events"]],
                "agent_runs": [self.agent_runs[item] for item in index["agent_runs"]],
                "model_calls": [self.model_calls[item] for item in index["model_calls"]],
                "tool_calls": [self.tool_calls[item] for item in index["tool_calls"]],
                "audit_logs": [self.audit_logs[item] for item in index["audit_logs"]],
                "artifacts": [self.artifacts[item] for item in index["artifacts"]],
                "chat_messages": [self.chat_messages[item] for item in index["chat_messages"]],
            }
