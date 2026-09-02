"""Seed the backend database with an initial profile and approved sources."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from pookie_backend.database import SessionLocal
from pookie_backend.models import (
    ApprovalStatus,
    JobSource,
    SourceKind,
    SourceStatus,
    UserProfile,
)

SEED_OWNER_USER_ID = "admin-configured-profile"

SEED_PROFILE_VALUES = {
    "owner_user_id": SEED_OWNER_USER_ID,
    "target_role_families": ["backend engineering", "platform engineering"],
    "seniority_min": 2,
    "seniority_max": 6,
    "remote_preference": "remote_or_hybrid",
    "allowed_locations": ["United States", "New York, NY", "San Francisco, CA"],
    "work_authorization_constraints": ["authorized to work in the United States"],
    "salary_floor": Decimal("180000.00"),
    "preferred_tech": [
        "Python",
        "TypeScript",
        "FastAPI",
        "Next.js",
        "PostgreSQL",
        "AWS",
    ],
    "avoided_tech": ["heavy on-call rotations", "greenfield blockchain"],
    "preferred_industries": ["developer tools", "infrastructure", "B2B SaaS"],
    "avoided_industries": ["adtech", "gambling"],
    "company_stage_preferences": ["seed", "series a", "series b", "series c"],
    "dealbreakers": [
        "must be remote-friendly or hybrid",
        "no unreasonable on-call expectations",
    ],
    "notes": (
        "Seeded admin profile for an experienced software engineer focused on backend "
        "and platform roles. Placeholder values should be confirmed before any user-facing use."
    ),
    "profile_version": 1,
}


class SeedSource(TypedDict):
    """Static definition for a seeded job source."""

    kind: SourceKind
    name: str
    company_name: str
    base_url: str
    external_board_id: str


SEED_SOURCES: Sequence[SeedSource] = (
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Astral Jobs",
        "company_name": "Astral",
        "base_url": "https://boards.greenhouse.io/astral",
        "external_board_id": "astral",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Ramp Careers",
        "company_name": "Ramp",
        "base_url": "https://boards.greenhouse.io/ramp",
        "external_board_id": "ramp",
    },
    {
        "kind": SourceKind.LEVER,
        "name": "Linear Careers",
        "company_name": "Linear",
        "base_url": "https://jobs.lever.co/linear",
        "external_board_id": "linear",
    },
    {
        "kind": SourceKind.LEVER,
        "name": "Vanta Careers",
        "company_name": "Vanta",
        "base_url": "https://jobs.lever.co/vanta",
        "external_board_id": "vanta",
    },
    {
        "kind": SourceKind.ASHBY,
        "name": "Fathom Careers",
        "company_name": "Fathom",
        "base_url": "https://jobs.ashbyhq.com/fathom",
        "external_board_id": "fathom",
    },
)


def seed_database(session: Session) -> tuple[UserProfile, list[JobSource]]:
    """Seed one profile and the initial approved source list."""
    profile = _get_or_create_profile(session)
    sources = [_get_or_create_source(session, source_data) for source_data in SEED_SOURCES]
    session.commit()
    return profile, sources


def main() -> None:
    """Run the database seed using the configured session factory."""
    with SessionLocal() as session:
        profile, sources = seed_database(session)
        print(
            f"Seeded profile {profile.owner_user_id!r} and {len(sources)} "
            "approved sources."
        )


def _get_or_create[ModelT](
    session: Session, stmt: Select[tuple[ModelT]], factory: Callable[[], ModelT]
) -> ModelT:
    """Return the row matching `stmt`, or create, add, and return a new one."""
    existing = session.scalar(stmt)
    if existing is not None:
        return existing

    created = factory()
    session.add(created)
    return created


def _get_or_create_profile(session: Session) -> UserProfile:
    return _get_or_create(
        session,
        select(UserProfile).where(UserProfile.owner_user_id == SEED_OWNER_USER_ID),
        lambda: UserProfile(**SEED_PROFILE_VALUES),
    )


def _get_or_create_source(session: Session, source_data: SeedSource) -> JobSource:
    kind = source_data["kind"]
    company_name = source_data["company_name"]
    external_board_id = source_data["external_board_id"]

    return _get_or_create(
        session,
        select(JobSource).where(
            JobSource.kind == kind,
            JobSource.company_name == company_name,
            JobSource.external_board_id == external_board_id,
        ),
        lambda: JobSource(
            kind=kind,
            name=source_data["name"],
            company_name=company_name,
            base_url=source_data["base_url"],
            external_board_id=external_board_id,
            status=SourceStatus.ACTIVE,
            approval_status=ApprovalStatus.APPROVED,
        ),
    )


if __name__ == "__main__":
    main()
