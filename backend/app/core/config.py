from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SpaceForge AI API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    database_url: str = "postgresql+asyncpg://spaceforge:spaceforge@localhost:5432/spaceforge"
    backend_url: str = "http://localhost:8000"
    cors_origins: list[str] = ["http://localhost:3000"]
    openai_api_key: Optional[SecretStr] = None
    openai_default_model: str = "gpt-5-mini"
    openai_reasoning_model: str = "gpt-5"
    openai_requirement_analyst_model: Optional[str] = None
    openai_research_model: Optional[str] = None
    openai_existing_system_analyst_model: Optional[str] = None
    openai_solution_analyst_model: Optional[str] = None
    openai_flow_designer_model: Optional[str] = None
    openai_ui_prototype_model: Optional[str] = None
    openai_technical_architect_model: Optional[str] = None
    openai_qa_analyst_model: Optional[str] = None
    openai_sa_reviewer_model: Optional[str] = None
    openai_development_planner_model: Optional[str] = None
    research_web_search_enabled: bool = True
    ai_temperature: Optional[float] = None
    openai_timeout_seconds: float = Field(default=120.0, ge=5.0, le=900.0)
    openai_max_retries: int = Field(default=2, ge=0, le=5)
    ai_max_output_tokens: int = Field(default=4096, ge=256, le=100_000)
    ai_prototype_max_output_tokens: int = Field(default=12000, ge=256, le=100_000)
    quality_max_revisions: int = Field(default=5, ge=0, le=20)
    orchestrator_lease_seconds: int = Field(default=900, ge=60, le=3600)
    max_request_body_bytes: int = Field(default=5_242_880, ge=65_536, le=52_428_800)
    file_storage_root: Path = Path(".data/files")

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
