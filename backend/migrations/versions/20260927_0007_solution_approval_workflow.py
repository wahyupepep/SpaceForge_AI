"""Add Solution Analyst approval workflow.

Revision ID: 20260927_0007
Revises: 20260927_0006
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260927_0007"
down_revision = "20260927_0006"
branch_labels = None
depends_on = None

solution_workflow_status = postgresql.ENUM(
    "WAITING_USER_APPROVAL",
    "REVISION_REQUESTED",
    "APPROVED",
    "REJECTED",
    name="solution_workflow_status",
    create_type=False,
)
solution_approval_action = postgresql.ENUM(
    "APPROVE",
    "REQUEST_REVISION",
    "REJECT",
    name="solution_approval_action",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    solution_workflow_status.create(bind, checkfirst=True)
    solution_approval_action.create(bind, checkfirst=True)

    op.create_table(
        "solution_workflows",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("solution_artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_artifact_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", solution_workflow_status, nullable=False),
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
        sa.ForeignKeyConstraint(["solution_artifact_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["current_artifact_version_id"], ["artifact_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("requirement_id", name="uq_solution_workflows_requirement_id"),
        sa.UniqueConstraint("solution_artifact_id"),
    )
    op.create_index("ix_solution_workflows_project_id", "solution_workflows", ["project_id"])
    op.create_index(
        "ix_solution_workflows_requirement_id", "solution_workflows", ["requirement_id"]
    )
    op.create_index("ix_solution_workflows_status", "solution_workflows", ["status"])

    op.create_table(
        "solution_approvals",
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("artifact_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", solution_approval_action, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("acted_by", sa.String(length=100), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["solution_workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requirement_id"], ["requirements.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["artifact_version_id"], ["artifact_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_solution_approvals_workflow_id", "solution_approvals", ["workflow_id"])
    op.create_index("ix_solution_approvals_project_id", "solution_approvals", ["project_id"])
    op.create_index(
        "ix_solution_approvals_requirement_id", "solution_approvals", ["requirement_id"]
    )
    op.create_index(
        "ix_solution_approvals_artifact_version_id", "solution_approvals", ["artifact_version_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_solution_approvals_artifact_version_id", table_name="solution_approvals")
    op.drop_index("ix_solution_approvals_requirement_id", table_name="solution_approvals")
    op.drop_index("ix_solution_approvals_project_id", table_name="solution_approvals")
    op.drop_index("ix_solution_approvals_workflow_id", table_name="solution_approvals")
    op.drop_table("solution_approvals")
    op.drop_index("ix_solution_workflows_status", table_name="solution_workflows")
    op.drop_index("ix_solution_workflows_requirement_id", table_name="solution_workflows")
    op.drop_index("ix_solution_workflows_project_id", table_name="solution_workflows")
    op.drop_table("solution_workflows")
    bind = op.get_bind()
    solution_approval_action.drop(bind, checkfirst=True)
    solution_workflow_status.drop(bind, checkfirst=True)
