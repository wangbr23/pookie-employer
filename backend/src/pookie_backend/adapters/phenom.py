"""Phenom People careers-site adapter.

Phenom boards (``careers.adobe.com`` and friends) expose no public JSON
listing API — the ``/api/apply/v2/jobs`` path used by some other platforms
answers ``Tenant not identified`` on every Phenom deployment.  Instead each
search-results page embeds its 10 results in the page's own ``phApp.ddo``
bootstrap JSON (``eagerLoadRefineSearch``), and the ``?from=`` query
parameter walks the board 10 postings at a time.

``source.base_url`` supplies the careers host and
``source.external_board_id`` carries the search-results path under it
(e.g. ``us/en/search-results``), since locale prefixes differ per tenant.
"""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from pookie_backend.ingestion import RawPostingInput
from pookie_backend.models import JobSource

# Search pages embed exactly 10 postings per page.
PAGE_SIZE = 10
# Page 0 reveals ``totalHits``, so the remaining offsets can be fetched with
# a small parallel pool — a 650-posting board is 65 requests (~65s sequential).
PAGE_CONCURRENCY = 4
# Hard stop in case a board reports an implausible total or ignores from=.
MAX_PAGES = 500
REQUEST_TIMEOUT = 30.0

_DDO_PREFIX = "phApp.ddo = "


@dataclass(frozen=True)
class PhenomResult:
    """Result of fetching one Phenom board."""

    postings: list[RawPostingInput]
    error: str | None = None


def fetch_phenom_postings(
    source: JobSource,
    *,
    client: httpx.Client | None = None,
    timeout: float = REQUEST_TIMEOUT,
) -> PhenomResult:
    """Fetch every posting from a Phenom board, following pagination.

    All-or-nothing like the other adapters: a failure on any page fails the
    whole source so a partial board can't pass silently as complete.
    """
    board_path = source.external_board_id
    if not board_path:
        return PhenomResult(postings=[], error="missing external_board_id")
    host = urlparse(source.base_url).hostname
    if not host:
        return PhenomResult(postings=[], error="invalid base_url")

    if client is not None:
        return _fetch_all_pages(client, source, host, board_path, timeout)
    with httpx.Client() as owned:
        return _fetch_all_pages(owned, source, host, board_path, timeout)


def _fetch_all_pages(
    client: httpx.Client,
    source: JobSource,
    host: str,
    board_path: str,
    timeout: float,
) -> PhenomResult:
    """Walk the search-results page until the board is drained."""
    url = f"https://{host}/{board_path.lstrip('/')}"
    seen: set[str] = set()
    postings: list[RawPostingInput] = []

    # Page 0 first: it is the only page whose totalHits is read.
    body, error = _get_page(client, url, host, 0, timeout)
    if error is not None:
        return PhenomResult(postings=[], error=error)
    search, error = _search_node(body, host)
    if error is not None:
        return PhenomResult(postings=[], error=error)
    entries, error = _jobs(search, host)
    if error is not None:
        return PhenomResult(postings=[], error=error)
    if not entries:
        return PhenomResult(postings=postings)
    postings += _collect(entries, source.company_name, host, seen)
    offset = len(entries)

    total = search.get("totalHits")
    if isinstance(total, int) and 0 < total <= offset:
        return PhenomResult(postings=postings)

    if isinstance(total, int) and total > offset:
        end = ((total + PAGE_SIZE - 1) // PAGE_SIZE) * PAGE_SIZE
        offsets = list(range(offset, end, PAGE_SIZE))
        if len(offsets) + 1 > MAX_PAGES:
            return PhenomResult(
                postings=[], error=f"page cap reached fetching {host}"
            )
        for page_body, page_error in _fetch_offsets(
            client, url, host, offsets, timeout
        ):
            if page_error is not None:
                return PhenomResult(postings=[], error=page_error)
            page_search, error = _search_node(page_body, host)
            if error is not None:
                return PhenomResult(postings=[], error=error)
            page_entries, error = _jobs(page_search, host)
            if error is not None:
                return PhenomResult(postings=[], error=error)
            postings += _collect(page_entries, source.company_name, host, seen)
        return PhenomResult(postings=postings)

    # No plausible total: drain page by page until one comes back empty.
    for _ in range(MAX_PAGES):
        body, error = _get_page(client, url, host, offset, timeout)
        if error is not None:
            return PhenomResult(postings=[], error=error)
        page_search, error = _search_node(body, host)
        if error is not None:
            return PhenomResult(postings=[], error=error)
        entries, error = _jobs(page_search, host)
        if error is not None:
            return PhenomResult(postings=[], error=error)
        if not entries:
            return PhenomResult(postings=postings)
        postings += _collect(entries, source.company_name, host, seen)
        offset += len(entries)

    return PhenomResult(postings=[], error=f"page cap reached fetching {host}")


def _search_node(
    ddo: dict[str, Any], host: str
) -> tuple[dict[str, Any], str | None]:
    """Pull the eagerLoadRefineSearch node out of a page's ddo, or an error."""
    search = ddo.get("eagerLoadRefineSearch")
    if not isinstance(search, dict):
        return {}, f"missing search data from {host}"
    return search, None


def _jobs(
    search: dict[str, Any], host: str
) -> tuple[list[dict[str, Any]], str | None]:
    """Pull the jobs list out of a search node, or an error string."""
    data = search.get("data")
    entries = data.get("jobs") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return [], f"missing jobs from {host}"
    return [entry for entry in entries if isinstance(entry, dict)], None


def _collect(
    entries: list[dict[str, Any]],
    company_name: str,
    host: str,
    seen: set[str],
) -> list[RawPostingInput]:
    """Parse entries, dropping duplicates the board reported twice.

    Offset pagination over a live board re-sights postings when jobs are
    added or removed mid-fetch, so identical ids can appear on two pages.
    """
    collected = []
    for entry in entries:
        posting = _parse_posting(entry, company_name, host)
        if posting is not None and posting.source_posting_id not in seen:
            seen.add(posting.source_posting_id)
            collected.append(posting)
    return collected


def _fetch_offsets(
    client: httpx.Client,
    url: str,
    host: str,
    offsets: list[int],
    timeout: float,
) -> list[tuple[dict[str, Any], str | None]]:
    """Fetch known page offsets with a bounded pool, in offset order."""
    if not offsets:
        return []
    with ThreadPoolExecutor(max_workers=PAGE_CONCURRENCY) as pool:
        futures = [
            pool.submit(_get_page, client, url, host, offset, timeout)
            for offset in offsets
        ]
        return [future.result() for future in futures]


def _get_page(
    client: httpx.Client,
    url: str,
    host: str,
    offset: int,
    timeout: float,
) -> tuple[dict[str, Any], str | None]:
    """Fetch one search page and return its embedded ddo JSON or an error."""
    try:
        response = client.get(url, params={"from": offset}, timeout=timeout)
        response.raise_for_status()
    except httpx.TimeoutException:
        return {}, f"timeout fetching {url} at offset {offset}"
    except httpx.HTTPStatusError as exc:
        return {}, f"HTTP {exc.response.status_code} from {url} at offset {offset}"
    except httpx.HTTPError as exc:
        return {}, f"network error fetching {url} at offset {offset}: {exc}"

    ddo, error = _extract_ddo(response.text, host)
    if error is not None:
        return {}, f"{error} at offset {offset}"
    return ddo, None


def _extract_ddo(html: str, host: str) -> tuple[dict[str, Any], str | None]:
    """Pull the ``phApp.ddo = {...}`` bootstrap JSON out of a page."""
    start = html.find(_DDO_PREFIX)
    if start < 0:
        return {}, f"missing embedded search data from {host}"
    start += len(_DDO_PREFIX)

    # The assignment ends where the opening brace closes; string-aware scan
    # so braces inside job titles or descriptions can't end it early.
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(html)):
        char = html[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
        elif char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                try:
                    data = json.loads(html[start : index + 1])
                except ValueError:
                    return {}, f"invalid embedded JSON from {host}"
                if not isinstance(data, dict):
                    return {}, f"invalid embedded JSON from {host}"
                return data, None
    return {}, f"unterminated embedded search data from {host}"


def _parse_posting(
    entry: dict[str, Any], company_name: str, host: str
) -> RawPostingInput | None:
    """Convert one embedded search entry into a RawPostingInput.

    ``descriptionTeaser`` is a short blurb rather than the full job
    description, but it is the only description Phenom search pages
    supply. ``location`` falls back to the first ``multi_location`` entry
    when the scalar field is absent. Entries without an apply link are
    dropped — preserving a working apply link is the minimum requirement.
    """
    posting_id = entry.get("jobSeqNo") or entry.get("reqId")
    title = entry.get("title")
    apply_url = entry.get("applyUrl")
    if not posting_id or not title:
        return None
    if not isinstance(apply_url, str) or not apply_url:
        return None

    location = entry.get("location")
    if not isinstance(location, str) or not location:
        locations = entry.get("multi_location")
        if isinstance(locations, list) and locations:
            location = locations[0]
    if not isinstance(location, str) or not location:
        location = entry.get("cityStateCountry")

    description = entry.get("descriptionTeaser")
    return RawPostingInput(
        source_posting_id=str(posting_id),
        source_url=apply_url,
        apply_url=apply_url,
        raw_title=str(title),
        raw_company=company_name,
        raw_location=location if isinstance(location, str) and location else None,
        raw_description=(
            description if isinstance(description, str) and description else None
        ),
    )
