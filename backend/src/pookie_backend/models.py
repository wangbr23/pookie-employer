"""SQLAlchemy models for profiles, sources, and crawl ingestion records."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.dialects.postgresql import UUID as PostgreSQLUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from pookie_backend.database import Base


class SourceKind(StrEnum):
    """Supported job-source adapter kinds."""

    GREENHOUSE = "greenhouse"
    LEVER = "lever"
    ASHBY = "ashby"
    COMPANY_PAGE = "company_page"


class SourceStatus(StrEnum):
    """Operational status for a configured job source."""

    ACTIVE = "active"
    PAUSED = "paused"
    NEEDS_REVIEW = "needs_review"


class ApprovalStatus(StrEnum):
    """Whether a source is approved for crawling."""

    APPROVED = "approved"
    SUGGESTED = "suggested"
    REJECTED = "rejected"


class CrawlTrigger(StrEnum):
    """What initiated a crawl run."""

    ON_DEMAND = "on_demand"
    MANUAL_SCRIPT = "manual_script"
    SCHEDULED = "scheduled"


class CrawlStatus(StrEnum):
    """Aggregate crawl-run result."""

    RUNNING = "running"
    PARTIAL_SUCCESS = "partial_success"
    SUCCESS = "success"
    FAILED = "failed"


class SourceRunStatus(StrEnum):
    """Result for one source within a crawl run."""

    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class JobStatus(StrEnum):
    """Lifecycle state shown for a canonical job."""

    NEW = "new"
    SEEN = "seen"
    SAVED = "saved"
    DISMISSED = "dismissed"
    POSSIBLY_CLOSED = "possibly_closed"
    CLOSED_ARCHIVED = "closed_archived"


class JobLinkStatus(StrEnum):
    """Availability state for a source or apply link."""

    ACTIVE = "active"
    BROKEN = "broken"
    POSSIBLY_CLOSED = "possibly_closed"
    CLOSED = "closed"


class FitBucket(StrEnum):
    """Coarse recommendation bucket for an evaluated job."""

    STRONG = "strong"
    POSSIBLE = "possible"
    STRETCH = "stretch"
    NEEDS_REVIEW = "needs_review"


class SalaryUncertainty(StrEnum):
    """Confidence state for salary information."""

    KNOWN = "known"
    UNKNOWN = "unknown"
    ESTIMATED = "estimated"
    CONFLICTING = "conflicting"


class RemoteUncertainty(StrEnum):
    """Confidence state for remote-work information."""

    CLEAR = "clear"
    UNCLEAR = "unclear"
    CONFLICTING = "conflicting"


class WorkAuthUncertainty(StrEnum):
    """Confidence state for work-authorization information."""

    CLEAR = "clear"
    UNCLEAR = "unclear"
    CONFLICTING = "conflicting"


class FeedbackAction(StrEnum):
    """Supported user feedback actions on recommendations."""

    SAVE = "save"
    DISMISS = "dismiss"
    MORE_LIKE_THIS = "more_like_this"
    LESS_LIKE_THIS = "less_like_this"
    AI_WRONG = "ai_wrong"


def enum_type(enum_class: type[StrEnum]) -> Enum:
    """Build a native PostgreSQL enum that persists the StrEnum values."""
    return Enum(
        enum_class,
        name=enum_class.__name__.lower(),
        native_enum=True,
        values_callable=lambda members: [member.value for member in members],
    )


class UserProfile(Base):
    """The persisted matching profile; the MVP uses one configured profile."""

    __tablename__ = "user_profiles"

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    owner_user_id: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    target_role_families: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    seniority_min: Mapped[int | None] = mapped_column(Integer)
    seniority_max: Mapped[int | None] = mapped_column(Integer)
    remote_preference: Mapped[str | None] = mapped_column(String(32))
    allowed_locations: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    work_authorization_constraints: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list
    )
    salary_floor: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    preferred_tech: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    avoided_tech: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    preferred_industries: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    avoided_industries: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    company_stage_preferences: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list
    )
    dealbreakers: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    notes: Mapped[str | None] = mapped_column(Text)
    profile_version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    evaluations: Mapped[list["JobEvaluation"]] = relationship(back_populates="profile")
    feedback: Mapped[list["JobFeedback"]] = relationship(back_populates="profile")


class JobSource(Base):
    """An allowlisted source that can be crawled for job postings."""

    __tablename__ = "job_sources"
    __table_args__ = (
        Index("ix_job_sources_status_approval", "status", "approval_status"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    kind: Mapped[SourceKind] = mapped_column(enum_type(SourceKind), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    base_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    external_board_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[SourceStatus] = mapped_column(
        enum_type(SourceStatus), nullable=False, default=SourceStatus.ACTIVE
    )
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        enum_type(ApprovalStatus), nullable=False, default=ApprovalStatus.SUGGESTED
    )
    last_successful_crawl_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    last_error_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error_summary: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    source_runs: Mapped[list["SourceRun"]] = relationship(back_populates="job_source")
    raw_postings: Mapped[list["RawJobPosting"]] = relationship(
        back_populates="job_source"
    )


class CrawlRun(Base):
    """Aggregate observability record for one crawl attempt."""

    __tablename__ = "crawl_runs"
    __table_args__ = (Index("ix_crawl_runs_status_started_at", "status", "started_at"),)

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    trigger: Mapped[CrawlTrigger] = mapped_column(
        enum_type(CrawlTrigger), nullable=False
    )
    status: Mapped[CrawlStatus] = mapped_column(enum_type(CrawlStatus), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sources_attempted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_succeeded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sources_failed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_new: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    evaluations_completed: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    evaluations_pending: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    elapsed_milliseconds: Mapped[int | None] = mapped_column(Integer)
    ai_call_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    estimated_ai_cost: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))

    source_runs: Mapped[list["SourceRun"]] = relationship(
        back_populates="crawl_run", cascade="all, delete-orphan"
    )


class SourceRun(Base):
    """Per-source result nested inside a crawl run."""

    __tablename__ = "source_runs"
    __table_args__ = (
        Index("ix_source_runs_crawl_run_status", "crawl_run_id", "status"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    crawl_run_id: Mapped[UUID] = mapped_column(
        ForeignKey("crawl_runs.id", ondelete="CASCADE"), nullable=False
    )
    job_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_sources.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[SourceRunStatus] = mapped_column(
        enum_type(SourceRunStatus), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    jobs_discovered: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_inserted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    jobs_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_summary: Mapped[str | None] = mapped_column(Text)

    crawl_run: Mapped[CrawlRun] = relationship(back_populates="source_runs")
    job_source: Mapped[JobSource] = relationship(back_populates="source_runs")


class RawJobPosting(Base):
    """Raw source payload retained for normalization and deduplication."""

    __tablename__ = "raw_job_postings"
    __table_args__ = (
        Index(
            "ix_raw_job_postings_source_content_hash", "job_source_id", "content_hash"
        ),
        Index("ix_raw_job_postings_last_seen_at", "last_seen_at"),
        UniqueConstraint(
            "job_source_id",
            "source_posting_id",
            name="uq_raw_postings_source_identity",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    job_source_id: Mapped[UUID] = mapped_column(
        ForeignKey("job_sources.id", ondelete="RESTRICT"), nullable=False
    )
    source_posting_id: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    apply_url: Mapped[str | None] = mapped_column(String(2048))
    raw_title: Mapped[str] = mapped_column(String(512), nullable=False)
    raw_company: Mapped[str | None] = mapped_column(String(255))
    raw_location: Mapped[str | None] = mapped_column(String(512))
    raw_description: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    closed_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    job_source: Mapped[JobSource] = relationship(back_populates="raw_postings")


class Job(Base):
    """Canonical job assembled from one or more raw postings."""

    __tablename__ = "jobs"
    __table_args__ = (
        Index("ix_jobs_status_fit_bucket", "status", "fit_bucket"),
        Index("ix_jobs_last_seen_at", "last_seen_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    canonical_title: Mapped[str] = mapped_column(String(512), nullable=False)
    canonical_company: Mapped[str] = mapped_column(String(255), nullable=False)
    canonical_location: Mapped[str | None] = mapped_column(String(512))
    remote_policy: Mapped[str | None] = mapped_column(String(32))
    employment_type: Mapped[str | None] = mapped_column(String(64))
    salary_min: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salary_max: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    salary_currency: Mapped[str | None] = mapped_column(String(3))
    salary_unknown: Mapped[bool] = mapped_column(default=True, nullable=False)
    seniority: Mapped[str | None] = mapped_column(String(64))
    status: Mapped[JobStatus] = mapped_column(
        enum_type(JobStatus), nullable=False, default=JobStatus.NEW
    )
    fit_bucket: Mapped[FitBucket | None] = mapped_column(enum_type(FitBucket))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    links: Mapped[list["JobLink"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    evaluations: Mapped[list["JobEvaluation"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    feedback: Mapped[list["JobFeedback"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )


class JobLink(Base):
    """A preserved source/apply link associated with a canonical job."""

    __tablename__ = "job_links"
    __table_args__ = (
        Index("ix_job_links_job_status", "job_id", "status"),
        UniqueConstraint("job_id", "raw_job_posting_id", name="uq_job_links_job_raw"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    raw_job_posting_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("raw_job_postings.id", ondelete="SET NULL")
    )
    source_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    apply_url: Mapped[str | None] = mapped_column(String(2048))
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[JobLinkStatus] = mapped_column(
        enum_type(JobLinkStatus), nullable=False, default=JobLinkStatus.ACTIVE
    )

    job: Mapped[Job] = relationship(back_populates="links")
    raw_job_posting: Mapped[RawJobPosting | None] = relationship()


class JobEvaluation(Base):
    """A profile-specific, cached evaluation of a canonical job."""

    __tablename__ = "job_evaluations"
    __table_args__ = (
        Index("ix_job_evaluations_profile_fit", "profile_id", "fit_bucket"),
        UniqueConstraint(
            "job_id",
            "profile_id",
            "job_content_hash",
            name="uq_job_evaluations_job_profile_content",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    profile_version: Mapped[int] = mapped_column(Integer, nullable=False)
    job_content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    fit_bucket: Mapped[FitBucket] = mapped_column(enum_type(FitBucket), nullable=False)
    internal_score: Mapped[Decimal | None] = mapped_column(Numeric(8, 3))
    matched_skills: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    matched_preferences: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    concerns: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    uncertainties: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    summary: Mapped[str | None] = mapped_column(Text)
    verify_before_applying: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list
    )
    salary_uncertainty: Mapped[SalaryUncertainty] = mapped_column(
        enum_type(SalaryUncertainty), nullable=False
    )
    remote_uncertainty: Mapped[RemoteUncertainty] = mapped_column(
        enum_type(RemoteUncertainty), nullable=False
    )
    work_auth_uncertainty: Mapped[WorkAuthUncertainty] = mapped_column(
        enum_type(WorkAuthUncertainty), nullable=False
    )
    model_provider: Mapped[str] = mapped_column(String(128), nullable=False)
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[Job] = relationship(back_populates="evaluations")
    profile: Mapped[UserProfile] = relationship(back_populates="evaluations")


class JobFeedback(Base):
    """User feedback used to track recommendation actions and corrections."""

    __tablename__ = "job_feedback"
    __table_args__ = (
        Index("ix_job_feedback_profile_created", "profile_id", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(
        PostgreSQLUUID(as_uuid=True), primary_key=True, default=uuid4
    )
    job_id: Mapped[UUID] = mapped_column(
        ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False
    )
    profile_id: Mapped[UUID] = mapped_column(
        ForeignKey("user_profiles.id", ondelete="CASCADE"), nullable=False
    )
    action: Mapped[FeedbackAction] = mapped_column(
        enum_type(FeedbackAction), nullable=False
    )
    reasons: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    free_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    job: Mapped[Job] = relationship(back_populates="feedback")
    profile: Mapped[UserProfile] = relationship(back_populates="feedback")
