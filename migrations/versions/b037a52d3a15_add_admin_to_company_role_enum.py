"""add_admin_to_company_role_enum

Revision ID: b037a52d3a15
Revises: cd8774f3da05
Create Date: 2026-06-22 13:13:29.329486

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b037a52d3a15'
down_revision: Union[str, Sequence[str], None] = 'cd8774f3da05'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Додаємо нове значення 'ADMIN' до вже існуючого PostgreSQL ENUM типу.
    # IF NOT EXISTS — захист від помилки, якщо міграцію запустять двічі.
    op.execute("ALTER TYPE companyrole ADD VALUE IF NOT EXISTS 'ADMIN'")


def downgrade() -> None:
    """Downgrade schema."""
    pass
