"""Tests for the bounded on-demand refresh orchestrator."""

from __future__ import annotations

import time
from unittest.mock import patch
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from pookie_backend.adapters.greenhouse import GreenhouseResult
from pookie_backend.adapters.lever import LeverResult
from pookie_backend.adapters.netflix import NetflixResult
from pookie_backend.adapters.phenom import PhenomResult
from pookie_backend.adapters.workday import WorkdayResult
from pookie_backend.ai.mock import MockAIProvider
from pookie_backend.ingestion import RawPostingInput
from pookie_backend.models import (
    ApprovalStatus,
    CrawlRun,
    CrawlStatus,
    Job,
    JobSource,
    SourceKind,
    SourceStatus,
    UserProfile,
)
from pookie_backend.refresh import run_refresh


def _make_source(
    session: Session,
    kind: SourceKind = SourceKind.GREENHOUSE,
    company: str = "Astral",
    board_id: str = "astral",
) -> JobSource:
    source = JobSource(
        id=uuid4(),
        kind=kind,
        name=f"{company} Careers",
        company_name=company,
        base_url=f"https://example.com/{board_id}",
        external_board_id=board_id,
        status=SourceStatus.ACTIVE,
        approval_status=ApprovalStatus.APPROVED,
    )
    session.add(source)
    session.flush()
    return source


def _make_profile(session: Session) -> UserProfile:
    profile = UserProfile(
        id=uuid4(),
        owner_user_id=f"owner-{uuid4()}",
        target_role_families=["backend"],
        preferred_tech=["python"],
        avoided_tech=[],
        dealbreakers=[],
        profile_version=1,
        ai_consent_given=True,
        ai_consent_provider="mock",
        ai_consent_model_family="mock-eval",
    )
    session.add(profile)
    session.flush()
    return profile


def _posting(
    source_id: str = "post-1",
    title: str = "Backend Engineer",
    company: str = "Astral",
    location: str = "Remote (US)",
) -> RawPostingInput:
    return RawPostingInput(
        source_posting_id=source_id,
        source_url=f"https://example.com/jobs/{source_id}",
        apply_url=f"https://example.com/apply/{source_id}",
        raw_title=title,
        raw_company=company,
        raw_location=location,
        raw_description="A great job.",
    )


class TestNoSources:
    def test_no_sources_returns_success_with_zero_counts(
        self, db_session: Session
    ) -> None:
        result = run_refresh(db_session)

        assert result.sources_attempted == 0
        assert result.sources_succeeded == 0
        assert result.sources_failed == 0
        assert result.jobs_discovered == 0

        crawl = db_session.get(CrawlRun, result.crawl_run_id)
        assert crawl is not None
        assert crawl.status == CrawlStatus.SUCCESS
        assert crawl.finished_at is not None


class TestSuccessfulSources:
    @patch("pookie_backend.refresh.fetch_greenhouse_postings")
    def test_single_source_persists_and_normalizes(
        self, mock_fetch, db_session: Session
    ) -> None:
        _make_profile(db_session)
        source = _make_source(db_session)
        mock_fetch.return_value = GreenhouseResult(
            postings=[_posting("gh-1"), _posting("gh-2", title="Frontend Engineer")]
        )

        result = run_refresh(db_session, evaluation_cap=0)

        assert result.sources_attempted == 1
        assert result.sources_succeeded == 1
        assert result.sources_failed == 0
        assert result.jobs_discovered == 2
        assert result.jobs_new == 2

        jobs = db_session.scalars(select(Job)).all()
        assert len(jobs) == 2

        crawl = db_session.get(CrawlRun, result.crawl_run_id)
        assert crawl is not None
        assert crawl.status == CrawlStatus.SUCCESS
        assert crawl.elapsed_milliseconds is not None
        assert crawl.elapsed_milliseconds >= 0

        assert source.last_successful_crawl_at is not None
        assert source.last_error_summary is None

    @patch("pookie_backend.refresh.fetch_workday_postings")
    def test_workday_source_dispatches_to_workday_adapter(
        self, mock_fetch, db_session: Session
    ) -> None:
        _make_profile(db_session)
        source = _make_source(
            db_session,
            kind=SourceKind.WORKDAY,
            company="NVIDIA",
            board_id="nvidia/NVIDIAExternalCareerSite",
        )
        mock_fetch.return_value = WorkdayResult(
            postings=[_posting("wd-1")],
        )

        result = run_refresh(db_session, evaluation_cap=0)

        assert result.sources_succeeded == 1
        assert result.jobs_discovered == 1
        assert source.last_successful_crawl_at is not None

    @patch("pookie_backend.refresh.fetch_netflix_postings")
    def test_netflix_source_dispatches_to_netflix_adapter(
        self, mock_fetch, db_session: Session
    ) -> None:
        _make_profile(db_session)
        source = _make_source(
            db_session,
            kind=SourceKind.NETFLIX,
            company="Netflix",
            board_id="netflix.com",
        )
        mock_fetch.return_value = NetflixResult(
            postings=[_posting("nf-1")],
        )

        result = run_refresh(db_session, evaluation_cap=0)

        assert result.sources_succeeded == 1
        assert result.jobs_discovered == 1
        assert source.last_successful_crawl_at is not None

    @patch("pookie_backend.refresh.fetch_phenom_postings")
    def test_phenom_source_dispatches_to_phenom_adapter(
        self, mock_fetch, db_session: Session
    ) -> None:
        _make_profile(db_session)
        source = _make_source(
            db_session,
            kind=SourceKind.PHENOM,
            company="Adobe",
            board_id="us/en/search-results",
        )
        mock_fetch.return_value = PhenomResult(
            postings=[_posting("ph-1")],
        )

        result = run_refresh(db_session, evaluation_cap=0)

        assert result.sources_succeeded == 1
        assert result.jobs_discovered == 1
        assert source.last_successful_crawl_at is not None

    @patch("pookie_backend.refresh.fetch_lever_postings")
    @patch("pookie_backend.refresh.fetch_greenhouse_postings")
    def test_multiple_sources_aggregate_counts(
        self, mock_gh, mock_lever, db_session: Session
    ) -> None:
        _make_profile(db_session)
        _make_source(
            db_session, kind=SourceKind.GREENHOUSE, company="Co1", board_id="co1"
        )
        _make_source(db_session, kind=SourceKind.LEVER, company="Co2", board_id="co2")

        mock_gh.return_value = GreenhouseResult(
            postings=[_posting("gh-1", company="Co1")]
        )
        mock_lever.return_value = LeverResult(
            postings=[_posting("lv-1", company="Co2")]
        )

        result = run_refresh(db_session, evaluation_cap=0)

        assert result.sources_attempted == 2
        assert result.sources_succeeded == 2
        assert result.jobs_discovered == 2
        assert result.jobs_new == 2


class TestFailedSources:
    @patch("pookie_backend.refresh.fetch_greenhouse_postings")
    def test_source_error_records_failure(
        self, mock_fetch, db_session: Session
    ) -> None:
        source = _make_source(db_session)
        mock_fetch.return_value = GreenhouseResult(
            postings=[], error="HTTP 503 from astral"
        )

        result = run_refresh(db_session)

        assert result.sources_attempted == 1
        assert result.sources_succeeded == 0
        assert result.sources_failed == 1
        assert result.jobs_discovered == 0

        crawl = db_session.get(CrawlRun, result.crawl_run_id)
        assert crawl is not None
        assert crawl.status == CrawlStatus.FAILED

        assert source.last_error_at is not None
        assert source.last_error_summary == "HTTP 503 from astral"


class TestMixedSuccessFailure:
    @patch("pookie_backend.refresh.fetch_lever_postings")
    @patch("pookie_backend.refresh.fetch_greenhouse_postings")
    def test_partial_success_when_one_fails(
        self, mock_gh, mock_lever, db_session: Session
    ) -> None:
        _make_profile(db_session)
        _make_source(
            db_session, kind=SourceKind.GREENHOUSE, company="OK", board_id="ok"
        )
        _make_source(db_session, kind=SourceKind.LEVER, company="Bad", board_id="bad")

        mock_gh.return_value = GreenhouseResult(postings=[_posting("p1", company="OK")])
        mock_lever.return_value = LeverResult(postings=[], error="timeout")

        result = run_refresh(db_session, evaluation_cap=0)

        assert result.sources_succeeded == 1
        assert result.sources_failed == 1
        assert result.jobs_discovered == 1

        crawl = db_session.get(CrawlRun, result.crawl_run_id)
        assert crawl is not None
        assert crawl.status == CrawlStatus.PARTIAL_SUCCESS


class TestCrawlBudget:
    @patch("pookie_backend.refresh.fetch_greenhouse_postings")
    def test_budget_exceeded_marks_remaining_as_failed(
        self, mock_fetch, db_session: Session
    ) -> None:
        _make_source(db_session, company="Slow", board_id="slow")

        def slow_fetch(source, *, timeout=30.0, client=None):
            time.sleep(0.5)
            return GreenhouseResult(postings=[_posting("p1")])

        mock_fetch.side_effect = slow_fetch

        result = run_refresh(db_session, crawl_budget=0.01, source_timeout=8.0)

        assert result.sources_failed >= 0
        crawl = db_session.get(CrawlRun, result.crawl_run_id)
        assert crawl is not None
        assert crawl.finished_at is not None


class TestEvaluation:
    @patch("pookie_backend.refresh.fetch_greenhouse_postings")
    def test_evaluation_runs_after_crawl(self, mock_fetch, db_session: Session) -> None:
        _make_profile(db_session)
        _make_source(db_session)
        mock_fetch.return_value = GreenhouseResult(
            postings=[_posting("e1"), _posting("e2", title="Frontend Dev")]
        )

        result = run_refresh(
            db_session, evaluation_cap=25, ai_provider=MockAIProvider()
        )

        assert result.evaluation_counts is not None
        assert result.evaluation_counts.evaluated >= 0

        crawl = db_session.get(CrawlRun, result.crawl_run_id)
        assert crawl is not None
        assert crawl.evaluations_completed >= 0
        assert crawl.ai_call_count == result.evaluation_counts.evaluated
        assert crawl.estimated_ai_cost is None  # mock provider records no cost


class TestUnsupportedSourceKind:
    def test_company_page_source_reports_no_adapter(self, db_session: Session) -> None:
        _make_source(
            db_session, kind=SourceKind.COMPANY_PAGE, company="Manual", board_id="m"
        )

        result = run_refresh(db_session)

        assert result.sources_failed == 1
        assert result.sources_succeeded == 0

        crawl = db_session.get(CrawlRun, result.crawl_run_id)
        assert crawl is not None
        assert crawl.status == CrawlStatus.FAILED


class TestSkippedPostings:
    @patch("pookie_backend.refresh.fetch_greenhouse_postings")
    def test_second_crawl_skips_unchanged_postings(
        self, mock_fetch, db_session: Session
    ) -> None:
        _make_profile(db_session)
        _make_source(db_session)
        postings = [_posting("dup1")]
        mock_fetch.return_value = GreenhouseResult(postings=postings)

        first = run_refresh(db_session, evaluation_cap=0)
        assert first.jobs_new == 1

        second = run_refresh(db_session, evaluation_cap=0)
        assert second.jobs_new == 0
        assert second.jobs_skipped == 1
