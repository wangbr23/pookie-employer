"""Add phenom source kind

Revision ID: 0007_add_phenom_source_kind
Revises: 0006_add_netflix_source_kind
Create Date: 2026-09-09

"""

from alembic import op

revision: str = "0007_add_phenom_source_kind"
down_revision: str = "0006_add_netflix_source_kind"
branch_labels: tuple[str, ...] | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Register the phenom adapter kind on the native sourcekind enum.

    Safe inside the migration transaction on Postgres 12+: the new value is
    added but never used within this transaction.
    """
    op.execute("ALTER TYPE sourcekind ADD VALUE IF NOT EXISTS 'phenom'")


def downgrade() -> None:
    """Postgres cannot drop enum values; the unused value stays registered."""
