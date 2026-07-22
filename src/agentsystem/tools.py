from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
import shutil
import subprocess

from agentsystem.domain import AgentName, TaskRecord, ToolCallRecord, ToolName
from agentsystem.policy import PolicyViolation, SecurityPolicy
from agentsystem.store import InMemoryStore


@dataclass(frozen=True)
class ToolResult:
    tool_name: ToolName
    exit_code: int
    output: str


class ToolExecutor:
    def __init__(self, store: InMemoryStore, policy: SecurityPolicy, workspace_root: str) -> None:
        self.store = store
        self.policy = policy
        self.workspace_root = Path(workspace_root)
        self.workspace_root.mkdir(parents=True, exist_ok=True)
        self.metadata_root = self.workspace_root / ".metadata"
        self.metadata_root.mkdir(parents=True, exist_ok=True)

    def execute(
        self,
        task: TaskRecord,
        agent_name: AgentName,
        tool_name: ToolName,
        input_summary: str,
        *,
        command: list[str] | None = None,
        text: str | None = None,
    ) -> ToolResult:
        permission = self.policy.check_tool_permission(agent_name, tool_name)
        if not permission.allowed:
            self.store.add_tool_call(
                ToolCallRecord(
                    task_id=task.id,
                    trace_id=task.trace_id,
                    run_id=task.run_id,
                    agent_name=agent_name,
                    tool_name=tool_name,
                    input_summary=input_summary,
                    allowed=False,
                    error_message=permission.reason,
                )
            )
            raise PolicyViolation(permission.reason)

        try:
            result = self._run_tool(task, tool_name, command=command, text=text)
            self.store.add_tool_call(
                ToolCallRecord(
                    task_id=task.id,
                    trace_id=task.trace_id,
                    run_id=task.run_id,
                    agent_name=agent_name,
                    tool_name=tool_name,
                    input_summary=input_summary,
                    allowed=True,
                    exit_code=result.exit_code,
                    output_summary=result.output[:500],
                )
            )
            return result
        except Exception as exc:
            self.store.add_tool_call(
                ToolCallRecord(
                    task_id=task.id,
                    trace_id=task.trace_id,
                    run_id=task.run_id,
                    agent_name=agent_name,
                    tool_name=tool_name,
                    input_summary=input_summary,
                    allowed=True,
                    exit_code=1,
                    error_message=str(exc),
                )
            )
            raise

    def _run_tool(
        self,
        task: TaskRecord,
        tool_name: ToolName,
        *,
        command: list[str] | None,
        text: str | None,
    ) -> ToolResult:
        workspace = self.prepare_workspace(task)

        if tool_name == ToolName.SECRET_SCAN:
            decision = self.policy.scan_for_secrets(text or "")
            return ToolResult(tool_name, 0 if decision.allowed else 1, decision.reason)

        if tool_name == ToolName.RUN_TESTS:
            safe_command = command or ["python", "-c", "print('deterministic test gate passed')"]
            decision = self.policy.check_command(safe_command)
            if not decision.allowed:
                return ToolResult(tool_name, 1, decision.reason)
            completed = subprocess.run(
                safe_command,
                cwd=workspace,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = (completed.stdout + completed.stderr).strip()
            return ToolResult(tool_name, completed.returncode, output)

        if tool_name == ToolName.CODE_SEARCH:
            files = self._source_files(workspace, limit=40)
            output = "\n".join(files) if files else "No source files found in the task workspace."
            return ToolResult(tool_name, 0, output)

        if tool_name == ToolName.GIT_STATUS:
            return self._git_command(tool_name, workspace, ["git", "status", "--short"])

        if tool_name == ToolName.GIT_DIFF:
            if self._is_git_workspace(workspace):
                return self._git_command(tool_name, workspace, ["git", "diff", "--no-ext-diff"])
            return ToolResult(tool_name, 0, self._non_git_diff(task, workspace))

        if tool_name in {ToolName.GIT_CLONE, ToolName.GIT_COMMIT}:
            return ToolResult(tool_name, 0, f"{tool_name.value} is disabled in simulated mode")

        if tool_name in {ToolName.READ_FILE, ToolName.WRITE_FILE, ToolName.CREATE_PR}:
            return ToolResult(tool_name, 0, f"{tool_name} accepted by executor boundary")

        return ToolResult(tool_name, 0, "Tool completed")

    def workspace_for(self, task: TaskRecord) -> Path:
        return self.workspace_root / (task.run_id or task.id)

    def prepare_workspace(self, task: TaskRecord) -> Path:
        destination = self.workspace_for(task).resolve()
        marker = self.metadata_root / f"{task.run_id or task.id}.json"
        if destination.exists() and marker.exists():
            return destination

        source = Path(task.workspace_path).expanduser().resolve() if task.workspace_path else None
        if destination.exists():
            shutil.rmtree(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)

        mode = "empty"
        if source and source.is_dir():
            mode = self._create_isolated_copy(source, destination, task.base_branch)
        else:
            destination.mkdir(parents=True, exist_ok=True)

        baseline = self._snapshot(destination)
        marker.write_text(
            json.dumps(
                {
                    "task_id": task.id,
                    "run_id": task.run_id,
                    "source": str(source) if source else None,
                    "workspace": str(destination),
                    "mode": mode,
                    "baseline": baseline,
                },
                ensure_ascii=True,
                indent=2,
            ),
            encoding="utf-8",
        )
        return destination

    def cleanup_workspace(self, task: TaskRecord) -> None:
        destination = self.workspace_for(task).resolve()
        if self._is_git_workspace(destination):
            source = Path(task.workspace_path).expanduser().resolve() if task.workspace_path else None
            if source and (source / ".git").exists():
                subprocess.run(
                    ["git", "-C", str(source), "worktree", "remove", "--force", str(destination)],
                    check=False,
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
        if destination.exists():
            shutil.rmtree(destination, ignore_errors=True)
        marker = self.metadata_root / f"{task.run_id or task.id}.json"
        marker.unlink(missing_ok=True)

    def _create_isolated_copy(self, source: Path, destination: Path, base_branch: str) -> str:
        workspace_root = self.workspace_root.resolve()
        destination_is_inside_source = self._is_within(destination, source)
        if (source / ".git").exists() and not destination_is_inside_source:
            completed = subprocess.run(
                ["git", "-C", str(source), "worktree", "add", "--detach", str(destination), base_branch],
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if completed.returncode == 0:
                return "git-worktree"

        def ignore(directory: str, names: list[str]) -> set[str]:
            ignored = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist"}
            current = Path(directory).resolve()
            for name in names:
                candidate = (current / name).resolve()
                if candidate == workspace_root or self._is_within(workspace_root, candidate):
                    ignored.add(name)
            return ignored.intersection(names)

        shutil.copytree(source, destination, ignore=ignore, symlinks=False)
        return "filesystem-copy"

    def _non_git_diff(self, task: TaskRecord, workspace: Path) -> str:
        marker = self.metadata_root / f"{task.run_id or task.id}.json"
        if not marker.exists():
            return "No baseline is available."
        baseline = json.loads(marker.read_text(encoding="utf-8")).get("baseline", {})
        current = self._snapshot(workspace)
        added = sorted(set(current) - set(baseline))
        removed = sorted(set(baseline) - set(current))
        changed = sorted(path for path in set(current) & set(baseline) if current[path] != baseline[path])
        lines = [*(f"A {path}" for path in added), *(f"M {path}" for path in changed), *(f"D {path}" for path in removed)]
        return "\n".join(lines) if lines else "No filesystem changes."

    @staticmethod
    def _git_command(tool_name: ToolName, workspace: Path, command: list[str]) -> ToolResult:
        if not ToolExecutor._is_git_workspace(workspace):
            return ToolResult(tool_name, 0, "Task workspace is not a Git worktree.")
        completed = subprocess.run(
            command,
            cwd=workspace,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        return ToolResult(tool_name, completed.returncode, (completed.stdout + completed.stderr).strip())

    @staticmethod
    def _is_git_workspace(path: Path) -> bool:
        return (path / ".git").exists()

    @staticmethod
    def _source_files(root: Path, limit: int) -> list[str]:
        ignored = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache", "dist"}
        files: list[str] = []
        for path in root.rglob("*"):
            if any(part in ignored for part in path.relative_to(root).parts):
                continue
            if path.is_file() and not path.is_symlink():
                files.append(path.relative_to(root).as_posix())
            if len(files) >= limit:
                break
        return files

    @staticmethod
    def _snapshot(root: Path, max_files: int = 5000, max_bytes: int = 1_000_000) -> dict[str, str]:
        snapshot: dict[str, str] = {}
        for relative in ToolExecutor._source_files(root, max_files):
            path = root / relative
            try:
                if path.stat().st_size > max_bytes:
                    continue
                snapshot[relative] = sha256(path.read_bytes()).hexdigest()
            except OSError:
                continue
        return snapshot

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False
