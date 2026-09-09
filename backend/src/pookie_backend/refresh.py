"""Bounded on-demand refresh orchestrator.

Fetches approved sources concurrently, persists raw postings, runs
normalization + dedupe, and evaluates new jobs — all within configurable
time budgets.
"""

from __future__ import annotations

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from pookie_backend.adapters.ashby import AshbyResult, fetch_ashby_postings
from pookie_backend.adapters.greenhouse import (
    GreenhouseResult,
    fetch_greenhouse_postings,
)
from pookie_backend.adapters.lever import LeverResult, fetch_lever_postings
from pookie_backend.adapters.netflix import NetflixResult, fetch_netflix_postings
from pookie_backend.adapters.phenom import PhenomResult, fetch_phenom_postings
from pookie_backend.adapters.workday import (
    WorkdayResult,
    fetch_workday_postings,
)
from pookie_backend.ai import AIProvider, AIService, create_provider
from pookie_backend.dedupe import dedupe_and_upsert
from pookie_backend.evaluation import EvaluationRunCounts, evaluate_pending_jobs
from pookie_backend.ingestion import (
    RawPostingInput,
    create_crawl_run,
    create_source_run,
    finish_source_run,
    upsert_raw_posting,
)
from pookie_backend.models import (
    ApprovalStatus,
    CrawlRun,
    CrawlStatus,
    CrawlTrigger,
    JobSource,
    RawJobPosting,
    SourceKind,
    SourceRun,
    SourceRunStatus,
    SourceStatus,
    UserProfile,
)
from pookie_backend.normalization import normalize_posting

log = logging.getLogger(__name__)

# --- defaults (design: §On-demand refresh performance approach) ---

SOURCE_CONCURRENCY = 4
SOURCE_TIMEOUT_SECONDS = 8.0
CRAWL_BUDGET_SECONDS = 60.0
EVALUATION_CAP = 25


@dataclass(frozen=True)
class SourceFetchResult:
    """What one adapter returned, before persistence."""

    source_id: UUID
    postings: list[RawPostingInput]
    error: str | None


def _fetch_source(source: JobSource, timeout: float) -> SourceFetchResult:
    """Call the right adapter for *source* and return a uniform result."""
    kind = source.kind
    r: GreenhouseResult | LeverResult | AshbyResult | WorkdayResult | NetflixResult | PhenomResult
    if kind == SourceKind.GREENHOUSE:
        r = fetch_greenhouse_postings(source, timeout=timeout)
    elif kind == SourceKind.LEVER:
        r = fetch_lever_postings(source, timeout=timeout)
    elif kind == SourceKind.ASHBY:
        r = fetch_ashby_postings(source, timeout=timeout)
    elif kind == SourceKind.WORKDAY:
        r = fetch_workday_postings(source, timeout=timeout)
    elif kind == SourceKind.NETFLIX:
        r = fetch_netflix_postings(source, timeout=timeout)
    elif kind == SourceKind.PHENOM:
        r = fetch_phenom_postings(source, timeout=timeout)
    else:
        return SourceFetchResult(
            source_id=source.id,
            postings=[],
            error=f"no adapter for source kind {kind}",
        )
    return SourceFetchResult(
        source_id=source.id,
        postings=list(r.postings),
        error=r.error,
    )


@dataclass(frozen=True)
class RefreshResult:
    """Aggregate outcome returned to the caller (API endpoint / CLI)."""

    crawl_run_id: UUID
    sources_attempted: int
    sources_succeeded: int
    sources_failed: int
    sources_timed_out: int
    jobs_discovered: int
    jobs_new: int
    jobs_updated: int
    jobs_skipped: int
    evaluation_counts: EvaluationRunCounts | None
    elapsed_seconds: float


def run_refresh(
    session: Session,
    *,
    trigger: CrawlTrigger = CrawlTrigger.ON_DEMAND,
    concurrency: int = SOURCE_CONCURRENCY,
    source_timeout: float = SOURCE_TIMEOUT_SECONDS,
    crawl_budget: float = CRAWL_BUDGET_SECONDS,
    evaluation_cap: int = EVALUATION_CAP,
    ai_provider: AIProvider | None = None,
) -> RefreshResult:
    """Orchestrate one full refresh cycle.

    1. Query approved+active sources.
    2. Fetch them concurrently with bounded concurrency and per-source timeout.
    3. Persist raw postings, normalize, dedupe.
    4. Evaluate new jobs up to *evaluation_cap*.
    5. Roll up counts on the CrawlRun.
    """
    wall_start = time.monotonic()
    deadline = wall_start + crawl_budget

    crawl_run = create_crawl_run(session, trigger)

    sources = session.scalars(
        select(JobSource).where(
            JobSource.status == SourceStatus.ACTIVE,
            JobSource.approval_status == ApprovalStatus.APPROVED,
        )
    ).all()

    if not sources:
        crawl_run.status = CrawlStatus.SUCCESS
        crawl_run.finished_at = datetime.now().astimezone()
        crawl_run.elapsed_milliseconds = 0
        session.flush()
        return RefreshResult(
            crawl_run_id=crawl_run.id,
            sources_attempted=0,
            sources_succeeded=0,
            sources_failed=0,
            sources_timed_out=0,
            jobs_discovered=0,
            jobs_new=0,
            jobs_updated=0,
            jobs_skipped=0,
            evaluation_counts=None,
            elapsed_seconds=0.0,
        )

    source_runs = {
        source.id: create_source_run(session, crawl_run.id, source.id)
        for source in sources
    }
    session.flush()

    source_by_id = {source.id: source for source in sources}
    fetch_results: dict[UUID, SourceFetchResult] = {}
    timed_out = 0

    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        future_to_sid = {
            pool.submit(_fetch_source, source, source_timeout): source.id
            for source in sources
        }
        for future in as_completed(future_to_sid):
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                for f in future_to_sid:
                    f.cancel()
                break
            try:
                result = future.result(timeout=max(remaining, 0.1))
                fetch_results[result.source_id] = result
            except TimeoutError:
                sid = future_to_sid[future]
                fetch_results[sid] = SourceFetchResult(
                    source_id=sid, postings=[], error="crawl budget exceeded"
                )
                timed_out += 1
            except Exception as exc:
                sid = future_to_sid[future]
                fetch_results[sid] = SourceFetchResult(
                    source_id=sid, postings=[], error=str(exc)
                )

    for sid in source_by_id:
        if sid not in fetch_results:
            fetch_results[sid] = SourceFetchResult(
                source_id=sid, postings=[], error="crawl budget exceeded"
            )
            timed_out += 1

    total_discovered = total_new = total_updated = total_skipped = 0
    succeeded = failed = 0

    for sid, result in fetch_results.items():
        source_run = source_runs[sid]
        source = source_by_id[sid]

        if result.error:
            finish_source_run(
                session,
                source_run,
                status=SourceRunStatus.FAILED,
                error_summary=result.error,
            )
            source.last_error_at = datetime.now().astimezone()
            source.last_error_summary = result.error
            failed += 1
            continue

        counts = _persist_normalize_dedupe(
            session, source_run, source, result.postings
        )
        total_discovered += counts.discovered
        total_new += counts.new
        total_updated += counts.updated
        total_skipped += counts.skipped

        finish_source_run(session, source_run, status=SourceRunStatus.SUCCESS)
        source.last_successful_crawl_at = datetime.now().astimezone()
        source.last_error_summary = None
        succeeded += 1

    # Evaluation phase
    evaluation_counts: EvaluationRunCounts | None = None
    profile = session.scalar(select(UserProfile).limit(1))
    if profile is not None and evaluation_cap > 0:
        provider = ai_provider if ai_provider is not None else create_provider()
        ai_service = AIService(provider, session)
        evaluation_counts = evaluate_pending_jobs(
            session, ai_service, profile, limit=evaluation_cap
        )
        crawl_run.evaluations_completed = evaluation_counts.evaluated
        crawl_run.evaluations_pending = evaluation_counts.pending

    elapsed = time.monotonic() - wall_start
    crawl_run.elapsed_milliseconds = int(elapsed * 1000)

    _finalize_crawl_status(crawl_run, succeeded, failed)
    session.flush()

    return RefreshResult(
        crawl_run_id=crawl_run.id,
        sources_attempted=len(sources),
        sources_succeeded=succeeded,
        sources_failed=failed,
        sources_timed_out=timed_out,
        jobs_discovered=total_discovered,
        jobs_new=total_new,
        jobs_updated=total_updated,
        jobs_skipped=total_skipped,
        evaluation_counts=evaluation_counts,
        elapsed_seconds=elapsed,
    )


@dataclass(frozen=True)
class _SourceCounts:
    discovered: int
    new: int
    updated: int
    skipped: int


def _persist_normalize_dedupe(
    session: Session,
    source_run: SourceRun,
    source: JobSource,
    postings: list[RawPostingInput],
) -> _SourceCounts:
    """Persist raw postings, then normalize+dedupe the new/changed ones."""
    inserted = updated = skipped = 0
    changed_rows: list[RawJobPosting] = []

    for posting in postings:
        raw, change_kind = upsert_raw_posting(session, source.id, posting)
        if change_kind == "inserted":
            inserted += 1
            changed_rows.append(raw)
        elif change_kind == "updated":
            updated += 1
            changed_rows.append(raw)
        else:
            skipped += 1

    source_run.jobs_discovered = len(postings)
    source_run.jobs_inserted = inserted
    source_run.jobs_updated = updated
    source_run.jobs_skipped = skipped

    for raw in changed_rows:
        norm_result = normalize_posting(raw, source)
        if norm_result.accepted and norm_result.candidate is not None:
            dedupe_and_upsert(session, norm_result.candidate)

    session.flush()
    return _SourceCounts(
        discovered=len(postings), new=inserted, updated=updated, skipped=skipped
    )


def _finalize_crawl_status(
    crawl_run: CrawlRun, succeeded: int, failed: int
) -> None:
    """Set the terminal status on a crawl run."""
    if failed and succeeded:
        crawl_run.status = CrawlStatus.PARTIAL_SUCCESS
    elif failed:
        crawl_run.status = CrawlStatus.FAILED
    else:
        crawl_run.status = CrawlStatus.SUCCESS
    crawl_run.finished_at = datetime.now().astimezone()
