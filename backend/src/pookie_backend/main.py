"""FastAPI application entrypoint."""

from fastapi import FastAPI

app = FastAPI(
    title="Pookie Employer Backend",
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
