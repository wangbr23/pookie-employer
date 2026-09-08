"""Add workday source kind

Revision ID: 0005_add_workday_source_kind
Revises: 6f5a807ad4cb
Create Date: 2026-09-08

"""

from alembic import op

revision: str = "0005_add_workday_source_kind"
down_revision: str = "6f5a807ad4cb"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Register the workday adapter kind on the native sourcekind enum.

    Safe inside the migration transaction on Postgres 12+: the new value is
    added but never used within this transaction.
    """
    op.execute("ALTER TYPE sourcekind ADD VALUE IF NOT EXISTS 'workday'")


def downgrade() -> None:
    """Postgres cannot drop enum values; the unused value stays registered."""
