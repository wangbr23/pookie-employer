"""Authentication dependencies for protected API routes."""

import hmac
import logging

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pookie_backend.config import Settings, get_settings
from pookie_backend.request_id import get_request_id

logger = logging.getLogger(__name__)
bearer_scheme = HTTPBearer(auto_error=False)


def _authentication_error(code: str, message: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail={"code": code, "message": message},
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_api_secret(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    settings: Settings = Depends(get_settings),
) -> None:
    """Require the configured shared bearer token for a protected route."""
    if credentials is None or credentials.scheme.lower() != "bearer":
        logger.warning(
            "request rejected: missing bearer token, request_id=%s", get_request_id()
        )
        raise _authentication_error("authentication_required", "Authentication required.")

    expected = settings.api_secret.get_secret_value().encode()
    provided = credentials.credentials.encode()
    if not hmac.compare_digest(provided, expected):
        logger.warning(
            "request rejected: invalid bearer token, request_id=%s", get_request_id()
        )
        raise _authentication_error("invalid_credentials", "Invalid credentials.")
