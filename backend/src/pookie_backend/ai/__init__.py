"""Typed AI service boundary and consent enforcement."""

from pookie_backend.ai.interface import (
    AIConsentConfigurationError,
    AIConsentRequiredError,
    AIJobEvaluationRequest,
    AIJobEvaluationResult,
    AIJobSnapshot,
    AIProfileSnapshot,
    AIProvider,
    AIProviderNotAllowedError,
    AIService,
    NotImplementedAIProvider,
)

__all__ = [
    "AIConsentConfigurationError",
    "AIConsentRequiredError",
    "AIJobEvaluationRequest",
    "AIJobEvaluationResult",
    "AIJobSnapshot",
    "AIProfileSnapshot",
    "AIProvider",
    "AIProviderNotAllowedError",
    "AIService",
    "NotImplementedAIProvider",
]
