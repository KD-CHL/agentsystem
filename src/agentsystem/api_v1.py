from __future__ import annotations

import asyncio
import json
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agentsystem.container import AppContainer
from agentsystem.auth import AuthenticationError, AuthorizationError
from agentsystem.capabilities import CapabilityError
from agentsystem.domain import (
    AgentCapabilitiesUpdate,
    AgentConfigurationRecord,
    AgentConfigurationUpdate,
    AgentName,
    ApprovalAction,
    ApprovalDecision,
    ApprovalDecisionV1,
    AuthSessionView,
    CallMode,
    ChatMessageCreate,
    ChatMessageRecord,
    ChatRole,
    CredentialCreate,
    CredentialMetadataRecord,
    LoginRequest,
    McpServerCreate,
    McpServerRecord,
    McpServerUpdate,
    McpToolInvokeRequest,
    McpToolInvokeResult,
    McpValidationResult,
    Permission,
    Principal,
    Priority,
    RunStatus,
    SkillImport,
    SkillRecord,
    SkillUpdate,
    StepStatus,
    TaskCreate,
    TaskStatus,
    TaskView,
    UserCreate,
    UserPublic,
    UserUpdate,
    WorkflowRunRecord,
    WorkspaceFile,
    WorkspaceOpen,
    WorkspaceRecord,
    utcnow,
)
from agentsystem.credentials import CredentialBackendError
from agentsystem.providers import PROVIDER_DEFINITIONS, provider_definition
from agentsystem.store import AlreadyExistsError, NotFoundError


AGENT_DETAILS: dict[AgentName, tuple[str, str]] = {
    AgentName.ORCHESTRATOR: ("Orchestrator", "Task routing and budget control"),
    AgentName.REPO_CONTEXT: ("Repo Context", "Repository discovery and context packaging"),
    AgentName.PLANNING: ("Planning", "Implementation planning and risk analysis"),
    AgentName.CODING: ("Coding", "Focused patch generation"),
    AgentName.TEST: ("Test", "Test execution and repair feedback"),
    AgentName.SECURITY: ("Security", "Secrets, permissions, and policy checks"),
    AgentName.REVIEW: ("Review", "Correctness and regression review"),
    AgentName.PR: ("PR", "Draft pull request packaging"),
}


class RunCreate(BaseModel):
    reason: str | None = None


class CredentialPresence(BaseModel):
    credential_id: str
    available: bool


def build_v1_router(resolve_container) -> APIRouter:
    router = APIRouter(prefix="/api/v1")

    def actor(request: Request) -> str:
        return _principal(request).username

    @router.post("/auth/login", response_model=AuthSessionView)
    def login(
        payload: LoginRequest,
        response: Response,
        app_container: AppContainer = Depends(resolve_container),
    ) -> AuthSessionView:
        try:
            token, user = app_container.auth.login(payload.username, payload.password)
        except AuthenticationError as exc:
            app_container.trace.audit(
                None,
                payload.username.strip().lower(),
                "auth.login.failed",
                {"reason": "invalid_credentials"},
            )
            raise HTTPException(
                status_code=401,
                detail={"code": "INVALID_CREDENTIALS", "message": str(exc)},
            ) from exc
        if token:
            response.set_cookie(
                app_container.settings.auth_cookie_name,
                token,
                max_age=app_container.settings.auth_session_ttl_hours * 3600,
                httponly=True,
                secure=app_container.settings.auth_cookie_secure,
                samesite="lax",
                path="/",
            )
        app_container.trace.audit(
            None,
            user.username,
            "auth.login.succeeded",
            {"auth_mode": app_container.settings.auth_mode},
            tenant_id=user.tenant_id,
            actor_id=user.id,
        )
        return AuthSessionView(user=user, auth_mode=app_container.settings.auth_mode)

    @router.get("/auth/me", response_model=AuthSessionView)
    def auth_me(
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> AuthSessionView:
        principal = _principal(request)
        return AuthSessionView(
            user=app_container.auth.user_for_principal(principal),
            auth_mode=app_container.settings.auth_mode,
        )

    @router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
    def logout(
        request: Request,
        response: Response,
        app_container: AppContainer = Depends(resolve_container),
    ) -> Response:
        principal = _principal(request)
        token = request.cookies.get(app_container.settings.auth_cookie_name)
        app_container.auth.logout(token)
        app_container.trace.audit(
            None,
            principal.username,
            "auth.logout",
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        response.delete_cookie(app_container.settings.auth_cookie_name, path="/")
        response.status_code = status.HTTP_204_NO_CONTENT
        return response

    @router.get("/users", response_model=list[UserPublic])
    def list_users(
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> list[UserPublic]:
        return app_container.auth.list_users(_principal(request))

    @router.post("/users", response_model=UserPublic, status_code=status.HTTP_201_CREATED)
    def create_user(
        payload: UserCreate,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> UserPublic:
        principal = _principal(request)
        try:
            user = app_container.auth.create_user(principal, payload)
        except AlreadyExistsError as exc:
            raise _conflict("USERNAME_ALREADY_EXISTS", str(exc)) from exc
        app_container.trace.audit(
            None,
            principal.username,
            "user.created",
            {"user_id": user.id, "role": user.role.value},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return user

    @router.patch("/users/{user_id}", response_model=UserPublic)
    def update_user(
        user_id: str,
        payload: UserUpdate,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> UserPublic:
        principal = _principal(request)
        try:
            user = app_container.auth.update_user(principal, user_id, payload)
        except NotFoundError as exc:
            raise _not_found("USER_NOT_FOUND", "User not found") from exc
        except AuthorizationError as exc:
            raise _forbidden(str(exc)) from exc
        app_container.trace.audit(
            None,
            principal.username,
            "user.updated",
            {"user_id": user.id, "role": user.role.value, "status": user.status.value},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return user

    @router.get("/system")
    def system_info(app_container: AppContainer = Depends(resolve_container)) -> dict[str, object]:
        profiles = [app_container.model_gateway.profile_for(agent_name) for agent_name in AgentName]
        live_agents = sum(profile.call_mode == CallMode.LIVE for profile in profiles)
        return {
            "name": "AgentSystem",
            "version": "0.3.0",
            "auth_mode": app_container.settings.auth_mode,
            "execution_mode": "live" if live_agents == len(profiles) else "mixed" if live_agents else "simulated",
            "model_calls_enabled": app_container.settings.model_gateway_calls_enabled,
            "live_agent_count": live_agents,
            "simulated_agent_count": len(profiles) - live_agents,
            "worker_running": bool(app_container.worker and app_container.worker.running),
        }

    @router.get("/model-providers")
    def model_providers(request: Request, app_container: AppContainer = Depends(resolve_container)) -> list[dict[str, object]]:
        _require(request, app_container, Permission.AGENT_READ)
        return [provider.public_payload() for provider in PROVIDER_DEFINITIONS]

    @router.get("/collaboration/rules")
    def collaboration_rules(
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> dict[str, object]:
        _require(request, app_container, Permission.TASK_READ)
        rules = app_container.collaboration_rules.public_rules()
        rules["failure_policy"]["test_repair_attempts"] = app_container.workflow.max_fix_attempts
        return rules

    @router.post("/tasks", response_model=TaskView, status_code=status.HTTP_202_ACCEPTED)
    def create_task(
        payload: TaskCreate,
        request: Request,
        idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
        app_container: AppContainer = Depends(resolve_container),
    ) -> TaskView:
        principal = _require(request, app_container, Permission.TASK_WRITE)
        payload = payload.model_copy(
            update={"tenant_id": principal.tenant_id, "owner_id": principal.user_id}
        )
        scoped_idempotency_key = (
            f"{principal.tenant_id}:{idempotency_key}" if idempotency_key else None
        )
        if scoped_idempotency_key:
            existing = app_container.store.task_for_idempotency_key(scoped_idempotency_key)
            if existing:
                _assert_tenant(existing.tenant_id, principal)
                return app_container.store.task_view(existing.id)
        payload = _normalize_workspace(payload, app_container)
        view = app_container.workflow.create_task_deferred(payload)
        if scoped_idempotency_key:
            app_container.store.remember_idempotency_key(scoped_idempotency_key, view.task.id)
        app_container.trace.audit(
            view.task,
            principal.username,
            "task.created.by_user",
            {"repo_id": view.task.repo_id},
            actor_id=principal.user_id,
        )
        if view.task.status == TaskStatus.QUEUED:
            _enqueue_or_run(
                app_container,
                view.task,
                AgentName.ORCHESTRATOR,
                {"prompt": view.task.prompt},
            )
        return view

    @router.get("/tasks", response_model=list)
    def list_tasks(
        request: Request,
        response: Response,
        task_statuses: list[TaskStatus] = Query(default=[], alias="status"),
        priority: Priority | None = None,
        q: str | None = Query(default=None, max_length=200),
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        app_container: AppContainer = Depends(resolve_container),
    ) -> list:
        principal = _require(request, app_container, Permission.TASK_READ)
        records, total = app_container.store.query_tasks(
            tenant_id=principal.tenant_id,
            statuses=[item.value for item in task_statuses],
            priority=priority.value if priority else None,
            query=q,
            limit=limit,
            offset=offset,
        )
        response.headers["X-Total-Count"] = str(total)
        return records

    @router.get("/tasks/{task_id}", response_model=TaskView)
    def get_task(
        task_id: str,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> TaskView:
        principal = _require(request, app_container, Permission.TASK_READ)
        try:
            _task_for_principal(app_container, task_id, principal)
            return app_container.workflow.get_task(task_id)
        except NotFoundError as exc:
            raise _not_found("TASK_NOT_FOUND", "Task not found") from exc

    @router.post("/tasks/{task_id}/runs", response_model=TaskView, status_code=status.HTTP_202_ACCEPTED)
    def create_run(
        task_id: str,
        payload: RunCreate,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> TaskView:
        principal = _require(request, app_container, Permission.TASK_WRITE)
        try:
            task = _task_for_principal(app_container, task_id, principal)
        except NotFoundError as exc:
            raise _not_found("TASK_NOT_FOUND", "Task not found") from exc
        if task.status in {TaskStatus.RUNNING, TaskStatus.QUEUED, TaskStatus.AWAITING_APPROVAL}:
            raise _conflict("TASK_ALREADY_ACTIVE", "Task already has an active run")
        previous_runs = app_container.store.list_workflow_runs(task_id)
        run = WorkflowRunRecord(
            task_id=task.id,
            trace_id=task.trace_id,
            attempt=len(previous_runs) + 1,
        )
        task.run_id = run.id
        task.status = TaskStatus.QUEUED
        task.current_step = "queued"
        task.failure_code = None
        task.failure_reason = None
        task.pr_url = None
        app_container.store.add_workflow_run(run)
        app_container.store.update_task(task)
        app_container.trace.audit(
            task,
            principal.username,
            "workflow.run.created",
            {"run_id": run.id, "reason": payload.reason},
            actor_id=principal.user_id,
        )
        _enqueue_or_run(app_container, task, AgentName.ORCHESTRATOR, {"prompt": task.prompt})
        return app_container.store.task_view(task.id)

    @router.post("/tasks/{task_id}/cancel", response_model=TaskView)
    def cancel_task(
        task_id: str,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> TaskView:
        principal = _require(request, app_container, Permission.TASK_WRITE)
        try:
            _task_for_principal(app_container, task_id, principal)
            return app_container.workflow.cancel(task_id)
        except NotFoundError as exc:
            raise _not_found("TASK_NOT_FOUND", "Task not found") from exc

    @router.get("/tasks/{task_id}/events")
    async def task_events(
        task_id: str,
        request: Request,
        after: str | None = None,
        follow: bool = Query(default=False),
        app_container: AppContainer = Depends(resolve_container),
    ) -> StreamingResponse:
        principal = _require(request, app_container, Permission.TASK_READ)
        try:
            _task_for_principal(app_container, task_id, principal)
        except NotFoundError as exc:
            raise _not_found("TASK_NOT_FOUND", "Task not found") from exc

        async def stream():
            cursor = after
            idle_ticks = 0
            while True:
                events = app_container.store.list_trace_events(task_id, cursor)
                for event in events:
                    cursor = event.id
                    payload = event.model_dump(mode="json")
                    yield f"id: {event.id}\nevent: {event.event_type}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                if not follow:
                    break
                idle_ticks += 1
                if idle_ticks % 30 == 0:
                    yield ": keepalive\n\n"
                await asyncio.sleep(0.5)

        return StreamingResponse(stream(), media_type="text/event-stream")

    @router.get("/tasks/{task_id}/messages", response_model=list[ChatMessageRecord])
    def list_messages(
        task_id: str,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.TASK_READ)
        try:
            _task_for_principal(app_container, task_id, principal)
            return app_container.store.list_chat_messages(task_id)
        except NotFoundError as exc:
            raise _not_found("TASK_NOT_FOUND", "Task not found") from exc

    @router.post(
        "/tasks/{task_id}/messages",
        response_model=list[ChatMessageRecord],
        status_code=status.HTTP_201_CREATED,
    )
    def create_message(
        task_id: str,
        payload: ChatMessageCreate,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.TASK_CHAT)
        try:
            task = _task_for_principal(app_container, task_id, principal)
        except NotFoundError as exc:
            raise _not_found("TASK_NOT_FOUND", "Task not found") from exc
        user_message = app_container.store.add_chat_message(
            ChatMessageRecord(
                task_id=task.id,
                trace_id=task.trace_id,
                role=ChatRole.USER,
                content=payload.content,
                agent_name=payload.agent_name,
            )
        )
        response = app_container.model_gateway.complete(
            task,
            payload.agent_name,
            "chat",
            f"Task {task.id} at {task.current_step}: {payload.content}",
        )
        assistant_content = (
            response.text
            if not response.simulated
            else (
                f"已将消息加入 {payload.agent_name.value} 的任务上下文。\n\n"
                f"当前配置：`{response.provider}/{response.model}`；本次为模拟响应，未调用外部模型。"
            )
        )
        assistant = app_container.store.add_chat_message(
            ChatMessageRecord(
                task_id=task.id,
                trace_id=task.trace_id,
                role=ChatRole.ASSISTANT,
                agent_name=payload.agent_name,
                content=assistant_content,
            )
        )
        app_container.trace.event(
            task,
            "chat.message",
            payload.agent_name,
            {
                "user_message_id": user_message.id,
                "assistant_message_id": assistant.id,
                "simulated": response.simulated,
            },
        )
        return app_container.store.list_chat_messages(task_id)

    @router.get("/approvals")
    def list_approvals(
        request: Request,
        task_id: str | None = None,
        approval_status: StepStatus | None = Query(default=None, alias="status"),
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.TASK_READ)
        if task_id:
            try:
                _task_for_principal(app_container, task_id, principal)
            except NotFoundError as exc:
                raise _not_found("TASK_NOT_FOUND", "Task not found") from exc
        approvals = app_container.store.list_approvals(task_id=task_id, status=approval_status)
        return [
            item
            for item in approvals
            if _task_in_tenant(app_container, item.task_id, principal.tenant_id)
        ]

    @router.post("/approvals/{approval_id}/decisions", response_model=TaskView)
    def decide_approval(
        approval_id: str,
        payload: ApprovalDecisionV1,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> TaskView:
        principal = _require(request, app_container, Permission.APPROVAL_DECIDE)
        try:
            approval = app_container.store.get_approval(approval_id)
            task = _task_for_principal(app_container, approval.task_id, principal)
        except NotFoundError as exc:
            raise _not_found("APPROVAL_NOT_FOUND", "Approval not found") from exc
        if payload.action == ApprovalAction.CHANGES_REQUESTED:
            candidate = approval.model_copy(deep=True)
            candidate.status = StepStatus.FAILED
            candidate.decided_at = utcnow()
            candidate.decided_by = principal.username
            candidate.comment = payload.comment
            if not app_container.store.decide_approval(candidate, StepStatus.AWAITING_APPROVAL):
                raise _conflict("APPROVAL_ALREADY_DECIDED", "Approval has already been decided")
            task.status = TaskStatus.INPUT_REQUIRED
            task.current_step = "changes_requested"
            task.failure_code = None
            task.failure_reason = payload.comment or "Changes requested"
            app_container.store.update_task(task)
            if task.run_id:
                run = app_container.store.get_workflow_run(task.run_id)
                run.status = RunStatus.AWAITING_APPROVAL
                app_container.store.update_workflow_run(run)
            app_container.trace.event(
                task,
                "approval.changes_requested",
                principal.username,
                {"approval_id": approval_id, "comment": payload.comment},
            )
            return app_container.store.task_view(task.id)

        approved = payload.action == ApprovalAction.APPROVE
        try:
            view = app_container.workflow.approve(
                task.id,
                ApprovalDecision(
                    approval_id=approval_id,
                    approved=approved,
                    actor=principal.username,
                    comment=payload.comment,
                ),
                resume=False,
            )
        except ValueError as exc:
            raise _conflict("APPROVAL_ALREADY_DECIDED", str(exc)) from exc
        if approved:
            next_agent = app_container.workflow.next_agent_after_approval(approval.approval_type)
            _enqueue_or_run(app_container, view.task, next_agent, {"approval_id": approval_id})
        return app_container.store.task_view(task.id)

    @router.post("/projects/pick")
    def pick_project(
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.PROJECT_WRITE)
        result = app_container.workspace_service.pick_directory()
        if result["status"] != "selected":
            return result
        try:
            return app_container.workspace_service.open_workspace(
                WorkspaceOpen(
                    path=result["path"],
                    tenant_id=principal.tenant_id,
                    owner_id=principal.user_id,
                )
            )
        except (NotFoundError, ValueError) as exc:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_PROJECT_PATH", "message": str(exc)},
            ) from exc

    @router.post("/projects", response_model=WorkspaceRecord, status_code=status.HTTP_201_CREATED)
    def add_project(
        payload: WorkspaceOpen,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.PROJECT_WRITE)
        payload = payload.model_copy(
            update={"tenant_id": principal.tenant_id, "owner_id": principal.user_id}
        )
        try:
            return app_container.workspace_service.open_workspace(payload)
        except NotFoundError as exc:
            raise _not_found("PROJECT_NOT_FOUND", "Project path not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "INVALID_PROJECT_PATH", "message": str(exc)}) from exc

    @router.get("/projects", response_model=list[WorkspaceRecord])
    def list_projects(
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.PROJECT_READ)
        return [
            item
            for item in app_container.workspace_service.list_workspaces()
            if item.tenant_id == principal.tenant_id
        ]

    @router.get("/projects/{project_id}/files", response_model=list[WorkspaceFile])
    def project_files(
        project_id: str,
        request: Request,
        path: str = "",
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.PROJECT_READ)
        try:
            _workspace_for_principal(app_container, project_id, principal)
            return app_container.workspace_service.list_files(project_id, path)
        except NotFoundError as exc:
            raise _not_found("PROJECT_PATH_NOT_FOUND", "Project path not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "INVALID_PROJECT_PATH", "message": str(exc)}) from exc

    @router.get("/projects/{project_id}/file")
    def project_file(
        project_id: str,
        request: Request,
        path: str,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.PROJECT_READ)
        try:
            _workspace_for_principal(app_container, project_id, principal)
            return app_container.workspace_service.read_file(project_id, path)
        except NotFoundError as exc:
            raise _not_found("PROJECT_FILE_NOT_FOUND", "Project file not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail={"code": "FILE_PREVIEW_BLOCKED", "message": str(exc)}) from exc

    @router.get("/capabilities/policy")
    def capability_policy(
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> dict[str, object]:
        _require(request, app_container, Permission.AGENT_READ)
        return app_container.capabilities.policy_summary()

    @router.get("/mcp-servers", response_model=list[McpServerRecord])
    def list_mcp_servers(
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> list[McpServerRecord]:
        principal = _require(request, app_container, Permission.AGENT_READ)
        return app_container.capabilities.list_mcp_servers(principal.tenant_id)

    @router.post("/mcp-servers", response_model=McpServerRecord, status_code=status.HTTP_201_CREATED)
    def create_mcp_server(
        payload: McpServerCreate,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> McpServerRecord:
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        try:
            server = app_container.capabilities.create_mcp_server(principal.tenant_id, payload)
        except AlreadyExistsError as exc:
            raise _conflict("MCP_SERVER_ALREADY_EXISTS", "An MCP server with this name already exists") from exc
        except NotFoundError as exc:
            raise _not_found("CREDENTIAL_NOT_FOUND", "Credential reference not found") from exc
        except CapabilityError as exc:
            raise _capability_error(exc) from exc
        app_container.trace.audit(
            None,
            principal.username,
            "mcp.server.created",
            {"server_id": server.id, "name": server.name, "transport": server.transport},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return server

    @router.patch("/mcp-servers/{server_id}", response_model=McpServerRecord)
    def update_mcp_server(
        server_id: str,
        payload: McpServerUpdate,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> McpServerRecord:
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        try:
            server = app_container.capabilities.update_mcp_server(principal.tenant_id, server_id, payload)
        except NotFoundError as exc:
            raise _not_found("MCP_SERVER_NOT_FOUND", "MCP server not found") from exc
        except AlreadyExistsError as exc:
            raise _conflict("MCP_SERVER_ALREADY_EXISTS", "An MCP server with this name already exists") from exc
        except CapabilityError as exc:
            raise _capability_error(exc) from exc
        app_container.trace.audit(
            None,
            principal.username,
            "mcp.server.updated",
            {"server_id": server.id, "version": server.version},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return server

    @router.delete("/mcp-servers/{server_id}", response_model=McpServerRecord)
    def delete_mcp_server(
        server_id: str,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> McpServerRecord:
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        try:
            server = app_container.capabilities.delete_mcp_server(principal.tenant_id, server_id)
        except NotFoundError as exc:
            raise _not_found("MCP_SERVER_NOT_FOUND", "MCP server not found") from exc
        app_container.trace.audit(
            None,
            principal.username,
            "mcp.server.deleted",
            {"server_id": server.id, "name": server.name},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return server

    @router.post("/mcp-servers/{server_id}/validate", response_model=McpValidationResult)
    def validate_mcp_server(
        server_id: str,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> McpValidationResult:
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        try:
            result = app_container.capabilities.validate_mcp_server(principal.tenant_id, server_id)
        except NotFoundError as exc:
            raise _not_found("MCP_SERVER_NOT_FOUND", "MCP server not found") from exc
        app_container.trace.audit(
            None,
            principal.username,
            "mcp.server.validated",
            {"server_id": server_id, "valid": result.valid, "tool_count": len(result.tools)},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return result

    @router.post(
        "/mcp-servers/{server_id}/tools/{tool_name}/invoke",
        response_model=McpToolInvokeResult,
    )
    def invoke_mcp_tool(
        server_id: str,
        tool_name: str,
        payload: McpToolInvokeRequest,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> McpToolInvokeResult:
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        try:
            result = app_container.capabilities.invoke_mcp_tool(
                principal.tenant_id,
                server_id,
                tool_name,
                payload.arguments,
            )
        except NotFoundError as exc:
            raise _not_found("MCP_SERVER_NOT_FOUND", "MCP server not found") from exc
        except CapabilityError as exc:
            raise _capability_error(exc) from exc
        app_container.trace.audit(
            None,
            principal.username,
            "mcp.tool.invoked",
            {"server_id": server_id, "tool_name": tool_name, "is_error": result.is_error},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return result

    @router.get("/skills", response_model=list[SkillRecord])
    def list_skills(
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> list[SkillRecord]:
        principal = _require(request, app_container, Permission.AGENT_READ)
        return app_container.capabilities.list_skills(principal.tenant_id)

    @router.post("/skills", response_model=SkillRecord, status_code=status.HTTP_201_CREATED)
    def import_skill(
        payload: SkillImport,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> SkillRecord:
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        try:
            skill = app_container.capabilities.import_skill(principal.tenant_id, payload)
        except AlreadyExistsError as exc:
            raise _conflict("SKILL_ALREADY_IMPORTED", "This Skill directory is already registered") from exc
        except CapabilityError as exc:
            raise _capability_error(exc) from exc
        app_container.trace.audit(
            None,
            principal.username,
            "skill.imported",
            {"skill_id": skill.id, "name": skill.name, "content_hash": skill.content_hash},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return skill

    @router.post("/skills/pick")
    def pick_skill(
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        result = app_container.workspace_service.pick_directory()
        if result["status"] != "selected":
            return result
        try:
            skill = app_container.capabilities.import_skill(
                principal.tenant_id,
                SkillImport(path=result["path"]),
            )
        except AlreadyExistsError as exc:
            raise _conflict("SKILL_ALREADY_IMPORTED", "This Skill directory is already registered") from exc
        except CapabilityError as exc:
            raise _capability_error(exc) from exc
        app_container.trace.audit(
            None,
            principal.username,
            "skill.imported",
            {"skill_id": skill.id, "name": skill.name, "content_hash": skill.content_hash},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return skill

    @router.patch("/skills/{skill_id}", response_model=SkillRecord)
    def update_skill(
        skill_id: str,
        payload: SkillUpdate,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> SkillRecord:
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        try:
            skill = app_container.capabilities.update_skill(principal.tenant_id, skill_id, payload)
        except NotFoundError as exc:
            raise _not_found("SKILL_NOT_FOUND", "Skill not found") from exc
        app_container.trace.audit(
            None,
            principal.username,
            "skill.updated",
            {"skill_id": skill.id, "enabled": skill.enabled},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return skill

    @router.post("/skills/{skill_id}/refresh", response_model=SkillRecord)
    def refresh_skill(
        skill_id: str,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> SkillRecord:
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        try:
            skill = app_container.capabilities.refresh_skill(principal.tenant_id, skill_id)
        except NotFoundError as exc:
            raise _not_found("SKILL_NOT_FOUND", "Skill not found") from exc
        except CapabilityError as exc:
            raise _capability_error(exc) from exc
        app_container.trace.audit(
            None,
            principal.username,
            "skill.refreshed",
            {"skill_id": skill.id, "content_hash": skill.content_hash},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return skill

    @router.delete("/skills/{skill_id}", response_model=SkillRecord)
    def delete_skill(
        skill_id: str,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> SkillRecord:
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        try:
            skill = app_container.capabilities.delete_skill(principal.tenant_id, skill_id)
        except NotFoundError as exc:
            raise _not_found("SKILL_NOT_FOUND", "Skill not found") from exc
        app_container.trace.audit(
            None,
            principal.username,
            "skill.deleted",
            {"skill_id": skill.id, "name": skill.name},
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return skill

    @router.get("/agents")
    def list_agents(
        request: Request,
        task_id: str | None = None,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.AGENT_READ)
        trace = None
        task = None
        if task_id:
            try:
                _task_for_principal(app_container, task_id, principal)
                trace = app_container.workflow.trace_for_task(task_id)
                task = trace["task"]
            except NotFoundError as exc:
                raise _not_found("TASK_NOT_FOUND", "Task not found") from exc
        latest_runs = {}
        if trace:
            for run in trace["agent_runs"]:
                latest_runs[run.agent_name] = run
        result = []
        for agent_name in AgentName:
            profile = app_container.model_gateway.profile_for(agent_name)
            run = latest_runs.get(agent_name)
            display_name, description = AGENT_DETAILS[agent_name]
            result.append(
                {
                    "agent_name": agent_name,
                    "display_name": display_name,
                    "description": description,
                    "status": _agent_state(task, agent_name, run),
                    "last_summary": run.output_summary if run else None,
                    "handoff_to": run.handoff_to if run else None,
                    "latency_ms": run.latency_ms if run else None,
                    "configuration": _profile_payload(profile),
                    "capabilities": app_container.capabilities.trace_manifest(
                        principal.tenant_id,
                        agent_name,
                    ),
                }
            )
        return result

    @router.get("/agents/{agent_name}/capabilities")
    def get_agent_capabilities(
        agent_name: AgentName,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.AGENT_READ)
        return app_container.capabilities.capabilities_for_agent(principal.tenant_id, agent_name)

    @router.put("/agents/{agent_name}/capabilities")
    def update_agent_capabilities(
        agent_name: AgentName,
        payload: AgentCapabilitiesUpdate,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        try:
            result = app_container.capabilities.replace_agent_capabilities(
                principal.tenant_id,
                agent_name,
                payload,
            )
        except NotFoundError as exc:
            raise _not_found("CAPABILITY_NOT_FOUND", "One or more selected capabilities were not found") from exc
        app_container.trace.audit(
            None,
            principal.username,
            "agent.capabilities.updated",
            {
                "agent_name": agent_name,
                "mcp_server_ids": payload.mcp_server_ids,
                "skill_ids": payload.skill_ids,
            },
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return result

    @router.get("/agents/{agent_name}/configuration")
    def get_agent_configuration(
        agent_name: AgentName,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        _require(request, app_container, Permission.AGENT_READ)
        return _profile_payload(app_container.model_gateway.profile_for(agent_name))

    @router.put("/agents/{agent_name}/configuration")
    def update_agent_configuration(
        agent_name: AgentName,
        payload: AgentConfigurationUpdate,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.AGENT_MANAGE)
        if payload.call_mode == CallMode.LIVE and not app_container.settings.model_gateway_calls_enabled:
            raise _conflict(
                "LIVE_MODE_DISABLED",
                "Live model calls are disabled by the server policy",
            )
        provider = provider_definition(payload.provider_id)
        if payload.provider_id == "simulated" and payload.call_mode == CallMode.LIVE:
            raise _conflict("INVALID_LIVE_PROVIDER", "The simulated provider cannot run in live mode")
        if payload.api_format not in provider.supported_api_formats:
            raise _conflict(
                "MODEL_API_FORMAT_UNSUPPORTED",
                f"{provider.display_name} does not support {payload.api_format.value}",
            )
        if payload.api_key_env and _looks_like_secret_value(payload.api_key_env):
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_API_KEY_ENV", "message": "Enter an environment variable name, not a secret value"},
            )
        if payload.credential_ref:
            try:
                app_container.store.get_credential(payload.credential_ref)
            except NotFoundError as exc:
                raise _not_found("CREDENTIAL_NOT_FOUND", "Credential reference not found") from exc
        current = app_container.store.get_agent_configuration(agent_name)
        record = AgentConfigurationRecord(
            agent_name=agent_name,
            version=(current.version + 1) if current else 1,
            **payload.model_dump(),
        )
        app_container.store.set_agent_configuration(record)
        app_container.trace.audit(
            None,
            principal.username,
            "agent.configuration.updated",
            {
                "agent_name": agent_name,
                "provider_id": record.provider_id,
                "model": record.model,
                "credential_ref": record.credential_ref,
                "call_mode": record.call_mode,
                "version": record.version,
            },
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
        )
        return _profile_payload(app_container.model_gateway.profile_for(agent_name))

    @router.post("/agents/{agent_name}/validate")
    def validate_agent_configuration(
        agent_name: AgentName,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        _require(request, app_container, Permission.AGENT_MANAGE)
        result = app_container.model_gateway.validate_configuration(agent_name)
        profile = app_container.model_gateway.profile_for(agent_name)
        return {
            "valid": result.valid,
            "mode": profile.call_mode,
            "network_attempted": result.network_attempted,
            "provider_id": profile.provider,
            "model": profile.model,
            "models": result.models,
            "message": result.message,
        }

    @router.get("/agents/{agent_name}/models")
    def discover_agent_models(
        agent_name: AgentName,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> dict[str, object]:
        _require(request, app_container, Permission.AGENT_MANAGE)
        try:
            models = app_container.model_gateway.discover_models(agent_name)
        except Exception as exc:
            code = getattr(exc, "code", "MODEL_DISCOVERY_FAILED")
            raise HTTPException(
                status_code=422,
                detail={"code": code, "message": str(exc)},
            ) from exc
        return {"agent_name": agent_name, "models": models}

    @router.post("/credentials", response_model=CredentialMetadataRecord, status_code=status.HTTP_201_CREATED)
    def create_credential(
        payload: CredentialCreate,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.CREDENTIAL_MANAGE)
        try:
            credential = app_container.credentials.create(payload)
            app_container.trace.audit(
                None,
                principal.username,
                "credential.created",
                {"credential_id": credential.id, "fingerprint": credential.fingerprint},
                tenant_id=principal.tenant_id,
                actor_id=principal.user_id,
            )
            return credential
        except CredentialBackendError as exc:
            raise HTTPException(
                status_code=503,
                detail={"code": "CREDENTIAL_BACKEND_UNAVAILABLE", "message": str(exc)},
            ) from exc

    @router.get("/credentials", response_model=list[CredentialMetadataRecord])
    def list_credentials(
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        _require(request, app_container, Permission.CREDENTIAL_MANAGE)
        return app_container.credentials.list()

    @router.get("/credentials/{credential_id}/exists", response_model=CredentialPresence)
    def credential_exists(
        credential_id: str,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        _require(request, app_container, Permission.CREDENTIAL_MANAGE)
        try:
            return CredentialPresence(
                credential_id=credential_id,
                available=app_container.credentials.exists(credential_id),
            )
        except NotFoundError as exc:
            raise _not_found("CREDENTIAL_NOT_FOUND", "Credential not found") from exc

    @router.delete("/credentials/{credential_id}", response_model=CredentialMetadataRecord)
    def delete_credential(
        credential_id: str,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.CREDENTIAL_MANAGE)
        try:
            credential = app_container.credentials.delete(credential_id)
            app_container.trace.audit(
                None,
                principal.username,
                "credential.deleted",
                {"credential_id": credential.id},
                tenant_id=principal.tenant_id,
                actor_id=principal.user_id,
            )
            return credential
        except NotFoundError as exc:
            raise _not_found("CREDENTIAL_NOT_FOUND", "Credential not found") from exc

    @router.get("/traces/{trace_id}")
    def get_trace(
        trace_id: str,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.TASK_READ)
        task = next(
            (
                item
                for item in app_container.store.list_tasks()
                if item.trace_id == trace_id and item.tenant_id == principal.tenant_id
            ),
            None,
        )
        if task is None:
            raise _not_found("TRACE_NOT_FOUND", "Trace not found")
        return app_container.store.trace_for_task(task.id)

    @router.get("/artifacts/{artifact_id}")
    def get_artifact(
        artifact_id: str,
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.TASK_READ)
        try:
            artifact = app_container.store.get_artifact(artifact_id)
            _task_for_principal(app_container, artifact.task_id, principal)
            return artifact
        except NotFoundError as exc:
            raise _not_found("ARTIFACT_NOT_FOUND", "Artifact not found") from exc

    @router.get("/operations/summary")
    def operations_summary(
        request: Request,
        app_container: AppContainer = Depends(resolve_container),
    ) -> dict[str, object]:
        principal = _require(request, app_container, Permission.OPERATIONS_READ)
        tasks = [item for item in app_container.store.list_tasks() if item.tenant_id == principal.tenant_id]
        total = len(tasks)
        tenant_task_ids = {item.id for item in tasks}
        counts = {task_status.value: 0 for task_status in TaskStatus}
        for task in tasks:
            counts[task.status.value] += 1
        pending_approvals = sum(
            1
            for item in app_container.store.list_approvals(status=StepStatus.AWAITING_APPROVAL)
            if item.task_id in tenant_task_ids
        )
        model_calls = [item for item in app_container.store.model_calls.values() if item.task_id in tenant_task_ids]
        tool_calls = [item for item in app_container.store.tool_calls.values() if item.task_id in tenant_task_ids]
        return {
            "total_tasks": total,
            "status_counts": counts,
            "active_tasks": sum(counts[item] for item in ("queued", "running", "awaiting_approval", "input_required")),
            "pending_approvals": pending_approvals,
            "model_calls": {
                "total": len(model_calls),
                "live": sum(not item.simulated for item in model_calls),
                "simulated": sum(item.simulated for item in model_calls),
                "cost": round(sum(item.total_cost for item in model_calls), 6),
            },
            "tool_calls": {
                "total": len(tool_calls),
                "denied": sum(not item.allowed for item in tool_calls),
            },
        }

    @router.get("/audit-logs")
    def audit_logs(
        request: Request,
        response: Response,
        action: str | None = Query(default=None, max_length=160),
        q: str | None = Query(default=None, max_length=200),
        limit: int = Query(default=100, ge=1, le=200),
        offset: int = Query(default=0, ge=0),
        app_container: AppContainer = Depends(resolve_container),
    ):
        principal = _require(request, app_container, Permission.AUDIT_READ)
        records, total = app_container.store.list_audit_logs(
            tenant_id=principal.tenant_id,
            action=action,
            query=q,
            limit=limit,
            offset=offset,
        )
        response.headers["X-Total-Count"] = str(total)
        return records

    return router


def _normalize_workspace(payload: TaskCreate, container: AppContainer) -> TaskCreate:
    if not payload.workspace_path:
        return payload
    try:
        workspace = container.workspace_service.workspace_for_path(
            payload.workspace_path,
            tenant_id=payload.tenant_id,
            owner_id=payload.owner_id,
        )
    except NotFoundError as exc:
        raise _not_found("PROJECT_NOT_FOUND", "Project path not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "INVALID_PROJECT_PATH", "message": str(exc)}) from exc
    return payload.model_copy(update={"workspace_path": workspace.path})


def _enqueue_or_run(
    container: AppContainer,
    task,
    start_agent: AgentName,
    context: dict[str, object],
) -> None:
    if container.worker:
        container.worker.enqueue(task, start_agent=start_agent, context=context)
    else:
        container.workflow.execute_task(task.id, start=start_agent, context=context)


def _profile_payload(profile) -> dict[str, object]:
    return {
        "agent_name": profile.agent_name,
        "provider_id": profile.provider,
        "model": profile.model,
        "credential_ref": profile.credential_ref,
        "api_key_env": profile.api_key_env or None,
        "credential_available": profile.api_key_present,
        "base_url": profile.base_url,
        "api_format": profile.api_format,
        "call_mode": profile.call_mode,
        "timeout_seconds": profile.timeout_seconds,
        "max_output_tokens": profile.max_output_tokens,
        "budget_limit": profile.budget_limit,
        "version": profile.version,
        "network_enabled": profile.calls_enabled,
    }


def _looks_like_secret_value(value: str) -> bool:
    normalized = value.strip()
    if normalized.startswith(("sk-", "sk_")):
        return True
    return len(normalized) > 40 and any(char.isdigit() for char in normalized)


def _agent_state(task, agent_name: AgentName, run) -> str:
    if task is None:
        return "idle"
    if task.status == TaskStatus.AWAITING_APPROVAL and task.current_step == f"awaiting_{agent_name.value}_approval":
        return StepStatus.AWAITING_APPROVAL
    approval_owner = {
        "awaiting_plan_approval": AgentName.PLANNING,
        "awaiting_create_pr_approval": AgentName.PR,
        "awaiting_high_risk_change_approval": AgentName.SECURITY,
        "awaiting_push_branch_approval": AgentName.PR,
    }.get(task.current_step)
    if approval_owner == agent_name:
        return StepStatus.AWAITING_APPROVAL
    if run is None:
        return StepStatus.PENDING
    if run.output_summary and run.output_summary.startswith("failed:"):
        return StepStatus.FAILED
    if run.completed_at is None:
        return StepStatus.RUNNING
    return StepStatus.COMPLETED


def _not_found(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=404, detail={"code": code, "message": message})


def _conflict(code: str, message: str) -> HTTPException:
    return HTTPException(status_code=409, detail={"code": code, "message": message})


def _capability_error(error: CapabilityError) -> HTTPException:
    status_code = 403 if error.code.endswith("_DISABLED") or error.code in {
        "MCP_HOST_BLOCKED",
        "MCP_COMMAND_BLOCKED",
        "SKILL_PATH_BLOCKED",
    } else 422
    return HTTPException(
        status_code=status_code,
        detail={
            "code": error.code,
            "message": str(error),
            "details": {"network_attempted": error.network_attempted},
        },
    )


def _forbidden(message: str = "You do not have permission to perform this action") -> HTTPException:
    return HTTPException(status_code=403, detail={"code": "PERMISSION_DENIED", "message": message})


def _principal(request: Request) -> Principal:
    principal = getattr(request.state, "principal", None)
    if principal is None:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTHENTICATION_REQUIRED", "message": "Sign in is required"},
        )
    return principal


def _require(request: Request, container: AppContainer, permission: Permission) -> Principal:
    principal = _principal(request)
    try:
        container.auth.require(principal, permission)
    except AuthorizationError as exc:
        raise _forbidden(str(exc)) from exc
    return principal


def _assert_tenant(resource_tenant_id: str, principal: Principal) -> None:
    if resource_tenant_id != principal.tenant_id:
        raise NotFoundError("resource")


def _task_for_principal(
    container: AppContainer,
    task_id: str,
    principal: Principal,
):
    task = container.store.get_task(task_id)
    _assert_tenant(task.tenant_id, principal)
    return task


def _workspace_for_principal(
    container: AppContainer,
    workspace_id: str,
    principal: Principal,
):
    workspace = container.store.get_workspace(workspace_id)
    _assert_tenant(workspace.tenant_id, principal)
    return workspace


def _task_in_tenant(container: AppContainer, task_id: str, tenant_id: str) -> bool:
    try:
        return container.store.get_task(task_id).tenant_id == tenant_id
    except NotFoundError:
        return False
