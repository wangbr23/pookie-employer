"""Integration tests for the debug coverage API."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from pookie_backend.models import (
    ApprovalStatus,
    CrawlRun,
    CrawlStatus,
    CrawlTrigger,
    JobSource,
    SourceKind,
    SourceRun,
    SourceRunStatus,
)

BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def add_source(session: Session, name: str, company: str) -> JobSource:
    source = JobSource(
        id=uuid4(),
        kind=SourceKind.GREENHOUSE,
        name=name,
        company_name=company,
        base_url=f"https://boards.greenhouse.io/{company.lower()}",
        external_board_id=company.lower(),
        approval_status=ApprovalStatus.APPROVED,
    )
    session.add(source)
    session.flush()
    return source


def add_crawl_run(
    session: Session, *, started_at: datetime, status: CrawlStatus
) -> CrawlRun:
    crawl_run = CrawlRun(
        id=uuid4(),
        trigger=CrawlTrigger.ON_DEMAND,
        status=status,
        started_at=started_at,
        elapsed_milliseconds=41_000,
        evaluations_pending=3,
        ai_call_count=12,
        estimated_ai_cost=Decimal("0.042000"),
    )
    session.add(crawl_run)
    session.flush()
    return crawl_run


def add_source_run(
    session: Session,
    crawl_run: CrawlRun,
    source: JobSource,
    *,
    status: SourceRunStatus,
    error_summary: str | None = None,
) -> SourceRun:
    source_run = SourceRun(
        id=uuid4(),
        crawl_run_id=crawl_run.id,
        job_source_id=source.id,
        status=status,
        started_at=crawl_run.started_at,
        jobs_discovered=4,
        jobs_inserted=2,
        jobs_updated=1,
        jobs_skipped=1,
        error_summary=error_summary,
    )
    session.add(source_run)
    session.flush()
    return source_run


def test_coverage_requires_authentication(api_client: TestClient):
    """The debug view sits behind the shared-secret boundary like every /api route."""
    assert api_client.get("/api/debug/coverage").status_code == 401


def test_coverage_reports_latest_run_with_partial_failure_detail(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Coverage surfaces the newest run, its cost/timing, and the failing source."""
    healthy = add_source(db_session, "Astral Jobs", "Astral")
    broken = add_source(db_session, "Ramp Careers", "Ramp")
    add_crawl_run(db_session, started_at=BASE_TIME, status=CrawlStatus.SUCCESS)
    latest = add_crawl_run(
        db_session,
        started_at=datetime(2026, 9, 2, 12, 0, tzinfo=UTC),
        status=CrawlStatus.PARTIAL_SUCCESS,
    )
    add_source_run(db_session, latest, healthy, status=SourceRunStatus.SUCCESS)
    add_source_run(
        db_session,
        latest,
        broken,
        status=SourceRunStatus.FAILED,
        error_summary="Timed out after 8s",
    )

    response = api_client.get("/api/debug/coverage", headers=auth_headers)

    assert response.status_code == 200
    run = response.json()["last_crawl_run"]
    assert run["id"] == str(latest.id)
    assert run["status"] == "partial_success"
    assert run["trigger"] == "on_demand"
    assert run["elapsed_milliseconds"] == 41_000
    assert run["evaluations_pending"] == 3
    assert run["ai_call_count"] == 12
    assert Decimal(run["estimated_ai_cost"]) == Decimal("0.042000")

    failed = next(source for source in run["sources"] if source["status"] == "failed")
    assert failed["source_name"] == "Ramp Careers"
    assert failed["company_name"] == "Ramp"
    assert failed["kind"] == "greenhouse"
    assert failed["error_summary"] == "Timed out after 8s"
    assert failed["jobs_discovered"] == 4


def test_coverage_lists_configured_sources_with_standing_health(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Every configured source is listed even when no crawl has touched it."""
    source = add_source(db_session, "Astral Jobs", "Astral")
    source.last_successful_crawl_at = BASE_TIME
    source.last_error_summary = "HTTP 503 from board"
    source.last_error_at = BASE_TIME
    db_session.flush()

    body = api_client.get("/api/debug/coverage", headers=auth_headers).json()

    listed = next(item for item in body["sources"] if item["id"] == str(source.id))
    assert listed["name"] == "Astral Jobs"
    assert listed["kind"] == "greenhouse"
    assert listed["status"] == "active"
    assert listed["approval_status"] == "approved"
    assert listed["last_error_summary"] == "HTTP 503 from board"
    assert listed["last_successful_crawl_at"].startswith("2026-09-01")


def test_coverage_reports_no_run_before_the_first_crawl(
    api_client: TestClient, auth_headers: dict[str, str]
):
    """Before any crawl exists the view renders an empty state, not an error."""
    body = api_client.get("/api/debug/coverage", headers=auth_headers).json()

    assert body["last_crawl_run"] is None
