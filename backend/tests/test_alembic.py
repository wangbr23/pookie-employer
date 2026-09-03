"""Test Alembic configuration and setup."""

import os
import subprocess
import sys
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from pookie_backend.config import get_settings
from pookie_backend.database import Base


def test_alembic_config_imports_settings_and_metadata():
    """Test that Alembic config properly imports our application settings and metadata."""
    # Test that we can import our settings
    settings = get_settings()
    assert settings is not None
    assert hasattr(settings, "database_url")

    # Test that we can access our Base metadata
    assert Base.metadata is not None


def test_alembic_env_configuration():
    """Test that Alembic environment is properly configured."""
    # Change to backend directory
    backend_dir = Path(__file__).parent.parent
    alembic_ini_path = backend_dir / "alembic.ini"

    # Create Alembic config
    config = Config(str(alembic_ini_path))

    # Check that script location is correct
    script_location = config.get_main_option("script_location")
    assert script_location is not None
    assert "alembic" in script_location

    # Check that we can load the script directory
    script_dir = ScriptDirectory.from_config(config)
    assert script_dir is not None

    versions_dir = backend_dir / "alembic" / "versions"
    assert versions_dir.is_dir()
    assert script_dir.get_heads() == ["0004_ai_consent_and_call_logs"]


def test_alembic_heads_command_runs_without_database():
    """The empty revision graph can be inspected without a database connection."""
    backend_dir = Path(__file__).parent.parent

    result = subprocess.run(
        [sys.executable, "-m", "alembic", "heads"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(backend_dir / "src")},
    )

    assert result.returncode == 0, result.stderr
    assert "0004_ai_consent_and_call_logs (head)" in result.stdout


def test_alembic_current_command():
    """Test that alembic current command runs without errors."""
    backend_dir = Path(__file__).parent.parent

    # Run alembic current command
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        cwd=backend_dir,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": str(backend_dir / "src")},
    )

    # Should either succeed or fail with expected messages for a new setup
    # It's okay if it fails due to database connection issues in test environments
    # What matters is that it loads our configuration correctly
    expected_messages = [
        "connection refused",
        "could not connect",
        "connection failed",
        "operation not permitted",
    ]

    # Success is acceptable
    if result.returncode == 0:
        return

    # Expected failure messages are also acceptable
    stderr_lower = result.stderr.lower()
    if any(msg in stderr_lower for msg in expected_messages):
        return

    # Unexpected failure - show the actual error
    assert False, f"Unexpected alembic current error:\n{result.stderr}"
