"""Tests for the Netflix source adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from pookie_backend.adapters.netflix import (
    _parse_posting,
    fetch_netflix_postings,
)
from pookie_backend.models import ApprovalStatus, JobSource, SourceKind

FIXTURES = Path(__file__).parent / "fixtures"
NETFLIX_HOST = "explore.jobs.netflix.net"


def _make_source(
    domain: str = "netflix.com",
    host: str = NETFLIX_HOST,
    company: str = "Netflix",
) -> JobSource:
    """Build an in-memory JobSource without touching the database."""
    return JobSource(
        id=uuid4(),
        kind=SourceKind.NETFLIX,
        name=f"{company} Careers",
        company_name=company,
        base_url=f"https://{host}",
        external_board_id=domain,
        approval_status=ApprovalStatus.APPROVED,
    )


def _fixture_json(name: str = "netflix_netflix.json") -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


def _page_transport(
    pages: dict[int, list[dict[str, Any]]],
    total: int | None = 497,
    status_code: int = 200,
    requests: list[httpx.Request] | None = None,
) -> httpx.MockTransport:
    """Serve list pages keyed by the request's ``start`` value."""

    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        if status_code != 200:
            return httpx.Response(status_code, content=b"")
        start = int(request.url.params["start"])
        body: dict[str, Any] = {"positions": pages.get(start, [])}
        if total is not None:
            body["count"] = total
        return httpx.Response(200, content=json.dumps(body).encode())

    return httpx.MockTransport(handler)


class TestParsePosting:
    def test_parses_complete_posting(self) -> None:
        source = _make_source()
        entry = _fixture_json()["positions"][0]

        posting = _parse_posting(entry, source.company_name, NETFLIX_HOST)

        assert posting is not None
        assert posting.source_posting_id == "790298014263"
        assert posting.raw_title == (
            "AI Engineer 6 - AI Foundation & Tooling, Ads Platform"
        )
        assert posting.raw_company == "Netflix"
        assert posting.raw_location == "USA - Remote"
        assert posting.raw_description is None
        assert posting.source_url == posting.apply_url
        assert posting.source_url == (
            "https://explore.jobs.netflix.net/careers/job/790298014263"
        )

    def test_constructs_url_without_canonical(self) -> None:
        entry = {
            "id": 790300000001,
            "name": "Engineer",
            "location": "Los Gatos,California,United States of America",
        }
        posting = _parse_posting(entry, "Netflix", NETFLIX_HOST)
        assert posting is not None
        assert posting.source_url == (
            "https://explore.jobs.netflix.net/careers/job/790300000001"
        )

    def test_location_falls_back_to_locations_list(self) -> None:
        entry = {
            "id": 790300000002,
            "name": "Engineer",
            "locations": ["USA - Remote"],
        }
        posting = _parse_posting(entry, "Netflix", NETFLIX_HOST)
        assert posting is not None
        assert posting.raw_location == "USA - Remote"

    def test_missing_location_is_none(self) -> None:
        entry = {"id": 790300000003, "name": "Engineer"}
        posting = _parse_posting(entry, "Netflix", NETFLIX_HOST)
        assert posting is not None
        assert posting.raw_location is None

    def test_keeps_nonempty_description(self) -> None:
        entry = {
            "id": 790300000004,
            "name": "Engineer",
            "job_description": "Build things",
        }
        posting = _parse_posting(entry, "Netflix", NETFLIX_HOST)
        assert posting is not None
        assert posting.raw_description == "Build things"

    def test_empty_description_is_none(self) -> None:
        entry = {
            "id": 790300000005,
            "name": "Engineer",
            "job_description": "",
        }
        posting = _parse_posting(entry, "Netflix", NETFLIX_HOST)
        assert posting is not None
        assert posting.raw_description is None

    def test_title_falls_back_to_posting_name(self) -> None:
        entry = {"id": 790300000006, "posting_name": "Engineer"}
        posting = _parse_posting(entry, "Netflix", NETFLIX_HOST)
        assert posting is not None
        assert posting.raw_title == "Engineer"

    def test_skips_posting_without_title(self) -> None:
        entry = {"id": 790300000007}
        assert _parse_posting(entry, "Netflix", NETFLIX_HOST) is None

    def test_skips_posting_without_id(self) -> None:
        entry = {"name": "Engineer"}
        assert _parse_posting(entry, "Netflix", NETFLIX_HOST) is None


class TestFetchNetflixPostings:
    def test_success_with_fixture(self) -> None:
        source = _make_source()
        data = _fixture_json()
        client = httpx.Client(
            transport=_page_transport({0: data["positions"]}, total=data["count"])
        )

        result = fetch_netflix_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 3
        assert "AI Engineer 6 - AI Foundation & Tooling, Ads Platform" in [
            p.raw_title for p in result.postings
        ]

    def test_paginates_until_total_reached(self) -> None:
        source = _make_source()
        page_one = [{"id": 790300000000 + i, "name": f"Job {i}"} for i in range(10)]
        page_two = [{"id": 790300000010, "name": "Job 10"}]
        requests: list[httpx.Request] = []
        client = httpx.Client(
            transport=_page_transport(
                {0: page_one, 10: page_two}, total=11, requests=requests
            )
        )

        result = fetch_netflix_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 11
        assert [p.source_posting_id for p in result.postings][-1] == "790300000010"
        assert [str(r.url.params["start"]) for r in requests] == ["0", "10"]
        for request in requests:
            assert request.url.params["domain"] == "netflix.com"
            assert request.url.params["num"] == "10"
            assert request.url.host == NETFLIX_HOST
            assert request.url.path == "/api/apply/v2/jobs"

    def test_deduplicates_repeated_posting_ids(self) -> None:
        """Board churn mid-fetch can re-sight a posting on a later page."""
        source = _make_source()
        page_one = [
            {"id": 790300000000 + i, "name": f"Job {i}"} for i in range(9)
        ] + [{"id": 790300000100, "name": "Job A"}]
        page_two = [
            {"id": 790300000100, "name": "Job A"},
            {"id": 790300000101, "name": "Job B"},
        ]
        client = httpx.Client(
            transport=_page_transport({0: page_one, 10: page_two}, total=20)
        )

        result = fetch_netflix_postings(source, client=client)

        assert result.error is None
        ids = [p.source_posting_id for p in result.postings]
        assert len(ids) == 11
        assert ids.count("790300000100") == 1
        assert ids[-1] == "790300000101"

    def test_page_cap_reached(self) -> None:
        source = _make_source()
        client = httpx.Client(
            transport=_page_transport(
                {
                    0: [
                        {"id": 790300000000 + i, "name": f"Job {i}"}
                        for i in range(10)
                    ]
                },
                total=20000,
            )
        )

        result = fetch_netflix_postings(source, client=client)

        assert result.error is not None
        assert "page cap" in result.error
        assert result.postings == []

    def test_stops_on_empty_page_without_total(self) -> None:
        source = _make_source()
        page_one = [{"id": 790300000000, "name": "Job 0"}]
        requests: list[httpx.Request] = []
        client = httpx.Client(
            transport=_page_transport({0: page_one}, total=None, requests=requests)
        )

        result = fetch_netflix_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 1
        assert len(requests) == 2

    def test_empty_board(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_page_transport({0: []}, total=0))

        result = fetch_netflix_postings(source, client=client)
        assert result.error is None
        assert result.postings == []

    def test_skips_malformed_entries_across_pages(self) -> None:
        source = _make_source()
        page_one = [
            {"id": 790300000001, "name": "Good Job"},
            {"name": "No Id"},
            {"id": 790300000002},
        ]
        client = httpx.Client(transport=_page_transport({0: page_one}, total=100))

        result = fetch_netflix_postings(source, client=client)
        assert result.error is None
        assert len(result.postings) == 1
        assert result.postings[0].raw_title == "Good Job"

    def test_missing_board_id(self) -> None:
        source = _make_source()
        source.external_board_id = None

        result = fetch_netflix_postings(source)
        assert result.error == "missing external_board_id"
        assert result.postings == []

    def test_invalid_base_url(self) -> None:
        source = _make_source()
        source.base_url = "not a url"

        result = fetch_netflix_postings(source)
        assert result.error == "invalid base_url"
        assert result.postings == []

    def test_http_404(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_page_transport({}, status_code=404))

        result = fetch_netflix_postings(source, client=client)
        assert result.error is not None
        assert "404" in result.error
        assert result.postings == []

    def test_http_500_on_later_page_discards_all(self) -> None:
        source = _make_source()
        page_one = [
            {"id": 790300000000 + i, "name": f"Job {i}"} for i in range(10)
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            if int(request.url.params["start"]) == 0:
                return httpx.Response(
                    200,
                    content=json.dumps({"count": 20, "positions": page_one}).encode(),
                )
            return httpx.Response(500, content=b"")

        client = httpx.Client(transport=httpx.MockTransport(handler))

        result = fetch_netflix_postings(source, client=client)
        assert result.error is not None
        assert "500" in result.error
        assert "offset 10" in result.error
        assert result.postings == []

    def test_invalid_json(self) -> None:
        source = _make_source()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"not json")

        client = httpx.Client(transport=httpx.MockTransport(handler))

        result = fetch_netflix_postings(source, client=client)
        assert result.error is not None
        assert "invalid JSON" in result.error

    def test_non_object_json(self) -> None:
        source = _make_source()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"[1, 2, 3]")

        client = httpx.Client(transport=httpx.MockTransport(handler))

        result = fetch_netflix_postings(source, client=client)
        assert result.error is not None
        assert "invalid JSON" in result.error

    def test_missing_positions_key(self) -> None:
        source = _make_source()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=json.dumps({"count": 0}).encode())

        client = httpx.Client(transport=httpx.MockTransport(handler))

        result = fetch_netflix_postings(source, client=client)
        assert result.error is not None
        assert "missing positions" in result.error

    def test_timeout(self) -> None:
        source = _make_source()

        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        client = httpx.Client(transport=httpx.MockTransport(timeout_handler))

        result = fetch_netflix_postings(source, client=client)
        assert result.error is not None
        assert "timeout" in result.error

    def test_network_error(self) -> None:
        source = _make_source()

        def error_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        client = httpx.Client(transport=httpx.MockTransport(error_handler))

        result = fetch_netflix_postings(source, client=client)
        assert result.error is not None
        assert "network error" in result.error
