"""Tests for backend configuration."""

import pytest
from pydantic import ValidationError

from pookie_backend.config import Settings


def test_settings_load_required_environment() -> None:
    """Settings load required values from explicit environment-style input."""
    settings = Settings(
        DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/pookie_test",
        SECRET_KEY="test-secret",
        PYTHON_ENV="test",
    )

    assert settings.environment == "test"
    assert settings.database_url.endswith("/pookie_test")
    assert settings.secret_key.get_secret_value() == "test-secret"


def test_settings_requires_database_url_and_secret_key(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Required settings fail fast instead of defaulting to unsafe values."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(ValidationError) as exc_info:
        Settings(PYTHON_ENV="test", _env_file=None)

    message = str(exc_info.value)
    assert "DATABASE_URL" in message
    assert "SECRET_KEY" in message
    assert "postgres:postgres" not in message


def test_secret_key_is_redacted_in_repr() -> None:
    """Secrets should not appear in normal settings representations."""
    settings = Settings(
        DATABASE_URL="postgresql+psycopg://postgres:postgres@localhost:5432/pookie_test",
        SECRET_KEY="super-sensitive-secret",
        PYTHON_ENV="test",
    )

    assert "super-sensitive-secret" not in repr(settings)
    assert "**********" in repr(settings)
