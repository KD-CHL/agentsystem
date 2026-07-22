from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import SecretStr

from agentsystem.api import create_app
from agentsystem.config import Settings
from agentsystem.container import AppContainer
from agentsystem.domain import ApprovalPolicy, Priority, TaskRecord


def local_settings(**overrides) -> Settings:
    return Settings(
        auth_mode="local",
        bootstrap_admin_username="admin",
        bootstrap_admin_password=SecretStr("test-only-admin-password"),
        **overrides,
    )


def login(client: TestClient, username: str = "admin", password: str = "test-only-admin-password"):
    return client.post("/api/v1/auth/login", json={"username": username, "password": password})


def test_local_auth_requires_session_and_never_returns_password_hash() -> None:
    client = TestClient(create_app(AppContainer(settings=local_settings())))

    unauthorized = client.get("/api/v1/tasks")
    signed_in = login(client)
    me = client.get("/api/v1/auth/me")

    assert unauthorized.status_code == 401
    assert unauthorized.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert signed_in.status_code == 200
    assert signed_in.json()["user"]["role"] == "admin"
    assert "password" not in signed_in.text
    assert me.status_code == 200
    assert "password" not in me.text


def test_role_permissions_and_legacy_bypass_are_blocked() -> None:
    container = AppContainer(settings=local_settings())
    admin = TestClient(create_app(container))
    assert login(admin).status_code == 200
    created_user = admin.post(
        "/api/v1/users",
        json={
            "username": "reader",
            "display_name": "Read Only",
            "password": "test-only-reader-password",
            "role": "viewer",
        },
    )
    assert created_user.status_code == 201

    viewer = TestClient(create_app(container))
    assert login(viewer, "reader", "test-only-reader-password").status_code == 200
    assert viewer.get("/api/v1/tasks").status_code == 200
    forbidden = viewer.post(
        "/api/v1/tasks",
        json={"repo_id": "local/demo", "prompt": "Create a task"},
    )
    legacy_forbidden = viewer.post(
        "/tasks",
        json={"repo_id": "local/demo", "prompt": "Bypass RBAC"},
    )

    assert forbidden.status_code == 403
    assert forbidden.json()["error"]["code"] == "PERMISSION_DENIED"
    assert legacy_forbidden.status_code == 403
    assert legacy_forbidden.json()["error"]["code"] == "LEGACY_API_ADMIN_ONLY"


def test_server_owns_tenant_and_hides_cross_tenant_resources() -> None:
    container = AppContainer(settings=local_settings())
    client = TestClient(create_app(container))
    assert login(client).status_code == 200

    created = client.post(
        "/api/v1/tasks",
        json={
            "repo_id": "local/demo",
            "prompt": "Verify tenant ownership",
            "tenant_id": "attacker-controlled",
            "owner_id": "attacker-controlled",
            "approval_policy": "manual_plan",
        },
    )
    assert created.status_code == 202
    task = created.json()["task"]
    assert task["tenant_id"] == "default"
    assert task["owner_id"] == "user_local_admin"

    foreign = TaskRecord(
        tenant_id="another-tenant",
        owner_id="foreign-user",
        repo_id="private/foreign",
        base_branch="main",
        prompt="Foreign task",
        approval_policy=ApprovalPolicy.MANUAL_PLAN,
        priority=Priority.NORMAL,
    )
    container.store.create_task(foreign)
    hidden = client.get(f"/api/v1/tasks/{foreign.id}")
    listed = client.get("/api/v1/tasks").json()

    assert hidden.status_code == 404
    assert all(item["id"] != foreign.id for item in listed)


def test_disabled_user_sessions_are_revoked() -> None:
    container = AppContainer(settings=local_settings())
    admin = TestClient(create_app(container))
    assert login(admin).status_code == 200
    user = admin.post(
        "/api/v1/users",
        json={
            "username": "operator",
            "display_name": "Operator",
            "password": "test-only-operator-password",
            "role": "operator",
        },
    ).json()

    operator = TestClient(create_app(container))
    assert login(operator, "operator", "test-only-operator-password").status_code == 200
    assert operator.get("/api/v1/tasks").status_code == 200
    assert admin.patch(f"/api/v1/users/{user['id']}", json={"status": "disabled"}).status_code == 200

    revoked = operator.get("/api/v1/tasks")
    assert revoked.status_code == 401


def test_local_users_and_sessions_survive_sqlite_restart(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'auth.db'}"
    settings = local_settings(database_url=database_url)
    first = AppContainer(persistent=True, database_url=database_url, settings=settings)
    first_client = TestClient(create_app(first))
    assert login(first_client).status_code == 200
    cookie = first_client.cookies.get(settings.auth_cookie_name)
    assert cookie

    second = AppContainer(persistent=True, database_url=database_url, settings=settings)
    second_client = TestClient(create_app(second))
    second_client.cookies.set(settings.auth_cookie_name, cookie)

    assert second_client.get("/api/v1/auth/me").status_code == 200
