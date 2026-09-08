"""Tests for the Workday source adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from pookie_backend.adapters.workday import (
    _parse_posting,
    fetch_workday_postings,
)
from pookie_backend.models import ApprovalStatus, JobSource, SourceKind

FIXTURES = Path(__file__).parent / "fixtures"
NVIDIA_HOST = "nvidia.wd5.myworkdayjobs.com"
NVIDIA_SITE = "NVIDIAExternalCareerSite"


def _make_source(
    tenant: str = "nvidia",
    site: str = NVIDIA_SITE,
    host: str = NVIDIA_HOST,
    company: str = "NVIDIA",
) -> JobSource:
    """Build an in-memory JobSource without touching the database."""
    return JobSource(
        id=uuid4(),
        kind=SourceKind.WORKDAY,
        name=f"{company} Careers",
        company_name=company,
        base_url=f"https://{host}/{site}",
        external_board_id=f"{tenant}/{site}",
        approval_status=ApprovalStatus.APPROVED,
    )


def _fixture_json(name: str = "workday_nvidia.json") -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


def _page_transport(
    pages: dict[int, list[dict[str, Any]]],
    total: int | None = 2000,
    status_code: int = 200,
    requests: list[httpx.Request] | None = None,
) -> httpx.MockTransport:
    """Serve list pages keyed by the request's ``offset`` value."""

    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        if status_code != 200:
            return httpx.Response(status_code, content=b"")
        payload = json.loads(request.content)
        entries = pages.get(payload["offset"], [])
        body: dict[str, Any] = {"jobPostings": entries}
        if total is not None:
            body["total"] = total
        return httpx.Response(200, content=json.dumps(body).encode())

    return httpx.MockTransport(handler)


class TestParsePosting:
    def test_parses_complete_posting(self) -> None:
        source = _make_source()
        entry = _fixture_json()["jobPostings"][0]

        posting = _parse_posting(
            entry, source.company_name, f"https://{NVIDIA_HOST}/{NVIDIA_SITE}"
        )

        assert posting is not None
        assert posting.source_posting_id == (
            "/job/US-TX-Austin/ASIC-Design-Engineer"
            "--Tools-and-Methodology-Development_JR2025219"
        )
        assert posting.raw_title == (
            "ASIC Design Engineer, Tools and Methodology Development"
        )
        assert posting.raw_company == "NVIDIA"
        assert posting.raw_location == "US, TX, Austin"
        assert posting.raw_description is None
        assert posting.source_url == posting.apply_url
        assert posting.source_url == (
            "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite"
            "/job/US-TX-Austin/ASIC-Design-Engineer"
            "--Tools-and-Methodology-Development_JR2025219"
        )

    def test_keeps_location_count_text(self) -> None:
        entry = {
            "title": "Engineer",
            "externalPath": "/job/x/y_JR1",
            "locationsText": "2 Locations",
        }
        posting = _parse_posting(entry, "NVIDIA", "https://h/site")
        assert posting is not None
        assert posting.raw_location == "2 Locations"

    def test_missing_location_is_none(self) -> None:
        entry = {"title": "Engineer", "externalPath": "/job/x/y_JR1"}
        posting = _parse_posting(entry, "NVIDIA", "https://h/site")
        assert posting is not None
        assert posting.raw_location is None

    def test_skips_posting_without_title(self) -> None:
        entry = {"externalPath": "/job/x/y_JR1"}
        assert _parse_posting(entry, "NVIDIA", "https://h/site") is None

    def test_skips_posting_without_external_path(self) -> None:
        entry = {"title": "Engineer"}
        assert _parse_posting(entry, "NVIDIA", "https://h/site") is None


class TestFetchWorkdayPostings:
    def test_success_with_fixture(self) -> None:
        source = _make_source()
        data = _fixture_json()
        client = httpx.Client(
            transport=_page_transport({0: data["jobPostings"]}, total=data["total"])
        )

        result = fetch_workday_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 3
        assert "ASIC Design Engineer, Tools and Methodology Development" in [
            p.raw_title for p in result.postings
        ]

    def test_paginates_until_total_reached(self) -> None:
        source = _make_source()
        page_one = [
            {"title": f"Job {i}", "externalPath": f"/job/a{i}_JR{i}"} for i in range(20)
        ]
        page_two = [
            {"title": "Job 20", "externalPath": "/job/a20_JR20"},
        ]
        requests: list[httpx.Request] = []
        client = httpx.Client(
            transport=_page_transport(
                {0: page_one, 20: page_two}, total=21, requests=requests
            )
        )

        result = fetch_workday_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 21
        assert [p.source_posting_id for p in result.postings][-1] == "/job/a20_JR20"
        payloads = [json.loads(r.content) for r in requests]
        assert payloads == [
            {"appliedFacets": {}, "limit": 20, "offset": 0},
            {"appliedFacets": {}, "limit": 20, "offset": 20},
        ]

    def test_later_page_totals_are_ignored(self) -> None:
        """Boards answer total: 0 on every page after the first; only page
        0's total drives pagination."""
        source = _make_source()
        page_one = [
            {"title": f"Job {i}", "externalPath": f"/job/a{i}_JR{i}"} for i in range(20)
        ]
        requests: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append(request)
            payload = json.loads(request.content)
            offset = payload["offset"]
            if offset == 0:
                entries, total = page_one, 100
            elif offset in (20, 40):
                entries = [
                    {
                        "title": f"Job {offset + i}",
                        "externalPath": f"/job/b{offset + i}_JRx",
                    }
                    for i in range(20)
                ]
                total = 0
            else:
                entries, total = [], 0
            return httpx.Response(
                200,
                content=json.dumps({"total": total, "jobPostings": entries}).encode(),
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))

        result = fetch_workday_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 60
        assert {json.loads(r.content)["offset"] for r in requests} == {
            0,
            20,
            40,
            60,
            80,
        }

    def test_deduplicates_repeated_posting_ids(self) -> None:
        """Board churn mid-fetch can re-sight a posting on a later page."""
        source = _make_source()
        page_one = [
            {
                "title": f"Job {i}",
                "externalPath": f"/job/a{i}_JR{i}",
                "locationsText": "US",
            }
            for i in range(19)
        ] + [{"title": "Job A", "externalPath": "/job/a_JR1", "locationsText": "US"}]
        page_two = [
            {"title": "Job A", "externalPath": "/job/a_JR1", "locationsText": "US"},
            {"title": "Job B", "externalPath": "/job/b_JR2", "locationsText": "US"},
        ]
        client = httpx.Client(
            transport=_page_transport({0: page_one, 20: page_two}, total=40)
        )

        result = fetch_workday_postings(source, client=client)

        assert result.error is None
        ids = [p.source_posting_id for p in result.postings]
        assert len(ids) == 21
        assert ids.count("/job/a_JR1") == 1
        assert ids[-1] == "/job/b_JR2"

    def test_page_cap_reached(self) -> None:
        source = _make_source()
        client = httpx.Client(
            transport=_page_transport(
                {
                    0: [
                        {"title": f"Job {i}", "externalPath": f"/job/a{i}_JR{i}"}
                        for i in range(20)
                    ]
                },
                total=20000,
            )
        )

        result = fetch_workday_postings(source, client=client)

        assert result.error is not None
        assert "page cap" in result.error
        assert result.postings == []

    def test_stops_on_empty_page_without_total(self) -> None:
        source = _make_source()
        page_one = [{"title": "Job 0", "externalPath": "/job/a_JR0"}]
        requests: list[httpx.Request] = []
        client = httpx.Client(
            transport=_page_transport({0: page_one}, total=None, requests=requests)
        )

        result = fetch_workday_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 1
        assert len(requests) == 2

    def test_empty_board(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_page_transport({0: []}, total=0))

        result = fetch_workday_postings(source, client=client)
        assert result.error is None
        assert result.postings == []

    def test_skips_malformed_entries_across_pages(self) -> None:
        source = _make_source()
        page_one = [
            {"title": "Good Job", "externalPath": "/job/good_JR1"},
            {"title": "No Path"},
            {"externalPath": "/job/no-title_JR2"},
        ]
        client = httpx.Client(transport=_page_transport({0: page_one}, total=100))

        result = fetch_workday_postings(source, client=client)
        assert result.error is None
        assert len(result.postings) == 1
        assert result.postings[0].raw_title == "Good Job"

    def test_missing_board_id(self) -> None:
        source = _make_source()
        source.external_board_id = None

        result = fetch_workday_postings(source)
        assert result.error == "external_board_id must be 'tenant/site'"
        assert result.postings == []

    def test_board_id_without_site(self) -> None:
        source = _make_source()
        source.external_board_id = "nvidia"

        result = fetch_workday_postings(source)
        assert result.error == "external_board_id must be 'tenant/site'"

    def test_invalid_base_url(self) -> None:
        source = _make_source()
        source.base_url = "not a url"

        result = fetch_workday_postings(source)
        assert result.error == "invalid base_url"
        assert result.postings == []

    def test_http_404(self) -> None:
        source = _make_source()
        client = httpx.Client(transport=_page_transport({}, status_code=404))

        result = fetch_workday_postings(source, client=client)
        assert result.error is not None
        assert "404" in result.error
        assert result.postings == []

    def test_http_500_on_later_page_discards_all(self) -> None:
        source = _make_source()
        page_one = [
            {"title": f"Job {i}", "externalPath": f"/job/a{i}_JR{i}"} for i in range(20)
        ]

        def handler(request: httpx.Request) -> httpx.Response:
            payload = json.loads(request.content)
            if payload["offset"] == 0:
                return httpx.Response(
                    200,
                    content=json.dumps({"total": 40, "jobPostings": page_one}).encode(),
                )
            return httpx.Response(500, content=b"")

        client = httpx.Client(transport=httpx.MockTransport(handler))

        result = fetch_workday_postings(source, client=client)
        assert result.error is not None
        assert "500" in result.error
        assert "offset 20" in result.error
        assert result.postings == []

    def test_invalid_json(self) -> None:
        source = _make_source()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"not json")

        client = httpx.Client(transport=httpx.MockTransport(handler))

        result = fetch_workday_postings(source, client=client)
        assert result.error is not None
        assert "invalid JSON" in result.error

    def test_non_object_json(self) -> None:
        source = _make_source()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=b"[1, 2, 3]")

        client = httpx.Client(transport=httpx.MockTransport(handler))

        result = fetch_workday_postings(source, client=client)
        assert result.error is not None
        assert "invalid JSON" in result.error

    def test_missing_job_postings_key(self) -> None:
        source = _make_source()

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, content=json.dumps({"total": 0}).encode())

        client = httpx.Client(transport=httpx.MockTransport(handler))

        result = fetch_workday_postings(source, client=client)
        assert result.error is not None
        assert "missing jobPostings" in result.error

    def test_timeout(self) -> None:
        source = _make_source()

        def timeout_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ReadTimeout("timed out")

        client = httpx.Client(transport=httpx.MockTransport(timeout_handler))

        result = fetch_workday_postings(source, client=client)
        assert result.error is not None
        assert "timeout" in result.error

    def test_network_error(self) -> None:
        source = _make_source()

        def error_handler(request: httpx.Request) -> httpx.Response:
            raise httpx.ConnectError("connection refused")

        client = httpx.Client(transport=httpx.MockTransport(error_handler))

        result = fetch_workday_postings(source, client=client)
        assert result.error is not None
        assert "network error" in result.error
