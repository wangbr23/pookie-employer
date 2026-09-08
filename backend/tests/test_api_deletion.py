"""Integration tests for the destructive data-deletion endpoints."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from pookie_backend.models import (
    AiCallLog,
    AiCallStatus,
    FeedbackAction,
    FitBucket,
    Job,
    JobEvaluation,
    JobFeedback,
    JobStatus,
    RemoteUncertainty,
    SalaryUncertainty,
    UserProfile,
    WorkAuthUncertainty,
)

BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def _profile(session: Session) -> UserProfile:
    p = UserProfile(id=uuid4(), owner_user_id=f"owner-{uuid4()}")
    session.add(p)
    session.flush()
    return p


def _job(
    session: Session,
    *,
    status: JobStatus = JobStatus.NEW,
    fit_bucket: FitBucket | None = None,
) -> Job:
    job = Job(
        id=uuid4(),
        canonical_title="Backend Engineer",
        canonical_company="Acme",
        canonical_location="Remote",
        salary_unknown=True,
        status=status,
        fit_bucket=fit_bucket,
        first_seen_at=BASE_TIME,
        last_seen_at=BASE_TIME,
    )
    session.add(job)
    session.flush()
    return job


def _evaluation(session: Session, job: Job, profile: UserProfile) -> JobEvaluation:
    ev = JobEvaluation(
        id=uuid4(),
        job_id=job.id,
        profile_id=profile.id,
        profile_version=1,
        job_content_hash="abc123",
        fit_bucket=FitBucket.STRONG,
        internal_score=Decimal("0.85"),
        matched_skills=["Python"],
        matched_preferences=["remote"],
        concerns=[],
        uncertainties=[],
        summary="Good fit",
        verify_before_applying=[],
        salary_uncertainty=SalaryUncertainty.UNKNOWN,
        remote_uncertainty=RemoteUncertainty.CLEAR,
        work_auth_uncertainty=WorkAuthUncertainty.CLEAR,
        model_provider="mock",
        model_name="mock-v1",
    )
    session.add(ev)
    session.flush()
    return ev


def _ai_call_log(session: Session, profile: UserProfile) -> AiCallLog:
    log = AiCallLog(
        id=uuid4(),
        profile_id=profile.id,
        provider="mock",
        model_name="mock-v1",
        operation="evaluate",
        status=AiCallStatus.SUCCEEDED,
        call_count=1,
        input_tokens=100,
        output_tokens=50,
        estimated_cost=Decimal("0.001"),
    )
    session.add(log)
    session.flush()
    return log


def _feedback(
    session: Session,
    job: Job,
    profile: UserProfile,
    action: FeedbackAction = FeedbackAction.SAVE,
) -> JobFeedback:
    fb = JobFeedback(
        id=uuid4(),
        job_id=job.id,
        profile_id=profile.id,
        action=action,
        reasons=["interesting"],
    )
    session.add(fb)
    session.flush()
    return fb


# -- DELETE /api/profile --


def test_delete_profile_requires_auth(api_client: TestClient):
    response = api_client.delete("/api/profile")
    assert response.status_code == 401


def test_delete_profile_removes_evaluations_and_ai_logs(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    profile = _profile(db_session)
    job = _job(db_session, fit_bucket=FitBucket.STRONG)
    _evaluation(db_session, job, profile)
    _ai_call_log(db_session, profile)

    response = api_client.delete("/api/profile", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["deleted"]["evaluations"] == 1
    assert data["deleted"]["ai_call_logs"] == 1

    assert db_session.query(JobEvaluation).filter_by(profile_id=profile.id).count() == 0
    assert db_session.query(AiCallLog).filter_by(profile_id=profile.id).count() == 0


def test_delete_profile_clears_fit_bucket_on_orphaned_jobs(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    profile = _profile(db_session)
    job = _job(db_session, fit_bucket=FitBucket.STRONG)
    _evaluation(db_session, job, profile)

    api_client.delete("/api/profile", headers=auth_headers)

    db_session.refresh(job)
    assert job.fit_bucket is None


def test_delete_profile_preserves_profile_row(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    profile = _profile(db_session)
    _ai_call_log(db_session, profile)

    api_client.delete("/api/profile", headers=auth_headers)

    assert db_session.get(UserProfile, profile.id) is not None


def test_delete_profile_idempotent_on_empty(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    _profile(db_session)

    response = api_client.delete("/api/profile", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["deleted"]["evaluations"] == 0
    assert response.json()["deleted"]["ai_call_logs"] == 0


# -- DELETE /api/job-history --


def test_delete_job_history_requires_auth(api_client: TestClient):
    response = api_client.delete("/api/job-history")
    assert response.status_code == 401


def test_delete_job_history_removes_feedback_and_resets_status(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    profile = _profile(db_session)
    saved_job = _job(db_session, status=JobStatus.SAVED)
    dismissed_job = _job(db_session, status=JobStatus.DISMISSED)
    _feedback(db_session, saved_job, profile, FeedbackAction.SAVE)
    _feedback(db_session, dismissed_job, profile, FeedbackAction.DISMISS)

    response = api_client.delete("/api/job-history", headers=auth_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["deleted"]["feedback_records"] == 2
    assert data["reset"]["jobs_to_seen"] == 2

    assert db_session.query(JobFeedback).filter_by(profile_id=profile.id).count() == 0
    db_session.refresh(saved_job)
    db_session.refresh(dismissed_job)
    assert saved_job.status == JobStatus.SEEN
    assert dismissed_job.status == JobStatus.SEEN


def test_delete_job_history_does_not_reset_new_or_seen_jobs(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    _profile(db_session)
    new_job = _job(db_session, status=JobStatus.NEW)
    seen_job = _job(db_session, status=JobStatus.SEEN)

    api_client.delete("/api/job-history", headers=auth_headers)

    db_session.refresh(new_job)
    db_session.refresh(seen_job)
    assert new_job.status == JobStatus.NEW
    assert seen_job.status == JobStatus.SEEN


def test_delete_job_history_idempotent_on_empty(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    _profile(db_session)

    response = api_client.delete("/api/job-history", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["deleted"]["feedback_records"] == 0
    assert response.json()["reset"]["jobs_to_seen"] == 0
