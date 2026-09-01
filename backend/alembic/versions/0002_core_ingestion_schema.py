"""Create profile, source, and raw-ingestion tables."""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0002_core_ingestion_schema"
down_revision: str | None = "0001_bootstrap"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create the core ingestion schema."""
    source_kind = sa.Enum(
        "greenhouse",
        "lever",
        "ashby",
        "company_page",
        name="sourcekind",
    )
    source_status = sa.Enum("active", "paused", "needs_review", name="sourcestatus")
    approval_status = sa.Enum(
        "approved", "suggested", "rejected", name="approvalstatus"
    )
    crawl_trigger = sa.Enum(
        "on_demand",
        "manual_script",
        "scheduled",
        name="crawltrigger",
    )
    crawl_status = sa.Enum(
        "running",
        "partial_success",
        "success",
        "failed",
        name="crawlstatus",
    )
    source_run_status = sa.Enum(
        "running",
        "success",
        "failed",
        "skipped",
        name="sourcerunstatus",
    )

    op.create_table(
        "user_profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("owner_user_id", sa.String(length=255), nullable=False),
        sa.Column(
            "target_role_families",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("seniority_min", sa.Integer()),
        sa.Column("seniority_max", sa.Integer()),
        sa.Column("remote_preference", sa.String(length=32)),
        sa.Column(
            "allowed_locations",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "work_authorization_constraints",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("salary_floor", sa.Numeric(precision=12, scale=2)),
        sa.Column(
            "preferred_tech",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "avoided_tech",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "preferred_industries",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "avoided_industries",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "company_stage_preferences",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column(
            "dealbreakers",
            postgresql.ARRAY(sa.String()),
            nullable=False,
            server_default="{}",
        ),
        sa.Column("notes", sa.Text()),
        sa.Column("profile_version", sa.Integer(), nullable=False, server_default="1"),
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
        sa.UniqueConstraint("owner_user_id", name="uq_user_profiles_owner_user_id"),
    )
    op.create_index(
        "ix_user_profiles_owner_user_id", "user_profiles", ["owner_user_id"]
    )

    op.create_table(
        "job_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("kind", source_kind, nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("company_name", sa.String(length=255), nullable=False),
        sa.Column("base_url", sa.String(length=2048), nullable=False),
        sa.Column("external_board_id", sa.String(length=255)),
        sa.Column("status", source_status, nullable=False, server_default="active"),
        sa.Column(
            "approval_status",
            approval_status,
            nullable=False,
            server_default="suggested",
        ),
        sa.Column("last_successful_crawl_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_at", sa.DateTime(timezone=True)),
        sa.Column("last_error_summary", sa.Text()),
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
    )
    op.create_index(
        "ix_job_sources_status_approval", "job_sources", ["status", "approval_status"]
    )

    op.create_table(
        "crawl_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("trigger", crawl_trigger, nullable=False),
        sa.Column("status", crawl_status, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column(
            "sources_attempted", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "sources_succeeded", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("sources_failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_new", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "evaluations_completed", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column(
            "evaluations_pending", sa.Integer(), nullable=False, server_default="0"
        ),
        sa.Column("elapsed_milliseconds", sa.Integer()),
        sa.Column("ai_call_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("estimated_ai_cost", sa.Numeric(precision=12, scale=6)),
    )
    op.create_index(
        "ix_crawl_runs_status_started_at", "crawl_runs", ["status", "started_at"]
    )

    op.create_table(
        "source_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("crawl_run_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("job_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", source_run_status, nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("jobs_discovered", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_inserted", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_updated", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("jobs_skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_summary", sa.Text()),
        sa.ForeignKeyConstraint(
            ["crawl_run_id"], ["crawl_runs.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["job_source_id"], ["job_sources.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(
        "ix_source_runs_crawl_run_status", "source_runs", ["crawl_run_id", "status"]
    )

    op.create_table(
        "raw_job_postings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("job_source_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("source_posting_id", sa.String(length=512), nullable=False),
        sa.Column("source_url", sa.String(length=2048), nullable=False),
        sa.Column("apply_url", sa.String(length=2048)),
        sa.Column("raw_title", sa.String(length=512), nullable=False),
        sa.Column("raw_company", sa.String(length=255)),
        sa.Column("raw_location", sa.String(length=512)),
        sa.Column("raw_description", sa.Text()),
        sa.Column("content_hash", sa.String(length=128), nullable=False),
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
        sa.Column("closed_detected_at", sa.DateTime(timezone=True)),
        sa.ForeignKeyConstraint(
            ["job_source_id"], ["job_sources.id"], ondelete="RESTRICT"
        ),
        sa.UniqueConstraint(
            "job_source_id", "source_posting_id", name="uq_raw_postings_source_identity"
        ),
    )
    op.create_index(
        "ix_raw_job_postings_source_content_hash",
        "raw_job_postings",
        ["job_source_id", "content_hash"],
    )
    op.create_index(
        "ix_raw_job_postings_last_seen_at", "raw_job_postings", ["last_seen_at"]
    )


def downgrade() -> None:
    """Drop the core ingestion schema."""
    op.drop_index("ix_raw_job_postings_last_seen_at", table_name="raw_job_postings")
    op.drop_index(
        "ix_raw_job_postings_source_content_hash", table_name="raw_job_postings"
    )
    op.drop_table("raw_job_postings")
    op.drop_index("ix_source_runs_crawl_run_status", table_name="source_runs")
    op.drop_table("source_runs")
    op.drop_index("ix_crawl_runs_status_started_at", table_name="crawl_runs")
    op.drop_table("crawl_runs")
    op.drop_index("ix_job_sources_status_approval", table_name="job_sources")
    op.drop_table("job_sources")
    op.drop_index("ix_user_profiles_owner_user_id", table_name="user_profiles")
    op.drop_table("user_profiles")

    bind = op.get_bind()
    for enum_name in (
        "sourcerunstatus",
        "crawlstatus",
        "crawltrigger",
        "approvalstatus",
        "sourcestatus",
        "sourcekind",
    ):
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
