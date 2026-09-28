from fastapi import APIRouter

from app.api.v1.routes.artifacts import router as artifacts_router
from app.api.v1.routes.design_generation import router as design_generation_router
from app.api.v1.routes.development_handoff import router as development_handoff_router
from app.api.v1.routes.discovery_analysis import router as discovery_analysis_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.orchestrator import router as orchestrator_router
from app.api.v1.routes.projects import router as projects_router
from app.api.v1.routes.quality_gate import router as quality_gate_router
from app.api.v1.routes.requirement_analysis import router as requirement_analysis_router
from app.api.v1.routes.requirements import router as requirements_router
from app.api.v1.routes.solution_analysis import router as solution_analysis_router

router = APIRouter()
router.include_router(health_router)
router.include_router(projects_router)
router.include_router(requirements_router)
router.include_router(artifacts_router)
router.include_router(requirement_analysis_router)
router.include_router(discovery_analysis_router)
router.include_router(solution_analysis_router)
router.include_router(design_generation_router)
router.include_router(quality_gate_router)
router.include_router(development_handoff_router)
router.include_router(orchestrator_router)
