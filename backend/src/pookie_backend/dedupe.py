"""Conservative deduplication of normalized candidates into canonical jobs.

Merging is deliberately reluctant: duplicate clutter on the dashboard is less
harmful than hiding a legitimate different role, so anything short of a strong
deterministic match becomes its own `Job`.
"""

from datetime import datetime
from typing import Literal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pookie_backend.models import FitBucket, Job, JobLink, JobStatus, RemotePolicy
from pookie_backend.normalization import NormalizedJobCandidate

JobChangeKind = Literal["created", "merged", "resighted"]


def dedupe_and_upsert(
    session: Session,
    candidate: NormalizedJobCandidate,
    *,
    seen_at: datetime | None = None,
) -> tuple[Job, JobChangeKind]:
    """Attach a candidate to its canonical job, creating one when none matches.

    Returns the job and what happened to it: `resighted` for a posting already
    linked to a job, `merged` for a new posting that matched an existing job,
    `created` for a role seen for the first time.
    """
    observed_at = seen_at or datetime.now().astimezone()

    existing_link = session.scalar(
        select(JobLink).where(
            JobLink.raw_job_posting_id == candidate.raw_job_posting_id
        )
    )
    if existing_link is not None:
        # The same posting seen by a later crawl. Refresh where it points, in
        # case the board moved it, but leave the job's canonical fields alone.
        existing_link.source_url = candidate.source_url
        existing_link.apply_url = candidate.apply_url
        job = existing_link.job
        job.last_seen_at = observed_at
        session.flush()
        return job, "resighted"

    match = find_matching_job(session, candidate)
    if match is not None:
        _add_link(session, match, candidate, is_primary=False)
        match.last_seen_at = observed_at
        session.flush()
        return match, "merged"

    job = Job(
        canonical_title=candidate.canonical_title,
        canonical_company=candidate.canonical_company,
        canonical_location=candidate.canonical_location,
        remote_policy=candidate.remote_policy.value,
        salary_unknown=candidate.salary_unknown,
        status=JobStatus.NEW,
        # A thin posting enters the Needs Review bucket rather than looking
        # unevaluated, so it surfaces instead of being hidden. Evaluation
        # overwrites this once the job is actually ranked.
        fit_bucket=FitBucket.NEEDS_REVIEW if candidate.needs_review else None,
        first_seen_at=observed_at,
        last_seen_at=observed_at,
    )
    session.add(job)
    session.flush()
    _add_link(session, job, candidate, is_primary=True)
    session.flush()
    return job, "created"


def find_matching_job(
    session: Session, candidate: NormalizedJobCandidate
) -> Job | None:
    """Find the one job a candidate obviously belongs to, or nothing.

    Company and title are matched in SQL; the location rule is then applied in
    Python so candidates and stored jobs go through exactly the same rule.
    """
    same_role = session.scalars(
        select(Job)
        .where(
            func.lower(Job.canonical_company) == candidate.canonical_company.lower(),
            func.lower(Job.canonical_title) == candidate.canonical_title.lower(),
        )
        .order_by(Job.created_at)
    ).all()

    wanted = location_key(candidate.canonical_location, candidate.remote_policy.value)
    for job in same_role:
        if (
            location_key(job.canonical_location or "", job.remote_policy or "")
            == wanted
        ):
            return job
    return None


def location_key(location: str, remote_policy: str) -> str:
    """Reduce where a job is worked to one comparable value.

    Remote roles collapse to a single key because their location text is free
    prose - "Remote (US)" and "Remote - Anywhere" are the same posting. Every
    other policy keeps its city, so the same title in two offices stays two
    jobs.
    """
    if remote_policy == RemotePolicy.REMOTE.value:
        return RemotePolicy.REMOTE.value
    return " ".join(location.split()).lower()


def _add_link(
    session: Session,
    job: Job,
    candidate: NormalizedJobCandidate,
    *,
    is_primary: bool,
) -> JobLink:
    """Preserve the candidate's posting as another way into the same job."""
    link = JobLink(
        job_id=job.id,
        raw_job_posting_id=candidate.raw_job_posting_id,
        source_url=candidate.source_url,
        apply_url=candidate.apply_url,
        is_primary=is_primary,
    )
    session.add(link)
    session.flush()
    return link
