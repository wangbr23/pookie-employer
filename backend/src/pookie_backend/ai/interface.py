"""Provider-independent AI interface with profile consent enforcement."""

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from sqlalchemy.orm import Session

from pookie_backend.models import AiCallLog, AiCallStatus, UserProfile


class AIConsentRequiredError(PermissionError):
    """Raised when a profile has not explicitly allowed third-party AI."""


class AIConsentConfigurationError(PermissionError):
    """Raised when consent is enabled without its provider/model restrictions."""


class AIProviderNotAllowedError(PermissionError):
    """Raised when a provider or model is outside the consented allowance."""


@dataclass(frozen=True)
class AIJobEvaluationRequest:
    """Stable identifiers and version data sent to an evaluation provider."""

    profile_id: UUID
    job_id: UUID
    profile_version: int
    job_content_hash: str


@dataclass(frozen=True)
class AIJobEvaluationResult:
    """Structured evaluation data returned by a provider."""

    fit_bucket: str
    summary: str | None
    concerns: tuple[str, ...]
    matched_skills: tuple[str, ...]
    internal_score: Decimal | None = None


class AIProvider(Protocol):
    """The narrow contract implemented by each concrete provider adapter."""

    @property
    def provider_name(self) -> str: ...

    @property
    def model_name(self) -> str: ...

    def evaluate_job(
        self, request: AIJobEvaluationRequest
    ) -> AIJobEvaluationResult: ...


class NotImplementedAIProvider:
    """Placeholder until a provider is selected and integrated."""

    provider_name = "unconfigured"
    model_name = "unconfigured"

    def evaluate_job(
        self, request: AIJobEvaluationRequest
    ) -> AIJobEvaluationResult:
        raise NotImplementedError("No AI provider has been configured")


class AIService:
    """Consent-gated entry point for provider-backed AI operations."""

    def __init__(self, provider: AIProvider, session: Session) -> None:
        self.provider = provider
        self.session = session

    def evaluate_job(
        self, profile: UserProfile, request: AIJobEvaluationRequest
    ) -> AIJobEvaluationResult:
        """Evaluate a job only when the requested provider/model is consented."""
        self._check_consent(profile)
        call = AiCallLog(
            profile_id=profile.id,
            provider=self.provider.provider_name,
            model_name=self.provider.model_name,
            operation="evaluate_job",
            status=AiCallStatus.ATTEMPTED,
            created_at=datetime.now(UTC),
        )
        self.session.add(call)
        try:
            result = self.provider.evaluate_job(request)
        except Exception:
            call.status = AiCallStatus.FAILED
            raise
        call.status = AiCallStatus.SUCCEEDED
        return result

    def _check_consent(self, profile: UserProfile) -> None:
        if not profile.ai_consent_given:
            raise AIConsentRequiredError("Third-party AI consent is required")
        if not profile.ai_consent_provider or not profile.ai_consent_model_family:
            raise AIConsentConfigurationError(
                "Consent must include an allowed provider and model family"
            )
        if profile.ai_consent_provider != self.provider.provider_name:
            raise AIProviderNotAllowedError("Provider is not allowed by profile consent")
        if not self.provider.model_name.startswith(profile.ai_consent_model_family):
            raise AIProviderNotAllowedError("Model is not allowed by profile consent")
