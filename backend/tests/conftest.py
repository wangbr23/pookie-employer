"""Pytest configuration."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/pookie_test"
)
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("API_SECRET", "test-api-secret")
os.environ.setdefault("PYTHON_ENV", "test")

from pookie_backend.database import engine, get_db_session  # noqa: E402
from pookie_backend.main import app  # noqa: E402


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Test client fixture."""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Run each integration test in a rolled-back transaction.

    Uses the app's configured engine (DATABASE_URL, defaulted to the
    `pookie_test` database above) rather than a separate database, so every
    integration test follows the same test-database convention.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, autoflush=False)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def api_client(db_session: Session) -> Generator[TestClient, None, None]:
    """Test client whose requests read the rolled-back transaction's rows.

    Without the override, request handlers would open their own committed
    connection and could not see rows the test only staged in its transaction.
    """
    app.dependency_overrides[get_db_session] = lambda: db_session
    try:
        with TestClient(app) as c:
            yield c
    finally:
        app.dependency_overrides.pop(get_db_session, None)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Authorization header carrying the shared API secret used in tests."""
    return {"Authorization": "Bearer test-api-secret"}
