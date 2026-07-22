"""Create the original local MVP persistence schema.

Revision ID: 0001_local_mvp
Revises:
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_local_mvp"
down_revision = None
branch_labels = None
depends_on = None


def _task_child(name: str, *, with_status: bool = False) -> None:
    columns = [
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    ]
    if with_status:
        columns.insert(3, sa.Column("status", sa.String(length=40), nullable=False))
    op.create_table(name, *columns)
    op.create_index(f"ix_{name}_task_id", name, ["task_id"])
    op.create_index(f"ix_{name}_created_at", name, ["created_at"])
    if with_status:
        op.create_index(f"ix_{name}_status", name, ["status"])


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    op.create_index("ix_tasks_tenant_id", "tasks", ["tenant_id"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_created_at", "tasks", ["created_at"])

    _task_child("approvals", with_status=True)
    _task_child("artifacts")
    _task_child("run_steps", with_status=True)
    _task_child("agent_runs")
    _task_child("model_calls")
    _task_child("tool_calls")
    _task_child("trace_events")
    _task_child("chat_messages")
    _task_child("workflow_runs", with_status=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    op.create_index("ix_audit_logs_task_id", "audit_logs", ["task_id"])
    op.create_index("ix_audit_logs_created_at", "audit_logs", ["created_at"])

    op.create_table(
        "projects",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("path", sa.Text(), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    op.create_index("ix_projects_created_at", "projects", ["created_at"])

    op.create_table(
        "agent_model_overrides",
        sa.Column("agent_name", sa.String(length=40), primary_key=True),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    op.create_table(
        "agent_configurations",
        sa.Column("agent_name", sa.String(length=40), primary_key=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    op.create_table(
        "credential_metadata",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    op.create_index("ix_credential_metadata_created_at", "credential_metadata", ["created_at"])
    op.create_table(
        "idempotency_keys",
        sa.Column("key", sa.String(length=180), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
    )
    op.create_index("ix_idempotency_keys_task_id", "idempotency_keys", ["task_id"])
    op.create_table(
        "workflow_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("lease_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
    )
    for column in ("task_id", "run_id", "status", "available_at", "created_at"):
        op.create_index(f"ix_workflow_jobs_{column}", "workflow_jobs", [column])


def downgrade() -> None:
    for table in (
        "workflow_jobs",
        "idempotency_keys",
        "credential_metadata",
        "agent_configurations",
        "agent_model_overrides",
        "projects",
        "audit_logs",
        "workflow_runs",
        "chat_messages",
        "trace_events",
        "tool_calls",
        "model_calls",
        "agent_runs",
        "run_steps",
        "artifacts",
        "approvals",
        "tasks",
    ):
        op.drop_table(table)
