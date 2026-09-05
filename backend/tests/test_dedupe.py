"""Integration tests for candidate deduplication and job/link upsert."""

from dataclasses import replace
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pookie_backend.dedupe import dedupe_and_upsert
from pookie_backend.models import (
    ApprovalStatus,
    FitBucket,
    Job,
    JobLink,
    JobSource,
    JobStatus,
    RawJobPosting,
    RemotePolicy,
    SourceKind,
)
from pookie_backend.normalization import NormalizedJobCandidate, normalize_posting

BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)
LATER_TIME = datetime(2026, 9, 8, 12, 0, tzinfo=UTC)
LONG_DESCRIPTION = "We are hiring a backend engineer. " * 20


def add_source(session: Session, company: str, kind: SourceKind) -> JobSource:
    source = JobSource(
        id=uuid4(),
        kind=kind,
        name=f"{company} via {kind.value}",
        company_name=company,
        base_url=f"https://{kind.value}.example/{company.lower()}",
        external_board_id=company.lower(),
        approval_status=ApprovalStatus.APPROVED,
    )
    session.add(source)
    session.flush()
    return source


def add_candidate(
    session: Session,
    source: JobSource,
    *,
    title: str = "Senior Backend Engineer",
    location: str = "Remote (US)",
    company: str | None = None,
    apply_url: str | None = None,
    description: str = LONG_DESCRIPTION,
) -> NormalizedJobCandidate:
    """Persist a raw posting and normalize it, as the real pipeline does."""
    posting_id = uuid4()
    url = apply_url or f"https://boards.example/{posting_id}"
    posting = RawJobPosting(
        id=posting_id,
        job_source_id=source.id,
        source_posting_id=str(posting_id),
        source_url=url,
        apply_url=url,
        raw_title=title,
        raw_company=company or source.company_name,
        raw_location=location,
        raw_description=description,
        content_hash=f"hash-{posting_id}",
    )
    session.add(posting)
    session.flush()

    result = normalize_posting(posting, source)
    assert result.candidate is not None, result.rejection_reasons
    return result.candidate


def count_jobs(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(Job)) or 0


def links_for(session: Session, job: Job) -> list[JobLink]:
    return list(session.scalars(select(JobLink).where(JobLink.job_id == job.id)).all())


def test_creates_a_canonical_job_with_a_primary_link(db_session: Session):
    """A first-seen role becomes a job whose posting is its primary link."""
    source = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    candidate = add_candidate(db_session, source)

    job, change = dedupe_and_upsert(db_session, candidate, seen_at=BASE_TIME)

    assert change == "created"
    assert job.canonical_title == "Senior Backend Engineer"
    assert job.canonical_company == "Astral"
    assert job.remote_policy == RemotePolicy.REMOTE.value
    assert job.status == JobStatus.NEW
    assert job.first_seen_at == BASE_TIME
    links = links_for(db_session, job)
    assert len(links) == 1
    assert links[0].is_primary is True
    assert links[0].raw_job_posting_id == candidate.raw_job_posting_id


def test_recrawling_the_same_posting_changes_nothing_but_last_seen(
    db_session: Session,
):
    """Repeated crawls must not multiply jobs or links."""
    source = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    candidate = add_candidate(db_session, source)
    first, _ = dedupe_and_upsert(db_session, candidate, seen_at=BASE_TIME)

    again, change = dedupe_and_upsert(db_session, candidate, seen_at=LATER_TIME)

    assert change == "resighted"
    assert again.id == first.id
    assert count_jobs(db_session) == 1
    assert len(links_for(db_session, again)) == 1
    assert again.last_seen_at == LATER_TIME
    assert again.first_seen_at == BASE_TIME


def test_a_repeated_crawl_of_many_postings_is_idempotent(db_session: Session):
    """A whole crawl replayed end to end leaves the job set unchanged."""
    source = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    candidates = [
        add_candidate(db_session, source, title="Senior Backend Engineer"),
        add_candidate(db_session, source, title="Platform Engineer"),
        add_candidate(db_session, source, title="Data Engineer"),
    ]
    for candidate in candidates:
        dedupe_and_upsert(db_session, candidate, seen_at=BASE_TIME)
    after_first_crawl = count_jobs(db_session)

    changes = [
        dedupe_and_upsert(db_session, candidate, seen_at=LATER_TIME)[1]
        for candidate in candidates
    ]

    assert after_first_crawl == 3
    assert count_jobs(db_session) == 3
    assert changes == ["resighted", "resighted", "resighted"]


def test_resighting_follows_a_posting_that_moved(db_session: Session):
    """A board that reissues a posting URL updates the link, not the job."""
    source = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    candidate = add_candidate(db_session, source)
    job, _ = dedupe_and_upsert(db_session, candidate, seen_at=BASE_TIME)
    moved = replace(
        candidate,
        source_url="https://boards.example/moved",
        apply_url="https://boards.example/moved/apply",
    )

    dedupe_and_upsert(db_session, moved, seen_at=LATER_TIME)

    links = links_for(db_session, job)
    assert len(links) == 1
    assert links[0].source_url == "https://boards.example/moved"
    assert links[0].apply_url == "https://boards.example/moved/apply"


def test_merges_the_same_role_from_two_sources_preserving_both_links(
    db_session: Session,
):
    """One role listed on two boards is one job reachable by either link."""
    greenhouse = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    lever = add_source(db_session, "Astral", SourceKind.LEVER)
    first = add_candidate(db_session, greenhouse)
    second = add_candidate(db_session, lever)

    job_one, _ = dedupe_and_upsert(db_session, first, seen_at=BASE_TIME)
    job_two, change = dedupe_and_upsert(db_session, second, seen_at=LATER_TIME)

    assert change == "merged"
    assert job_two.id == job_one.id
    assert count_jobs(db_session) == 1
    links = sorted(links_for(db_session, job_two), key=lambda link: link.is_primary)
    assert len(links) == 2
    assert [link.is_primary for link in links] == [False, True]
    assert {link.raw_job_posting_id for link in links} == {
        first.raw_job_posting_id,
        second.raw_job_posting_id,
    }


def test_merges_across_differing_remote_location_wording(db_session: Session):
    """Remote location text is prose, so its wording must not split a job."""
    greenhouse = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    lever = add_source(db_session, "Astral", SourceKind.LEVER)
    first = add_candidate(db_session, greenhouse, location="Remote (US)")
    second = add_candidate(db_session, lever, location="Remote - Anywhere")

    dedupe_and_upsert(db_session, first, seen_at=BASE_TIME)
    _, change = dedupe_and_upsert(db_session, second, seen_at=LATER_TIME)

    assert change == "merged"
    assert count_jobs(db_session) == 1


def test_merges_despite_case_and_spacing_differences(db_session: Session):
    """Formatting noise in title or company must not split a job."""
    greenhouse = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    lever = add_source(db_session, "Astral", SourceKind.LEVER)
    first = add_candidate(db_session, greenhouse, title="Senior Backend Engineer")
    second = add_candidate(
        db_session, lever, title="senior   backend  engineer", company="ASTRAL"
    )

    dedupe_and_upsert(db_session, first, seen_at=BASE_TIME)
    _, change = dedupe_and_upsert(db_session, second, seen_at=LATER_TIME)

    assert change == "merged"
    assert count_jobs(db_session) == 1


def test_keeps_the_same_title_in_two_cities_separate(db_session: Session):
    """Different offices are different roles; merging would hide one."""
    greenhouse = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    lever = add_source(db_session, "Astral", SourceKind.LEVER)
    first = add_candidate(db_session, greenhouse, location="New York, NY (Onsite)")
    second = add_candidate(db_session, lever, location="San Francisco, CA (Onsite)")

    dedupe_and_upsert(db_session, first, seen_at=BASE_TIME)
    _, change = dedupe_and_upsert(db_session, second, seen_at=LATER_TIME)

    assert change == "created"
    assert count_jobs(db_session) == 2


def test_keeps_different_titles_at_one_company_separate(db_session: Session):
    """A near-miss title is not evidence of the same role."""
    source = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    first = add_candidate(db_session, source, title="Senior Backend Engineer")
    second = add_candidate(db_session, source, title="Staff Backend Engineer")

    dedupe_and_upsert(db_session, first, seen_at=BASE_TIME)
    _, change = dedupe_and_upsert(db_session, second, seen_at=LATER_TIME)

    assert change == "created"
    assert count_jobs(db_session) == 2


def test_keeps_the_same_title_at_two_companies_separate(db_session: Session):
    """Company is part of identity; two employers are never one job."""
    astral = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    ramp = add_source(db_session, "Ramp", SourceKind.GREENHOUSE)
    first = add_candidate(db_session, astral)
    second = add_candidate(db_session, ramp)

    dedupe_and_upsert(db_session, first, seen_at=BASE_TIME)
    _, change = dedupe_and_upsert(db_session, second, seen_at=LATER_TIME)

    assert change == "created"
    assert count_jobs(db_session) == 2


def test_a_thin_posting_lands_in_the_needs_review_bucket(db_session: Session):
    """A job flagged during normalization surfaces rather than looking unranked."""
    source = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    candidate = add_candidate(db_session, source, description="Apply now.")

    job, _ = dedupe_and_upsert(db_session, candidate, seen_at=BASE_TIME)

    assert candidate.needs_review is True
    assert job.fit_bucket == FitBucket.NEEDS_REVIEW


def test_a_complete_posting_stays_unranked_until_evaluation(db_session: Session):
    """Dedupe must not invent a fit bucket for a job it has not evaluated."""
    source = add_source(db_session, "Astral", SourceKind.GREENHOUSE)
    candidate = add_candidate(db_session, source)

    job, _ = dedupe_and_upsert(db_session, candidate, seen_at=BASE_TIME)

    assert job.fit_bucket is None
