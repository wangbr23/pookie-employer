"""Persistence helpers for crawl runs and raw source postings."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from pookie_backend.models import (
    CrawlRun,
    CrawlStatus,
    CrawlTrigger,
    RawJobPosting,
    SourceRun,
    SourceRunStatus,
)


@dataclass(frozen=True)
class RawPostingInput:
    """Already-fetched posting fields accepted by the persistence layer."""

    source_posting_id: str
    source_url: str
    raw_title: str
    apply_url: str | None = None
    raw_company: str | None = None
    raw_location: str | None = None
    raw_description: str | None = None


@dataclass(frozen=True)
class PostingPersistenceCounts:
    """Insert/update/skip counts for one source result."""

    discovered: int
    inserted: int
    updated: int
    skipped: int


ChangeKind = Literal["inserted", "updated", "skipped"]


def create_crawl_run(session: Session, trigger: CrawlTrigger) -> CrawlRun:
    """Create a running crawl record and return it after flushing its id."""
    crawl_run = CrawlRun(trigger=trigger, status=CrawlStatus.RUNNING)
    session.add(crawl_run)
    session.flush()
    return crawl_run


def create_source_run(
    session: Session, crawl_run_id: UUID, job_source_id: UUID
) -> SourceRun:
    """Create a running source record within an existing crawl."""
    source_run = SourceRun(
        crawl_run_id=crawl_run_id,
        job_source_id=job_source_id,
        status=SourceRunStatus.RUNNING,
    )
    session.add(source_run)
    session.flush()
    return source_run


def content_hash(posting: RawPostingInput) -> str:
    """Return a stable hash of the source content used for change detection."""
    values = (
        posting.raw_title,
        posting.raw_company,
        posting.raw_location,
        posting.raw_description,
    )
    normalized = "\x1f".join((value or "").strip() for value in values)
    return sha256(normalized.encode("utf-8")).hexdigest()


def upsert_raw_posting(
    session: Session,
    job_source_id: UUID,
    posting: RawPostingInput,
    *,
    seen_at: datetime | None = None,
) -> tuple[RawJobPosting, ChangeKind]:
    """Insert or re-sight a posting, returning the row and its change kind."""
    existing = session.scalar(
        select(RawJobPosting).where(
            RawJobPosting.job_source_id == job_source_id,
            RawJobPosting.source_posting_id == posting.source_posting_id,
        )
    )
    observed_at = seen_at or datetime.now().astimezone()
    posting_hash = content_hash(posting)

    if existing is None:
        existing = RawJobPosting(
            job_source_id=job_source_id,
            source_posting_id=posting.source_posting_id,
            source_url=posting.source_url,
            apply_url=posting.apply_url,
            raw_title=posting.raw_title,
            raw_company=posting.raw_company,
            raw_location=posting.raw_location,
            raw_description=posting.raw_description,
            content_hash=posting_hash,
            first_seen_at=observed_at,
            last_seen_at=observed_at,
        )
        session.add(existing)
        session.flush()
        return existing, "inserted"

    changed = existing.content_hash != posting_hash
    existing.source_url = posting.source_url
    existing.apply_url = posting.apply_url
    existing.raw_title = posting.raw_title
    existing.raw_company = posting.raw_company
    existing.raw_location = posting.raw_location
    existing.raw_description = posting.raw_description
    existing.content_hash = posting_hash
    existing.last_seen_at = observed_at
    session.flush()
    return existing, "updated" if changed else "skipped"


def persist_raw_postings(
    session: Session,
    source_run: SourceRun,
    postings: Sequence[RawPostingInput],
    *,
    seen_at: datetime | None = None,
) -> PostingPersistenceCounts:
    """Persist fetched postings and record their source-level counts."""
    counts = {"inserted": 0, "updated": 0, "skipped": 0}
    for posting in postings:
        _, change_kind = upsert_raw_posting(
            session, source_run.job_source_id, posting, seen_at=seen_at
        )
        counts[change_kind] += 1

    source_run.jobs_discovered = len(postings)
    source_run.jobs_inserted = counts["inserted"]
    source_run.jobs_updated = counts["updated"]
    source_run.jobs_skipped = counts["skipped"]
    session.flush()
    return PostingPersistenceCounts(len(postings), **counts)


def finish_source_run(
    session: Session,
    source_run: SourceRun,
    *,
    status: SourceRunStatus,
    error_summary: str | None = None,
    finished_at: datetime | None = None,
) -> SourceRun:
    """Record terminal source status and its optional error summary."""
    if status == SourceRunStatus.RUNNING:
        raise ValueError("A source run can only be finished with a terminal status")
    source_run.status = status
    source_run.error_summary = error_summary
    source_run.finished_at = finished_at or datetime.now().astimezone()
    session.flush()
    rollup_crawl_run(session, source_run.crawl_run_id)
    return source_run


def rollup_crawl_run(session: Session, crawl_run_id: UUID) -> CrawlRun:
    """Roll source counts into a crawl and finalize it when all sources finish.

    Finalization considers only the ``SourceRun`` rows that already exist for
    this crawl: if they are all terminal, the crawl is marked done. Callers
    must therefore create every source run for a crawl (via
    `create_source_run`) before finishing any of them - finishing sources one
    at a time as they are created would finalize the crawl after the first
    one completes, then silently "reopen" and re-finalize it as later sources
    are added.
    """
    crawl_run = session.get(CrawlRun, crawl_run_id)
    if crawl_run is None:
        raise ValueError(f"Crawl run {crawl_run_id} does not exist")

    source_runs = session.scalars(
        select(SourceRun).where(SourceRun.crawl_run_id == crawl_run_id)
    ).all()
    terminal_runs = [
        run for run in source_runs if run.status != SourceRunStatus.RUNNING
    ]
    failed = sum(run.status == SourceRunStatus.FAILED for run in source_runs)
    succeeded = sum(run.status == SourceRunStatus.SUCCESS for run in source_runs)
    crawl_run.sources_attempted = sum(
        run.status != SourceRunStatus.SKIPPED for run in source_runs
    )
    crawl_run.sources_succeeded = succeeded
    crawl_run.sources_failed = failed
    crawl_run.jobs_discovered = sum(run.jobs_discovered for run in source_runs)
    crawl_run.jobs_new = sum(run.jobs_inserted for run in source_runs)
    crawl_run.jobs_updated = sum(run.jobs_updated for run in source_runs)
    crawl_run.jobs_skipped = sum(run.jobs_skipped for run in source_runs)

    if source_runs and len(terminal_runs) == len(source_runs):
        if failed and succeeded:
            crawl_run.status = CrawlStatus.PARTIAL_SUCCESS
        elif failed:
            crawl_run.status = CrawlStatus.FAILED
        else:
            crawl_run.status = CrawlStatus.SUCCESS
        crawl_run.finished_at = datetime.now().astimezone()
    session.flush()
    return crawl_run
