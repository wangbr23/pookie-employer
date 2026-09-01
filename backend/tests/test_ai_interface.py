"""Tests for consent-gated AI provider calls."""

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from pookie_backend.ai import AIConsentRequiredError, AIService
from pookie_backend.ai.interface import AIJobEvaluationRequest, AIJobEvaluationResult
from pookie_backend.models import UserProfile


class FakeProvider:
    provider_name = "test-provider"
    model_name = "test-model-v1"

    def evaluate_job(self, request: AIJobEvaluationRequest) -> AIJobEvaluationResult:
        return AIJobEvaluationResult(
            fit_bucket="possible",
            summary="Looks promising",
            concerns=(),
            matched_skills=("python",),
        )


def make_request() -> AIJobEvaluationRequest:
    return AIJobEvaluationRequest(uuid4(), uuid4(), 1, "job-hash")


def test_ai_call_is_blocked_without_consent():
    profile = UserProfile(id=uuid4(), owner_user_id="owner")
    service = AIService(FakeProvider(), Session())

    with pytest.raises(AIConsentRequiredError):
        service.evaluate_job(profile, make_request())


def test_consented_provider_call_proceeds_and_records_metadata():
    profile = UserProfile(
        id=uuid4(),
        owner_user_id="owner",
        ai_consent_given=True,
        ai_consent_provider="test-provider",
        ai_consent_model_family="test-model",
    )
    session = Session()
    service = AIService(FakeProvider(), session)

    result = service.evaluate_job(profile, make_request())

    assert result.fit_bucket == "possible"
    call = next(iter(session.new))
    assert call.provider == "test-provider"
    assert call.model_name == "test-model-v1"
