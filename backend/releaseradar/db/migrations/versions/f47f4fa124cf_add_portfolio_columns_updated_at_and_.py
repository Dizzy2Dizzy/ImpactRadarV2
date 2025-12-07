"""add_portfolio_columns_updated_at_and_label

Revision ID: f47f4fa124cf
Revises: 0120cfecad24
Create Date: 2025-11-13 03:08:27.806767

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f47f4fa124cf'
down_revision: Union[str, Sequence[str], None] = '0120cfecad24'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add updated_at column to user_portfolios
    op.add_column('user_portfolios', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Add label, created_at, updated_at columns to portfolio_positions
    op.add_column('portfolio_positions', sa.Column('label', sa.String(), nullable=True))
    op.add_column('portfolio_positions', sa.Column('created_at', sa.DateTime(), nullable=True))
    op.add_column('portfolio_positions', sa.Column('updated_at', sa.DateTime(), nullable=True))
    
    # Update ondelete cascade for portfolio_positions foreign key
    # Note: This requires dropping and recreating the constraint
    op.drop_constraint('portfolio_positions_portfolio_id_fkey', 'portfolio_positions', type_='foreignkey')
    op.create_foreign_key(
        'portfolio_positions_portfolio_id_fkey',
        'portfolio_positions',
        'user_portfolios',
        ['portfolio_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove ondelete cascade
    op.drop_constraint('portfolio_positions_portfolio_id_fkey', 'portfolio_positions', type_='foreignkey')
    op.create_foreign_key(
        'portfolio_positions_portfolio_id_fkey',
        'portfolio_positions',
        'user_portfolios',
        ['portfolio_id'],
        ['id']
    )
    
    # Remove columns from portfolio_positions
    op.drop_column('portfolio_positions', 'updated_at')
    op.drop_column('portfolio_positions', 'created_at')
    op.drop_column('portfolio_positions', 'label')
    
    # Remove updated_at from user_portfolios
    op.drop_column('user_portfolios', 'updated_at')
