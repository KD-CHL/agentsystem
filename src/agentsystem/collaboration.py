from __future__ import annotations

from dataclasses import dataclass

from agentsystem.domain import AgentName, ToolName


class CollaborationRuleViolation(RuntimeError):
    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class AgentContract:
    agent_name: AgentName
    objective: str
    required_inputs: tuple[str, ...]
    required_outputs: tuple[str, ...]
    allowed_handoffs: tuple[AgentName, ...]
    tools: tuple[ToolName, ...]
    failure_owner: AgentName


class CollaborationRuleEngine:
    """Executable collaboration contract for deterministic multi-agent runs."""

    VERSION = "1.0"
    EXECUTION_MODE = "provider-configured"

    def __init__(self) -> None:
        self.contracts: dict[AgentName, AgentContract] = {
            AgentName.ORCHESTRATOR: AgentContract(
                AgentName.ORCHESTRATOR,
                "Classify the request and select the controlled code-change workflow.",
                ("prompt",),
                ("workflow",),
                (AgentName.REPO_CONTEXT,),
                (),
                AgentName.ORCHESTRATOR,
            ),
            AgentName.REPO_CONTEXT: AgentContract(
                AgentName.REPO_CONTEXT,
                "Create an isolated workspace and a bounded repository context package.",
                ("workflow",),
                ("likely_files", "base_branch"),
                (AgentName.PLANNING,),
                (ToolName.GIT_CLONE, ToolName.GIT_STATUS, ToolName.READ_FILE, ToolName.CODE_SEARCH),
                AgentName.ORCHESTRATOR,
            ),
            AgentName.PLANNING: AgentContract(
                AgentName.PLANNING,
                "Produce a minimal implementation plan, risk notes, and test strategy.",
                ("likely_files", "base_branch"),
                ("plan", "expected_paths"),
                (AgentName.CODING,),
                (ToolName.CODE_SEARCH, ToolName.READ_FILE),
                AgentName.ORCHESTRATOR,
            ),
            AgentName.CODING: AgentContract(
                AgentName.CODING,
                "Generate a focused patch in the isolated task workspace.",
                ("plan",),
                ("branch_name", "changed_paths"),
                (AgentName.TEST,),
                (ToolName.READ_FILE, ToolName.WRITE_FILE, ToolName.CODE_SEARCH, ToolName.GIT_DIFF, ToolName.GIT_COMMIT),
                AgentName.CODING,
            ),
            AgentName.TEST: AgentContract(
                AgentName.TEST,
                "Run deterministic quality gates and return repair evidence.",
                ("changed_paths",),
                ("tests_passed",),
                (AgentName.CODING, AgentName.SECURITY),
                (ToolName.RUN_TESTS, ToolName.READ_FILE),
                AgentName.CODING,
            ),
            AgentName.SECURITY: AgentContract(
                AgentName.SECURITY,
                "Check secrets, permissions, prompt injection, and high-risk paths.",
                ("changed_paths", "tests_passed"),
                ("security_passed", "changed_paths"),
                (AgentName.REVIEW,),
                (ToolName.SECRET_SCAN, ToolName.READ_FILE, ToolName.CODE_SEARCH),
                AgentName.SECURITY,
            ),
            AgentName.REVIEW: AgentContract(
                AgentName.REVIEW,
                "Review correctness, regressions, maintainability, and test coverage.",
                ("security_passed", "tests_passed"),
                ("review_passed", "review"),
                (AgentName.PR,),
                (ToolName.GIT_DIFF, ToolName.READ_FILE, ToolName.CODE_SEARCH),
                AgentName.CODING,
            ),
            AgentName.PR: AgentContract(
                AgentName.PR,
                "Package approved evidence into a simulated draft pull request.",
                ("tests_passed", "security_passed", "review_passed"),
                ("pr_url",),
                (),
                (ToolName.CREATE_PR, ToolName.GIT_STATUS, ToolName.GIT_DIFF),
                AgentName.PR,
            ),
        }

    def validate_entry(self, agent_name: AgentName, context: dict[str, object]) -> None:
        contract = self.contracts[agent_name]
        missing = [key for key in contract.required_inputs if key not in context]
        if missing:
            raise CollaborationRuleViolation(
                "HANDOFF_INPUT_INCOMPLETE",
                f"{agent_name.value} is missing required handoff input: {', '.join(missing)}",
            )
        if agent_name == AgentName.PR:
            failed = [
                key
                for key in ("tests_passed", "security_passed", "review_passed")
                if context.get(key) is not True
            ]
            if failed:
                raise CollaborationRuleViolation(
                    "QUALITY_GATE_INCOMPLETE",
                    f"PR handoff blocked by incomplete quality gates: {', '.join(failed)}",
                )

    def validate_exit(
        self,
        agent_name: AgentName,
        data: dict[str, object],
        handoff_to: AgentName | None,
    ) -> None:
        contract = self.contracts[agent_name]
        missing = [key for key in contract.required_outputs if key not in data]
        if missing:
            raise CollaborationRuleViolation(
                "AGENT_OUTPUT_INCOMPLETE",
                f"{agent_name.value} did not produce required output: {', '.join(missing)}",
            )
        if handoff_to is None and contract.allowed_handoffs:
            raise CollaborationRuleViolation(
                "HANDOFF_TARGET_MISSING",
                f"{agent_name.value} must hand off to an allowed downstream agent",
            )
        if handoff_to is not None and handoff_to not in contract.allowed_handoffs:
            raise CollaborationRuleViolation(
                "HANDOFF_TARGET_DENIED",
                f"{agent_name.value} cannot hand off to {handoff_to.value}",
            )
        if agent_name == AgentName.TEST:
            expected = AgentName.SECURITY if data.get("tests_passed") is True else AgentName.CODING
            if handoff_to != expected:
                raise CollaborationRuleViolation(
                    "TEST_HANDOFF_INVALID",
                    f"Test result requires handoff to {expected.value}",
                )

    def public_rules(self) -> dict[str, object]:
        return {
            "version": self.VERSION,
            "execution_mode": self.EXECUTION_MODE,
            "principles": [
                "deterministic orchestration owns state and recovery",
                "each agent has one bounded objective and least-privilege tools",
                "handoffs use required input and output contracts",
                "test, security, and review must reach consensus before PR packaging",
                "human approvals pause and resume the same versioned context",
                "all decisions are attributable through one task trace",
            ],
            "failure_policy": {
                "test_repair_attempts": 2,
                "missing_contract_data": "fail_closed",
                "tool_permission_violation": "fail_closed",
                "live_model_call": "disabled",
                "human_rejection": "terminal",
            },
            "agents": [
                {
                    "agent_name": contract.agent_name,
                    "objective": contract.objective,
                    "required_inputs": contract.required_inputs,
                    "required_outputs": contract.required_outputs,
                    "allowed_handoffs": contract.allowed_handoffs,
                    "tools": contract.tools,
                    "failure_owner": contract.failure_owner,
                }
                for contract in self.contracts.values()
            ],
        }
