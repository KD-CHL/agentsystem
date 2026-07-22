from __future__ import annotations

from agentsystem.agents import AgentRuntime
from agentsystem.collaboration import CollaborationRuleEngine, CollaborationRuleViolation
from agentsystem.domain import (
    AgentName,
    ApprovalDecision,
    ApprovalPolicy,
    ApprovalRecord,
    ApprovalType,
    GitHubWebhookEvent,
    RunStatus,
    RunStepRecord,
    StepStatus,
    TaskCreate,
    TaskRecord,
    TaskStatus,
    TaskView,
    WorkflowRunRecord,
    utcnow,
)
from agentsystem.policy import SecurityPolicy
from agentsystem.store import InMemoryStore, NotFoundError
from agentsystem.tracing import TraceRecorder


class WorkflowService:
    def __init__(
        self,
        store: InMemoryStore,
        runtime: AgentRuntime,
        policy: SecurityPolicy,
        trace: TraceRecorder,
        rules: CollaborationRuleEngine | None = None,
        max_fix_attempts: int = 2,
    ) -> None:
        self.store = store
        self.runtime = runtime
        self.policy = policy
        self.trace = trace
        self.rules = rules or CollaborationRuleEngine()
        self.max_fix_attempts = max_fix_attempts

    def create_task(self, payload: TaskCreate) -> TaskView:
        view = self.prepare_task(payload)
        if view.task.status == TaskStatus.QUEUED:
            self.execute_task(
                view.task.id,
                start=AgentName.ORCHESTRATOR,
                context={"prompt": view.task.prompt},
            )
        return self.store.task_view(view.task.id)

    def create_task_deferred(self, payload: TaskCreate) -> TaskView:
        return self.prepare_task(payload)

    def prepare_task(self, payload: TaskCreate) -> TaskView:
        task = TaskRecord(
            tenant_id=payload.tenant_id,
            owner_id=payload.owner_id,
            repo_id=payload.repo_id,
            base_branch=payload.base_branch,
            prompt=payload.prompt,
            issue_url=payload.issue_url,
            workspace_path=payload.workspace_path,
            approval_policy=payload.approval_policy,
            priority=payload.priority,
            status=TaskStatus.QUEUED,
            current_step="queued",
        )
        run = WorkflowRunRecord(task_id=task.id, trace_id=task.trace_id)
        task.run_id = run.id
        self.store.create_task(task)
        self.store.add_workflow_run(run)
        self.trace.audit(task, "api", "task.created", payload.model_dump())
        decision = self.policy.screen_prompt(task.prompt)
        if not decision.allowed:
            task.status = TaskStatus.FAILED
            task.failure_code = "PROMPT_GUARDRAIL_BLOCKED"
            task.failure_reason = decision.reason
            task.current_step = "security_prescreen"
            self.store.update_task(task)
            run.status = RunStatus.FAILED
            run.error_code = task.failure_code
            run.error_message = task.failure_reason
            run.completed_at = utcnow()
            self.store.update_workflow_run(run)
            self.trace.event(task, "guardrail.failed", "security", {"reason": decision.reason})
            return self.store.task_view(task.id)
        return self.store.task_view(task.id)

    def execute_task(
        self,
        task_id: str,
        *,
        start: AgentName,
        context: dict[str, object] | None = None,
    ) -> TaskView:
        task = self.store.get_task(task_id)
        if task.status in {TaskStatus.CANCELED, TaskStatus.COMPLETED, TaskStatus.FAILED}:
            return self.store.task_view(task_id)
        self._run_until_gate(task, start=start, context=context or {})
        return self.store.task_view(task_id)

    def create_task_from_webhook(self, payload: GitHubWebhookEvent) -> TaskView:
        return self.create_task(
            TaskCreate(
                repo_id=payload.repo_id,
                base_branch=payload.base_branch,
                prompt=payload.prompt,
                issue_url=payload.issue_url,
                approval_policy=ApprovalPolicy.MANUAL_PLAN,
            )
        )

    def get_task(self, task_id: str) -> TaskView:
        return self.store.task_view(task_id)

    def list_tasks(self) -> list[TaskRecord]:
        return self.store.list_tasks()

    def approve(
        self,
        task_id: str,
        decision: ApprovalDecision,
        *,
        resume: bool = True,
    ) -> TaskView:
        task = self.store.get_task(task_id)
        if task.status != TaskStatus.AWAITING_APPROVAL:
            raise ValueError("Task is not awaiting approval")
        approval = self.store.get_approval(decision.approval_id)
        if approval.task_id != task_id:
            raise NotFoundError(decision.approval_id)
        if approval.status != StepStatus.AWAITING_APPROVAL:
            raise ValueError("Approval has already been decided")

        decided = approval.model_copy(deep=True)
        decided.status = StepStatus.COMPLETED if decision.approved else StepStatus.FAILED
        decided.decided_at = utcnow()
        decided.decided_by = decision.actor
        decided.comment = decision.comment
        if not self.store.decide_approval(decided, StepStatus.AWAITING_APPROVAL):
            raise ValueError("Approval has already been decided")
        self.trace.audit(
            task,
            decision.actor,
            "approval.decided",
            {
                "approval_id": decided.id,
                "approval_type": decided.approval_type,
                "approved": decision.approved,
            },
        )

        if not decision.approved:
            task.status = TaskStatus.FAILED
            task.current_step = "approval_rejected"
            task.failure_code = "APPROVAL_REJECTED"
            task.failure_reason = decision.comment or "Approval rejected"
            self.store.update_task(task)
            self._finish_run(task, RunStatus.FAILED, task.failure_code, task.failure_reason)
            self.trace.event(
                task,
                "workflow.failed",
                "workflow",
                {"code": task.failure_code, "reason": task.failure_reason},
            )
            return self.store.task_view(task_id)

        next_agent = self.next_agent_after_approval(decided.approval_type)
        task.status = TaskStatus.QUEUED
        task.current_step = f"queued_{next_agent.value}"
        self.store.update_task(task)
        self._set_run_status(task, RunStatus.QUEUED)
        if resume:
            self._run_until_gate(task, start=next_agent, context={"approval_id": decided.id})
        return self.store.task_view(task_id)

    def cancel(self, task_id: str) -> TaskView:
        task = self.store.get_task(task_id)
        if task.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELED}:
            return self.store.task_view(task_id)
        task.status = TaskStatus.CANCELED
        task.current_step = "canceled"
        task.failure_code = None
        task.failure_reason = None
        self.store.update_task(task)
        self.store.cancel_pending_approvals(task_id)
        cancel_jobs = getattr(self.store, "cancel_workflow_jobs", None)
        if cancel_jobs:
            cancel_jobs(task_id)
        self.runtime.tools.cleanup_workspace(task)
        self._finish_run(task, RunStatus.CANCELED)
        self.trace.audit(task, "api", "task.canceled", {})
        self.trace.event(task, "workflow.canceled", "workflow", {})
        return self.store.task_view(task_id)

    def trace_for_task(self, task_id: str) -> dict[str, object]:
        return self.store.trace_for_task(task_id)

    def _run_until_gate(
        self,
        task: TaskRecord,
        *,
        start: AgentName,
        context: dict[str, object],
    ) -> None:
        current_agent: AgentName | None = start
        task.status = TaskStatus.RUNNING
        task.failure_code = None
        task.failure_reason = None
        self.store.update_task(task)
        run = self._set_run_status(task, RunStatus.RUNNING)
        rolling_context = dict(run.context_snapshot if run else {})
        rolling_context.update(context)
        if run and run.started_at is None:
            run.started_at = utcnow()
            self.store.update_workflow_run(run)

        while current_agent:
            task = self.store.get_task(task.id)
            if task.status == TaskStatus.CANCELED:
                self._finish_run(task, RunStatus.CANCELED)
                return
            step = self._start_step(task, current_agent)
            task.current_step = current_agent
            self.store.update_task(task)
            try:
                self.rules.validate_entry(current_agent, rolling_context)
                self.trace.event(
                    task,
                    "handoff.received",
                    current_agent,
                    {
                        "from": run.last_agent if run else None,
                        "to": current_agent,
                        "context_version": run.context_version if run else 0,
                        "available_keys": sorted(key for key in rolling_context if not key.startswith("_")),
                    },
                )
                result = self.runtime.run(current_agent, task, rolling_context)
                result_data = result.data or {}
                self.rules.validate_exit(current_agent, result_data, result.handoff_to)
                rolling_context.update(result_data)
                if run:
                    run.context_version += 1
                    run.context_snapshot = dict(rolling_context)
                    run.last_agent = current_agent
                    self.store.update_workflow_run(run)
                self.trace.event(
                    task,
                    "handoff.completed",
                    current_agent,
                    {
                        "from": current_agent,
                        "to": result.handoff_to,
                        "context_version": run.context_version if run else 0,
                        "produced_keys": sorted(result_data),
                    },
                )
            except Exception as exc:
                step.status = StepStatus.FAILED
                step.error = str(exc)[:1000]
                step.completed_at = utcnow()
                self.store.update_step(step)
                code = getattr(exc, "code", None) or "AGENT_EXECUTION_FAILED"
                self._fail_task(
                    task,
                    code=code,
                    reason=f"{current_agent.value} failed: {exc}",
                )
                return
            self._complete_step(step)

            if current_agent == AgentName.TEST and rolling_context.get("tests_passed") is False:
                fix_attempts = int(rolling_context.get("fix_attempts", 0)) + 1
                rolling_context["fix_attempts"] = fix_attempts
                if run:
                    run.context_snapshot = dict(rolling_context)
                    self.store.update_workflow_run(run)
                if fix_attempts > self.max_fix_attempts:
                    self._fail_task(
                        task,
                        code="TEST_REPAIR_EXHAUSTED",
                        reason="Automated test repair attempts exhausted",
                        current_step="test_repair_exhausted",
                        details={"fix_attempts": fix_attempts},
                    )
                    return

            gate = self._approval_gate_for(task, current_agent, rolling_context)
            if gate:
                self._request_approval(task, gate[0], gate[1])
                return

            current_agent = result.handoff_to

        task.status = TaskStatus.COMPLETED
        task.current_step = "completed"
        self.store.update_task(task)
        self._finish_run(task, RunStatus.COMPLETED)
        self.trace.event(task, "workflow.completed", "workflow", {"pr_url": task.pr_url})

    def _approval_gate_for(
        self,
        task: TaskRecord,
        agent_name: AgentName,
        context: dict[str, object],
    ) -> tuple[ApprovalType, str] | None:
        if task.approval_policy == ApprovalPolicy.AUTO:
            return None
        if agent_name == AgentName.PLANNING and task.approval_policy in {
            ApprovalPolicy.MANUAL_PLAN,
            ApprovalPolicy.MANUAL_ALL,
        }:
            return ApprovalType.PLAN, "Implementation plan requires human approval"
        if context.get("requires_approval") and context.get("approval_type"):
            return context["approval_type"], "Security policy requires human approval"
        if agent_name == AgentName.REVIEW and task.approval_policy == ApprovalPolicy.MANUAL_ALL:
            return ApprovalType.CREATE_PR, "Draft PR creation requires human approval"
        return None

    def _request_approval(
        self,
        task: TaskRecord,
        approval_type: ApprovalType,
        reason: str,
    ) -> ApprovalRecord:
        approval = self.store.add_approval(
            ApprovalRecord(task_id=task.id, approval_type=approval_type, reason=reason)
        )
        task.status = TaskStatus.AWAITING_APPROVAL
        task.current_step = f"awaiting_{approval_type}_approval"
        self.store.update_task(task)
        self._set_run_status(task, RunStatus.AWAITING_APPROVAL)
        self.trace.event(
            task,
            "approval.requested",
            "workflow",
            {"approval_id": approval.id, "approval_type": approval_type, "reason": reason},
        )
        return approval

    @staticmethod
    def next_agent_after_approval(approval_type: ApprovalType) -> AgentName:
        if approval_type == ApprovalType.PLAN:
            return AgentName.CODING
        if approval_type == ApprovalType.CREATE_PR:
            return AgentName.PR
        if approval_type == ApprovalType.HIGH_RISK_CHANGE:
            return AgentName.REVIEW
        if approval_type == ApprovalType.PUSH_BRANCH:
            return AgentName.PR
        return AgentName.CODING

    def _start_step(self, task: TaskRecord, agent_name: AgentName) -> RunStepRecord:
        step = self.store.add_step(
            RunStepRecord(
                task_id=task.id,
                run_id=task.run_id,
                name=agent_name,
                status=StepStatus.RUNNING,
                started_at=utcnow(),
            )
        )
        self.trace.event(task, "step.started", "workflow", {"step": agent_name})
        return step

    def _complete_step(self, step: RunStepRecord) -> None:
        step.status = StepStatus.COMPLETED
        step.completed_at = utcnow()
        self.store.update_step(step)

    def _set_run_status(
        self,
        task: TaskRecord,
        status: RunStatus,
    ) -> WorkflowRunRecord | None:
        if not task.run_id:
            return None
        run = self.store.get_workflow_run(task.run_id)
        run.status = status
        self.store.update_workflow_run(run)
        return run

    def _finish_run(
        self,
        task: TaskRecord,
        status: RunStatus,
        error_code: str | None = None,
        error_message: str | None = None,
    ) -> None:
        run = self._set_run_status(task, status)
        if run is None:
            return
        run.error_code = error_code
        run.error_message = error_message
        run.completed_at = utcnow()
        self.store.update_workflow_run(run)

    def _fail_task(
        self,
        task: TaskRecord,
        *,
        code: str,
        reason: str,
        current_step: str = "failed",
        details: dict[str, object] | None = None,
    ) -> None:
        task.status = TaskStatus.FAILED
        task.current_step = current_step
        task.failure_code = code
        task.failure_reason = reason[:1000]
        self.store.update_task(task)
        self._finish_run(task, RunStatus.FAILED, code, task.failure_reason)
        payload = {"code": code, "reason": task.failure_reason}
        payload.update(details or {})
        self.trace.event(task, "workflow.failed", "workflow", payload)
