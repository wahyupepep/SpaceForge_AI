from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

from pydantic import AliasChoices, Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url


def normalize_database_url(value: str) -> str:
    """Accept Marketplace PostgreSQL URLs with the application's async driver."""
    url = make_url(value)
    if url.drivername not in {"postgres", "postgresql", "postgresql+asyncpg"}:
        raise ValueError("A PostgreSQL connection URL is required.")
    query = dict(url.query)
    if "sslmode" in query:
        query.setdefault("ssl", query.pop("sslmode"))
    # libpq's channel_binding option is not supported by asyncpg. TLS settings
    # remain intact; the provider's default connection string needs no edits.
    query.pop("channel_binding", None)
    return url.set(drivername="postgresql+asyncpg", query=query).render_as_string(
        hide_password=False
    )


class Settings(BaseSettings):
    app_name: str = "SpaceForge AI API"
    app_version: str = "0.1.0"
    app_env: str = "development"
    database_url: str = Field(
        default="postgresql+asyncpg://spaceforge:spaceforge@localhost:5432/spaceforge",
        validation_alias=AliasChoices(
            "DATABASE_URL",
            "DATABASE_DATABASE_URL",
            "DATABASE_POSTGRES_URL",
            "POSTGRES_URL",
            "DATABASE_POSTGRES_URL_NON_POOLING",
        ),
    )
    database_url_unpooled: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices(
            "DATABASE_URL_UNPOOLED",
            "DATABASE_DATABASE_URL_UNPOOLED",
            "DATABASE_POSTGRES_URL_NON_POOLING",
            "POSTGRES_URL_NON_POOLING",
        ),
    )
    database_pooling: bool = True
    vercel: bool = False
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
    orchestrator_max_stages_per_request: int = Field(default=0, ge=0, le=100)
    max_request_body_bytes: int = Field(default=5_242_880, ge=65_536, le=52_428_800)
    file_storage_root: Path = Path(".data/files")
    file_storage_backend: Literal["local", "database"] = "local"
    auth_cookie_secure: bool = False
    auth_required: bool = False

    @field_validator("database_url", "database_url_unpooled")
    @classmethod
    def validate_database_url(cls, value: Optional[str]) -> Optional[str]:
        return normalize_database_url(value) if value else value

    @model_validator(mode="after")
    def configure_hosting_defaults(self) -> Settings:
        if self.vercel:
            defaults = {
                "app_env": "production",
                "database_pooling": False,
                "file_storage_backend": "database",
                "auth_cookie_secure": True,
                "auth_required": True,
                "orchestrator_max_stages_per_request": 1,
                "openai_timeout_seconds": 75.0,
                "openai_max_retries": 0,
                "max_request_body_bytes": 4_400_000,
            }
            for name, value in defaults.items():
                if name not in self.model_fields_set:
                    setattr(self, name, value)
        if self.app_env == "production":
            for name in ("auth_required", "auth_cookie_secure"):
                if name not in self.model_fields_set:
                    setattr(self, name, True)
        return self

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        populate_by_name=True,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
