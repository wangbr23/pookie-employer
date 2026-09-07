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
    "create_provider",
]


def create_provider() -> AIProvider:
    """Build an AI provider from the current application settings.

    Returns the OpenRouter provider when an API key is configured, otherwise
    falls back to the deterministic mock.
    """
    from pookie_backend.config import get_settings

    settings = get_settings()
    if settings.open_router_api_key is not None:
        from pookie_backend.ai.openrouter import OpenRouterProvider

        return OpenRouterProvider(
            api_key=settings.open_router_api_key.get_secret_value(),
            model=settings.ai_model,
        )

    from pookie_backend.ai.mock import MockAIProvider

    return MockAIProvider()
