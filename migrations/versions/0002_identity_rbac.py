"""Add local identity, RBAC ownership, and query columns.

Revision ID: 0002_identity_rbac
Revises: 0001_local_mvp
"""
from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa


revision = "0002_identity_rbac"
down_revision = "0001_local_mvp"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("username", sa.String(length=120), nullable=False),
        sa.Column("role", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.UniqueConstraint("tenant_id", "username", name="uq_users_tenant_username"),
    )
    for column in ("tenant_id", "username", "role", "status", "created_at"):
        op.create_index(f"ix_users_{column}", "users", [column])

    op.create_table(
        "auth_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_auth_sessions_user"),
    )
    for column in ("user_id", "token_hash", "expires_at", "revoked_at", "created_at"):
        op.create_index(f"ix_auth_sessions_{column}", "auth_sessions", [column])

    with op.batch_alter_table("tasks") as batch:
        batch.add_column(sa.Column("owner_id", sa.String(length=64), nullable=False, server_default="local-admin"))
        batch.add_column(sa.Column("priority", sa.String(length=20), nullable=False, server_default="normal"))
        batch.add_column(sa.Column("repo_id", sa.String(length=300), nullable=False, server_default=""))
        batch.add_column(sa.Column("prompt", sa.Text(), nullable=False, server_default=""))
        batch.create_index("ix_tasks_owner_id", ["owner_id"])
        batch.create_index("ix_tasks_priority", ["priority"])
        batch.create_index("ix_tasks_repo_id", ["repo_id"])

    with op.batch_alter_table("projects") as batch:
        batch.add_column(sa.Column("tenant_id", sa.String(length=120), nullable=False, server_default="default"))
        batch.add_column(sa.Column("owner_id", sa.String(length=64), nullable=False, server_default="local-admin"))
        batch.create_index("ix_projects_tenant_id", ["tenant_id"])
        batch.create_index("ix_projects_owner_id", ["owner_id"])

    with op.batch_alter_table("audit_logs") as batch:
        batch.add_column(sa.Column("tenant_id", sa.String(length=120), nullable=False, server_default="default"))
        batch.add_column(sa.Column("actor_id", sa.String(length=64), nullable=True))
        batch.add_column(sa.Column("action", sa.String(length=160), nullable=False, server_default=""))
        batch.create_index("ix_audit_logs_tenant_id", ["tenant_id"])
        batch.create_index("ix_audit_logs_actor_id", ["actor_id"])
        batch.create_index("ix_audit_logs_action", ["action"])

    _backfill_json_columns()


def _backfill_json_columns() -> None:
    connection = op.get_bind()
    for row in connection.execute(sa.text("SELECT id, payload FROM tasks")):
        payload = json.loads(row.payload)
        connection.execute(
            sa.text(
                "UPDATE tasks SET owner_id=:owner_id, priority=:priority, repo_id=:repo_id, prompt=:prompt WHERE id=:id"
            ),
            {
                "id": row.id,
                "owner_id": payload.get("owner_id", "local-admin"),
                "priority": payload.get("priority", "normal"),
                "repo_id": payload.get("repo_id", ""),
                "prompt": payload.get("prompt", ""),
            },
        )
    for row in connection.execute(sa.text("SELECT id, payload FROM projects")):
        payload = json.loads(row.payload)
        connection.execute(
            sa.text("UPDATE projects SET tenant_id=:tenant_id, owner_id=:owner_id WHERE id=:id"),
            {
                "id": row.id,
                "tenant_id": payload.get("tenant_id", "default"),
                "owner_id": payload.get("owner_id", "local-admin"),
            },
        )
    for row in connection.execute(sa.text("SELECT id, payload FROM audit_logs")):
        payload = json.loads(row.payload)
        connection.execute(
            sa.text(
                "UPDATE audit_logs SET tenant_id=:tenant_id, actor_id=:actor_id, action=:action WHERE id=:id"
            ),
            {
                "id": row.id,
                "tenant_id": payload.get("tenant_id", "default"),
                "actor_id": payload.get("actor_id"),
                "action": payload.get("action", ""),
            },
        )


def downgrade() -> None:
    with op.batch_alter_table("audit_logs") as batch:
        batch.drop_index("ix_audit_logs_action")
        batch.drop_index("ix_audit_logs_actor_id")
        batch.drop_index("ix_audit_logs_tenant_id")
        batch.drop_column("action")
        batch.drop_column("actor_id")
        batch.drop_column("tenant_id")
    with op.batch_alter_table("projects") as batch:
        batch.drop_index("ix_projects_owner_id")
        batch.drop_index("ix_projects_tenant_id")
        batch.drop_column("owner_id")
        batch.drop_column("tenant_id")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_index("ix_tasks_repo_id")
        batch.drop_index("ix_tasks_priority")
        batch.drop_index("ix_tasks_owner_id")
        batch.drop_column("prompt")
        batch.drop_column("repo_id")
        batch.drop_column("priority")
        batch.drop_column("owner_id")
    op.drop_table("auth_sessions")
    op.drop_table("users")
