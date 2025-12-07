"""
Data Quality Validation Script

Runs comprehensive validation checks on data completeness, accuracy, ML metrics, and pipeline health.
Results are written to database and JSON report is generated.

Usage:
    python -m jobs.data_quality_validation
    python -m jobs.data_quality_validation --report-file=/tmp/validation_report.json
"""

import os
import sys
import json
import argparse
from datetime import datetime, timedelta, date
from typing import Dict, List, Any, Optional
from collections import defaultdict

from sqlalchemy import select, func, and_, desc

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from releaseradar.db.models import (
    Event,
    EventOutcome,
    PriceHistory,
    EventStats,
    DataPipelineRun,
    ModelRegistry,
)
from releaseradar.db.session import get_db_transaction
from releaseradar.services.quality_metrics import QualityMetricsService
from releaseradar.log_config import logger


class DataQualityValidator:
    """Comprehensive data quality validation."""
    
    def __init__(self):
        self.findings: List[Dict[str, Any]] = []
        self.passed_checks = 0
        self.failed_checks = 0
        self.warnings = 0
    
    def add_finding(
        self,
        category: str,
        check_name: str,
        status: str,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Add a validation finding."""
        finding = {
            "category": category,
            "check": check_name,
            "status": status,  # "pass", "fail", "warning"
            "message": message,
            "details": details or {},
            "timestamp": datetime.utcnow().isoformat(),
        }
        self.findings.append(finding)
        
        if status == "pass":
            self.passed_checks += 1
        elif status == "fail":
            self.failed_checks += 1
        elif status == "warning":
            self.warnings += 1
        
        logger.info(f"[{status.upper()}] {category} - {check_name}: {message}")
    
    def validate_data_completeness(self, db) -> None:
        """Validate data completeness checks."""
        logger.info("=== Validating Data Completeness ===")
        
        # Check 1: Event count hasn't dropped unexpectedly
        cutoff_7d = datetime.utcnow() - timedelta(days=7)
        cutoff_14d = datetime.utcnow() - timedelta(days=14)
        
        events_last_7d = db.execute(
            select(func.count(Event.id)).where(Event.created_at >= cutoff_7d)
        ).scalar() or 0
        
        events_prev_7d = db.execute(
            select(func.count(Event.id)).where(
                and_(Event.created_at >= cutoff_14d, Event.created_at < cutoff_7d)
            )
        ).scalar() or 0
        
        if events_prev_7d > 0:
            drop_pct = ((events_prev_7d - events_last_7d) / events_prev_7d) * 100
            if drop_pct > 10:
                self.add_finding(
                    "data_completeness",
                    "event_count_stability",
                    "fail",
                    f"Event count dropped by {drop_pct:.1f}% in last 7 days",
                    {"events_last_7d": events_last_7d, "events_prev_7d": events_prev_7d}
                )
            else:
                self.add_finding(
                    "data_completeness",
                    "event_count_stability",
                    "pass",
                    f"Event count stable (change: {drop_pct:+.1f}%)",
                    {"events_last_7d": events_last_7d, "events_prev_7d": events_prev_7d}
                )
        else:
            self.add_finding(
                "data_completeness",
                "event_count_stability",
                "warning",
                "Insufficient data to compare event counts",
                {"events_last_7d": events_last_7d, "events_prev_7d": events_prev_7d}
            )
        
        # Check 2: Price data gaps
        # Get all unique tickers from events
        result = db.execute(
            select(Event.ticker).distinct().where(Event.created_at >= cutoff_7d)
        )
        active_tickers = [row[0] for row in result]
        
        tickers_with_gaps = []
        for ticker in active_tickers[:50]:  # Sample first 50 tickers
            # Check if price data exists for last 7 days
            price_count = db.execute(
                select(func.count(PriceHistory.id)).where(
                    and_(
                        PriceHistory.ticker == ticker,
                        PriceHistory.date >= (datetime.utcnow() - timedelta(days=7)).date()
                    )
                )
            ).scalar() or 0
            
            if price_count < 3:  # Less than 3 trading days
                tickers_with_gaps.append(ticker)
        
        if len(tickers_with_gaps) > 10:
            self.add_finding(
                "data_completeness",
                "price_data_gaps",
                "fail",
                f"Found {len(tickers_with_gaps)} tickers with insufficient price data",
                {"tickers_with_gaps": tickers_with_gaps[:10]}
            )
        elif len(tickers_with_gaps) > 0:
            self.add_finding(
                "data_completeness",
                "price_data_gaps",
                "warning",
                f"Found {len(tickers_with_gaps)} tickers with insufficient price data",
                {"tickers_with_gaps": tickers_with_gaps}
            )
        else:
            self.add_finding(
                "data_completeness",
                "price_data_gaps",
                "pass",
                "No significant price data gaps detected",
                {"tickers_checked": len(active_tickers[:50])}
            )
        
        # Check 3: Outcome labels for recent events
        cutoff_30d = datetime.utcnow() - timedelta(days=30)
        cutoff_35d = datetime.utcnow() - timedelta(days=35)
        
        recent_events = db.execute(
            select(func.count(Event.id)).where(
                and_(Event.date >= cutoff_35d, Event.date < cutoff_30d)
            )
        ).scalar() or 0
        
        labeled_events = db.execute(
            select(func.count(EventOutcome.event_id.distinct())).where(
                EventOutcome.event_id.in_(
                    select(Event.id).where(
                        and_(Event.date >= cutoff_35d, Event.date < cutoff_30d)
                    )
                )
            )
        ).scalar() or 0
        
        if recent_events > 0:
            label_rate = (labeled_events / recent_events) * 100
            if label_rate < 50:
                self.add_finding(
                    "data_completeness",
                    "outcome_labeling",
                    "fail",
                    f"Only {label_rate:.1f}% of recent events have outcome labels",
                    {"recent_events": recent_events, "labeled_events": labeled_events}
                )
            elif label_rate < 80:
                self.add_finding(
                    "data_completeness",
                    "outcome_labeling",
                    "warning",
                    f"{label_rate:.1f}% of recent events have outcome labels",
                    {"recent_events": recent_events, "labeled_events": labeled_events}
                )
            else:
                self.add_finding(
                    "data_completeness",
                    "outcome_labeling",
                    "pass",
                    f"{label_rate:.1f}% of recent events have outcome labels",
                    {"recent_events": recent_events, "labeled_events": labeled_events}
                )
        else:
            self.add_finding(
                "data_completeness",
                "outcome_labeling",
                "warning",
                "No recent events to check for labeling",
                {"recent_events": 0}
            )
    
    def validate_data_accuracy(self, db) -> None:
        """Validate data accuracy checks."""
        logger.info("=== Validating Data Accuracy ===")
        
        # Check 1: Verify price data consistency (internal validation only)
        # Check that prices are within reasonable ranges and don't have outliers
        sample_tickers = db.execute(
            select(PriceHistory.ticker).distinct().limit(5)
        )
        sample_tickers = [row[0] for row in sample_tickers]
        
        price_outliers = []
        for ticker in sample_tickers:
            # Get recent prices for this ticker
            recent_prices = db.execute(
                select(PriceHistory).where(
                    PriceHistory.ticker == ticker
                ).order_by(desc(PriceHistory.date)).limit(30)
            ).scalars().all()
            
            if len(recent_prices) >= 5:
                # Check for outliers using simple statistical tests
                closes = [p.close for p in recent_prices]
                mean_price = sum(closes) / len(closes)
                
                # Check each price against mean (outliers are >50% away from mean)
                for price in recent_prices[:5]:  # Check last 5 prices
                    diff_pct = abs((price.close - mean_price) / mean_price) * 100
                    
                    if diff_pct > 50.0:  # More than 50% deviation from mean
                        price_outliers.append({
                            "ticker": ticker,
                            "date": price.date.isoformat(),
                            "price": price.close,
                            "mean": round(mean_price, 2),
                            "diff_pct": round(diff_pct, 2)
                        })
        
        if len(price_outliers) > 0:
            self.add_finding(
                "data_accuracy",
                "price_data_verification",
                "warning",
                f"Found {len(price_outliers)} potential price outliers",
                {"outliers": price_outliers}
            )
        else:
            self.add_finding(
                "data_accuracy",
                "price_data_verification",
                "pass",
                "Price data appears consistent (no major outliers detected)",
                {"tickers_checked": len(sample_tickers)}
            )
        
        # Check 2: Validate return_pct calculations
        # Sample 10 random outcomes and recalculate
        sample_outcomes = db.execute(
            select(EventOutcome).order_by(func.random()).limit(10)
        ).scalars().all()
        
        calc_errors = []
        for outcome in sample_outcomes:
            expected_return = ((outcome.price_after - outcome.price_before) / outcome.price_before) * 100
            
            # Allow for small floating point errors
            if abs(expected_return - outcome.return_pct_raw) > 0.01:
                calc_errors.append({
                    "outcome_id": outcome.id,
                    "stored_return": outcome.return_pct_raw,
                    "calculated_return": expected_return,
                    "diff": abs(expected_return - outcome.return_pct_raw)
                })
        
        if len(calc_errors) > 0:
            self.add_finding(
                "data_accuracy",
                "return_calculation",
                "fail",
                f"Found {len(calc_errors)} outcomes with incorrect return calculations",
                {"errors": calc_errors}
            )
        else:
            self.add_finding(
                "data_accuracy",
                "return_calculation",
                "pass",
                "Return calculations are accurate",
                {"outcomes_checked": len(sample_outcomes)}
            )
        
        # Check 3: Check for outliers
        outliers_1d = db.execute(
            select(func.count(EventOutcome.id)).where(
                and_(
                    EventOutcome.horizon == "1d",
                    func.abs(EventOutcome.return_pct) > 50
                )
            )
        ).scalar() or 0
        
        outliers_5d = db.execute(
            select(func.count(EventOutcome.id)).where(
                and_(
                    EventOutcome.horizon == "5d",
                    func.abs(EventOutcome.return_pct) > 100
                )
            )
        ).scalar() or 0
        
        total_outcomes = db.execute(
            select(func.count(EventOutcome.id))
        ).scalar() or 1
        
        outlier_rate = ((outliers_1d + outliers_5d) / total_outcomes) * 100
        
        if outlier_rate > 5:
            self.add_finding(
                "data_accuracy",
                "outlier_detection",
                "warning",
                f"High outlier rate: {outlier_rate:.2f}%",
                {"outliers_1d": outliers_1d, "outliers_5d": outliers_5d, "total": total_outcomes}
            )
        else:
            self.add_finding(
                "data_accuracy",
                "outlier_detection",
                "pass",
                f"Outlier rate acceptable: {outlier_rate:.2f}%",
                {"outliers_1d": outliers_1d, "outliers_5d": outliers_5d, "total": total_outcomes}
            )
    
    def validate_ml_metrics(self, db) -> None:
        """Validate ML metrics."""
        logger.info("=== Validating ML Metrics ===")
        
        # Check 1: Verify sample sizes in EventStats match actual query counts
        sample_stats = db.execute(
            select(EventStats).order_by(func.random()).limit(5)
        ).scalars().all()
        
        sample_size_errors = []
        for stat in sample_stats:
            # Count actual outcomes for this ticker/event_type
            actual_count = db.execute(
                select(func.count(EventOutcome.id)).where(
                    EventOutcome.event_id.in_(
                        select(Event.id).where(
                            and_(
                                Event.ticker == stat.ticker,
                                Event.event_type == stat.event_type
                            )
                        )
                    )
                )
            ).scalar() or 0
            
            # Divide by 3 horizons to get event count
            actual_event_count = actual_count // 3 if actual_count > 0 else 0
            
            if abs(actual_event_count - stat.sample_size) > 2:  # Allow for small discrepancies
                sample_size_errors.append({
                    "ticker": stat.ticker,
                    "event_type": stat.event_type,
                    "stored_sample_size": stat.sample_size,
                    "actual_sample_size": actual_event_count
                })
        
        if len(sample_size_errors) > 0:
            self.add_finding(
                "ml_metrics",
                "sample_size_validation",
                "warning",
                f"Found {len(sample_size_errors)} stats with incorrect sample sizes",
                {"errors": sample_size_errors}
            )
        else:
            self.add_finding(
                "ml_metrics",
                "sample_size_validation",
                "pass",
                "Sample sizes match query counts",
                {"stats_checked": len(sample_stats)}
            )
        
        # Check 2: Check if active models exist
        active_models = db.execute(
            select(func.count(ModelRegistry.id)).where(ModelRegistry.status == "active")
        ).scalar() or 0
        
        if active_models == 0:
            self.add_finding(
                "ml_metrics",
                "active_models",
                "warning",
                "No active models in registry",
                {"active_models": 0}
            )
        else:
            self.add_finding(
                "ml_metrics",
                "active_models",
                "pass",
                f"Found {active_models} active models",
                {"active_models": active_models}
            )
    
    def validate_pipeline_health(self, db) -> None:
        """Validate pipeline health."""
        logger.info("=== Validating Pipeline Health ===")
        
        cutoff_24h = datetime.utcnow() - timedelta(hours=24)
        
        # Check 1: Recent pipeline runs
        recent_runs = db.execute(
            select(func.count(DataPipelineRun.id)).where(
                DataPipelineRun.started_at >= cutoff_24h
            )
        ).scalar() or 0
        
        if recent_runs == 0:
            self.add_finding(
                "pipeline_health",
                "recent_runs",
                "fail",
                "No pipeline runs in last 24 hours",
                {"recent_runs": 0}
            )
        else:
            self.add_finding(
                "pipeline_health",
                "recent_runs",
                "pass",
                f"Found {recent_runs} pipeline runs in last 24 hours",
                {"recent_runs": recent_runs}
            )
        
        # Check 2: Jobs stuck in "running" status
        cutoff_1h = datetime.utcnow() - timedelta(hours=1)
        
        stuck_jobs = db.execute(
            select(DataPipelineRun).where(
                and_(
                    DataPipelineRun.status == "running",
                    DataPipelineRun.started_at < cutoff_1h
                )
            )
        ).scalars().all()
        
        if len(stuck_jobs) > 0:
            self.add_finding(
                "pipeline_health",
                "stuck_jobs",
                "fail",
                f"Found {len(stuck_jobs)} jobs stuck in 'running' status >1 hour",
                {"stuck_jobs": [{"job_name": j.job_name, "started_at": j.started_at.isoformat()} for j in stuck_jobs]}
            )
        else:
            self.add_finding(
                "pipeline_health",
                "stuck_jobs",
                "pass",
                "No jobs stuck in 'running' status",
                {"stuck_jobs": 0}
            )
        
        # Check 3: Error rates
        total_runs_24h = db.execute(
            select(func.count(DataPipelineRun.id)).where(
                DataPipelineRun.started_at >= cutoff_24h
            )
        ).scalar() or 1
        
        failed_runs_24h = db.execute(
            select(func.count(DataPipelineRun.id)).where(
                and_(
                    DataPipelineRun.started_at >= cutoff_24h,
                    DataPipelineRun.status == "failure"
                )
            )
        ).scalar() or 0
        
        error_rate = (failed_runs_24h / total_runs_24h) * 100
        
        if error_rate > 5:
            self.add_finding(
                "pipeline_health",
                "error_rate",
                "fail",
                f"High error rate: {error_rate:.1f}% in last 24 hours",
                {"total_runs": total_runs_24h, "failed_runs": failed_runs_24h}
            )
        elif error_rate > 2:
            self.add_finding(
                "pipeline_health",
                "error_rate",
                "warning",
                f"Elevated error rate: {error_rate:.1f}% in last 24 hours",
                {"total_runs": total_runs_24h, "failed_runs": failed_runs_24h}
            )
        else:
            self.add_finding(
                "pipeline_health",
                "error_rate",
                "pass",
                f"Low error rate: {error_rate:.1f}% in last 24 hours",
                {"total_runs": total_runs_24h, "failed_runs": failed_runs_24h}
            )
    
    def run_validation(self, db) -> Dict[str, Any]:
        """Run all validation checks."""
        logger.info("Starting data quality validation...")
        
        start_time = datetime.utcnow()
        
        try:
            self.validate_data_completeness(db)
            self.validate_data_accuracy(db)
            self.validate_ml_metrics(db)
            self.validate_pipeline_health(db)
            
            # Determine overall health
            if self.failed_checks > 0:
                overall_health = "critical"
            elif self.warnings > 2:
                overall_health = "warning"
            else:
                overall_health = "healthy"
            
            end_time = datetime.utcnow()
            runtime_seconds = (end_time - start_time).total_seconds()
            
            report = {
                "report_time": end_time.isoformat(),
                "runtime_seconds": runtime_seconds,
                "overall_health": overall_health,
                "summary": {
                    "total_checks": self.passed_checks + self.failed_checks + self.warnings,
                    "passed": self.passed_checks,
                    "failed": self.failed_checks,
                    "warnings": self.warnings,
                },
                "findings": self.findings,
            }
            
            logger.info(f"Validation complete: {overall_health} - "
                       f"{self.passed_checks} passed, {self.failed_checks} failed, {self.warnings} warnings")
            
            return report
            
        except Exception as e:
            logger.error(f"Validation failed with exception: {e}")
            raise


def main():
    """Entry point for validation script."""
    parser = argparse.ArgumentParser(description="Run data quality validation")
    parser.add_argument(
        "--report-file",
        type=str,
        default=None,
        help="Path to write JSON report (default: no file output)"
    )
    args = parser.parse_args()
    
    with get_db_transaction() as db:
        validator = DataQualityValidator()
        quality_service = QualityMetricsService(db)
        
        # Record pipeline run start
        started_at = datetime.utcnow()
        pipeline_run = quality_service.record_pipeline_run(
            job_name="data_quality_validation",
            started_at=started_at,
            status="running"
        )
        
        try:
            # Run validation
            report = validator.run_validation(db)
            
            # Write report to file if requested
            if args.report_file:
                with open(args.report_file, 'w') as f:
                    json.dump(report, f, indent=2)
                logger.info(f"Report written to {args.report_file}")
            
            # Record quality snapshot
            quality_service.record_quality_snapshot(
                metric_key="data_quality_validation",
                scope="global",
                sample_count=report["summary"]["total_checks"],
                freshness_ts=datetime.utcnow(),
                source_job="data_quality_validation",
                quality_grade=report["overall_health"],
                summary_json=report["summary"]
            )
            
            # Record audit log
            quality_service.record_audit_log(
                entity_type="validation_report",
                entity_id=pipeline_run.id,
                action="create",
                performed_by=None,
                diff_json={"report": report}
            )
            
            # Update pipeline run status
            quality_service.update_pipeline_run(
                run_id=pipeline_run.id,
                status="success",
                completed_at=datetime.utcnow(),
                rows_written=report["summary"]["total_checks"]
            )
            
            # Exit with appropriate code
            if report["overall_health"] == "critical":
                logger.error("Validation failed with critical issues")
                sys.exit(1)
            else:
                logger.info("Validation completed successfully")
                sys.exit(0)
        
        except Exception as e:
            logger.error(f"Validation script failed: {e}")
            
            # Rollback current transaction first
            db.rollback()
            
            # Update pipeline run as failure in a new transaction
            try:
                quality_service.update_pipeline_run(
                    run_id=pipeline_run.id,
                    status="failure",
                    completed_at=datetime.utcnow(),
                    error_blob=str(e)
                )
                db.commit()
            except Exception as update_error:
                logger.error(f"Failed to update pipeline run status: {update_error}")
            
            sys.exit(1)


if __name__ == "__main__":
    main()
