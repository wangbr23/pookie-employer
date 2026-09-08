"""Netflix public job board adapter (Eightfold AI careers API).

Fetches postings from ``https://explore.jobs.netflix.net/api/apply/v2/jobs``
with ``domain=netflix.com``.  ``source.external_board_id`` carries the
``domain`` query value and ``source.base_url`` supplies the host.

Each response's ``count`` field reports the board total, but the list
endpoint caps ``num`` at 10 postings per page no matter what is requested,
so large boards need real pagination.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

import httpx

from pookie_backend.ingestion import RawPostingInput
from pookie_backend.models import JobSource

# The API answers at most 10 postings per page regardless of ``num``.
PAGE_SIZE = 10
# Pages answer in ~0.5s, so a ~500-posting board takes ~25s sequential; a
# small parallel pool after page 0 reveals the total keeps the fetch well
# inside the crawl budget.
PAGE_CONCURRENCY = 4
# Hard stop in case a board reports an implausible total or ignores start.
MAX_PAGES = 500
REQUEST_TIMEOUT = 30.0


@dataclass(frozen=True)
class NetflixResult:
    """Result of fetching one Netflix board."""

    postings: list[RawPostingInput]
    error: str | None = None


def fetch_netflix_postings(
    source: JobSource,
    *,
    client: httpx.Client | None = None,
    timeout: float = REQUEST_TIMEOUT,
) -> NetflixResult:
    """Fetch every posting from a Netflix board, following pagination.

    All-or-nothing like the other adapters: a failure on any page fails the
    whole source so a partial board can't pass silently as complete.
    """
    domain = source.external_board_id
    if not domain:
        return NetflixResult(postings=[], error="missing external_board_id")
    host = urlparse(source.base_url).hostname
    if not host:
        return NetflixResult(postings=[], error="invalid base_url")

    if client is not None:
        return _fetch_all_pages(client, source, host, domain, timeout)
    with httpx.Client() as owned:
        return _fetch_all_pages(owned, source, host, domain, timeout)


def _fetch_all_pages(
    client: httpx.Client,
    source: JobSource,
    host: str,
    domain: str,
    timeout: float,
) -> NetflixResult:
    """Walk the list endpoint until the board is drained."""
    url = f"https://{host}/api/apply/v2/jobs"
    seen: set[str] = set()
    postings: list[RawPostingInput] = []

    # Page 0 first: it is the only page whose count is read.
    body, error = _get_page(client, url, domain, 0, timeout)
    if error is not None:
        return NetflixResult(postings=[], error=error)
    entries, error = _positions(body, domain)
    if error is not None:
        return NetflixResult(postings=[], error=error)
    if not entries:
        return NetflixResult(postings=postings)
    postings += _collect(entries, source.company_name, host, seen)
    offset = len(entries)

    total = body.get("count")
    if isinstance(total, int) and 0 < total <= offset:
        return NetflixResult(postings=postings)

    if isinstance(total, int) and total > offset:
        end = ((total + PAGE_SIZE - 1) // PAGE_SIZE) * PAGE_SIZE
        offsets = list(range(offset, end, PAGE_SIZE))
        if len(offsets) + 1 > MAX_PAGES:
            return NetflixResult(
                postings=[], error=f"page cap reached fetching {domain}"
            )
        for page_body, page_error in _fetch_offsets(
            client, url, domain, offsets, timeout
        ):
            if page_error is not None:
                return NetflixResult(postings=[], error=page_error)
            page_entries, error = _positions(page_body, domain)
            if error is not None:
                return NetflixResult(postings=[], error=error)
            postings += _collect(page_entries, source.company_name, host, seen)
        return NetflixResult(postings=postings)

    # No plausible total: drain page by page until one comes back empty.
    for _ in range(MAX_PAGES):
        body, error = _get_page(client, url, domain, offset, timeout)
        if error is not None:
            return NetflixResult(postings=[], error=error)
        entries, error = _positions(body, domain)
        if error is not None:
            return NetflixResult(postings=[], error=error)
        if not entries:
            return NetflixResult(postings=postings)
        postings += _collect(entries, source.company_name, host, seen)
        offset += len(entries)

    return NetflixResult(postings=[], error=f"page cap reached fetching {domain}")


def _positions(
    body: dict[str, Any], domain: str
) -> tuple[list[dict[str, Any]], str | None]:
    """Pull the positions list out of a page body, or an error string."""
    entries = body.get("positions")
    if not isinstance(entries, list):
        return [], f"missing positions from {domain}"
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
    domain: str,
    offsets: list[int],
    timeout: float,
) -> list[tuple[dict[str, Any], str | None]]:
    """Fetch known page offsets with a bounded pool, in offset order."""
    if not offsets:
        return []
    with ThreadPoolExecutor(max_workers=PAGE_CONCURRENCY) as pool:
        futures = [
            pool.submit(_get_page, client, url, domain, offset, timeout)
            for offset in offsets
        ]
        return [future.result() for future in futures]


def _get_page(
    client: httpx.Client,
    url: str,
    domain: str,
    offset: int,
    timeout: float,
) -> tuple[dict[str, Any], str | None]:
    """Fetch one list page, returning its JSON body or an error string."""
    params: dict[str, str | int] = {"domain": domain, "start": offset, "num": PAGE_SIZE}
    try:
        response = client.get(url, params=params, timeout=timeout)
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
    entry: dict[str, Any], company_name: str, host: str
) -> RawPostingInput | None:
    """Convert one Netflix list entry into a RawPostingInput.

    ``job_description`` is empty on most list entries; it is kept when the
    board does supply one. ``location`` falls back to the first entry of
    the ``locations`` list when the scalar field is absent.
    """
    posting_id = entry.get("id")
    title = entry.get("name") or entry.get("posting_name")
    if posting_id is None or not title:
        return None

    canonical = entry.get("canonicalPositionUrl")
    if isinstance(canonical, str) and canonical:
        posting_url = canonical
    else:
        posting_url = f"https://{host}/careers/job/{posting_id}"

    location = entry.get("location")
    if not isinstance(location, str) or not location:
        locations = entry.get("locations")
        if isinstance(locations, list) and locations:
            location = locations[0]

    description = entry.get("job_description")
    return RawPostingInput(
        source_posting_id=str(posting_id),
        source_url=posting_url,
        apply_url=posting_url,
        raw_title=str(title),
        raw_company=company_name,
        raw_location=location if isinstance(location, str) and location else None,
        raw_description=(
            description if isinstance(description, str) and description else None
        ),
    )
