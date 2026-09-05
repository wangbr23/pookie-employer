"""Integration tests for the read-only jobs API."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from pookie_backend.models import (
    FitBucket,
    Job,
    JobEvaluation,
    JobLink,
    JobLinkStatus,
    JobStatus,
    RemoteUncertainty,
    SalaryUncertainty,
    UserProfile,
    WorkAuthUncertainty,
)

BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def add_job(
    session: Session,
    *,
    title: str = "Senior Backend Engineer",
    company: str = "Astral",
    status: JobStatus = JobStatus.NEW,
    fit_bucket: FitBucket | None = FitBucket.STRONG,
    first_seen_at: datetime = BASE_TIME,
) -> Job:
    """Insert one canonical job with the fields the API reads."""
    job = Job(
        id=uuid4(),
        canonical_title=title,
        canonical_company=company,
        canonical_location="Remote (US)",
        remote_policy="remote",
        employment_type="full_time",
        salary_min=Decimal("180000.00"),
        salary_max=Decimal("220000.00"),
        salary_currency="USD",
        salary_unknown=False,
        seniority="senior",
        status=status,
        fit_bucket=fit_bucket,
        first_seen_at=first_seen_at,
        last_seen_at=first_seen_at,
    )
    session.add(job)
    session.flush()
    return job


def add_link(
    session: Session,
    job: Job,
    *,
    apply_url: str,
    is_primary: bool = False,
    status: JobLinkStatus = JobLinkStatus.ACTIVE,
) -> JobLink:
    link = JobLink(
        id=uuid4(),
        job_id=job.id,
        source_url=f"{apply_url}/posting",
        apply_url=apply_url,
        is_primary=is_primary,
        status=status,
    )
    session.add(link)
    session.flush()
    return link


def add_profile(session: Session) -> UserProfile:
    profile = UserProfile(id=uuid4(), owner_user_id=f"test-{uuid4()}")
    session.add(profile)
    session.flush()
    return profile


def add_evaluation(session: Session, job: Job, profile: UserProfile) -> JobEvaluation:
    evaluation = JobEvaluation(
        id=uuid4(),
        job_id=job.id,
        profile_id=profile.id,
        profile_version=1,
        job_content_hash="hash-1",
        fit_bucket=FitBucket.STRONG,
        internal_score=Decimal("0.870"),
        matched_skills=["Python", "FastAPI"],
        matched_preferences=["remote"],
        concerns=["On-call rotation is unclear"],
        uncertainties=["Team size unknown"],
        summary="Strong backend match on Python and platform work.",
        verify_before_applying=["Confirm remote policy"],
        salary_uncertainty=SalaryUncertainty.KNOWN,
        remote_uncertainty=RemoteUncertainty.CLEAR,
        work_auth_uncertainty=WorkAuthUncertainty.CLEAR,
        model_provider="mock",
        model_name="mock-eval-1",
    )
    session.add(evaluation)
    session.flush()
    return evaluation


def test_job_endpoints_require_authentication(api_client: TestClient):
    """Both job routes sit behind the shared-secret boundary."""
    assert api_client.get("/api/jobs").status_code == 401
    assert api_client.get(f"/api/jobs/{uuid4()}").status_code == 401


def test_list_jobs_returns_card_fields_newest_first(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """The list returns job-card fields ordered by most recently discovered."""
    older = add_job(db_session, title="Older Role", first_seen_at=BASE_TIME)
    newer = add_job(
        db_session, title="Newer Role", first_seen_at=BASE_TIME + timedelta(days=1)
    )
    add_link(
        db_session, newer, apply_url="https://boards.example/newer", is_primary=True
    )

    response = api_client.get("/api/jobs", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 50
    assert body["offset"] == 0
    assert [item["id"] for item in body["items"]] == [str(newer.id), str(older.id)]
    first = body["items"][0]
    assert first["canonical_title"] == "Newer Role"
    assert first["canonical_company"] == "Astral"
    assert first["fit_bucket"] == "strong"
    assert first["status"] == "new"
    assert first["apply_url"] == "https://boards.example/newer"
    assert body["items"][1]["apply_url"] is None


def test_list_jobs_filters_by_status_and_fit_bucket(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Repeatable status/fit filters back the Saved, All Jobs, and For You views."""
    saved = add_job(db_session, status=JobStatus.SAVED, fit_bucket=FitBucket.STRONG)
    add_job(db_session, status=JobStatus.DISMISSED, fit_bucket=FitBucket.STRETCH)
    stretch = add_job(db_session, status=JobStatus.NEW, fit_bucket=FitBucket.STRETCH)

    by_status = api_client.get(
        "/api/jobs", params={"status": ["saved"]}, headers=auth_headers
    ).json()
    by_fit = api_client.get(
        "/api/jobs",
        params={"fit_bucket": ["stretch"], "status": ["new"]},
        headers=auth_headers,
    ).json()

    assert [item["id"] for item in by_status["items"]] == [str(saved.id)]
    assert [item["id"] for item in by_fit["items"]] == [str(stretch.id)]


def test_list_jobs_search_matches_title_or_company_literally(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Search covers title and company, treating wildcards as literal text."""
    platform = add_job(db_session, title="Platform Engineer", company="Ramp")
    add_job(db_session, title="Data Scientist", company="Linear")

    by_title = api_client.get(
        "/api/jobs", params={"search": "platform"}, headers=auth_headers
    ).json()
    by_company = api_client.get(
        "/api/jobs", params={"search": "ramp"}, headers=auth_headers
    ).json()
    wildcard = api_client.get(
        "/api/jobs", params={"search": "%"}, headers=auth_headers
    ).json()

    assert [item["id"] for item in by_title["items"]] == [str(platform.id)]
    assert [item["id"] for item in by_company["items"]] == [str(platform.id)]
    assert wildcard["total"] == 0


def test_list_jobs_pages_with_limit_and_offset(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Paging returns one page at a time while total counts every match."""
    for offset_days in range(3):
        add_job(db_session, first_seen_at=BASE_TIME + timedelta(days=offset_days))

    page = api_client.get(
        "/api/jobs", params={"limit": 2, "offset": 2}, headers=auth_headers
    ).json()

    assert page["total"] == 3
    assert len(page["items"]) == 1
    assert page["limit"] == 2
    assert page["offset"] == 2


def test_list_jobs_rejects_out_of_range_limit(
    api_client: TestClient, auth_headers: dict[str, str]
):
    """An oversized page size is rejected rather than silently clamped."""
    response = api_client.get("/api/jobs", params={"limit": 500}, headers=auth_headers)

    assert response.status_code == 422


def test_get_job_returns_evaluation_and_all_links(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Detail carries the stored fit explanation and every preserved link."""
    job = add_job(db_session)
    add_link(
        db_session, job, apply_url="https://boards.example/primary", is_primary=True
    )
    add_link(db_session, job, apply_url="https://boards.example/mirror")
    add_evaluation(db_session, job, add_profile(db_session))

    response = api_client.get(f"/api/jobs/{job.id}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(job.id)
    assert body["apply_url"] == "https://boards.example/primary"
    assert len(body["links"]) == 2
    evaluation = body["evaluation"]
    assert evaluation["fit_bucket"] == "strong"
    assert evaluation["summary"] == "Strong backend match on Python and platform work."
    assert evaluation["concerns"] == ["On-call rotation is unclear"]
    assert evaluation["salary_uncertainty"] == "known"
    assert evaluation["model_provider"] == "mock"


def test_get_job_returns_null_evaluation_when_not_yet_ranked(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """An unranked job is still readable; the API never evaluates on request."""
    job = add_job(db_session, fit_bucket=None)

    body = api_client.get(f"/api/jobs/{job.id}", headers=auth_headers).json()

    assert body["evaluation"] is None
    assert body["fit_bucket"] is None
    assert body["links"] == []


def test_get_job_prefers_an_active_link_over_a_broken_primary(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """A dead primary link must not become the Apply button's target."""
    job = add_job(db_session)
    add_link(
        db_session,
        job,
        apply_url="https://boards.example/dead",
        is_primary=True,
        status=JobLinkStatus.CLOSED,
    )
    add_link(db_session, job, apply_url="https://boards.example/live")

    body = api_client.get(f"/api/jobs/{job.id}", headers=auth_headers).json()

    assert body["apply_url"] == "https://boards.example/live"


def test_get_job_returns_structured_404_for_unknown_id(
    api_client: TestClient, auth_headers: dict[str, str]
):
    """A missing job returns the project's structured error shape."""
    response = api_client.get(f"/api/jobs/{uuid4()}", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "job_not_found",
        "message": "Job not found.",
    }
