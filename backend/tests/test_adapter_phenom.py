"""Tests for the Phenom source adapter."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

import httpx

from pookie_backend.adapters.phenom import (
    MAX_PAGES,
    PAGE_SIZE,
    _parse_posting,
    fetch_phenom_postings,
)
from pookie_backend.models import ApprovalStatus, JobSource, SourceKind

FIXTURES = Path(__file__).parent / "fixtures"
PHENOM_HOST = "careers.adobe.com"
PHENOM_BOARD = "us/en/search-results"


def _make_source(
    board: str = PHENOM_BOARD,
    host: str = PHENOM_HOST,
    company: str = "Adobe",
) -> JobSource:
    """Build an in-memory JobSource without touching the database."""
    return JobSource(
        id=uuid4(),
        kind=SourceKind.PHENOM,
        name=f"{company} Careers",
        company_name=company,
        base_url=f"https://{host}",
        external_board_id=board,
        approval_status=ApprovalStatus.APPROVED,
    )


def _fixture_ddo() -> dict[str, Any]:
    """Parse the phApp.ddo JSON out of the saved Adobe search page."""
    html = (FIXTURES / "phenom_adobe.html").read_text()
    start = html.find("phApp.ddo = ") + len("phApp.ddo = ")
    end = html.rfind("};")
    return json.loads(html[start : end + 1])


def _fixture_jobs() -> list[dict[str, Any]]:
    return _fixture_ddo()["eagerLoadRefineSearch"]["data"]["jobs"]


def _make_job(seq: int = 1, **overrides: Any) -> dict[str, Any]:
    job: dict[str, Any] = {
        "jobSeqNo": f"ADOBUSR{seq:06d}EXTERNALENUS",
        "reqId": f"R{seq:06d}",
        "title": f"Software Engineer {seq}",
        "applyUrl": f"https://adobe.wd5.myworkdayjobs.com/external_experienced/job/San-Jose/Software-Engineer_R{seq:06d}/apply",
        "location": "San Jose, California, United States",
        "multi_location": ["San Jose, California, United States"],
        "descriptionTeaser": f"Build great software as engineer {seq}.",
        "postedDate": "2026-09-01T00:00:00.000+0000",
    }
    job.update(overrides)
    return job


def _page_html(jobs: list[dict[str, Any]], total: int | None = 650) -> str:
    search: dict[str, Any] = {
        "status": 200,
        "hits": len(jobs),
        "data": {"keywords": "", "jobs": jobs},
    }
    if total is not None:
        search["totalHits"] = total
    ddo = {"eagerLoadRefineSearch": search}
    return (
        "<!doctype html><html><body><script>"
        f"phApp.ddo = {json.dumps(ddo)};"
        "</script></body></html>"
    )


def _page_transport(
    pages: dict[int, list[dict[str, Any]]],
    total: int | None = 650,
    status_code: int = 200,
    html_override: str | None = None,
    requests: list[httpx.Request] | None = None,
) -> httpx.MockTransport:
    """Serve search pages keyed by the request's ``from`` value."""

    def handler(request: httpx.Request) -> httpx.Response:
        if requests is not None:
            requests.append(request)
        if status_code != 200:
            return httpx.Response(status_code, content=b"")
        if html_override is not None:
            return httpx.Response(200, text=html_override)
        offset = int(request.url.params["from"])
        jobs = pages.get(offset, [])
        return httpx.Response(200, text=_page_html(jobs, total))

    return httpx.MockTransport(handler)


class TestParsePosting:
    def test_parses_complete_posting(self) -> None:
        source = _make_source()
        entry = _fixture_jobs()[0]

        posting = _parse_posting(entry, source.company_name, PHENOM_HOST)

        assert posting is not None
        assert posting.source_posting_id == "ADOBUSR171000EXTERNALENUS"
        assert posting.raw_title == "Content Business Architect"
        assert posting.raw_company == "Adobe"
        assert posting.raw_location == "Tokyo, Tokyo, Japan"
        assert posting.raw_description == (
            "Take on the role of Content Business Architect to drive "
            "transformation in content operations for enterprise clients."
        )
        assert posting.apply_url == (
            "https://adobe.wd5.myworkdayjobs.com/external_experienced/job/"
            "Tokyo/Content-Business-Architect_R171000/apply"
        )
        assert posting.source_url == posting.apply_url

    def test_falls_back_to_req_id_when_seq_missing(self) -> None:
        posting = _parse_posting(_make_job(), "Adobe", PHENOM_HOST)
        assert posting is not None
        assert posting.source_posting_id == "ADOBUSR000001EXTERNALENUS"

        entry = _make_job()
        del entry["jobSeqNo"]
        posting = _parse_posting(entry, "Adobe", PHENOM_HOST)

        assert posting is not None
        assert posting.source_posting_id == "R000001"

    def test_falls_back_to_first_multi_location(self) -> None:
        entry = _make_job(
            multi_location=["New York, New York, United States"],
        )
        del entry["location"]

        posting = _parse_posting(entry, "Adobe", PHENOM_HOST)

        assert posting is not None
        assert posting.raw_location == "New York, New York, United States"

    def test_missing_title_returns_none(self) -> None:
        entry = _make_job()
        del entry["title"]

        assert _parse_posting(entry, "Adobe", PHENOM_HOST) is None

    def test_missing_id_returns_none(self) -> None:
        entry = _make_job()
        del entry["jobSeqNo"]
        del entry["reqId"]

        assert _parse_posting(entry, "Adobe", PHENOM_HOST) is None

    def test_missing_apply_url_returns_none(self) -> None:
        entry = _make_job()
        del entry["applyUrl"]

        assert _parse_posting(entry, "Adobe", PHENOM_HOST) is None


class TestFetchPostings:
    def test_fetches_all_pages_when_total_known(self) -> None:
        source = _make_source()
        pages = {
            0: [_make_job(i) for i in range(1, PAGE_SIZE + 1)],
            PAGE_SIZE: [_make_job(i) for i in range(PAGE_SIZE + 1, PAGE_SIZE * 2 + 1)],
            PAGE_SIZE * 2: [_make_job(i) for i in range(PAGE_SIZE * 2 + 1, 26)],
        }
        requests: list[httpx.Request] = []

        with httpx.Client(
            transport=_page_transport(pages, total=25, requests=requests)
        ) as client:
            result = fetch_phenom_postings(source, client=client)

        assert result.error is None
        assert [p.source_posting_id for p in result.postings] == [
            f"ADOBUSR{i:06d}EXTERNALENUS" for i in range(1, 26)
        ]
        assert [r.url.params["from"] for r in requests] == ["0", "10", "20"]
        assert {r.url.host for r in requests} == {PHENOM_HOST}
        assert all(
            r.url.path == f"/{PHENOM_BOARD}" for r in requests
        )

    def test_drains_pages_when_total_unknown(self) -> None:
        source = _make_source()
        pages = {
            0: [_make_job(i) for i in range(1, 11)],
            10: [_make_job(i) for i in range(11, 21)],
            20: [_make_job(i) for i in range(21, 31)],
            30: [],
        }

        with httpx.Client(
            transport=_page_transport(pages, total=None)
        ) as client:
            result = fetch_phenom_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 30

    def test_stops_early_when_total_matches_first_page(self) -> None:
        source = _make_source()
        pages = {0: [_make_job(i) for i in range(1, 4)]}

        with httpx.Client(
            transport=_page_transport(pages, total=3)
        ) as client:
            result = fetch_phenom_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 3

    def test_empty_board_returns_no_postings(self) -> None:
        source = _make_source()

        with httpx.Client(transport=_page_transport({}, total=0)) as client:
            result = fetch_phenom_postings(source, client=client)

        assert result.error is None
        assert result.postings == []

    def test_drops_duplicates_across_pages(self) -> None:
        source = _make_source()
        dupe = _make_job(1)
        pages = {
            0: [_make_job(i) for i in range(1, 11)],
            10: [_make_job(i) for i in range(11, 16)] + [dupe],
        }

        with httpx.Client(
            transport=_page_transport(pages, total=15)
        ) as client:
            result = fetch_phenom_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 15

    def test_http_error_fails_whole_source(self) -> None:
        source = _make_source()
        pages = {0: [_make_job(i) for i in range(1, 11)]}

        with httpx.Client(
            transport=_page_transport(pages, status_code=503)
        ) as client:
            result = fetch_phenom_postings(source, client=client)

        assert result.postings == []
        assert result.error is not None
        assert "503" in result.error

    def test_page_without_embedded_data_fails_source(self) -> None:
        source = _make_source()
        pages = {0: [_make_job(i) for i in range(1, 11)]}

        with httpx.Client(
            transport=_page_transport(
                pages, html_override="<html><body>blocked</body></html>"
            )
        ) as client:
            result = fetch_phenom_postings(source, client=client)

        assert result.postings == []
        assert result.error is not None
        assert "missing embedded search data" in result.error

    def test_unterminated_ddo_json_fails_source(self) -> None:
        source = _make_source()
        pages = {0: [_make_job(i) for i in range(1, 11)]}

        with httpx.Client(
            transport=_page_transport(
                pages,
                html_override="<html><script>phApp.ddo = {\"broken</script></html>",
            )
        ) as client:
            result = fetch_phenom_postings(source, client=client)

        assert result.postings == []
        assert result.error is not None

    def test_braces_inside_titles_do_not_break_extraction(self) -> None:
        source = _make_source()
        jobs = [
            _make_job(1, title='Engineer {"weird": true} C++'),
            _make_job(2, descriptionTeaser='Uses {"lang": "rust"} daily'),
        ]

        with httpx.Client(
            transport=_page_transport({0: jobs}, total=2)
        ) as client:
            result = fetch_phenom_postings(source, client=client)

        assert result.error is None
        assert len(result.postings) == 2

    def test_page_cap_reached_on_implausible_total(self) -> None:
        source = _make_source()
        pages = {0: [_make_job(i) for i in range(1, 11)]}

        with httpx.Client(
            transport=_page_transport(
                pages, total=PAGE_SIZE * (MAX_PAGES + 5)
            )
        ) as client:
            result = fetch_phenom_postings(source, client=client)

        assert result.postings == []
        assert result.error is not None
        assert "page cap" in result.error


class TestSourceValidation:
    def test_missing_board_id_fails(self) -> None:
        source = _make_source(board="")

        result = fetch_phenom_postings(source)

        assert result.postings == []
        assert result.error == "missing external_board_id"

    def test_invalid_base_url_fails(self) -> None:
        source = _make_source(host="")

        result = fetch_phenom_postings(source)

        assert result.postings == []
        assert result.error == "invalid base_url"
