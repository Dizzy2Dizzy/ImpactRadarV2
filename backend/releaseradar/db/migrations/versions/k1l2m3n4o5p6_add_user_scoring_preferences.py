"""Add user_scoring_preferences table

Revision ID: k1l2m3n4o5p6
Revises: b7d8e9f0a1b2
Create Date: 2025-11-14 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'k1l2m3n4o5p6'
down_revision: Union[str, Sequence[str], None] = 'b7d8e9f0a1b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - add user_scoring_preferences table."""
    op.create_table(
        'user_scoring_preferences',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('event_type_weights', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('sector_weights', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence_threshold', sa.Float(), nullable=True),
        sa.Column('min_impact_score', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    op.create_index(
        op.f('ix_user_scoring_preferences_id'),
        'user_scoring_preferences',
        ['id'],
        unique=False
    )
    op.create_index(
        'ix_user_scoring_preferences_user_id',
        'user_scoring_preferences',
        ['user_id'],
        unique=False
    )


def downgrade() -> None:
    """Downgrade schema - drop user_scoring_preferences table."""
    op.drop_index('ix_user_scoring_preferences_user_id', table_name='user_scoring_preferences')
    op.drop_index(op.f('ix_user_scoring_preferences_id'), table_name='user_scoring_preferences')
    op.drop_table('user_scoring_preferences')
