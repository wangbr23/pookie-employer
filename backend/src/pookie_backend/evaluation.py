"""Turn canonical jobs into stored evaluations the dashboard can read.

Ranking is a stored result, never computed while a page loads. This module
owns the two-step path the design calls for: deterministic facts about the job
are derived here, and only the judgement call is delegated to a provider.
"""

from dataclasses import dataclass
from hashlib import sha256
from typing import Literal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from pookie_backend.ai.interface import (
    AIJobEvaluationRequest,
    AIJobEvaluationResult,
    AIJobSnapshot,
    AIProfileSnapshot,
    AIService,
)
from pookie_backend.eligibility import check_eligibility
from pookie_backend.models import (
    FitBucket,
    Job,
    JobEvaluation,
    JobStatus,
    RemotePolicy,
    RemoteUncertainty,
    SalaryUncertainty,
    UserProfile,
    WorkAuthUncertainty,
)

# The design's per-refresh cap. Anything past it is reported as pending so a
# refresh returns useful results instead of spending a long AI budget.
DEFAULT_EVALUATION_LIMIT = 25

# Jobs the user has already closed out are not worth spending a call on.
_UNRANKABLE_STATUSES = (JobStatus.DISMISSED, JobStatus.CLOSED_ARCHIVED)

EvaluationChangeKind = Literal["evaluated", "reused"]


@dataclass(frozen=True)
class EvaluationRunCounts:
    """What one ranking pass did, for crawl reporting and the debug view."""

    evaluated: int
    reused: int
    pending: int
    filtered: int = 0


def job_content_hash(job: Job) -> str:
    """Hash the job facts an evaluation depends on.

    Must cover every field in `AIJobSnapshot`: a change the snapshot can see
    but the hash cannot would serve a stale evaluation forever.
    """
    values = (
        job.canonical_title,
        job.canonical_company,
        job.canonical_location,
        job.remote_policy,
        str(job.salary_unknown),
    )
    return sha256("\x1f".join(value or "" for value in values).encode()).hexdigest()


def evaluate_job(
    session: Session,
    service: AIService,
    profile: UserProfile,
    job: Job,
    *,
    crawl_run_id: UUID | None = None,
) -> tuple[JobEvaluation, EvaluationChangeKind]:
    """Return this job's current evaluation, calling the provider only if needed."""
    content_hash = job_content_hash(job)
    existing = _find_evaluation(session, profile, job, content_hash)
    return _evaluate(
        session, service, profile, job, content_hash, existing, crawl_run_id
    )


def evaluate_pending_jobs(
    session: Session,
    service: AIService,
    profile: UserProfile,
    *,
    limit: int = DEFAULT_EVALUATION_LIMIT,
    crawl_run_id: UUID | None = None,
) -> EvaluationRunCounts:
    """Rank the newest unevaluated jobs, leaving the rest reported as pending.

    The cap counts provider calls only: reusing a cached evaluation is free, so
    it never consumes budget a new job could have used. Provider calls are
    logged against *crawl_run_id* when one is supplied.
    """
    if limit < 0:
        raise ValueError("Evaluation limit cannot be negative")

    jobs = session.scalars(
        select(Job)
        .where(Job.status.notin_(_UNRANKABLE_STATUSES))
        .order_by(Job.first_seen_at.desc(), Job.id)
    ).all()

    evaluated = reused = pending = filtered = 0
    for job in jobs:
        skip_reason = check_eligibility(job, profile)
        if skip_reason is not None:
            job.skip_reason = skip_reason
            filtered += 1
            continue

        if job.skip_reason is not None:
            job.skip_reason = None

        content_hash = job_content_hash(job)
        existing = _find_evaluation(session, profile, job, content_hash)
        is_current = existing is not None and _is_current(existing, profile)
        if not is_current and evaluated >= limit:
            pending += 1
            continue
        _, change = _evaluate(
            session, service, profile, job, content_hash, existing, crawl_run_id
        )
        if change == "evaluated":
            evaluated += 1
        else:
            reused += 1
    return EvaluationRunCounts(
        evaluated=evaluated, reused=reused, pending=pending, filtered=filtered
    )


def _is_current(evaluation: JobEvaluation, profile: UserProfile) -> bool:
    """Whether a cached evaluation still reflects the profile as it stands."""
    return evaluation.profile_version == profile.profile_version


def _evaluate(
    session: Session,
    service: AIService,
    profile: UserProfile,
    job: Job,
    content_hash: str,
    existing: JobEvaluation | None,
    crawl_run_id: UUID | None = None,
) -> tuple[JobEvaluation, EvaluationChangeKind]:
    """Call the provider unless the cached evaluation is still current."""
    if existing is not None and _is_current(existing, profile):
        return existing, "reused"

    result = service.evaluate_job(
        profile, _build_request(profile, job, content_hash), crawl_run_id=crawl_run_id
    )
    evaluation = existing or JobEvaluation(
        job_id=job.id, profile_id=profile.id, job_content_hash=content_hash
    )
    _apply_result(evaluation, result, job, profile, service)
    # Keeps the dashboard's bucket grouping in step with the stored evaluation.
    job.fit_bucket = evaluation.fit_bucket
    session.add(evaluation)
    session.flush()
    return evaluation, "evaluated"


def _find_evaluation(
    session: Session, profile: UserProfile, job: Job, content_hash: str
) -> JobEvaluation | None:
    """Look up the cached evaluation for this exact job content and profile."""
    return session.scalar(
        select(JobEvaluation).where(
            JobEvaluation.job_id == job.id,
            JobEvaluation.profile_id == profile.id,
            JobEvaluation.job_content_hash == content_hash,
        )
    )


def _build_request(
    profile: UserProfile, job: Job, content_hash: str
) -> AIJobEvaluationRequest:
    return AIJobEvaluationRequest(
        profile_id=profile.id,
        job_id=job.id,
        profile_version=profile.profile_version,
        job_content_hash=content_hash,
        job=AIJobSnapshot(
            title=job.canonical_title,
            company=job.canonical_company,
            location=job.canonical_location,
            remote_policy=job.remote_policy,
            salary_unknown=job.salary_unknown,
        ),
        profile=AIProfileSnapshot(
            target_role_families=tuple(profile.target_role_families or ()),
            preferred_tech=tuple(profile.preferred_tech or ()),
            avoided_tech=tuple(profile.avoided_tech or ()),
            dealbreakers=tuple(profile.dealbreakers or ()),
            remote_preference=profile.remote_preference,
            salary_floor=profile.salary_floor,
        ),
    )


def _apply_result(
    evaluation: JobEvaluation,
    result: AIJobEvaluationResult,
    job: Job,
    profile: UserProfile,
    service: AIService,
) -> None:
    """Write a provider result onto an evaluation row.

    Reused for refreshes so a re-evaluation updates the existing row: the
    schema allows only one evaluation per job, profile, and content hash.
    """
    salary = _salary_uncertainty(job)
    remote = _remote_uncertainty(job)
    work_auth = _work_auth_uncertainty()

    evaluation.profile_version = profile.profile_version
    evaluation.fit_bucket = _parse_fit_bucket(result.fit_bucket)
    evaluation.internal_score = result.internal_score
    evaluation.matched_skills = list(result.matched_skills)
    evaluation.matched_preferences = list(result.matched_preferences)
    evaluation.concerns = list(result.concerns)
    evaluation.summary = result.summary
    evaluation.salary_uncertainty = salary
    evaluation.remote_uncertainty = remote
    evaluation.work_auth_uncertainty = work_auth
    evaluation.uncertainties = _uncertainties(salary, remote, work_auth)
    evaluation.verify_before_applying = _verify_before_applying(salary, remote)
    evaluation.model_provider = service.provider.provider_name
    evaluation.model_name = service.provider.model_name


def _parse_fit_bucket(value: str) -> FitBucket:
    """Validate the one free-form field a provider controls."""
    try:
        return FitBucket(value)
    except ValueError as error:
        raise ValueError(
            f"Provider returned an unknown fit bucket: {value!r}"
        ) from error


def _salary_uncertainty(job: Job) -> SalaryUncertainty:
    return SalaryUncertainty.UNKNOWN if job.salary_unknown else SalaryUncertainty.KNOWN


def _remote_uncertainty(job: Job) -> RemoteUncertainty:
    known = {
        RemotePolicy.REMOTE.value,
        RemotePolicy.HYBRID.value,
        RemotePolicy.ONSITE.value,
    }
    return (
        RemoteUncertainty.CLEAR
        if job.remote_policy in known
        else RemoteUncertainty.UNCLEAR
    )


def _work_auth_uncertainty() -> WorkAuthUncertainty:
    """Always unclear: nothing in the pipeline reads sponsorship terms yet."""
    return WorkAuthUncertainty.UNCLEAR


def _uncertainties(
    salary: SalaryUncertainty,
    remote: RemoteUncertainty,
    work_auth: WorkAuthUncertainty,
) -> list[str]:
    labels = []
    if salary != SalaryUncertainty.KNOWN:
        labels.append(f"salary_{salary.value}")
    if remote != RemoteUncertainty.CLEAR:
        labels.append(f"remote_{remote.value}")
    if work_auth != WorkAuthUncertainty.CLEAR:
        labels.append(f"work_auth_{work_auth.value}")
    return labels


def _verify_before_applying(
    salary: SalaryUncertainty, remote: RemoteUncertainty
) -> list[str]:
    checks = []
    if salary != SalaryUncertainty.KNOWN:
        checks.append("Confirm the salary range")
    if remote != RemoteUncertainty.CLEAR:
        checks.append("Confirm the remote policy")
    checks.append("Confirm work authorization requirements")
    return checks
