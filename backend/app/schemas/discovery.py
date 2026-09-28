from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from app.domain.discovery import ExistingEvidenceType
from app.schemas.artifact import ArtifactResponse


class RunResearchRequest(BaseModel):
    requirement_id: UUID


class ExistingEvidenceInput(BaseModel):
    source_type: ExistingEvidenceType
    title: str = Field(min_length=1, max_length=200)
    content: str = Field(min_length=1, max_length=200_000)

    @field_validator("title", "content", mode="before")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()


class AnalyzeExistingSystemRequest(BaseModel):
    requirement_id: UUID
    evidence: list[ExistingEvidenceInput] = Field(default_factory=list, max_length=50)


class SpecialistAnalysisResponse(BaseModel):
    execution_id: UUID
    artifact: ArtifactResponse
