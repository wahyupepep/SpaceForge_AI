"""Add workflow concurrency, LLM duration, and artifact uniqueness guards.

Revision ID: 20260928_0011
Revises: 20260928_0010
Create Date: 2026-09-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260928_0011"
down_revision = "20260928_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("agent_executions", sa.Column("duration_ms", sa.Integer(), nullable=True))
    op.add_column(
        "orchestrator_workflows",
        sa.Column("active_run_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "orchestrator_workflows",
        sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_unique_constraint(
        "uq_artifacts_project_requirement_type",
        "artifacts",
        ["project_id", "requirement_id", "artifact_type"],
    )
    op.create_index(
        "uq_artifacts_project_type_without_requirement",
        "artifacts",
        ["project_id", "artifact_type"],
        unique=True,
        postgresql_where=sa.text("requirement_id IS NULL"),
    )
    op.create_index(
        "ix_agent_executions_project_requirement_created",
        "agent_executions",
        ["project_id", "requirement_id", "created_at"],
    )
    op.create_index(
        "ix_orchestrator_executions_workflow_started",
        "orchestrator_executions",
        ["workflow_id", "started_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_orchestrator_executions_workflow_started",
        table_name="orchestrator_executions",
    )
    op.drop_index(
        "ix_agent_executions_project_requirement_created",
        table_name="agent_executions",
    )
    op.drop_index(
        "uq_artifacts_project_type_without_requirement",
        table_name="artifacts",
    )
    op.drop_constraint(
        "uq_artifacts_project_requirement_type", "artifacts", type_="unique"
    )
    op.drop_column("orchestrator_workflows", "lease_expires_at")
    op.drop_column("orchestrator_workflows", "active_run_id")
    op.drop_column("agent_executions", "duration_ms")
