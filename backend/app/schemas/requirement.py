from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.analysis import RequirementReadiness
from app.domain.requirements import RequirementStatus


class RequirementInput(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    raw_requirement: str = Field(min_length=1, max_length=100_000)
    business_objective: Optional[str] = Field(default=None, max_length=50_000)
    actors: list[str] = Field(default_factory=list, max_length=500)
    known_rules: list[str] = Field(default_factory=list, max_length=1000)
    constraints: list[str] = Field(default_factory=list, max_length=1000)
    dependencies: list[str] = Field(default_factory=list, max_length=1000)

    @field_validator("title", "raw_requirement", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip()

    @field_validator("business_objective", mode="before")
    @classmethod
    def normalize_optional_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("actors", "known_rules", "constraints", "dependencies", mode="before")
    @classmethod
    def normalize_lists(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


class RequirementCreate(RequirementInput):
    pass


class RequirementUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    raw_requirement: Optional[str] = Field(default=None, min_length=1, max_length=100_000)
    business_objective: Optional[str] = Field(default=None, max_length=50_000)
    actors: Optional[list[str]] = Field(default=None, max_length=500)
    known_rules: Optional[list[str]] = Field(default=None, max_length=1000)
    constraints: Optional[list[str]] = Field(default=None, max_length=1000)
    dependencies: Optional[list[str]] = Field(default=None, max_length=1000)

    @field_validator("title", "raw_requirement", "business_objective", mode="before")
    @classmethod
    def normalize_text(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip() or None
        return value

    @field_validator("actors", "known_rules", "constraints", "dependencies", mode="before")
    @classmethod
    def normalize_lists(cls, value: object) -> object:
        if not isinstance(value, list):
            return value
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]


class RequirementResponse(RequirementInput):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    status: RequirementStatus
    analysis_readiness: Optional[RequirementReadiness] = None
    created_at: datetime
    updated_at: datetime
