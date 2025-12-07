"""
Quality Metrics Service - Data quality monitoring and validation.

Provides methods for tracking data freshness, pipeline health, lineage, and audit logs.
Used by API endpoints and data jobs to monitor data quality and surface issues.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from sqlalchemy import select, func, desc, and_
from sqlalchemy.orm import Session

from releaseradar.db.models import (
    DataQualitySnapshot,
    DataPipelineRun,
    DataLineageRecord,
    AuditLogEntry,
    Event,
    EventOutcome,
    PriceHistory,
)
from releaseradar.db.session import get_db_context
from releaseradar.log_config import logger
import json


class QualityMetricsService:
    """Service for tracking and querying data quality metrics."""
    
    def __init__(self, db: Optional[Session] = None):
        """
        Initialize quality metrics service.
        
        Args:
            db: Optional database session (if None, uses context manager)
        """
        self.db = db
        self._owns_session = db is None
    
    def _get_db(self) -> Session:
        """Get database session."""
        if self.db:
            return self.db
        return get_db_context().__enter__()
    
    def get_freshness_indicators(
        self,
        scope: Optional[str] = None,
        metric_keys: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get freshness indicators for all metrics or specific metrics.
        
        Args:
            scope: Filter by scope ("global", "portfolio", "watchlist")
            metric_keys: Filter by specific metric keys
            
        Returns:
            List of freshness indicator dicts with metric_key, scope, sample_count,
            freshness_ts, quality_grade, and summary_json
        """
        db = self._get_db()
        
        try:
            # Use window function to get latest snapshot per metric_key
            # This works with both PostgreSQL and SQLite
            from sqlalchemy import func as sa_func
            
            # Create subquery that ranks snapshots by created_at DESC within each metric_key
            subq = (
                select(
                    DataQualitySnapshot,
                    sa_func.row_number().over(
                        partition_by=DataQualitySnapshot.metric_key,
                        order_by=desc(DataQualitySnapshot.created_at)
                    ).label('rn')
                )
            )
            
            if scope:
                subq = subq.where(DataQualitySnapshot.scope == scope)
            
            if metric_keys:
                subq = subq.where(DataQualitySnapshot.metric_key.in_(metric_keys))
            
            subq = subq.subquery()
            
            # Select only rows with rn=1 (latest for each metric_key)
            query = (
                select(
                    subq.c.id,
                    subq.c.metric_key,
                    subq.c.scope,
                    subq.c.sample_count,
                    subq.c.freshness_ts,
                    subq.c.source_job,
                    subq.c.quality_grade,
                    subq.c.summary_json,
                    subq.c.created_at
                )
                .where(subq.c.rn == 1)
            )
            
            rows = db.execute(query).all()
            
            # Convert to dict format
            results = []
            for row in rows:
                results.append({
                    "metric_key": row.metric_key,
                    "scope": row.scope,
                    "sample_count": row.sample_count,
                    "freshness_ts": row.freshness_ts.isoformat(),
                    "source_job": row.source_job,
                    "quality_grade": row.quality_grade,
                    "summary": row.summary_json or {},
                    "recorded_at": row.created_at.isoformat(),
                })
            
            return results
            
        finally:
            if self._owns_session:
                db.close()
    
    def get_pipeline_health(
        self,
        job_name: Optional[str] = None,
        hours_back: int = 24
    ) -> Dict[str, Any]:
        """
        Get pipeline health status and success/failure rates.
        
        Args:
            job_name: Filter by specific job (None = all jobs)
            hours_back: Look back this many hours for health metrics
            
        Returns:
            Dict with job stats including success rate, avg runtime, recent failures
        """
        db = self._get_db()
        
        try:
            cutoff = datetime.utcnow() - timedelta(hours=hours_back)
            
            query = (
                select(DataPipelineRun)
                .where(DataPipelineRun.started_at >= cutoff)
                .order_by(desc(DataPipelineRun.started_at))
            )
            
            if job_name:
                query = query.where(DataPipelineRun.job_name == job_name)
            
            runs = db.execute(query).scalars().all()
            
            # If no recent runs, try fetching all historical runs (last 30 days max)
            if not runs:
                extended_cutoff = datetime.utcnow() - timedelta(days=30)
                extended_query = (
                    select(DataPipelineRun)
                    .where(DataPipelineRun.started_at >= extended_cutoff)
                    .order_by(desc(DataPipelineRun.started_at))
                    .limit(100)
                )
                if job_name:
                    extended_query = extended_query.where(DataPipelineRun.job_name == job_name)
                runs = db.execute(extended_query).scalars().all()
            
            if not runs:
                return {
                    "total_runs": 0,
                    "success_rate": 0.0,
                    "avg_runtime_seconds": 0.0,
                    "recent_failures": [],
                    "jobs": {},
                }
            
            # Compute aggregate stats
            total = len(runs)
            successful = sum(1 for r in runs if r.status == "success")
            success_rate = (successful / total * 100) if total > 0 else 0.0
            
            # Compute avg runtime (only for completed runs)
            runtimes = []
            for run in runs:
                if run.completed_at and run.status in ["success", "failure"]:
                    runtime = (run.completed_at - run.started_at).total_seconds()
                    runtimes.append(runtime)
            
            avg_runtime = sum(runtimes) / len(runtimes) if runtimes else 0.0
            
            # Get recent failures
            failures = [
                {
                    "job_name": r.job_name,
                    "started_at": r.started_at.isoformat(),
                    "error": r.error_blob[:200] if r.error_blob else None,
                }
                for r in runs
                if r.status == "failure"
            ][:10]  # Last 10 failures
            
            # Group by job_name
            jobs_stats: Dict[str, Dict[str, Any]] = {}
            job_runs: Dict[str, list] = {}  # Track all runs per job for calculating stats
            
            for run in runs:
                job = run.job_name
                if job not in jobs_stats:
                    jobs_stats[job] = {
                        "total_runs": 0,
                        "success_count": 0,
                        "failure": 0,
                        "running": 0,
                        "last_run": None,
                        "last_success": None,
                        "last_status": None,
                        "runtimes": [],  # For calculating avg_runtime
                        "recent_runs": [],  # For trend chart
                    }
                    job_runs[job] = []
                
                jobs_stats[job]["total_runs"] += 1
                if run.status == "success":
                    jobs_stats[job]["success_count"] += 1
                jobs_stats[job][run.status] = jobs_stats[job].get(run.status, 0) + 1
                
                # Track last run and last success
                if not jobs_stats[job]["last_run"]:
                    jobs_stats[job]["last_run"] = run.started_at.isoformat()
                    jobs_stats[job]["last_status"] = run.status
                
                if run.status == "success" and not jobs_stats[job]["last_success"]:
                    jobs_stats[job]["last_success"] = run.started_at.isoformat()
                
                # Calculate runtime for this run
                if run.completed_at and run.status in ["success", "failure"]:
                    runtime = (run.completed_at - run.started_at).total_seconds()
                    jobs_stats[job]["runtimes"].append(runtime)
                    # Store recent runs for trend chart (last 10)
                    jobs_stats[job]["recent_runs"].append({
                        "duration": round(runtime, 1),
                        "timestamp": run.started_at.isoformat(),
                    })
                
                job_runs[job].append(run)
            
            # Calculate avg_runtime for each job and limit recent_runs
            for job in jobs_stats:
                runtimes = jobs_stats[job]["runtimes"]
                if runtimes:
                    jobs_stats[job]["avg_runtime"] = round(sum(runtimes) / len(runtimes), 2)
                else:
                    jobs_stats[job]["avg_runtime"] = 0.0
                
                # Keep only last 10 runs for trends
                jobs_stats[job]["recent_runs"] = jobs_stats[job]["recent_runs"][:10]
                
                # Remove temporary runtimes list
                del jobs_stats[job]["runtimes"]
            
            return {
                "total_runs": total,
                "success_rate": round(success_rate, 2),
                "avg_runtime_seconds": round(avg_runtime, 2),
                "recent_failures": failures,
                "jobs": jobs_stats,
            }
            
        finally:
            if self._owns_session:
                db.close()
    
    def get_metric_lineage(
        self,
        metric_key: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get lineage records for a specific metric key.
        
        Args:
            metric_key: Metric key to query (e.g., "event_created", "outcome_labeled")
            limit: Maximum records to return
            
        Returns:
            List of lineage records with entity info and source URLs
        """
        db = self._get_db()
        
        try:
            query = (
                select(DataLineageRecord)
                .where(DataLineageRecord.metric_key == metric_key)
                .order_by(desc(DataLineageRecord.observed_at))
                .limit(limit)
            )
            
            records = db.execute(query).scalars().all()
            
            return [
                {
                    "metric_key": rec.metric_key,
                    "entity_id": rec.entity_id,
                    "entity_type": rec.entity_type,
                    "source_url": rec.source_url,
                    "payload_hash": rec.payload_hash,
                    "observed_at": rec.observed_at.isoformat(),
                }
                for rec in records
            ]
            
        finally:
            if self._owns_session:
                db.close()
    
    def _get_lineage_mapping(self, metric_key: str) -> List[str]:
        """
        Map freshness metric keys to actual lineage record keys.
        Some metrics are derived from underlying data sources.
        """
        mappings = {
            "accuracy_1d": ["outcome_labeled", "event_created"],
            "accuracy_5d": ["outcome_labeled", "event_created"],
            "calibration_error_1d": ["outcome_labeled", "event_created"],
            "labeled_events_count": ["outcome_labeled"],
            "outcomes_labeled": ["outcome_labeled"],
            "ml_predictions": ["ml_predictions", "event_created"],
            "scanner_health": ["event_created"],
            "watchlist_coverage": ["companies_tracked"],
            "portfolio_exposure": ["event_created"],
            "data_quality_validation": ["event_created", "companies_tracked"],
        }
        return mappings.get(metric_key, [metric_key])

    def get_metric_lineage_detail(
        self,
        metric_key: str
    ) -> Dict[str, Any]:
        """
        Get detailed lineage data with aggregated source events, outcomes, and prices.
        
        Args:
            metric_key: Metric key to query (e.g., "event_created", "outcome_labeled")
            
        Returns:
            Dict with metric_key, metric_name, source_events, outcomes, price_history,
            payload_hash, generated_at, and total_events
        """
        db = self._get_db()
        
        try:
            # Map to actual lineage keys if needed
            lineage_keys = self._get_lineage_mapping(metric_key)
            
            # Try each mapped key until we find records
            lineage_records = []
            for lkey in lineage_keys:
                query = (
                    select(DataLineageRecord)
                    .where(DataLineageRecord.metric_key == lkey)
                    .order_by(desc(DataLineageRecord.observed_at))
                    .limit(100)
                )
                records = db.execute(query).scalars().all()
                if records:
                    lineage_records = records
                    break
            
            # If still no lineage records, try to get data directly from events
            if not lineage_records:
                return self._get_fallback_lineage_from_events(db, metric_key)
            
            # Use first record's metadata for top-level fields
            first_record = lineage_records[0]
            payload_hash = first_record.payload_hash
            generated_at = first_record.observed_at.isoformat()
            
            # Generate human-readable metric name
            metric_name = metric_key.replace("_", " ").title()
            
            # Collect entity IDs from lineage records by type
            # Note: entity_id is stored as text in DataLineageRecord, so we need type conversion
            event_ids = set()
            outcome_ids = set()
            
            for rec in lineage_records:
                if not rec.entity_type or not rec.entity_id:
                    continue
                entity_type_lower = rec.entity_type.lower()
                try:
                    entity_id_int = int(rec.entity_id)
                    if entity_type_lower == "event":
                        event_ids.add(entity_id_int)
                    elif entity_type_lower == "outcome":
                        outcome_ids.add(entity_id_int)
                except (ValueError, TypeError):
                    continue
            
            # Always resolve outcome-type lineage to associated events (merge with any event IDs)
            if outcome_ids:
                # Get events that have outcomes with these IDs (now using integer IDs)
                outcomes_for_events = (
                    select(EventOutcome.event_id)
                    .where(EventOutcome.id.in_(list(outcome_ids)))
                    .distinct()
                )
                outcome_event_ids = db.execute(outcomes_for_events).scalars().all()
                event_ids.update(outcome_event_ids)
            
            # If still no events after resolving both event and outcome lineage, fallback to recent outcomes
            if not event_ids:
                # Fix: Use subquery to get distinct event IDs from recent outcomes
                # The issue was DISTINCT with ORDER BY on different columns
                recent_outcomes_query = (
                    select(EventOutcome.event_id)
                    .distinct()
                    .order_by(desc(EventOutcome.event_id))
                    .limit(50)
                )
                recent_event_ids = db.execute(recent_outcomes_query).scalars().all()
                event_ids.update(recent_event_ids)
            
            source_events = []
            outcomes = []
            price_history = []
            tickers_set = set()
            event_dates = []
            
            # Query events if we have event IDs
            event_ids_list = list(event_ids)
            if event_ids_list:
                events_query = (
                    select(Event)
                    .where(Event.id.in_(event_ids_list))
                    .order_by(desc(Event.date))
                )
                events = db.execute(events_query).scalars().all()
                
                # Build source_events list and collect dates
                for event in events:
                    tickers_set.add(event.ticker)
                    if event.date:
                        event_dates.append(event.date)
                    source_events.append({
                        "ticker": event.ticker,
                        "event_type": event.event_type,
                        "date": event.date.isoformat() if event.date else "",
                        "source_url": event.source_url or "",
                        "event_id": event.id,
                        "title": event.title or "",
                    })
                
                # Query outcomes for these events
                outcomes_query = (
                    select(EventOutcome)
                    .where(EventOutcome.event_id.in_(event_ids_list))
                    .order_by(EventOutcome.horizon)
                )
                event_outcomes = db.execute(outcomes_query).scalars().all()
                
                # Map EventOutcome fields directly to frontend (no fabrication)
                for outcome in event_outcomes:
                    outcome_dict = {
                        "horizon": outcome.horizon,
                        "return_pct": round(outcome.return_pct, 2) if outcome.return_pct is not None else None,
                        "return_pct_raw": round(outcome.return_pct_raw, 2) if outcome.return_pct_raw is not None else None,
                        "abs_return_pct": round(outcome.abs_return_pct, 2) if outcome.abs_return_pct is not None else None,
                        "direction_correct": outcome.direction_correct,
                        "has_benchmark_data": outcome.has_benchmark_data or False,
                    }
                    
                    outcomes.append(outcome_dict)
            
            # Query price history based on actual event dates
            if tickers_set and event_dates:
                # Find earliest and latest event dates
                min_event_date = min(event_dates)
                max_event_date = max(event_dates)
                
                # Query 30 days before earliest event to 30 days after latest event
                start_date = min_event_date - timedelta(days=30)
                end_date = max_event_date + timedelta(days=30)
                
                # BUG FIX: Remove global LIMIT to ensure all tickers get price data
                # Date range filtering provides natural bounds
                prices_query = (
                    select(PriceHistory)
                    .where(
                        and_(
                            PriceHistory.ticker.in_(list(tickers_set)),
                            PriceHistory.date >= start_date,
                            PriceHistory.date <= end_date
                        )
                    )
                    .order_by(PriceHistory.ticker, PriceHistory.date)
                )
                prices = db.execute(prices_query).scalars().all()
                
                # Build price_history list
                for price in prices:
                    price_history.append({
                        "date": price.date.isoformat(),
                        "open": round(price.open, 2),
                        "high": round(price.high, 2),
                        "low": round(price.low, 2),
                        "close": round(price.close, 2),
                        "volume": price.volume,
                    })
            
            return {
                "metric_key": metric_key,
                "metric_name": metric_name,
                "source_events": source_events,
                "outcomes": outcomes,
                "price_history": price_history,
                "payload_hash": payload_hash,
                "generated_at": generated_at,
                "total_events": len(source_events),
            }
            
        finally:
            if self._owns_session:
                db.close()
    
    def _get_fallback_lineage_from_events(
        self,
        db: Any,
        metric_key: str
    ) -> Dict[str, Any]:
        """
        Fallback method to get lineage data directly from events when no lineage records exist.
        This queries the events table directly based on the metric_key type.
        """
        source_events = []
        outcomes = []
        price_history = []
        
        # Determine query filters based on metric key
        event_type_filters = {
            "events_8k": ["8-K"],
            "events_10q": ["10-Q"],
            "events_fda": ["FDA"],
            "events_press": ["press_release"],
            "events_primary": None,  # Use is_primary flag
            "events_secondary": None,  # Use is_primary flag (negated)
            "events_total": None,  # All events
            "accuracy_1d": None,  # Labeled events
            "accuracy_5d": None,  # Labeled events
        }
        
        # Build base query - get recent events
        base_query = select(Event).order_by(desc(Event.date)).limit(50)
        
        filter_types = event_type_filters.get(metric_key)
        if filter_types:
            base_query = base_query.where(Event.event_type.in_(filter_types))
        elif metric_key in ["accuracy_1d", "accuracy_5d"]:
            # For accuracy metrics, get events that have outcomes
            subq = select(EventOutcome.event_id).distinct()
            base_query = base_query.where(Event.id.in_(subq))
        
        events = db.execute(base_query).scalars().all()
        
        tickers_set = set()
        event_dates = []
        event_ids = []
        
        for event in events:
            tickers_set.add(event.ticker)
            if event.date:
                event_dates.append(event.date)
            event_ids.append(event.id)
            source_events.append({
                "ticker": event.ticker,
                "event_type": event.event_type,
                "date": event.date.isoformat() if event.date else "",
                "source_url": event.source_url or "",
                "event_id": event.id,
                "title": event.title or "",
            })
        
        # Get outcomes for these events
        if event_ids:
            outcomes_query = (
                select(EventOutcome)
                .where(EventOutcome.event_id.in_(event_ids))
                .order_by(EventOutcome.horizon)
            )
            event_outcomes = db.execute(outcomes_query).scalars().all()
            
            for outcome in event_outcomes:
                outcomes.append({
                    "horizon": outcome.horizon,
                    "return_pct": round(outcome.return_pct, 2) if outcome.return_pct is not None else None,
                    "return_pct_raw": round(outcome.return_pct_raw, 2) if outcome.return_pct_raw is not None else None,
                    "abs_return_pct": round(outcome.abs_return_pct, 2) if outcome.abs_return_pct is not None else None,
                    "direction_correct": outcome.direction_correct,
                    "has_benchmark_data": outcome.has_benchmark_data or False,
                })
        
        # Get price history
        if tickers_set and event_dates:
            min_event_date = min(event_dates)
            max_event_date = max(event_dates)
            start_date = min_event_date - timedelta(days=30)
            end_date = max_event_date + timedelta(days=30)
            
            prices_query = (
                select(PriceHistory)
                .where(
                    and_(
                        PriceHistory.ticker.in_(list(tickers_set)[:5]),  # Limit to 5 tickers for performance
                        PriceHistory.date >= start_date,
                        PriceHistory.date <= end_date
                    )
                )
                .order_by(PriceHistory.ticker, PriceHistory.date)
                .limit(200)
            )
            prices = db.execute(prices_query).scalars().all()
            
            for price in prices:
                price_history.append({
                    "date": price.date.isoformat(),
                    "open": round(price.open, 2),
                    "high": round(price.high, 2),
                    "low": round(price.low, 2),
                    "close": round(price.close, 2),
                    "volume": price.volume,
                })
        
        return {
            "metric_key": metric_key,
            "metric_name": metric_key.replace("_", " ").title(),
            "source_events": source_events,
            "outcomes": outcomes,
            "price_history": price_history,
            "payload_hash": None,
            "generated_at": datetime.utcnow().isoformat(),
            "total_events": len(source_events),
        }
    
    def get_audit_log(
        self,
        entity_type: Optional[str] = None,
        entity_id: Optional[int] = None,
        action: Optional[str] = None,
        performed_by: Optional[int] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get audit log entries with filtering and pagination.
        
        Args:
            entity_type: Filter by entity type
            entity_id: Filter by entity ID
            action: Filter by action ("create", "update", "delete")
            performed_by: Filter by user ID
            date_from: Filter by start date
            date_to: Filter by end date
            limit: Max records per page
            offset: Pagination offset
            
        Returns:
            Dict with entries list and pagination metadata
        """
        db = self._get_db()
        
        try:
            # Build query with filters
            query = select(AuditLogEntry).order_by(desc(AuditLogEntry.created_at))
            
            if entity_type:
                query = query.where(AuditLogEntry.entity_type == entity_type)
            
            if entity_id is not None:
                query = query.where(AuditLogEntry.entity_id == entity_id)
            
            if action:
                query = query.where(AuditLogEntry.action == action)
            
            if performed_by is not None:
                query = query.where(AuditLogEntry.performed_by == performed_by)
            
            if date_from:
                query = query.where(AuditLogEntry.created_at >= date_from)
            
            if date_to:
                query = query.where(AuditLogEntry.created_at <= date_to)
            
            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total = db.execute(count_query).scalar() or 0
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            entries = db.execute(query).scalars().all()
            
            return {
                "entries": [
                    {
                        "id": entry.id,
                        "entity_type": entry.entity_type,
                        "entity_id": entry.entity_id,
                        "action": entry.action,
                        "performed_by": entry.performed_by,
                        "diff": entry.diff_json,
                        "signature": entry.signature,
                        "created_at": entry.created_at.isoformat(),
                    }
                    for entry in entries
                ],
                "total": total,
                "limit": limit,
                "offset": offset,
                "has_more": (offset + len(entries)) < total,
            }
            
        finally:
            if self._owns_session:
                db.close()
    
    def record_quality_snapshot(
        self,
        metric_key: str,
        scope: str,
        sample_count: int,
        freshness_ts: datetime,
        source_job: str,
        quality_grade: str,
        summary_json: Optional[Dict[str, Any]] = None
    ) -> DataQualitySnapshot:
        """
        Record a data quality snapshot.
        
        Args:
            metric_key: Metric identifier (e.g., "events_total", "prices_spy")
            scope: Scope ("global", "portfolio", "watchlist")
            sample_count: Number of records in snapshot
            freshness_ts: Timestamp of most recent data
            source_job: Job that created this snapshot
            quality_grade: Quality grade ("excellent", "good", "fair", "stale")
            summary_json: Additional metadata
            
        Returns:
            Created DataQualitySnapshot instance
        """
        db = self._get_db()
        
        try:
            snapshot = DataQualitySnapshot(
                metric_key=metric_key,
                scope=scope,
                sample_count=sample_count,
                freshness_ts=freshness_ts,
                source_job=source_job,
                quality_grade=quality_grade,
                summary_json=summary_json or {},
            )
            
            db.add(snapshot)
            db.commit()
            db.refresh(snapshot)
            
            logger.info(
                f"Recorded quality snapshot: {metric_key} "
                f"[{scope}] grade={quality_grade} samples={sample_count}"
            )
            
            return snapshot
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record quality snapshot: {e}")
            raise
        finally:
            if self._owns_session:
                db.close()
    
    def record_pipeline_run(
        self,
        job_name: str,
        started_at: datetime,
        status: str = "running",
        completed_at: Optional[datetime] = None,
        rows_written: Optional[int] = None,
        source_hash: Optional[str] = None,
        error_blob: Optional[str] = None
    ) -> DataPipelineRun:
        """
        Record a pipeline run.
        
        Args:
            job_name: Name of the job
            started_at: When the job started
            status: Status ("running", "success", "failure")
            completed_at: When the job completed (if finished)
            rows_written: Number of records written
            source_hash: Hash of source data
            error_blob: Error message if failed
            
        Returns:
            Created/updated DataPipelineRun instance
        """
        db = self._get_db()
        
        try:
            run = DataPipelineRun(
                job_name=job_name,
                started_at=started_at,
                status=status,
                completed_at=completed_at,
                rows_written=rows_written,
                source_hash=source_hash,
                error_blob=error_blob,
            )
            
            db.add(run)
            db.commit()
            db.refresh(run)
            
            logger.info(f"Recorded pipeline run: {job_name} status={status}")
            
            return run
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record pipeline run: {e}")
            raise
        finally:
            if self._owns_session:
                db.close()
    
    def update_pipeline_run(
        self,
        run_id: int,
        status: str,
        completed_at: Optional[datetime] = None,
        rows_written: Optional[int] = None,
        error_blob: Optional[str] = None
    ) -> DataPipelineRun:
        """
        Update an existing pipeline run.
        
        Args:
            run_id: ID of the pipeline run to update
            status: New status
            completed_at: Completion timestamp
            rows_written: Final row count
            error_blob: Error message if failed
            
        Returns:
            Updated DataPipelineRun instance
        """
        db = self._get_db()
        
        try:
            run = db.execute(
                select(DataPipelineRun).where(DataPipelineRun.id == run_id)
            ).scalar_one()
            
            run.status = status
            if completed_at:
                run.completed_at = completed_at
            if rows_written is not None:
                run.rows_written = rows_written
            if error_blob:
                run.error_blob = error_blob
            
            db.commit()
            db.refresh(run)
            
            logger.info(f"Updated pipeline run {run_id}: status={status}")
            
            return run
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to update pipeline run: {e}")
            raise
        finally:
            if self._owns_session:
                db.close()
    
    def record_lineage(
        self,
        metric_key: str,
        entity_id: int,
        entity_type: str,
        observed_at: datetime,
        source_url: Optional[str] = None,
        payload_hash: Optional[str] = None
    ) -> DataLineageRecord:
        """
        Record a data lineage entry.
        
        Args:
            metric_key: Metric identifier (e.g., "event_created")
            entity_id: ID of the created entity
            entity_type: Type of entity ("event", "outcome", "price", "model")
            observed_at: When the entity was created
            source_url: Original source URL
            payload_hash: Hash of source payload
            
        Returns:
            Created DataLineageRecord instance
        """
        db = self._get_db()
        
        try:
            record = DataLineageRecord(
                metric_key=metric_key,
                entity_id=entity_id,
                entity_type=entity_type,
                source_url=source_url,
                payload_hash=payload_hash,
                observed_at=observed_at,
            )
            
            db.add(record)
            db.commit()
            db.refresh(record)
            
            logger.debug(
                f"Recorded lineage: {metric_key} {entity_type}#{entity_id}"
            )
            
            return record
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record lineage: {e}")
            raise
        finally:
            if self._owns_session:
                db.close()
    
    def record_audit_entry(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        performed_by: Optional[int] = None,
        diff_json: Optional[Dict[str, Any]] = None,
        signature: Optional[str] = None
    ) -> AuditLogEntry:
        """
        Record an audit log entry.
        
        Args:
            entity_type: Type of entity ("event", "user", "portfolio", etc.)
            entity_id: ID of the entity
            action: Action performed ("create", "update", "delete")
            performed_by: User ID who performed the action (None for system)
            diff_json: JSON diff for updates
            signature: Optional digital signature
            
        Returns:
            Created AuditLogEntry instance
        """
        db = self._get_db()
        
        try:
            entry = AuditLogEntry(
                entity_type=entity_type,
                entity_id=entity_id,
                action=action,
                performed_by=performed_by,
                diff_json=diff_json,
                signature=signature,
            )
            
            db.add(entry)
            db.commit()
            db.refresh(entry)
            
            logger.debug(
                f"Audit log: {action} {entity_type}#{entity_id} "
                f"by user={performed_by or 'system'}"
            )
            
            return entry
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to record audit entry: {e}")
            raise
        finally:
            if self._owns_session:
                db.close()
    
    def record_audit_log(
        self,
        entity_type: str,
        entity_id: int,
        action: str,
        performed_by: Optional[int] = None,
        diff_json: Optional[Dict[str, Any]] = None,
        signature: Optional[str] = None
    ) -> AuditLogEntry:
        """
        Alias for record_audit_entry() for backwards compatibility.
        
        Record an audit log entry.
        
        Args:
            entity_type: Type of entity ("event", "user", "portfolio", etc.)
            entity_id: ID of the entity
            action: Action performed ("create", "update", "delete")
            performed_by: User ID who performed the action (None for system)
            diff_json: JSON diff for updates
            signature: Optional digital signature
            
        Returns:
            Created AuditLogEntry instance
        """
        return self.record_audit_entry(
            entity_type=entity_type,
            entity_id=entity_id,
            action=action,
            performed_by=performed_by,
            diff_json=diff_json,
            signature=signature
        )
