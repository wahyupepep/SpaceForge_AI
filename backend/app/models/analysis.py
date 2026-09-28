from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.analysis import AgentExecutionStatus, ClarificationStatus


class AgentExecution(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "agent_executions"
    __table_args__ = (
        Index(
            "ix_agent_executions_project_requirement_created",
            "project_id",
            "requirement_id",
            "created_at",
        ),
    )

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    artifact_version_id: Mapped[Optional[UUID]] = mapped_column(
        ForeignKey("artifact_versions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    agent_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[AgentExecutionStatus] = mapped_column(
        Enum(AgentExecutionStatus, name="agent_execution_status"),
        nullable=False,
        index=True,
    )
    request_json: Mapped[dict] = mapped_column(JSONB, nullable=False)
    response_json: Mapped[Optional[dict]] = mapped_column(JSONB)
    provider_response_id: Mapped[Optional[str]] = mapped_column(String(200))
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    total_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    error_message: Mapped[Optional[str]] = mapped_column(Text)


class RequirementClarification(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "requirement_clarifications"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    requirement_id: Mapped[UUID] = mapped_column(
        ForeignKey("requirements.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_execution_id: Mapped[UUID] = mapped_column(
        ForeignKey("agent_executions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[Optional[str]] = mapped_column(Text)
    status: Mapped[ClarificationStatus] = mapped_column(
        Enum(ClarificationStatus, name="clarification_status"),
        nullable=False,
        default=ClarificationStatus.PENDING,
        index=True,
    )
    answered_by: Mapped[Optional[str]] = mapped_column(String(100))
    answered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
