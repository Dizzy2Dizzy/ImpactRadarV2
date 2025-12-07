"""
Label outcomes pipeline - captures realized price movements (T+1) for events.

Fetches price data after events and computes returns for ML training labels.
"""

import os
import sys
from datetime import datetime, timedelta, date
from typing import List, Optional
from collections import defaultdict

from sqlalchemy import select, func
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from releaseradar.db.models import Event, EventOutcome, PriceHistory, EventStats, ModelRegistry
from releaseradar.db.session import get_db_transaction
from releaseradar.log_config import logger
from releaseradar.services.quality_metrics import QualityMetricsService
from releaseradar.ml.monitoring.drift_monitor import DriftMonitor
from releaseradar.ml.monitoring.calibration_service import CalibrationService


class OutcomeLabeler:
    """Labels events with realized outcomes based on price movements."""
    
    HORIZONS = ["1d", "5d", "20d"]
    HORIZON_DAYS = {"1d": 1, "5d": 5, "20d": 20}
    
    def __init__(self):
        self.prices_to_persist = []
    
    def get_price_at_date(
        self,
        db,
        ticker: str,
        target_date: date,
        max_lookback_days: int = 5,
        fetch_and_store: bool = True
    ) -> Optional[float]:
        """
        Get closing price for ticker at or near target date.
        
        Args:
            db: Database session
            ticker: Stock ticker
            target_date: Target date
            max_lookback_days: Max days to look back for closest price
            fetch_and_store: If True, fetch from API and store if not in DB
            
        Returns:
            Close price or None if not found
        """
        for offset in range(max_lookback_days + 1):
            check_date = target_date - timedelta(days=offset)
            
            price_record = db.execute(
                select(PriceHistory)
                .where(PriceHistory.ticker == ticker)
                .where(PriceHistory.date == check_date)
            ).scalar_one_or_none()
            
            if price_record:
                return price_record.close
        
        # If price not found and we should fetch from API
        if fetch_and_store:
            try:
                import yfinance as yf
                
                # Fetch price data around target date (±7 days window)
                start_date = target_date - timedelta(days=7)
                end_date = target_date + timedelta(days=1)
                
                ticker_obj = yf.Ticker(ticker)
                hist = ticker_obj.history(start=start_date, end=end_date)
                
                if not hist.empty:
                    # Store all fetched prices
                    for idx, row in hist.iterrows():
                        price_date = idx.date()
                        
                        # Upsert to price_history
                        stmt = insert(PriceHistory).values(
                            ticker=ticker,
                            date=price_date,
                            open=float(row['Open']),
                            close=float(row['Close']),
                            high=float(row['High']),
                            low=float(row['Low']),
                            volume=int(row['Volume']),
                            source='yahoo'
                        )
                        stmt = stmt.on_conflict_do_update(
                            index_elements=['ticker', 'date'],
                            set_={
                                'close': stmt.excluded.close,
                                'open': stmt.excluded.open,
                                'high': stmt.excluded.high,
                                'low': stmt.excluded.low,
                                'volume': stmt.excluded.volume,
                            }
                        )
                        db.execute(stmt)
                    
                    db.commit()
                    logger.info(f"Fetched and stored {len(hist)} price records for {ticker}")
                    
                    # Now try to get the price again
                    for offset in range(max_lookback_days + 1):
                        check_date = target_date - timedelta(days=offset)
                        
                        price_record = db.execute(
                            select(PriceHistory)
                            .where(PriceHistory.ticker == ticker)
                            .where(PriceHistory.date == check_date)
                        ).scalar_one_or_none()
                        
                        if price_record:
                            return price_record.close
            
            except Exception as e:
                logger.warning(f"Failed to fetch price data for {ticker}: {e}")
        
        return None
    
    def label_event_outcome(
        self,
        db,
        event: Event,
        horizon: str,
        label_date: date
    ) -> Optional[dict]:
        """
        Calculate outcome for a single event at given horizon with abnormal returns.
        
        Args:
            db: Database session
            event: Event to label
            horizon: Time horizon ("1d", "5d", "20d")
            label_date: Date when label is computed
            
        Returns:
            Dict with outcome data (including abnormal returns) or None if prices unavailable
        """
        # Get price before event (on or just before event date)
        event_date = event.date.date()
        price_before = self.get_price_at_date(db, event.ticker, event_date)
        
        if price_before is None:
            logger.debug(f"No price data for {event.ticker} around {event_date}")
            return None
        
        # Calculate target date for price after
        days_ahead = self.HORIZON_DAYS[horizon]
        target_date_after = event_date + timedelta(days=days_ahead)
        
        # Don't label if target date is in the future
        if target_date_after > label_date:
            logger.debug(f"Target date {target_date_after} is in the future, skipping")
            return None
        
        # Get price after event
        price_after = self.get_price_at_date(db, event.ticker, target_date_after)
        
        if price_after is None:
            logger.debug(f"No price data for {event.ticker} at target date {target_date_after}")
            return None
        
        # Calculate raw stock return
        return_pct_raw = ((price_after - price_before) / price_before) * 100
        
        # Calculate benchmark (SPY) return for same period
        spy_before = self.get_price_at_date(db, "SPY", event_date, fetch_and_store=True)
        spy_after = self.get_price_at_date(db, "SPY", target_date_after, fetch_and_store=True)
        
        has_benchmark_data = False
        benchmark_return_pct = 0.0
        
        if spy_before is not None and spy_after is not None:
            benchmark_return_pct = ((spy_after - spy_before) / spy_before) * 100
            has_benchmark_data = True
            logger.debug(f"SPY benchmark return for {horizon}: {benchmark_return_pct:.2f}%")
        else:
            logger.debug(f"No SPY benchmark data available for {event_date} to {target_date_after}, "
                        f"using raw return (benchmark=0.0)")
        
        # Calculate abnormal return (event-specific impact)
        return_pct = return_pct_raw - benchmark_return_pct
        abs_return_pct = abs(return_pct)
        
        # Check if predicted direction was correct (if prediction exists)
        direction_correct = None
        if event.direction:
            predicted_up = event.direction.lower() in ["bullish", "positive", "up"]
            actual_up = return_pct > 0
            direction_correct = predicted_up == actual_up
        
        outcome = {
            "event_id": event.id,
            "ticker": event.ticker,
            "horizon": horizon,
            "price_before": price_before,
            "price_after": price_after,
            "return_pct_raw": return_pct_raw,
            "benchmark_return_pct": benchmark_return_pct,
            "return_pct": return_pct,
            "abs_return_pct": abs_return_pct,
            "direction_correct": direction_correct,
            "has_benchmark_data": has_benchmark_data,
            "label_date": label_date,
        }
        
        logger.debug(f"Labeled event {event.id} ({event.ticker}): "
                    f"{horizon} raw return = {return_pct_raw:.2f}%, "
                    f"benchmark = {benchmark_return_pct:.2f}%, "
                    f"abnormal return = {return_pct:.2f}%")
        
        return outcome
    
    def label_events(
        self,
        lookback_days: int = 30,
        ticker: Optional[str] = None,
        event_type: Optional[str] = None,
        label_all: bool = False
    ) -> dict:
        """
        Label outcomes for events in lookback window.
        
        Args:
            lookback_days: How many days back to label events (ignored if label_all=True)
            ticker: Optional ticker filter
            event_type: Optional event type filter
            label_all: If True, label all historical events regardless of age
            
        Returns:
            Statistics dict with event_type breakdown
        """
        with get_db_transaction() as db:
            # Record pipeline run start
            quality_service = QualityMetricsService(db)
            started_at = datetime.utcnow()
            pipeline_run = quality_service.record_pipeline_run(
                job_name="label_outcomes",
                started_at=started_at,
                status="running"
            )
            logger.info(f"🚀 Pipeline run #{pipeline_run.id} started for label_outcomes job")
            
            stats = {
                "events_processed": 0,
                "outcomes_created": 0,
                "outcomes_skipped": 0,
                "errors": 0,
                "by_event_type": defaultdict(lambda: {"processed": 0, "created": 0, "skipped": 0})
            }
            
            # Calculate date range
            today = datetime.utcnow().date()
            
            # Build query for events to label
            if label_all:
                # Label all events that are old enough for at least 1d horizon
                query = select(Event).where(Event.date <= today - timedelta(days=1))
                logger.info("Labeling ALL historical events (label_all=True)")
            else:
                cutoff_date = today - timedelta(days=lookback_days)
                query = select(Event).where(Event.date >= cutoff_date)
                logger.info(f"Labeling events from last {lookback_days} days")
            
            if ticker:
                query = query.where(Event.ticker == ticker)
            
            if event_type:
                query = query.where(Event.event_type == event_type)
            
            events = db.execute(query).scalars().all()
            
            logger.info(f"Found {len(events)} events to label")
            
            # Group events by type for logging
            events_by_type = defaultdict(list)
            for event in events:
                events_by_type[event.event_type].append(event)
            
            logger.info(f"Events by type: {dict((k, len(v)) for k, v in events_by_type.items())}")
            
            for event in events:
                try:
                    stats["events_processed"] += 1
                    event_type_key = event.event_type or "unknown"
                    stats["by_event_type"][event_type_key]["processed"] += 1
                    
                    # Label for each horizon
                    for horizon in self.HORIZONS:
                        # Check if outcome already exists
                        existing = db.execute(
                            select(EventOutcome)
                            .where(EventOutcome.event_id == event.id)
                            .where(EventOutcome.horizon == horizon)
                        ).scalar_one_or_none()
                        
                        if existing:
                            stats["outcomes_skipped"] += 1
                            stats["by_event_type"][event_type_key]["skipped"] += 1
                            continue
                        
                        # Compute outcome
                        outcome_data = self.label_event_outcome(db, event, horizon, today)
                        
                        if outcome_data is None:
                            stats["outcomes_skipped"] += 1
                            stats["by_event_type"][event_type_key]["skipped"] += 1
                            continue
                        
                        # Upsert outcome
                        stmt = insert(EventOutcome).values(outcome_data)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["event_id", "horizon"],
                            set_={
                                "price_before": stmt.excluded.price_before,
                                "price_after": stmt.excluded.price_after,
                                "return_pct": stmt.excluded.return_pct,
                                "abs_return_pct": stmt.excluded.abs_return_pct,
                                "direction_correct": stmt.excluded.direction_correct,
                                "label_date": stmt.excluded.label_date,
                                "return_pct_raw": stmt.excluded.return_pct_raw,
                                "benchmark_return_pct": stmt.excluded.benchmark_return_pct,
                                "has_benchmark_data": stmt.excluded.has_benchmark_data,
                            }
                        )
                        db.execute(stmt)
                        stats["outcomes_created"] += 1
                        stats["by_event_type"][event_type_key]["created"] += 1
                    
                    # Commit every 50 events
                    if stats["events_processed"] % 50 == 0:
                        db.commit()
                        logger.info(f"Processed {stats['events_processed']} events, "
                                   f"created {stats['outcomes_created']} outcomes")
                
                except Exception as e:
                    logger.error(f"Error labeling event {event.id}: {e}")
                    stats["errors"] += 1
                    db.rollback()
                    continue
            
            # Final commit
            db.commit()
            
            # Convert by_event_type to regular dict for logging
            stats["by_event_type"] = dict(stats["by_event_type"])
            
            # Record audit log for outcome labeling operation
            try:
                quality_service.record_audit_log(
                    entity_type="outcome_labeling",
                    entity_id=0,  # No specific entity ID for batch operation
                    action="create",
                    performed_by=None,  # System operation
                    diff_json={
                        "events_processed": stats["events_processed"],
                        "outcomes_created": stats["outcomes_created"],
                        "outcomes_skipped": stats["outcomes_skipped"],
                        "errors": stats["errors"],
                        "lookback_days": lookback_days,
                        "ticker": ticker,
                        "event_type": event_type,
                        "label_all": label_all,
                        "by_event_type": stats["by_event_type"]
                    }
                )
                logger.debug(f"Audit log created for outcome labeling operation")
            except Exception as e:
                logger.warning(f"Failed to record audit log for outcome labeling: {e}")
            
            # Update pipeline run status
            try:
                completed_at = datetime.utcnow()
                status = "success" if stats["errors"] == 0 else "failure"
                quality_service.update_pipeline_run(
                    run_id=pipeline_run.id,
                    status=status,
                    completed_at=completed_at,
                    rows_written=stats["outcomes_created"]
                )
                runtime = (completed_at - started_at).total_seconds()
                logger.info(f"✅ Pipeline run #{pipeline_run.id} completed with status={status} "
                           f"(runtime={runtime:.1f}s, rows_written={stats['outcomes_created']})")
            except Exception as e:
                logger.warning(f"Failed to update pipeline run: {e}")
            
            logger.info(f"Outcome labeling complete: {stats}")
            logger.info(f"Breakdown by event type:")
            for et, et_stats in stats["by_event_type"].items():
                logger.info(f"  {et}: processed={et_stats['processed']}, "
                           f"created={et_stats['created']}, skipped={et_stats['skipped']}")
            
            return stats
    
    def compute_event_stats(self) -> dict:
        """
        Compute and store EventStats based on labeled outcomes.
        
        Calculates aggregate statistics for ticker+event_type combinations.
        
        Returns:
            Statistics dict
        """
        with get_db_transaction() as db:
            stats = {
                "stats_updated": 0,
                "errors": 0,
            }
            
            # Get all unique ticker+event_type combinations that have outcomes
            ticker_event_combinations = db.execute(
                select(EventOutcome.ticker, Event.event_type)
                .join(Event, EventOutcome.event_id == Event.id)
                .distinct()
            ).all()
            
            logger.info(f"Computing stats for {len(ticker_event_combinations)} ticker+event_type combinations")
            
            for ticker, event_type in ticker_event_combinations:
                try:
                    # Fetch all outcomes for this ticker+event_type
                    outcomes_1d = db.execute(
                        select(EventOutcome)
                        .join(Event, EventOutcome.event_id == Event.id)
                        .where(EventOutcome.ticker == ticker)
                        .where(Event.event_type == event_type)
                        .where(EventOutcome.horizon == "1d")
                    ).scalars().all()
                    
                    outcomes_5d = db.execute(
                        select(EventOutcome)
                        .join(Event, EventOutcome.event_id == Event.id)
                        .where(EventOutcome.ticker == ticker)
                        .where(Event.event_type == event_type)
                        .where(EventOutcome.horizon == "5d")
                    ).scalars().all()
                    
                    outcomes_20d = db.execute(
                        select(EventOutcome)
                        .join(Event, EventOutcome.event_id == Event.id)
                        .where(EventOutcome.ticker == ticker)
                        .where(Event.event_type == event_type)
                        .where(EventOutcome.horizon == "20d")
                    ).scalars().all()
                    
                    if not outcomes_1d:
                        continue
                    
                    # Calculate statistics
                    sample_size = len(outcomes_1d)
                    
                    # Win rate (% of positive returns)
                    positive_count = sum(1 for o in outcomes_1d if o.return_pct > 0)
                    win_rate = positive_count / sample_size if sample_size > 0 else None
                    
                    # Average absolute moves
                    avg_abs_move_1d = sum(o.abs_return_pct for o in outcomes_1d) / len(outcomes_1d) if outcomes_1d else None
                    avg_abs_move_5d = sum(o.abs_return_pct for o in outcomes_5d) / len(outcomes_5d) if outcomes_5d else None
                    avg_abs_move_20d = sum(o.abs_return_pct for o in outcomes_20d) / len(outcomes_20d) if outcomes_20d else None
                    
                    # Mean moves (directional)
                    mean_move_1d = sum(o.return_pct for o in outcomes_1d) / len(outcomes_1d) if outcomes_1d else None
                    mean_move_5d = sum(o.return_pct for o in outcomes_5d) / len(outcomes_5d) if outcomes_5d else None
                    mean_move_20d = sum(o.return_pct for o in outcomes_20d) / len(outcomes_20d) if outcomes_20d else None
                    
                    # Upsert EventStats
                    stmt = insert(EventStats).values(
                        ticker=ticker,
                        event_type=event_type,
                        sample_size=sample_size,
                        win_rate=win_rate,
                        avg_abs_move_1d=avg_abs_move_1d,
                        avg_abs_move_5d=avg_abs_move_5d,
                        avg_abs_move_20d=avg_abs_move_20d,
                        mean_move_1d=mean_move_1d,
                        mean_move_5d=mean_move_5d,
                        mean_move_20d=mean_move_20d,
                        updated_at=datetime.utcnow(),
                    )
                    stmt = stmt.on_conflict_do_update(
                        index_elements=['ticker', 'event_type'],
                        set_={
                            'sample_size': stmt.excluded.sample_size,
                            'win_rate': stmt.excluded.win_rate,
                            'avg_abs_move_1d': stmt.excluded.avg_abs_move_1d,
                            'avg_abs_move_5d': stmt.excluded.avg_abs_move_5d,
                            'avg_abs_move_20d': stmt.excluded.avg_abs_move_20d,
                            'mean_move_1d': stmt.excluded.mean_move_1d,
                            'mean_move_5d': stmt.excluded.mean_move_5d,
                            'mean_move_20d': stmt.excluded.mean_move_20d,
                            'updated_at': stmt.excluded.updated_at,
                        }
                    )
                    db.execute(stmt)
                    stats["stats_updated"] += 1
                    
                    # Commit every 50 stats
                    if stats["stats_updated"] % 50 == 0:
                        db.commit()
                        logger.info(f"Updated {stats['stats_updated']} EventStats records")
                
                except Exception as e:
                    logger.error(f"Error computing stats for {ticker}/{event_type}: {e}")
                    stats["errors"] += 1
                    continue
            
            # Final commit
            db.commit()
            
            logger.info(f"EventStats computation complete: {stats}")
            
            return stats
    
    def run_drift_monitoring(self, db) -> dict:
        """
        Run drift monitoring after labeling to compare predictions with outcomes.
        
        Checks all active models for drift and logs calibration metrics.
        Flags contrarian events where predictions were significantly wrong.
        
        Returns:
            Dict with drift monitoring results
        """
        results = {
            "drift_checks": 0,
            "drifts_detected": 0,
            "calibration_snapshots": 0,
            "contrarian_events": 0,
            "errors": 0,
        }
        
        try:
            active_models = db.execute(
                select(ModelRegistry)
                .where(ModelRegistry.status == "active")
            ).scalars().all()
            
            if not active_models:
                logger.info("No active models found for drift monitoring")
                return results
            
            logger.info(f"Running drift monitoring for {len(active_models)} active models")
            
            drift_monitor = DriftMonitor(db=db)
            calibration_service = CalibrationService(db=db)
            
            for model in active_models:
                for horizon in ["1d", "5d"]:
                    try:
                        for window_days in [7, 30, 90]:
                            drift_monitor.store_performance_snapshot(
                                model_id=model.id,
                                horizon=horizon,
                                window_days=window_days
                            )
                        
                        drift_result = drift_monitor.detect_drift(
                            model_id=model.id,
                            horizon=horizon
                        )
                        results["drift_checks"] += 1
                        
                        if drift_result.get("has_drift"):
                            drift_monitor.create_drift_alert(
                                model_id=model.id,
                                horizon=horizon,
                                alert_type=drift_result["drift_type"],
                                severity=drift_result["severity"],
                                metrics_before=drift_result["baseline_metrics"],
                                metrics_after=drift_result["current_metrics"]
                            )
                            results["drifts_detected"] += 1
                            logger.warning(
                                f"Drift detected for {model.name}/{horizon}: "
                                f"{drift_result['drift_type']} ({drift_result['severity']})"
                            )
                        
                        calibration_service.store_calibration_snapshot(
                            model_id=model.id,
                            horizon=horizon
                        )
                        results["calibration_snapshots"] += 1
                        
                        is_calibrated, ece = calibration_service.is_well_calibrated(
                            model_id=model.id,
                            horizon=horizon
                        )
                        
                        if not is_calibrated and ece > 0:
                            logger.warning(
                                f"Model {model.name}/{horizon} poorly calibrated: ECE={ece:.4f}"
                            )
                        
                    except Exception as e:
                        logger.error(f"Error in drift monitoring for {model.name}/{horizon}: {e}")
                        results["errors"] += 1
                        continue
            
            for horizon in ["1d", "5d"]:
                try:
                    contrarian = drift_monitor.get_contrarian_events(
                        horizon=horizon,
                        lookback_days=30,
                        min_error=5.0
                    )
                    results["contrarian_events"] += len(contrarian)
                    
                    if contrarian:
                        logger.info(
                            f"Found {len(contrarian)} contrarian events for {horizon} "
                            f"(top error: {abs(contrarian[0].get('error', 0)):.2f}%)"
                        )
                except Exception as e:
                    logger.error(f"Error getting contrarian events for {horizon}: {e}")
            
            logger.info(
                f"Drift monitoring complete: {results['drift_checks']} checks, "
                f"{results['drifts_detected']} drifts, "
                f"{results['calibration_snapshots']} calibration snapshots, "
                f"{results['contrarian_events']} contrarian events"
            )
            
        except Exception as e:
            logger.error(f"Error in drift monitoring: {e}")
            results["errors"] += 1
        
        return results


def main():
    """Entry point for scheduled job."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Label event outcomes with price data")
    parser.add_argument("--lookback-days", type=int, default=60,
                       help="Days to look back for events (default: 60)")
    parser.add_argument("--ticker", type=str, default=None,
                       help="Filter by specific ticker")
    parser.add_argument("--event-type", type=str, default=None,
                       help="Filter by specific event type")
    parser.add_argument("--label-all", action="store_true",
                       help="Label ALL historical events (ignores lookback-days)")
    args = parser.parse_args()
    
    logger.info("Starting outcome labeling job")
    
    labeler = OutcomeLabeler()
    
    # Label events
    label_stats = labeler.label_events(
        lookback_days=args.lookback_days,
        ticker=args.ticker,
        event_type=args.event_type,
        label_all=args.label_all
    )
    
    # Compute EventStats from labeled outcomes
    stats_stats = labeler.compute_event_stats()
    
    # Run drift monitoring to compare predictions with actual outcomes
    drift_stats = {}
    try:
        with get_db_transaction() as db:
            drift_stats = labeler.run_drift_monitoring(db)
    except Exception as e:
        logger.error(f"Drift monitoring failed: {e}")
        drift_stats = {"errors": 1}
    
    total_errors = label_stats["errors"] + stats_stats["errors"] + drift_stats.get("errors", 0)
    
    if total_errors > 0:
        logger.warning(f"Completed with {total_errors} errors")
        sys.exit(1)
    else:
        logger.info("Outcome labeling, stats computation, and drift monitoring completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
