"""make quiz_results.completed_at timezone-aware

Revision ID: 3e03b6ead29f
Revises: 0e4f0fd0fa5b
Create Date: 2026-07-19 08:39:16.490428

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '3e03b6ead29f'
down_revision: Union[str, Sequence[str], None] = '0e4f0fd0fa5b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(
        """
        ALTER TABLE quiz_results
        ALTER COLUMN completed_at
        TYPE TIMESTAMPTZ
        USING completed_at AT TIME ZONE 'UTC'
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        """
        ALTER TABLE quiz_results
        ALTER COLUMN completed_at
        TYPE TIMESTAMP
        USING completed_at AT TIME ZONE 'UTC'
        """
    )