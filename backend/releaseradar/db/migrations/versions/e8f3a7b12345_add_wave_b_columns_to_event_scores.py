"""Add Wave B columns to event_scores (ticker, event_type, confidence)

Revision ID: e8f3a7b12345
Revises: d9c86ccd5496
Create Date: 2025-11-11 19:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f3a7b12345'
down_revision: Union[str, Sequence[str], None] = 'd9c86ccd5496'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ticker, event_type, and confidence columns to event_scores table."""
    # Add new columns
    op.add_column('event_scores', sa.Column('ticker', sa.String(), nullable=True))
    op.add_column('event_scores', sa.Column('event_type', sa.String(), nullable=True))
    op.add_column('event_scores', sa.Column('confidence', sa.Integer(), server_default='70', nullable=False))
    
    # Backfill ticker and event_type from events table
    op.execute("""
        UPDATE event_scores
        SET ticker = events.ticker,
            event_type = events.event_type
        FROM events
        WHERE event_scores.event_id = events.id
    """)
    
    # Make ticker and event_type NOT NULL after backfill
    op.alter_column('event_scores', 'ticker', nullable=False)
    op.alter_column('event_scores', 'event_type', nullable=False)
    
    # Create new indexes
    op.create_index('ix_event_scores_ticker', 'event_scores', ['ticker'], unique=False)
    op.create_index('ix_event_scores_ticker_event_type', 'event_scores', ['ticker', 'event_type'], unique=False)


def downgrade() -> None:
    """Remove Wave B columns from event_scores table."""
    op.drop_index('ix_event_scores_ticker_event_type', table_name='event_scores')
    op.drop_index('ix_event_scores_ticker', table_name='event_scores')
    op.drop_column('event_scores', 'confidence')
    op.drop_column('event_scores', 'event_type')
    op.drop_column('event_scores', 'ticker')
