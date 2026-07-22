from __future__ import annotations

from typing import Any

from agentsystem.domain import AuditLogRecord, TaskRecord, TraceEvent
from agentsystem.store import InMemoryStore


class TraceRecorder:
    def __init__(self, store: InMemoryStore) -> None:
        self.store = store

    def event(
        self,
        task: TaskRecord,
        event_type: str,
        actor: str,
        payload: dict[str, Any] | None = None,
    ) -> TraceEvent:
        return self.store.add_trace_event(
            TraceEvent(
                task_id=task.id,
                trace_id=task.trace_id,
                run_id=task.run_id,
                event_type=event_type,
                actor=actor,
                payload=payload or {},
            )
        )

    def audit(
        self,
        task: TaskRecord | None,
        actor: str,
        action: str,
        details: dict[str, Any] | None = None,
        *,
        tenant_id: str | None = None,
        actor_id: str | None = None,
    ) -> AuditLogRecord:
        return self.store.add_audit_log(
            AuditLogRecord(
                task_id=task.id if task else None,
                trace_id=task.trace_id if task else None,
                tenant_id=task.tenant_id if task else (tenant_id or "default"),
                actor_id=actor_id,
                actor=actor,
                action=action,
                details=details or {},
            )
        )
