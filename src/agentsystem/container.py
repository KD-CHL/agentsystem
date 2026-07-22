from __future__ import annotations

from functools import lru_cache

from agentsystem.agents import AgentRuntime
from agentsystem.auth import AuthService
from agentsystem.capabilities import CapabilityRegistry
from agentsystem.collaboration import CollaborationRuleEngine
from agentsystem.config import Settings, get_settings
from agentsystem.credentials import CredentialService
from agentsystem.github_adapter import GitHubEnterpriseAdapter
from agentsystem.model_gateway import ModelGateway
from agentsystem.policy import SecurityPolicy
from agentsystem.persistence import SQLiteStore
from agentsystem.store import InMemoryStore
from agentsystem.tools import ToolExecutor
from agentsystem.tracing import TraceRecorder
from agentsystem.workspace import WorkspaceService
from agentsystem.workflow import WorkflowService
from agentsystem.worker import DurableWorkflowWorker


class AppContainer:
    def __init__(
        self,
        *,
        persistent: bool = False,
        database_url: str | None = None,
        settings: Settings | None = None,
    ) -> None:
        self.settings = settings or get_settings()
        self.store = (
            SQLiteStore(database_url or self.settings.database_url)
            if persistent
            else InMemoryStore()
        )
        self.policy = SecurityPolicy()
        self.collaboration_rules = CollaborationRuleEngine()
        self.trace = TraceRecorder(self.store)
        self.auth = AuthService(self.store, self.settings)
        self.credentials = CredentialService(self.store)
        self.capabilities = CapabilityRegistry(self.store, self.credentials, self.settings)
        self.model_gateway = ModelGateway(
            self.settings,
            self.store,
            self.credentials,
            capabilities=self.capabilities,
        )
        self.tools = ToolExecutor(self.store, self.policy, self.settings.workspace_dir)
        self.github = GitHubEnterpriseAdapter(self.settings)
        allowed_roots = [
            item.strip()
            for item in self.settings.allowed_project_roots.replace(",", ":").split(":")
            if item.strip()
        ]
        self.workspace_service = WorkspaceService(self.store, allowed_roots=allowed_roots)
        self.runtime = AgentRuntime(
            self.model_gateway,
            self.tools,
            self.store,
            self.trace,
            self.policy,
            self.github,
        )
        self.workflow = WorkflowService(
            self.store,
            self.runtime,
            self.policy,
            self.trace,
            rules=self.collaboration_rules,
            max_fix_attempts=self.settings.max_fix_attempts,
        )
        self.worker = (
            DurableWorkflowWorker(
                self.store,
                self.workflow,
                poll_interval_seconds=self.settings.workflow_poll_interval_seconds,
                lease_seconds=self.settings.workflow_lease_seconds,
            )
            if persistent
            else None
        )

    def start_background_services(self) -> None:
        if self.worker:
            self.worker.start()

    def stop_background_services(self) -> None:
        if self.worker:
            self.worker.stop()


@lru_cache
def get_container() -> AppContainer:
    return AppContainer(persistent=True)
