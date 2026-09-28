from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.config import settings
from app.core.errors import ServiceUnavailableError
from app.db.session import database_is_ready
from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])
DatabaseReadiness = Annotated[bool, Depends(database_is_ready)]


@router.get("/health", response_model=HealthResponse)
async def health_check(database_ready: DatabaseReadiness) -> HealthResponse:
    if not database_ready:
        raise ServiceUnavailableError("Database connection is unavailable.")

    return HealthResponse(
        status="ok",
        service="spaceforge-api",
        environment=settings.app_env,
        database="ok",
    )
