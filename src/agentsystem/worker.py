from __future__ import annotations

from threading import Event, Thread

from agentsystem.domain import AgentName, TaskRecord, WorkflowJobRecord
from agentsystem.workflow import WorkflowService


class DurableWorkflowWorker:
    """Small SQLite-backed worker for resumable local task execution."""

    def __init__(
        self,
        store,
        workflow: WorkflowService,
        *,
        poll_interval_seconds: float = 0.25,
        lease_seconds: int = 60,
    ) -> None:
        self.store = store
        self.workflow = workflow
        self.poll_interval_seconds = poll_interval_seconds
        self.lease_seconds = lease_seconds
        self._stop = Event()
        self._wake = Event()
        self._thread: Thread | None = None

    @property
    def running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = Thread(target=self._run, name="agentsystem-worker", daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 5.0) -> None:
        self._stop.set()
        self._wake.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        self._thread = None

    def enqueue(
        self,
        task: TaskRecord,
        *,
        start_agent: AgentName,
        context: dict[str, object] | None = None,
    ) -> WorkflowJobRecord:
        if not task.run_id:
            raise ValueError("Task has no workflow run")
        job = WorkflowJobRecord(
            task_id=task.id,
            run_id=task.run_id,
            start_agent=start_agent,
            context=context or {},
        )
        self.store.enqueue_workflow_job(job)
        self._wake.set()
        return job

    def run_once(self) -> bool:
        job = self.store.claim_workflow_job(self.lease_seconds)
        if job is None:
            return False
        try:
            self.workflow.execute_task(
                job.task_id,
                start=job.start_agent,
                context=job.context,
            )
            self.store.complete_workflow_job(job)
        except Exception as exc:
            self.store.fail_workflow_job(job, str(exc))
        return True

    def _run(self) -> None:
        while not self._stop.is_set():
            if self.run_once():
                continue
            self._wake.wait(self.poll_interval_seconds)
            self._wake.clear()
