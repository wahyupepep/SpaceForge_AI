from typing import Annotated

from fastapi import Depends
from openai import AsyncOpenAI
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.design import (
    DesignAgentConfig,
    FlowDesignerAgent,
    TechnicalArchitectAgent,
    UIPrototypeAgent,
)
from app.agents.development_planner import DevelopmentPlannerAgent, DevelopmentPlannerConfig
from app.agents.discovery import ExistingSystemAnalyst, ResearchAgent, SpecialistAgentConfig
from app.agents.quality import QAAnalystAgent, QualityAgentConfig, SAReviewerAgent
from app.agents.requirement_analyst import RequirementAnalystAgent, RequirementAnalystConfig
from app.agents.solution_analyst import SolutionAnalyst, SolutionAnalystConfig
from app.core.config import settings
from app.db.session import get_db_session
from app.integrations.local_file_storage import LocalFileStorageService
from app.integrations.openai_llm import OpenAILLMService
from app.repositories.analysis import RequirementAnalysisRepository
from app.repositories.artifacts import ArtifactRepository
from app.repositories.handoff import HandoffRepository
from app.repositories.orchestrator import OrchestratorRepository
from app.repositories.projects import SQLAlchemyProjectRepository
from app.repositories.quality import QualityRepository
from app.repositories.requirements import RequirementRepository
from app.repositories.solution import SolutionRepository
from app.services.artifacts import ArtifactService
from app.services.design_generation import DesignGenerationService
from app.services.development_handoff import DevelopmentHandoffService
from app.services.discovery_analysis import DiscoveryAnalysisService
from app.services.orchestrator import SAOrchestratorService
from app.services.projects import ProjectService
from app.services.quality_gate import QualityGateService
from app.services.requirement_analysis import RequirementAnalysisService
from app.services.requirements import RequirementService
from app.services.solution_analysis import SolutionAnalysisService


def _openai_llm_service() -> OpenAILLMService:
    if settings.openai_api_key is None:
        raise RuntimeError("OpenAI client requested without OPENAI_API_KEY.")
    return OpenAILLMService(
        AsyncOpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )
    )


def get_project_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ProjectService:
    return ProjectService(SQLAlchemyProjectRepository(session))


def get_requirement_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RequirementService:
    return RequirementService(RequirementRepository(session))


def get_artifact_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ArtifactService:
    return ArtifactService(ArtifactRepository(session))


def get_requirement_analysis_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> RequirementAnalysisService:
    agent = None
    if settings.openai_api_key is not None:
        llm = _openai_llm_service()
        agent = RequirementAnalystAgent(
            llm,
            RequirementAnalystConfig(
                model=(
                    settings.openai_requirement_analyst_model or settings.openai_reasoning_model
                ),
                max_output_tokens=settings.ai_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
    return RequirementAnalysisService(RequirementAnalysisRepository(session), agent)


def get_discovery_analysis_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DiscoveryAnalysisService:
    research_agent = None
    existing_system_analyst = None
    if settings.openai_api_key is not None:
        llm = _openai_llm_service()
        research_agent = ResearchAgent(
            llm,
            SpecialistAgentConfig(
                model=settings.openai_research_model or settings.openai_default_model,
                max_output_tokens=settings.ai_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
            web_search_enabled=settings.research_web_search_enabled,
        )
        existing_system_analyst = ExistingSystemAnalyst(
            llm,
            SpecialistAgentConfig(
                model=(
                    settings.openai_existing_system_analyst_model or settings.openai_reasoning_model
                ),
                max_output_tokens=settings.ai_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
    return DiscoveryAnalysisService(
        RequirementAnalysisRepository(session),
        research_agent,
        existing_system_analyst,
    )


def get_solution_analysis_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SolutionAnalysisService:
    agent = None
    if settings.openai_api_key is not None:
        llm = _openai_llm_service()
        agent = SolutionAnalyst(
            llm,
            SolutionAnalystConfig(
                model=(settings.openai_solution_analyst_model or settings.openai_reasoning_model),
                max_output_tokens=settings.ai_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
    return SolutionAnalysisService(SolutionRepository(session), agent)


def get_design_generation_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DesignGenerationService:
    flow_agent = None
    ui_agent = None
    technical_agent = None
    if settings.openai_api_key is not None:
        llm = _openai_llm_service()
        flow_agent = FlowDesignerAgent(
            llm,
            DesignAgentConfig(
                model=settings.openai_flow_designer_model or settings.openai_default_model,
                max_output_tokens=settings.ai_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
        ui_agent = UIPrototypeAgent(
            llm,
            DesignAgentConfig(
                model=settings.openai_ui_prototype_model or settings.openai_default_model,
                max_output_tokens=settings.ai_prototype_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
        technical_agent = TechnicalArchitectAgent(
            llm,
            DesignAgentConfig(
                model=(
                    settings.openai_technical_architect_model or settings.openai_reasoning_model
                ),
                max_output_tokens=settings.ai_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
    return DesignGenerationService(
        SolutionRepository(session),
        flow_agent,
        ui_agent,
        technical_agent,
        LocalFileStorageService(settings.file_storage_root),
    )


def get_quality_gate_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> QualityGateService:
    qa_agent = None
    reviewer_agent = None
    flow_agent = None
    ui_agent = None
    technical_agent = None
    if settings.openai_api_key is not None:
        llm = _openai_llm_service()
        qa_agent = QAAnalystAgent(
            llm,
            QualityAgentConfig(
                model=settings.openai_qa_analyst_model or settings.openai_reasoning_model,
                max_output_tokens=settings.ai_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
        reviewer_agent = SAReviewerAgent(
            llm,
            QualityAgentConfig(
                model=settings.openai_sa_reviewer_model or settings.openai_reasoning_model,
                max_output_tokens=settings.ai_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
        flow_agent = FlowDesignerAgent(
            llm,
            DesignAgentConfig(
                model=settings.openai_flow_designer_model or settings.openai_default_model,
                max_output_tokens=settings.ai_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
        ui_agent = UIPrototypeAgent(
            llm,
            DesignAgentConfig(
                model=settings.openai_ui_prototype_model or settings.openai_default_model,
                max_output_tokens=settings.ai_prototype_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
        technical_agent = TechnicalArchitectAgent(
            llm,
            DesignAgentConfig(
                model=settings.openai_technical_architect_model or settings.openai_reasoning_model,
                max_output_tokens=settings.ai_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
    storage = LocalFileStorageService(settings.file_storage_root)
    design_service = DesignGenerationService(
        QualityRepository(session), flow_agent, ui_agent, technical_agent, storage
    )
    return QualityGateService(
        QualityRepository(session),
        qa_agent,
        reviewer_agent,
        design_service,
        storage,
        settings.quality_max_revisions,
    )


def get_development_handoff_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DevelopmentHandoffService:
    planner = None
    if settings.openai_api_key is not None:
        llm = _openai_llm_service()
        planner = DevelopmentPlannerAgent(
            llm,
            DevelopmentPlannerConfig(
                model=(
                    settings.openai_development_planner_model
                    or settings.openai_reasoning_model
                ),
                max_output_tokens=settings.ai_max_output_tokens,
                temperature=settings.ai_temperature,
            ),
        )
    return DevelopmentHandoffService(
        HandoffRepository(session),
        planner,
        LocalFileStorageService(settings.file_storage_root),
    )


def get_orchestrator_service(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> SAOrchestratorService:
    return SAOrchestratorService(
        OrchestratorRepository(session),
        get_requirement_analysis_service(session),
        get_discovery_analysis_service(session),
        get_solution_analysis_service(session),
        get_design_generation_service(session),
        get_quality_gate_service(session),
        get_development_handoff_service(session),
        settings.orchestrator_lease_seconds,
    )
