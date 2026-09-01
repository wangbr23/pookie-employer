"""Tests for the core profile and ingestion schema metadata."""

from pookie_backend.database import Base
from pookie_backend.models import (
    ApprovalStatus,
    CrawlRun,
    CrawlStatus,
    CrawlTrigger,
    FeedbackAction,
    FitBucket,
    Job,
    JobEvaluation,
    JobFeedback,
    JobLink,
    JobLinkStatus,
    JobSource,
    JobStatus,
    RawJobPosting,
    RemoteUncertainty,
    SalaryUncertainty,
    SourceKind,
    SourceRun,
    SourceRunStatus,
    SourceStatus,
    UserProfile,
    WorkAuthUncertainty,
)


def test_core_tables_are_registered_with_metadata():
    assert set(Base.metadata.tables) == {
        "user_profiles",
        "job_sources",
        "crawl_runs",
        "source_runs",
        "raw_job_postings",
        "jobs",
        "job_links",
        "job_evaluations",
        "job_feedback",
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


def test_recommendation_enums_have_design_values():
    assert {member.value for member in JobStatus} == {
        "new",
        "seen",
        "saved",
        "dismissed",
        "possibly_closed",
        "closed_archived",
    }
    assert {member.value for member in JobLinkStatus} == {
        "active",
        "broken",
        "possibly_closed",
        "closed",
    }
    assert {member.value for member in FitBucket} == {
        "strong",
        "possible",
        "stretch",
        "needs_review",
    }
    assert {member.value for member in SalaryUncertainty} == {
        "known",
        "unknown",
        "estimated",
        "conflicting",
    }
    assert {member.value for member in RemoteUncertainty} == {
        "clear",
        "unclear",
        "conflicting",
    }
    assert {member.value for member in WorkAuthUncertainty} == {
        "clear",
        "unclear",
        "conflicting",
    }
    assert {member.value for member in FeedbackAction} == {
        "save",
        "dismiss",
        "more_like_this",
        "less_like_this",
        "ai_wrong",
    }


def test_source_runs_and_postings_reference_sources():
    assert SourceRun.__table__.c.job_source_id.foreign_keys
    assert RawJobPosting.__table__.c.job_source_id.foreign_keys
    assert JobSource.__table__.c.id.primary_key
    assert CrawlRun.__table__.c.id.primary_key
    assert UserProfile.__table__.c.id.primary_key


def test_recommendation_tables_have_expected_relationship_keys():
    assert JobLink.__table__.c.job_id.foreign_keys
    assert JobEvaluation.__table__.c.profile_id.foreign_keys
    assert JobFeedback.__table__.c.profile_id.foreign_keys
    assert Job.__table__.c.id.primary_key
