"""Establish the Phase 0.5 migration baseline.

Revision ID: 20260927_0001
Revises:
Create Date: 2026-09-27
"""

revision = "20260927_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """No product tables are introduced before Phase 1."""


def downgrade() -> None:
    """The empty baseline has no schema operations to reverse."""

