"""Integration tests for the job feedback API."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from pookie_backend.models import (
    FeedbackAction,
    Job,
    JobFeedback,
    JobStatus,
    UserProfile,
)

BASE_TIME = datetime(2026, 9, 1, 12, 0, tzinfo=UTC)


def add_profile(session: Session) -> UserProfile:
    profile = UserProfile(id=uuid4(), owner_user_id=f"owner-{uuid4()}")
    session.add(profile)
    session.flush()
    return profile


def add_job(session: Session, *, status: JobStatus = JobStatus.NEW) -> Job:
    job = Job(
        id=uuid4(),
        canonical_title="Senior Backend Engineer",
        canonical_company="Astral",
        canonical_location="Remote (US)",
        remote_policy="remote",
        salary_unknown=True,
        status=status,
        first_seen_at=BASE_TIME,
        last_seen_at=BASE_TIME,
    )
    session.add(job)
    session.flush()
    return job


def feedback_rows(session: Session) -> list[JobFeedback]:
    return list(session.scalars(select(JobFeedback)).all())


def count_feedback(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(JobFeedback)) or 0


@pytest.mark.parametrize(
    ("path", "body"),
    [
        ("save", None),
        ("dismiss", {"reasons": ["Too junior"]}),
        ("seen", None),
    ],
)
def test_feedback_endpoints_require_authentication(
    api_client: TestClient, path: str, body: dict[str, object] | None
):
    """Every feedback route sits behind the shared-secret boundary."""
    response = api_client.post(f"/api/jobs/{uuid4()}/{path}", json=body)

    assert response.status_code == 401


def test_saving_a_job_updates_status_and_logs_the_action(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """A save moves the job and records who decided it."""
    profile = add_profile(db_session)
    job = add_job(db_session)

    response = api_client.post(
        f"/api/jobs/{job.id}/save",
        json={"reasons": ["Great stack"], "free_text": "Worth a look"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "saved"
    assert job.status == JobStatus.SAVED
    logged = feedback_rows(db_session)
    assert len(logged) == 1
    assert logged[0].action == FeedbackAction.SAVE
    assert logged[0].profile_id == profile.id
    assert logged[0].reasons == ["Great stack"]
    assert logged[0].free_text == "Worth a look"


def test_saving_without_a_body_is_accepted(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Context is optional on a save; the click alone is the signal."""
    add_profile(db_session)
    job = add_job(db_session)

    response = api_client.post(f"/api/jobs/{job.id}/save", headers=auth_headers)

    assert response.status_code == 200
    assert feedback_rows(db_session)[0].reasons == []


def test_dismissing_a_job_records_its_reasons(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """A dismissal carries the structured reason the design's flow collects."""
    add_profile(db_session)
    job = add_job(db_session)

    response = api_client.post(
        f"/api/jobs/{job.id}/dismiss",
        json={"reasons": ["Onsite only", "Below salary floor"]},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "dismissed"
    assert job.status == JobStatus.DISMISSED
    logged = feedback_rows(db_session)
    assert logged[0].action == FeedbackAction.DISMISS
    assert logged[0].reasons == ["Onsite only", "Below salary floor"]


def test_dismissing_without_a_reason_is_rejected(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """A reasonless dismissal teaches later ranking nothing, so it is refused."""
    add_profile(db_session)
    job = add_job(db_session)

    empty = api_client.post(
        f"/api/jobs/{job.id}/dismiss", json={"reasons": []}, headers=auth_headers
    )
    missing = api_client.post(
        f"/api/jobs/{job.id}/dismiss", json={}, headers=auth_headers
    )
    blank = api_client.post(
        f"/api/jobs/{job.id}/dismiss", json={"reasons": ["   "]}, headers=auth_headers
    )

    assert empty.status_code == 422
    assert missing.status_code == 422
    assert blank.status_code == 422
    assert job.status == JobStatus.NEW
    assert count_feedback(db_session) == 0


def test_rejects_more_reasons_or_longer_text_than_allowed(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Bounded input keeps a runaway client from filling the feedback log."""
    add_profile(db_session)
    job = add_job(db_session)

    too_many = api_client.post(
        f"/api/jobs/{job.id}/dismiss",
        json={"reasons": [f"reason {index}" for index in range(11)]},
        headers=auth_headers,
    )
    too_long = api_client.post(
        f"/api/jobs/{job.id}/dismiss",
        json={"reasons": ["Onsite only"], "free_text": "x" * 2001},
        headers=auth_headers,
    )

    assert too_many.status_code == 422
    assert too_long.status_code == 422
    assert count_feedback(db_session) == 0


def test_marking_seen_advances_only_a_new_job(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Seen is the passive signal that a new card was shown."""
    add_profile(db_session)
    job = add_job(db_session)

    response = api_client.post(f"/api/jobs/{job.id}/seen", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["status"] == "seen"
    assert job.status == JobStatus.SEEN
    assert count_feedback(db_session) == 0


@pytest.mark.parametrize(
    "status", [JobStatus.SAVED, JobStatus.DISMISSED, JobStatus.CLOSED_ARCHIVED]
)
def test_marking_seen_never_overwrites_a_decided_job(
    api_client: TestClient,
    db_session: Session,
    auth_headers: dict[str, str],
    status: JobStatus,
):
    """Scrolling past a saved job must not silently unsave it."""
    add_profile(db_session)
    job = add_job(db_session, status=status)

    response = api_client.post(f"/api/jobs/{job.id}/seen", headers=auth_headers)

    assert response.status_code == 200
    assert job.status == status
    assert response.json()["status"] == status.value


def test_repeating_a_save_logs_the_decision_once(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """A double-clicked save is one decision, not two."""
    add_profile(db_session)
    job = add_job(db_session)

    api_client.post(f"/api/jobs/{job.id}/save", headers=auth_headers)
    second = api_client.post(f"/api/jobs/{job.id}/save", headers=auth_headers)

    assert second.status_code == 200
    assert job.status == JobStatus.SAVED
    assert count_feedback(db_session) == 1


def test_a_user_can_change_their_mind_about_a_job(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Save then dismiss is a real sequence, and both decisions are kept."""
    add_profile(db_session)
    job = add_job(db_session)

    api_client.post(f"/api/jobs/{job.id}/save", headers=auth_headers)
    api_client.post(
        f"/api/jobs/{job.id}/dismiss",
        json={"reasons": ["Changed my mind"]},
        headers=auth_headers,
    )

    assert job.status == JobStatus.DISMISSED
    actions = [row.action for row in feedback_rows(db_session)]
    assert actions == [FeedbackAction.SAVE, FeedbackAction.DISMISS]


def test_feedback_on_an_unknown_job_returns_a_structured_404(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """A missing job answers the same way the read API does."""
    add_profile(db_session)

    response = api_client.post(f"/api/jobs/{uuid4()}/save", headers=auth_headers)

    assert response.status_code == 404
    assert response.json()["detail"] == {
        "code": "job_not_found",
        "message": "Job not found.",
    }


def test_a_malformed_job_id_is_rejected_before_the_database(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """An unparseable id is a bad request, not a database error."""
    add_profile(db_session)

    response = api_client.post("/api/jobs/not-a-uuid/save", headers=auth_headers)

    assert response.status_code == 422


def test_feedback_is_refused_when_no_profile_is_configured(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Feedback needs an owner, so an unseeded database fails loudly."""
    job = add_job(db_session)

    response = api_client.post(f"/api/jobs/{job.id}/save", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "profile_not_configured"
    assert job.status == JobStatus.NEW


def test_feedback_is_refused_when_the_profile_is_ambiguous(
    api_client: TestClient, db_session: Session, auth_headers: dict[str, str]
):
    """Two profiles must not be guessed between; the write would be wrong."""
    add_profile(db_session)
    add_profile(db_session)
    job = add_job(db_session)

    response = api_client.post(f"/api/jobs/{job.id}/save", headers=auth_headers)

    assert response.status_code == 409
    assert response.json()["detail"]["code"] == "ambiguous_profile"
    assert count_feedback(db_session) == 0
