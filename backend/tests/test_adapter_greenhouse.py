"""Tests for the Greenhouse source adapter."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

import httpx

from pookie_backend.adapters.greenhouse import (
    _parse_job,
    fetch_greenhouse_postings,
)
from pookie_backend.models import ApprovalStatus, JobSource, SourceKind

FIXTURES = Path(__file__).parent / "fixtures"


def _make_source(
    board_id: str = "astral",
    company: str = "Astral",
) -> JobSource:
    """Build an in-memory JobSource without touching the database."""
    return JobSource(
        id=uuid4(),
        kind=SourceKind.GREENHOUSE,
        name=f"{company} Careers",
        company_name=company,
        base_url=f"https://boards.greenhouse.io/{board_id}",
        external_board_id=board_id,
        approval_status=ApprovalStatus.APPROVED,
    )


def _fixture_json(name: str = "greenhouse_astral.json") -> dict:
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
        assert posting.source_posting_id == "4080029007"
        assert posting.raw_title == "Senior Software Engineer, Backend"
        assert posting.source_url == "https://boards.greenhouse.io/astral/jobs/4080029007"
        assert posting.apply_url == posting.source_url
        assert posting.raw_company == "Astral"
        assert posting.raw_location == "New York, NY"
        assert posting.raw_description is not None
        assert "Senior Software Engineer" in posting.raw_description

    def test_parses_job_with_no_location(self) -> None:
        source = _make_source()
        job = {"id": 123, "title": "Engineer", "absolute_url": "https://example.com/123"}
        posting = _parse_job(job, source)
        assert posting is not None
        assert posting.raw_location is None

    def test_skips_job_without_id(self) -> None:
        source = _make_source()
        job = {"title": "Engineer"}
        assert _parse_job(job, source) is None

    def test_skips_job_without_title(self) -> None:
        source = _make_source()
        job = {"id": 123}
        assert _parse_job(job, source) is None


class TestFetchGreenhousePostings:
    def test_success_with_fixture(self) -> None:
        source = _make_source()
        data = _fixture_json()
        client = httpx.Client(transport=_mock_transport(data))

        result = fetch_greenhouse_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 3
        titles = [p.raw_title for p in result.postings]
        assert "Senior Software Engineer, Backend" in titles
        assert "Product Manager" in titles

    def test_empty_board(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_mock_transport({"jobs": []}))

        result = fetch_greenhouse_postings(source, client=client)
        assert result.error is None
        assert result.postings == []

    def test_missing_board_id(self) -> None:
        source = _make_source()
        source.external_board_id = None

        result = fetch_greenhouse_postings(source)
        assert result.error == "missing external_board_id"
        assert result.postings == []

    def test_http_404(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_mock_transport(status_code=404))

        result = fetch_greenhouse_postings(source, client=client)
        assert result.error is not None
        assert "404" in result.error
        assert result.postings == []

    def test_http_500(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_mock_transport(status_code=500))

        result = fetch_greenhouse_postings(source, client=client)
        assert result.error is not None
        assert "500" in result.error

    def test_invalid_json(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_mock_transport(body="not json", status_code=200))

        result = fetch_greenhouse_postings(source, client=client)
        assert result.error is not None
        assert "invalid JSON" in result.error

    def test_timeout(self) -> None:
        source = _make_source()

        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        client = httpx.Client(transport=httpx.MockTransport(timeout_handler))

        result = fetch_greenhouse_postings(source, client=client)
        assert result.error is not None
        assert "timeout" in result.error

    def test_network_error(self) -> None:
        source = _make_source()

        def error_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        client = httpx.Client(transport=httpx.MockTransport(error_handler))

        result = fetch_greenhouse_postings(source, client=client)
        assert result.error is not None
        assert "network error" in result.error

    def test_skips_malformed_jobs(self) -> None:
        source = _make_source()
        data = {
            "jobs": [
                {"id": 1, "title": "Good Job", "absolute_url": "https://example.com/1"},
                {"id": None, "title": "Bad Job"},
                {"title": "No ID"},
                {"id": 2},
            ]
        }
        client = httpx.Client(transport=_mock_transport(data))

        result = fetch_greenhouse_postings(source, client=client)
        assert result.error is None
        assert len(result.postings) == 1
        assert result.postings[0].raw_title == "Good Job"

    def test_company_name_from_source(self) -> None:
        source = _make_source(company="Ramp")
        data = {"jobs": [{"id": 99, "title": "Engineer", "absolute_url": "https://x.com"}]}
        client = httpx.Client(transport=_mock_transport(data))

        result = fetch_greenhouse_postings(source, client=client)
        assert result.postings[0].raw_company == "Ramp"
