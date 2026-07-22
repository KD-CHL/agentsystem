from __future__ import annotations

from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
from types import SimpleNamespace

import pytest

from agentsystem.container import AppContainer
from agentsystem.domain import (
    AgentConfigurationRecord,
    AgentName,
    ApiFormat,
    ApprovalPolicy,
    CallMode,
    Priority,
    TaskRecord,
)
from agentsystem.model_gateway import ModelGatewayError


def task() -> TaskRecord:
    return TaskRecord(
        tenant_id="default",
        repo_id="local/test",
        base_branch="main",
        prompt="Review the retry implementation",
        approval_policy=ApprovalPolicy.AUTO,
        priority=Priority.NORMAL,
    )


class FakeResponses:
    def __init__(self) -> None:
        self.request = None
        self.output_text = "A focused live review."

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(
            output_text=self.output_text,
            usage=SimpleNamespace(input_tokens=17, output_tokens=6),
            _request_id="req_test_responses",
        )


class FakeClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()
        self.models = SimpleNamespace(
            list=lambda: SimpleNamespace(data=[SimpleNamespace(id="gpt-5.6-terra")])
        )


def test_live_responses_call_records_usage_and_request_id(monkeypatch: pytest.MonkeyPatch) -> None:
    container = AppContainer()
    fake = FakeClient()
    container.model_gateway.client_factory = lambda profile, api_key: fake
    monkeypatch.setenv("TEST_OPENAI_KEY", "test-only-key")
    container.store.set_agent_configuration(
        AgentConfigurationRecord(
            agent_name=AgentName.REVIEW,
            provider_id="openai",
            model="gpt-5.6-terra",
            api_key_env="TEST_OPENAI_KEY",
            api_format=ApiFormat.RESPONSES,
            call_mode=CallMode.LIVE,
        )
    )

    result = container.model_gateway.complete(task(), AgentName.REVIEW, "review", "Review this diff")

    assert result.simulated is False
    assert result.text == "A focused live review."
    assert result.prompt_tokens == 17
    assert result.completion_tokens == 6
    assert fake.responses.request["model"] == "gpt-5.6-terra"
    assert "untrusted data" in fake.responses.request["instructions"]
    call = list(container.store.model_calls.values())[-1]
    assert call.provider_request_id == "req_test_responses"
    assert call.api_format == ApiFormat.RESPONSES


def test_live_call_without_credential_fails_closed_and_is_audited() -> None:
    container = AppContainer()
    container.store.set_agent_configuration(
        AgentConfigurationRecord(
            agent_name=AgentName.PLANNING,
            provider_id="openai",
            model="gpt-5.6-terra",
            api_format=ApiFormat.RESPONSES,
            call_mode=CallMode.LIVE,
        )
    )

    with pytest.raises(ModelGatewayError) as error:
        container.model_gateway.complete(task(), AgentName.PLANNING, "planning", "Plan this change")

    assert error.value.code == "MODEL_CREDENTIAL_MISSING"
    call = list(container.store.model_calls.values())[-1]
    assert call.error_message.startswith("MODEL_CREDENTIAL_MISSING")


def test_live_coding_response_becomes_patch_artifact(monkeypatch: pytest.MonkeyPatch) -> None:
    container = AppContainer()
    fake = FakeClient()
    fake.responses.output_text = (
        "diff --git a/src/retry.py b/src/retry.py\n"
        "--- a/src/retry.py\n"
        "+++ b/src/retry.py\n"
        "@@ -1 +1 @@\n"
        "-RETRIES = 1\n"
        "+RETRIES = 2\n"
    )
    container.model_gateway.client_factory = lambda profile, api_key: fake
    monkeypatch.setenv("TEST_CODING_KEY", "test-only-key")
    container.store.set_agent_configuration(
        AgentConfigurationRecord(
            agent_name=AgentName.CODING,
            provider_id="openai",
            model="gpt-5.6-sol",
            api_key_env="TEST_CODING_KEY",
            api_format=ApiFormat.RESPONSES,
            call_mode=CallMode.LIVE,
        )
    )
    coding_task = task()
    container.store.create_task(coding_task)

    result = container.runtime.run(AgentName.CODING, coding_task, {"plan": "Adjust retry count"})

    assert result.artifacts is not None
    assert result.artifacts[0].content == fake.responses.output_text.strip()
    assert result.data is not None
    assert result.data["changed_paths"] == ["src/retry.py"]


class CompatibleHandler(BaseHTTPRequestHandler):
    requests: list[dict[str, object]] = []

    def do_GET(self) -> None:  # noqa: N802
        if self.path != "/v1/models":
            self.send_error(404)
            return
        self._json({"object": "list", "data": [{"id": "local-code-model", "object": "model"}]})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(length))
        self.requests.append(payload)
        self._json(
            {
                "id": "chatcmpl_local",
                "object": "chat.completion",
                "created": 1,
                "model": payload["model"],
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "Local provider response."},
                    }
                ],
                "usage": {"prompt_tokens": 11, "completion_tokens": 4, "total_tokens": 15},
            }
        )

    def _json(self, payload: dict[str, object]) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def test_openai_compatible_live_mode_uses_real_http_transport() -> None:
    CompatibleHandler.requests = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), CompatibleHandler)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        container = AppContainer()
        container.store.set_agent_configuration(
            AgentConfigurationRecord(
                agent_name=AgentName.CODING,
                provider_id="local-vllm",
                model="local-code-model",
                base_url=f"http://127.0.0.1:{server.server_port}/v1",
                api_format=ApiFormat.CHAT_COMPLETIONS,
                call_mode=CallMode.LIVE,
                timeout_seconds=5,
                max_output_tokens=256,
            )
        )

        validation = container.model_gateway.validate_configuration(AgentName.CODING)
        result = container.model_gateway.complete(task(), AgentName.CODING, "coding", "Describe a patch")

        assert validation.valid is True
        assert validation.network_attempted is True
        assert validation.models == ("local-code-model",)
        assert result.text == "Local provider response."
        assert result.simulated is False
        assert CompatibleHandler.requests[0]["model"] == "local-code-model"
        assert CompatibleHandler.requests[0]["max_tokens"] == 256
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)
