from fastapi.testclient import TestClient

from agentsystem.api import create_app
from agentsystem.container import AppContainer


def test_task_api_approval_flow() -> None:
    client = TestClient(create_app(AppContainer()))

    created = client.post(
        "/tasks",
        json={
            "repo_id": "github.example.com/acme/payments",
            "base_branch": "main",
            "prompt": "Fix retry handling",
            "approval_policy": "manual_plan",
            "priority": "normal",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["task"]["status"] == "awaiting_approval"
    approval_id = payload["approvals"][0]["id"]
    task_id = payload["task"]["id"]

    approved = client.post(
        f"/tasks/{task_id}/approve",
        json={"approval_id": approval_id, "approved": True, "actor": "pytest"},
    )

    assert approved.status_code == 200
    assert approved.json()["task"]["status"] == "completed"


def test_root_serves_console_ui() -> None:
    client = TestClient(create_app(AppContainer()))

    response = client.get("/")

    assert response.status_code == 200
    assert '<div id="root"></div>' in response.text
    assert "AgentSystem" in response.text

    legacy = client.get("/legacy")
    assert legacy.status_code == 200
    response = legacy
    assert "AgentSystem 控制台" in response.text
    assert "创建任务" in response.text
    assert "Agent 工作状态" in response.text
    assert "Agent 模型路由" in response.text
    assert "本地项目" in response.text
    assert "AI 协作对话" in response.text
    assert "切换白天黑夜模式" in response.text
    assert "界面语言" in response.text
    assert "agentsystem-language" in response.text
    assert "选择项目目录" in response.text


def test_workspace_open_and_task_context(tmp_path) -> None:
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "example.py").write_text("def ok():\n    return True\n")
    client = TestClient(create_app(AppContainer()))

    opened = client.post("/workspaces/open", json={"path": str(tmp_path)})

    assert opened.status_code == 201
    workspace = opened.json()
    assert workspace["path"] == str(tmp_path)
    assert workspace["file_count"] == 1

    files = client.get(f"/workspaces/{workspace['id']}/files")
    assert files.status_code == 200
    assert files.json()[0]["path"] == "src"

    created = client.post(
        "/tasks",
        json={
            "repo_id": "local/example",
            "base_branch": "main",
            "prompt": "Explain local source layout",
            "workspace_path": str(tmp_path),
            "approval_policy": "manual_plan",
            "priority": "normal",
        },
    )

    assert created.status_code == 201
    payload = created.json()
    assert payload["task"]["workspace_path"] == str(tmp_path)
    repo_context = next(item for item in payload["artifacts"] if item["kind"] == "repo_context")
    assert "Local workspace" in repo_context["content"]
    assert "src/example.py" in repo_context["content"]


def test_workspace_picker_endpoint(monkeypatch, tmp_path) -> None:
    client = TestClient(create_app(AppContainer()))

    def fake_pick_directory(self) -> dict[str, str]:
        return {"status": "selected", "path": str(tmp_path)}

    monkeypatch.setattr("agentsystem.workspace.WorkspaceService.pick_directory", fake_pick_directory)

    picked = client.post("/workspaces/pick")

    assert picked.status_code == 200
    assert picked.json() == {"status": "selected", "path": str(tmp_path)}


def test_task_chat_messages_are_agent_routed(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n")
    client = TestClient(create_app(AppContainer()))
    created = client.post(
        "/tasks",
        json={
            "repo_id": "local/example",
            "base_branch": "main",
            "prompt": "Review this project",
            "workspace_path": str(tmp_path),
            "approval_policy": "manual_plan",
            "priority": "normal",
        },
    ).json()
    task_id = created["task"]["id"]

    response = client.post(
        f"/tasks/{task_id}/messages",
        json={"agent_name": "coding", "content": "请帮我定位应该修改哪些文件"},
    )

    assert response.status_code == 201
    messages = response.json()
    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[-1]["agent_name"] == "coding"
    assert "openai/gpt-5.6-sol" in messages[-1]["content"]

    trace = client.get(f"/tasks/{task_id}/trace").json()
    assert trace["chat_messages"][-1]["role"] == "assistant"
    assert trace["model_calls"][-1]["agent_name"] == "coding"


def test_agent_model_config_endpoint_never_returns_secret_values() -> None:
    client = TestClient(create_app(AppContainer()))

    response = client.get("/agent-models")

    assert response.status_code == 200
    payload = response.json()
    assert {item["agent_name"] for item in payload} >= {"orchestrator", "coding", "review"}
    assert all("api_key_env" in item for item in payload)
    assert all("api_key" not in item for item in payload)


def test_agent_model_config_can_be_overridden_per_agent(tmp_path) -> None:
    (tmp_path / "README.md").write_text("# Demo\n")
    client = TestClient(create_app(AppContainer()))

    updated = client.put(
        "/agent-models/coding",
        json={
            "provider": "local-vllm",
            "model": "qwen2.5-coder-enterprise",
            "api_key_env": "CUSTOM_CODING_AGENT_API_KEY",
            "base_url": "http://model-gateway.internal/v1",
            "calls_enabled": False,
        },
    )

    assert updated.status_code == 200
    assert updated.json()["provider"] == "local-vllm"
    assert updated.json()["model"] == "qwen2.5-coder-enterprise"
    assert updated.json()["api_key_env"] == "CUSTOM_CODING_AGENT_API_KEY"
    assert "api_key" not in updated.json()

    status = client.get("/agent-status").json()
    coding_status = next(item for item in status if item["agent_name"] == "coding")
    assert coding_status["provider"] == "local-vllm"
    assert coding_status["model"] == "qwen2.5-coder-enterprise"

    task_id = client.post(
        "/tasks",
        json={
            "repo_id": "local/example",
            "base_branch": "main",
            "prompt": "Review this project",
            "workspace_path": str(tmp_path),
            "approval_policy": "manual_plan",
            "priority": "normal",
        },
    ).json()["task"]["id"]
    response = client.post(
        f"/tasks/{task_id}/messages",
        json={"agent_name": "coding", "content": "请帮我定位应该修改哪些文件"},
    )

    assert response.status_code == 201
    assert "local-vllm/qwen2.5-coder-enterprise" in response.json()[-1]["content"]
    trace = client.get(f"/tasks/{task_id}/trace").json()
    assert trace["model_calls"][-1]["api_key_env"] == "CUSTOM_CODING_AGENT_API_KEY"


def test_agent_model_config_rejects_secret_like_api_key_env() -> None:
    client = TestClient(create_app(AppContainer()))

    response = client.put(
        "/agent-models/coding",
        json={
            "provider": "openai-compatible",
            "model": "gpt-5.5",
            "api_key_env": "sk-this-looks-like-a-real-secret-value",
            "calls_enabled": False,
        },
    )

    assert response.status_code == 400


def test_agent_status_endpoint_tracks_selected_task() -> None:
    client = TestClient(create_app(AppContainer()))
    created = client.post(
        "/tasks",
        json={
            "repo_id": "github.example.com/acme/payments",
            "base_branch": "main",
            "prompt": "Fix retry handling",
            "approval_policy": "manual_plan",
            "priority": "normal",
        },
    ).json()

    task_id = created["task"]["id"]
    response = client.get(f"/agent-status?task_id={task_id}")

    assert response.status_code == 200
    payload = response.json()
    by_agent = {item["agent_name"]: item for item in payload}
    assert by_agent["orchestrator"]["status"] == "completed"
    assert by_agent["planning"]["status"] == "awaiting_approval"
    assert by_agent["coding"]["status"] == "pending"
    assert by_agent["planning"]["api_key_env"] == "PLANNING_AGENT_API_KEY"


def test_github_webhook_creates_task() -> None:
    client = TestClient(create_app(AppContainer()))

    response = client.post(
        "/webhooks/github",
        json={
            "event_type": "issues.opened",
            "repo_id": "github.example.com/acme/payments",
            "prompt": "Fix checkout retry issue",
            "issue_url": "https://github.example.com/acme/payments/issues/7",
        },
    )

    assert response.status_code == 202
    assert response.json()["task"]["issue_url"].endswith("/issues/7")
