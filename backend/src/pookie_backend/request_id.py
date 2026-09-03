"""Request ID context used by middleware and request-scoped logs."""

import re
from contextvars import ContextVar

request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)

# Client-supplied request IDs are echoed into response headers and log lines,
# so they're constrained to a safe charset/length to avoid header or log
# injection (e.g. embedded CRLF/control characters) from untrusted input.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


def get_request_id() -> str | None:
    """Return the request ID for the current request, when one is active."""
    return request_id_context.get()


def sanitize_client_request_id(value: str | None) -> str | None:
    """Return `value` if it's a safe request ID, otherwise None."""
    if value and _SAFE_REQUEST_ID.match(value):
        return value
    return None
