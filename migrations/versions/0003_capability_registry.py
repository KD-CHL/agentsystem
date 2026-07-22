"""Add MCP, Skill, and per-Agent capability bindings.

Revision ID: 0003_capability_registry
Revises: 0002_identity_rbac
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0003_capability_registry"
down_revision = "0002_identity_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "mcp_servers",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.UniqueConstraint("tenant_id", "name", name="uq_mcp_servers_tenant_name"),
    )
    for column in ("tenant_id", "name", "created_at"):
        op.create_index(f"ix_mcp_servers_{column}", "mcp_servers", [column])

    op.create_table(
        "skills",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.UniqueConstraint("tenant_id", "source_path", name="uq_skills_tenant_path"),
    )
    for column in ("tenant_id", "name", "created_at"):
        op.create_index(f"ix_skills_{column}", "skills", [column])

    op.create_table(
        "agent_capability_bindings",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("tenant_id", sa.String(length=120), nullable=False),
        sa.Column("agent_name", sa.String(length=40), nullable=False),
        sa.Column("capability_kind", sa.String(length=40), nullable=False),
        sa.Column("capability_id", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "tenant_id",
            "agent_name",
            "capability_kind",
            "capability_id",
            name="uq_agent_capability_binding",
        ),
    )
    for column in ("tenant_id", "agent_name", "capability_kind", "capability_id", "created_at"):
        op.create_index(
            f"ix_agent_capability_bindings_{column}",
            "agent_capability_bindings",
            [column],
        )


def downgrade() -> None:
    op.drop_table("agent_capability_bindings")
    op.drop_table("skills")
    op.drop_table("mcp_servers")
