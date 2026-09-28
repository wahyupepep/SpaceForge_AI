"""Add resumable SA orchestrator state and execution history.

Revision ID: 20260928_0010
Revises: 20260928_0009
Create Date: 2026-09-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260928_0010"
down_revision = "20260928_0009"
branch_labels = None
depends_on = None

orchestrator_stage = postgresql.ENUM(
    "PROJECT_CONTEXT",
    "REQUIREMENT_ANALYSIS",
    "CLARIFICATION",
    "REQUIREMENT_READY",
    "RESEARCH",
    "EXISTING_SYSTEM_ANALYSIS",
    "SOLUTION_DESIGN",
    "USER_APPROVAL",
    "FLOW_UI_TECHNICAL_DESIGN",
    "QA",
    "SA_REVIEW",
    "REVISION_LOOP",
    "HANDOFF_READY",
    "COMPLETED",
    name="orchestrator_stage",
    create_type=False,
)
orchestrator_status = postgresql.ENUM(
    "ACTIVE",
    "WAITING_USER_ACTION",
    "FAILED",
    "COMPLETED",
    name="orchestrator_status",
    create_type=False,
)
orchestrator_execution_status = postgresql.ENUM(
    "RUNNING",
    "SUCCEEDED",
    "WAITING",
    "FAILED",
    name="orchestrator_execution_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    orchestrator_stage.create(bind, checkfirst=True)
    orchestrator_status.create(bind, checkfirst=True)
    orchestrator_execution_status.create(bind, checkfirst=True)
    op.create_table(
        "orchestrator_workflows",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_stage", orchestrator_stage, nullable=False),
        sa.Column("status", orchestrator_status, nullable=False),
        sa.Column("current_agent", sa.String(length=100), nullable=True),
        sa.Column("pending_user_action", sa.String(length=100), nullable=True),
        sa.Column("completed_stages", postgresql.JSONB(), nullable=False),
        sa.Column("artifact_status", postgresql.JSONB(), nullable=False),
        sa.Column("revision_history", postgresql.JSONB(), nullable=False),
        sa.Column("state_json", postgresql.JSONB(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
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
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requirement_id", name="uq_orchestrator_workflows_requirement_id"),
    )
    op.create_index(
        "ix_orchestrator_workflows_project_id", "orchestrator_workflows", ["project_id"]
    )
    op.create_index(
        "ix_orchestrator_workflows_requirement_id",
        "orchestrator_workflows",
        ["requirement_id"],
    )
    op.create_index(
        "ix_orchestrator_workflows_current_stage",
        "orchestrator_workflows",
        ["current_stage"],
    )
    op.create_index("ix_orchestrator_workflows_status", "orchestrator_workflows", ["status"])
    op.create_table(
        "orchestrator_executions",
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("stage", orchestrator_stage, nullable=False),
        sa.Column("agent_name", sa.String(length=100), nullable=True),
        sa.Column("status", orchestrator_execution_status, nullable=False),
        sa.Column("input_json", postgresql.JSONB(), nullable=False),
        sa.Column("output_json", postgresql.JSONB(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["orchestrator_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_orchestrator_executions_workflow_id",
        "orchestrator_executions",
        ["workflow_id"],
    )
    op.create_index("ix_orchestrator_executions_stage", "orchestrator_executions", ["stage"])
    op.create_index("ix_orchestrator_executions_status", "orchestrator_executions", ["status"])


def downgrade() -> None:
    op.drop_table("orchestrator_executions")
    op.drop_table("orchestrator_workflows")
    orchestrator_execution_status.drop(op.get_bind(), checkfirst=True)
    orchestrator_status.drop(op.get_bind(), checkfirst=True)
    orchestrator_stage.drop(op.get_bind(), checkfirst=True)
