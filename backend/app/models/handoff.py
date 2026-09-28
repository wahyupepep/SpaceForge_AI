from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.handoff import HandoffWorkflowStatus


class HandoffWorkflow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "handoff_workflows"
    __table_args__ = (
        UniqueConstraint("requirement_id", name="uq_handoff_workflows_requirement_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    development_task_artifact_id: Mapped[UUID] = mapped_column(
        ForeignKey("artifacts.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    current_task_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[HandoffWorkflowStatus] = mapped_column(
        Enum(HandoffWorkflowStatus, name="handoff_workflow_status"),
        nullable=False,
        index=True,
    )
    current_package_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    packages: Mapped[list[HandoffPackageVersion]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="HandoffPackageVersion.version",
        lazy="selectin",
    )


class HandoffPackageVersion(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "handoff_package_versions"
    __table_args__ = (
        UniqueConstraint(
            "workflow_id", "version", name="uq_handoff_package_versions_workflow_version"
        ),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("handoff_workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    development_task_version_id: Mapped[UUID] = mapped_column(
        ForeignKey("artifact_versions.id", ondelete="RESTRICT"), nullable=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    source_versions: Mapped[dict] = mapped_column(JSONB, nullable=False)
    content_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    json_storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    markdown_storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    trello_storage_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    workflow: Mapped[HandoffWorkflow] = relationship(back_populates="packages")
