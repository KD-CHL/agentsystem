from __future__ import annotations

from dataclasses import dataclass

from agentsystem.domain import ApiFormat


@dataclass(frozen=True)
class ProviderDefinition:
    id: str
    display_name: str
    description: str
    default_api_format: ApiFormat
    supported_api_formats: tuple[ApiFormat, ...]
    default_base_url: str | None
    requires_base_url: bool
    requires_credential: bool
    default_model: str
    models: tuple[str, ...]
    supports_model_discovery: bool = True

    def public_payload(self) -> dict[str, object]:
        return {
            "id": self.id,
            "display_name": self.display_name,
            "description": self.description,
            "default_api_format": self.default_api_format,
            "supported_api_formats": self.supported_api_formats,
            "default_base_url": self.default_base_url,
            "requires_base_url": self.requires_base_url,
            "requires_credential": self.requires_credential,
            "default_model": self.default_model,
            "models": self.models,
            "supports_model_discovery": self.supports_model_discovery,
        }


PROVIDER_DEFINITIONS: tuple[ProviderDefinition, ...] = (
    ProviderDefinition(
        id="simulated",
        display_name="Simulated",
        description="Deterministic local responses without network access.",
        default_api_format=ApiFormat.RESPONSES,
        supported_api_formats=(ApiFormat.RESPONSES,),
        default_base_url=None,
        requires_base_url=False,
        requires_credential=False,
        default_model="deterministic-local",
        models=("deterministic-local",),
        supports_model_discovery=False,
    ),
    ProviderDefinition(
        id="openai",
        display_name="OpenAI",
        description="Official OpenAI Responses API.",
        default_api_format=ApiFormat.RESPONSES,
        supported_api_formats=(ApiFormat.RESPONSES, ApiFormat.CHAT_COMPLETIONS),
        default_base_url="https://api.openai.com/v1",
        requires_base_url=False,
        requires_credential=True,
        default_model="gpt-5.6-terra",
        models=("gpt-5.6-sol", "gpt-5.6-terra", "gpt-5.6-luna"),
    ),
    ProviderDefinition(
        id="deepseek",
        display_name="DeepSeek",
        description="DeepSeek's OpenAI-compatible Chat Completions API.",
        default_api_format=ApiFormat.CHAT_COMPLETIONS,
        supported_api_formats=(ApiFormat.CHAT_COMPLETIONS,),
        default_base_url="https://api.deepseek.com",
        requires_base_url=False,
        requires_credential=True,
        default_model="deepseek-v4-flash",
        models=("deepseek-v4-flash", "deepseek-v4-pro"),
    ),
    ProviderDefinition(
        id="qwen",
        display_name="Qwen / DashScope",
        description="Alibaba Model Studio's OpenAI-compatible endpoint.",
        default_api_format=ApiFormat.CHAT_COMPLETIONS,
        supported_api_formats=(ApiFormat.CHAT_COMPLETIONS,),
        default_base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        requires_base_url=False,
        requires_credential=True,
        default_model="qwen-plus",
        models=("qwen-plus",),
    ),
    ProviderDefinition(
        id="local-vllm",
        display_name="Local vLLM",
        description="Local OpenAI-compatible Chat Completions endpoint.",
        default_api_format=ApiFormat.CHAT_COMPLETIONS,
        supported_api_formats=(ApiFormat.CHAT_COMPLETIONS,),
        default_base_url="http://127.0.0.1:8001/v1",
        requires_base_url=True,
        requires_credential=False,
        default_model="local-model",
        models=(),
    ),
    ProviderDefinition(
        id="openai-compatible",
        display_name="Custom OpenAI-compatible",
        description="Custom gateway using Responses or Chat Completions.",
        default_api_format=ApiFormat.CHAT_COMPLETIONS,
        supported_api_formats=(ApiFormat.RESPONSES, ApiFormat.CHAT_COMPLETIONS),
        default_base_url=None,
        requires_base_url=True,
        requires_credential=True,
        default_model="custom-model",
        models=(),
    ),
)

PROVIDERS_BY_ID = {provider.id: provider for provider in PROVIDER_DEFINITIONS}


def provider_definition(provider_id: str) -> ProviderDefinition:
    normalized = provider_id.strip().lower()
    provider = PROVIDERS_BY_ID.get(normalized)
    if provider is not None:
        return provider
    # Existing installations may contain a vendor-specific provider id. Treat
    # it as an OpenAI-compatible gateway without rewriting stored config.
    return ProviderDefinition(
        id=normalized,
        display_name=provider_id.strip(),
        description="Custom OpenAI-compatible provider.",
        default_api_format=ApiFormat.CHAT_COMPLETIONS,
        supported_api_formats=(ApiFormat.RESPONSES, ApiFormat.CHAT_COMPLETIONS),
        default_base_url=None,
        requires_base_url=True,
        requires_credential=True,
        default_model="custom-model",
        models=(),
    )
