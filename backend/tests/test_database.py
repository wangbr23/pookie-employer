"""Tests for database initialization."""

from sqlalchemy.engine import Engine

from pookie_backend.database import create_db_engine, redact_database_url


def test_create_db_engine_uses_sqlalchemy_postgres_url() -> None:
    """The database layer creates a SQLAlchemy engine without connecting eagerly."""
    engine = create_db_engine(
        "postgresql+psycopg://postgres:postgres@localhost:5432/pookie_test"
    )

    assert isinstance(engine, Engine)
    assert engine.url.get_backend_name() == "postgresql"
    assert engine.url.database == "pookie_test"

    engine.dispose()


def test_redact_database_url_hides_password() -> None:
    """Diagnostic database URLs must not leak passwords."""
    safe_url = redact_database_url(
        "postgresql+psycopg://postgres:postgres@localhost:5432/pookie_test"
    )

    assert "postgres:postgres" not in safe_url
    assert "***" in safe_url
    assert "pookie_test" in safe_url
