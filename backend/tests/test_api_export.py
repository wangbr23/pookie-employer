"""Integration tests for the saved-jobs export API."""

import csv
import io
import json
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from pookie_backend.models import (
    FitBucket,
    Job,
    JobEvaluation,
    JobLink,
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


def _saved_job(
    session: Session,
    *,
    title: str = "Backend Engineer",
    company: str = "Acme",
    location: str = "Remote (US)",
    salary_min: Decimal | None = None,
    salary_max: Decimal | None = None,
    salary_currency: str | None = None,
    fit_bucket: FitBucket | None = None,
    add_link: bool = True,
) -> Job:
    job = Job(
        id=uuid4(),
        canonical_title=title,
        canonical_company=company,
        canonical_location=location,
        remote_policy="remote",
        salary_min=salary_min,
        salary_max=salary_max,
        salary_currency=salary_currency,
        salary_unknown=salary_min is None,
        status=JobStatus.SAVED,
        fit_bucket=fit_bucket,
        first_seen_at=BASE_TIME,
        last_seen_at=BASE_TIME,
    )
    session.add(job)
    session.flush()
    if add_link:
        link = JobLink(
            id=uuid4(),
            job_id=job.id,
            source_url="https://boards.greenhouse.io/acme/jobs/1",
            apply_url="https://boards.greenhouse.io/acme/jobs/1/apply",
            is_primary=True,
        )
        session.add(link)
        session.flush()
    return job


def _evaluation(
    session: Session,
    job: Job,
    profile: UserProfile,
    *,
    summary: str = "Strong backend match",
    concerns: list[str] | None = None,
    fit_bucket: FitBucket = FitBucket.STRONG,
) -> JobEvaluation:
    ev = JobEvaluation(
        id=uuid4(),
        job_id=job.id,
        profile_id=profile.id,
        profile_version=1,
        job_content_hash="abc123",
        fit_bucket=fit_bucket,
        internal_score=Decimal("0.85"),
        matched_skills=["Python"],
        matched_preferences=["remote"],
        concerns=concerns or ["No salary listed"],
        uncertainties=[],
        summary=summary,
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


def test_export_requires_authentication(api_client: TestClient):
    response = api_client.get("/api/export/saved")
    assert response.status_code == 401


def test_export_csv_with_saved_jobs(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    profile = _profile(db_session)
    job = _saved_job(db_session, salary_min=Decimal("120000"), salary_currency="USD")
    _evaluation(db_session, job, profile)

    response = api_client.get("/api/export/saved", headers=auth_headers)

    assert response.status_code == 200
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert "saved_jobs.csv" in response.headers["content-disposition"]

    reader = csv.DictReader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) == 1
    row = rows[0]
    assert row["title"] == "Backend Engineer"
    assert row["company"] == "Acme"
    assert row["fit_bucket"] == "strong"
    assert row["fit_summary"] == "Strong backend match"
    assert row["concerns"] == "No salary listed"
    assert row["apply_url"] == "https://boards.greenhouse.io/acme/jobs/1/apply"
    assert row["salary_min"] == "120000"
    assert row["salary_currency"] == "USD"


def test_export_json_with_saved_jobs(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    profile = _profile(db_session)
    job = _saved_job(db_session)
    _evaluation(db_session, job, profile, concerns=["Relocation", "Visa"])

    response = api_client.get(
        "/api/export/saved?format=json", headers=auth_headers
    )

    assert response.status_code == 200
    assert "application/json" in response.headers["content-type"]
    assert "saved_jobs.json" in response.headers["content-disposition"]

    data = json.loads(response.text)
    assert len(data) == 1
    assert data[0]["title"] == "Backend Engineer"
    assert data[0]["concerns"] == "Relocation; Visa"
    assert data[0]["apply_url"] == "https://boards.greenhouse.io/acme/jobs/1/apply"


def test_export_empty_returns_header_only_csv(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    _profile(db_session)

    response = api_client.get("/api/export/saved", headers=auth_headers)

    assert response.status_code == 200
    reader = csv.DictReader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) == 0
    assert "title" in reader.fieldnames


def test_export_excludes_non_saved_jobs(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    profile = _profile(db_session)
    saved = _saved_job(db_session, title="Saved Job")
    _evaluation(db_session, saved, profile)

    non_saved = Job(
        id=uuid4(),
        canonical_title="Not Saved",
        canonical_company="Other",
        canonical_location="SF",
        salary_unknown=True,
        status=JobStatus.NEW,
        first_seen_at=BASE_TIME,
        last_seen_at=BASE_TIME,
    )
    db_session.add(non_saved)
    db_session.flush()

    response = api_client.get("/api/export/saved", headers=auth_headers)
    reader = csv.DictReader(io.StringIO(response.text))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["title"] == "Saved Job"


def test_export_job_without_evaluation_uses_job_fit_bucket(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    _profile(db_session)
    _saved_job(db_session, fit_bucket=FitBucket.POSSIBLE)

    response = api_client.get("/api/export/saved?format=json", headers=auth_headers)
    data = json.loads(response.text)
    assert len(data) == 1
    assert data[0]["fit_bucket"] == "possible"
    assert data[0]["fit_summary"] is None
