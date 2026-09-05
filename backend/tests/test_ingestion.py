"""Integration tests for crawl and raw-posting persistence."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pookie_backend.ingestion import (
    RawPostingInput,
    create_crawl_run,
    create_source_run,
    finish_source_run,
    persist_raw_postings,
    upsert_raw_posting,
)
from pookie_backend.models import (
    ApprovalStatus,
    CrawlStatus,
    CrawlTrigger,
    JobSource,
    RawJobPosting,
    SourceKind,
    SourceRunStatus,
)


def add_source(session: Session, name: str) -> JobSource:
    source = JobSource(
        id=uuid4(),
        kind=SourceKind.COMPANY_PAGE,
        name=name,
        company_name=name,
        base_url="https://example.com/jobs",
        approval_status=ApprovalStatus.APPROVED,
    )
    session.add(source)
    session.flush()
    return source


def posting(title: str = "Software Engineer") -> RawPostingInput:
    return RawPostingInput(
        source_posting_id="job-1",
        source_url="https://example.com/jobs/job-1",
        apply_url="https://example.com/apply/job-1",
        raw_title=title,
        raw_company="Example Co",
        raw_location="Remote",
        raw_description="Build useful software.",
    )


def test_raw_posting_upsert_is_idempotent_and_detects_changes(
    db_session: Session,
) -> None:
    source = add_source(db_session, "Upsert source")
    first_seen = datetime(2026, 1, 1, tzinfo=UTC)
    second_seen = datetime(2026, 1, 2, tzinfo=UTC)

    row, first_kind = upsert_raw_posting(
        db_session, source.id, posting(), seen_at=first_seen
    )
    original_hash = row.content_hash
    same_row, same_kind = upsert_raw_posting(
        db_session, source.id, posting(), seen_at=second_seen
    )

    assert first_kind == "inserted"
    assert same_kind == "skipped"
    assert same_row.id == row.id
    assert same_row.last_seen_at == second_seen
    assert db_session.scalar(select(func.count()).select_from(RawJobPosting)) == 1

    changed_row, changed_kind = upsert_raw_posting(
        db_session,
        source.id,
        posting("Senior Software Engineer"),
        seen_at=second_seen,
    )
    assert changed_kind == "updated"
    assert changed_row.id == row.id
    assert changed_row.content_hash != original_hash


def test_partial_source_failure_preserves_successful_postings(
    db_session: Session,
) -> None:
    successful_source = add_source(db_session, "Successful source")
    failed_source = add_source(db_session, "Failed source")
    crawl_run = create_crawl_run(db_session, CrawlTrigger.MANUAL_SCRIPT)
    successful_run = create_source_run(db_session, crawl_run.id, successful_source.id)
    failed_run = create_source_run(db_session, crawl_run.id, failed_source.id)

    counts = persist_raw_postings(db_session, successful_run, [posting()])
    finish_source_run(db_session, successful_run, status=SourceRunStatus.SUCCESS)
    finish_source_run(
        db_session,
        failed_run,
        status=SourceRunStatus.FAILED,
        error_summary="source timed out",
    )
    db_session.refresh(crawl_run)

    assert counts.inserted == 1
    assert successful_run.jobs_inserted == 1
    assert failed_run.error_summary == "source timed out"
    assert crawl_run.status == CrawlStatus.PARTIAL_SUCCESS
    assert crawl_run.sources_succeeded == 1
    assert crawl_run.sources_failed == 1
    assert crawl_run.jobs_new == 1
    assert db_session.scalar(select(func.count()).select_from(RawJobPosting)) == 1
