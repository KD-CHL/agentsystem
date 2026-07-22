from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shlex
from time import perf_counter

from agentsystem.domain import (
    AgentName,
    AgentRunRecord,
    ArtifactRecord,
    TaskRecord,
    ToolName,
)
from agentsystem.github_adapter import GitHubEnterpriseAdapter
from agentsystem.model_gateway import ModelGateway
from agentsystem.policy import SecurityPolicy
from agentsystem.store import InMemoryStore
from agentsystem.tools import ToolExecutor
from agentsystem.tracing import TraceRecorder


@dataclass
class AgentResult:
    summary: str
    handoff_to: AgentName | None = None
    artifacts: list[ArtifactRecord] | None = None
    data: dict[str, object] | None = None


class BaseAgent:
    name: AgentName

    def __init__(
        self,
        model_gateway: ModelGateway,
        tools: ToolExecutor,
        store: InMemoryStore,
        trace: TraceRecorder,
    ) -> None:
        self.model_gateway = model_gateway
        self.tools = tools
        self.store = store
        self.trace = trace

    def run(self, task: TaskRecord, context: dict[str, object]) -> AgentResult:
        started = perf_counter()
        model_profile = self.model_gateway.profile_for(self.name)
        run = self.store.add_agent_run(
            AgentRunRecord(
                task_id=task.id,
                trace_id=task.trace_id,
                run_id=task.run_id,
                agent_name=self.name,
                input_summary=str(context)[:500],
            )
        )
        self.trace.event(
            task,
            "agent.started",
            self.name,
            {
                "context": context,
                "capabilities": (
                    self.model_gateway.capabilities.trace_manifest(task.tenant_id, self.name)
                    if self.model_gateway.capabilities
                    else {"skills": [], "mcp_servers": []}
                ),
                "model": {
                    "provider": model_profile.provider,
                    "model": model_profile.model,
                    "api_key_env": model_profile.api_key_env,
                    "api_key_present": model_profile.api_key_present,
                    "simulated": model_profile.call_mode.value == "simulated",
                },
            },
        )
        try:
            result = self._run(task, context)
            run.output_summary = result.summary
            run.handoff_to = result.handoff_to
            run.latency_ms = int((perf_counter() - started) * 1000)
            from agentsystem.domain import utcnow

            run.completed_at = utcnow()
            self.store.update_agent_run(run)
            self.trace.event(
                task,
                "agent.completed",
                self.name,
                {"summary": result.summary, "handoff_to": result.handoff_to},
            )
            return result
        except Exception as exc:
            run.output_summary = f"failed: {exc}"
            run.latency_ms = int((perf_counter() - started) * 1000)
            from agentsystem.domain import utcnow

            run.completed_at = utcnow()
            self.store.update_agent_run(run)
            self.trace.event(task, "agent.failed", self.name, {"error": str(exc)})
            raise

    def _run(self, task: TaskRecord, context: dict[str, object]) -> AgentResult:
        raise NotImplementedError


class OrchestratorAgent(BaseAgent):
    name = AgentName.ORCHESTRATOR

    def _run(self, task: TaskRecord, context: dict[str, object]) -> AgentResult:
        response = self.model_gateway.complete(
            task,
            self.name,
            "orchestration",
            f"Classify and route task: {task.prompt}",
        )
        return AgentResult(
            summary=(
                f"Task classified as code-change workflow by {response.provider}/{response.model}. "
                f"{response.text}"
            ),
            handoff_to=AgentName.REPO_CONTEXT,
            data={"workflow": "code_change"},
        )


class RepoContextAgent(BaseAgent):
    name = AgentName.REPO_CONTEXT

    def _run(self, task: TaskRecord, context: dict[str, object]) -> AgentResult:
        task_workspace = self.tools.prepare_workspace(task)
        response = self.model_gateway.complete(
            task,
            self.name,
            "repo_context",
            f"Prepare repository context for {task.repo_id}@{task.base_branch}",
        )
        self.tools.execute(
            task,
            self.name,
            ToolName.CODE_SEARCH,
            "build repository context",
        )
        workspace_summary = self._workspace_context(task.workspace_path, task_workspace)
        summary = (
            f"Repository context prepared for {task.repo_id}@{task.base_branch}. "
            f"Model profile: {response.provider}/{response.model}.\n\n"
            f"{workspace_summary}\n\nModel analysis:\n{response.text}"
        )
        artifact = self.store.add_artifact(
            ArtifactRecord(
                task_id=task.id,
                run_id=task.run_id,
                kind="repo_context",
                name="repo-context.md",
                content=summary,
            )
        )
        return AgentResult(
            summary=summary,
            handoff_to=AgentName.PLANNING,
            artifacts=[artifact],
            data={"likely_files": self._likely_files(str(task_workspace)), "base_branch": task.base_branch},
        )

    @staticmethod
    def _workspace_context(source_path: str | None, task_workspace: Path) -> str:
        if not source_path:
            return "No local workspace bound yet. Use the console project picker to attach one."
        root = task_workspace
        if not root.exists() or not root.is_dir():
            return f"Task workspace is unavailable: {task_workspace}"
        files = RepoContextAgent._likely_files(str(task_workspace), limit=40)
        listing = "\n".join(f"- {path}" for path in files) if files else "- No source files found"
        return (
            f"Local workspace source: {source_path}\n"
            f"Isolated task workspace: {task_workspace}\n"
            f"Sample files:\n{listing}"
        )

    @staticmethod
    def _likely_files(workspace_path: str | None, limit: int = 24) -> list[str]:
        if not workspace_path:
            return ["src/", "tests/"]
        root = Path(workspace_path)
        ignored = {".git", ".venv", "__pycache__", "node_modules", ".pytest_cache"}
        paths: list[str] = []
        for path in root.rglob("*"):
            rel_parts = path.relative_to(root).parts
            if any(part in ignored for part in rel_parts):
                continue
            if path.is_file():
                paths.append(path.relative_to(root).as_posix())
            if len(paths) >= limit:
                break
        return paths or ["src/", "tests/"]


class PlanningAgent(BaseAgent):
    name = AgentName.PLANNING

    def _run(self, task: TaskRecord, context: dict[str, object]) -> AgentResult:
        response = self.model_gateway.complete(task, self.name, "planning", task.prompt)
        artifact = self.store.add_artifact(
            ArtifactRecord(
                task_id=task.id,
                run_id=task.run_id,
                kind="plan",
                name="implementation-plan.md",
                content=response.text,
            )
        )
        return AgentResult(
            summary="Implementation plan generated",
            handoff_to=AgentName.CODING,
            artifacts=[artifact],
            data={"plan": response.text, "expected_paths": ["src/", "tests/"]},
        )


class CodingAgent(BaseAgent):
    name = AgentName.CODING

    def _run(self, task: TaskRecord, context: dict[str, object]) -> AgentResult:
        branch = f"ai/{task.id}"
        task.branch_name = branch
        self.store.update_task(task)
        response = self.model_gateway.complete(task, self.name, "coding", str(context))
        patch = self._patch_for_task(task) if response.simulated else response.text
        changed_paths = self._changed_paths(patch) or ["src/example.py", "tests/test_example.py"]
        artifact = self.store.add_artifact(
            ArtifactRecord(
                task_id=task.id,
                run_id=task.run_id,
                kind="patch",
                name="proposed.patch",
                content=patch,
            )
        )
        self.tools.execute(task, self.name, ToolName.GIT_DIFF, "capture proposed diff")
        return AgentResult(
            summary=f"Patch artifact generated on branch {branch}",
            handoff_to=AgentName.TEST,
            artifacts=[artifact],
            data={"branch_name": branch, "changed_paths": changed_paths},
        )

    @staticmethod
    def _patch_for_task(task: TaskRecord) -> str:
        return (
            f"diff --git a/src/example.py b/src/example.py\n"
            f"+# Proposed change for task {task.id}\n"
            f"+# Prompt: {task.prompt[:120]}\n"
            "diff --git a/tests/test_example.py b/tests/test_example.py\n"
            "+def test_proposed_change_contract():\n"
            "+    assert True\n"
        )

    @staticmethod
    def _changed_paths(patch: str) -> list[str]:
        paths: list[str] = []
        for line in patch.splitlines():
            if not line.startswith("diff --git "):
                continue
            try:
                parts = shlex.split(line)
            except ValueError:
                continue
            if len(parts) < 4 or not parts[3].startswith("b/"):
                continue
            path = parts[3][2:]
            if path and path not in paths:
                paths.append(path)
        return paths


class TestAgent(BaseAgent):
    name = AgentName.TEST

    def _run(self, task: TaskRecord, context: dict[str, object]) -> AgentResult:
        response = self.model_gateway.complete(
            task,
            self.name,
            "test_strategy",
            f"Choose test gates for changed paths: {context.get('changed_paths', [])}",
        )
        result = self.tools.execute(
            task,
            self.name,
            ToolName.RUN_TESTS,
            "run deterministic test gate",
        )
        artifact = self.store.add_artifact(
            ArtifactRecord(
                task_id=task.id,
                run_id=task.run_id,
                kind="test_report",
                name="test-report.txt",
                content=f"Model test strategy:\n{response.text}\n\nExecution:\n{result.output}",
            )
        )
        if result.exit_code != 0:
            return AgentResult(
                summary=f"Tests failed: {result.output}",
                handoff_to=AgentName.CODING,
                artifacts=[artifact],
                data={"tests_passed": False},
            )
        return AgentResult(
            summary="Tests passed",
            handoff_to=AgentName.SECURITY,
            artifacts=[artifact],
            data={"tests_passed": True},
        )


class SecurityAgent(BaseAgent):
    name = AgentName.SECURITY

    def __init__(
        self,
        model_gateway: ModelGateway,
        tools: ToolExecutor,
        store: InMemoryStore,
        trace: TraceRecorder,
        policy: SecurityPolicy,
    ) -> None:
        super().__init__(model_gateway, tools, store, trace)
        self.policy = policy

    def _run(self, task: TaskRecord, context: dict[str, object]) -> AgentResult:
        response = self.model_gateway.complete(
            task,
            self.name,
            "security_review",
            f"Assess security policy for changed paths: {context.get('changed_paths', [])}",
        )
        patch_content = "\n".join(
            artifact.content
            for artifact in self.store.task_view(task.id).artifacts
            if artifact.kind == "patch"
        )
        scan_target = f"{task.prompt}\n{context}\n{patch_content}"
        result = self.tools.execute(
            task,
            self.name,
            ToolName.SECRET_SCAN,
            "scan task, context, and patch for secrets",
            text=scan_target,
        )
        if result.exit_code != 0:
            raise ValueError(result.output)
        paths = [str(path) for path in context.get("changed_paths", [])]
        decision = self.policy.check_changed_paths(paths, task.approval_policy)
        return AgentResult(
            summary=(
                f"{decision.reason}. Model profile: {response.provider}/{response.model}. "
                f"Assessment: {response.text}"
            ),
            handoff_to=AgentName.REVIEW,
            data={
                "security_passed": decision.allowed,
                "requires_approval": decision.requires_approval,
                "approval_type": decision.approval_type,
                "changed_paths": paths,
            },
        )


class ReviewAgent(BaseAgent):
    name = AgentName.REVIEW

    def _run(self, task: TaskRecord, context: dict[str, object]) -> AgentResult:
        response = self.model_gateway.complete(task, self.name, "review", str(context))
        artifact = self.store.add_artifact(
            ArtifactRecord(
                task_id=task.id,
                run_id=task.run_id,
                kind="review_report",
                name="review-report.md",
                content=response.text,
            )
        )
        return AgentResult(
            summary="Review gate passed",
            handoff_to=AgentName.PR,
            artifacts=[artifact],
            data={"review_passed": True, "review": response.text},
        )


class PRAgent(BaseAgent):
    name = AgentName.PR

    def __init__(
        self,
        model_gateway: ModelGateway,
        tools: ToolExecutor,
        store: InMemoryStore,
        trace: TraceRecorder,
        github: GitHubEnterpriseAdapter,
    ) -> None:
        super().__init__(model_gateway, tools, store, trace)
        self.github = github

    def _run(self, task: TaskRecord, context: dict[str, object]) -> AgentResult:
        response = self.model_gateway.complete(
            task,
            self.name,
            "pr_summary",
            f"Draft pull request summary for {task.prompt}",
        )
        self.tools.execute(task, self.name, ToolName.CREATE_PR, "create draft pull request")
        title = f"[AI] {task.prompt[:72]}"
        body = (
            f"{response.text}\n\n"
            "## AgentSystem validation\n"
            f"- PR summary generated using {response.provider}/{response.model}.\n"
            "- Includes implementation plan, patch, test report, security gate, and review gate.\n\n"
            f"Trace ID: `{task.trace_id}`\n"
        )
        draft = self.github.create_draft_pr(
            task,
            title=title,
            body=body,
            head_branch=task.branch_name or f"ai/{task.id}",
        )
        task.pr_url = draft.url
        self.store.update_task(task)
        artifact = self.store.add_artifact(
            ArtifactRecord(
                task_id=task.id,
                run_id=task.run_id,
                kind="pr_description",
                name="draft-pr.md",
                content=f"# {draft.title}\n\n{draft.body}\n\n{draft.url}\n",
            )
        )
        return AgentResult(
            summary=f"Draft PR created: {draft.url}",
            artifacts=[artifact],
            data={"pr_url": draft.url},
        )


class AgentRuntime:
    def __init__(
        self,
        model_gateway: ModelGateway,
        tools: ToolExecutor,
        store: InMemoryStore,
        trace: TraceRecorder,
        policy: SecurityPolicy,
        github: GitHubEnterpriseAdapter,
    ) -> None:
        self.tools = tools
        self.agents: dict[AgentName, BaseAgent] = {
            AgentName.ORCHESTRATOR: OrchestratorAgent(model_gateway, tools, store, trace),
            AgentName.REPO_CONTEXT: RepoContextAgent(model_gateway, tools, store, trace),
            AgentName.PLANNING: PlanningAgent(model_gateway, tools, store, trace),
            AgentName.CODING: CodingAgent(model_gateway, tools, store, trace),
            AgentName.TEST: TestAgent(model_gateway, tools, store, trace),
            AgentName.SECURITY: SecurityAgent(model_gateway, tools, store, trace, policy),
            AgentName.REVIEW: ReviewAgent(model_gateway, tools, store, trace),
            AgentName.PR: PRAgent(model_gateway, tools, store, trace, github),
        }

    def run(self, agent_name: AgentName, task: TaskRecord, context: dict[str, object]) -> AgentResult:
        return self.agents[agent_name].run(task, context)
