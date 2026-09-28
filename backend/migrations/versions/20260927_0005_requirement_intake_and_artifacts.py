"""Add requirement intake and versioned artifacts.

Revision ID: 20260927_0005
Revises: 20260927_0004
Create Date: 2026-09-27
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "20260927_0005"
down_revision = "20260927_0004"
branch_labels = None
depends_on = None

requirement_status = postgresql.ENUM(
    "DRAFT", "BASELINED", name="requirement_status", create_type=False
)
artifact_type = postgresql.ENUM(
    "PROJECT_CONTEXT",
    "REQUIREMENT_BASELINE",
    "RESEARCH",
    "EXISTING_SYSTEM_ANALYSIS",
    "SOLUTION",
    "PROCESS_FLOW",
    "UI_PROTOTYPE",
    "DATABASE_DESIGN",
    "API_SPECIFICATION",
    "TEST_SCENARIO",
    "ACCEPTANCE_CRITERIA",
    "DEVELOPMENT_TASK",
    name="artifact_type",
    create_type=False,
)
artifact_status = postgresql.ENUM(
    "DRAFT", "VALIDATED", name="artifact_status", create_type=False
)


def upgrade() -> None:
    bind = op.get_bind()
    requirement_status.create(bind, checkfirst=True)
    artifact_type.create(bind, checkfirst=True)
    artifact_status.create(bind, checkfirst=True)

    op.create_table(
        "requirements",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("raw_requirement", sa.Text(), nullable=False),
        sa.Column("business_objective", sa.Text(), nullable=True),
        sa.Column(
            "actors", postgresql.JSONB(astext_type=sa.Text()), server_default="[]", nullable=False
        ),
        sa.Column(
            "known_rules",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "constraints",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column(
            "dependencies",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
        sa.Column("status", requirement_status, nullable=False),
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
    )
    op.create_index("ix_requirements_project_id", "requirements", ["project_id"])
    op.create_index("ix_requirements_status", "requirements", ["status"])

    op.create_table(
        "artifacts",
        sa.Column("project_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("requirement_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("artifact_type", artifact_type, nullable=False),
        sa.Column("current_version", sa.Integer(), nullable=False),
        sa.Column("status", artifact_status, nullable=False),
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
            ["requirement_id"], ["requirements.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_artifacts_project_id", "artifacts", ["project_id"])
    op.create_index("ix_artifacts_requirement_id", "artifacts", ["requirement_id"])
    op.create_index("ix_artifacts_artifact_type", "artifacts", ["artifact_type"])
    op.create_index("ix_artifacts_status", "artifacts", ["status"])

    op.create_table(
        "artifact_versions",
        sa.Column("artifact_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_json", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.String(length=100), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(["artifact_id"], ["artifacts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "artifact_id", "version", name="uq_artifact_versions_artifact_version"
        ),
    )
    op.create_index("ix_artifact_versions_artifact_id", "artifact_versions", ["artifact_id"])


def downgrade() -> None:
    op.drop_index("ix_artifact_versions_artifact_id", table_name="artifact_versions")
    op.drop_table("artifact_versions")
    op.drop_index("ix_artifacts_status", table_name="artifacts")
    op.drop_index("ix_artifacts_artifact_type", table_name="artifacts")
    op.drop_index("ix_artifacts_requirement_id", table_name="artifacts")
    op.drop_index("ix_artifacts_project_id", table_name="artifacts")
    op.drop_table("artifacts")
    op.drop_index("ix_requirements_status", table_name="requirements")
    op.drop_index("ix_requirements_project_id", table_name="requirements")
    op.drop_table("requirements")

    bind = op.get_bind()
    artifact_status.drop(bind, checkfirst=True)
    artifact_type.drop(bind, checkfirst=True)
    requirement_status.drop(bind, checkfirst=True)
