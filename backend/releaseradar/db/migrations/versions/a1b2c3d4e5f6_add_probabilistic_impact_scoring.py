"""Add probabilistic impact scoring (EventGroupPrior table and Event columns)

Revision ID: a1b2c3d4e5f6
Revises: f47f4fa124cf
Create Date: 2025-11-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'f47f4fa124cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add EventGroupPrior table and probabilistic scoring columns to events."""
    
    # Create event_group_priors table
    op.create_table(
        'event_group_priors',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('sector', sa.String(), nullable=False),
        sa.Column('cap_bucket', sa.String(), nullable=False),
        sa.Column('mu', sa.Float(), nullable=False),
        sa.Column('sigma', sa.Float(), nullable=False),
        sa.Column('n', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_type', 'sector', 'cap_bucket', name='uq_event_group_priors_key')
    )
    
    # Create indexes on event_group_priors
    op.create_index('ix_event_group_priors_event_type', 'event_group_priors', ['event_type'], unique=False)
    op.create_index('ix_event_group_priors_sector', 'event_group_priors', ['sector'], unique=False)
    op.create_index(op.f('ix_event_group_priors_id'), 'event_group_priors', ['id'], unique=False)
    
    # Add probabilistic scoring columns to events table
    op.add_column('events', sa.Column('impact_p_move', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('impact_p_up', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('impact_p_down', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('impact_score_version', sa.Integer(), server_default='1', nullable=False))


def downgrade() -> None:
    """Remove probabilistic impact scoring tables and columns."""
    
    # Drop columns from events table
    op.drop_column('events', 'impact_score_version')
    op.drop_column('events', 'impact_p_down')
    op.drop_column('events', 'impact_p_up')
    op.drop_column('events', 'impact_p_move')
    
    # Drop indexes and table
    op.drop_index(op.f('ix_event_group_priors_id'), table_name='event_group_priors')
    op.drop_index('ix_event_group_priors_sector', table_name='event_group_priors')
    op.drop_index('ix_event_group_priors_event_type', table_name='event_group_priors')
    op.drop_table('event_group_priors')
