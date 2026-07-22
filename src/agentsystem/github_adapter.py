from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import quote

from agentsystem.config import Settings
from agentsystem.domain import TaskRecord


@dataclass(frozen=True)
class DraftPR:
    url: str
    title: str
    body: str
    draft: bool = True


class GitHubEnterpriseAdapter:
    """Boundary for GitHub Enterprise or compatible private Git providers."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def create_draft_pr(
        self,
        task: TaskRecord,
        title: str,
        body: str,
        head_branch: str,
    ) -> DraftPR:
        if self.settings.github_enterprise_url and self.settings.github_app_token:
            # Real implementation should call the GitHub REST API or GraphQL API
            # here. The MVP keeps the boundary explicit and side-effect free.
            base = self.settings.github_enterprise_url.rstrip("/")
            repo = quote(task.repo_id, safe="")
            url = f"{base}/mock-pr/{repo}/{quote(head_branch, safe='')}"
        else:
            repo = quote(task.repo_id, safe="")
            url = f"https://github-enterprise.local/mock-pr/{repo}/{quote(head_branch, safe='')}"
        return DraftPR(url=url, title=title, body=body)
