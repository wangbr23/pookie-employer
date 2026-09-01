"""Database connection setup."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from pookie_backend.config import get_settings


class Base(DeclarativeBase):
    """Base class for SQLAlchemy models."""


def create_db_engine(database_url: str) -> Engine:
    """Create a SQLAlchemy engine for the configured database URL."""
    return create_engine(database_url, pool_pre_ping=True)


settings = get_settings()
engine = create_db_engine(settings.database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db_session() -> Generator[Session, None, None]:
    """Yield a database session for FastAPI dependencies."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def redact_database_url(database_url: str) -> str:
    """Return a database URL string with password hidden for safe diagnostics."""
    url: URL = make_url(database_url)
    return url.render_as_string(hide_password=True)
