"""Export endpoints for saved jobs."""

import csv
import io
from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from pookie_backend.api.dependencies import get_active_profile
from pookie_backend.api.jobs import _best_apply_link
from pookie_backend.database import get_db_session
from pookie_backend.models import (
    Job,
    JobEvaluation,
    JobStatus,
    UserProfile,
)

router = APIRouter(prefix="/export", tags=["export"])


class ExportFormat(StrEnum):
    CSV = "csv"
    JSON = "json"


CSV_COLUMNS = [
    "title",
    "company",
    "location",
    "remote_policy",
    "salary_min",
    "salary_max",
    "salary_currency",
    "fit_bucket",
    "fit_summary",
    "concerns",
    "apply_url",
    "first_seen_at",
]


def _job_export_row(
    job: Job, evaluation: JobEvaluation | None
) -> dict[str, str | None]:
    link = _best_apply_link(job.links)
    return {
        "title": job.canonical_title,
        "company": job.canonical_company,
        "location": job.canonical_location,
        "remote_policy": job.remote_policy,
        "salary_min": str(job.salary_min) if job.salary_min is not None else None,
        "salary_max": str(job.salary_max) if job.salary_max is not None else None,
        "salary_currency": job.salary_currency,
        "fit_bucket": evaluation.fit_bucket.value if evaluation else (
            job.fit_bucket.value if job.fit_bucket else None
        ),
        "fit_summary": evaluation.summary if evaluation else None,
        "concerns": "; ".join(evaluation.concerns) if evaluation else None,
        "apply_url": (link.apply_url or link.source_url) if link else None,
        "first_seen_at": job.first_seen_at.isoformat(),
    }


def _latest_evaluation(
    evaluations: list[JobEvaluation], profile_id: object
) -> JobEvaluation | None:
    matches = [e for e in evaluations if e.profile_id == profile_id]
    if not matches:
        return None
    return max(matches, key=lambda e: e.evaluated_at)


@router.get("/saved")
def export_saved_jobs(
    session: Annotated[Session, Depends(get_db_session)],
    profile: Annotated[UserProfile, Depends(get_active_profile)],
    format: Annotated[
        ExportFormat,
        Query(description="Export format: csv or json."),
    ] = ExportFormat.CSV,
) -> Response:
    """Export all saved jobs as CSV or JSON."""
    jobs = session.scalars(
        select(Job)
        .where(Job.status == JobStatus.SAVED)
        .order_by(Job.first_seen_at.desc(), Job.id)
        .options(selectinload(Job.links), selectinload(Job.evaluations))
    ).all()

    rows = [
        _job_export_row(job, _latest_evaluation(job.evaluations, profile.id))
        for job in jobs
    ]

    if format == ExportFormat.JSON:
        return Response(
            content=_to_json(rows),
            media_type="application/json",
            headers={
                "Content-Disposition": 'attachment; filename="saved_jobs.json"',
            },
        )

    return Response(
        content=_to_csv(rows),
        media_type="text/csv",
        headers={
            "Content-Disposition": 'attachment; filename="saved_jobs.csv"',
        },
    )


def _to_csv(rows: list[dict[str, str | None]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_COLUMNS)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buf.getvalue()


def _to_json(rows: list[dict[str, str | None]]) -> str:
    import json

    return json.dumps(rows, indent=2)
