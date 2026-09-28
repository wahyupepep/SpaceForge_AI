"""Add Development Handoff workflow and package versions.

Revision ID: 20260928_0009
Revises: 20260927_0008
Create Date: 2026-09-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260928_0009"
down_revision = "20260927_0008"
branch_labels = None
depends_on = None

handoff_workflow_status = postgresql.ENUM(
    "TASKS_READY",
    "PACKAGE_READY",
    name="handoff_workflow_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    handoff_workflow_status.create(bind, checkfirst=True)
    op.create_table(
        "handoff_workflows",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("development_task_artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_task_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", handoff_workflow_status, nullable=False),
        sa.Column("current_package_version", sa.Integer(), server_default="0", nullable=False),
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
            ["development_task_artifact_id"], ["artifacts.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["current_task_version_id"], ["artifact_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "development_task_artifact_id",
            name="uq_handoff_workflows_development_task_artifact_id",
        ),
        sa.UniqueConstraint("requirement_id", name="uq_handoff_workflows_requirement_id"),
    )
    op.create_index("ix_handoff_workflows_project_id", "handoff_workflows", ["project_id"])
    op.create_index(
        "ix_handoff_workflows_requirement_id", "handoff_workflows", ["requirement_id"]
    )
    op.create_index("ix_handoff_workflows_status", "handoff_workflows", ["status"])

    op.create_table(
        "handoff_package_versions",
        sa.Column("workflow_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("development_task_version_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("source_versions", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("json_storage_key", sa.String(length=1000), nullable=False),
        sa.Column("markdown_storage_key", sa.String(length=1000), nullable=False),
        sa.Column("trello_storage_key", sa.String(length=1000), nullable=False),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["workflow_id"], ["handoff_workflows.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["development_task_version_id"], ["artifact_versions.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workflow_id", "version", name="uq_handoff_package_versions_workflow_version"
        ),
    )
    op.create_index(
        "ix_handoff_package_versions_workflow_id",
        "handoff_package_versions",
        ["workflow_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_handoff_package_versions_workflow_id", table_name="handoff_package_versions"
    )
    op.drop_table("handoff_package_versions")
    op.drop_index("ix_handoff_workflows_status", table_name="handoff_workflows")
    op.drop_index("ix_handoff_workflows_requirement_id", table_name="handoff_workflows")
    op.drop_index("ix_handoff_workflows_project_id", table_name="handoff_workflows")
    op.drop_table("handoff_workflows")
    handoff_workflow_status.drop(op.get_bind(), checkfirst=True)
