"""Add ML provenance fields to events table

Revision ID: p1q2r3s4t5u6
Revises: n9o8p7q6r5s4
Create Date: 2025-11-16 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'p1q2r3s4t5u6'
down_revision: Union[str, Sequence[str], None] = 'n9o8p7q6r5s4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add model_source and delta_applied to events table."""
    
    # Add ML provenance columns to events table
    op.add_column('events', sa.Column('model_source', sa.String(), nullable=True))
    op.add_column('events', sa.Column('delta_applied', sa.Float(), nullable=True))


def downgrade() -> None:
    """Remove model_source and delta_applied from events table."""
    
    # Drop columns from events table
    op.drop_column('events', 'delta_applied')
    op.drop_column('events', 'model_source')
