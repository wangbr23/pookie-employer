"""Read-only job list and detail endpoints and their response contracts."""

from datetime import datetime
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import ColumnElement, func, or_, select
from sqlalchemy.orm import Session, selectinload

from pookie_backend.database import get_db_session
from pookie_backend.models import (
    FitBucket,
    Job,
    JobEvaluation,
    JobLink,
    JobLinkStatus,
    JobStatus,
    RemoteUncertainty,
    SalaryUncertainty,
    WorkAuthUncertainty,
)

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200

router = APIRouter(prefix="/jobs", tags=["jobs"])


class JobLinkResponse(BaseModel):
    """A preserved source/apply link for a job."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_url: str
    apply_url: str | None
    is_primary: bool
    status: JobLinkStatus
    last_checked_at: datetime | None


class JobEvaluationResponse(BaseModel):
    """The stored fit explanation for a job; never computed at request time."""

    model_config = ConfigDict(from_attributes=True)

    fit_bucket: FitBucket
    internal_score: Decimal | None
    matched_skills: list[str]
    matched_preferences: list[str]
    concerns: list[str]
    uncertainties: list[str]
    summary: str | None
    verify_before_applying: list[str]
    salary_uncertainty: SalaryUncertainty
    remote_uncertainty: RemoteUncertainty
    work_auth_uncertainty: WorkAuthUncertainty
    model_provider: str
    model_name: str
    evaluated_at: datetime


class JobSummaryResponse(BaseModel):
    """The job-card shape: everything the dashboard list renders without expanding."""

    id: UUID
    canonical_title: str
    canonical_company: str
    canonical_location: str | None
    remote_policy: str | None
    employment_type: str | None
    salary_min: Decimal | None
    salary_max: Decimal | None
    salary_currency: str | None
    salary_unknown: bool
    seniority: str | None
    status: JobStatus
    fit_bucket: FitBucket | None
    first_seen_at: datetime
    last_seen_at: datetime
    apply_url: str | None

    @staticmethod
    def from_job(job: Job) -> "JobSummaryResponse":
        """Build a summary, resolving the single link the Apply button should use."""
        link = _best_apply_link(job.links)
        return JobSummaryResponse(
            id=job.id,
            canonical_title=job.canonical_title,
            canonical_company=job.canonical_company,
            canonical_location=job.canonical_location,
            remote_policy=job.remote_policy,
            employment_type=job.employment_type,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            salary_unknown=job.salary_unknown,
            seniority=job.seniority,
            status=job.status,
            fit_bucket=job.fit_bucket,
            first_seen_at=job.first_seen_at,
            last_seen_at=job.last_seen_at,
            apply_url=(link.apply_url or link.source_url) if link else None,
        )


class JobDetailResponse(JobSummaryResponse):
    """A job plus its stored evaluation and every preserved link."""

    evaluation: JobEvaluationResponse | None
    links: list[JobLinkResponse]

    @staticmethod
    def from_job_and_evaluation(
        job: Job, evaluation: JobEvaluation | None
    ) -> "JobDetailResponse":
        """Extend the summary shape with the expandable-details payload."""
        return JobDetailResponse(
            **JobSummaryResponse.from_job(job).model_dump(),
            evaluation=(
                JobEvaluationResponse.model_validate(evaluation)
                if evaluation is not None
                else None
            ),
            links=[JobLinkResponse.model_validate(link) for link in job.links],
        )


class JobListResponse(BaseModel):
    """One page of jobs plus the total matching the same filters."""

    items: list[JobSummaryResponse]
    total: int
    limit: int
    offset: int


def _best_apply_link(links: list[JobLink]) -> JobLink | None:
    """Pick the link the Apply button should open: active first, then primary."""
    if not links:
        return None
    return min(
        links,
        key=lambda link: (link.status != JobLinkStatus.ACTIVE, not link.is_primary),
    )


def _escape_like(value: str) -> str:
    """Escape LIKE wildcards so user search text matches literally."""
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _job_filters(
    status: list[JobStatus] | None,
    fit_bucket: list[FitBucket] | None,
    search: str | None,
) -> list[ColumnElement[bool]]:
    """Translate query parameters into SQL conditions shared by page and count."""
    filters: list[ColumnElement[bool]] = []
    if status:
        filters.append(Job.status.in_(status))
    if fit_bucket:
        filters.append(Job.fit_bucket.in_(fit_bucket))
    if search and search.strip():
        pattern = f"%{_escape_like(search.strip())}%"
        filters.append(
            or_(
                Job.canonical_title.ilike(pattern, escape="\\"),
                Job.canonical_company.ilike(pattern, escape="\\"),
            )
        )
    return filters


# Defined with `def` rather than `async def`: the handler does blocking
# SQLAlchemy I/O, so FastAPI must run it in its threadpool instead of on the
# event loop.
@router.get("", summary="List jobs for the dashboard views")
def list_jobs(
    session: Annotated[Session, Depends(get_db_session)],
    status: Annotated[
        list[JobStatus] | None,
        Query(description="Repeatable; restricts results to these job statuses."),
    ] = None,
    fit_bucket: Annotated[
        list[FitBucket] | None,
        Query(description="Repeatable; restricts results to these fit buckets."),
    ] = None,
    search: Annotated[
        str | None,
        Query(max_length=200, description="Case-insensitive title/company substring."),
    ] = None,
    limit: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = DEFAULT_PAGE_SIZE,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> JobListResponse:
    """Return newest-first jobs matching the filters, with a total for paging."""
    filters = _job_filters(status, fit_bucket, search)
    total = session.scalar(select(func.count()).select_from(Job).where(*filters)) or 0
    jobs = session.scalars(
        select(Job)
        .where(*filters)
        # id breaks ties so paging stays stable across jobs seen in the same crawl.
        .order_by(Job.first_seen_at.desc(), Job.id)
        .limit(limit)
        .offset(offset)
        .options(selectinload(Job.links))
    ).all()
    return JobListResponse(
        items=[JobSummaryResponse.from_job(job) for job in jobs],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{job_id}", summary="Get one job with its evaluation and links")
def get_job(
    job_id: UUID, session: Annotated[Session, Depends(get_db_session)]
) -> JobDetailResponse:
    """Return a single job with its stored evaluation and preserved links."""
    job = session.scalar(
        select(Job).where(Job.id == job_id).options(selectinload(Job.links))
    )
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "job_not_found", "message": "Job not found."},
        )

    # The MVP runs a single configured profile, so the newest evaluation is that
    # profile's current one. This needs a profile filter once profiles multiply.
    evaluation = session.scalar(
        select(JobEvaluation)
        .where(JobEvaluation.job_id == job_id)
        .order_by(JobEvaluation.evaluated_at.desc())
        .limit(1)
    )
    return JobDetailResponse.from_job_and_evaluation(job, evaluation)
