"""Integration tests for crawl and raw-posting persistence."""

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pookie_backend.ingestion import (
    RawPostingInput,
    create_crawl_run,
    create_source_run,
    finish_source_run,
    persist_raw_postings,
    rollup_crawl_run_ai_usage,
    upsert_raw_posting,
)
from pookie_backend.models import (
    AiCallLog,
    AiCallStatus,
    ApprovalStatus,
    CrawlStatus,
    CrawlTrigger,
    JobSource,
    RawJobPosting,
    SourceKind,
    SourceRunStatus,
    UserProfile,
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


def _ai_profile(session: Session) -> UserProfile:
    profile = UserProfile(
        id=uuid4(), owner_user_id=f"owner-{uuid4()}", ai_consent_given=True
    )
    session.add(profile)
    session.flush()
    return profile


def _ai_call(
    session: Session,
    profile: UserProfile,
    crawl_run_id,
    *,
    call_count: int = 1,
    cost: Decimal | None = None,
) -> None:
    session.add(
        AiCallLog(
            id=uuid4(),
            profile_id=profile.id,
            provider="mock",
            model_name="mock-v1",
            operation="evaluate_job",
            status=AiCallStatus.SUCCEEDED,
            call_count=call_count,
            estimated_cost=cost,
            crawl_run_id=crawl_run_id,
        )
    )


def test_ai_usage_rollup_sums_calls_and_cost(db_session: Session) -> None:
    profile = _ai_profile(db_session)
    crawl_run = create_crawl_run(db_session, CrawlTrigger.ON_DEMAND)
    other_crawl = create_crawl_run(db_session, CrawlTrigger.MANUAL_SCRIPT)
    _ai_call(db_session, profile, crawl_run.id, cost=Decimal("0.0100"))
    _ai_call(
        db_session,
        profile,
        crawl_run.id,
        call_count=2,
        cost=Decimal("0.0250"),
    )
    _ai_call(db_session, profile, other_crawl.id, cost=Decimal("9.99"))

    crawl_run = rollup_crawl_run_ai_usage(db_session, crawl_run.id)

    assert crawl_run.ai_call_count == 3
    assert crawl_run.estimated_ai_cost == Decimal("0.0350")


def test_ai_usage_rollup_is_idempotent_and_handles_no_calls(
    db_session: Session,
) -> None:
    profile = _ai_profile(db_session)
    crawl_run = create_crawl_run(db_session, CrawlTrigger.ON_DEMAND)
    _ai_call(db_session, profile, crawl_run.id, cost=Decimal("0.0100"))

    rollup_crawl_run_ai_usage(db_session, crawl_run.id)
    crawl_run = rollup_crawl_run_ai_usage(db_session, crawl_run.id)

    assert crawl_run.ai_call_count == 1
    assert crawl_run.estimated_ai_cost == Decimal("0.0100")

    other = create_crawl_run(db_session, CrawlTrigger.ON_DEMAND)
    other = rollup_crawl_run_ai_usage(db_session, other.id)
    assert other.ai_call_count == 0
    assert other.estimated_ai_cost is None
