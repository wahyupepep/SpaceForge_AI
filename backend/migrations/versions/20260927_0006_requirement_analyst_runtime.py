"""Add Requirement Analyst runtime and audit trail.

Revision ID: 20260927_0006
Revises: 20260927_0005
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260927_0006"
down_revision = "20260927_0005"
branch_labels = None
depends_on = None

requirement_readiness = postgresql.ENUM(
    "READY",
    "NEEDS_CLARIFICATION",
    "BLOCKED",
    name="requirement_readiness",
    create_type=False,
)
agent_execution_status = postgresql.ENUM(
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    name="agent_execution_status",
    create_type=False,
)
clarification_status = postgresql.ENUM(
    "PENDING", "ANSWERED", name="clarification_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    requirement_readiness.create(bind, checkfirst=True)
    agent_execution_status.create(bind, checkfirst=True)
    clarification_status.create(bind, checkfirst=True)

    op.add_column(
        "requirements",
        sa.Column("analysis_readiness", requirement_readiness, nullable=True),
    )
    op.create_index(
        "ix_requirements_analysis_readiness", "requirements", ["analysis_readiness"]
    )

    op.create_table(
        "agent_executions",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_version_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("agent_name", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("status", agent_execution_status, nullable=False),
        sa.Column("request_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("response_json", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("provider_response_id", sa.String(length=200), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["requirement_id"], ["requirements.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["artifact_version_id"], ["artifact_versions.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_agent_executions_project_id", "agent_executions", ["project_id"])
    op.create_index(
        "ix_agent_executions_requirement_id", "agent_executions", ["requirement_id"]
    )
    op.create_index(
        "ix_agent_executions_artifact_version_id",
        "agent_executions",
        ["artifact_version_id"],
    )
    op.create_index("ix_agent_executions_status", "agent_executions", ["status"])

    op.create_table(
        "requirement_clarifications",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("agent_execution_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=True),
        sa.Column("status", clarification_status, nullable=False),
        sa.Column("answered_by", sa.String(length=100), nullable=True),
        sa.Column("answered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["requirement_id"], ["requirements.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["agent_execution_id"], ["agent_executions.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_requirement_clarifications_project_id",
        "requirement_clarifications",
        ["project_id"],
    )
    op.create_index(
        "ix_requirement_clarifications_requirement_id",
        "requirement_clarifications",
        ["requirement_id"],
    )
    op.create_index(
        "ix_requirement_clarifications_agent_execution_id",
        "requirement_clarifications",
        ["agent_execution_id"],
    )
    op.create_index(
        "ix_requirement_clarifications_status",
        "requirement_clarifications",
        ["status"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_requirement_clarifications_status",
        table_name="requirement_clarifications",
    )
    op.drop_index(
        "ix_requirement_clarifications_agent_execution_id",
        table_name="requirement_clarifications",
    )
    op.drop_index(
        "ix_requirement_clarifications_requirement_id",
        table_name="requirement_clarifications",
    )
    op.drop_index(
        "ix_requirement_clarifications_project_id",
        table_name="requirement_clarifications",
    )
    op.drop_table("requirement_clarifications")
    op.drop_index("ix_agent_executions_status", table_name="agent_executions")
    op.drop_index(
        "ix_agent_executions_artifact_version_id", table_name="agent_executions"
    )
    op.drop_index("ix_agent_executions_requirement_id", table_name="agent_executions")
    op.drop_index("ix_agent_executions_project_id", table_name="agent_executions")
    op.drop_table("agent_executions")
    op.drop_index("ix_requirements_analysis_readiness", table_name="requirements")
    op.drop_column("requirements", "analysis_readiness")

    bind = op.get_bind()
    clarification_status.drop(bind, checkfirst=True)
    agent_execution_status.drop(bind, checkfirst=True)
    requirement_readiness.drop(bind, checkfirst=True)
