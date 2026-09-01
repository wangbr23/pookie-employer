"""Add profile AI consent and structured AI call metadata."""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_ai_consent_and_call_logs"
down_revision: str | None = "0003_recommendation_schema"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Add explicit consent fields and minimal call observability."""
    ai_call_status = sa.Enum(
        "attempted", "succeeded", "failed", name="aicallstatus"
    )
    ai_call_status.create(op.get_bind(), checkfirst=True)
    op.add_column(
        "user_profiles",
        sa.Column(
            "ai_consent_given",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("user_profiles", sa.Column("ai_consent_provider", sa.String(128)))
    op.add_column(
        "user_profiles", sa.Column("ai_consent_model_family", sa.String(128))
    )
    op.add_column(
        "user_profiles",
        sa.Column("ai_consent_updated_at", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "ai_call_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("profile_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("provider", sa.String(128), nullable=False),
        sa.Column("model_name", sa.String(128), nullable=False),
        sa.Column("operation", sa.String(64), nullable=False),
        sa.Column("status", ai_call_status, nullable=False),
        sa.Column("call_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("input_tokens", sa.Integer()),
        sa.Column("output_tokens", sa.Integer()),
        sa.Column("estimated_cost", sa.Numeric(precision=12, scale=6)),
        sa.Column("crawl_run_id", postgresql.UUID(as_uuid=True)),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["profile_id"], ["user_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["crawl_run_id"], ["crawl_runs.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "ix_ai_call_logs_profile_created",
        "ai_call_logs",
        ["profile_id", "created_at"],
    )


def downgrade() -> None:
    """Remove AI consent and call metadata."""
    op.drop_index("ix_ai_call_logs_profile_created", table_name="ai_call_logs")
    op.drop_table("ai_call_logs")
    op.drop_column("user_profiles", "ai_consent_updated_at")
    op.drop_column("user_profiles", "ai_consent_model_family")
    op.drop_column("user_profiles", "ai_consent_provider")
    op.drop_column("user_profiles", "ai_consent_given")
    sa.Enum(name="aicallstatus").drop(op.get_bind(), checkfirst=True)
