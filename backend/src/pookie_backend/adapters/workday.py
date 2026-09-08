"""Workday CXS public job board adapter.

Fetches postings from Workday's candidate experience service (CXS) jobs API.
``source.external_board_id`` must be ``{tenant}/{site}`` (e.g.
``nvidia/NVIDIAExternalCareerSite``) and ``source.base_url`` supplies the
board host, so the list endpoint is
``https://{host}/wday/cxs/{tenant}/{site}/jobs``.

The list response carries no description, so postings are stored without one;
normalization flags those for review and the AI snapshot never reads
descriptions. Fetching per-job details would add one request per posting and
blow the refresh budget on large boards.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from pookie_backend.ingestion import RawPostingInput
from pookie_backend.models import JobSource

# Workday CXS list pages cap at 20 postings regardless of the requested limit.
PAGE_SIZE = 20
# Boards answer ~1s per page, so a large board's pages are fetched in a small
# parallel pool after page 0 reveals how many there are; sequential paging of
# a 2000-posting board takes ~100s and blows the crawl budget.
PAGE_CONCURRENCY = 4
# Hard stop in case a board reports an implausible total or ignores offset.
MAX_PAGES = 500
REQUEST_TIMEOUT = 30.0


@dataclass(frozen=True)
class WorkdayResult:
    """Result of fetching one Workday board."""

    postings: list[RawPostingInput]
    error: str | None = None


def fetch_workday_postings(
    source: JobSource,
    *,
    client: httpx.Client | None = None,
    timeout: float = REQUEST_TIMEOUT,
) -> WorkdayResult:
    """Fetch every posting from a Workday board, following pagination.

    All-or-nothing like the other adapters: a failure on any page fails the
    whole source so a partial board can't pass silently as complete.
    """
    coordinates = _board_coordinates(source)
    if isinstance(coordinates, str):
        return WorkdayResult(postings=[], error=coordinates)
    host, tenant, site = coordinates

    if client is not None:
        return _fetch_all_pages(client, source, host, tenant, site, timeout)
    with httpx.Client() as owned:
        return _fetch_all_pages(owned, source, host, tenant, site, timeout)


def _board_coordinates(source: JobSource) -> tuple[str, str, str] | str:
    """Resolve ``(host, tenant, site)`` for a source, or an error string."""
    board_id = source.external_board_id or ""
    tenant, slash, site = board_id.partition("/")
    if not slash or not tenant or not site:
        return "external_board_id must be 'tenant/site'"
    host = urlparse(source.base_url).hostname
    if not host:
        return "invalid base_url"
    return host, tenant, site


def _fetch_all_pages(
    client: httpx.Client,
    source: JobSource,
    host: str,
    tenant: str,
    site: str,
    timeout: float,
) -> WorkdayResult:
    """Walk the list endpoint until the board is drained."""
    url = f"https://{host}/wday/cxs/{tenant}/{site}/jobs"
    prefix = f"https://{host}/{site}"
    seen: set[str] = set()
    postings: list[RawPostingInput] = []

    # Page 0 first: it is the only page whose total is reliable, and the
    # remaining offsets all follow from that count.
    body, error = _post_page(client, url, 0, timeout)
    if error is not None:
        return WorkdayResult(postings=[], error=error)
    entries, error = _entries(body, site)
    if error is not None:
        return WorkdayResult(postings=[], error=error)
    if not entries:
        return WorkdayResult(postings=postings)
    postings += _collect(entries, source.company_name, prefix, seen)
    offset = len(entries)

    total = body.get("total")
    if isinstance(total, int) and 0 < total <= offset:
        return WorkdayResult(postings=postings)

    if isinstance(total, int) and total > offset:
        end = ((total + PAGE_SIZE - 1) // PAGE_SIZE) * PAGE_SIZE
        offsets = list(range(offset, end, PAGE_SIZE))
        if len(offsets) + 1 > MAX_PAGES:
            return WorkdayResult(postings=[], error=f"page cap reached fetching {site}")
        for page_body, page_error in _fetch_offsets(client, url, offsets, timeout):
            if page_error is not None:
                return WorkdayResult(postings=[], error=page_error)
            page_entries, error = _entries(page_body, site)
            if error is not None:
                return WorkdayResult(postings=[], error=error)
            postings += _collect(page_entries, source.company_name, prefix, seen)
        return WorkdayResult(postings=postings)

    # No plausible total: drain page by page until one comes back empty.
    for _ in range(MAX_PAGES):
        body, error = _post_page(client, url, offset, timeout)
        if error is not None:
            return WorkdayResult(postings=[], error=error)
        entries, error = _entries(body, site)
        if error is not None:
            return WorkdayResult(postings=[], error=error)
        if not entries:
            return WorkdayResult(postings=postings)
        postings += _collect(entries, source.company_name, prefix, seen)
        offset += len(entries)

    return WorkdayResult(postings=[], error=f"page cap reached fetching {site}")


def _entries(
    body: dict[str, Any], site: str
) -> tuple[list[dict[str, Any]], str | None]:
    """Pull the jobPostings list out of a page body, or an error string."""
    entries = body.get("jobPostings")
    if not isinstance(entries, list):
        return [], f"missing jobPostings from {site}"
    return [entry for entry in entries if isinstance(entry, dict)], None


def _collect(
    entries: list[dict[str, Any]],
    company_name: str,
    posting_url_prefix: str,
    seen: set[str],
) -> list[RawPostingInput]:
    """Parse entries, dropping duplicates the board reported twice.

    Offset pagination over a live board re-sights postings when jobs are
    added or removed mid-fetch, so identical ids can appear on two pages.
    """
    collected = []
    for entry in entries:
        posting = _parse_posting(entry, company_name, posting_url_prefix)
        if posting is not None and posting.source_posting_id not in seen:
            seen.add(posting.source_posting_id)
            collected.append(posting)
    return collected


def _fetch_offsets(
    client: httpx.Client,
    url: str,
    offsets: list[int],
    timeout: float,
) -> list[tuple[dict[str, Any], str | None]]:
    """Fetch known page offsets with a bounded pool, in offset order."""
    if not offsets:
        return []
    with ThreadPoolExecutor(max_workers=PAGE_CONCURRENCY) as pool:
        futures = [
            pool.submit(_post_page, client, url, offset, timeout) for offset in offsets
        ]
        return [future.result() for future in futures]


def _post_page(
    client: httpx.Client,
    url: str,
    offset: int,
    timeout: float,
) -> tuple[dict[str, Any], str | None]:
    """Fetch one list page, returning its JSON body or an error string."""
    payload = {"appliedFacets": {}, "limit": PAGE_SIZE, "offset": offset}
    try:
        response = client.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
    except httpx.TimeoutException:
        return {}, f"timeout fetching {url} at offset {offset}"
    except httpx.HTTPStatusError as exc:
        return {}, f"HTTP {exc.response.status_code} from {url} at offset {offset}"
    except httpx.HTTPError as exc:
        return {}, f"network error fetching {url} at offset {offset}: {exc}"

    try:
        data = response.json()
    except ValueError:
        return {}, f"invalid JSON from {url} at offset {offset}"
    if not isinstance(data, dict):
        return {}, f"invalid JSON from {url} at offset {offset}"
    return data, None


def _parse_posting(
    entry: dict[str, Any], company_name: str, posting_url_prefix: str
) -> RawPostingInput | None:
    """Convert one Workday list entry into a RawPostingInput.

    ``locationsText`` can be a real place ("US, TX, Austin") or just a count
    ("2 Locations"); it is kept as-is either way — dropping the posting would
    hide jobs that normalization or the eligibility filter can still triage.
    """
    title = entry.get("title")
    external_path = entry.get("externalPath")
    if not title or not external_path:
        return None

    posting_url = f"{posting_url_prefix}{external_path}"
    return RawPostingInput(
        source_posting_id=str(external_path),
        source_url=posting_url,
        apply_url=posting_url,
        raw_title=str(title),
        raw_company=company_name,
        raw_location=entry.get("locationsText"),
    )
