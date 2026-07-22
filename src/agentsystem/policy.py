from __future__ import annotations

import re
from dataclasses import dataclass

from agentsystem.domain import AgentName, ApprovalPolicy, ApprovalType, ToolName


class PolicyViolation(RuntimeError):
    pass


@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    requires_approval: bool = False
    approval_type: ApprovalType | None = None


class SecurityPolicy:
    SECRET_PATTERNS = [
        re.compile(r"(?i)(api[_-]?key|secret|token|password)\s*[:=]\s*['\"]?[a-z0-9_\-]{12,}"),
        re.compile(r"ghp_[A-Za-z0-9_]{20,}"),
        re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),
    ]
    PROMPT_INJECTION_PATTERNS = [
        re.compile(r"(?i)ignore (all )?(previous|prior) instructions"),
        re.compile(r"(?i)reveal (the )?(system|developer) prompt"),
        re.compile(r"(?i)exfiltrate|steal|leak"),
    ]
    HIGH_RISK_PATHS = (
        ".github/workflows/",
        "infra/",
        "terraform/",
        "k8s/",
        "helm/",
        "migrations/",
        ".env",
    )

    TOOL_PERMISSIONS: dict[AgentName, set[ToolName]] = {
        AgentName.ORCHESTRATOR: set(),
        AgentName.REPO_CONTEXT: {
            ToolName.GIT_CLONE,
            ToolName.GIT_STATUS,
            ToolName.READ_FILE,
            ToolName.CODE_SEARCH,
        },
        AgentName.PLANNING: {ToolName.CODE_SEARCH, ToolName.READ_FILE},
        AgentName.CODING: {
            ToolName.READ_FILE,
            ToolName.WRITE_FILE,
            ToolName.CODE_SEARCH,
            ToolName.GIT_DIFF,
            ToolName.GIT_COMMIT,
        },
        AgentName.TEST: {ToolName.RUN_TESTS, ToolName.READ_FILE},
        AgentName.SECURITY: {ToolName.SECRET_SCAN, ToolName.READ_FILE, ToolName.CODE_SEARCH},
        AgentName.REVIEW: {ToolName.GIT_DIFF, ToolName.READ_FILE, ToolName.CODE_SEARCH},
        AgentName.PR: {ToolName.CREATE_PR, ToolName.GIT_STATUS, ToolName.GIT_DIFF},
    }

    def screen_prompt(self, prompt: str) -> PolicyDecision:
        for pattern in self.PROMPT_INJECTION_PATTERNS:
            if pattern.search(prompt):
                return PolicyDecision(False, "Prompt injection pattern detected")
        return PolicyDecision(True, "Prompt accepted")

    def scan_for_secrets(self, text: str) -> PolicyDecision:
        for pattern in self.SECRET_PATTERNS:
            if pattern.search(text):
                return PolicyDecision(False, "Potential secret detected")
        return PolicyDecision(True, "No secret-like content detected")

    def check_tool_permission(self, agent_name: AgentName, tool_name: ToolName) -> PolicyDecision:
        allowed = tool_name in self.TOOL_PERMISSIONS.get(agent_name, set())
        return PolicyDecision(
            allowed=allowed,
            reason="Tool allowed" if allowed else f"{agent_name} cannot call {tool_name}",
        )

    def check_changed_paths(self, paths: list[str], approval_policy: ApprovalPolicy) -> PolicyDecision:
        risky = [
            path
            for path in paths
            if any(path.startswith(prefix) or path == prefix for prefix in self.HIGH_RISK_PATHS)
        ]
        if risky and approval_policy != ApprovalPolicy.AUTO:
            return PolicyDecision(
                allowed=True,
                reason=f"High-risk paths require approval: {', '.join(risky)}",
                requires_approval=True,
                approval_type=ApprovalType.HIGH_RISK_CHANGE,
            )
        return PolicyDecision(True, "Changed paths accepted")

    def check_command(self, command: list[str]) -> PolicyDecision:
        joined = " ".join(command)
        disallowed = ["rm -rf", "curl ", "wget ", "nc ", "ssh ", "scp ", "sudo "]
        if any(token in joined for token in disallowed):
            return PolicyDecision(False, f"Command denied by sandbox policy: {joined}")
        return PolicyDecision(True, "Command accepted")
