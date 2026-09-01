"""Tests for the core profile and ingestion schema metadata."""

from pookie_backend.database import Base
from pookie_backend.models import (
    ApprovalStatus,
    CrawlRun,
    CrawlStatus,
    CrawlTrigger,
    JobSource,
    RawJobPosting,
    SourceKind,
    SourceRun,
    SourceRunStatus,
    SourceStatus,
    UserProfile,
)


def test_core_tables_are_registered_with_metadata():
    assert set(Base.metadata.tables) == {
        "user_profiles",
        "job_sources",
        "crawl_runs",
        "source_runs",
        "raw_job_postings",
    }


def test_core_enums_use_persisted_values():
    assert [member.value for member in SourceKind] == [
        "greenhouse",
        "lever",
        "ashby",
        "company_page",
    ]
    assert [member.value for member in SourceStatus] == [
        "active",
        "paused",
        "needs_review",
    ]
    assert [member.value for member in ApprovalStatus] == [
        "approved",
        "suggested",
        "rejected",
    ]
    assert [member.value for member in CrawlTrigger] == [
        "on_demand",
        "manual_script",
        "scheduled",
    ]
    assert [member.value for member in CrawlStatus] == [
        "running",
        "partial_success",
        "success",
        "failed",
    ]
    assert [member.value for member in SourceRunStatus] == [
        "running",
        "success",
        "failed",
        "skipped",
    ]


def test_raw_postings_have_source_identity_constraint():
    constraints = RawJobPosting.__table__.constraints
    assert any(
        constraint.name == "uq_raw_postings_source_identity"
        for constraint in constraints
    )


def test_source_runs_and_postings_reference_sources():
    assert SourceRun.__table__.c.job_source_id.foreign_keys
    assert RawJobPosting.__table__.c.job_source_id.foreign_keys
    assert JobSource.__table__.c.id.primary_key
    assert CrawlRun.__table__.c.id.primary_key
    assert UserProfile.__table__.c.id.primary_key
