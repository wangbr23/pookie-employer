"""Deterministic normalization of raw postings into validated job candidates.

This layer decides only what a posting *says*. Whether it is a good match is
`JobEvaluation`'s job (T21), and whether it is the same role as another
posting is dedupe's (T19). Nothing here calls an AI provider or touches the
database.
"""

import re
from dataclasses import dataclass
from urllib.parse import urlparse
from uuid import UUID

from pookie_backend.models import (
    JobSource,
    RawJobPosting,
    RemotePolicy,
    RemoteUncertainty,
    SalaryUncertainty,
)

# Mirror the column widths on `Job` and `JobLink`. A value longer than its
# column is malformed source data, not something to silently truncate.
MAX_TITLE_LENGTH = 512
MAX_COMPANY_LENGTH = 255
MAX_LOCATION_LENGTH = 512
MAX_URL_LENGTH = 2048

# Under this, a posting is a stub - a title and a link with nothing for the
# evaluation step to reason about - so it is shown as Needs Review instead of
# being ranked as though it had been read.
MIN_DESCRIPTION_LENGTH = 200

_REMOTE_PATTERNS = (r"\bremote\b", r"\bwork from home\b", r"\bwfh\b")
_HYBRID_PATTERNS = (r"\bhybrid\b",)
_ONSITE_PATTERNS = (r"\bon-?site\b", r"\bin[- ]office\b", r"\bin[- ]person\b")


@dataclass(frozen=True)
class NormalizedJobCandidate:
    """A posting that passed validation, ready for dedupe and upsert."""

    raw_job_posting_id: UUID
    job_source_id: UUID
    canonical_title: str
    canonical_company: str
    canonical_location: str
    source_url: str
    apply_url: str
    remote_policy: RemotePolicy
    remote_uncertainty: RemoteUncertainty
    salary_unknown: bool
    salary_uncertainty: SalaryUncertainty
    needs_review: bool
    review_reasons: tuple[str, ...]


@dataclass(frozen=True)
class NormalizationResult:
    """A candidate, or the reasons the posting could not become one."""

    candidate: NormalizedJobCandidate | None
    rejection_reasons: tuple[str, ...]

    @property
    def accepted(self) -> bool:
        """Whether the posting produced a usable candidate."""
        return self.candidate is not None


def normalize_posting(posting: RawJobPosting, source: JobSource) -> NormalizationResult:
    """Validate and normalize one raw posting against its configured source.

    `source` supplies the company name for boards that omit it per posting,
    which is most of them - the board's owner is authoritative there.
    """
    title = _collapse_whitespace(posting.raw_title)
    company = _collapse_whitespace(posting.raw_company) or _collapse_whitespace(
        source.company_name
    )
    location = _collapse_whitespace(posting.raw_location)
    source_url = _collapse_whitespace(posting.source_url)
    # The posting page is where you apply when a board exposes no separate
    # apply URL, matching how the jobs API resolves a job's Apply button.
    apply_url = _collapse_whitespace(posting.apply_url) or source_url

    rejection_reasons = _reject_missing_minimum_fields(
        title=title, company=company, location=location, apply_url=apply_url
    ) + _reject_overlong_fields(
        title=title, company=company, location=location, apply_url=apply_url
    )
    if rejection_reasons:
        return NormalizationResult(candidate=None, rejection_reasons=rejection_reasons)

    remote_policy, remote_uncertainty = detect_remote_policy(title, location)
    review_reasons = _review_reasons(remote_uncertainty, posting.raw_description)
    return NormalizationResult(
        candidate=NormalizedJobCandidate(
            raw_job_posting_id=posting.id,
            job_source_id=posting.job_source_id,
            canonical_title=title,
            canonical_company=company,
            canonical_location=location,
            source_url=source_url,
            apply_url=apply_url,
            remote_policy=remote_policy,
            remote_uncertainty=remote_uncertainty,
            # Raw postings carry no salary column, so salary is always unknown
            # here. Filling it needs a source of structured pay data, not a
            # guess parsed out of description prose.
            salary_unknown=True,
            salary_uncertainty=SalaryUncertainty.UNKNOWN,
            needs_review=bool(review_reasons),
            review_reasons=review_reasons,
        ),
        rejection_reasons=(),
    )


def detect_remote_policy(
    title: str, location: str
) -> tuple[RemotePolicy, RemoteUncertainty]:
    """Infer where a job is worked from its title and location.

    Deliberately ignores the description: prose like "we have remote team
    members" describes the company, not the role, and reading it turns every
    posting remote.
    """
    signals = {
        RemotePolicy.REMOTE: _matches_any(_REMOTE_PATTERNS, title, location),
        RemotePolicy.HYBRID: _matches_any(_HYBRID_PATTERNS, title, location),
        RemotePolicy.ONSITE: _matches_any(_ONSITE_PATTERNS, title, location),
    }
    matched = [policy for policy, found in signals.items() if found]
    if len(matched) == 1:
        return matched[0], RemoteUncertainty.CLEAR
    if len(matched) > 1:
        return RemotePolicy.UNCLEAR, RemoteUncertainty.CONFLICTING
    return RemotePolicy.UNCLEAR, RemoteUncertainty.UNCLEAR


def _collapse_whitespace(value: str | None) -> str:
    """Trim and collapse runs of whitespace so equal text compares equal."""
    return " ".join(value.split()) if value else ""


def _matches_any(patterns: tuple[str, ...], *values: str) -> bool:
    haystack = " ".join(values).lower()
    return any(re.search(pattern, haystack) for pattern in patterns)


def _reject_missing_minimum_fields(
    *, title: str, company: str, location: str, apply_url: str
) -> tuple[str, ...]:
    """Enforce the spec's minimum fields: title, company, location, apply link."""
    reasons = []
    if not title:
        reasons.append("missing_title")
    if not company:
        reasons.append("missing_company")
    if not location:
        reasons.append("missing_location")
    if not apply_url:
        reasons.append("missing_apply_url")
    elif not _is_web_url(apply_url):
        # Keeps a relative path or a `javascript:` URL from reaching the
        # dashboard's Apply button.
        reasons.append("invalid_apply_url")
    return tuple(reasons)


def _reject_overlong_fields(
    *, title: str, company: str, location: str, apply_url: str
) -> tuple[str, ...]:
    too_long = {
        "title_too_long": len(title) > MAX_TITLE_LENGTH,
        "company_too_long": len(company) > MAX_COMPANY_LENGTH,
        "location_too_long": len(location) > MAX_LOCATION_LENGTH,
        "apply_url_too_long": len(apply_url) > MAX_URL_LENGTH,
    }
    return tuple(reason for reason, exceeded in too_long.items() if exceeded)


def _is_web_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)


def _review_reasons(
    remote_uncertainty: RemoteUncertainty, description: str | None
) -> tuple[str, ...]:
    """Flag a valid-but-thin posting for Needs Review rather than hiding it.

    Unknown salary is deliberately not a trigger: the spec ranks those lower
    and keeps them filterable, but does not sideline them.
    """
    reasons = []
    if remote_uncertainty != RemoteUncertainty.CLEAR:
        reasons.append(f"remote_policy_{remote_uncertainty.value}")
    if len(_collapse_whitespace(description)) < MIN_DESCRIPTION_LENGTH:
        reasons.append("description_too_short")
    return tuple(reasons)
