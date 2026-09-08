"""Profile-driven pre-evaluation eligibility filter.

Skips jobs that cannot match the profile based on deterministic criteria
(title, location, seniority, salary) so they never reach the AI provider.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pookie_backend.models import Job, UserProfile


# Titles qualify only if they name a role that builds software: an explicit
# "software" + engineer/developer pairing, or a core software-family phrase
# next to engineer/developer. Bare "engineer"/"developer"/"platform"/
# "infrastructure" are not enough — they let data/security/HR roles through.
_CORE_SOFTWARE_PATTERNS = (
    r"\bsde\b",
    r"\bswe\b",
    r"\bfull[- ]?stack\s+(?:engineer|developer)\b",
    r"\bback[- ]?end\s+(?:engineer|developer)\b",
    r"\bfront[- ]?end\s+(?:engineer|developer)\b",
)

_SOFTWARE_WORD = re.compile(r"\bsoftware\b")
_BUILD_ROLE_WORD = re.compile(r"\b(?:engineer|developer)\b")

_NON_ENGINEERING_OVERRIDES = (
    r"\bdevops\b",
    r"\bsre\b",
    r"\bsite reliability\b",
    r"\bsales\s+engineer",
    r"\bsolutions?\s+engineer",
    r"\bsupport\s+engineer",
    r"\bfield\s+engineer",
    r"\bcustomer\s+engineer",
    r"\bpre[- ]?sales\b",
    r"\bsecurity\s+engineer",
    r"\bnetwork\s+engineer",
    r"\bhardware\s+engineer",
    r"\belectrical\s+engineer",
    r"\bmechanical\s+engineer",
    r"\baudio\s+engineer",
    r"\bdesign\s+engineer",
    r"\bbusiness\s+systems\s+engineer",
    r"\berp\b",
    r"\brecruiter\b",
    r"\btechnical\s+program",
    r"\btpm\b",
    r"\btlm\b",
)

_OVER_SENIOR_PATTERNS = (
    r"\bsenior\b",
    r"\bstaff\b",
    r"\bprincipal\b",
    r"\bdistinguished\b",
    r"\bfellow\b",
    r"\bdirector\b",
    r"\bvp\b",
    r"\bvice\s+president\b",
    r"\bhead\s+of\b",
    r"\bchief\b",
    r"\bengineering\s+manager",
    r"\bmanager,?\s+engineering",
    r"\bem\b,",
)

_REMOTE_PATTERNS = (r"\bremote\b", r"\banywhere\b")

_US_WIDE_PATTERNS = (r"\bunited states\b", r"\busa\b")

_NY_PATTERNS = (
    r"\bnew york\b",
    r"\bnyc\b",
    r"\bmanhattan\b",
    r"\bbrooklyn\b",
)


def _matches(patterns: tuple[str, ...], text: str) -> bool:
    text_lower = text.lower()
    return any(re.search(p, text_lower) for p in patterns)


def _is_software_role(title: str) -> bool:
    if _matches(_CORE_SOFTWARE_PATTERNS, title):
        return True
    title_lower = title.lower()
    return bool(_SOFTWARE_WORD.search(title_lower)) and bool(
        _BUILD_ROLE_WORD.search(title_lower)
    )


def check_eligibility(job: Job, profile: UserProfile) -> str | None:
    """Return a skip reason if the job fails eligibility, or None if eligible."""
    title = job.canonical_title or ""
    location = job.canonical_location or ""

    if not _is_software_role(title):
        return "not_engineering_role"
    if _matches(_NON_ENGINEERING_OVERRIDES, title):
        return "non_engineering_specialty"

    if _matches(_OVER_SENIOR_PATTERNS, title):
        return "seniority_too_high"

    if not _is_location_eligible(location, profile):
        return "location_mismatch"

    if not job.salary_unknown and profile.salary_floor is not None:
        effective_salary = job.salary_max or job.salary_min
        if effective_salary is not None and effective_salary < profile.salary_floor:
            return "salary_below_floor"

    return None


def _is_location_eligible(location: str, profile: UserProfile) -> bool:
    if _matches(_REMOTE_PATTERNS, location):
        return True
    if _matches(_US_WIDE_PATTERNS, location):
        return True
    for allowed in profile.allowed_locations or []:
        if _location_matches(location, allowed):
            return True
    return False


def _location_matches(location: str, allowed: str) -> bool:
    loc_lower = location.lower()
    allowed_lower = allowed.lower()
    if allowed_lower in loc_lower:
        return True
    if "new york" in allowed_lower and _matches(_NY_PATTERNS, location):
        return True
    return False
