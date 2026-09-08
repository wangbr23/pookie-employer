"""add skip_reason to jobs

Revision ID: 6f5a807ad4cb
Revises: 0004_ai_consent_and_call_logs
Create Date: 2026-09-08 00:48:58.890387

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6f5a807ad4cb'
down_revision: Union[str, Sequence[str], None] = '0004_ai_consent_and_call_logs'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('jobs', sa.Column('skip_reason', sa.String(length=64), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('jobs', 'skip_reason')
