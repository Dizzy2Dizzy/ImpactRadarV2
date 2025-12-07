"""Add ML self-learning tables and columns

Revision ID: m1n2o3p4q5r6
Revises: k1l2m3n4o5p6
Create Date: 2025-11-15 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = 'm1n2o3p4q5r6'
down_revision: Union[str, Sequence[str], None] = 'k1l2m3n4o5p6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ML self-learning tables and columns to events and event_scores."""
    
    # ============================================================================
    # 1. Create event_outcomes table
    # ============================================================================
    op.create_table(
        'event_outcomes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('ticker', sa.String(), nullable=False),
        sa.Column('horizon', sa.String(), nullable=False),
        sa.Column('price_before', sa.Float(), nullable=False),
        sa.Column('price_after', sa.Float(), nullable=False),
        sa.Column('return_pct', sa.Float(), nullable=False),
        sa.Column('abs_return_pct', sa.Float(), nullable=False),
        sa.Column('direction_correct', sa.Boolean(), nullable=True),
        sa.Column('label_date', sa.Date(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'horizon', name='uq_event_outcomes_event_horizon')
    )
    
    # Create indexes on event_outcomes
    op.create_index(op.f('ix_event_outcomes_id'), 'event_outcomes', ['id'], unique=False)
    op.create_index('ix_event_outcomes_event_id', 'event_outcomes', ['event_id'], unique=False)
    op.create_index('ix_event_outcomes_ticker', 'event_outcomes', ['ticker'], unique=False)
    op.create_index('ix_event_outcomes_label_date', 'event_outcomes', ['label_date'], unique=False)
    op.create_index('ix_event_outcomes_horizon', 'event_outcomes', ['horizon'], unique=False)
    
    # ============================================================================
    # 2. Create model_features table
    # ============================================================================
    op.create_table(
        'model_features',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('horizon', sa.String(), nullable=False),
        sa.Column('features', JSON, nullable=False),
        sa.Column('feature_version', sa.String(), nullable=False),
        sa.Column('base_score', sa.Integer(), nullable=True),
        sa.Column('sector', sa.String(), nullable=True),
        sa.Column('event_type', sa.String(), nullable=True),
        sa.Column('market_vol', sa.Float(), nullable=True),
        sa.Column('info_tier', sa.String(), nullable=True),
        sa.Column('extracted_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'horizon', name='uq_model_features_event_horizon')
    )
    
    # Create indexes on model_features
    op.create_index(op.f('ix_model_features_id'), 'model_features', ['id'], unique=False)
    op.create_index('ix_model_features_event_id', 'model_features', ['event_id'], unique=False)
    op.create_index('ix_model_features_feature_version', 'model_features', ['feature_version'], unique=False)
    op.create_index('ix_model_features_extracted_at', 'model_features', ['extracted_at'], unique=False)
    
    # ============================================================================
    # 3. Create model_registry table
    # ============================================================================
    op.create_table(
        'model_registry',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('version', sa.String(), nullable=False),
        sa.Column('status', sa.String(), nullable=False, server_default='staging'),
        sa.Column('model_path', sa.String(), nullable=False),
        sa.Column('metrics', JSON, nullable=False),
        sa.Column('feature_version', sa.String(), nullable=False),
        sa.Column('trained_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('promoted_at', sa.DateTime(), nullable=True),
        sa.Column('cohort_pct', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'version', name='uq_model_registry_name_version')
    )
    
    # Create indexes on model_registry
    op.create_index(op.f('ix_model_registry_id'), 'model_registry', ['id'], unique=False)
    op.create_index('ix_model_registry_status', 'model_registry', ['status'], unique=False)
    op.create_index('ix_model_registry_trained_at', 'model_registry', ['trained_at'], unique=False)
    
    # ============================================================================
    # 4. Add ML columns to events table
    # ============================================================================
    op.add_column('events', sa.Column('ml_adjusted_score', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('ml_confidence', sa.Float(), nullable=True))
    op.add_column('events', sa.Column('ml_model_version', sa.String(), nullable=True))
    
    # ============================================================================
    # 5. Add ML columns to event_scores table
    # ============================================================================
    op.add_column('event_scores', sa.Column('ml_adjusted_score', sa.Integer(), nullable=True))
    op.add_column('event_scores', sa.Column('ml_confidence', sa.Float(), nullable=True))
    op.add_column('event_scores', sa.Column('ml_model_version', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove ML self-learning tables and columns."""
    
    # Drop columns from event_scores table
    op.drop_column('event_scores', 'ml_model_version')
    op.drop_column('event_scores', 'ml_confidence')
    op.drop_column('event_scores', 'ml_adjusted_score')
    
    # Drop columns from events table
    op.drop_column('events', 'ml_model_version')
    op.drop_column('events', 'ml_confidence')
    op.drop_column('events', 'ml_adjusted_score')
    
    # Drop model_registry table
    op.drop_index('ix_model_registry_trained_at', table_name='model_registry')
    op.drop_index('ix_model_registry_status', table_name='model_registry')
    op.drop_index(op.f('ix_model_registry_id'), table_name='model_registry')
    op.drop_table('model_registry')
    
    # Drop model_features table
    op.drop_index('ix_model_features_extracted_at', table_name='model_features')
    op.drop_index('ix_model_features_feature_version', table_name='model_features')
    op.drop_index('ix_model_features_event_id', table_name='model_features')
    op.drop_index(op.f('ix_model_features_id'), table_name='model_features')
    op.drop_table('model_features')
    
    # Drop event_outcomes table
    op.drop_index('ix_event_outcomes_horizon', table_name='event_outcomes')
    op.drop_index('ix_event_outcomes_label_date', table_name='event_outcomes')
    op.drop_index('ix_event_outcomes_ticker', table_name='event_outcomes')
    op.drop_index('ix_event_outcomes_event_id', table_name='event_outcomes')
    op.drop_index(op.f('ix_event_outcomes_id'), table_name='event_outcomes')
    op.drop_table('event_outcomes')
