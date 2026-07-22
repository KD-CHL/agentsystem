from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import os

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from agentsystem.domain import AgentName, ApiFormat, CallMode
from agentsystem.providers import provider_definition


@dataclass(frozen=True)
class AgentModelConfig:
    agent_name: AgentName
    provider: str
    model: str
    api_key_env: str
    api_key_present: bool
    credential_ref: str | None = None
    base_url: str | None = None
    api_format: ApiFormat = ApiFormat.CHAT_COMPLETIONS
    calls_enabled: bool = False
    call_mode: CallMode = CallMode.SIMULATED
    timeout_seconds: int = 60
    max_output_tokens: int = 4096
    budget_limit: float | None = None
    version: int = 1


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", ".env.local"),
        env_prefix="AGENTSYSTEM_",
        extra="ignore",
    )

    env: str = "local"
    require_manual_approval: bool = True
    max_fix_attempts: int = Field(default=2, ge=0, le=5)
    artifact_dir: str = "data/artifacts"
    workspace_dir: str = "data/workspaces"
    database_url: str = "sqlite:///data/agentsystem.db"
    auth_mode: str = "dev"
    auth_cookie_name: str = "agentsystem_session"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    cors_origins: str = ""
    auth_session_ttl_hours: int = Field(default=12, ge=1, le=720)
    bootstrap_admin_username: str = "admin"
    bootstrap_admin_display_name: str = "Local Administrator"
    bootstrap_admin_password: SecretStr | None = None
    allowed_project_roots: str = ""
    workflow_poll_interval_seconds: float = Field(default=0.25, ge=0.05, le=10)
    workflow_lease_seconds: int = Field(default=60, ge=10, le=3600)

    mcp_network_enabled: bool = True
    mcp_allowed_hosts: str = "127.0.0.1,localhost,::1"
    mcp_stdio_enabled: bool = False
    mcp_stdio_allowed_commands: str = "uv,uvx,npx,node,python,python3"
    skill_allowed_roots: str = ""
    skill_max_bytes: int = Field(default=65_536, ge=1_024, le=1_048_576)
    skill_prompt_budget_chars: int = Field(default=24_000, ge=1_000, le=100_000)

    github_enterprise_url: str | None = None
    github_app_token: str | None = None

    model_gateway_base_url: str | None = None
    model_gateway_default_model: str = "private-code-model"
    model_gateway_calls_enabled: bool = True

    orchestrator_model_provider: str = "openai"
    orchestrator_model: str = "gpt-5.6-terra"
    orchestrator_api_key_env: str = "ORCHESTRATOR_AGENT_API_KEY"
    orchestrator_model_base_url: str | None = None

    repo_context_model_provider: str = "qwen"
    repo_context_model: str = "qwen-plus"
    repo_context_api_key_env: str = "REPO_CONTEXT_AGENT_API_KEY"
    repo_context_model_base_url: str | None = None

    planning_model_provider: str = "openai"
    planning_model: str = "gpt-5.6-terra"
    planning_api_key_env: str = "PLANNING_AGENT_API_KEY"
    planning_model_base_url: str | None = None

    coding_model_provider: str = "openai"
    coding_model: str = "gpt-5.6-sol"
    coding_api_key_env: str = "CODING_AGENT_API_KEY"
    coding_model_base_url: str | None = None

    test_model_provider: str = "deepseek"
    test_model: str = "deepseek-v4-flash"
    test_api_key_env: str = "TEST_AGENT_API_KEY"
    test_model_base_url: str | None = None

    security_model_provider: str = "local-vllm"
    security_model: str = "local-model"
    security_api_key_env: str = "SECURITY_AGENT_API_KEY"
    security_model_base_url: str | None = None

    review_model_provider: str = "openai"
    review_model: str = "gpt-5.6-terra"
    review_api_key_env: str = "REVIEW_AGENT_API_KEY"
    review_model_base_url: str | None = None

    pr_model_provider: str = "openai"
    pr_model: str = "gpt-5.6-luna"
    pr_api_key_env: str = "PR_AGENT_API_KEY"
    pr_model_base_url: str | None = None

    def agent_model_config(self, agent_name: AgentName) -> AgentModelConfig:
        prefix = agent_name.value
        provider = getattr(self, f"{prefix}_model_provider")
        model = getattr(self, f"{prefix}_model")
        api_key_env = getattr(self, f"{prefix}_api_key_env")
        base_url = getattr(self, f"{prefix}_model_base_url") or self.model_gateway_base_url
        provider_config = provider_definition(provider)
        return AgentModelConfig(
            agent_name=agent_name,
            provider=provider,
            model=model,
            api_key_env=api_key_env,
            api_key_present=bool(os.getenv(api_key_env)),
            base_url=base_url,
            api_format=provider_config.default_api_format,
            calls_enabled=False,
            call_mode=CallMode.SIMULATED,
        )

    def agent_model_configs(self) -> list[AgentModelConfig]:
        return [self.agent_model_config(agent_name) for agent_name in AgentName]


@lru_cache
def get_settings() -> Settings:
    return Settings()
