"""A deterministic stand-in for a hosted evaluation provider.

Scores from stated preferences with fixed weights and no randomness, so the
same job and profile always produce the same bucket. It exists to exercise the
pipeline end to end without a provider account - it is not a ranking model, and
its weights are not tuned against real outcomes.
"""

import re
from decimal import Decimal

from pookie_backend.ai.interface import (
    AIJobEvaluationRequest,
    AIJobEvaluationResult,
    AIJobSnapshot,
)
from pookie_backend.models import FitBucket, RemotePolicy

BASE_SCORE = Decimal("0.50")
PREFERRED_TECH_BONUS = Decimal("0.15")
ROLE_FAMILY_BONUS = Decimal("0.10")
AVOIDED_TECH_PENALTY = Decimal("0.25")
DEALBREAKER_PENALTY = Decimal("0.30")
UNKNOWN_SALARY_PENALTY = Decimal("0.05")
UNCLEAR_REMOTE_PENALTY = Decimal("0.10")

# Bucket floors, checked highest first.
BUCKET_THRESHOLDS = (
    (Decimal("0.75"), FitBucket.STRONG),
    (Decimal("0.50"), FitBucket.POSSIBLE),
    (Decimal("0.30"), FitBucket.STRETCH),
)


class MockAIProvider:
    """Provider adapter that evaluates locally and calls nothing."""

    provider_name = "mock"
    model_name = "mock-eval-v1"

    def evaluate_job(self, request: AIJobEvaluationRequest) -> AIJobEvaluationResult:
        """Score one job against one profile with fixed, inspectable rules."""
        job, profile = request.job, request.profile
        haystack = _tokenize(f"{job.title} {job.company} {job.location or ''}")

        matched_skills = _overlap(profile.preferred_tech, haystack)
        matched_families = _overlap(profile.target_role_families, haystack)
        avoided = _overlap(profile.avoided_tech, haystack)
        broken_dealbreakers = _overlap(profile.dealbreakers, haystack)

        score = (
            BASE_SCORE
            + PREFERRED_TECH_BONUS * len(matched_skills)
            + ROLE_FAMILY_BONUS * len(matched_families)
            - AVOIDED_TECH_PENALTY * len(avoided)
            - DEALBREAKER_PENALTY * len(broken_dealbreakers)
            - (UNKNOWN_SALARY_PENALTY if job.salary_unknown else Decimal("0"))
            - (
                UNCLEAR_REMOTE_PENALTY
                if job.remote_policy != RemotePolicy.REMOTE.value
                and job.remote_policy != RemotePolicy.HYBRID.value
                else Decimal("0")
            )
        )
        score = _clamp(score)

        return AIJobEvaluationResult(
            fit_bucket=_bucket_for(score).value,
            summary=_summarize(job, matched_skills, avoided),
            concerns=_concerns(job, avoided, broken_dealbreakers),
            matched_skills=matched_skills,
            matched_preferences=matched_families,
            internal_score=score,
        )


def _tokenize(text: str) -> set[str]:
    """Split text into lowercase word tokens for whole-word matching."""
    return set(re.findall(r"[a-z0-9+#.]+", text.lower()))


def _overlap(terms: tuple[str, ...], haystack: set[str]) -> tuple[str, ...]:
    """Return the terms whose words all appear in the text, order preserved."""
    matched = []
    for term in terms:
        words = _tokenize(term)
        if words and words <= haystack:
            matched.append(term)
    return tuple(matched)


def _clamp(score: Decimal) -> Decimal:
    return min(Decimal("1.00"), max(Decimal("0.00"), score))


def _bucket_for(score: Decimal) -> FitBucket:
    for floor, bucket in BUCKET_THRESHOLDS:
        if score >= floor:
            return bucket
    return FitBucket.NEEDS_REVIEW


def _summarize(
    job: AIJobSnapshot, matched_skills: tuple[str, ...], avoided: tuple[str, ...]
) -> str:
    parts = [f"{job.title} at {job.company}"]
    if matched_skills:
        parts.append(f"matches {', '.join(matched_skills)}")
    else:
        parts.append("matches none of the listed preferred technologies")
    if avoided:
        parts.append(f"but mentions {', '.join(avoided)}")
    return "; ".join(parts) + "."


def _concerns(
    job: AIJobSnapshot, avoided: tuple[str, ...], broken_dealbreakers: tuple[str, ...]
) -> tuple[str, ...]:
    concerns = []
    if job.salary_unknown:
        concerns.append("Salary is not published")
    if job.remote_policy == RemotePolicy.UNCLEAR.value:
        concerns.append("Remote policy is unclear")
    concerns.extend(f"Mentions avoided technology: {term}" for term in avoided)
    concerns.extend(f"May break dealbreaker: {term}" for term in broken_dealbreakers)
    return tuple(concerns)
