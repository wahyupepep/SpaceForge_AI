from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.orchestrator import (
    OrchestratorExecutionStatus,
    OrchestratorStage,
    OrchestratorStatus,
)


class OrchestratorWorkflow(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "orchestrator_workflows"
    __table_args__ = (
        UniqueConstraint("requirement_id", name="uq_orchestrator_workflows_requirement_id"),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    current_stage: Mapped[OrchestratorStage] = mapped_column(
        Enum(OrchestratorStage, name="orchestrator_stage"), nullable=False, index=True
    )
    status: Mapped[OrchestratorStatus] = mapped_column(
        Enum(OrchestratorStatus, name="orchestrator_status"), nullable=False, index=True
    )
    current_agent: Mapped[Optional[str]] = mapped_column(String(100))
    pending_user_action: Mapped[Optional[str]] = mapped_column(String(100))
    completed_stages: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    artifact_status: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    revision_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    last_error: Mapped[Optional[str]] = mapped_column(Text)
    active_run_id: Mapped[Optional[UUID]] = mapped_column(PostgreSQLUUID(as_uuid=True))
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    executions: Mapped[list[OrchestratorExecution]] = relationship(
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="OrchestratorExecution.started_at",
        lazy="selectin",
    )


class OrchestratorExecution(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "orchestrator_executions"
    __table_args__ = (
        Index(
            "ix_orchestrator_executions_workflow_started",
            "workflow_id",
            "started_at",
        ),
    )

    workflow_id: Mapped[UUID] = mapped_column(
        ForeignKey("orchestrator_workflows.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stage: Mapped[OrchestratorStage] = mapped_column(
        Enum(OrchestratorStage, name="orchestrator_stage", create_type=False),
        nullable=False,
        index=True,
    )
    agent_name: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[OrchestratorExecutionStatus] = mapped_column(
        Enum(OrchestratorExecutionStatus, name="orchestrator_execution_status"),
        nullable=False,
        index=True,
    )
    input_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output_json: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    workflow: Mapped[OrchestratorWorkflow] = relationship(back_populates="executions")
