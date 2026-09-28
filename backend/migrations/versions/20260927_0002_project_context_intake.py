"""Add project context intake tables.

Revision ID: 20260927_0002
Revises: 20260927_0001
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260927_0002"
down_revision = "20260927_0001"
branch_labels = None
depends_on = None

project_type = postgresql.ENUM(
    "NEW_SYSTEM", "NEW_FEATURE", "ENHANCEMENT", name="project_type", create_type=False
)
project_status = postgresql.ENUM(
    "DRAFT",
    "CONTEXT_INCOMPLETE",
    "READY_FOR_ANALYSIS",
    name="project_status",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    project_type.create(bind, checkfirst=True)
    project_status.create(bind, checkfirst=True)

    op.create_table(
        "projects",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("project_type", project_type, nullable=False),
        sa.Column("business_objective", sa.Text(), nullable=False),
        sa.Column("status", project_status, nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_projects_name", "projects", ["name"])
    op.create_index("ix_projects_project_type", "projects", ["project_type"])
    op.create_index("ix_projects_status", "projects", ["status"])

    op.create_table(
        "project_contexts",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("current_flow", sa.Text(), nullable=True),
        sa.Column("current_actors", sa.Text(), nullable=True),
        sa.Column("current_rules", sa.Text(), nullable=True),
        sa.Column("current_problem", sa.Text(), nullable=True),
        sa.Column("requested_change", sa.Text(), nullable=True),
        sa.Column("constraints", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id"),
    )
    op.create_index("ix_project_contexts_project_id", "project_contexts", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_project_contexts_project_id", table_name="project_contexts")
    op.drop_table("project_contexts")
    op.drop_index("ix_projects_status", table_name="projects")
    op.drop_index("ix_projects_project_type", table_name="projects")
    op.drop_index("ix_projects_name", table_name="projects")
    op.drop_table("projects")

    bind = op.get_bind()
    project_status.drop(bind, checkfirst=True)
    project_type.drop(bind, checkfirst=True)
