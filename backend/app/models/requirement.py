from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.analysis import RequirementReadiness
from app.domain.requirements import RequirementStatus

if TYPE_CHECKING:
    from app.models.artifact import Artifact
    from app.models.project import Project


class Requirement(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "requirements"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_requirement: Mapped[str] = mapped_column(Text, nullable=False)
    business_objective: Mapped[Optional[str]] = mapped_column(Text)
    actors: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    known_rules: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    constraints: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    dependencies: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[RequirementStatus] = mapped_column(
        Enum(RequirementStatus, name="requirement_status"),
        nullable=False,
        default=RequirementStatus.DRAFT,
        index=True,
    )
    analysis_readiness: Mapped[Optional[RequirementReadiness]] = mapped_column(
        Enum(RequirementReadiness, name="requirement_readiness"), nullable=True, index=True
    )

    project: Mapped[Project] = relationship(back_populates="requirements")
    artifacts: Mapped[list[Artifact]] = relationship(back_populates="requirement")
