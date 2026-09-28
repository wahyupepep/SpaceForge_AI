from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.projects import ProjectStatus, ProjectType


class ProjectContextInput(BaseModel):
    current_flow: Optional[str] = Field(default=None, max_length=100_000)
    current_actors: Optional[str] = Field(default=None, max_length=50_000)
    current_rules: Optional[str] = Field(default=None, max_length=100_000)
    current_problem: Optional[str] = Field(default=None, max_length=50_000)
    requested_change: Optional[str] = Field(default=None, max_length=50_000)
    constraints: Optional[str] = Field(default=None, max_length=50_000)
    notes: Optional[str] = Field(default=None, max_length=50_000)

    @field_validator("*", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip()
            return normalized or None
        return value


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=100_000)
    project_type: ProjectType
    business_objective: str = Field(min_length=1, max_length=50_000)
    context: ProjectContextInput = Field(default_factory=ProjectContextInput)

    @field_validator("name", "description", "business_objective", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, min_length=1, max_length=100_000)
    project_type: Optional[ProjectType] = None
    business_objective: Optional[str] = Field(
        default=None, min_length=1, max_length=50_000
    )
    context: Optional[ProjectContextInput] = None

    @field_validator("name", "description", "business_objective", mode="before")
    @classmethod
    def strip_optional_required_text(cls, value: Optional[str]) -> Optional[str]:
        return value.strip() if value is not None else value


class ProjectContextResponse(ProjectContextInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class ProjectResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    description: str
    project_type: ProjectType
    business_objective: str
    status: ProjectStatus
    owner_id: Optional[UUID]
    context: ProjectContextResponse
    missing_context_fields: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
