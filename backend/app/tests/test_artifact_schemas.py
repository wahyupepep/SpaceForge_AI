import pytest
from pydantic import ValidationError

from app.artifacts.schemas import ARTIFACT_SCHEMA_REGISTRY, validate_artifact_content
from app.domain.artifacts import ArtifactType

VALID_CONTENT = {
    ArtifactType.PROJECT_CONTEXT: {
        "project_name": "Approval",
        "project_type": "NEW_FEATURE",
        "business_objective": "Reduce risk",
        "context": {},
    },
    ArtifactType.REQUIREMENT_BASELINE: {
        "feature": "Tiered approval",
        "business_objective": "Reduce risk",
        "problem_statement": "Controls are insufficient",
    },
    ArtifactType.RESEARCH: {"objective": "Review regulations"},
    ArtifactType.EXISTING_SYSTEM_ANALYSIS: {"as_is_summary": "Legacy workflow"},
    ArtifactType.SOLUTION: {"summary": "Proposed boundary"},
    ArtifactType.PROCESS_FLOW: {"name": "Approval flow"},
    ArtifactType.UI_PROTOTYPE: {},
    ArtifactType.DATABASE_DESIGN: {},
    ArtifactType.API_SPECIFICATION: {"base_path": "/api/v1"},
    ArtifactType.TEST_SCENARIO: {},
    ArtifactType.ACCEPTANCE_CRITERIA: {},
    ArtifactType.DEVELOPMENT_TASK: {},
}


def test_every_artifact_type_has_a_validating_schema() -> None:
    assert set(ARTIFACT_SCHEMA_REGISTRY) == set(ArtifactType)
    for artifact_type, content in VALID_CONTENT.items():
        assert validate_artifact_content(artifact_type, content) is not None


def test_requirement_baseline_rejects_incomplete_content() -> None:
    with pytest.raises(ValidationError):
        validate_artifact_content(
            ArtifactType.REQUIREMENT_BASELINE,
            {"feature": "Tiered approval"},
        )
