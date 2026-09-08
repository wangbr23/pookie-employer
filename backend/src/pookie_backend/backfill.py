"""Re-apply the eligibility filter to every stored job.

Run after a filter change so already-stored postings get the new skip_reason
treatment immediately instead of waiting for the next refresh to touch them.
No AI calls are made — this is the deterministic eligibility sweep only.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from pookie_backend.database import SessionLocal
from pookie_backend.eligibility import check_eligibility
from pookie_backend.evaluation import _UNRANKABLE_STATUSES
from pookie_backend.models import Job, UserProfile


def backfill_skip_reasons(session: Session) -> tuple[int, int]:
    """Set or clear skip_reason on every rankable job; commit left to the caller.

    Returns (filtered, restored): jobs newly given a skip_reason, and jobs
    whose stale skip_reason was cleared because they now pass the filter.
    """
    profile = session.scalar(select(UserProfile).limit(1))
    if profile is None:
        return (0, 0)

    jobs = session.scalars(
        select(Job)
        # Same scope as the evaluation loop: never touch jobs a user
        # dismissed or that were closed.
        .where(Job.status.notin_(_UNRANKABLE_STATUSES))
    ).all()

    filtered = restored = 0
    for job in jobs:
        reason = check_eligibility(job, profile)
        if reason is not None:
            job.skip_reason = reason
            filtered += 1
        elif job.skip_reason is not None:
            job.skip_reason = None
            restored += 1
    session.flush()
    return (filtered, restored)


def main() -> None:
    """Run the backfill against the configured database."""
    with SessionLocal() as session:
        filtered, restored = backfill_skip_reasons(session)
        session.commit()
        print(f"Backfill complete: {filtered} jobs filtered, {restored} restored.")


if __name__ == "__main__":
    main()
