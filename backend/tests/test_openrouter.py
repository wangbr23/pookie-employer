"""Tests for the OpenRouter provider — all HTTP calls are mocked."""

from __future__ import annotations

import json
from decimal import Decimal
from uuid import uuid4

import httpx
import pytest

from pookie_backend.ai.interface import (
    AIJobEvaluationRequest,
    AIJobSnapshot,
    AIProfileSnapshot,
)
from pookie_backend.ai.openrouter import OpenRouterProvider, _parse_response


def _make_request() -> AIJobEvaluationRequest:
    return AIJobEvaluationRequest(
        profile_id=uuid4(),
        job_id=uuid4(),
        profile_version=1,
        job_content_hash="abc123",
        job=AIJobSnapshot(
            title="Backend Engineer",
            company="Acme Corp",
            location="San Francisco, CA",
            remote_policy="remote",
            salary_unknown=False,
        ),
        profile=AIProfileSnapshot(
            target_role_families=("backend engineering",),
            preferred_tech=("Python", "PostgreSQL"),
            avoided_tech=("blockchain",),
            dealbreakers=("must be remote-friendly or hybrid",),
            remote_preference="remote_or_hybrid",
            salary_floor=Decimal("150000"),
        ),
    )


def _success_body(
    fit_bucket: str = "strong",
    summary: str = "Great fit for backend role.",
    concerns: list[str] | None = None,
    matched_skills: list[str] | None = None,
    input_tokens: int = 150,
    output_tokens: int = 80,
) -> dict:
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "fit_bucket": fit_bucket,
                            "summary": summary,
                            "concerns": concerns or [],
                            "matched_skills": matched_skills or ["Python"],
                        }
                    )
                }
            }
        ],
        "usage": {
            "prompt_tokens": input_tokens,
            "completion_tokens": output_tokens,
        },
    }


def _mock_transport(body: dict, status_code: int = 200) -> httpx.MockTransport:
    content = json.dumps(body).encode()

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, content=content)

    return httpx.MockTransport(handler)


def _provider_with_transport(transport: httpx.MockTransport) -> OpenRouterProvider:
    provider = OpenRouterProvider(api_key="test-key", model="z-ai/glm-5.3-flash")
    provider._client = httpx.Client(transport=transport)
    return provider


class TestOpenRouterProvider:
    def test_successful_evaluation(self) -> None:
        body = _success_body(matched_skills=["Python", "PostgreSQL"])
        provider = _provider_with_transport(_mock_transport(body))

        result = provider.evaluate_job(_make_request())

        assert result.fit_bucket == "strong"
        assert result.summary == "Great fit for backend role."
        assert result.matched_skills == ("Python", "PostgreSQL")
        assert result.concerns == ()

    def test_records_token_usage(self) -> None:
        body = _success_body(input_tokens=200, output_tokens=100)
        provider = _provider_with_transport(_mock_transport(body))

        provider.evaluate_job(_make_request())

        assert provider.last_usage is not None
        assert provider.last_usage.input_tokens == 200
        assert provider.last_usage.output_tokens == 100

    def test_concerns_are_captured(self) -> None:
        body = _success_body(
            fit_bucket="possible",
            concerns=["Salary is not published", "Remote policy is unclear"],
        )
        provider = _provider_with_transport(_mock_transport(body))

        result = provider.evaluate_job(_make_request())

        assert result.fit_bucket == "possible"
        assert len(result.concerns) == 2

    def test_invalid_bucket_falls_back_to_needs_review(self) -> None:
        body = _success_body(fit_bucket="excellent")
        provider = _provider_with_transport(_mock_transport(body))

        result = provider.evaluate_job(_make_request())

        assert result.fit_bucket == "needs_review"

    def test_http_error_propagates(self) -> None:
        provider = _provider_with_transport(
            _mock_transport({"error": "unauthorized"}, status_code=401)
        )

        with pytest.raises(httpx.HTTPStatusError):
            provider.evaluate_job(_make_request())

    def test_provider_identity(self) -> None:
        provider = OpenRouterProvider(api_key="k", model="z-ai/glm-5.3-flash")
        assert provider.provider_name == "openrouter"
        assert provider.model_name == "z-ai/glm-5.3-flash"

    def test_sends_correct_headers(self) -> None:
        captured_request: httpx.Request | None = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_request
            captured_request = request
            body = _success_body()
            return httpx.Response(200, content=json.dumps(body).encode())

        provider = _provider_with_transport(httpx.MockTransport(handler))
        provider.evaluate_job(_make_request())

        assert captured_request is not None
        assert captured_request.headers["authorization"] == "Bearer test-key"

    def test_sends_correct_model_in_payload(self) -> None:
        captured_body: dict | None = None

        def handler(request: httpx.Request) -> httpx.Response:
            nonlocal captured_body
            captured_body = json.loads(request.content)
            body = _success_body()
            return httpx.Response(200, content=json.dumps(body).encode())

        provider = _provider_with_transport(httpx.MockTransport(handler))
        provider.evaluate_job(_make_request())

        assert captured_body is not None
        assert captured_body["model"] == "z-ai/glm-5.3-flash"
        assert captured_body["temperature"] == 0.0

    def test_cost_from_usage(self) -> None:
        body = _success_body()
        body["usage"]["cost"] = 0.000123
        provider = _provider_with_transport(_mock_transport(body))

        provider.evaluate_job(_make_request())

        assert provider.last_usage is not None
        assert provider.last_usage.estimated_cost == Decimal("0.000123")


class TestParseResponse:
    def test_plain_json(self) -> None:
        result = _parse_response('{"fit_bucket": "strong"}')
        assert result["fit_bucket"] == "strong"

    def test_markdown_fenced_json(self) -> None:
        result = _parse_response('```json\n{"fit_bucket": "possible"}\n```')
        assert result["fit_bucket"] == "possible"

    def test_invalid_json_raises(self) -> None:
        with pytest.raises(json.JSONDecodeError):
            _parse_response("not json at all")
