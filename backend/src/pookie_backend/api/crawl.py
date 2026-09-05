"""Protected triggers for on-demand refresh and reranking.

Stubs on purpose. The endpoints, their contracts, and their run bookkeeping
are real, so the dashboard's Refresh action and status polling can be built
against them, but nothing here fetches a source or calls a provider yet -
source adapters and orchestration arrive with their own tasks.
"""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from pookie_backend.api.coverage import CrawlRunResponse
from pookie_backend.database import get_db_session
from pookie_backend.ingestion import create_crawl_run
from pookie_backend.models import (
    CrawlRun,
    CrawlStatus,
    CrawlTrigger,
    Job,
    JobStatus,
    SourceRun,
)

# Jobs the user has closed out are not candidates for ranking.
_UNRANKABLE_STATUSES = (JobStatus.DISMISSED, JobStatus.CLOSED_ARCHIVED)

router = APIRouter(tags=["refresh"])


class RankRunResponse(BaseModel):
    """What a rerank would have to do, before ranking is wired up."""

    jobs_considered: int
    jobs_awaiting_evaluation: int
    evaluations_run: int


@router.post("/crawl/run", summary="Trigger an on-demand refresh")
def trigger_crawl_run(
    session: Annotated[Session, Depends(get_db_session)],
) -> CrawlRunResponse:
    """Open a crawl run and return it.

    The run is finished immediately with zero counts because no source is
    contacted yet: leaving it running would strand the coverage view on a
    refresh that never completes.
    """
    running = session.scalar(
        select(CrawlRun).where(CrawlRun.status == CrawlStatus.RUNNING)
    )
    if running is not None:
        # Guards the double-clicked Refresh button, and still matters once
        # orchestration makes a run take real time.
        raise HTTPException(
            status_code=409,
            detail={
                "code": "refresh_already_running",
                "message": f"Refresh {running.id} is already running.",
            },
        )

    crawl_run = create_crawl_run(session, CrawlTrigger.ON_DEMAND)
    crawl_run.status = CrawlStatus.SUCCESS
    crawl_run.finished_at = datetime.now(UTC)
    crawl_run.elapsed_milliseconds = 0
    session.flush()
    return CrawlRunResponse.from_crawl_run(crawl_run)


@router.get("/crawl/runs/{run_id}", summary="Report a refresh's status and result")
def get_crawl_run(
    run_id: UUID, session: Annotated[Session, Depends(get_db_session)]
) -> CrawlRunResponse:
    """Return one refresh with its per-source detail, for status polling."""
    crawl_run = session.scalar(
        select(CrawlRun)
        .where(CrawlRun.id == run_id)
        .options(selectinload(CrawlRun.source_runs).joinedload(SourceRun.job_source))
    )
    if crawl_run is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "crawl_run_not_found", "message": "Crawl run not found."},
        )
    return CrawlRunResponse.from_crawl_run(crawl_run)


@router.post("/rank/run", summary="Trigger a reranking pass")
def trigger_rank_run(
    session: Annotated[Session, Depends(get_db_session)],
) -> RankRunResponse:
    """Report the ranking backlog without spending anything on it.

    `evaluations_run` is always zero here: this reports what a real pass would
    face, and makes no provider call.
    """
    considered = (
        select(func.count())
        .select_from(Job)
        .where(Job.status.notin_(_UNRANKABLE_STATUSES))
    )
    awaiting = considered.where(Job.fit_bucket.is_(None))
    return RankRunResponse(
        jobs_considered=session.scalar(considered) or 0,
        jobs_awaiting_evaluation=session.scalar(awaiting) or 0,
        evaluations_run=0,
    )
