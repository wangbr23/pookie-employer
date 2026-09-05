"""Unit tests for deterministic posting normalization.

These build unsaved model instances rather than rows: normalization is a pure
function over posting fields and never touches a session.
"""

from uuid import uuid4

import pytest

from pookie_backend.models import (
    ApprovalStatus,
    JobSource,
    RawJobPosting,
    RemotePolicy,
    RemoteUncertainty,
    SalaryUncertainty,
    SourceKind,
)
from pookie_backend.normalization import (
    MAX_TITLE_LENGTH,
    MIN_DESCRIPTION_LENGTH,
    normalize_posting,
)

LONG_DESCRIPTION = "We are hiring a backend engineer. " * 20


def make_source(company_name: str = "Astral") -> JobSource:
    return JobSource(
        id=uuid4(),
        kind=SourceKind.GREENHOUSE,
        name=f"{company_name} Jobs",
        company_name=company_name,
        base_url=f"https://boards.greenhouse.io/{company_name.lower()}",
        external_board_id=company_name.lower(),
        approval_status=ApprovalStatus.APPROVED,
    )


def make_posting(
    *,
    title: str | None = "Senior Backend Engineer",
    company: str | None = "Astral",
    location: str | None = "Remote (US)",
    apply_url: str | None = "https://boards.example/apply/1",
    source_url: str = "https://boards.example/jobs/1",
    description: str | None = LONG_DESCRIPTION,
) -> RawJobPosting:
    return RawJobPosting(
        id=uuid4(),
        job_source_id=uuid4(),
        source_posting_id="posting-1",
        source_url=source_url,
        apply_url=apply_url,
        raw_title=title,
        raw_company=company,
        raw_location=location,
        raw_description=description,
        content_hash="hash-1",
    )


def test_accepts_a_complete_posting():
    """A complete posting becomes a candidate carrying its source identity."""
    posting = make_posting()

    result = normalize_posting(posting, make_source())

    assert result.accepted
    candidate = result.candidate
    assert candidate is not None
    assert result.rejection_reasons == ()
    assert candidate.raw_job_posting_id == posting.id
    assert candidate.job_source_id == posting.job_source_id
    assert candidate.canonical_title == "Senior Backend Engineer"
    assert candidate.canonical_company == "Astral"
    assert candidate.canonical_location == "Remote (US)"
    assert candidate.apply_url == "https://boards.example/apply/1"
    assert candidate.source_url == "https://boards.example/jobs/1"
    assert candidate.needs_review is False
    assert candidate.review_reasons == ()


def test_collapses_whitespace_so_equal_text_compares_equal():
    """Ragged source formatting must not survive into canonical fields."""
    posting = make_posting(
        title="  Senior   Backend\n Engineer ", location="New\tYork,  NY"
    )

    candidate = normalize_posting(posting, make_source()).candidate

    assert candidate is not None
    assert candidate.canonical_title == "Senior Backend Engineer"
    assert candidate.canonical_location == "New York, NY"


def test_falls_back_to_the_source_company_when_the_posting_omits_it():
    """Most ATS boards omit the company per posting; the board owner is it."""
    posting = make_posting(company=None)

    candidate = normalize_posting(posting, make_source("Ramp")).candidate

    assert candidate is not None
    assert candidate.canonical_company == "Ramp"


def test_falls_back_to_the_source_url_when_no_apply_url_is_given():
    """A posting page is a usable apply target when no apply link is exposed."""
    posting = make_posting(apply_url=None)

    candidate = normalize_posting(posting, make_source()).candidate

    assert candidate is not None
    assert candidate.apply_url == "https://boards.example/jobs/1"


@pytest.mark.parametrize(
    ("field", "expected_reason"),
    [
        ("title", "missing_title"),
        ("location", "missing_location"),
    ],
)
def test_rejects_a_posting_missing_a_minimum_field(field: str, expected_reason: str):
    """Title and location are minimum fields; without them there is no job."""
    result = normalize_posting(make_posting(**{field: None}), make_source())

    assert not result.accepted
    assert result.candidate is None
    assert expected_reason in result.rejection_reasons


def test_rejects_a_posting_with_no_company_anywhere():
    """Company is required even after the source fallback is exhausted."""
    result = normalize_posting(make_posting(company=None), make_source(""))

    assert not result.accepted
    assert "missing_company" in result.rejection_reasons


def test_rejects_a_blank_field_the_same_as_a_missing_one():
    """Whitespace-only source data is absence, not content."""
    result = normalize_posting(make_posting(title="   "), make_source())

    assert "missing_title" in result.rejection_reasons


@pytest.mark.parametrize(
    "apply_url",
    [
        "javascript:alert(1)",
        "/jobs/relative-path",
        "mailto:jobs@example.com",
        "not a url",
    ],
)
def test_rejects_an_apply_link_that_is_not_a_web_url(apply_url: str):
    """A non-web apply link must never reach the dashboard's Apply button."""
    posting = make_posting(apply_url=apply_url, source_url=apply_url)

    result = normalize_posting(posting, make_source())

    assert not result.accepted
    assert "invalid_apply_url" in result.rejection_reasons


def test_rejects_a_field_wider_than_its_column():
    """Oversized values are malformed source data, not something to truncate."""
    result = normalize_posting(
        make_posting(title="x" * (MAX_TITLE_LENGTH + 1)), make_source()
    )

    assert not result.accepted
    assert "title_too_long" in result.rejection_reasons


def test_reports_every_rejection_reason_at_once():
    """One pass names every problem so debugging needs no second run."""
    result = normalize_posting(
        make_posting(title=None, location=None, apply_url=None, source_url=""),
        make_source(),
    )

    assert set(result.rejection_reasons) == {
        "missing_title",
        "missing_location",
        "missing_apply_url",
    }


@pytest.mark.parametrize(
    ("location", "title", "expected_policy"),
    [
        ("Remote (US)", "Backend Engineer", RemotePolicy.REMOTE),
        ("New York, NY - Hybrid", "Backend Engineer", RemotePolicy.HYBRID),
        ("New York, NY (Onsite)", "Backend Engineer", RemotePolicy.ONSITE),
        ("Anywhere", "Backend Engineer, Remote", RemotePolicy.REMOTE),
    ],
)
def test_detects_a_clear_remote_policy(
    location: str, title: str, expected_policy: RemotePolicy
):
    """An unambiguous signal in the title or location resolves the policy."""
    candidate = normalize_posting(
        make_posting(title=title, location=location), make_source()
    ).candidate

    assert candidate is not None
    assert candidate.remote_policy == expected_policy
    assert candidate.remote_uncertainty == RemoteUncertainty.CLEAR
    assert candidate.needs_review is False


def test_flags_conflicting_remote_signals_for_review():
    """Contradictory signals stay visible as Needs Review, not guessed at."""
    candidate = normalize_posting(
        make_posting(location="New York, NY (Onsite) - Remote option"), make_source()
    ).candidate

    assert candidate is not None
    assert candidate.remote_policy == RemotePolicy.UNCLEAR
    assert candidate.remote_uncertainty == RemoteUncertainty.CONFLICTING
    assert candidate.needs_review is True
    assert "remote_policy_conflicting" in candidate.review_reasons


def test_flags_an_absent_remote_signal_for_review():
    """Silence about remote work is uncertainty, not an onsite answer."""
    candidate = normalize_posting(
        make_posting(location="New York, NY"), make_source()
    ).candidate

    assert candidate is not None
    assert candidate.remote_policy == RemotePolicy.UNCLEAR
    assert candidate.remote_uncertainty == RemoteUncertainty.UNCLEAR
    assert candidate.needs_review is True
    assert "remote_policy_unclear" in candidate.review_reasons


def test_ignores_remote_wording_in_the_description():
    """Prose about the company must not make an onsite role look remote."""
    candidate = normalize_posting(
        make_posting(
            location="New York, NY (Onsite)",
            description="We have remote team members worldwide. " * 10,
        ),
        make_source(),
    ).candidate

    assert candidate is not None
    assert candidate.remote_policy == RemotePolicy.ONSITE


def test_does_not_mistake_distributed_systems_for_remote_work():
    """A common backend phrase must not be read as a location signal."""
    candidate = normalize_posting(
        make_posting(title="Distributed Systems Engineer", location="New York, NY"),
        make_source(),
    ).candidate

    assert candidate is not None
    assert candidate.remote_policy == RemotePolicy.UNCLEAR


def test_flags_a_stub_posting_for_review_without_rejecting_it():
    """A thin posting is surfaced as Needs Review rather than silently hidden."""
    result = normalize_posting(make_posting(description="Apply now."), make_source())

    assert result.accepted
    assert result.candidate is not None
    assert result.candidate.needs_review is True
    assert "description_too_short" in result.candidate.review_reasons


def test_accepts_a_description_at_the_review_threshold():
    """The stub check is a floor, not a range - exactly at the limit passes."""
    candidate = normalize_posting(
        make_posting(description="d" * MIN_DESCRIPTION_LENGTH), make_source()
    ).candidate

    assert candidate is not None
    assert candidate.review_reasons == ()


def test_marks_salary_unknown_without_forcing_review():
    """Raw postings carry no pay data, and missing salary never hides a job."""
    candidate = normalize_posting(make_posting(), make_source()).candidate

    assert candidate is not None
    assert candidate.salary_unknown is True
    assert candidate.salary_uncertainty == SalaryUncertainty.UNKNOWN
    assert candidate.needs_review is False
