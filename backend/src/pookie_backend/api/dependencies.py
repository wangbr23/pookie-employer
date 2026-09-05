"""Shared request dependencies for the protected API."""

from typing import Annotated

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from pookie_backend.database import get_db_session
from pookie_backend.models import UserProfile


def get_active_profile(
    session: Annotated[Session, Depends(get_db_session)],
) -> UserProfile:
    """Resolve the profile that owns feedback and evaluations.

    The MVP's auth is one shared secret with no user identity attached, so the
    active profile is simply the configured one. Two profiles are refused
    rather than guessed between: writing a save or a dismissal onto the wrong
    profile silently is worse than failing loudly, and this is the point where
    real per-user resolution belongs once auth carries an identity.
    """
    profiles = session.scalars(
        select(UserProfile).order_by(UserProfile.created_at).limit(2)
    ).all()
    if not profiles:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "profile_not_configured",
                "message": "No profile is configured. Run the seed command first.",
            },
        )
    if len(profiles) > 1:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "ambiguous_profile",
                "message": "More than one profile exists; the MVP supports exactly one.",
            },
        )
    return profiles[0]
