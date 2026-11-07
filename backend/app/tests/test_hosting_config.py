import pytest

from app.core.config import Settings, normalize_database_url


@pytest.fixture(autouse=True)
def isolated_settings_environment(monkeypatch):  # type: ignore[no-untyped-def]
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


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
