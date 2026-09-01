"""Pytest configuration."""

import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/pookie_test"
)
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("PYTHON_ENV", "test")

from pookie_backend.main import app  # noqa: E402


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Test client fixture."""
    with TestClient(app) as c:
        yield c
