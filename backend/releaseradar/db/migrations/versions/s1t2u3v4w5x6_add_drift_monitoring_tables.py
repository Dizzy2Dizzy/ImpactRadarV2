"""Add drift monitoring and calibration tables for ML accuracy improvements

Revision ID: s1t2u3v4w5x6
Revises: r1s2t3u4v5w6
Create Date: 2025-12-04 00:00:00.000000

Tier 1 of accuracy improvement roadmap:
- ModelPerformanceSnapshot: Track model metrics over rolling windows
- DriftAlert: Store alerts when model performance degrades
- CalibrationSnapshot: Store ECE and reliability diagram data
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


revision: str = 's1t2u3v4w5x6'
down_revision: Union[str, Sequence[str], None] = ('r1s2t3u4v5w6', '74ab486dae91')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create model performance monitoring tables."""
    
    op.create_table(
        'model_performance_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('horizon', sa.String(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('direction_accuracy', sa.Float(), nullable=True),
        sa.Column('mae', sa.Float(), nullable=True),
        sa.Column('rmse', sa.Float(), nullable=True),
        sa.Column('calibration_error', sa.Float(), nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('window_days', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['model_id'], ['model_registry.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_id', 'horizon', 'snapshot_date', 'window_days', 
                           name='uq_model_perf_snapshot')
    )
    
    op.create_index(op.f('ix_model_performance_snapshots_id'), 
                   'model_performance_snapshots', ['id'], unique=False)
    op.create_index('ix_model_perf_snapshot_model_id', 
                   'model_performance_snapshots', ['model_id'], unique=False)
    op.create_index('ix_model_perf_snapshot_date', 
                   'model_performance_snapshots', ['snapshot_date'], unique=False)
    op.create_index('ix_model_perf_snapshot_horizon', 
                   'model_performance_snapshots', ['horizon'], unique=False)
    
    op.create_table(
        'drift_alerts',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('horizon', sa.String(), nullable=False),
        sa.Column('alert_type', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False, server_default='medium'),
        sa.Column('metrics_before', JSON, nullable=True),
        sa.Column('metrics_after', JSON, nullable=True),
        sa.Column('detected_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('resolution_notes', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['model_id'], ['model_registry.id']),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_index(op.f('ix_drift_alerts_id'), 
                   'drift_alerts', ['id'], unique=False)
    op.create_index('ix_drift_alerts_model_id', 
                   'drift_alerts', ['model_id'], unique=False)
    op.create_index('ix_drift_alerts_detected_at', 
                   'drift_alerts', ['detected_at'], unique=False)
    op.create_index('ix_drift_alerts_severity', 
                   'drift_alerts', ['severity'], unique=False)
    op.create_index('ix_drift_alerts_resolved_at', 
                   'drift_alerts', ['resolved_at'], unique=False)
    
    op.create_table(
        'calibration_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('model_id', sa.Integer(), nullable=False),
        sa.Column('horizon', sa.String(), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('expected_calibration_error', sa.Float(), nullable=True),
        sa.Column('max_calibration_error', sa.Float(), nullable=True),
        sa.Column('bin_data', JSON, nullable=True),
        sa.Column('sample_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('window_days', sa.Integer(), nullable=False, server_default='30'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['model_id'], ['model_registry.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_id', 'horizon', 'snapshot_date', 
                           name='uq_calibration_snapshot')
    )
    
    op.create_index(op.f('ix_calibration_snapshots_id'), 
                   'calibration_snapshots', ['id'], unique=False)
    op.create_index('ix_calibration_snapshot_model_id', 
                   'calibration_snapshots', ['model_id'], unique=False)
    op.create_index('ix_calibration_snapshot_date', 
                   'calibration_snapshots', ['snapshot_date'], unique=False)


def downgrade() -> None:
    """Remove model performance monitoring tables."""
    
    op.drop_index('ix_calibration_snapshot_date', table_name='calibration_snapshots')
    op.drop_index('ix_calibration_snapshot_model_id', table_name='calibration_snapshots')
    op.drop_index(op.f('ix_calibration_snapshots_id'), table_name='calibration_snapshots')
    op.drop_table('calibration_snapshots')
    
    op.drop_index('ix_drift_alerts_resolved_at', table_name='drift_alerts')
    op.drop_index('ix_drift_alerts_severity', table_name='drift_alerts')
    op.drop_index('ix_drift_alerts_detected_at', table_name='drift_alerts')
    op.drop_index('ix_drift_alerts_model_id', table_name='drift_alerts')
    op.drop_index(op.f('ix_drift_alerts_id'), table_name='drift_alerts')
    op.drop_table('drift_alerts')
    
    op.drop_index('ix_model_perf_snapshot_horizon', table_name='model_performance_snapshots')
    op.drop_index('ix_model_perf_snapshot_date', table_name='model_performance_snapshots')
    op.drop_index('ix_model_perf_snapshot_model_id', table_name='model_performance_snapshots')
    op.drop_index(op.f('ix_model_performance_snapshots_id'), table_name='model_performance_snapshots')
    op.drop_table('model_performance_snapshots')
