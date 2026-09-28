from __future__ import annotations

from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.domain.projects import ProjectStatus, ProjectType

if TYPE_CHECKING:
    from app.models.artifact import Artifact
    from app.models.requirement import Requirement


class Project(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    project_type: Mapped[ProjectType] = mapped_column(
        Enum(ProjectType, name="project_type"), nullable=False, index=True
    )
    business_objective: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
        Enum(ProjectStatus, name="project_status"),
        nullable=False,
        default=ProjectStatus.DRAFT,
        index=True,
    )
    owner_id: Mapped[Optional[UUID]] = mapped_column(
        PostgreSQLUUID(as_uuid=True), nullable=True, index=True
    )

    context: Mapped[ProjectContext] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
        lazy="selectin",
    )
    requirements: Mapped[list[Requirement]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="project", cascade="all, delete-orphan"
    )


class ProjectContext(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "project_contexts"

    project_id: Mapped[UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    current_flow: Mapped[Optional[str]] = mapped_column(Text)
    current_actors: Mapped[Optional[str]] = mapped_column(Text)
    current_rules: Mapped[Optional[str]] = mapped_column(Text)
    current_problem: Mapped[Optional[str]] = mapped_column(Text)
    requested_change: Mapped[Optional[str]] = mapped_column(Text)
    constraints: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    project: Mapped[Project] = relationship(back_populates="context")
