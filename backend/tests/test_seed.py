"""Tests for the database seed command."""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from pookie_backend.database import SessionLocal
from pookie_backend.models import ApprovalStatus, JobSource, SourceKind, UserProfile
from pookie_backend.seed import SEED_OWNER_USER_ID, seed_database


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """Provide a database session for this test.

    Cleanup between tests is handled by the `clean_seed_tables` fixture, since
    `seed_database` commits — a rollback here would have nothing to undo.
    """
    with SessionLocal() as session:
        yield session


@pytest.fixture(autouse=True)
def clean_seed_tables(db_session: Session) -> Generator[None, None, None]:
    """Start each seed test with an empty set of seed rows."""
    db_session.execute(delete(JobSource))
    db_session.execute(delete(UserProfile))
    db_session.commit()
    yield
    db_session.execute(delete(JobSource))
    db_session.execute(delete(UserProfile))
    db_session.commit()


def test_seed_database_is_idempotent(db_session: Session) -> None:
    """Running the seed twice should not create duplicate seed rows."""
    seed_database(db_session)
    seed_database(db_session)

    assert (
        db_session.scalar(
            select(UserProfile).where(UserProfile.owner_user_id == SEED_OWNER_USER_ID)
        )
        is not None
    )
    assert db_session.scalar(select(func.count()).select_from(UserProfile)) == 1
    assert db_session.scalar(select(func.count()).select_from(JobSource)) == 5


def test_seed_database_creates_expected_profile_and_sources(db_session: Session) -> None:
    """The seeded profile and sources should match the expected MVP shape."""
    profile, sources = seed_database(db_session)

    assert profile.owner_user_id == SEED_OWNER_USER_ID
    assert profile.target_role_families == [
        "backend engineering",
        "platform engineering",
    ]
    assert profile.remote_preference == "remote_or_hybrid"
    assert profile.salary_floor == Decimal("180000.00")
    assert "Python" in profile.preferred_tech
    assert len(sources) == 5
    assert all(
        source.approval_status == ApprovalStatus.APPROVED for source in sources
    )
    assert {source.kind for source in sources} == {
        SourceKind.GREENHOUSE,
        SourceKind.LEVER,
        SourceKind.ASHBY,
    }
