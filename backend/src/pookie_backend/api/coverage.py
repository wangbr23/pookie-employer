"""Debug endpoint reporting crawl coverage and per-source health."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Self
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pookie_backend.database import get_db_session
from pookie_backend.models import (
    ApprovalStatus,
    CrawlRun,
    CrawlStatus,
    CrawlTrigger,
    JobSource,
    SourceKind,
    SourceRun,
    SourceRunStatus,
    SourceStatus,
)

router = APIRouter(prefix="/debug", tags=["debug"])


class SourceRunResponse(BaseModel):
    """How one source fared inside a crawl run."""

    job_source_id: UUID
    source_name: str
    company_name: str
    kind: SourceKind
    status: SourceRunStatus
    started_at: datetime
    finished_at: datetime | None
    jobs_discovered: int
    jobs_inserted: int
    jobs_updated: int
    jobs_skipped: int
    error_summary: str | None

    @classmethod
    def from_source_run(cls, source_run: SourceRun) -> Self:
        """Flatten the source's identity onto its run so one row renders a table line."""
        return cls(
            job_source_id=source_run.job_source_id,
            source_name=source_run.job_source.name,
            company_name=source_run.job_source.company_name,
            kind=source_run.job_source.kind,
            status=source_run.status,
            started_at=source_run.started_at,
            finished_at=source_run.finished_at,
            jobs_discovered=source_run.jobs_discovered,
            jobs_inserted=source_run.jobs_inserted,
            jobs_updated=source_run.jobs_updated,
            jobs_skipped=source_run.jobs_skipped,
            error_summary=source_run.error_summary,
        )


class CrawlRunResponse(BaseModel):
    """Aggregate result of one refresh, including its cost and timing metadata."""

    id: UUID
    trigger: CrawlTrigger
    status: CrawlStatus
    started_at: datetime
    finished_at: datetime | None
    elapsed_milliseconds: int | None
    sources_attempted: int
    sources_succeeded: int
    sources_failed: int
    jobs_discovered: int
    jobs_new: int
    jobs_updated: int
    jobs_skipped: int
    evaluations_completed: int
    evaluations_pending: int
    ai_call_count: int
    estimated_ai_cost: Decimal | None
    sources: list[SourceRunResponse]

    @classmethod
    def from_crawl_run(cls, crawl_run: CrawlRun) -> Self:
        """Build the run payload with its per-source rows attached."""
        return cls(
            id=crawl_run.id,
            trigger=crawl_run.trigger,
            status=crawl_run.status,
            started_at=crawl_run.started_at,
            finished_at=crawl_run.finished_at,
            elapsed_milliseconds=crawl_run.elapsed_milliseconds,
            sources_attempted=crawl_run.sources_attempted,
            sources_succeeded=crawl_run.sources_succeeded,
            sources_failed=crawl_run.sources_failed,
            jobs_discovered=crawl_run.jobs_discovered,
            jobs_new=crawl_run.jobs_new,
            jobs_updated=crawl_run.jobs_updated,
            jobs_skipped=crawl_run.jobs_skipped,
            evaluations_completed=crawl_run.evaluations_completed,
            evaluations_pending=crawl_run.evaluations_pending,
            ai_call_count=crawl_run.ai_call_count,
            estimated_ai_cost=crawl_run.estimated_ai_cost,
            sources=[
                SourceRunResponse.from_source_run(source_run)
                for source_run in crawl_run.source_runs
            ],
        )


class JobSourceStatusResponse(BaseModel):
    """Standing health of a configured source, independent of any single crawl."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    kind: SourceKind
    name: str
    company_name: str
    status: SourceStatus
    approval_status: ApprovalStatus
    last_successful_crawl_at: datetime | None
    last_error_at: datetime | None
    last_error_summary: str | None


class CoverageResponse(BaseModel):
    """Everything the debug/coverage view needs about ingestion health."""

    last_crawl_run: CrawlRunResponse | None
    sources: list[JobSourceStatusResponse]


# Blocking SQLAlchemy I/O, so `def` keeps it on FastAPI's threadpool.
@router.get("/coverage", summary="Report last-crawl coverage and source health")
def get_coverage(
    session: Annotated[Session, Depends(get_db_session)],
) -> CoverageResponse:
    """Return the most recent crawl run and the standing status of every source."""
    crawl_run = session.scalar(
        select(CrawlRun)
        .order_by(CrawlRun.started_at.desc())
        .limit(1)
        .options(selectinload(CrawlRun.source_runs).joinedload(SourceRun.job_source))
    )
    sources = session.scalars(
        select(JobSource).order_by(JobSource.company_name, JobSource.name)
    ).all()
    return CoverageResponse(
        last_crawl_run=(
            CrawlRunResponse.from_crawl_run(crawl_run) if crawl_run else None
        ),
        sources=[JobSourceStatusResponse.model_validate(source) for source in sources],
    )
