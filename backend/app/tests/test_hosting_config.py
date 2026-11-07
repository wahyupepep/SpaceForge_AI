import pytest

from app.core.config import Settings, normalize_database_url


@pytest.fixture(autouse=True)
def isolated_settings_environment(monkeypatch):  # type: ignore[no-untyped-def]
    for name, field in Settings.model_fields.items():
        monkeypatch.delenv(name.upper(), raising=False)
        for alias in getattr(field.validation_alias, "choices", []):
            monkeypatch.delenv(alias, raising=False)


def test_marketplace_url_preserves_credentials_and_tls() -> None:
    normalized = normalize_database_url(
        "postgres://analyst:p%40ss%25word@database.example/app"
        "?sslmode=verify-full&channel_binding=require"
    )
    assert normalized == (
        "postgresql+asyncpg://analyst:p%40ss%25word@database.example/app?ssl=verify-full"
    )


def test_vercel_uses_durable_storage_secure_cookies_and_bounded_workflows() -> None:
    settings = Settings(_env_file=None, vercel=True)

    assert settings.app_env == "production"
    assert settings.file_storage_backend == "database"
    assert not settings.database_pooling
    assert settings.auth_required
    assert settings.auth_cookie_secure
    assert settings.orchestrator_max_stages_per_request == 1
    assert settings.openai_timeout_seconds == 75
    assert settings.openai_max_retries == 0
    assert settings.max_request_body_bytes < 4_500_000


def test_explicit_hosting_settings_are_preserved() -> None:
    settings = Settings(
        _env_file=None,
        vercel=True,
        openai_timeout_seconds=100,
        orchestrator_max_stages_per_request=2,
    )
    assert settings.openai_timeout_seconds == 100
    assert settings.orchestrator_max_stages_per_request == 2


def test_native_development_keeps_local_storage_and_full_workflow() -> None:
    settings = Settings(_env_file=None)

    assert settings.file_storage_backend == "local"
    assert not settings.auth_required
    assert settings.orchestrator_max_stages_per_request == 0


def test_production_requires_login_even_outside_vercel() -> None:
    settings = Settings(_env_file=None, app_env="production")
    assert settings.auth_required
    assert settings.auth_cookie_secure


@pytest.mark.parametrize(
    "name",
    [
        "DATABASE_DATABASE_URL",
        "DATABASE_POSTGRES_URL",
        "POSTGRES_URL",
        "DATABASE_POSTGRES_URL_NON_POOLING",
    ],
)
def test_marketplace_database_aliases_are_loaded_without_copying_secrets(monkeypatch, name):  # type: ignore[no-untyped-def]
    monkeypatch.setenv(name, "postgres://analyst:example@database.example/app?sslmode=require")
    settings = Settings(_env_file=None, vercel=True)

    assert settings.database_url == (
        "postgresql+asyncpg://analyst:example@database.example/app?ssl=require"
    )
    assert "database_url" in settings.model_fields_set


@pytest.mark.parametrize(
    "name", ["DATABASE_DATABASE_URL_UNPOOLED", "DATABASE_POSTGRES_URL_NON_POOLING"]
)
def test_prefixed_direct_url_is_used_for_migrations(monkeypatch, name):  # type: ignore[no-untyped-def]
    monkeypatch.setenv(name, "postgres://analyst:example@direct.example/app?sslmode=require")
    settings = Settings(_env_file=None)

    assert settings.database_url_unpooled == (
        "postgresql+asyncpg://analyst:example@direct.example/app?ssl=require"
    )


def test_standard_database_url_has_priority_over_prefixed_alias(monkeypatch):  # type: ignore[no-untyped-def]
    monkeypatch.setenv("DATABASE_URL", "postgres://analyst:example@primary.example/app")
    monkeypatch.setenv("DATABASE_DATABASE_URL", "postgres://analyst:example@other.example/app")
    settings = Settings(_env_file=None)

    assert "@primary.example/" in settings.database_url


def test_database_url_can_still_be_set_by_python_field_name() -> None:
    settings = Settings(
        _env_file=None, database_url="postgres://analyst:example@direct.example/app"
    )
    assert settings.database_url == "postgresql+asyncpg://analyst:example@direct.example/app"
