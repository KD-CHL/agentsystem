from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient

from agentsystem.api import create_app
from agentsystem.config import Settings
from agentsystem.container import AppContainer
from agentsystem.domain import (
    AgentCapabilitiesUpdate,
    AgentConfigurationRecord,
    AgentName,
    ApiFormat,
    ApprovalPolicy,
    CallMode,
    McpToolDescriptor,
    McpToolInvokeResult,
    Priority,
    SkillImport,
    TaskRecord,
)


def test_skill_import_binding_and_runtime_manifest(tmp_path: Path) -> None:
    skill_dir = tmp_path / "focused-review"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """---
name: focused-review
description: Review only concrete regressions.
version: 1.0
---
Always cite the affected file and explain the regression path.
""",
        encoding="utf-8",
    )
    settings = Settings(skill_allowed_roots=str(tmp_path))
    container = AppContainer(settings=settings)
    client = TestClient(create_app(container))

    imported = client.post("/api/v1/skills", json={"path": str(skill_dir)})

    assert imported.status_code == 201
    skill = imported.json()
    assert skill["name"] == "focused-review"
    assert skill["content_hash"]
    bound = client.put(
        "/api/v1/agents/review/capabilities",
        json={"mcp_server_ids": [], "skill_ids": [skill["id"]]},
    )
    assert bound.status_code == 200
    assert [item["id"] for item in bound.json()["skills"]] == [skill["id"]]
    prompt_context = container.capabilities.prompt_context("default", "review")
    assert "Always cite the affected file" in prompt_context
    assert container.capabilities.trace_manifest("default", "review")["skills"][0]["name"] == "focused-review"


def test_skill_import_rejects_paths_outside_policy(tmp_path: Path) -> None:
    allowed = tmp_path / "allowed"
    allowed.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text("# Not allowed\n", encoding="utf-8")
    container = AppContainer(settings=Settings(skill_allowed_roots=str(allowed)))
    client = TestClient(create_app(container))

    response = client.post("/api/v1/skills", json={"path": str(outside)})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "SKILL_PATH_BLOCKED"


def test_mcp_configuration_is_persisted_and_policy_blocks_unlisted_host(tmp_path: Path) -> None:
    database_url = f"sqlite:///{tmp_path / 'capabilities.db'}"
    first = AppContainer(persistent=True, database_url=database_url)
    client = TestClient(create_app(first))
    created = client.post(
        "/api/v1/mcp-servers",
        json={
            "name": "Internal docs",
            "transport": "streamable_http",
            "url": "https://unlisted.example.test/mcp",
            "enabled": True,
        },
    )

    assert created.status_code == 201
    server_id = created.json()["id"]
    validation = client.post(f"/api/v1/mcp-servers/{server_id}/validate")
    assert validation.status_code == 200
    assert validation.json()["status"] == "blocked"
    assert validation.json()["network_attempted"] is False

    second = AppContainer(persistent=True, database_url=database_url)
    restored = second.capabilities.list_mcp_servers("default")
    assert restored[0].id == server_id
    assert restored[0].status == "blocked"


def test_mcp_validation_catalog_and_agent_binding(monkeypatch, tmp_path: Path) -> None:
    container = AppContainer(
        settings=Settings(mcp_allowed_hosts="localhost", skill_allowed_roots=str(tmp_path))
    )
    client = TestClient(create_app(container))
    created = client.post(
        "/api/v1/mcp-servers",
        json={
            "name": "Local tools",
            "transport": "streamable_http",
            "url": "http://localhost:9123/mcp",
            "enabled": True,
            "tool_allowlist": ["search_code"],
        },
    ).json()

    async def fake_discover(_server):
        return [McpToolDescriptor(name="search_code", description="Search repository")], True

    monkeypatch.setattr(container.capabilities, "_discover_tools", fake_discover)
    validation = client.post(f"/api/v1/mcp-servers/{created['id']}/validate")
    assert validation.status_code == 200
    assert validation.json()["valid"] is True
    assert validation.json()["tools"][0]["name"] == "search_code"

    bound = client.put(
        "/api/v1/agents/repo_context/capabilities",
        json={"mcp_server_ids": [created["id"]], "skill_ids": []},
    )
    assert bound.status_code == 200
    manifest = container.capabilities.trace_manifest("default", "repo_context")
    assert manifest["mcp_servers"][0]["tool_count"] == 1

    async def fake_invoke(_server, tool_name, arguments):
        return McpToolInvokeResult(
            server_id=created["id"],
            tool_name=tool_name,
            output={"query": arguments["query"], "matches": 2},
        )

    monkeypatch.setattr(container.capabilities, "_invoke_tool", fake_invoke)
    invoked = client.post(
        f"/api/v1/mcp-servers/{created['id']}/tools/search_code/invoke",
        json={"arguments": {"query": "CapabilityRegistry"}},
    )
    assert invoked.status_code == 200
    assert invoked.json()["output"]["matches"] == 2


def test_bound_skill_is_added_to_live_agent_system_prompt(monkeypatch, tmp_path: Path) -> None:
    skill_dir = tmp_path / "minimal-patch"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "---\nname: minimal-patch\ndescription: Keep patches focused.\n---\n"
        "Never modify files outside the approved plan.\n",
        encoding="utf-8",
    )
    container = AppContainer(settings=Settings(skill_allowed_roots=str(tmp_path)))
    skill = container.capabilities.import_skill("default", SkillImport(path=str(skill_dir)))
    container.capabilities.replace_agent_capabilities(
        "default",
        AgentName.CODING,
        AgentCapabilitiesUpdate(skill_ids=[skill.id]),
    )
    container.store.set_agent_configuration(
        AgentConfigurationRecord(
            agent_name=AgentName.CODING,
            provider_id="openai",
            model="test-model",
            api_key_env="CAPABILITY_TEST_KEY",
            api_format=ApiFormat.RESPONSES,
            call_mode=CallMode.LIVE,
        )
    )
    monkeypatch.setenv("CAPABILITY_TEST_KEY", "test-only-key")
    captured: dict[str, object] = {}

    def create_response(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(
            output_text="Focused patch prepared.",
            usage=SimpleNamespace(input_tokens=10, output_tokens=3),
            _request_id="req_capability",
        )

    fake = SimpleNamespace(responses=SimpleNamespace(create=create_response))
    container.model_gateway.client_factory = lambda profile, api_key: fake
    task = TaskRecord(
        tenant_id="default",
        repo_id="local/test",
        base_branch="main",
        prompt="Prepare the patch",
        approval_policy=ApprovalPolicy.AUTO,
        priority=Priority.NORMAL,
    )
    container.model_gateway.complete(task, AgentName.CODING, "coding", "Prepare the patch")

    assert "Trusted configured skill: minimal-patch" in str(captured["instructions"])
    assert "Never modify files outside the approved plan" in str(captured["instructions"])
