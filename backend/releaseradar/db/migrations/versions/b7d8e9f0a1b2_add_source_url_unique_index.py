"""Add unique index on source_url

Revision ID: b7d8e9f0a1b2
Revises: a1b2c3d4e5f6
Create Date: 2025-11-14 06:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7d8e9f0a1b2'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique index on lowercase source_url to prevent duplicate events."""
    
    # First, clean up duplicates (keep oldest event per URL)
    op.execute("""
        DELETE FROM events
        WHERE id NOT IN (
            SELECT MIN(id)
            FROM events
            WHERE source_url IS NOT NULL
            GROUP BY LOWER(source_url)
        )
        AND source_url IS NOT NULL
    """)
    
    # Add unique index on lowercase source_url
    # This prevents race condition duplicates at database level
    op.create_index(
        'ix_events_source_url_lower_unique',
        'events',
        [sa.text('LOWER(source_url)')],
        unique=True,
        postgresql_where=sa.text('source_url IS NOT NULL')
    )


def downgrade() -> None:
    """Remove unique index on source_url."""
    op.drop_index('ix_events_source_url_lower_unique', table_name='events')
