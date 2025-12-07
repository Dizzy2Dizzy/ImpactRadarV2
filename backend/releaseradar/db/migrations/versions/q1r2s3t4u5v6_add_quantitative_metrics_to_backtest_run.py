"""add_quantitative_metrics_to_backtest_run

Revision ID: q1r2s3t4u5v6
Revises: p1q2r3s4t5u6
Create Date: 2025-11-22 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'q1r2s3t4u5v6'
down_revision = 'p1q2r3s4t5u6'
branch_labels = None
depends_on = None


def upgrade():
    """
    Add Phase 1 quantitative metrics columns to backtest_runs table:
    - sortino_ratio: Sortino Ratio (risk-adjusted return using downside deviation)
    - avg_atr: Average True Range (volatility measure)
    - parkinson_volatility: Parkinson's historical volatility (high-low range based)
    """
    op.add_column('backtest_runs', sa.Column('sortino_ratio', sa.Float(), nullable=True))
    op.add_column('backtest_runs', sa.Column('avg_atr', sa.Float(), nullable=True))
    op.add_column('backtest_runs', sa.Column('parkinson_volatility', sa.Float(), nullable=True))


def downgrade():
    """Remove quantitative metrics columns from backtest_runs table"""
    op.drop_column('backtest_runs', 'parkinson_volatility')
    op.drop_column('backtest_runs', 'avg_atr')
    op.drop_column('backtest_runs', 'sortino_ratio')
