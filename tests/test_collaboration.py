from agentsystem.agents import AgentResult
from agentsystem.collaboration import CollaborationRuleEngine, CollaborationRuleViolation
from agentsystem.container import AppContainer
from agentsystem.domain import AgentName, ApprovalDecision, ApprovalPolicy, StepStatus, TaskCreate, TaskStatus


def test_collaboration_rules_expose_bounded_contracts() -> None:
    rules = CollaborationRuleEngine()
    payload = rules.public_rules()

    assert payload["version"] == "1.0"
    assert payload["execution_mode"] == "provider-configured"
    assert len(payload["agents"]) == 8
    pr = next(item for item in payload["agents"] if item["agent_name"] == AgentName.PR)
    assert set(pr["required_inputs"]) == {"tests_passed", "security_passed", "review_passed"}


def test_rule_engine_rejects_illegal_handoff() -> None:
    rules = CollaborationRuleEngine()

    try:
        rules.validate_exit(AgentName.PLANNING, {"plan": "ok", "expected_paths": []}, AgentName.PR)
    except CollaborationRuleViolation as exc:
        assert exc.code == "HANDOFF_TARGET_DENIED"
    else:
        raise AssertionError("Illegal handoff should be rejected")


def test_context_is_versioned_and_restored_across_approval() -> None:
    container = AppContainer()
    view = container.workflow.create_task(
        TaskCreate(
            repo_id="local/demo",
            prompt="Improve retry behavior",
            approval_policy=ApprovalPolicy.MANUAL_PLAN,
        )
    )

    assert view.task.status == TaskStatus.AWAITING_APPROVAL
    run = view.runs[-1]
    assert run.context_version == 3
    assert {"workflow", "likely_files", "plan"} <= set(run.context_snapshot)

    approval = next(item for item in view.approvals if item.status == StepStatus.AWAITING_APPROVAL)
    completed = container.workflow.approve(
        view.task.id,
        ApprovalDecision(approval_id=approval.id, approved=True, actor="pytest"),
    )

    assert completed.task.status == TaskStatus.COMPLETED
    final_run = completed.runs[-1]
    assert final_run.context_version == 8
    assert final_run.context_snapshot["tests_passed"] is True
    assert final_run.context_snapshot["security_passed"] is True
    assert final_run.context_snapshot["review_passed"] is True
    events = container.store.trace_for_task(view.task.id)["events"]
    assert any(item.event_type == "handoff.received" for item in events)
    assert any(item.event_type == "handoff.completed" for item in events)


def test_pr_is_blocked_when_review_consensus_is_false(monkeypatch) -> None:
    container = AppContainer()
    review = container.runtime.agents[AgentName.REVIEW]

    def negative_review(task, context):
        return AgentResult(
            summary="Review rejected",
            handoff_to=AgentName.PR,
            data={"review_passed": False, "review": "Regression risk remains"},
        )

    monkeypatch.setattr(review, "_run", negative_review)
    view = container.workflow.create_task(
        TaskCreate(
            repo_id="local/demo",
            prompt="Change critical behavior",
            approval_policy=ApprovalPolicy.AUTO,
        )
    )

    assert view.task.status == TaskStatus.FAILED
    assert view.task.failure_code == "QUALITY_GATE_INCOMPLETE"
    assert "review_passed" in (view.task.failure_reason or "")
