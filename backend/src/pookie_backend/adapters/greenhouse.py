"""Greenhouse public job board adapter.

Fetches postings from the Greenhouse public JSON API for allowlisted boards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from pookie_backend.ingestion import RawPostingInput
from pookie_backend.models import JobSource

API_BASE = "https://boards-api.greenhouse.io/v1/boards"
REQUEST_TIMEOUT = 30.0


@dataclass(frozen=True)
class GreenhouseResult:
    """Result of fetching one Greenhouse board."""

    postings: list[RawPostingInput]
    error: str | None = None


def fetch_greenhouse_postings(
    source: JobSource,
    *,
    client: httpx.Client | None = None,
    timeout: float = REQUEST_TIMEOUT,
) -> GreenhouseResult:
    """Fetch all job postings from a Greenhouse public board.

    Uses the board token stored in ``source.external_board_id`` to call the
    Greenhouse boards API.  Returns parsed ``RawPostingInput`` items on success,
    or an error description on failure.
    """
    board_token = source.external_board_id
    if not board_token:
        return GreenhouseResult(postings=[], error="missing external_board_id")

    url = f"{API_BASE}/{board_token}/jobs"
    params = {"content": "true"}

    try:
        if client is not None:
            response = client.get(url, params=params, timeout=timeout)
        else:
            response = httpx.get(url, params=params, timeout=timeout)
        response.raise_for_status()
    except httpx.TimeoutException:
        return GreenhouseResult(
            postings=[], error=f"timeout fetching {board_token}"
        )
    except httpx.HTTPStatusError as exc:
        return GreenhouseResult(
            postings=[],
            error=f"HTTP {exc.response.status_code} from {board_token}",
        )
    except httpx.HTTPError as exc:
        return GreenhouseResult(
            postings=[], error=f"network error fetching {board_token}: {exc}"
        )

    try:
        data = response.json()
    except ValueError:
        return GreenhouseResult(
            postings=[], error=f"invalid JSON from {board_token}"
        )

    jobs = data.get("jobs", [])
    postings = [
        posting
        for job in jobs
        if (posting := _parse_job(job, source)) is not None
    ]
    return GreenhouseResult(postings=postings)


def _parse_job(job: dict[str, Any], source: JobSource) -> RawPostingInput | None:
    """Convert a Greenhouse API job object into a RawPostingInput."""
    job_id = job.get("id")
    title = job.get("title")
    if not job_id or not title:
        return None

    absolute_url = job.get("absolute_url") or ""
    location_name = (job.get("location") or {}).get("name")
    content = job.get("content")

    return RawPostingInput(
        source_posting_id=str(job_id),
        source_url=absolute_url,
        apply_url=absolute_url,
        raw_title=title,
        raw_company=source.company_name,
        raw_location=location_name,
        raw_description=content,
    )
