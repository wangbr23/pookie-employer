"""OpenRouter-backed evaluation provider.

Calls the OpenAI-compatible chat completions endpoint at
https://openrouter.ai/api/v1/chat/completions and parses a structured JSON
response into the standard AIJobEvaluationResult.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx

from pookie_backend.ai.interface import (
    AIJobEvaluationRequest,
    AIJobEvaluationResult,
    AIJobSnapshot,
    AIProfileSnapshot,
)

logger = logging.getLogger(__name__)

_COMPLETIONS_URL = "https://openrouter.ai/api/v1/chat/completions"
_TIMEOUT_SECONDS = 30

_VALID_FIT_BUCKETS = frozenset({"strong", "possible", "stretch", "needs_review"})

_SYSTEM_PROMPT = """\
You are a job-fit evaluator. Given a job posting summary and a candidate profile, \
return a JSON object with exactly these fields:

- "fit_bucket": one of "strong", "possible", "stretch", "needs_review"
- "summary": a one-sentence explanation of the fit (or null)
- "concerns": an array of short concern strings (empty array if none)
- "matched_skills": an array of skills from the profile that match the job

Return ONLY valid JSON, no markdown fences or extra text."""


def _build_user_message(job: AIJobSnapshot, profile: AIProfileSnapshot) -> str:
    parts = [
        f"Job: {job.title} at {job.company}",
        f"Location: {job.location or 'Not specified'}",
        f"Remote policy: {job.remote_policy or 'Unclear'}",
        f"Salary published: {'No' if job.salary_unknown else 'Yes'}",
        "",
        f"Target roles: {', '.join(profile.target_role_families) or 'Any'}",
        f"Preferred tech: {', '.join(profile.preferred_tech) or 'None listed'}",
        f"Avoided tech: {', '.join(profile.avoided_tech) or 'None listed'}",
        f"Dealbreakers: {', '.join(profile.dealbreakers) or 'None listed'}",
        f"Remote preference: {profile.remote_preference or 'Any'}",
        f"Salary floor: {profile.salary_floor or 'Not set'}",
    ]
    return "\n".join(parts)


def _parse_response(text: str) -> dict[str, Any]:
    """Extract JSON from the model response, stripping markdown fences."""
    cleaned = text.strip()
    if cleaned.startswith("```"):
        first_newline = cleaned.index("\n")
        cleaned = cleaned[first_newline + 1 :]
        if cleaned.endswith("```"):
            cleaned = cleaned[: -len("```")]
        cleaned = cleaned.strip()
    result: dict[str, Any] = json.loads(cleaned)
    return result


def _as_str_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if item)


@dataclass(frozen=True)
class ProviderUsage:
    """Token counts and cost from one provider call."""

    input_tokens: int | None = None
    output_tokens: int | None = None
    estimated_cost: Decimal | None = None


class OpenRouterProvider:
    """AIProvider backed by OpenRouter's chat completions API."""

    def __init__(self, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model
        self._client = httpx.Client(timeout=_TIMEOUT_SECONDS)
        self.last_usage: ProviderUsage | None = None

    @property
    def provider_name(self) -> str:
        return "openrouter"

    @property
    def model_name(self) -> str:
        return self._model

    def evaluate_job(
        self, request: AIJobEvaluationRequest
    ) -> AIJobEvaluationResult:
        self.last_usage = None
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": _build_user_message(request.job, request.profile),
                },
            ],
            "temperature": 0.0,
            # Reasoning models (e.g. z-ai glm) spend completion tokens on
            # internal reasoning before the JSON answer; a tight cap makes
            # them return `content: null`.
            "max_tokens": 2048,
        }
        response = self._client.post(
            _COMPLETIONS_URL,
            json=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )
        response.raise_for_status()
        body = response.json()

        self.last_usage = _extract_usage(body)

        content = body["choices"][0]["message"]["content"]
        if not content or not content.strip():
            raise ValueError(
                "Provider returned empty content; the model likely spent its "
                "entire token budget on reasoning without answering"
            )
        parsed = _parse_response(content)

        fit_bucket = parsed.get("fit_bucket", "needs_review")
        if fit_bucket not in _VALID_FIT_BUCKETS:
            logger.warning("Provider returned invalid fit_bucket %r, falling back", fit_bucket)
            fit_bucket = "needs_review"

        return AIJobEvaluationResult(
            fit_bucket=fit_bucket,
            summary=parsed.get("summary"),
            concerns=_as_str_tuple(parsed.get("concerns", [])),
            matched_skills=_as_str_tuple(parsed.get("matched_skills", [])),
        )


def _extract_usage(body: dict[str, Any]) -> ProviderUsage:
    usage = body.get("usage", {})
    input_tokens = usage.get("prompt_tokens")
    output_tokens = usage.get("completion_tokens")
    # OpenRouter reports spend as usage.cost (dollars), not total_cost.
    cost = usage.get("cost")
    if cost is None:
        cost = body.get("cost")
    return ProviderUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        estimated_cost=Decimal(str(cost)) if cost is not None else None,
    )
