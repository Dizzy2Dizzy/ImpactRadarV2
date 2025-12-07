"""add_data_quality_tables

Revision ID: 74ab486dae91
Revises: 87c2226ce044
Create Date: 2025-11-21 03:01:01.892222

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSON


# revision identifiers, used by Alembic.
revision: str = '74ab486dae91'
down_revision: Union[str, Sequence[str], None] = '87c2226ce044'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add data quality monitoring tables."""
    
    # ============================================================================
    # 1. Create data_quality_snapshots table
    # ============================================================================
    op.create_table(
        'data_quality_snapshots',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('metric_key', sa.String(), nullable=False, index=True),
        sa.Column('scope', sa.String(), nullable=False),
        sa.Column('sample_count', sa.Integer(), nullable=False),
        sa.Column('freshness_ts', sa.DateTime(), nullable=False),
        sa.Column('source_job', sa.String(), nullable=False),
        sa.Column('quality_grade', sa.String(), nullable=False),
        sa.Column('summary_json', JSON, nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes on data_quality_snapshots
    op.create_index(op.f('ix_data_quality_snapshots_id'), 'data_quality_snapshots', ['id'], unique=False)
    op.create_index('ix_data_quality_snapshots_metric_key', 'data_quality_snapshots', ['metric_key'], unique=False)
    op.create_index('ix_data_quality_snapshots_created_at', 'data_quality_snapshots', ['created_at'], unique=False)
    
    # ============================================================================
    # 2. Create data_pipeline_runs table
    # ============================================================================
    op.create_table(
        'data_pipeline_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('job_name', sa.String(), nullable=False, index=True),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, index=True),
        sa.Column('rows_written', sa.Integer(), nullable=True),
        sa.Column('source_hash', sa.String(), nullable=True),
        sa.Column('error_blob', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes on data_pipeline_runs
    op.create_index(op.f('ix_data_pipeline_runs_id'), 'data_pipeline_runs', ['id'], unique=False)
    op.create_index('ix_data_pipeline_runs_job_name', 'data_pipeline_runs', ['job_name'], unique=False)
    op.create_index('ix_data_pipeline_runs_status', 'data_pipeline_runs', ['status'], unique=False)
    op.create_index('ix_data_pipeline_runs_started_at', 'data_pipeline_runs', ['started_at'], unique=False)
    
    # ============================================================================
    # 3. Create data_lineage_records table
    # ============================================================================
    op.create_table(
        'data_lineage_records',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('metric_key', sa.String(), nullable=False, index=True),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False, index=True),
        sa.Column('source_url', sa.String(), nullable=True),
        sa.Column('payload_hash', sa.String(), nullable=True),
        sa.Column('observed_at', sa.DateTime(), nullable=False, index=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes on data_lineage_records
    op.create_index(op.f('ix_data_lineage_records_id'), 'data_lineage_records', ['id'], unique=False)
    op.create_index('ix_data_lineage_records_metric_key', 'data_lineage_records', ['metric_key'], unique=False)
    op.create_index('ix_data_lineage_records_entity_type', 'data_lineage_records', ['entity_type'], unique=False)
    op.create_index('ix_data_lineage_records_observed_at', 'data_lineage_records', ['observed_at'], unique=False)
    
    # ============================================================================
    # 4. Create audit_log_entries table
    # ============================================================================
    op.create_table(
        'audit_log_entries',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False, index=True),
        sa.Column('entity_id', sa.Integer(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('performed_by', sa.Integer(), nullable=True, index=True),
        sa.Column('diff_json', JSON, nullable=True),
        sa.Column('signature', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['performed_by'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Create indexes on audit_log_entries
    op.create_index(op.f('ix_audit_log_entries_id'), 'audit_log_entries', ['id'], unique=False)
    op.create_index('ix_audit_log_entries_entity_type', 'audit_log_entries', ['entity_type'], unique=False)
    op.create_index('ix_audit_log_entries_created_at', 'audit_log_entries', ['created_at'], unique=False)
    op.create_index('ix_audit_log_entries_performed_by', 'audit_log_entries', ['performed_by'], unique=False)


def downgrade() -> None:
    """Remove data quality monitoring tables."""
    
    # Drop audit_log_entries table
    op.drop_index('ix_audit_log_entries_performed_by', table_name='audit_log_entries')
    op.drop_index('ix_audit_log_entries_created_at', table_name='audit_log_entries')
    op.drop_index('ix_audit_log_entries_entity_type', table_name='audit_log_entries')
    op.drop_index(op.f('ix_audit_log_entries_id'), table_name='audit_log_entries')
    op.drop_table('audit_log_entries')
    
    # Drop data_lineage_records table
    op.drop_index('ix_data_lineage_records_observed_at', table_name='data_lineage_records')
    op.drop_index('ix_data_lineage_records_entity_type', table_name='data_lineage_records')
    op.drop_index('ix_data_lineage_records_metric_key', table_name='data_lineage_records')
    op.drop_index(op.f('ix_data_lineage_records_id'), table_name='data_lineage_records')
    op.drop_table('data_lineage_records')
    
    # Drop data_pipeline_runs table
    op.drop_index('ix_data_pipeline_runs_started_at', table_name='data_pipeline_runs')
    op.drop_index('ix_data_pipeline_runs_status', table_name='data_pipeline_runs')
    op.drop_index('ix_data_pipeline_runs_job_name', table_name='data_pipeline_runs')
    op.drop_index(op.f('ix_data_pipeline_runs_id'), table_name='data_pipeline_runs')
    op.drop_table('data_pipeline_runs')
    
    # Drop data_quality_snapshots table
    op.drop_index('ix_data_quality_snapshots_created_at', table_name='data_quality_snapshots')
    op.drop_index('ix_data_quality_snapshots_metric_key', table_name='data_quality_snapshots')
    op.drop_index(op.f('ix_data_quality_snapshots_id'), table_name='data_quality_snapshots')
    op.drop_table('data_quality_snapshots')
