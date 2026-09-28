from datetime import datetime, timezone
from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_quality_gate_service
from app.domain.quality import QualityWorkflowStatus
from app.main import app
from app.schemas.quality import QualityAgentResponse, QualityWorkflowResponse

client = TestClient(app)


def test_quality_gate_routes() -> None:
    project_id = uuid4()
    requirement_id = uuid4()
    workflow = QualityWorkflowResponse(
        id=uuid4(),
        project_id=project_id,
        requirement_id=requirement_id,
        status=QualityWorkflowStatus.READY_FOR_REVIEW,
        decision=None,
        revision_count=0,
        max_revisions=5,
        development_handoff_allowed=False,
        reviewed_versions={},
        issues=[],
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    response = QualityAgentResponse(execution_id=uuid4(), workflow=workflow, artifacts=[])
    service = AsyncMock()
    service.run_qa.return_value = response
    service.run_review.return_value = response
    service.revise.return_value = response
    service.get.return_value = workflow
    service.list.return_value = [workflow]
    app.dependency_overrides[get_quality_gate_service] = lambda: service

    payload = {"requirement_id": str(requirement_id)}
    qa = client.post(f"/api/v1/projects/{project_id}/quality/qa", json=payload)
    review = client.post(f"/api/v1/projects/{project_id}/quality/review", json=payload)
    revise = client.post(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}/quality/revise",
        json={"artifact_type": "PROCESS_FLOW"},
    )
    detail = client.get(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}/quality-workflow"
    )
    listing = client.get(f"/api/v1/projects/{project_id}/quality-workflows")
    app.dependency_overrides.clear()

    assert [qa.status_code, review.status_code, revise.status_code] == [200, 200, 200]
    assert detail.status_code == 200
    assert listing.status_code == 200
