"""Lever public job board adapter.

Fetches postings from the Lever public postings API for allowlisted boards.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from pookie_backend.ingestion import RawPostingInput
from pookie_backend.models import JobSource

API_BASE = "https://api.lever.co/v0/postings"
REQUEST_TIMEOUT = 30.0


@dataclass(frozen=True)
class LeverResult:
    """Result of fetching one Lever board."""

    postings: list[RawPostingInput]
    error: str | None = None


def fetch_lever_postings(
    source: JobSource,
    *,
    client: httpx.Client | None = None,
    timeout: float = REQUEST_TIMEOUT,
) -> LeverResult:
    """Fetch all job postings from a Lever public board.

    Uses the board token stored in ``source.external_board_id`` to call the
    Lever postings API.  Returns parsed ``RawPostingInput`` items on success,
    or an error description on failure.
    """
    board_token = source.external_board_id
    if not board_token:
        return LeverResult(postings=[], error="missing external_board_id")

    url = f"{API_BASE}/{board_token}"

    try:
        if client is not None:
            response = client.get(url, timeout=timeout)
        else:
            response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
    except httpx.TimeoutException:
        return LeverResult(
            postings=[], error=f"timeout fetching {board_token}"
        )
    except httpx.HTTPStatusError as exc:
        return LeverResult(
            postings=[],
            error=f"HTTP {exc.response.status_code} from {board_token}",
        )
    except httpx.HTTPError as exc:
        return LeverResult(
            postings=[], error=f"network error fetching {board_token}: {exc}"
        )

    try:
        data = response.json()
    except ValueError:
        return LeverResult(
            postings=[], error=f"invalid JSON from {board_token}"
        )

    if not isinstance(data, list):
        return LeverResult(
            postings=[], error=f"unexpected response shape from {board_token}"
        )

    postings = [
        posting
        for job in data
        if (posting := _parse_job(job, source)) is not None
    ]
    return LeverResult(postings=postings)


def _parse_job(job: dict[str, Any], source: JobSource) -> RawPostingInput | None:
    """Convert a Lever API posting object into a RawPostingInput."""
    job_id = job.get("id")
    title = job.get("text")
    if not job_id or not title:
        return None

    hosted_url = job.get("hostedUrl") or ""
    apply_url = job.get("applyUrl") or hosted_url
    categories = job.get("categories") or {}
    location = categories.get("location")
    description = job.get("descriptionPlain") or job.get("description")

    return RawPostingInput(
        source_posting_id=str(job_id),
        source_url=hosted_url,
        apply_url=apply_url,
        raw_title=title,
        raw_company=source.company_name,
        raw_location=location,
        raw_description=description,
    )
