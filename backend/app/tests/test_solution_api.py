from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from app.api.dependencies import get_solution_analysis_service
from app.main import app
from app.tests.test_solution_analyst import FakeSolutionRepository, make_service

client = TestClient(app)


def test_solution_routes_use_service_contract() -> None:
    repository = FakeSolutionRepository()
    service, _llm = make_service(repository)

    import asyncio

    generated = asyncio.run(service.generate(repository.project.id, repository.requirement.id))
    mock_service = AsyncMock()
    mock_service.generate.return_value = generated
    mock_service.list.return_value = [generated.workflow]
    mock_service.get.return_value = generated.workflow
    mock_service.act.return_value = generated.workflow
    mock_service.retry_revision.return_value = generated
    app.dependency_overrides[get_solution_analysis_service] = lambda: mock_service

    project_id = repository.project.id
    requirement_id = repository.requirement.id
    create = client.post(
        f"/api/v1/projects/{project_id}/generate-solution",
        json={"requirement_id": str(requirement_id)},
    )
    listing = client.get(f"/api/v1/projects/{project_id}/solution-workflows")
    approval = client.post(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}/solution-approval",
        json={"action": "APPROVE", "expected_version": 1},
    )
    retry = client.post(
        f"/api/v1/projects/{project_id}/requirements/{requirement_id}/solution-revision/retry"
    )
    app.dependency_overrides.clear()

    assert create.status_code == 201
    assert listing.status_code == 200
    assert approval.status_code == 200
    assert retry.status_code == 200
    assert create.json()["workflow"]["status"] == "WAITING_USER_APPROVAL"
