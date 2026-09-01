"""Pytest configuration."""

import pytest
from fastapi.testclient import TestClient

from pookie_backend.main import app


@pytest.fixture
def client():
    """Test client fixture."""
    with TestClient(app) as c:
        yield c
