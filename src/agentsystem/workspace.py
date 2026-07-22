from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from agentsystem.domain import WorkspaceFile, WorkspaceOpen, WorkspaceRecord
from agentsystem.store import InMemoryStore, NotFoundError


IGNORED_NAMES = {
    ".git",
    ".hg",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "__pycache__",
    "dist",
    "node_modules",
}

TEXT_SUFFIXES = {
    ".css",
    ".go",
    ".html",
    ".js",
    ".json",
    ".jsx",
    ".md",
    ".py",
    ".rs",
    ".sh",
    ".toml",
    ".ts",
    ".tsx",
    ".txt",
    ".yaml",
    ".yml",
}


class WorkspaceService:
    def __init__(self, store: InMemoryStore, allowed_roots: list[str] | None = None) -> None:
        self.store = store
        self.allowed_roots = [Path(item).expanduser().resolve() for item in (allowed_roots or [])]

    def open_workspace(self, payload: WorkspaceOpen) -> WorkspaceRecord:
        root = self._resolve_directory(payload.path)
        files = self._walk_files(root, limit=180)
        summary = self._summary(root, files)
        return self.store.upsert_workspace(
            WorkspaceRecord(
                tenant_id=payload.tenant_id,
                owner_id=payload.owner_id,
                name=root.name,
                path=str(root),
                summary=summary,
                file_count=len(files),
            )
        )

    def list_workspaces(self) -> list[WorkspaceRecord]:
        return self.store.list_workspaces()

    def pick_directory(self) -> dict[str, str]:
        if sys.platform != "darwin":
            return {"status": "unsupported", "path": ""}
        script = 'POSIX path of (choose folder with prompt "选择项目目录")'
        result = subprocess.run(
            ["osascript", "-e", script],
            capture_output=True,
            check=False,
            text=True,
            timeout=120,
        )
        if result.returncode != 0:
            return {"status": "canceled", "path": ""}
        path = result.stdout.strip()
        if not path:
            return {"status": "canceled", "path": ""}
        return {"status": "selected", "path": str(self._resolve_directory(path))}

    def workspace_for_path(
        self,
        path: str,
        *,
        tenant_id: str = "default",
        owner_id: str = "local-admin",
    ) -> WorkspaceRecord:
        root = self._resolve_directory(path)
        return self.open_workspace(
            WorkspaceOpen(path=str(root), tenant_id=tenant_id, owner_id=owner_id)
        )

    def list_files(self, workspace_id: str, path: str = "") -> list[WorkspaceFile]:
        workspace = self.store.get_workspace(workspace_id)
        root = Path(workspace.path)
        target = self._safe_child(root, path)
        if not target.is_dir():
            raise NotFoundError(path)

        items: list[WorkspaceFile] = []
        for child in sorted(target.iterdir(), key=lambda item: (item.is_file(), item.name.lower())):
            if child.name in IGNORED_NAMES:
                continue
            try:
                child.resolve().relative_to(root)
                stat = child.stat()
            except (OSError, ValueError):
                continue
            rel = child.relative_to(root).as_posix()
            items.append(
                WorkspaceFile(
                    path=rel,
                    name=child.name,
                    kind="directory" if child.is_dir() else "file",
                    size_bytes=None if child.is_dir() else stat.st_size,
                )
            )
            if len(items) >= 200:
                break
        return items

    def read_file(self, workspace_id: str, path: str, max_bytes: int = 120_000) -> dict[str, object]:
        workspace = self.store.get_workspace(workspace_id)
        root = Path(workspace.path)
        target = self._safe_child(root, path)
        if not target.is_file():
            raise NotFoundError(path)
        if target.suffix.lower() not in TEXT_SUFFIXES and target.name not in {"Dockerfile", "Makefile"}:
            raise ValueError("Only common text/code files can be previewed")
        with target.open("rb") as handle:
            data = handle.read(max_bytes + 1)
        return {
            "path": target.relative_to(root).as_posix(),
            "truncated": len(data) > max_bytes,
            "content": data[:max_bytes].decode("utf-8", errors="replace"),
        }

    def reveal(self, workspace_id: str) -> dict[str, str]:
        workspace = self.store.get_workspace(workspace_id)
        if sys.platform == "darwin":
            subprocess.run(["open", workspace.path], check=False, timeout=5)
            return {"status": "opened", "path": workspace.path}
        return {"status": "unsupported", "path": workspace.path}

    def _resolve_directory(self, path: str) -> Path:
        expanded = Path(path).expanduser().resolve()
        if not expanded.exists():
            raise NotFoundError(path)
        if not expanded.is_dir():
            raise ValueError("Workspace path must be a directory")
        if self.allowed_roots and not any(self._is_within(expanded, root) for root in self.allowed_roots):
            raise ValueError("Workspace path is outside the configured project roots")
        return expanded

    @staticmethod
    def _safe_child(root: Path, path: str) -> Path:
        target = (root / path).resolve()
        target.relative_to(root)
        return target

    def _walk_files(self, root: Path, limit: int) -> list[Path]:
        files: list[Path] = []
        for path in root.rglob("*"):
            if any(part in IGNORED_NAMES for part in path.relative_to(root).parts):
                continue
            if path.is_symlink():
                continue
            if path.is_file():
                files.append(path)
            if len(files) >= limit:
                break
        return files

    @staticmethod
    def _is_within(path: Path, root: Path) -> bool:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            return False

    @staticmethod
    def _summary(root: Path, files: list[Path]) -> str:
        suffix_counts: dict[str, int] = {}
        visible = []
        for file_path in files[:60]:
            rel = file_path.relative_to(root).as_posix()
            visible.append(rel)
            suffix = file_path.suffix.lower() or "[no extension]"
            suffix_counts[suffix] = suffix_counts.get(suffix, 0) + 1

        top_suffixes = ", ".join(
            f"{suffix}:{count}" for suffix, count in sorted(suffix_counts.items(), key=lambda item: item[1], reverse=True)[:8]
        )
        tree = "\n".join(f"- {item}" for item in visible) if visible else "- No readable files found"
        return (
            f"Workspace: {root}\n"
            f"Indexed files: {len(files)}\n"
            f"Top file types: {top_suffixes or 'n/a'}\n"
            "Sample files:\n"
            f"{tree}"
        )
