from app.core.security import sanitized_error


def test_error_sanitizer_redacts_api_key_and_database_password() -> None:
    error = RuntimeError(
        "api_key=secret-value sk-example123456 "
        "postgresql+asyncpg://user:password@db/spaceforge"
    )

    sanitized = sanitized_error(error)

    assert "secret-value" not in sanitized
    assert "sk-example123456" not in sanitized
    assert ":password@" not in sanitized
    assert "[REDACTED]" in sanitized
