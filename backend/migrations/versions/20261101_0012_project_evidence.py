"""Add persistent project evidence for existing-system analysis.

Revision ID: 20261101_0012
Revises: 20260928_0011
Create Date: 2026-11-01
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20261101_0012"
down_revision = "20260928_0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "project_evidence",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("storage_key", sa.String(length=500), nullable=False),
        sa.Column("content_type", sa.String(length=150), nullable=False),
        sa.Column("size_bytes", sa.BigInteger(), nullable=False),
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
        sa.UniqueConstraint("storage_key"),
    )
    op.create_index("ix_project_evidence_project_id", "project_evidence", ["project_id"])
    op.create_index("ix_project_evidence_category", "project_evidence", ["category"])


def downgrade() -> None:
    op.drop_index("ix_project_evidence_category", table_name="project_evidence")
    op.drop_index("ix_project_evidence_project_id", table_name="project_evidence")
    op.drop_table("project_evidence")
