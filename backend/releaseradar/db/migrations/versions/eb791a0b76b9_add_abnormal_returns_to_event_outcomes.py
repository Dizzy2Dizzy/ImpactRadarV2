"""add abnormal returns to event outcomes

Revision ID: eb791a0b76b9
Revises: m1n2o3p4q5r6
Create Date: 2025-11-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'eb791a0b76b9'
down_revision: Union[str, None] = 'm1n2o3p4q5r6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add abnormal returns columns to event_outcomes table."""
    
    # Add new columns for abnormal returns calculation
    op.add_column('event_outcomes', sa.Column('return_pct_raw', sa.Float(), nullable=True))
    op.add_column('event_outcomes', sa.Column('benchmark_return_pct', sa.Float(), nullable=True))
    op.add_column('event_outcomes', sa.Column('has_benchmark_data', sa.Boolean(), nullable=False, server_default='false'))
    
    # Update existing rows: copy return_pct to return_pct_raw and set benchmark to 0
    op.execute("""
        UPDATE event_outcomes 
        SET 
            return_pct_raw = return_pct,
            benchmark_return_pct = 0.0,
            has_benchmark_data = false
        WHERE return_pct_raw IS NULL
    """)
    
    # Update column comment to reflect that return_pct is now abnormal return
    # Note: This is PostgreSQL-specific syntax
    op.execute("COMMENT ON COLUMN event_outcomes.return_pct IS 'Abnormal return (stock return - benchmark return) - PRIMARY ML TARGET'")
    op.execute("COMMENT ON COLUMN event_outcomes.return_pct_raw IS 'Raw stock return (before benchmark adjustment)'")
    op.execute("COMMENT ON COLUMN event_outcomes.benchmark_return_pct IS 'SPY benchmark return for same period'")
    op.execute("COMMENT ON COLUMN event_outcomes.has_benchmark_data IS 'True if SPY benchmark data was available'")


def downgrade() -> None:
    """Remove abnormal returns columns from event_outcomes table."""
    
    # Remove the new columns
    op.drop_column('event_outcomes', 'has_benchmark_data')
    op.drop_column('event_outcomes', 'benchmark_return_pct')
    op.drop_column('event_outcomes', 'return_pct_raw')
    
    # Remove column comments
    op.execute("COMMENT ON COLUMN event_outcomes.return_pct IS NULL")
