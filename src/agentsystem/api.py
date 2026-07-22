from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import asdict
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from agentsystem.api_v1 import build_v1_router, extract_token
from agentsystem.auth import AuthenticationError, AuthorizationError
from agentsystem.config import get_settings
from agentsystem.container import AppContainer, get_container
from agentsystem.domain import (
    AgentModelUpdate,
    AgentName,
    ApprovalDecision,
    CallMode,
    ChatMessageCreate,
    ChatMessageRecord,
    ChatRole,
    GitHubWebhookEvent,
    StepStatus,
    TaskCreate,
    TaskRecord,
    TaskStatus,
    TaskView,
    UserRole,
    WorkspaceFile,
    WorkspaceOpen,
    WorkspaceRecord,
)
from agentsystem.model_gateway import ModelGatewayError
from agentsystem.store import NotFoundError


def create_app(container: AppContainer | None = None) -> FastAPI:
    def resolve_container() -> AppContainer:
        return container or get_container()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        app_container = resolve_container()
        app_container.start_background_services()
        try:
            yield
        finally:
            app_container.stop_background_services()

    app = FastAPI(
        title="AgentSystem",
        version="0.3.0",
        description="Private multi-agent code collaboration platform MVP.",
        lifespan=lifespan,
    )

    cors_origins = [origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()]
    if cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["Content-Type", "Authorization", "Idempotency-Key", "X-Request-ID"],
            expose_headers=["X-Total-Count", "X-Request-ID"],
        )

    @app.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or f"req_{uuid4().hex[:16]}"
        request.state.request_id = request_id
        path = request.url.path
        public_api_paths = {"/health", "/api/v1/system", "/api/v1/auth/login"}
        legacy_api_prefixes = (
            "/agent-models",
            "/workspaces",
            "/agent-status",
            "/tasks",
            "/webhooks",
        )
        protected_api = (
            path.startswith("/api/v1/")
            or any(path == prefix or path.startswith(f"{prefix}/") for prefix in legacy_api_prefixes)
        ) and path not in public_api_paths
        if protected_api:
            token = extract_token(request, resolve_container().settings.auth_cookie_name)
            try:
                request.state.principal = resolve_container().auth.principal_for_token(token)
            except AuthenticationError as exc:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "code": "AUTHENTICATION_REQUIRED",
                            "message": str(exc),
                            "request_id": request_id,
                            "details": {},
                        }
                    },
                    headers={"X-Request-ID": request_id},
                )
            if not path.startswith("/api/v1/") and request.state.principal.role != UserRole.ADMIN:
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": {
                            "code": "LEGACY_API_ADMIN_ONLY",
                            "message": "Legacy API compatibility routes are restricted to administrators",
                            "request_id": request_id,
                            "details": {},
                        }
                    },
                    headers={"X-Request-ID": request_id},
                )
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "same-origin"
        response.headers["X-Frame-Options"] = "DENY"
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException):
        details = exc.detail if isinstance(exc.detail, dict) else {}
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": details.get("code", f"HTTP_{exc.status_code}"),
                    "message": details.get("message", str(exc.detail)),
                    "request_id": getattr(request.state, "request_id", None),
                    "details": details.get("details", {}),
                }
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed",
                    "request_id": getattr(request.state, "request_id", None),
                    "details": {"errors": exc.errors()},
                }
            },
        )

    @app.exception_handler(ModelGatewayError)
    async def model_gateway_error(request: Request, exc: ModelGatewayError):
        return JSONResponse(
            status_code=503 if exc.retryable else 502,
            content={
                "error": {
                    "code": exc.code,
                    "message": str(exc),
                    "request_id": getattr(request.state, "request_id", None),
                    "details": {"retryable": exc.retryable},
                }
            },
        )

    @app.exception_handler(AuthorizationError)
    async def authorization_error(request: Request, exc: AuthorizationError):
        return JSONResponse(
            status_code=403,
            content={
                "error": {
                    "code": "PERMISSION_DENIED",
                    "message": str(exc),
                    "request_id": getattr(request.state, "request_id", None),
                    "details": {},
                }
            },
        )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/agent-models")
    def agent_models(app_container: AppContainer = Depends(resolve_container)) -> list[dict[str, object]]:
        return [_model_config_payload(app_container.model_gateway.profile_for(agent_name)) for agent_name in AgentName]

    @app.put("/agent-models/{agent_name}")
    def update_agent_model(
        agent_name: AgentName,
        payload: AgentModelUpdate,
        app_container: AppContainer = Depends(resolve_container),
    ) -> dict[str, object]:
        if _looks_like_secret_value(payload.api_key_env):
            raise HTTPException(
                status_code=400,
                detail="api_key_env must be an environment variable name, not a secret value",
            )
        app_container.store.set_agent_model_override(agent_name, payload)
        config = app_container.model_gateway.profile_for(agent_name)
        app_container.trace.audit(
            None,
            "console",
            "agent_model.updated",
            {
                "agent_name": agent_name,
                "provider": config.provider,
                "model": config.model,
                "api_key_env": config.api_key_env,
                "calls_enabled": config.calls_enabled,
            },
        )
        return _model_config_payload(config)

    @app.get("/workspaces", response_model=list[WorkspaceRecord])
    def list_workspaces(app_container: AppContainer = Depends(resolve_container)) -> list[WorkspaceRecord]:
        return app_container.workspace_service.list_workspaces()

    @app.post("/workspaces/open", response_model=WorkspaceRecord, status_code=status.HTTP_201_CREATED)
    def open_workspace(
        payload: WorkspaceOpen,
        app_container: AppContainer = Depends(resolve_container),
    ) -> WorkspaceRecord:
        try:
            workspace = app_container.workspace_service.open_workspace(payload)
            app_container.trace.audit(
                None,
                "console",
                "workspace.opened",
                {"workspace_id": workspace.id, "path": workspace.path},
            )
            return workspace
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Workspace path not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/workspaces/pick")
    def pick_workspace(app_container: AppContainer = Depends(resolve_container)) -> dict[str, str]:
        try:
            result = app_container.workspace_service.pick_directory()
            app_container.trace.audit(None, "console", "workspace.pick", result)
            return result
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Workspace path not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/workspaces/{workspace_id}/files", response_model=list[WorkspaceFile])
    def list_workspace_files(
        workspace_id: str,
        path: str = "",
        app_container: AppContainer = Depends(resolve_container),
    ) -> list[WorkspaceFile]:
        try:
            return app_container.workspace_service.list_files(workspace_id, path)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Workspace path not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/workspaces/{workspace_id}/file")
    def read_workspace_file(
        workspace_id: str,
        path: str,
        app_container: AppContainer = Depends(resolve_container),
    ) -> dict[str, object]:
        try:
            return app_container.workspace_service.read_file(workspace_id, path)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Workspace file not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/workspaces/{workspace_id}/reveal")
    def reveal_workspace(
        workspace_id: str,
        app_container: AppContainer = Depends(resolve_container),
    ) -> dict[str, str]:
        try:
            return app_container.workspace_service.reveal(workspace_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Workspace not found") from exc

    @app.get("/agent-status")
    def agent_status(
        task_id: str | None = None,
        app_container: AppContainer = Depends(resolve_container),
    ) -> list[dict[str, object]]:
        task = None
        trace: dict[str, object] | None = None
        if task_id:
            try:
                trace = app_container.workflow.trace_for_task(task_id)
                task = trace["task"]
            except NotFoundError as exc:
                raise HTTPException(status_code=404, detail="Task not found") from exc

        runs_by_agent = {}
        model_calls_by_agent = {}
        if trace:
            for run in trace["agent_runs"]:
                runs_by_agent[run.agent_name] = run
            for call in trace["model_calls"]:
                model_calls_by_agent[call.agent_name] = call

        statuses: list[dict[str, object]] = []
        for agent_name in AgentName:
            config = app_container.model_gateway.profile_for(agent_name)
            run = runs_by_agent.get(config.agent_name)
            model_call = model_calls_by_agent.get(config.agent_name)
            state = _agent_state(task, config.agent_name, run)
            statuses.append(
                {
                    "agent_name": config.agent_name,
                    "status": state,
                    "provider": config.provider,
                    "model": config.model,
                    "api_key_env": config.api_key_env,
                    "api_key_present": config.api_key_present,
                    "base_url": config.base_url,
                    "calls_enabled": config.calls_enabled,
                    "simulated": config.call_mode == CallMode.SIMULATED,
                    "last_summary": run.output_summary if run else None,
                    "handoff_to": run.handoff_to if run else None,
                    "latency_ms": run.latency_ms if run else None,
                    "last_model_call_id": model_call.id if model_call else None,
                }
            )
        return statuses

    @app.post("/tasks", response_model=TaskView, status_code=status.HTTP_201_CREATED)
    def create_task(
        payload: TaskCreate,
        app_container: AppContainer = Depends(resolve_container),
    ) -> TaskView:
        if payload.workspace_path:
            try:
                workspace = app_container.workspace_service.workspace_for_path(payload.workspace_path)
            except NotFoundError as exc:
                raise HTTPException(status_code=404, detail="Workspace path not found") from exc
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            payload = payload.model_copy(update={"workspace_path": workspace.path})
        return app_container.workflow.create_task(payload)

    @app.get("/tasks", response_model=list[TaskRecord])
    def list_tasks(app_container: AppContainer = Depends(resolve_container)) -> list[TaskRecord]:
        return app_container.workflow.list_tasks()

    @app.get("/tasks/{task_id}", response_model=TaskView)
    def get_task(
        task_id: str,
        app_container: AppContainer = Depends(resolve_container),
    ) -> TaskView:
        try:
            return app_container.workflow.get_task(task_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Task not found") from exc

    @app.get("/tasks/{task_id}/messages", response_model=list[ChatMessageRecord])
    def list_task_messages(
        task_id: str,
        app_container: AppContainer = Depends(resolve_container),
    ) -> list[ChatMessageRecord]:
        try:
            return app_container.store.list_chat_messages(task_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Task not found") from exc

    @app.post("/tasks/{task_id}/messages", response_model=list[ChatMessageRecord], status_code=status.HTTP_201_CREATED)
    def send_task_message(
        task_id: str,
        payload: ChatMessageCreate,
        app_container: AppContainer = Depends(resolve_container),
    ) -> list[ChatMessageRecord]:
        try:
            task = app_container.store.get_task(task_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Task not found") from exc

        user_message = app_container.store.add_chat_message(
            ChatMessageRecord(
                task_id=task.id,
                trace_id=task.trace_id,
                role=ChatRole.USER,
                content=payload.content,
                agent_name=payload.agent_name,
            )
        )
        model_response = app_container.model_gateway.complete(
            task,
            payload.agent_name,
            "chat",
            _chat_prompt(task, payload.content, payload.agent_name),
        )
        assistant_message = app_container.store.add_chat_message(
            ChatMessageRecord(
                task_id=task.id,
                trace_id=task.trace_id,
                role=ChatRole.ASSISTANT,
                agent_name=payload.agent_name,
                content=(
                    _assistant_chat_reply(task, payload.content, model_response.provider, model_response.model)
                    if model_response.simulated
                    else model_response.text
                ),
            )
        )
        app_container.trace.event(
            task,
            "chat.message",
            payload.agent_name,
            {
                "user_message_id": user_message.id,
                "assistant_message_id": assistant_message.id,
                "simulated": model_response.simulated,
            },
        )
        app_container.trace.audit(
            task,
            "console",
            "chat.message.created",
            {"agent_name": payload.agent_name, "message_id": user_message.id},
        )
        return app_container.store.list_chat_messages(task_id)

    @app.post("/tasks/{task_id}/approve", response_model=TaskView)
    def approve_task(
        task_id: str,
        payload: ApprovalDecision,
        app_container: AppContainer = Depends(resolve_container),
    ) -> TaskView:
        try:
            return app_container.workflow.approve(task_id, payload)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Task or approval not found") from exc
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc

    @post_cancel(app)
    def cancel_task(
        task_id: str,
        app_container: AppContainer = Depends(resolve_container),
    ) -> TaskView:
        try:
            return app_container.workflow.cancel(task_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Task not found") from exc

    @app.post("/webhooks/github", response_model=TaskView, status_code=status.HTTP_202_ACCEPTED)
    def github_webhook(
        payload: GitHubWebhookEvent,
        app_container: AppContainer = Depends(resolve_container),
    ) -> TaskView:
        return app_container.workflow.create_task_from_webhook(payload)

    @app.get("/tasks/{task_id}/trace")
    def get_trace(
        task_id: str,
        app_container: AppContainer = Depends(resolve_container),
    ) -> dict[str, object]:
        try:
            return app_container.workflow.trace_for_task(task_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=404, detail="Task not found") from exc

    app.include_router(build_v1_router(resolve_container))

    return app


def post_cancel(app: FastAPI):
    return app.post("/tasks/{task_id}/cancel", response_model=TaskView)


def _model_config_payload(config) -> dict[str, object]:
    return {
        **asdict(config),
        "agent_name": config.agent_name,
    }


def _looks_like_secret_value(value: str) -> bool:
    normalized = value.strip()
    if normalized.startswith(("sk-", "sk_")):
        return True
    return len(normalized) > 40 and any(char.isdigit() for char in normalized)


def _agent_state(task: TaskRecord | None, agent_name: AgentName, run) -> str:
    if task is None:
        return "idle"

    approval_agent = _approval_agent_for_step(task.current_step)
    if approval_agent == agent_name and task.status == TaskStatus.AWAITING_APPROVAL:
        return StepStatus.AWAITING_APPROVAL

    if run is None:
        return StepStatus.PENDING

    if run.output_summary and run.output_summary.startswith("failed:"):
        return StepStatus.FAILED
    if run.completed_at is None:
        return StepStatus.RUNNING
    if task.status == TaskStatus.RUNNING and task.current_step == agent_name:
        return StepStatus.RUNNING
    return StepStatus.COMPLETED


def _approval_agent_for_step(current_step: str) -> AgentName | None:
    if current_step == "awaiting_plan_approval":
        return AgentName.PLANNING
    if current_step == "awaiting_create_pr_approval":
        return AgentName.PR
    if current_step == "awaiting_high_risk_change_approval":
        return AgentName.SECURITY
    if current_step == "awaiting_push_branch_approval":
        return AgentName.PR
    return None


def _chat_prompt(task: TaskRecord, content: str, agent_name: AgentName) -> str:
    workspace = f"\nWorkspace: {task.workspace_path}" if task.workspace_path else ""
    return (
        f"Task {task.id} is at step {task.current_step}.{workspace}\n"
        f"User asks {agent_name}: {content}"
    )


def _assistant_chat_reply(task: TaskRecord, content: str, provider: str, model: str) -> str:
    workspace_line = (
        f"\n- 已绑定本地项目：`{task.workspace_path}`"
        if task.workspace_path
        else "\n- 尚未绑定本地项目，可先在左侧打开项目目录。"
    )
    return (
        f"已接收你的协作消息：{content}\n\n"
        f"- 当前任务：`{task.id}` / `{task.current_step}`"
        f"{workspace_line}\n"
        f"- 当前回复由 `{provider}/{model}` 的配置层模拟生成，未发起真实模型调用。\n"
        "- 后续可以把这条消息作为计划调整、代码定位、补丁开发或审查上下文。"
    )
