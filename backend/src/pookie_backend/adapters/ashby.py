"""Ashby public job board adapter.

Fetches postings from the Ashby posting API for allowlisted boards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from pookie_backend.ingestion import RawPostingInput
from pookie_backend.models import JobSource

API_BASE = "https://api.ashbyhq.com/posting-api/job-board"
REQUEST_TIMEOUT = 30.0


@dataclass(frozen=True)
class AshbyResult:
    """Result of fetching one Ashby board."""

    postings: list[RawPostingInput]
    error: str | None = None


def fetch_ashby_postings(
    source: JobSource,
    *,
    client: httpx.Client | None = None,
    timeout: float = REQUEST_TIMEOUT,
) -> AshbyResult:
    """Fetch all job postings from an Ashby public board.

    Uses the board token stored in ``source.external_board_id`` to call the
    Ashby posting API.  Returns parsed ``RawPostingInput`` items on success,
    or an error description on failure.
    """
    board_token = source.external_board_id
    if not board_token:
        return AshbyResult(postings=[], error="missing external_board_id")

    url = f"{API_BASE}/{board_token}"

    try:
        if client is not None:
            response = client.get(url, timeout=timeout)
        else:
            response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
    except httpx.TimeoutException:
        return AshbyResult(
            postings=[], error=f"timeout fetching {board_token}"
        )
    except httpx.HTTPStatusError as exc:
        return AshbyResult(
            postings=[],
            error=f"HTTP {exc.response.status_code} from {board_token}",
        )
    except httpx.HTTPError as exc:
        return AshbyResult(
            postings=[], error=f"network error fetching {board_token}: {exc}"
        )

    try:
        data = response.json()
    except ValueError:
        return AshbyResult(
            postings=[], error=f"invalid JSON from {board_token}"
        )

    jobs = data.get("jobs", [])
    postings = [
        posting
        for job in jobs
        if (posting := _parse_job(job, source)) is not None
    ]
    return AshbyResult(postings=postings)


def _parse_job(job: dict[str, Any], source: JobSource) -> RawPostingInput | None:
    """Convert an Ashby API job object into a RawPostingInput."""
    job_id = job.get("id")
    title = job.get("title")
    if not job_id or not title:
        return None

    job_url = job.get("jobUrl") or ""
    apply_url = job.get("applyUrl") or job_url
    location = job.get("location")
    description = job.get("descriptionHtml")

    return RawPostingInput(
        source_posting_id=str(job_id),
        source_url=job_url,
        apply_url=apply_url,
        raw_title=title,
        raw_company=source.company_name,
        raw_location=location,
        raw_description=description,
    )
