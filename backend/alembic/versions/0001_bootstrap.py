"""Establish the initial Alembic revision without adding domain tables."""

revision: str = "0001_bootstrap"
down_revision: str | None = None
branch_labels: tuple[str, ...] | None = None
depends_on: tuple[str, ...] | None = None


def upgrade() -> None:
    """Apply the empty bootstrap revision."""


def downgrade() -> None:
    """Revert the empty bootstrap revision."""
