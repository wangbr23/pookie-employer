"""Integration tests for the stored job-evaluation pipeline."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pookie_backend.ai import AIConsentRequiredError, AIService
from pookie_backend.ai.interface import (
    AIJobEvaluationRequest,
    AIJobEvaluationResult,
    AIJobSnapshot,
    AIProfileSnapshot,
)
from pookie_backend.ai.mock import MockAIProvider
from pookie_backend.evaluation import (
    EvaluationRunCounts,
    evaluate_job,
    evaluate_pending_jobs,
    job_content_hash,
)
from pookie_backend.models import (
    FitBucket,
    Job,
    JobEvaluation,
    JobStatus,
    RemotePolicy,
    RemoteUncertainty,
    SalaryUncertainty,
    UserProfile,
    WorkAuthUncertainty,
)

BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def add_profile(session: Session, *, consented: bool = True) -> UserProfile:
    profile = UserProfile(
        id=uuid4(),
        owner_user_id=f"owner-{uuid4()}",
        target_role_families=["backend"],
        preferred_tech=["Python", "FastAPI"],
        avoided_tech=["Blockchain"],
        dealbreakers=["Contract"],
        profile_version=1,
        ai_consent_given=consented,
        ai_consent_provider="mock" if consented else None,
        ai_consent_model_family="mock-eval" if consented else None,
    )
    session.add(profile)
    session.flush()
    return profile


def add_job(
    session: Session,
    *,
    title: str = "Python Backend Engineer",
    company: str = "Astral",
    location: str = "Remote (US)",
    remote_policy: str = RemotePolicy.REMOTE.value,
    salary_unknown: bool = True,
    status: JobStatus = JobStatus.NEW,
    first_seen_at: datetime = BASE_TIME,
) -> Job:
    job = Job(
        id=uuid4(),
        canonical_title=title,
        canonical_company=company,
        canonical_location=location,
        remote_policy=remote_policy,
        salary_unknown=salary_unknown,
        status=status,
        first_seen_at=first_seen_at,
        last_seen_at=first_seen_at,
    )
    session.add(job)
    session.flush()
    return job


def make_service(session: Session) -> AIService:
    return AIService(MockAIProvider(), session)


def test_evaluation_is_blocked_without_ai_consent(db_session: Session):
    """The pipeline must not reach a provider a profile has not allowed."""
    profile = add_profile(db_session, consented=False)
    job = add_job(db_session)

    with pytest.raises(AIConsentRequiredError):
        evaluate_job(db_session, make_service(db_session), profile, job)

    assert db_session.scalar(select(func.count()).select_from(JobEvaluation)) == 0


def test_stores_a_full_evaluation_and_updates_the_job_bucket(db_session: Session):
    """One pass fills the stored evaluation and the job's grouping bucket."""
    profile = add_profile(db_session)
    job = add_job(db_session)

    evaluation, change = evaluate_job(
        db_session, make_service(db_session), profile, job
    )

    assert change == "evaluated"
    assert evaluation.fit_bucket == FitBucket.POSSIBLE
    assert evaluation.internal_score is not None
    assert "Python" in evaluation.matched_skills
    assert "backend" in evaluation.matched_preferences
    assert evaluation.summary
    assert evaluation.model_provider == "mock"
    assert evaluation.model_name == "mock-eval-v1"
    assert evaluation.profile_version == profile.profile_version
    # The list view groups on the job, so it must track the evaluation.
    assert job.fit_bucket == FitBucket.POSSIBLE


def test_matching_more_preferences_reaches_the_strong_bucket(db_session: Session):
    """Bucket floors are real thresholds, not a single collapsed band."""
    profile = add_profile(db_session)
    job = add_job(db_session, title="Senior Python FastAPI Backend Engineer")

    evaluation, _ = evaluate_job(db_session, make_service(db_session), profile, job)

    assert evaluation.fit_bucket == FitBucket.STRONG


def test_records_uncertainty_and_verification_prompts(db_session: Session):
    """Uncertainty is derived from job facts, not asked of the provider."""
    profile = add_profile(db_session)
    job = add_job(
        db_session, remote_policy=RemotePolicy.UNCLEAR.value, salary_unknown=True
    )

    evaluation, _ = evaluate_job(db_session, make_service(db_session), profile, job)

    assert evaluation.salary_uncertainty == SalaryUncertainty.UNKNOWN
    assert evaluation.remote_uncertainty == RemoteUncertainty.UNCLEAR
    assert evaluation.work_auth_uncertainty == WorkAuthUncertainty.UNCLEAR
    assert "salary_unknown" in evaluation.uncertainties
    assert "remote_unclear" in evaluation.uncertainties
    assert "Confirm the salary range" in evaluation.verify_before_applying
    assert "Confirm the remote policy" in evaluation.verify_before_applying


def test_known_salary_is_not_reported_as_uncertain(db_session: Session):
    """A job with published pay carries no salary caveat."""
    profile = add_profile(db_session)
    job = add_job(db_session, salary_unknown=False)

    evaluation, _ = evaluate_job(db_session, make_service(db_session), profile, job)

    assert evaluation.salary_uncertainty == SalaryUncertainty.KNOWN
    assert "salary_unknown" not in evaluation.uncertainties
    assert "Confirm the salary range" not in evaluation.verify_before_applying


def test_reuses_a_stored_evaluation_instead_of_calling_again(db_session: Session):
    """Re-running a pass must not spend a second call on unchanged content."""
    profile = add_profile(db_session)
    job = add_job(db_session)
    first, _ = evaluate_job(db_session, make_service(db_session), profile, job)

    second, change = evaluate_job(db_session, make_service(db_session), profile, job)

    assert change == "reused"
    assert second.id == first.id
    assert db_session.scalar(select(func.count()).select_from(JobEvaluation)) == 1


def test_changed_job_content_earns_a_fresh_evaluation(db_session: Session):
    """Editing the facts an evaluation depends on invalidates the cache."""
    profile = add_profile(db_session)
    job = add_job(db_session)
    evaluate_job(db_session, make_service(db_session), profile, job)

    job.canonical_title = "Senior Blockchain Engineer"
    db_session.flush()
    evaluation, change = evaluate_job(
        db_session, make_service(db_session), profile, job
    )

    assert change == "evaluated"
    assert evaluation.job_content_hash == job_content_hash(job)
    assert db_session.scalar(select(func.count()).select_from(JobEvaluation)) == 2


def test_a_newer_profile_version_refreshes_the_evaluation_in_place(
    db_session: Session,
):
    """The schema allows one row per job, profile, and content hash."""
    profile = add_profile(db_session)
    job = add_job(db_session)
    first, _ = evaluate_job(db_session, make_service(db_session), profile, job)

    profile.profile_version = 2
    db_session.flush()
    second, change = evaluate_job(db_session, make_service(db_session), profile, job)

    assert change == "evaluated"
    assert second.id == first.id
    assert second.profile_version == 2
    assert db_session.scalar(select(func.count()).select_from(JobEvaluation)) == 1


def test_pending_pass_ranks_up_to_the_cap_and_reports_the_rest(db_session: Session):
    """A refresh returns useful results instead of exhausting the AI budget."""
    profile = add_profile(db_session)
    for index in range(5):
        add_job(db_session, title=f"Python Backend Engineer {index}")

    counts = evaluate_pending_jobs(
        db_session, make_service(db_session), profile, limit=2
    )

    assert counts == EvaluationRunCounts(evaluated=2, reused=0, pending=3)
    assert db_session.scalar(select(func.count()).select_from(JobEvaluation)) == 2


def test_a_second_pass_reuses_stored_work_and_clears_the_backlog(
    db_session: Session,
):
    """Cached evaluations are free, so they never consume the cap."""
    profile = add_profile(db_session)
    for index in range(4):
        add_job(db_session, title=f"Python Backend Engineer {index}")
    evaluate_pending_jobs(db_session, make_service(db_session), profile, limit=2)

    counts = evaluate_pending_jobs(
        db_session, make_service(db_session), profile, limit=2
    )

    assert counts == EvaluationRunCounts(evaluated=2, reused=2, pending=0)


def test_pending_pass_skips_jobs_the_user_closed_out(db_session: Session):
    """Dismissed and archived jobs are not worth an AI call."""
    profile = add_profile(db_session)
    add_job(db_session, status=JobStatus.DISMISSED)
    add_job(db_session, status=JobStatus.CLOSED_ARCHIVED)
    add_job(db_session, status=JobStatus.NEW)

    counts = evaluate_pending_jobs(db_session, make_service(db_session), profile)

    assert counts == EvaluationRunCounts(evaluated=1, reused=0, pending=0)


def test_a_zero_cap_evaluates_nothing_and_reports_everything_pending(
    db_session: Session,
):
    """A refresh with no AI budget still reports what is waiting."""
    profile = add_profile(db_session)
    add_job(db_session)

    counts = evaluate_pending_jobs(
        db_session, make_service(db_session), profile, limit=0
    )

    assert counts == EvaluationRunCounts(evaluated=0, reused=0, pending=1)


def test_rejects_an_unknown_fit_bucket_from_a_provider(db_session: Session):
    """A provider's one free-form field is validated at the boundary."""

    class RogueProvider:
        provider_name = "mock"
        model_name = "mock-eval-v1"

        def evaluate_job(
            self, request: AIJobEvaluationRequest
        ) -> AIJobEvaluationResult:
            return AIJobEvaluationResult(
                fit_bucket="excellent",
                summary=None,
                concerns=(),
                matched_skills=(),
            )

    profile = add_profile(db_session)
    job = add_job(db_session)

    with pytest.raises(ValueError, match="unknown fit bucket"):
        evaluate_job(db_session, AIService(RogueProvider(), db_session), profile, job)


def test_the_mock_scores_deterministically(db_session: Session):
    """The same job and profile always produce the same score and bucket."""
    profile = add_profile(db_session)
    job = add_job(db_session)
    service = make_service(db_session)

    first = service.evaluate_job(
        profile,
        AIJobEvaluationRequest(
            profile_id=profile.id,
            job_id=job.id,
            profile_version=1,
            job_content_hash="hash",
            job=AIJobSnapshot(
                title=job.canonical_title,
                company=job.canonical_company,
                location=job.canonical_location,
                remote_policy=job.remote_policy,
                salary_unknown=job.salary_unknown,
            ),
            profile=AIProfileSnapshot(
                target_role_families=("backend",),
                preferred_tech=("Python",),
                avoided_tech=(),
                dealbreakers=(),
                remote_preference=None,
                salary_floor=None,
            ),
        ),
    )
    second, _ = evaluate_job(db_session, service, profile, job)

    assert first.fit_bucket == second.fit_bucket.value
    assert isinstance(first.internal_score, Decimal)


def test_an_avoided_technology_drags_a_job_down_a_bucket(db_session: Session):
    """Stated dislikes must visibly move the ranking, not just be recorded."""
    profile = add_profile(db_session)
    liked = add_job(db_session, title="Senior Python Backend Engineer")
    disliked = add_job(db_session, title="Senior Blockchain Engineer")
    service = make_service(db_session)

    good, _ = evaluate_job(db_session, service, profile, liked)
    bad, _ = evaluate_job(db_session, service, profile, disliked)

    assert good.internal_score is not None and bad.internal_score is not None
    assert bad.internal_score < good.internal_score
    assert any("Blockchain" in concern for concern in bad.concerns)


def test_the_dashboard_api_serves_the_stored_evaluation(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Ranking is read from storage, never computed while a page loads."""
    profile = add_profile(db_session)
    job = add_job(db_session)
    evaluate_job(db_session, make_service(db_session), profile, job)

    detail = api_client.get(f"/api/jobs/{job.id}", headers=auth_headers).json()
    listed = api_client.get(
        "/api/jobs", params={"fit_bucket": ["possible"]}, headers=auth_headers
    ).json()

    assert detail["evaluation"]["fit_bucket"] == "possible"
    assert detail["evaluation"]["model_provider"] == "mock"
    assert "Confirm work authorization requirements" in (
        detail["evaluation"]["verify_before_applying"]
    )
    assert [item["id"] for item in listed["items"]] == [str(job.id)]


def test_eligibility_filter_skips_ineligible_jobs(db_session: Session):
    """Non-engineering roles and over-senior titles are filtered without AI calls."""
    profile = add_profile(db_session)
    add_job(db_session, title="Software Engineer", location="Remote (US)")
    add_job(db_session, title="Product Manager", location="Remote (US)")
    add_job(db_session, title="Staff Software Engineer", location="Remote (US)")

    counts = evaluate_pending_jobs(db_session, make_service(db_session), profile)

    assert counts.evaluated == 1
    assert counts.filtered == 2
    assert counts.pending == 0
    assert db_session.scalar(select(func.count()).select_from(JobEvaluation)) == 1


def test_eligibility_filter_does_not_count_against_cap(db_session: Session):
    """Filtered jobs leave more of the evaluation cap for eligible ones."""
    profile = add_profile(db_session)
    add_job(db_session, title="Backend Engineer 1", location="Remote (US)")
    add_job(db_session, title="Backend Engineer 2", location="Remote (US)")
    add_job(db_session, title="Product Manager", location="Remote (US)")
    add_job(db_session, title="Data Analyst", location="Remote (US)")

    counts = evaluate_pending_jobs(
        db_session, make_service(db_session), profile, limit=2
    )

    assert counts == EvaluationRunCounts(evaluated=2, reused=0, pending=0, filtered=2)
