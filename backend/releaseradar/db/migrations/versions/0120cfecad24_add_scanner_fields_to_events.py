"""add scanner fields to events

Revision ID: 0120cfecad24
Revises: e8f3a7b12345
Create Date: 2025-11-11 22:03:36.077267

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0120cfecad24'
down_revision: Union[str, Sequence[str], None] = 'e8f3a7b12345'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns for scanner tracking
    op.add_column('events', sa.Column('raw_id', sa.String(), nullable=True))
    op.add_column('events', sa.Column('source_scanner', sa.String(), nullable=True))
    op.add_column('events', sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()))
    
    # Add indexes on new columns
    op.create_index(op.f('ix_events_raw_id'), 'events', ['raw_id'], unique=False)
    op.create_index(op.f('ix_events_source_scanner'), 'events', ['source_scanner'], unique=False)
    
    # Add unique constraint on natural key (ticker, event_type, raw_id)
    op.create_unique_constraint('uix_event_natural_key', 'events', ['ticker', 'event_type', 'raw_id'])


def downgrade() -> None:
    """Downgrade schema."""
    # Drop unique constraint
    op.drop_constraint('uix_event_natural_key', 'events', type_='unique')
    
    # Drop indexes
    op.drop_index(op.f('ix_events_source_scanner'), table_name='events')
    op.drop_index(op.f('ix_events_raw_id'), table_name='events')
    
    # Drop columns
    op.drop_column('events', 'updated_at')
    op.drop_column('events', 'source_scanner')
    op.drop_column('events', 'raw_id')
