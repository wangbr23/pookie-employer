"""Tests for the Ashby source adapter."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import httpx

from pookie_backend.adapters.ashby import (
    _parse_job,
    fetch_ashby_postings,
)
from pookie_backend.models import ApprovalStatus, JobSource, SourceKind

FIXTURES = Path(__file__).parent / "fixtures"


def _make_source(
    board_id: str = "fathom",
    company: str = "Fathom",
) -> JobSource:
    """Build an in-memory JobSource without touching the database."""
    return JobSource(
        id=uuid4(),
        kind=SourceKind.ASHBY,
        name=f"{company} Careers",
        company_name=company,
        base_url=f"https://jobs.ashbyhq.com/{board_id}",
        external_board_id=board_id,
        approval_status=ApprovalStatus.APPROVED,
    )


def _fixture_json(name: str = "ashby_fathom.json") -> dict:
    return json.loads((FIXTURES / name).read_text())


def _mock_transport(
    body: dict | str | None = None,
    status_code: int = 200,
) -> httpx.MockTransport:
    """Return a transport that replies with the given JSON body."""
    if isinstance(body, dict):
        content = json.dumps(body).encode()
    elif isinstance(body, str):
        content = body.encode()
    else:
        content = b""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=content)

    return httpx.MockTransport(handler)


class TestParseJob:
    def test_parses_complete_job(self) -> None:
        source = _make_source()
        data = _fixture_json()
        job = data["jobs"][0]

        posting = _parse_job(job, source)
        assert posting is not None
        assert posting.source_posting_id == "a1b2c3d4-1111-2222-3333-444455556666"
        assert posting.raw_title == "Senior Software Engineer, Backend"
        assert posting.source_url == "https://jobs.ashbyhq.com/fathom/a1b2c3d4-1111-2222-3333-444455556666"
        assert posting.apply_url == "https://jobs.ashbyhq.com/fathom/a1b2c3d4-1111-2222-3333-444455556666/application"
        assert posting.raw_company == "Fathom"
        assert posting.raw_location == "San Francisco, CA"
        assert posting.raw_description is not None
        assert "Senior Backend Engineer" in posting.raw_description

    def test_parses_job_with_no_location(self) -> None:
        source = _make_source()
        job = {
            "id": "aaaa-bbbb",
            "title": "Engineer",
            "jobUrl": "https://jobs.ashbyhq.com/fathom/aaaa-bbbb",
        }
        posting = _parse_job(job, source)
        assert posting is not None
        assert posting.raw_location is None

    def test_skips_job_without_id(self) -> None:
        source = _make_source()
        job = {"title": "Engineer"}
        assert _parse_job(job, source) is None

    def test_skips_job_without_title(self) -> None:
        source = _make_source()
        job = {"id": "aaaa-bbbb"}
        assert _parse_job(job, source) is None

    def test_apply_url_falls_back_to_job_url(self) -> None:
        source = _make_source()
        job = {
            "id": "aaaa-bbbb",
            "title": "Engineer",
            "jobUrl": "https://jobs.ashbyhq.com/fathom/aaaa-bbbb",
        }
        posting = _parse_job(job, source)
        assert posting is not None
        assert posting.apply_url == posting.source_url


class TestFetchAshbyPostings:
    def test_success_with_fixture(self) -> None:
        source = _make_source()
        data = _fixture_json()
        client = httpx.Client(transport=_mock_transport(data))

        result = fetch_ashby_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 3
        titles = [p.raw_title for p in result.postings]
        assert "Senior Software Engineer, Backend" in titles
        assert "Product Manager" in titles

    def test_empty_board(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_mock_transport({"jobs": []}))

        result = fetch_ashby_postings(source, client=client)
        assert result.error is None
        assert result.postings == []

    def test_missing_board_id(self) -> None:
        source = _make_source()
        source.external_board_id = None

        result = fetch_ashby_postings(source)
        assert result.error == "missing external_board_id"
        assert result.postings == []

    def test_http_404(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_mock_transport(status_code=404))

        result = fetch_ashby_postings(source, client=client)
        assert result.error is not None
        assert "404" in result.error
        assert result.postings == []

    def test_http_500(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_mock_transport(status_code=500))

        result = fetch_ashby_postings(source, client=client)
        assert result.error is not None
        assert "500" in result.error

    def test_invalid_json(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_mock_transport(body="not json", status_code=200))

        result = fetch_ashby_postings(source, client=client)
        assert result.error is not None
        assert "invalid JSON" in result.error

    def test_timeout(self) -> None:
        source = _make_source()

        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        client = httpx.Client(transport=httpx.MockTransport(timeout_handler))

        result = fetch_ashby_postings(source, client=client)
        assert result.error is not None
        assert "timeout" in result.error

    def test_network_error(self) -> None:
        source = _make_source()

        def error_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        client = httpx.Client(transport=httpx.MockTransport(error_handler))

        result = fetch_ashby_postings(source, client=client)
        assert result.error is not None
        assert "network error" in result.error

    def test_skips_malformed_jobs(self) -> None:
        source = _make_source()
        data = {
            "jobs": [
                {"id": "aaa", "title": "Good Job", "jobUrl": "https://example.com/aaa"},
                {"id": None, "title": "Bad Job"},
                {"title": "No ID"},
                {"id": "bbb"},
            ]
        }
        client = httpx.Client(transport=_mock_transport(data))

        result = fetch_ashby_postings(source, client=client)
        assert result.error is None
        assert len(result.postings) == 1
        assert result.postings[0].raw_title == "Good Job"

    def test_company_name_from_source(self) -> None:
        source = _make_source(company="Ramp")
        data = {"jobs": [{"id": "xyz", "title": "Engineer", "jobUrl": "https://x.com"}]}
        client = httpx.Client(transport=_mock_transport(data))

        result = fetch_ashby_postings(source, client=client)
        assert result.postings[0].raw_company == "Ramp"
