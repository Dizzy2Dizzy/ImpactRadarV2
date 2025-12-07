"""add_dashboard_mode_to_users

Revision ID: n9o8p7q6r5s4
Revises: eb791a0b76b9
Create Date: 2025-11-16 04:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'n9o8p7q6r5s4'
down_revision: Union[str, Sequence[str], None] = 'eb791a0b76b9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add dashboard_mode column to users table with default value."""
    op.add_column('users', sa.Column('dashboard_mode', sa.String(), nullable=False, server_default='watchlist'))


def downgrade() -> None:
    """Remove dashboard_mode column from users table."""
    op.drop_column('users', 'dashboard_mode')
