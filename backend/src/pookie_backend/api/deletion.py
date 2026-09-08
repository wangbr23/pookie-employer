"""Destructive data-deletion endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import delete, update
from sqlalchemy.orm import Session

from pookie_backend.api.dependencies import get_active_profile
from pookie_backend.database import get_db_session
from pookie_backend.models import (
    AiCallLog,
    Job,
    JobEvaluation,
    JobFeedback,
    JobStatus,
    UserProfile,
)

router = APIRouter(tags=["deletion"])


@router.delete("/profile")
def delete_profile_data(
    session: Annotated[Session, Depends(get_db_session)],
    profile: Annotated[UserProfile, Depends(get_active_profile)],
) -> dict[str, object]:
    """Delete profile-derived data: evaluations and AI call logs.

    The profile row and raw job data are preserved so the user can
    re-evaluate with an updated profile.
    """
    eval_count = session.execute(
        delete(JobEvaluation).where(JobEvaluation.profile_id == profile.id)
    ).rowcount

    ai_log_count = session.execute(
        delete(AiCallLog).where(AiCallLog.profile_id == profile.id)
    ).rowcount

    # Clear cached fit_bucket on jobs whose only evaluation was from this profile.
    session.execute(
        update(Job)
        .where(
            Job.fit_bucket.is_not(None),
            ~Job.id.in_(
                session.query(JobEvaluation.job_id).filter(
                    JobEvaluation.profile_id != profile.id
                )
            ),
        )
        .values(fit_bucket=None)
    )

    session.commit()
    return {
        "deleted": {
            "evaluations": eval_count,
            "ai_call_logs": ai_log_count,
        }
    }


@router.delete("/job-history")
def delete_job_history(
    session: Annotated[Session, Depends(get_db_session)],
    profile: Annotated[UserProfile, Depends(get_active_profile)],
) -> dict[str, object]:
    """Delete all job feedback and reset affected job statuses.

    Jobs that were saved or dismissed revert to 'seen' so they remain
    visible without their prior feedback state.
    """
    feedback_count = session.execute(
        delete(JobFeedback).where(JobFeedback.profile_id == profile.id)
    ).rowcount

    # Reset jobs whose status was set by feedback actions back to seen.
    reset_count = session.execute(
        update(Job)
        .where(Job.status.in_([JobStatus.SAVED, JobStatus.DISMISSED]))
        .values(status=JobStatus.SEEN)
    ).rowcount

    session.commit()
    return {
        "deleted": {"feedback_records": feedback_count},
        "reset": {"jobs_to_seen": reset_count},
    }
