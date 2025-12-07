-- ============================================================================
-- Migration: 001_add_data_quality_tables
-- Description: Creates data quality monitoring tables for Impact Radar
-- Date: 2025-11-21
-- ============================================================================
-- This migration adds 4 tables for data quality monitoring and auditing:
--   1. data_quality_snapshots - tracks quality metrics and freshness
--   2. data_pipeline_runs - logs pipeline execution status
--   3. data_lineage_records - tracks data provenance
--   4. audit_log_entries - audit log for entity mutations
--
-- These tables enable production-grade data quality monitoring, pipeline
-- observability, and compliance auditing.
-- ============================================================================

BEGIN;

-- ============================================================================
-- 1. CREATE TABLE: data_quality_snapshots
-- ============================================================================
-- Tracks quality metrics for various data sources and scopes.
-- Used to surface data quality warnings in dashboards and admin panels.

CREATE TABLE IF NOT EXISTS data_quality_snapshots (
    id SERIAL PRIMARY KEY,
    metric_key VARCHAR NOT NULL,
    scope VARCHAR NOT NULL,
    sample_count INTEGER NOT NULL,
    freshness_ts TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    source_job VARCHAR NOT NULL,
    quality_grade VARCHAR NOT NULL,
    summary_json JSON,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Create indexes for data_quality_snapshots
CREATE INDEX IF NOT EXISTS ix_data_quality_snapshots_id ON data_quality_snapshots(id);
CREATE INDEX IF NOT EXISTS ix_data_quality_snapshots_metric_key ON data_quality_snapshots(metric_key);
CREATE INDEX IF NOT EXISTS ix_data_quality_snapshots_created_at ON data_quality_snapshots(created_at);

COMMENT ON TABLE data_quality_snapshots IS 'Data quality snapshots for monitoring metric freshness and completeness';
COMMENT ON COLUMN data_quality_snapshots.metric_key IS 'Metric identifier (e.g., events_total, prices_spy, ml_outcomes_1d)';
COMMENT ON COLUMN data_quality_snapshots.scope IS 'Scope of metric (global, portfolio, watchlist)';
COMMENT ON COLUMN data_quality_snapshots.sample_count IS 'Number of records in this snapshot';
COMMENT ON COLUMN data_quality_snapshots.freshness_ts IS 'Timestamp of most recent data point';
COMMENT ON COLUMN data_quality_snapshots.source_job IS 'Job that generated this snapshot (e.g., fetch_prices, ml_learning_pipeline)';
COMMENT ON COLUMN data_quality_snapshots.quality_grade IS 'Quality grade: excellent, good, fair, stale';
COMMENT ON COLUMN data_quality_snapshots.summary_json IS 'Additional metadata (e.g., {"avg_age_hours": 2.5, "missing_tickers": []})';

-- ============================================================================
-- 2. CREATE TABLE: data_pipeline_runs
-- ============================================================================
-- Tracks job execution status, timing, and outcomes for monitoring and debugging.
-- Used to detect pipeline failures and surface alerts to ops team.

CREATE TABLE IF NOT EXISTS data_pipeline_runs (
    id SERIAL PRIMARY KEY,
    job_name VARCHAR NOT NULL,
    started_at TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    completed_at TIMESTAMP WITHOUT TIME ZONE,
    status VARCHAR NOT NULL,
    rows_written INTEGER,
    source_hash VARCHAR,
    error_blob TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW()
);

-- Create indexes for data_pipeline_runs
CREATE INDEX IF NOT EXISTS ix_data_pipeline_runs_id ON data_pipeline_runs(id);
CREATE INDEX IF NOT EXISTS ix_data_pipeline_runs_job_name ON data_pipeline_runs(job_name);
CREATE INDEX IF NOT EXISTS ix_data_pipeline_runs_status ON data_pipeline_runs(status);
CREATE INDEX IF NOT EXISTS ix_data_pipeline_runs_started_at ON data_pipeline_runs(started_at);

COMMENT ON TABLE data_pipeline_runs IS 'Pipeline execution logs for data jobs (ETL, scanners, backfills)';
COMMENT ON COLUMN data_pipeline_runs.job_name IS 'Job identifier (e.g., fetch_prices, ml_learning_pipeline, scanner_fda)';
COMMENT ON COLUMN data_pipeline_runs.started_at IS 'Job start timestamp';
COMMENT ON COLUMN data_pipeline_runs.completed_at IS 'Job completion timestamp';
COMMENT ON COLUMN data_pipeline_runs.status IS 'Job status: running, success, failure';
COMMENT ON COLUMN data_pipeline_runs.rows_written IS 'Number of records created/updated';
COMMENT ON COLUMN data_pipeline_runs.source_hash IS 'Hash of source data for change detection';
COMMENT ON COLUMN data_pipeline_runs.error_blob IS 'Error message/stack trace if failed';

-- ============================================================================
-- 3. CREATE TABLE: data_lineage_records
-- ============================================================================
-- Tracks source URLs and payloads for events, outcomes, prices, and models.
-- Used to trace back where data came from and verify data integrity.

CREATE TABLE IF NOT EXISTS data_lineage_records (
    id SERIAL PRIMARY KEY,
    metric_key VARCHAR NOT NULL,
    entity_id INTEGER NOT NULL,
    entity_type VARCHAR NOT NULL,
    source_url VARCHAR,
    payload_hash VARCHAR,
    observed_at TIMESTAMP WITHOUT TIME ZONE NOT NULL
);

-- Create indexes for data_lineage_records
CREATE INDEX IF NOT EXISTS ix_data_lineage_records_id ON data_lineage_records(id);
CREATE INDEX IF NOT EXISTS ix_data_lineage_records_metric_key ON data_lineage_records(metric_key);
CREATE INDEX IF NOT EXISTS ix_data_lineage_records_entity_type ON data_lineage_records(entity_type);
CREATE INDEX IF NOT EXISTS ix_data_lineage_records_observed_at ON data_lineage_records(observed_at);

COMMENT ON TABLE data_lineage_records IS 'Data lineage tracking for provenance and debugging';
COMMENT ON COLUMN data_lineage_records.metric_key IS 'Lineage event type (e.g., event_created, outcome_labeled, price_backfilled)';
COMMENT ON COLUMN data_lineage_records.entity_id IS 'ID of the created/updated entity';
COMMENT ON COLUMN data_lineage_records.entity_type IS 'Entity type: event, outcome, price, model';
COMMENT ON COLUMN data_lineage_records.source_url IS 'Original source URL (e.g., SEC filing URL, FDA announcement URL)';
COMMENT ON COLUMN data_lineage_records.payload_hash IS 'Hash of source payload for deduplication';
COMMENT ON COLUMN data_lineage_records.observed_at IS 'Timestamp when data was observed';

-- ============================================================================
-- 4. CREATE TABLE: audit_log_entries
-- ============================================================================
-- Records all data modifications for compliance, debugging, and security.
-- Includes diffs for updates and optional digital signatures for tamper detection.

CREATE TABLE IF NOT EXISTS audit_log_entries (
    id SERIAL PRIMARY KEY,
    entity_type VARCHAR NOT NULL,
    entity_id INTEGER NOT NULL,
    action VARCHAR NOT NULL,
    performed_by INTEGER,
    diff_json JSON,
    signature VARCHAR,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW(),
    CONSTRAINT fk_audit_log_entries_user FOREIGN KEY (performed_by) REFERENCES users(id)
);

-- Create indexes for audit_log_entries
CREATE INDEX IF NOT EXISTS ix_audit_log_entries_id ON audit_log_entries(id);
CREATE INDEX IF NOT EXISTS ix_audit_log_entries_entity_type ON audit_log_entries(entity_type);
CREATE INDEX IF NOT EXISTS ix_audit_log_entries_created_at ON audit_log_entries(created_at);
CREATE INDEX IF NOT EXISTS ix_audit_log_entries_performed_by ON audit_log_entries(performed_by);

COMMENT ON TABLE audit_log_entries IS 'Audit log for tracking entity mutations (create, update, delete)';
COMMENT ON COLUMN audit_log_entries.entity_type IS 'Entity type: event, user, portfolio, etc.';
COMMENT ON COLUMN audit_log_entries.entity_id IS 'ID of the affected entity';
COMMENT ON COLUMN audit_log_entries.action IS 'Action performed: create, update, delete';
COMMENT ON COLUMN audit_log_entries.performed_by IS 'User ID who performed the action (null for system actions)';
COMMENT ON COLUMN audit_log_entries.diff_json IS 'JSON diff for updates ({"field": {"old": x, "new": y}})';
COMMENT ON COLUMN audit_log_entries.signature IS 'Optional digital signature for tamper detection';

COMMIT;

-- ============================================================================
-- Migration complete!
-- ============================================================================
-- Tables created:
--   ✓ data_quality_snapshots
--   ✓ data_pipeline_runs
--   ✓ data_lineage_records
--   ✓ audit_log_entries
--
-- All indexes and foreign keys created successfully.
-- ============================================================================
