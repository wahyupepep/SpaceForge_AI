from __future__ import annotations

from typing import Optional
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.quality import QualityWorkflowStatus


class QualityWorkflow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "quality_workflows"
    __table_args__ = (
        UniqueConstraint("requirement_id", name="uq_quality_workflows_requirement_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[QualityWorkflowStatus] = mapped_column(
        Enum(QualityWorkflowStatus, name="quality_workflow_status"),
        nullable=False,
        index=True,
    )
    revision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_revisions: Mapped[int] = mapped_column(Integer, nullable=False, default=5)
    current_review_execution_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("agent_executions.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_versions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    issues_json: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
