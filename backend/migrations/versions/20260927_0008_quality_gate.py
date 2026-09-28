"""Add Phase 7 quality gate workflow.

Revision ID: 20260927_0008
Revises: 20260927_0007
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260927_0008"
down_revision = "20260927_0007"
branch_labels = None
depends_on = None

quality_workflow_status = postgresql.ENUM(
    "READY_FOR_REVIEW",
    "REVISION_REQUIRED",
    "PASSED",
    "MAX_REVISIONS_REACHED",
    name="quality_workflow_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    quality_workflow_status.create(bind, checkfirst=True)
    op.create_table(
        "quality_workflows",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", quality_workflow_status, nullable=False),
        sa.Column("revision_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_revisions", sa.Integer(), server_default="5", nullable=False),
        sa.Column("current_review_execution_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "reviewed_versions",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        sa.Column(
            "issues_json",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text("'[]'::jsonb"),
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["current_review_execution_id"], ["agent_executions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requirement_id", name="uq_quality_workflows_requirement_id"),
    )
    op.create_index("ix_quality_workflows_project_id", "quality_workflows", ["project_id"])
    op.create_index(
        "ix_quality_workflows_requirement_id", "quality_workflows", ["requirement_id"]
    )
    op.create_index("ix_quality_workflows_status", "quality_workflows", ["status"])


def downgrade() -> None:
    op.drop_index("ix_quality_workflows_status", table_name="quality_workflows")
    op.drop_index("ix_quality_workflows_requirement_id", table_name="quality_workflows")
    op.drop_index("ix_quality_workflows_project_id", table_name="quality_workflows")
    op.drop_table("quality_workflows")
    quality_workflow_status.drop(op.get_bind(), checkfirst=True)
