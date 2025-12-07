"""
Populate Data Quality Tables with Sample Data

Populates all 4 data quality tables (snapshots, pipeline runs, lineage, audit log)
with realistic sample data for testing and demonstration.

Usage:
    cd backend
    python3 scripts/populate_quality_data.py
"""

import os
import sys
from datetime import datetime, timedelta
import hashlib
import random

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from releaseradar.db.session import get_db_transaction
from releaseradar.services.quality_metrics import QualityMetricsService
from releaseradar.log_config import logger


def generate_payload_hash(data: str) -> str:
    """Generate hash for payload."""
    return hashlib.sha256(data.encode()).hexdigest()[:16]


def populate_quality_snapshots(service: QualityMetricsService, db) -> int:
    """
    Populate DataQualitySnapshot table with sample metrics.
    
    Returns:
        Number of records inserted
    """
    logger.info("=== Populating DataQualitySnapshot table ===")
    
    now = datetime.utcnow()
    
    snapshots = [
        # Event metrics
        {
            "metric_key": "labeled_events_count",
            "scope": "global",
            "sample_count": 1247,
            "freshness_ts": now - timedelta(hours=2),
            "source_job": "ml_learning_pipeline",
            "quality_grade": "excellent",
            "summary_json": {
                "avg_age_hours": 2.3,
                "labeled_1d": 450,
                "labeled_5d": 380,
                "labeled_20d": 417
            }
        },
        {
            "metric_key": "events_total",
            "scope": "global",
            "sample_count": 3456,
            "freshness_ts": now - timedelta(hours=1),
            "source_job": "fetch_prices",
            "quality_grade": "excellent",
            "summary_json": {
                "avg_age_hours": 1.0,
                "events_last_hour": 23,
                "events_last_day": 456
            }
        },
        # ML accuracy metrics
        {
            "metric_key": "accuracy_1d",
            "scope": "global",
            "sample_count": 856,
            "freshness_ts": now - timedelta(hours=6),
            "source_job": "ml_learning_pipeline",
            "quality_grade": "good",
            "summary_json": {
                "directional_accuracy": 0.687,
                "mae": 12.4,
                "rmse": 18.7
            }
        },
        {
            "metric_key": "accuracy_5d",
            "scope": "global",
            "sample_count": 734,
            "freshness_ts": now - timedelta(hours=6),
            "source_job": "ml_learning_pipeline",
            "quality_grade": "good",
            "summary_json": {
                "directional_accuracy": 0.623,
                "mae": 18.9,
                "rmse": 27.3
            }
        },
        {
            "metric_key": "calibration_error_1d",
            "scope": "global",
            "sample_count": 856,
            "freshness_ts": now - timedelta(hours=6),
            "source_job": "ml_learning_pipeline",
            "quality_grade": "good",
            "summary_json": {
                "mean_calibration_error": 0.087,
                "bins": 10,
                "underconfident_bins": 3,
                "overconfident_bins": 2
            }
        },
        # Price data metrics
        {
            "metric_key": "prices_spy",
            "scope": "global",
            "sample_count": 252,
            "freshness_ts": now - timedelta(hours=16),
            "source_job": "fetch_prices",
            "quality_grade": "fair",
            "summary_json": {
                "avg_age_hours": 16.2,
                "missing_days": 0,
                "data_source": "yahoo"
            }
        },
        # Watchlist metrics
        {
            "metric_key": "watchlist_coverage",
            "scope": "watchlist",
            "sample_count": 47,
            "freshness_ts": now - timedelta(hours=3),
            "source_job": "fetch_prices",
            "quality_grade": "excellent",
            "summary_json": {
                "tickers_tracked": 47,
                "tickers_with_events_24h": 8,
                "tickers_with_prices_today": 45
            }
        },
        # Portfolio metrics
        {
            "metric_key": "portfolio_exposure",
            "scope": "portfolio",
            "sample_count": 23,
            "freshness_ts": now - timedelta(hours=4),
            "source_job": "portfolio_sync",
            "quality_grade": "good",
            "summary_json": {
                "portfolios_tracked": 12,
                "total_positions": 23,
                "exposure_checks_passed": 21
            }
        },
        # Scanner health
        {
            "metric_key": "scanner_health",
            "scope": "global",
            "sample_count": 8,
            "freshness_ts": now - timedelta(hours=1),
            "source_job": "run_scanners",
            "quality_grade": "excellent",
            "summary_json": {
                "scanners_active": 8,
                "scanners_failed": 0,
                "events_detected_24h": 156
            }
        },
        # Outcome labeling
        {
            "metric_key": "outcomes_labeled",
            "scope": "global",
            "sample_count": 892,
            "freshness_ts": now - timedelta(hours=12),
            "source_job": "label_outcomes",
            "quality_grade": "good",
            "summary_json": {
                "outcomes_1d": 345,
                "outcomes_5d": 287,
                "outcomes_20d": 260,
                "missing_price_data": 12
            }
        },
    ]
    
    count = 0
    for snapshot_data in snapshots:
        try:
            service.record_quality_snapshot(**snapshot_data)
            count += 1
            logger.info(f"✓ Inserted snapshot: {snapshot_data['metric_key']} ({snapshot_data['quality_grade']})")
        except Exception as e:
            logger.error(f"✗ Failed to insert snapshot {snapshot_data['metric_key']}: {e}")
    
    logger.info(f"Inserted {count} quality snapshots")
    return count


def populate_pipeline_runs(service: QualityMetricsService, db) -> int:
    """
    Populate DataPipelineRun table with sample job executions.
    
    Returns:
        Number of records inserted
    """
    logger.info("=== Populating DataPipelineRun table ===")
    
    now = datetime.utcnow()
    
    runs = [
        # Successful runs
        {
            "job_name": "fetch_prices",
            "started_at": now - timedelta(hours=2),
            "status": "success",
            "completed_at": now - timedelta(hours=2) + timedelta(minutes=8),
            "rows_written": 2456,
            "source_hash": generate_payload_hash("prices_2024_11_21_run_1"),
        },
        {
            "job_name": "fetch_prices",
            "started_at": now - timedelta(hours=26),
            "status": "success",
            "completed_at": now - timedelta(hours=26) + timedelta(minutes=7),
            "rows_written": 2398,
            "source_hash": generate_payload_hash("prices_2024_11_20_run_1"),
        },
        {
            "job_name": "label_outcomes",
            "started_at": now - timedelta(hours=6),
            "status": "success",
            "completed_at": now - timedelta(hours=6) + timedelta(minutes=14),
            "rows_written": 127,
            "source_hash": generate_payload_hash("outcomes_2024_11_21_run_1"),
        },
        {
            "job_name": "ml_learning_pipeline",
            "started_at": now - timedelta(hours=12),
            "status": "success",
            "completed_at": now - timedelta(hours=12) + timedelta(minutes=45),
            "rows_written": 892,
            "source_hash": generate_payload_hash("ml_2024_11_21_run_1"),
        },
        {
            "job_name": "run_scanners",
            "started_at": now - timedelta(hours=1),
            "status": "success",
            "completed_at": now - timedelta(hours=1) + timedelta(minutes=3),
            "rows_written": 23,
            "source_hash": generate_payload_hash("scanners_2024_11_21_run_1"),
        },
        {
            "job_name": "data_quality_validation",
            "started_at": now - timedelta(hours=24),
            "status": "success",
            "completed_at": now - timedelta(hours=24) + timedelta(minutes=2),
            "rows_written": 0,
            "source_hash": None,
        },
        # Failed runs
        {
            "job_name": "fetch_prices",
            "started_at": now - timedelta(hours=50),
            "status": "failure",
            "completed_at": now - timedelta(hours=50) + timedelta(minutes=1),
            "rows_written": 0,
            "source_hash": None,
            "error_blob": "ConnectionError: Failed to connect to Yahoo Finance API. Timeout after 30s. Check network connectivity and API status."
        },
        {
            "job_name": "label_outcomes",
            "started_at": now - timedelta(hours=30),
            "status": "failure",
            "completed_at": now - timedelta(hours=30) + timedelta(seconds=45),
            "rows_written": 34,
            "source_hash": generate_payload_hash("outcomes_2024_11_20_run_1"),
            "error_blob": "ValueError: Missing price data for ticker AAPL on date 2024-11-19. Cannot compute outcome for event #12456."
        },
        # Running job
        {
            "job_name": "ml_learning_pipeline",
            "started_at": now - timedelta(minutes=15),
            "status": "running",
            "completed_at": None,
            "rows_written": None,
            "source_hash": None,
        },
        # Recent successful runs
        {
            "job_name": "run_scanners",
            "started_at": now - timedelta(hours=25),
            "status": "success",
            "completed_at": now - timedelta(hours=25) + timedelta(minutes=4),
            "rows_written": 34,
            "source_hash": generate_payload_hash("scanners_2024_11_20_run_1"),
        },
    ]
    
    count = 0
    for run_data in runs:
        try:
            service.record_pipeline_run(**run_data)
            count += 1
            status_emoji = "✓" if run_data["status"] == "success" else ("✗" if run_data["status"] == "failure" else "⏳")
            logger.info(f"{status_emoji} Inserted pipeline run: {run_data['job_name']} ({run_data['status']})")
        except Exception as e:
            logger.error(f"✗ Failed to insert pipeline run {run_data['job_name']}: {e}")
    
    logger.info(f"Inserted {count} pipeline runs")
    return count


def populate_lineage_records(service: QualityMetricsService, db) -> int:
    """
    Populate DataLineageRecord table with sample lineage data.
    
    Returns:
        Number of records inserted
    """
    logger.info("=== Populating DataLineageRecord table ===")
    
    now = datetime.utcnow()
    
    records = [
        {
            "metric_key": "event_created",
            "entity_id": 12456,
            "entity_type": "event",
            "source_url": "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193&type=8-K",
            "payload_hash": generate_payload_hash("sec_8k_aapl_2024_11_20"),
            "observed_at": now - timedelta(hours=3),
        },
        {
            "metric_key": "event_created",
            "entity_id": 12457,
            "entity_type": "event",
            "source_url": "https://www.fda.gov/news-events/press-announcements/fda-approves-new-treatment-diabetes",
            "payload_hash": generate_payload_hash("fda_approval_novo_2024_11_20"),
            "observed_at": now - timedelta(hours=5),
        },
        {
            "metric_key": "outcome_labeled",
            "entity_id": 8934,
            "entity_type": "outcome",
            "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/AAPL",
            "payload_hash": generate_payload_hash("yahoo_prices_aapl_2024_11_20"),
            "observed_at": now - timedelta(hours=6),
        },
        {
            "metric_key": "outcome_labeled",
            "entity_id": 8935,
            "entity_type": "outcome",
            "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/MSFT",
            "payload_hash": generate_payload_hash("yahoo_prices_msft_2024_11_20"),
            "observed_at": now - timedelta(hours=6),
        },
        {
            "metric_key": "price_backfilled",
            "entity_id": 45678,
            "entity_type": "price",
            "source_url": "https://query1.finance.yahoo.com/v8/finance/chart/TSLA",
            "payload_hash": generate_payload_hash("yahoo_prices_tsla_2024_11_20"),
            "observed_at": now - timedelta(hours=2),
        },
        {
            "metric_key": "model_trained",
            "entity_id": 3,
            "entity_type": "model",
            "source_url": None,
            "payload_hash": generate_payload_hash("xgboost_impact_1d_v1.0.2"),
            "observed_at": now - timedelta(hours=12),
        },
        {
            "metric_key": "event_created",
            "entity_id": 12458,
            "entity_type": "event",
            "source_url": "https://www.businesswire.com/news/home/20241120/en/Company-Announces-Earnings",
            "payload_hash": generate_payload_hash("earnings_nvda_2024_11_20"),
            "observed_at": now - timedelta(hours=8),
        },
    ]
    
    count = 0
    for record_data in records:
        try:
            service.record_lineage(**record_data)
            count += 1
            logger.info(f"✓ Inserted lineage: {record_data['metric_key']} → {record_data['entity_type']}#{record_data['entity_id']}")
        except Exception as e:
            logger.error(f"✗ Failed to insert lineage record: {e}")
    
    logger.info(f"Inserted {count} lineage records")
    return count


def populate_audit_log(service: QualityMetricsService, db) -> int:
    """
    Populate AuditLogEntry table with sample audit events.
    
    Returns:
        Number of records inserted
    """
    logger.info("=== Populating AuditLogEntry table ===")
    
    now = datetime.utcnow()
    
    entries = [
        # Event creation
        {
            "entity_type": "event",
            "entity_id": 12456,
            "action": "create",
            "performed_by": None,  # System
            "diff_json": None,
        },
        {
            "entity_type": "event",
            "entity_id": 12457,
            "action": "create",
            "performed_by": None,  # System
            "diff_json": None,
        },
        # Event updates
        {
            "entity_type": "event",
            "entity_id": 12456,
            "action": "update",
            "performed_by": None,  # System (ML scoring)
            "diff_json": {
                "ml_adjusted_score": {"old": None, "new": 78},
                "ml_confidence": {"old": None, "new": 0.82},
                "ml_model_version": {"old": None, "new": "xgboost_impact_1d_1.0.2"}
            },
        },
        # User actions
        {
            "entity_type": "user",
            "entity_id": 1,
            "action": "update",
            "performed_by": 1,
            "diff_json": {
                "plan": {"old": "free", "new": "pro"}
            },
        },
        {
            "entity_type": "watchlist",
            "entity_id": 123,
            "action": "create",
            "performed_by": 1,
            "diff_json": None,
        },
        # Outcome labeling
        {
            "entity_type": "outcome_labeling",
            "entity_id": 8934,
            "action": "create",
            "performed_by": None,  # System
            "diff_json": None,
        },
        {
            "entity_type": "outcome_labeling",
            "entity_id": 8935,
            "action": "create",
            "performed_by": None,  # System
            "diff_json": None,
        },
        # Alert configuration
        {
            "entity_type": "alert",
            "entity_id": 45,
            "action": "create",
            "performed_by": 1,
            "diff_json": None,
        },
        {
            "entity_type": "alert",
            "entity_id": 45,
            "action": "update",
            "performed_by": 1,
            "diff_json": {
                "min_score": {"old": 70, "new": 80},
                "active": {"old": True, "new": False}
            },
        },
        # Portfolio management
        {
            "entity_type": "portfolio",
            "entity_id": 7,
            "action": "create",
            "performed_by": 2,
            "diff_json": None,
        },
    ]
    
    count = 0
    for entry_data in entries:
        try:
            service.record_audit_entry(**entry_data)
            count += 1
            action_emoji = {"create": "➕", "update": "✏️", "delete": "🗑️"}.get(entry_data["action"], "•")
            user_str = f"user#{entry_data['performed_by']}" if entry_data['performed_by'] else "system"
            logger.info(f"{action_emoji} Inserted audit: {entry_data['action']} {entry_data['entity_type']}#{entry_data['entity_id']} by {user_str}")
        except Exception as e:
            logger.error(f"✗ Failed to insert audit entry: {e}")
    
    logger.info(f"Inserted {count} audit log entries")
    return count


def main():
    """Main execution function."""
    logger.info("=" * 60)
    logger.info("POPULATING DATA QUALITY TABLES")
    logger.info("=" * 60)
    
    try:
        with get_db_transaction() as db:
            service = QualityMetricsService(db)
            
            # Populate all tables
            snapshot_count = populate_quality_snapshots(service, db)
            pipeline_count = populate_pipeline_runs(service, db)
            lineage_count = populate_lineage_records(service, db)
            audit_count = populate_audit_log(service, db)
            
            # Summary
            logger.info("=" * 60)
            logger.info("POPULATION SUMMARY")
            logger.info("=" * 60)
            logger.info(f"✓ DataQualitySnapshot:    {snapshot_count} records")
            logger.info(f"✓ DataPipelineRun:        {pipeline_count} records")
            logger.info(f"✓ DataLineageRecord:      {lineage_count} records")
            logger.info(f"✓ AuditLogEntry:          {audit_count} records")
            logger.info(f"✓ TOTAL:                  {snapshot_count + pipeline_count + lineage_count + audit_count} records")
            logger.info("=" * 60)
            logger.info("✓ SUCCESS: All data quality tables populated!")
            logger.info("=" * 60)
            
            return 0
            
    except Exception as e:
        logger.error(f"✗ FAILED TO POPULATE DATA: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
