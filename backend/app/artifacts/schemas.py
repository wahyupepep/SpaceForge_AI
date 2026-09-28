from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain.analysis import RequirementReadiness
from app.domain.artifacts import ArtifactType
from app.domain.discovery import ChangeClassification, ExistingComponentType
from app.domain.handoff import DevelopmentWorkstream
from app.domain.quality import TestCategory
from app.domain.technical import APIChangeType, DatabaseChangeType, HTTPMethod


class ArtifactContent(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProjectContextContent(ArtifactContent):
    project_name: str
    project_type: str
    business_objective: str
    context: dict[str, Optional[str]]


class RequirementBaselineContent(ArtifactContent):
    feature: str = Field(min_length=1)
    business_objective: str = Field(min_length=1)
    problem_statement: str = Field(min_length=1)
    actors: list[str] = Field(default_factory=list)
    known_requirements: list[str] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    unknown_information: list[str] = Field(default_factory=list)
    readiness: RequirementReadiness = RequirementReadiness.READY
    clarification_questions: list[str] = Field(default_factory=list)
    blocked_reason: str = ""


class ResearchSourceContent(ArtifactContent):
    title: str
    url: str
    supports: str

    @field_validator("url")
    @classmethod
    def require_http_url(cls, value: str) -> str:
        if urlparse(value).scheme not in {"http", "https"}:
            raise ValueError("Research source URL must use HTTP or HTTPS.")
        return value


class ResearchContent(ArtifactContent):
    objective: str
    common_practices: list[str] = Field(default_factory=list)
    comparable_workflows: list[str] = Field(default_factory=list)
    common_metadata: list[str] = Field(default_factory=list)
    ux_patterns: list[str] = Field(default_factory=list)
    technical_considerations: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    sources: list[ResearchSourceContent] = Field(default_factory=list)
    open_questions: list[str] = Field(default_factory=list)


class ExistingComponentContent(ArtifactContent):
    name: str
    component_type: ExistingComponentType
    classification: ChangeClassification
    evidence: str
    rationale: str
    impact: str


class GapAnalysisContent(ArtifactContent):
    area: str
    current_state: str
    required_state: str
    gap: str


class ExistingSystemAnalysisContent(ArtifactContent):
    as_is_summary: str
    components: list[ExistingComponentContent] = Field(default_factory=list)
    affected_components: list[str] = Field(default_factory=list)
    gap_analysis: list[GapAnalysisContent] = Field(default_factory=list)
    regression_risks: list[str] = Field(default_factory=list)
    unknown_information: list[str] = Field(default_factory=list)


class SolutionContent(ArtifactContent):
    summary: str = Field(min_length=1)
    scope: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    actors: list[str] = Field(default_factory=list)
    functional_requirements: list[str] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list)
    proposed_process: list[str] = Field(default_factory=list)
    alternative_flow: list[str] = Field(default_factory=list)
    exception_flow: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    integration_requirements: list[str] = Field(default_factory=list)
    data_requirements: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    as_is: list[str] = Field(default_factory=list)
    gap: list[str] = Field(default_factory=list)
    to_be: list[str] = Field(default_factory=list)


class FlowStepContent(ArtifactContent):
    step_id: str
    actor: str
    action: str
    outcome: str
    requirement_refs: list[str] = Field(default_factory=list)


class FlowVariantContent(ArtifactContent):
    name: str
    trigger: str
    steps: list[FlowStepContent] = Field(default_factory=list)


class StateTransitionContent(ArtifactContent):
    from_state: str
    event: str
    to_state: str
    condition: Optional[str] = None


class ProcessFlowContent(ArtifactContent):
    name: str
    mermaid: str = ""
    main_flow: list[FlowStepContent] = Field(default_factory=list)
    alternative_flows: list[FlowVariantContent] = Field(default_factory=list)
    exception_flows: list[FlowVariantContent] = Field(default_factory=list)
    state_transitions: list[StateTransitionContent] = Field(default_factory=list)
    requirement_traceability: list[str] = Field(default_factory=list)


class PrototypeFileContent(ArtifactContent):
    filename: str
    title: str
    purpose: str
    storage_key: str
    content_type: str = "text/html"
    size_bytes: int
    requirement_refs: list[str] = Field(default_factory=list)


class UIPrototypeContent(ArtifactContent):
    summary: str = ""
    screens: list[PrototypeFileContent] = Field(default_factory=list)
    interactions: list[str] = Field(default_factory=list)
    requirement_traceability: list[str] = Field(default_factory=list)


class DatabaseFieldContent(ArtifactContent):
    name: str
    datatype: str
    primary_key: bool
    foreign_key: Optional[str] = None
    nullable: bool
    default: Optional[str] = None
    indexed: bool
    unique: bool
    description: str


class DatabaseEntityContent(ArtifactContent):
    entity: str
    table: str
    classification: DatabaseChangeType
    description: str
    fields: list[DatabaseFieldContent] = Field(default_factory=list)
    audit_fields: list[str] = Field(default_factory=list)
    requirement_refs: list[str] = Field(default_factory=list)


class DatabaseRelationshipContent(ArtifactContent):
    from_entity: str
    to_entity: str
    relationship_type: str
    foreign_key: str
    description: str


class DatabaseDesignContent(ArtifactContent):
    summary: str = ""
    entities: list[DatabaseEntityContent] = Field(default_factory=list)
    relationships: list[DatabaseRelationshipContent] = Field(default_factory=list)
    constraints: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    requirement_traceability: list[str] = Field(default_factory=list)


class APIFieldContent(ArtifactContent):
    name: str
    datatype: str
    required: bool
    description: str


class APIErrorContent(ArtifactContent):
    status_code: int
    code: str
    condition: str
    response_fields: list[APIFieldContent] = Field(default_factory=list)


class APIEndpointContent(ArtifactContent):
    method: HTTPMethod
    endpoint: str
    classification: APIChangeType
    purpose: str
    actor: str
    authorization: str
    request_fields: list[APIFieldContent] = Field(default_factory=list)
    response_fields: list[APIFieldContent] = Field(default_factory=list)
    validations: list[str] = Field(default_factory=list)
    business_rules: list[str] = Field(default_factory=list)
    error_responses: list[APIErrorContent] = Field(default_factory=list)
    requirement_refs: list[str] = Field(default_factory=list)


class APISpecificationContent(ArtifactContent):
    base_path: str
    authentication: str = ""
    endpoints: list[APIEndpointContent] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    requirement_traceability: list[str] = Field(default_factory=list)


class TestCaseContent(ArtifactContent):
    id: str = Field(min_length=1)
    category: TestCategory
    scenario: str = Field(min_length=1)
    precondition: str = Field(min_length=1)
    steps: list[str] = Field(default_factory=list)
    expected_result: str = Field(min_length=1)
    related_requirement: str = Field(min_length=1)


class TestScenarioContent(ArtifactContent):
    summary: str = ""
    test_cases: list[TestCaseContent] = Field(default_factory=list)
    requirement_traceability: list[str] = Field(default_factory=list)


class AcceptanceCriterionContent(ArtifactContent):
    id: str = Field(min_length=1)
    requirement_ref: str = Field(min_length=1)
    given: str = Field(min_length=1)
    when: str = Field(min_length=1)
    then: str = Field(min_length=1)


class AcceptanceCriteriaContent(ArtifactContent):
    criteria: list[AcceptanceCriterionContent] = Field(default_factory=list)
    requirement_traceability: list[str] = Field(default_factory=list)


class DevelopmentTaskItemContent(ArtifactContent):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    workstream: DevelopmentWorkstream
    objective: str = Field(min_length=1)
    scope: list[str] = Field(default_factory=list)
    requirement: str = Field(min_length=1)
    technical_notes: list[str] = Field(default_factory=list)
    dependency: list[str] = Field(default_factory=list)
    acceptance_criteria: list[str] = Field(default_factory=list)
    reference_artifact: list[ArtifactType] = Field(default_factory=list)


class DevelopmentTaskContent(ArtifactContent):
    summary: str = ""
    tasks: list[DevelopmentTaskItemContent] = Field(default_factory=list)
    execution_order: list[str] = Field(default_factory=list)
    traceability: list[str] = Field(default_factory=list)


ARTIFACT_SCHEMA_REGISTRY: dict[ArtifactType, type[ArtifactContent]] = {
    ArtifactType.PROJECT_CONTEXT: ProjectContextContent,
    ArtifactType.REQUIREMENT_BASELINE: RequirementBaselineContent,
    ArtifactType.RESEARCH: ResearchContent,
    ArtifactType.EXISTING_SYSTEM_ANALYSIS: ExistingSystemAnalysisContent,
    ArtifactType.SOLUTION: SolutionContent,
    ArtifactType.PROCESS_FLOW: ProcessFlowContent,
    ArtifactType.UI_PROTOTYPE: UIPrototypeContent,
    ArtifactType.DATABASE_DESIGN: DatabaseDesignContent,
    ArtifactType.API_SPECIFICATION: APISpecificationContent,
    ArtifactType.TEST_SCENARIO: TestScenarioContent,
    ArtifactType.ACCEPTANCE_CRITERIA: AcceptanceCriteriaContent,
    ArtifactType.DEVELOPMENT_TASK: DevelopmentTaskContent,
}


def validate_artifact_content(artifact_type: ArtifactType, content: dict) -> dict:
    return ARTIFACT_SCHEMA_REGISTRY[artifact_type].model_validate(content).model_dump(mode="json")
