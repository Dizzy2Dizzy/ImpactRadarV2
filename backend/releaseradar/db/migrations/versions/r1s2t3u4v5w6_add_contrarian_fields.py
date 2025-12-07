"""Add contrarian/hidden bearish fields to events table

Revision ID: r1s2t3u4v5w6
Revises: q1r2s3t4u5v6
Create Date: 2025-11-28 00:00:00.000000

These fields enable the Market Echo Engine to learn from contrarian outcomes:
- Events where prediction was positive/neutral but stock declined
- Used to detect "hidden bearish" patterns for future events
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'r1s2t3u4v5w6'
down_revision: Union[str, Sequence[str], None] = 'q1r2s3t4u5v6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add contrarian/hidden bearish fields to events table."""
    
    op.add_column('events', sa.Column('contrarian_outcome', sa.Boolean(), nullable=True))
    op.add_column('events', sa.Column('realized_direction', sa.String(), nullable=True))
    op.add_column('events', sa.Column('realized_return_1d', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('hidden_bearish_prob', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('hidden_bearish_signal', sa.Boolean(), nullable=True))
    
    op.create_index('ix_events_contrarian_outcome', 'events', ['contrarian_outcome'])
    op.create_index('ix_events_hidden_bearish_signal', 'events', ['hidden_bearish_signal'])


def downgrade() -> None:
    """Remove contrarian/hidden bearish fields from events table."""
    
    op.drop_index('ix_events_hidden_bearish_signal', table_name='events')
    op.drop_index('ix_events_contrarian_outcome', table_name='events')
    
    op.drop_column('events', 'hidden_bearish_signal')
    op.drop_column('events', 'hidden_bearish_prob')
    op.drop_column('events', 'realized_return_1d')
    op.drop_column('events', 'realized_direction')
    op.drop_column('events', 'contrarian_outcome')
