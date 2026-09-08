"""Tests for the stored-job skip_reason backfill."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy.orm import Session

from pookie_backend.backfill import backfill_skip_reasons
from pookie_backend.models import Job, JobStatus, RemotePolicy, UserProfile

BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def add_profile(session: Session) -> UserProfile:
    profile = UserProfile(
        id=uuid4(),
        owner_user_id=f"owner-{uuid4()}",
        target_role_families=["backend"],
        preferred_tech=["Python", "FastAPI"],
        avoided_tech=["Blockchain"],
        dealbreakers=["Contract"],
        profile_version=1,
        ai_consent_given=True,
        ai_consent_provider="mock",
        ai_consent_model_family="mock-eval",
    )
    session.add(profile)
    session.flush()
    return profile


def add_job(
    session: Session,
    *,
    title: str,
    status: JobStatus = JobStatus.NEW,
    skip_reason: str | None = None,
) -> Job:
    job = Job(
        id=uuid4(),
        canonical_title=title,
        canonical_company="Astral",
        canonical_location="Remote (US)",
        remote_policy=RemotePolicy.REMOTE.value,
        salary_unknown=True,
        status=status,
        first_seen_at=BASE_TIME,
        last_seen_at=BASE_TIME,
        skip_reason=skip_reason,
    )
    session.add(job)
    session.flush()
    return job


def test_filters_stored_jobs_that_fail_the_gate(db_session: Session):
    add_profile(db_session)
    leak = add_job(db_session, title="Senior Data Engineer - Revenue Data Platform")
    pm = add_job(db_session, title="Senior Product Manager - Observability Data Platform")
    swe = add_job(db_session, title="Senior Software Engineer")

    assert backfill_skip_reasons(db_session) == (3, 0)

    assert leak.skip_reason == "not_engineering_role"
    assert pm.skip_reason == "not_engineering_role"
    assert swe.skip_reason == "seniority_too_high"


def test_clears_stale_skip_reason_when_job_now_passes(db_session: Session):
    add_profile(db_session)
    job = add_job(
        db_session, title="Backend Engineer", skip_reason="not_engineering_role"
    )

    assert backfill_skip_reasons(db_session) == (0, 1)

    assert job.skip_reason is None


def test_leaves_dismissed_and_archived_jobs_untouched(db_session: Session):
    add_profile(db_session)
    dismissed = add_job(db_session, title="Data Engineer", status=JobStatus.DISMISSED)
    archived = add_job(
        db_session, title="Data Engineer", status=JobStatus.CLOSED_ARCHIVED
    )

    assert backfill_skip_reasons(db_session) == (0, 0)

    assert dismissed.skip_reason is None
    assert archived.skip_reason is None


def test_without_a_profile_is_a_noop(db_session: Session):
    job = add_job(db_session, title="Data Engineer")

    assert backfill_skip_reasons(db_session) == (0, 0)

    assert job.skip_reason is None
