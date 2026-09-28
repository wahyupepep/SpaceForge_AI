from unittest.mock import AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient

from app.api.dependencies import get_discovery_analysis_service
from app.main import app
from app.schemas.discovery import SpecialistAnalysisResponse
from app.tests.test_requirement_analysis_api import sample_response

client = TestClient(app)


def test_discovery_routes_use_service_contract() -> None:
    analysis = sample_response()
    response = SpecialistAnalysisResponse(execution_id=uuid4(), artifact=analysis.artifact)
    service = AsyncMock()
    service.run_research.return_value = response
    service.analyze_existing_system.return_value = response
    app.dependency_overrides[get_discovery_analysis_service] = lambda: service
    project_id = analysis.requirement.project_id

    research = client.post(
        f"/api/v1/projects/{project_id}/research",
        json={"requirement_id": str(analysis.requirement.id)},
    )
    existing = client.post(
        f"/api/v1/projects/{project_id}/analyze-existing-system",
        json={
            "requirement_id": str(analysis.requirement.id),
            "evidence": [
                {
                    "source_type": "USER_DESCRIPTION",
                    "title": "Current flow",
                    "content": "One manager approves every request.",
                }
            ],
        },
    )
    app.dependency_overrides.clear()

    assert research.status_code == 200
    assert existing.status_code == 200
    assert research.json()["execution_id"] == str(response.execution_id)
