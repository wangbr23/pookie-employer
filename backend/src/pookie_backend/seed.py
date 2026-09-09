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
    "seniority_max": 5,
    "remote_preference": "remote_or_hybrid",
    "allowed_locations": ["New York, NY"],
    "work_authorization_constraints": ["authorized to work in the United States"],
    "salary_floor": Decimal("170000.00"),
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
    "ai_consent_given": True,
    "ai_consent_provider": "openrouter",
    "ai_consent_model_family": "z-ai/glm",
}


class SeedSource(TypedDict):
    """Static definition for a seeded job source."""

    kind: SourceKind
    name: str
    company_name: str
    base_url: str
    external_board_id: str


SEED_SOURCES: Sequence[SeedSource] = (
    # --- Greenhouse boards (verified reachable 2026-09-08) ---
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Airbnb Careers",
        "company_name": "Airbnb",
        "base_url": "https://boards.greenhouse.io/airbnb",
        "external_board_id": "airbnb",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Stripe Careers",
        "company_name": "Stripe",
        "base_url": "https://boards.greenhouse.io/stripe",
        "external_board_id": "stripe",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Coinbase Careers",
        "company_name": "Coinbase",
        "base_url": "https://boards.greenhouse.io/coinbase",
        "external_board_id": "coinbase",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Roblox Careers",
        "company_name": "Roblox",
        "base_url": "https://boards.greenhouse.io/roblox",
        "external_board_id": "roblox",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Discord Careers",
        "company_name": "Discord",
        "base_url": "https://boards.greenhouse.io/discord",
        "external_board_id": "discord",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Lyft Careers",
        "company_name": "Lyft",
        "base_url": "https://boards.greenhouse.io/lyft",
        "external_board_id": "lyft",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Asana Careers",
        "company_name": "Asana",
        "base_url": "https://boards.greenhouse.io/asana",
        "external_board_id": "asana",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Datadog Careers",
        "company_name": "Datadog",
        "base_url": "https://boards.greenhouse.io/datadog",
        "external_board_id": "datadog",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "LinkedIn Careers",
        "company_name": "LinkedIn",
        "base_url": "https://boards.greenhouse.io/linkedin",
        "external_board_id": "linkedin",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Dropbox Careers",
        "company_name": "Dropbox",
        "base_url": "https://boards.greenhouse.io/dropbox",
        "external_board_id": "dropbox",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Twilio Careers",
        "company_name": "Twilio",
        "base_url": "https://boards.greenhouse.io/twilio",
        "external_board_id": "twilio",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "DoorDash Careers",
        "company_name": "DoorDash",
        "base_url": "https://boards.greenhouse.io/doordashusa",
        "external_board_id": "doordashusa",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Databricks Careers",
        "company_name": "Databricks",
        "base_url": "https://boards.greenhouse.io/databricks",
        "external_board_id": "databricks",
    },
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "MongoDB Careers",
        "company_name": "MongoDB",
        "base_url": "https://boards.greenhouse.io/mongodb",
        "external_board_id": "mongodb",
    },
    # --- Ashby boards (verified reachable 2026-09-08) ---
    {
        "kind": SourceKind.ASHBY,
        "name": "Snowflake Careers",
        "company_name": "Snowflake",
        "base_url": "https://jobs.ashbyhq.com/snowflake",
        "external_board_id": "snowflake",
    },
    {
        "kind": SourceKind.ASHBY,
        "name": "Notion Careers",
        "company_name": "Notion",
        "base_url": "https://jobs.ashbyhq.com/notion",
        "external_board_id": "notion",
    },
    # --- Workday boards (verified reachable 2026-09-08) ---
    {
        "kind": SourceKind.WORKDAY,
        "name": "NVIDIA Careers",
        "company_name": "NVIDIA",
        "base_url": "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        "external_board_id": "nvidia/NVIDIAExternalCareerSite",
    },
    {
        "kind": SourceKind.WORKDAY,
        "name": "Salesforce Careers",
        "company_name": "Salesforce",
        "base_url": "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site",
        "external_board_id": "salesforce/External_Career_Site",
    },
    # --- Netflix (verified reachable 2026-09-08) ---
    {
        "kind": SourceKind.NETFLIX,
        "name": "Netflix Jobs",
        "company_name": "Netflix",
        "base_url": "https://explore.jobs.netflix.net",
        "external_board_id": "netflix.com",
    },
    # --- Smaller companies (original test sources) ---
    {
        "kind": SourceKind.GREENHOUSE,
        "name": "Airtable Careers",
        "company_name": "Airtable",
        "base_url": "https://boards.greenhouse.io/airtable",
        "external_board_id": "airtable",
    },
    {
        "kind": SourceKind.ASHBY,
        "name": "Linear Careers",
        "company_name": "Linear",
        "base_url": "https://jobs.ashbyhq.com/linear",
        "external_board_id": "linear",
    },
    {
        "kind": SourceKind.ASHBY,
        "name": "Ramp Careers",
        "company_name": "Ramp",
        "base_url": "https://jobs.ashbyhq.com/ramp",
        "external_board_id": "ramp",
    },
    {
        "kind": SourceKind.ASHBY,
        "name": "Resend Careers",
        "company_name": "Resend",
        "base_url": "https://jobs.ashbyhq.com/resend",
        "external_board_id": "resend",
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
