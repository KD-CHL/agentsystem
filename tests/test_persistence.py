from pathlib import Path
from time import sleep

from fastapi.testclient import TestClient
import pytest

from agentsystem.api import create_app
from agentsystem.container import AppContainer


def test_sqlite_worker_persists_and_resumes_task(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'agentsystem.db'}"
    first = AppContainer(persistent=True, database_url=database_url)

    with TestClient(create_app(first)) as client:
        response = client.post(
            "/api/v1/tasks",
            json={
                "repo_id": "local/persistent-demo",
                "prompt": "Verify durable simulated workflow",
                "approval_policy": "manual_plan",
            },
        )
        assert response.status_code == 202
        task_id = response.json()["task"]["id"]
        for _ in range(30):
            payload = client.get(f"/api/v1/tasks/{task_id}").json()
            if payload["task"]["status"] == "awaiting_approval":
                break
            sleep(0.05)
        assert payload["task"]["status"] == "awaiting_approval"

    second = AppContainer(persistent=True, database_url=database_url)
    restored = second.workflow.get_task(task_id)
    assert restored.task.status == "awaiting_approval"
    assert restored.runs[-1].context_version == 3
    assert restored.artifacts


def test_v1_accepts_live_agent_configuration_and_fails_closed_without_credential() -> None:
    client = TestClient(create_app(AppContainer()))

    response = client.put(
        "/api/v1/agents/coding/configuration",
        json={
            "provider_id": "openai",
            "model": "gpt-example",
            "call_mode": "live",
            "timeout_seconds": 60,
        },
    )

    assert response.status_code == 200
    assert response.json()["call_mode"] == "live"
    assert response.json()["network_enabled"] is True

    validation = client.post("/api/v1/agents/coding/validate")
    assert validation.status_code == 200
    assert validation.json()["valid"] is False
    assert validation.json()["network_attempted"] is False
    assert "credential" in validation.json()["message"].lower()


def test_credential_api_keeps_plaintext_out_of_responses(monkeypatch: pytest.MonkeyPatch) -> None:
    keychain: dict[tuple[str, str], str] = {}

    monkeypatch.setattr(
        "agentsystem.credentials.keyring.set_password",
        lambda service, account, secret: keychain.__setitem__((service, account), secret),
    )
    monkeypatch.setattr(
        "agentsystem.credentials.keyring.get_password",
        lambda service, account: keychain.get((service, account)),
    )
    monkeypatch.setattr(
        "agentsystem.credentials.keyring.delete_password",
        lambda service, account: keychain.pop((service, account), None),
    )
    client = TestClient(create_app(AppContainer()))
    secret = "test-only-provider-key"

    created = client.post("/api/v1/credentials", json={"name": "Test provider", "secret": secret})

    assert created.status_code == 201
    credential_id = created.json()["id"]
    assert secret not in created.text
    assert secret not in client.get("/api/v1/credentials").text
    assert client.get(f"/api/v1/credentials/{credential_id}/exists").json()["available"] is True
    assert client.delete(f"/api/v1/credentials/{credential_id}").status_code == 200
    assert not keychain
