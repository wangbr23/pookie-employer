"""FastAPI application entrypoint."""

import logging
from collections.abc import Awaitable, Callable
from uuid import uuid4

from fastapi import APIRouter, Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, Response

from pookie_backend.api import coverage, jobs
from pookie_backend.config import get_settings
from pookie_backend.request_id import request_id_context, sanitize_client_request_id
from pookie_backend.security import require_api_secret

settings = get_settings()
logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.app_name,
    description="Backend API and job-processing pipeline for Pookie Employer.",
    version="0.1.0",
)


@app.middleware("http")
async def add_request_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Propagate or generate a request ID and include it in request logs."""
    request_id = sanitize_client_request_id(request.headers.get("X-Request-ID")) or str(
        uuid4()
    )
    request.state.request_id = request_id
    token = request_id_context.set(request_id)
    try:
        response = await call_next(request)
    except Exception:
        logger.exception(
            "request failed: method=%s path=%s request_id=%s",
            request.method,
            request.url.path,
            request_id,
        )
        response = JSONResponse(
            status_code=500,
            content={
                "detail": {
                    "code": "internal_server_error",
                    "message": "An internal server error occurred.",
                }
            },
        )

    try:
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed: method=%s path=%s status=%s request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            request_id,
        )
        return response
    finally:
        request_id_context.reset(token)


# Registered after add_request_id so CORS ends up as the outermost middleware
# (Starlette's add_middleware prepends, so the last one added wraps the rest).
# That way CORS headers are applied to every response leaving the app,
# including the request-id middleware's manually built 500 fallback, which
# would otherwise bypass CORSMiddleware's ASGI send-wrapping entirely.
# Tradeoff: CORSMiddleware answers preflight (OPTIONS) requests directly
# without calling into add_request_id, so preflight responses don't get an
# X-Request-ID header or a request-completed log line. Accepted: preflight
# requests carry no app state to trace, and CORS headers on every real
# response (including error fallbacks) matters more.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"service": "pookie-employer-backend", "version": app.version}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


# All routes mounted on this router require the shared API secret by default.
# Add new protected endpoints here rather than on `app` directly, so protection
# is structural instead of something each route has to remember to declare.
protected_router = APIRouter(prefix="/api", dependencies=[Depends(require_api_secret)])


@protected_router.get("/protected")
async def protected() -> dict[str, str]:
    """Minimal protected route proving the API authorization boundary."""
    return {"status": "authorized"}


protected_router.include_router(jobs.router)
protected_router.include_router(coverage.router)

app.include_router(protected_router)
