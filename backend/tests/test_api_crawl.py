"""Integration tests for the refresh and rerank trigger stubs."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pookie_backend.models import (
    ApprovalStatus,
    CrawlRun,
    CrawlStatus,
    CrawlTrigger,
    FitBucket,
    Job,
    JobSource,
    JobStatus,
    SourceKind,
    SourceRun,
    SourceRunStatus,
)

BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def add_job(
    session: Session,
    *,
    status: JobStatus = JobStatus.NEW,
    fit_bucket: FitBucket | None = None,
) -> Job:
    job = Job(
        id=uuid4(),
        canonical_title="Senior Backend Engineer",
        canonical_company="Astral",
        canonical_location="Remote (US)",
        remote_policy="remote",
        salary_unknown=True,
        status=status,
        fit_bucket=fit_bucket,
        first_seen_at=BASE_TIME,
        last_seen_at=BASE_TIME,
    )
    session.add(job)
    session.flush()
    return job


def add_running_crawl(session: Session) -> CrawlRun:
    crawl_run = CrawlRun(
        id=uuid4(),
        trigger=CrawlTrigger.ON_DEMAND,
        status=CrawlStatus.RUNNING,
        started_at=BASE_TIME,
    )
    session.add(crawl_run)
    session.flush()
    return crawl_run


def count_crawl_runs(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(CrawlRun)) or 0


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("post", "/api/crawl/run"),
        ("get", f"/api/crawl/runs/{uuid4()}"),
        ("post", "/api/rank/run"),
    ],
)
def test_trigger_endpoints_require_authentication(
    api_client: TestClient, method: str, path: str
):
    """Refresh and rerank stay protected even with a single user."""
    assert getattr(api_client, method)(path).status_code == 401


def test_triggering_a_refresh_records_a_finished_run(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """A refresh leaves a real run record, finished rather than stranded."""
    response = api_client.post("/api/crawl/run", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["trigger"] == "on_demand"
    assert body["status"] == "success"
    assert body["finished_at"] is not None
    assert body["sources_attempted"] == 0
    assert body["jobs_discovered"] == 0
    assert body["sources"] == []
    assert count_crawl_runs(db_session) == 1


def test_a_second_refresh_is_refused_while_one_is_running(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """A double-clicked Refresh must not start overlapping crawls."""
    running = add_running_crawl(db_session)

    response = api_client.post("/api/crawl/run", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "refresh_already_running"
    assert str(running.id) in response.json()["detail"]["message"]
    assert count_crawl_runs(db_session) == 1


def test_a_finished_run_does_not_block_the_next_refresh(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Only a run still in flight blocks; finished history never does."""
    api_client.post("/api/crawl/run", headers=auth_headers)

    second = api_client.post("/api/crawl/run", headers=auth_headers)

    assert second.status_code == 200
    assert count_crawl_runs(db_session) == 2


def test_refresh_status_reports_per_source_detail(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Status polling returns the same shape the coverage view uses."""
    crawl_run = add_running_crawl(db_session)
    source = JobSource(
        id=uuid4(),
        kind=SourceKind.GREENHOUSE,
        name="Astral Jobs",
        company_name="Astral",
        base_url="https://boards.greenhouse.io/astral",
        approval_status=ApprovalStatus.APPROVED,
    )
    db_session.add(source)
    db_session.flush()
    db_session.add(
        SourceRun(
            id=uuid4(),
            crawl_run_id=crawl_run.id,
            job_source_id=source.id,
            status=SourceRunStatus.FAILED,
            started_at=BASE_TIME,
            error_summary="Timed out after 8s",
        )
    )
    db_session.flush()

    body = api_client.get(
        f"/api/crawl/runs/{crawl_run.id}", headers=auth_headers
    ).json()

    assert body["id"] == str(crawl_run.id)
    assert body["status"] == "running"
    assert len(body["sources"]) == 1
    assert body["sources"][0]["source_name"] == "Astral Jobs"
    assert body["sources"][0]["error_summary"] == "Timed out after 8s"


def test_status_for_an_unknown_run_returns_a_structured_404(
    api_client: TestClient, auth_headers: dict[str, str]
):
    """A stale run id answers in the project's error shape."""
    response = api_client.get(f"/api/crawl/runs/{uuid4()}", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "crawl_run_not_found",
        "message": "Crawl run not found.",
    }


def test_rerank_reports_the_backlog_without_ranking_anything(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """The stub measures the work; it never calls a provider."""
    add_job(db_session, fit_bucket=None)
    add_job(db_session, fit_bucket=None)
    add_job(db_session, fit_bucket=FitBucket.STRONG)

    body = api_client.post("/api/rank/run", headers=auth_headers).json()

    assert body["jobs_considered"] == 3
    assert body["jobs_awaiting_evaluation"] == 2
    assert body["evaluations_run"] == 0


def test_rerank_ignores_jobs_the_user_closed_out(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Dismissed and archived jobs are not ranking candidates."""
    add_job(db_session, status=JobStatus.DISMISSED)
    add_job(db_session, status=JobStatus.CLOSED_ARCHIVED)
    add_job(db_session, status=JobStatus.NEW)

    body = api_client.post("/api/rank/run", headers=auth_headers).json()

    assert body["jobs_considered"] == 1
    assert body["jobs_awaiting_evaluation"] == 1


def test_rerank_on_an_empty_database_reports_nothing_to_do(
    api_client: TestClient, auth_headers: dict[str, str]
):
    """An empty backlog is a valid answer, not an error."""
    body = api_client.post("/api/rank/run", headers=auth_headers).json()

    assert body == {
        "jobs_considered": 0,
        "jobs_awaiting_evaluation": 0,
        "evaluations_run": 0,
    }
