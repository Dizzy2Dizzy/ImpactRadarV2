-- ============================================================================
-- Migration Rollback: 001_add_data_quality_tables
-- Description: Removes data quality monitoring tables
-- Date: 2025-11-21
-- ============================================================================
-- WARNING: This script will DROP all data quality tables and their data.
-- Only run this if you need to reverse the migration.
-- ============================================================================

BEGIN;

-- Drop tables in reverse order to respect foreign key constraints
-- (audit_log_entries has FK to users, so drop it first)

-- ============================================================================
-- 4. DROP TABLE: audit_log_entries
-- ============================================================================
DROP TABLE IF EXISTS audit_log_entries CASCADE;

-- ============================================================================
-- 3. DROP TABLE: data_lineage_records
-- ============================================================================
DROP TABLE IF EXISTS data_lineage_records CASCADE;

-- ============================================================================
-- 2. DROP TABLE: data_pipeline_runs
-- ============================================================================
DROP TABLE IF EXISTS data_pipeline_runs CASCADE;

-- ============================================================================
-- 1. DROP TABLE: data_quality_snapshots
-- ============================================================================
DROP TABLE IF EXISTS data_quality_snapshots CASCADE;

COMMIT;

-- ============================================================================
-- Rollback complete!
-- ============================================================================
-- Tables removed:
--   ✓ audit_log_entries
--   ✓ data_lineage_records
--   ✓ data_pipeline_runs
--   ✓ data_quality_snapshots
--
-- All associated indexes and constraints have been removed.
-- ============================================================================
