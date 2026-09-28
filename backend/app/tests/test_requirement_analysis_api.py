from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_requirement_analysis_service
from app.domain.analysis import RequirementReadiness
from app.domain.artifacts import ArtifactStatus, ArtifactType
from app.domain.requirements import RequirementStatus
from app.main import app
from app.schemas.analysis import RequirementAnalysisResponse
from app.schemas.artifact import ArtifactResponse, ArtifactVersionResponse
from app.schemas.requirement import RequirementResponse

client = TestClient(app)


def sample_response() -> RequirementAnalysisResponse:
    now = datetime.now(timezone.utc)
    project_id = uuid4()
    requirement_id = uuid4()
    content = {
        "feature": "Tiered approval",
        "business_objective": "Reduce risk",
        "problem_statement": "Approval control is insufficient",
        "actors": [],
        "known_requirements": [],
        "business_rules": [],
        "constraints": [],
        "dependencies": [],
        "assumptions": [],
        "unknown_information": [],
        "readiness": "READY",
        "clarification_questions": [],
        "blocked_reason": "",
    }
    version = ArtifactVersionResponse(
        id=uuid4(),
        version=1,
        content_json=content,
        created_by="REQUIREMENT_ANALYST",
        created_at=now,
    )
    return RequirementAnalysisResponse(
        execution_id=uuid4(),
        readiness=RequirementReadiness.READY,
        requirement=RequirementResponse(
            id=requirement_id,
            project_id=project_id,
            title="Tiered approval",
            raw_requirement="Add approval tiers.",
            status=RequirementStatus.BASELINED,
            analysis_readiness=RequirementReadiness.READY,
            created_at=now,
            updated_at=now,
        ),
        artifact=ArtifactResponse(
            id=uuid4(),
            project_id=project_id,
            requirement_id=requirement_id,
            artifact_type=ArtifactType.REQUIREMENT_BASELINE,
            version=1,
            content_json=content,
            status=ArtifactStatus.VALIDATED,
            created_by="REQUIREMENT_ANALYST",
            created_at=now,
            updated_at=now,
            versions=[version],
        ),
        clarifications=[],
    )


def test_requirement_analysis_and_audit_routes_use_service_contract() -> None:
    response = sample_response()
    service = AsyncMock()
    service.analyze.return_value = response
    service.answer_clarifications.return_value = response
    service.list_clarifications.return_value = []
    service.list_history.return_value = []
    app.dependency_overrides[get_requirement_analysis_service] = lambda: service
    base = f"/api/v1/projects/{response.requirement.project_id}"

    analyzed = client.post(
        f"{base}/analyze-requirement",
        json={"requirement_id": str(response.requirement.id)},
    )
    clarifications = client.get(f"{base}/requirements/{response.requirement.id}/clarifications")
    answered = client.post(
        f"{base}/requirements/{response.requirement.id}/clarifications/answer",
        json={"answers": [{"clarification_id": str(uuid4()), "answer": "Manager then director."}]},
    )
    history = client.get(f"{base}/requirements/{response.requirement.id}/analysis-history")
    app.dependency_overrides.clear()

    assert analyzed.status_code == 200
    assert analyzed.json()["readiness"] == "READY"
    assert clarifications.status_code == 200
    assert answered.status_code == 200
    assert history.status_code == 200
