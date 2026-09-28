from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.analysis import AgentExecutionStatus, ClarificationStatus, RequirementReadiness
from app.schemas.artifact import ArtifactResponse
from app.schemas.requirement import RequirementResponse


class AnalyzeRequirementRequest(BaseModel):
    requirement_id: UUID


class ClarificationAnswerInput(BaseModel):
    clarification_id: UUID
    answer: str = Field(min_length=1)

    @field_validator("answer", mode="before")
    @classmethod
    def strip_answer(cls, value: str) -> str:
        return value.strip()


class AnswerClarificationsRequest(BaseModel):
    answers: list[ClarificationAnswerInput] = Field(min_length=1)
    answered_by: str = Field(default="USER", min_length=1, max_length=100)


class ClarificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    requirement_id: UUID
    agent_execution_id: UUID
    question: str
    answer: Optional[str]
    status: ClarificationStatus
    answered_by: Optional[str]
    answered_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class AgentExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    requirement_id: UUID
    artifact_version_id: Optional[UUID]
    agent_name: str
    model: str
    status: AgentExecutionStatus
    request_json: dict
    response_json: Optional[dict]
    provider_response_id: Optional[str]
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    total_tokens: Optional[int]
    duration_ms: Optional[int]
    error_message: Optional[str]
    created_at: datetime
    updated_at: datetime


class RequirementAnalysisResponse(BaseModel):
    execution_id: UUID
    readiness: RequirementReadiness
    requirement: RequirementResponse
    artifact: ArtifactResponse
    clarifications: list[ClarificationResponse]
