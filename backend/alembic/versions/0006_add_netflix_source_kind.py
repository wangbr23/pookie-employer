"""Add netflix source kind

Revision ID: 0006_add_netflix_source_kind
Revises: 0005_add_workday_source_kind
Create Date: 2026-09-08

"""

from alembic import op

revision: str = "0006_add_netflix_source_kind"
down_revision: str = "0005_add_workday_source_kind"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Register the netflix adapter kind on the native sourcekind enum.

    Safe inside the migration transaction on Postgres 12+: the new value is
    added but never used within this transaction.
    """
    op.execute("ALTER TYPE sourcekind ADD VALUE IF NOT EXISTS 'netflix'")


def downgrade() -> None:
    """Postgres cannot drop enum values; the unused value stays registered."""
