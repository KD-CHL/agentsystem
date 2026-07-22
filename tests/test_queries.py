from fastapi.testclient import TestClient

from agentsystem.api import create_app
from agentsystem.container import AppContainer


def create_task(client: TestClient, prompt: str, priority: str = "normal"):
    response = client.post(
        "/api/v1/tasks",
        json={
            "repo_id": "local/query-demo",
            "prompt": prompt,
            "priority": priority,
            "approval_policy": "manual_plan",
        },
    )
    assert response.status_code == 202
    return response.json()["task"]


def test_task_query_filters_and_total_header() -> None:
    client = TestClient(create_app(AppContainer()))
    create_task(client, "Fix checkout retry", "high")
    create_task(client, "Document payment flow", "low")

    response = client.get(
        "/api/v1/tasks",
        params=[("status", "awaiting_approval"), ("priority", "high"), ("q", "checkout")],
    )

    assert response.status_code == 200
    assert response.headers["X-Total-Count"] == "1"
    assert [item["prompt"] for item in response.json()] == ["Fix checkout retry"]


def test_operations_summary_and_audit_query_are_server_backed() -> None:
    client = TestClient(create_app(AppContainer()))
    create_task(client, "Audit this workflow")

    summary = client.get("/api/v1/operations/summary")
    audit = client.get("/api/v1/audit-logs", params={"action": "task.created.by_user"})

    assert summary.status_code == 200
    assert summary.json()["total_tasks"] == 1
    assert summary.json()["pending_approvals"] == 1
    assert summary.json()["status_counts"]["awaiting_approval"] == 1
    assert audit.status_code == 200
    assert audit.headers["X-Total-Count"] == "1"
    assert audit.json()[0]["action"] == "task.created.by_user"
