from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from threading import RLock
from typing import TypeVar

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, create_engine, delete, func, or_, select, update
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

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
    ChatMessageRecord,
    CredentialMetadataRecord,
    McpServerRecord,
    ModelCallRecord,
    RunStepRecord,
    SkillRecord,
    TaskRecord,
    ToolCallRecord,
    TraceEvent,
    UserRecord,
    WorkflowJobRecord,
    WorkflowJobStatus,
    WorkflowRunRecord,
    WorkspaceRecord,
    utcnow,
)
from agentsystem.store import InMemoryStore, NotFoundError


class Base(DeclarativeBase):
    pass


class TaskRow(Base):
    __tablename__ = "tasks"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True)
    owner_id: Mapped[str] = mapped_column(String(64), index=True, default="local-admin")
    status: Mapped[str] = mapped_column(String(40), index=True)
    priority: Mapped[str] = mapped_column(String(20), index=True, default="normal")
    repo_id: Mapped[str] = mapped_column(String(300), index=True, default="")
    prompt: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    payload: Mapped[str] = mapped_column(Text)


class TaskChildMixin:
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[str] = mapped_column(Text)


class ApprovalRow(TaskChildMixin, Base):
    __tablename__ = "approvals"
    status: Mapped[str] = mapped_column(String(40), index=True)


class ArtifactRow(TaskChildMixin, Base):
    __tablename__ = "artifacts"


class StepRow(TaskChildMixin, Base):
    __tablename__ = "run_steps"
    status: Mapped[str] = mapped_column(String(40), index=True)


class AgentRunRow(TaskChildMixin, Base):
    __tablename__ = "agent_runs"


class ModelCallRow(TaskChildMixin, Base):
    __tablename__ = "model_calls"


class ToolCallRow(TaskChildMixin, Base):
    __tablename__ = "tool_calls"


class TraceEventRow(TaskChildMixin, Base):
    __tablename__ = "trace_events"


class ChatMessageRow(TaskChildMixin, Base):
    __tablename__ = "chat_messages"


class WorkflowRunRow(TaskChildMixin, Base):
    __tablename__ = "workflow_runs"
    status: Mapped[str] = mapped_column(String(40), index=True)


class AuditLogRow(Base):
    __tablename__ = "audit_logs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True, default="default")
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    action: Mapped[str] = mapped_column(String(160), index=True, default="")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[str] = mapped_column(Text)


class WorkspaceRow(Base):
    __tablename__ = "projects"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True, default="default")
    owner_id: Mapped[str] = mapped_column(String(64), index=True, default="local-admin")
    path: Mapped[str] = mapped_column(Text, unique=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[str] = mapped_column(Text)


class AgentModelOverrideRow(Base):
    __tablename__ = "agent_model_overrides"
    agent_name: Mapped[str] = mapped_column(String(40), primary_key=True)
    payload: Mapped[str] = mapped_column(Text)


class AgentConfigurationRow(Base):
    __tablename__ = "agent_configurations"
    agent_name: Mapped[str] = mapped_column(String(40), primary_key=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    payload: Mapped[str] = mapped_column(Text)


class McpServerRow(Base):
    __tablename__ = "mcp_servers"
    __table_args__ = (UniqueConstraint("tenant_id", "name", name="uq_mcp_servers_tenant_name"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(100), index=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    payload: Mapped[str] = mapped_column(Text)


class SkillRow(Base):
    __tablename__ = "skills"
    __table_args__ = (UniqueConstraint("tenant_id", "source_path", name="uq_skills_tenant_path"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True)
    name: Mapped[str] = mapped_column(String(120), index=True)
    source_path: Mapped[str] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    payload: Mapped[str] = mapped_column(Text)


class AgentCapabilityBindingRow(Base):
    __tablename__ = "agent_capability_bindings"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "agent_name",
            "capability_kind",
            "capability_id",
            name="uq_agent_capability_binding",
        ),
    )
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True)
    agent_name: Mapped[str] = mapped_column(String(40), index=True)
    capability_kind: Mapped[str] = mapped_column(String(40), index=True)
    capability_id: Mapped[str] = mapped_column(String(64), index=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[str] = mapped_column(Text)


class CredentialRow(Base):
    __tablename__ = "credential_metadata"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    payload: Mapped[str] = mapped_column(Text)


class IdempotencyRow(Base):
    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(String(180), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)


class WorkflowJobRow(Base):
    __tablename__ = "workflow_jobs"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    task_id: Mapped[str] = mapped_column(String(64), index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    available_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    lease_until: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    payload: Mapped[str] = mapped_column(Text)


class UserRow(Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("tenant_id", "username", name="uq_users_tenant_username"),)
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(120), index=True)
    username: Mapped[str] = mapped_column(String(120), index=True)
    role: Mapped[str] = mapped_column(String(40), index=True)
    status: Mapped[str] = mapped_column(String(40), index=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    payload: Mapped[str] = mapped_column(Text)


class AuthSessionRow(Base):
    __tablename__ = "auth_sessions"
    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[object | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), index=True)
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    payload: Mapped[str] = mapped_column(Text)


PydanticRecord = TypeVar("PydanticRecord")


def _normalize_database_url(database_url: str) -> str:
    """Map provider-supplied PostgreSQL URLs onto the psycopg 3 driver scheme.

    Cloud providers hand out ``postgres://`` or ``postgresql://`` URLs; SQLAlchemy
    needs an explicit driver (``postgresql+psycopg://``) to use psycopg 3.
    SQLite and already-qualified URLs pass through unchanged.
    """
    if database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgres://")
    if database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url.removeprefix("postgresql://")
    return database_url


class SQLiteStore(InMemoryStore):
    """Single-process write-through store with durable SQLite recovery.

    The in-memory indexes keep the existing MVP service API intact. SQLite is
    authoritative across restarts; PostgreSQL can replace this adapter later.
    """

    def __init__(self, database_url: str) -> None:
        super().__init__()
        self._db_lock = RLock()
        database_url = _normalize_database_url(database_url)
        if database_url.startswith("sqlite:///"):
            path = Path(database_url.removeprefix("sqlite:///"))
            path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            database_url,
            future=True,
            connect_args={"check_same_thread": False} if database_url.startswith("sqlite") else {},
        )
        self.Session = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)
        if database_url.startswith("sqlite"):
            with self.engine.begin() as connection:
                connection.exec_driver_sql("PRAGMA journal_mode=WAL")
                connection.exec_driver_sql("PRAGMA busy_timeout=5000")
                connection.exec_driver_sql("PRAGMA foreign_keys=ON")
        self._load_all()

    def _load_all(self) -> None:
        with self.Session() as session:
            for row in session.scalars(select(TaskRow)):
                task = TaskRecord.model_validate_json(row.payload)
                self.tasks[task.id] = task
            specs = [
                (ApprovalRow, ApprovalRecord, self.approvals, "approvals"),
                (ArtifactRow, ArtifactRecord, self.artifacts, "artifacts"),
                (StepRow, RunStepRecord, self.steps, "steps"),
                (AgentRunRow, AgentRunRecord, self.agent_runs, "agent_runs"),
                (ModelCallRow, ModelCallRecord, self.model_calls, "model_calls"),
                (ToolCallRow, ToolCallRecord, self.tool_calls, "tool_calls"),
                (TraceEventRow, TraceEvent, self.trace_events, "trace_events"),
                (ChatMessageRow, ChatMessageRecord, self.chat_messages, "chat_messages"),
                (WorkflowRunRow, WorkflowRunRecord, self.workflow_runs, "workflow_runs"),
            ]
            for row_model, record_model, target, index_name in specs:
                for row in session.scalars(select(row_model).order_by(row_model.created_at)):
                    record = record_model.model_validate_json(row.payload)
                    target[record.id] = record
                    self._task_index[record.task_id][index_name].append(record.id)
            for row in session.scalars(select(AuditLogRow).order_by(AuditLogRow.created_at)):
                record = AuditLogRecord.model_validate_json(row.payload)
                self.audit_logs[record.id] = record
                if record.task_id:
                    self._task_index[record.task_id]["audit_logs"].append(record.id)
            for row in session.scalars(select(WorkspaceRow).order_by(WorkspaceRow.created_at)):
                record = WorkspaceRecord.model_validate_json(row.payload)
                self.workspaces[record.id] = record
                self._workspace_paths[(record.tenant_id, record.path)] = record.id
            for row in session.scalars(select(AgentModelOverrideRow)):
                self.agent_model_overrides[AgentName(row.agent_name)] = AgentModelUpdate.model_validate_json(row.payload)
            for row in session.scalars(select(AgentConfigurationRow)):
                config = AgentConfigurationRecord.model_validate_json(row.payload)
                self.agent_configurations[config.agent_name] = config
            for row in session.scalars(select(McpServerRow).order_by(McpServerRow.created_at)):
                server = McpServerRecord.model_validate_json(row.payload)
                self.mcp_servers[server.id] = server
            for row in session.scalars(select(SkillRow).order_by(SkillRow.created_at)):
                skill = SkillRecord.model_validate_json(row.payload)
                self.skills[skill.id] = skill
            for row in session.scalars(
                select(AgentCapabilityBindingRow).order_by(AgentCapabilityBindingRow.created_at)
            ):
                binding = AgentCapabilityBindingRecord.model_validate_json(row.payload)
                self.agent_capability_bindings[binding.id] = binding
            for row in session.scalars(select(CredentialRow)):
                credential = CredentialMetadataRecord.model_validate_json(row.payload)
                self.credentials[credential.id] = credential
            for row in session.scalars(select(IdempotencyRow)):
                self.idempotency_keys[row.key] = row.task_id
            for row in session.scalars(select(UserRow)):
                user = UserRecord.model_validate_json(row.payload)
                self.users[user.id] = user
                self._usernames[(user.tenant_id, user.username.casefold())] = user.id
            for row in session.scalars(select(AuthSessionRow)):
                auth_session = AuthSessionRecord.model_validate_json(row.payload)
                self.auth_sessions[auth_session.id] = auth_session
                self._session_tokens[auth_session.token_hash] = auth_session.id

    def _merge(self, row) -> None:
        with self._db_lock, self.Session.begin() as session:
            session.merge(row)

    def _persist_task_child(self, row_model, record, *, status: str | None = None) -> None:
        values = {
            "id": record.id,
            "task_id": record.task_id,
            "created_at": getattr(record, "created_at", None) or getattr(record, "started_at", None) or utcnow(),
            "payload": record.model_dump_json(),
        }
        if status is not None:
            values["status"] = status
        self._merge(row_model(**values))

    def create_task(self, task: TaskRecord) -> TaskRecord:
        result = super().create_task(task)
        self._persist_task(task)
        return result

    def update_task(self, task: TaskRecord) -> TaskRecord:
        result = super().update_task(task)
        self._persist_task(task)
        return result

    def _persist_task(self, task: TaskRecord) -> None:
        self._merge(
            TaskRow(
                id=task.id,
                tenant_id=task.tenant_id,
                owner_id=task.owner_id,
                status=task.status.value,
                priority=task.priority.value,
                repo_id=task.repo_id,
                prompt=task.prompt,
                created_at=task.created_at,
                updated_at=task.updated_at,
                payload=task.model_dump_json(),
            )
        )

    def upsert_workspace(self, workspace: WorkspaceRecord) -> WorkspaceRecord:
        result = super().upsert_workspace(workspace)
        self._merge(
            WorkspaceRow(
                id=result.id,
                tenant_id=result.tenant_id,
                owner_id=result.owner_id,
                path=result.path,
                created_at=result.created_at,
                payload=result.model_dump_json(),
            )
        )
        return result

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
        filters = [TaskRow.tenant_id == tenant_id]
        if statuses:
            filters.append(TaskRow.status.in_(statuses))
        if priority:
            filters.append(TaskRow.priority == priority)
        if query:
            pattern = f"%{query}%"
            filters.append(
                or_(TaskRow.id.ilike(pattern), TaskRow.repo_id.ilike(pattern), TaskRow.prompt.ilike(pattern))
            )
        with self.Session() as session:
            total = session.scalar(select(func.count()).select_from(TaskRow).where(*filters)) or 0
            rows = session.scalars(
                select(TaskRow)
                .where(*filters)
                .order_by(TaskRow.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            return [TaskRecord.model_validate_json(row.payload) for row in rows], int(total)

    def add_user(self, user: UserRecord) -> UserRecord:
        result = super().add_user(user)
        self._persist_user(result)
        return result

    def update_user(self, user: UserRecord) -> UserRecord:
        result = super().update_user(user)
        self._persist_user(result)
        return result

    def _persist_user(self, user: UserRecord) -> None:
        self._merge(
            UserRow(
                id=user.id,
                tenant_id=user.tenant_id,
                username=user.username,
                role=user.role.value,
                status=user.status.value,
                created_at=user.created_at,
                updated_at=user.updated_at,
                payload=user.model_dump_json(),
            )
        )

    def add_auth_session(self, auth_session: AuthSessionRecord) -> AuthSessionRecord:
        result = super().add_auth_session(auth_session)
        self._persist_auth_session(result)
        return result

    def update_auth_session(self, auth_session: AuthSessionRecord) -> AuthSessionRecord:
        result = super().update_auth_session(auth_session)
        self._persist_auth_session(result)
        return result

    def revoke_user_sessions(self, user_id: str) -> None:
        super().revoke_user_sessions(user_id)
        for auth_session in self.auth_sessions.values():
            if auth_session.user_id == user_id:
                self._persist_auth_session(auth_session)

    def _persist_auth_session(self, auth_session: AuthSessionRecord) -> None:
        self._merge(
            AuthSessionRow(
                id=auth_session.id,
                user_id=auth_session.user_id,
                token_hash=auth_session.token_hash,
                expires_at=auth_session.expires_at,
                revoked_at=auth_session.revoked_at,
                created_at=auth_session.created_at,
                updated_at=auth_session.updated_at,
                payload=auth_session.model_dump_json(),
            )
        )

    def set_agent_model_override(self, agent_name: AgentName, config: AgentModelUpdate) -> AgentModelUpdate:
        result = super().set_agent_model_override(agent_name, config)
        self._merge(AgentModelOverrideRow(agent_name=agent_name.value, payload=config.model_dump_json()))
        return result

    def set_agent_configuration(self, config: AgentConfigurationRecord) -> AgentConfigurationRecord:
        result = super().set_agent_configuration(config)
        self._merge(
            AgentConfigurationRow(
                agent_name=config.agent_name.value,
                version=config.version,
                payload=config.model_dump_json(),
            )
        )
        return result

    def add_mcp_server(self, server: McpServerRecord) -> McpServerRecord:
        result = super().add_mcp_server(server)
        self._persist_mcp_server(result)
        return result

    def update_mcp_server(self, server: McpServerRecord) -> McpServerRecord:
        result = super().update_mcp_server(server)
        self._persist_mcp_server(result)
        return result

    def _persist_mcp_server(self, server: McpServerRecord) -> None:
        self._merge(
            McpServerRow(
                id=server.id,
                tenant_id=server.tenant_id,
                name=server.name,
                created_at=server.created_at,
                updated_at=server.updated_at,
                payload=server.model_dump_json(),
            )
        )

    def delete_mcp_server(self, server_id: str) -> McpServerRecord:
        result = super().delete_mcp_server(server_id)
        with self._db_lock, self.Session.begin() as session:
            session.execute(delete(McpServerRow).where(McpServerRow.id == server_id))
            session.execute(
                delete(AgentCapabilityBindingRow).where(
                    AgentCapabilityBindingRow.capability_kind == "mcp_server",
                    AgentCapabilityBindingRow.capability_id == server_id,
                )
            )
        return result

    def add_skill(self, skill: SkillRecord) -> SkillRecord:
        result = super().add_skill(skill)
        self._persist_skill(result)
        return result

    def update_skill(self, skill: SkillRecord) -> SkillRecord:
        result = super().update_skill(skill)
        self._persist_skill(result)
        return result

    def _persist_skill(self, skill: SkillRecord) -> None:
        self._merge(
            SkillRow(
                id=skill.id,
                tenant_id=skill.tenant_id,
                name=skill.name,
                source_path=skill.source_path,
                created_at=skill.created_at,
                updated_at=skill.updated_at,
                payload=skill.model_dump_json(),
            )
        )

    def delete_skill(self, skill_id: str) -> SkillRecord:
        result = super().delete_skill(skill_id)
        with self._db_lock, self.Session.begin() as session:
            session.execute(delete(SkillRow).where(SkillRow.id == skill_id))
            session.execute(
                delete(AgentCapabilityBindingRow).where(
                    AgentCapabilityBindingRow.capability_kind == "skill",
                    AgentCapabilityBindingRow.capability_id == skill_id,
                )
            )
        return result

    def replace_agent_capability_bindings(
        self,
        tenant_id: str,
        agent_name: AgentName,
        bindings: list[AgentCapabilityBindingRecord],
    ) -> list[AgentCapabilityBindingRecord]:
        result = super().replace_agent_capability_bindings(tenant_id, agent_name, bindings)
        with self._db_lock, self.Session.begin() as session:
            session.execute(
                delete(AgentCapabilityBindingRow).where(
                    AgentCapabilityBindingRow.tenant_id == tenant_id,
                    AgentCapabilityBindingRow.agent_name == agent_name.value,
                )
            )
            for binding in result:
                session.add(
                    AgentCapabilityBindingRow(
                        id=binding.id,
                        tenant_id=binding.tenant_id,
                        agent_name=binding.agent_name.value,
                        capability_kind=binding.capability_kind.value,
                        capability_id=binding.capability_id,
                        created_at=binding.created_at,
                        payload=binding.model_dump_json(),
                    )
                )
        return result

    def add_credential(self, credential: CredentialMetadataRecord) -> CredentialMetadataRecord:
        result = super().add_credential(credential)
        self._merge(CredentialRow(id=credential.id, created_at=credential.created_at, payload=credential.model_dump_json()))
        return result

    def delete_credential(self, credential_id: str) -> CredentialMetadataRecord:
        result = super().delete_credential(credential_id)
        with self._db_lock, self.Session.begin() as session:
            session.execute(delete(CredentialRow).where(CredentialRow.id == credential_id))
        return result

    def remember_idempotency_key(self, key: str, task_id: str) -> None:
        super().remember_idempotency_key(key, task_id)
        self._merge(IdempotencyRow(key=key, task_id=task_id))

    def add_workflow_run(self, run: WorkflowRunRecord) -> WorkflowRunRecord:
        result = super().add_workflow_run(run)
        self._persist_task_child(WorkflowRunRow, run, status=run.status.value)
        return result

    def update_workflow_run(self, run: WorkflowRunRecord) -> WorkflowRunRecord:
        result = super().update_workflow_run(run)
        self._persist_task_child(WorkflowRunRow, run, status=run.status.value)
        return result

    def add_chat_message(self, message: ChatMessageRecord) -> ChatMessageRecord:
        result = super().add_chat_message(message)
        self._persist_task_child(ChatMessageRow, message)
        return result

    def add_approval(self, approval: ApprovalRecord) -> ApprovalRecord:
        result = super().add_approval(approval)
        self._persist_task_child(ApprovalRow, approval, status=approval.status.value)
        return result

    def update_approval(self, approval: ApprovalRecord) -> ApprovalRecord:
        result = super().update_approval(approval)
        self._persist_task_child(ApprovalRow, approval, status=approval.status.value)
        return result

    def decide_approval(self, approval: ApprovalRecord, expected_status) -> bool:
        with self._db_lock, self.Session.begin() as session:
            changed = session.execute(
                update(ApprovalRow)
                .where(ApprovalRow.id == approval.id, ApprovalRow.status == expected_status.value)
                .values(status=approval.status.value, payload=approval.model_dump_json())
            ).rowcount
        if not changed:
            return False
        with self._lock:
            self.approvals[approval.id] = approval
        return True

    def cancel_pending_approvals(self, task_id: str) -> None:
        super().cancel_pending_approvals(task_id)
        for approval_id in self._task_index[task_id]["approvals"]:
            approval = self.approvals[approval_id]
            self._persist_task_child(ApprovalRow, approval, status=approval.status.value)

    def add_artifact(self, artifact: ArtifactRecord) -> ArtifactRecord:
        result = super().add_artifact(artifact)
        self._persist_task_child(ArtifactRow, artifact)
        return result

    def add_step(self, step: RunStepRecord) -> RunStepRecord:
        result = super().add_step(step)
        self._persist_task_child(StepRow, step, status=step.status.value)
        return result

    def update_step(self, step: RunStepRecord) -> RunStepRecord:
        result = super().update_step(step)
        self._persist_task_child(StepRow, step, status=step.status.value)
        return result

    def add_agent_run(self, run: AgentRunRecord) -> AgentRunRecord:
        result = super().add_agent_run(run)
        self._persist_task_child(AgentRunRow, run)
        return result

    def update_agent_run(self, run: AgentRunRecord) -> AgentRunRecord:
        result = super().update_agent_run(run)
        self._persist_task_child(AgentRunRow, run)
        return result

    def add_model_call(self, call: ModelCallRecord) -> ModelCallRecord:
        result = super().add_model_call(call)
        self._persist_task_child(ModelCallRow, call)
        return result

    def add_tool_call(self, call: ToolCallRecord) -> ToolCallRecord:
        result = super().add_tool_call(call)
        self._persist_task_child(ToolCallRow, call)
        return result

    def add_audit_log(self, log: AuditLogRecord) -> AuditLogRecord:
        result = super().add_audit_log(log)
        self._merge(
            AuditLogRow(
                id=log.id,
                task_id=log.task_id,
                tenant_id=log.tenant_id,
                actor_id=log.actor_id,
                action=log.action,
                created_at=log.created_at,
                payload=log.model_dump_json(),
            )
        )
        return result

    def list_audit_logs(
        self,
        *,
        tenant_id: str,
        action: str | None = None,
        query: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[AuditLogRecord], int]:
        filters = [AuditLogRow.tenant_id == tenant_id]
        if action:
            filters.append(AuditLogRow.action == action)
        if query:
            pattern = f"%{query}%"
            filters.append(or_(AuditLogRow.action.ilike(pattern), AuditLogRow.payload.ilike(pattern)))
        with self.Session() as session:
            total = session.scalar(select(func.count()).select_from(AuditLogRow).where(*filters)) or 0
            rows = session.scalars(
                select(AuditLogRow)
                .where(*filters)
                .order_by(AuditLogRow.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            return [AuditLogRecord.model_validate_json(row.payload) for row in rows], int(total)

    def add_trace_event(self, event: TraceEvent) -> TraceEvent:
        result = super().add_trace_event(event)
        self._persist_task_child(TraceEventRow, event)
        return result

    def enqueue_workflow_job(self, job: WorkflowJobRecord) -> WorkflowJobRecord:
        self._merge(
            WorkflowJobRow(
                id=job.id,
                task_id=job.task_id,
                run_id=job.run_id,
                status=job.status.value,
                available_at=job.available_at,
                lease_until=job.lease_until,
                created_at=job.created_at,
                updated_at=job.updated_at,
                payload=job.model_dump_json(),
            )
        )
        return job

    def claim_workflow_job(self, lease_seconds: int) -> WorkflowJobRecord | None:
        now = utcnow()
        with self._db_lock, self.Session.begin() as session:
            row = session.scalar(
                select(WorkflowJobRow)
                .where(
                    WorkflowJobRow.available_at <= now,
                    (
                        (WorkflowJobRow.status == WorkflowJobStatus.PENDING.value)
                        | (
                            (WorkflowJobRow.status == WorkflowJobStatus.RUNNING.value)
                            & (WorkflowJobRow.lease_until < now)
                        )
                    ),
                )
                .order_by(WorkflowJobRow.created_at)
                .limit(1)
            )
            if row is None:
                return None
            job = WorkflowJobRecord.model_validate_json(row.payload)
            job.status = WorkflowJobStatus.RUNNING
            job.attempts += 1
            job.lease_until = now + timedelta(seconds=lease_seconds)
            job.updated_at = now
            row.status = job.status.value
            row.lease_until = job.lease_until
            row.updated_at = job.updated_at
            row.payload = job.model_dump_json()
            return job

    def complete_workflow_job(self, job: WorkflowJobRecord) -> None:
        job.status = WorkflowJobStatus.COMPLETED
        job.lease_until = None
        job.updated_at = utcnow()
        self._update_job(job)

    def fail_workflow_job(self, job: WorkflowJobRecord, message: str) -> None:
        job.status = WorkflowJobStatus.FAILED
        job.error_message = message[:1000]
        job.lease_until = None
        job.updated_at = utcnow()
        self._update_job(job)

    def cancel_workflow_jobs(self, task_id: str) -> None:
        now = utcnow()
        with self._db_lock, self.Session.begin() as session:
            rows = list(session.scalars(select(WorkflowJobRow).where(WorkflowJobRow.task_id == task_id)))
            for row in rows:
                job = WorkflowJobRecord.model_validate_json(row.payload)
                if job.status in {WorkflowJobStatus.PENDING, WorkflowJobStatus.RUNNING}:
                    job.status = WorkflowJobStatus.CANCELED
                    job.lease_until = None
                    job.updated_at = now
                    row.status = job.status.value
                    row.lease_until = None
                    row.updated_at = now
                    row.payload = job.model_dump_json()

    def _update_job(self, job: WorkflowJobRecord) -> None:
        with self._db_lock, self.Session.begin() as session:
            row = session.get(WorkflowJobRow, job.id)
            if row is None:
                raise NotFoundError(job.id)
            row.status = job.status.value
            row.lease_until = job.lease_until
            row.updated_at = job.updated_at
            row.payload = job.model_dump_json()
