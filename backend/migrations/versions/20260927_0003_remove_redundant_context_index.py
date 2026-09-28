"""Remove redundant project context foreign-key index.

Revision ID: 20260927_0003
Revises: 20260927_0002
Create Date: 2026-09-27
"""

from alembic import op

revision = "20260927_0003"
down_revision = "20260927_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("ix_project_contexts_project_id", table_name="project_contexts")


def downgrade() -> None:
    op.create_index(
        "ix_project_contexts_project_id",
        "project_contexts",
        ["project_id"],
        unique=False,
    )

