"""Endpoints that record what the user did with a job.

Separate from the read contract in `jobs.py`: these change job state and write
the feedback log that later ranking work learns from.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, StringConstraints
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pookie_backend.api.dependencies import get_active_profile
from pookie_backend.api.jobs import JobSummaryResponse
from pookie_backend.database import get_db_session
from pookie_backend.models import (
    FeedbackAction,
    Job,
    JobFeedback,
    JobStatus,
    UserProfile,
)

MAX_REASONS = 10
MAX_FREE_TEXT_LENGTH = 2000

Reason = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
]
FreeText = Annotated[
    str, StringConstraints(strip_whitespace=True, max_length=MAX_FREE_TEXT_LENGTH)
]

router = APIRouter(prefix="/jobs", tags=["feedback"])


class SaveJobRequest(BaseModel):
    """Optional context for why a job was saved."""

    reasons: list[Reason] = Field(default_factory=list, max_length=MAX_REASONS)
    free_text: FreeText | None = None


class DismissJobRequest(BaseModel):
    """Why a job was dismissed.

    At least one reason is required: the design's dismiss flow is a reason
    flow, and a dismissal with no stated reason teaches later ranking nothing.
    """

    reasons: list[Reason] = Field(min_length=1, max_length=MAX_REASONS)
    free_text: FreeText | None = None


@router.post("/{job_id}/save", summary="Save a job")
def save_job(
    job_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
    profile: Annotated[UserProfile, Depends(get_active_profile)],
    request: SaveJobRequest | None = None,
) -> JobSummaryResponse:
    """Mark a job saved, recording the action once even if repeated."""
    body = request or SaveJobRequest()
    job = _get_job(session, job_id)
    _record_action(
        session,
        job,
        profile,
        action=FeedbackAction.SAVE,
        status=JobStatus.SAVED,
        reasons=body.reasons,
        free_text=body.free_text,
    )
    return JobSummaryResponse.from_job(job)


@router.post("/{job_id}/dismiss", summary="Dismiss a job with a reason")
def dismiss_job(
    job_id: UUID,
    request: DismissJobRequest,
    session: Annotated[Session, Depends(get_db_session)],
    profile: Annotated[UserProfile, Depends(get_active_profile)],
) -> JobSummaryResponse:
    """Mark a job dismissed and record why."""
    job = _get_job(session, job_id)
    _record_action(
        session,
        job,
        profile,
        action=FeedbackAction.DISMISS,
        status=JobStatus.DISMISSED,
        reasons=request.reasons,
        free_text=request.free_text,
    )
    return JobSummaryResponse.from_job(job)


@router.post("/{job_id}/seen", summary="Mark a new job as seen")
def mark_job_seen(
    job_id: UUID,
    session: Annotated[Session, Depends(get_db_session)],
) -> JobSummaryResponse:
    """Advance a new job to seen, leaving every other state untouched.

    Seen is a passive signal from scrolling past a card, so it must never
    overwrite a deliberate save or dismissal. Calling it on an already-decided
    job succeeds and changes nothing, rather than failing a harmless request.
    """
    job = _get_job(session, job_id)
    if job.status == JobStatus.NEW:
        job.status = JobStatus.SEEN
        session.flush()
    return JobSummaryResponse.from_job(job)


def _get_job(session: Session, job_id: UUID) -> Job:
    """Load a job by id, returning the same structured 404 the read API uses."""
    job = session.scalar(
        select(Job).where(Job.id == job_id).options(selectinload(Job.links))
    )
    if job is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "job_not_found", "message": "Job not found."},
        )
    return job


def _record_action(
    session: Session,
    job: Job,
    profile: UserProfile,
    *,
    action: FeedbackAction,
    status: JobStatus,
    reasons: list[str],
    free_text: str | None,
) -> None:
    """Apply a decision, skipping the log when the job is already in that state.

    Repeating the request is therefore safe: a double-clicked save leaves one
    feedback row, not two, so the log stays a record of decisions rather than
    of clicks.
    """
    if job.status == status:
        return
    job.status = status
    session.add(
        JobFeedback(
            job_id=job.id,
            profile_id=profile.id,
            action=action,
            reasons=reasons,
            free_text=free_text,
        )
    )
    session.flush()
