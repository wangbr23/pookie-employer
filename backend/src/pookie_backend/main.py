"""FastAPI application entrypoint."""

from fastapi import FastAPI

from pookie_backend.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    description="Backend API and job-processing pipeline for Pookie Employer.",
    version="0.1.0",
)


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"service": "pookie-employer-backend", "version": app.version}


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}
