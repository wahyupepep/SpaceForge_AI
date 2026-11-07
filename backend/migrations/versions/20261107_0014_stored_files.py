"""Store small uploads and generated files durably on serverless deployments."""

import sqlalchemy as sa
from alembic import op

revision = "20261107_0014"
down_revision = "20261101_0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stored_files",
        sa.Column("key", sa.String(500), primary_key=True),
        sa.Column("content", sa.LargeBinary(), nullable=False),
        sa.Column("content_type", sa.String(150), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )


def downgrade() -> None:
    op.drop_table("stored_files")
