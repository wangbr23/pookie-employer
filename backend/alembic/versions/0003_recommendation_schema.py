"""Create canonical jobs, recommendation evaluations, and feedback tables."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0003_recommendation_schema"
down_revision: str | None = "0002_core_ingestion_schema"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create the recommendation and feedback schema."""
    job_status = sa.Enum(
        "new",
        "seen",
        "saved",
        "dismissed",
        "possibly_closed",
        "closed_archived",
        name="jobstatus",
    )
    fit_bucket = sa.Enum(
        "strong", "possible", "stretch", "needs_review", name="fitbucket"
    )
    job_link_status = sa.Enum(
        "active", "broken", "possibly_closed", "closed", name="joblinkstatus"
    )
    salary_uncertainty = sa.Enum(
        "known", "unknown", "estimated", "conflicting", name="salaryuncertainty"
    )
    remote_uncertainty = sa.Enum(
        "clear", "unclear", "conflicting", name="remoteuncertainty"
    )
    work_auth_uncertainty = sa.Enum(
        "clear", "unclear", "conflicting", name="workauthuncertainty"
    )
    feedback_action = sa.Enum(
        "save",
        "dismiss",
        "more_like_this",
        "less_like_this",
        "ai_wrong",
        name="feedbackaction",
    )

    op.create_table(
        "jobs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("canonical_title", sa.String(length=512), nullable=False),
        sa.Column("canonical_company", sa.String(length=255), nullable=False),
        sa.Column("canonical_location", sa.String(length=512)),
        sa.Column("remote_policy", sa.String(length=32)),
        sa.Column("employment_type", sa.String(length=64)),
        sa.Column("salary_min", sa.Numeric(precision=12, scale=2)),
        sa.Column("salary_max", sa.Numeric(precision=12, scale=2)),
        sa.Column("salary_currency", sa.String(length=3)),
        sa.Column(
            "salary_unknown", sa.Boolean(), nullable=False, server_default=sa.true()
        ),
        sa.Column("seniority", sa.String(length=64)),
        sa.Column("status", job_status, nullable=False, server_default="new"),
        sa.Column("fit_bucket", fit_bucket),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_jobs_status_fit_bucket", "jobs", ["status", "fit_bucket"])
    op.create_index("ix_jobs_last_seen_at", "jobs", ["last_seen_at"])

    op.create_table(
        "job_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("raw_job_posting_id", postgresql.UUID(as_uuid=True)),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("apply_url", sa.String(length=2048)),
        sa.Column(
            "is_primary", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("last_checked_at", sa.DateTime(timezone=True)),
        sa.Column("status", job_link_status, nullable=False, server_default="active"),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["raw_job_posting_id"], ["raw_job_postings.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "job_id", "raw_job_posting_id", name="uq_job_links_job_raw"
        ),
    )
    op.create_index("ix_job_links_job_status", "job_links", ["job_id", "status"])

    evaluation_fit_bucket = sa.Enum(
        "strong",
        "possible",
        "stretch",
        "needs_review",
        name="fitbucket",
        create_type=False,
    )
    op.create_table(
        "job_evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("job_content_hash", sa.String(length=128), nullable=False),
        sa.Column("fit_bucket", evaluation_fit_bucket, nullable=False),
        sa.Column("internal_score", sa.Numeric(precision=8, scale=3)),
        sa.Column(
            "matched_skills",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "matched_preferences",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "concerns",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "uncertainties",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("summary", sa.Text()),
        sa.Column(
            "verify_before_applying",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("salary_uncertainty", salary_uncertainty, nullable=False),
        sa.Column("remote_uncertainty", remote_uncertainty, nullable=False),
        sa.Column("work_auth_uncertainty", work_auth_uncertainty, nullable=False),
        sa.Column("model_provider", sa.String(length=128), nullable=False),
        sa.Column("model_name", sa.String(length=128), nullable=False),
        sa.Column(
            "evaluated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["user_profiles.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "job_id",
            "profile_id",
            "job_content_hash",
            name="uq_job_evaluations_job_profile_content",
        ),
    )
    op.create_index(
        "ix_job_evaluations_profile_fit",
        "job_evaluations",
        ["profile_id", "fit_bucket"],
    )

    op.create_table(
        "job_feedback",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", feedback_action, nullable=False),
        sa.Column(
            "reasons",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("free_text", sa.Text()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["job_id"], ["jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["user_profiles.id"], ondelete="CASCADE"
        ),
    )
    op.create_index(
        "ix_job_feedback_profile_created", "job_feedback", ["profile_id", "created_at"]
    )


def downgrade() -> None:
    """Drop the recommendation and feedback schema."""
    op.drop_index("ix_job_feedback_profile_created", table_name="job_feedback")
    op.drop_table("job_feedback")
    op.drop_index("ix_job_evaluations_profile_fit", table_name="job_evaluations")
    op.drop_table("job_evaluations")
    op.drop_index("ix_job_links_job_status", table_name="job_links")
    op.drop_table("job_links")
    op.drop_index("ix_jobs_last_seen_at", table_name="jobs")
    op.drop_index("ix_jobs_status_fit_bucket", table_name="jobs")
    op.drop_table("jobs")

    bind = op.get_bind()
    for enum_name in (
        "feedbackaction",
        "workauthuncertainty",
        "remoteuncertainty",
        "salaryuncertainty",
        "joblinkstatus",
        "fitbucket",
        "jobstatus",
    ):
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
