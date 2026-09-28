from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.solution import SolutionApprovalAction, SolutionWorkflowStatus


class SolutionWorkflow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "solution_workflows"
    __table_args__ = (
        UniqueConstraint("requirement_id", name="uq_solution_workflows_requirement_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    solution_artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    current_artifact_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[SolutionWorkflowStatus] = mapped_column(
        Enum(SolutionWorkflowStatus, name="solution_workflow_status"),
        nullable=False,
        index=True,
    )

    approvals: Mapped[list[SolutionApproval]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="SolutionApproval.created_at",
        lazy="selectin",
    )


class SolutionApproval(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "solution_approvals"

    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("solution_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    action: Mapped[SolutionApprovalAction] = mapped_column(
        Enum(SolutionApprovalAction, name="solution_approval_action"), nullable=False
    )
    note: Mapped[Optional[str]] = mapped_column(Text)
    acted_by: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    workflow: Mapped[SolutionWorkflow] = relationship(back_populates="approvals")
