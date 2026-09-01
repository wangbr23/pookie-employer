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
