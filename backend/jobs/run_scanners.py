#!/usr/bin/env python3
"""
Scanner orchestration job with parallel execution, retry logic, and metrics.

Runs all enabled scanners with:
- Bounded concurrency (max 4 parallel)
- Exponential backoff retry
- Prometheus metrics
- Idempotent event upserts
- Circuit breaker protection
- Automatic transaction rollback

Usage:
    python jobs/run_scanners.py           # Run once
    python jobs/run_scanners.py --loop   # Run continuously
"""

import sys
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from typing import List, Dict, Any, Callable, Optional
import importlib
import threading

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scanners.catalog import SCANNERS, ScannerDefinition
from releaseradar.db.session import (
    SessionLocal,
    get_scanner_db_context,
    scanner_circuit_breaker,
    pool_health,
    check_db_health,
    reset_db_connections,
    cleanup_idle_transactions,
    CircuitBreaker,
)
from releaseradar.db.models import Company, Event
from releaseradar.utils.errors import DatabaseError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, OperationalError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# Scanner-Specific Circuit Breakers
# ============================================================================

class ScannerCircuitBreakers:
    """Manage individual circuit breakers for each scanner."""
    
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = threading.Lock()
    
    def get(self, scanner_key: str) -> CircuitBreaker:
        """Get or create a circuit breaker for a scanner."""
        with self._lock:
            if scanner_key not in self._breakers:
                self._breakers[scanner_key] = CircuitBreaker(
                    name=f"scanner_{scanner_key}",
                    failure_threshold=3,  # Trip after 3 consecutive failures
                    recovery_timeout=120,  # Wait 2 minutes before retry
                    half_open_max_calls=1  # Test with 1 call
                )
            return self._breakers[scanner_key]
    
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get stats for all circuit breakers."""
        with self._lock:
            return {key: cb.get_stats() for key, cb in self._breakers.items()}


# Global scanner circuit breakers
scanner_breakers = ScannerCircuitBreakers()

# Metrics tracking
_metrics = {
    "scanner_runs_total": {},
    "scanner_events_ingested_total": {},
    "scanner_errors_total": {},
    "scanner_runtime_seconds": {},
    "scanner_timeouts_total": {},
    "scanner_circuit_breaker_trips": {},
}

_metrics_lock = threading.Lock()


def increment_metric(metric_name: str, scanner_key: str, value: float = 1.0):
    """Increment a metric for a specific scanner (thread-safe)."""
    with _metrics_lock:
        if scanner_key not in _metrics[metric_name]:
            _metrics[metric_name][scanner_key] = 0
        _metrics[metric_name][scanner_key] += value


def get_metrics() -> Dict[str, Dict[str, float]]:
    """Get all metrics (thread-safe)."""
    with _metrics_lock:
        return {k: dict(v) for k, v in _metrics.items()}


# ============================================================================
# Database Operations with Automatic Rollback
# ============================================================================

def get_tracked_tickers() -> List[str]:
    """Get list of tracked company tickers with automatic rollback on error."""
    try:
        with get_scanner_db_context("ticker_fetch") as session:
            stmt = select(Company.ticker).where(Company.tracked == True)
            result = session.execute(stmt)
            return [row[0] for row in result.fetchall()]
    except DatabaseError as e:
        logger.error(f"Failed to fetch tracked tickers: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching tracked tickers: {e}")
        return []


def upsert_event(session, event_data: Dict[str, Any], scanner_key: str) -> bool:
    """
    Idempotent event upsert using natural key (ticker, event_type, raw_id).
    
    Uses nested transactions (savepoints) for ML scoring to prevent full rollback
    on ML failures while ensuring the base event is saved.
    
    Args:
        session: Database session
        event_data: Normalized event dict from scanner
        scanner_key: Scanner identifier for tracking
        
    Returns:
        True if event was created/updated, False if skipped
    """
    try:
        ticker = event_data["ticker"]
        event_type = event_data["event_type"]
        raw_id = event_data.get("raw_id")
        
        if not raw_id:
            # Generate fallback raw_id from event data
            raw_id = f"{event_type}_{ticker}_{event_data['announced_at'].strftime('%Y%m%d%H%M')}"
        
        # Check if event exists using natural key
        existing = None
        if raw_id:
            stmt = select(Event).where(
                Event.ticker == ticker,
                Event.event_type == event_type,
                Event.raw_id == raw_id
            )
            existing = session.execute(stmt).scalar_one_or_none()
        
        # Track whether this is new or updated for scoring logic
        is_new = existing is None
        event = None
        
        if existing:
            # Update existing event
            existing.title = event_data["headline"]
            existing.source_url = event_data.get("source_url")
            existing.date = event_data["announced_at"]
            existing.updated_at = datetime.utcnow()
            event = existing
            logger.debug(f"Updated event: {ticker} {event_type} {raw_id}")
        else:
            # Create new event with default scores (will be overwritten by scoring engine)
            event = Event(
                ticker=ticker,
                company_name=event_data.get("company_name", ticker),
                event_type=event_type,
                title=event_data["headline"],
                description=event_data.get("description"),
                date=event_data["announced_at"],
                source="scanner",
                source_url=event_data.get("source_url"),
                raw_id=raw_id,
                source_scanner=scanner_key,
                impact_score=50,
                direction='neutral',
                confidence=0.5,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(event)
            logger.debug(f"Created event: {ticker} {event_type} {raw_id}")
        
        # Flush to get event ID for scoring
        session.flush()
        
        # Get sector from event_data or fetch from Company table
        sector = event_data.get("sector")
        if not sector:
            # Try to fetch sector from Company table
            company_stmt = select(Company).where(Company.ticker == ticker)
            company = session.execute(company_stmt).scalar_one_or_none()
            if company:
                sector = company.sector
        
        # Apply impact scoring (content-based scoring with 8-K item analysis)
        try:
            from impact_scoring import score_event as impact_score_event
            
            # Get metadata from event_data (includes 8k_items for SEC filings)
            metadata = event_data.get("metadata", {})
            
            # Score using content-based analysis
            impact_result = impact_score_event(
                event_type=event_type,
                title=event_data["headline"],
                description=event_data.get("description", ""),
                sector=sector,
                metadata=metadata
            )
            
            # Apply content-based scoring results
            event.impact_score = impact_result.get('impact_score', 50)
            event.direction = impact_result.get('direction', 'neutral')
            event.confidence = impact_result.get('confidence', 0.5)
            event.rationale = impact_result.get('rationale', '')
            
            logger.info(f"Impact scored event {event.id} ({ticker} {event_type}): score={event.impact_score}, direction={event.direction}, confidence={event.confidence:.2f}")
            
        except Exception as e:
            logger.warning(f"Failed to compute impact score for event {ticker} {event_type}: {e}, using defaults")
        
        # Apply context-aware scoring (market factors, sector beta, etc.)
        try:
            from analytics.scoring import compute_event_score
            
            score_result = compute_event_score(
                event_id=event.id,
                ticker=ticker,
                event_type=event_type,
                event_date=event.date,
                source=event.source,
                sector=sector,
                db=session
            )
            
            # Use context score if higher than impact score (context can boost but not reduce)
            context_score = score_result.get('final_score', 50)
            if context_score > event.impact_score:
                event.impact_score = context_score
                rationale_addition = '; '.join(score_result.get('rationale', []))
                if rationale_addition:
                    event.rationale = f"{event.rationale}; Context: {rationale_addition}"
            
            # Update confidence using context scoring if available
            context_confidence = score_result.get('confidence', 50) / 100.0
            if context_confidence > event.confidence:
                event.confidence = context_confidence
            
            logger.info(f"Context scored event {event.id} ({ticker} {event_type}): final_score={event.impact_score}, direction={event.direction}, confidence={event.confidence:.2f}")
            
        except Exception as e:
            logger.warning(f"Failed to compute context score for event {ticker} {event_type}: {e}")
        
        # Apply ML predictions (only for new events to avoid redundant predictions)
        # Uses savepoint (nested transaction) to isolate ML scoring failures
        if is_new:
            try:
                from releaseradar.ml.serving import MLScoringService
                
                # Use begin_nested() to create a savepoint - if ML fails, only rollback to savepoint
                nested = session.begin_nested()
                try:
                    ml_service = MLScoringService(session)
                    ml_prediction = ml_service.predict_single(
                        event_id=event.id,
                        horizon="1d",
                        confidence_threshold=0.4,
                        use_blending=True
                    )
                    
                    if ml_prediction:
                        # Update event with ML predictions
                        event.ml_adjusted_score = ml_prediction.ml_adjusted_score
                        event.ml_confidence = ml_prediction.ml_confidence
                        event.ml_model_version = ml_prediction.ml_model_version
                        event.model_source = ml_prediction.model_source
                        event.delta_applied = ml_prediction.delta_applied
                        
                        # If ML model predicts strong move, override direction
                        if ml_prediction.predicted_return_1d is not None:
                            if ml_prediction.predicted_return_1d < -1.0 and ml_prediction.ml_confidence > 0.5:
                                event.direction = 'negative'
                                logger.info(f"ML predicted negative return ({ml_prediction.predicted_return_1d:.2f}%), overriding direction to 'negative'")
                            elif ml_prediction.predicted_return_1d > 1.0 and ml_prediction.ml_confidence > 0.5:
                                event.direction = 'positive'
                                logger.info(f"ML predicted positive return ({ml_prediction.predicted_return_1d:.2f}%), overriding direction to 'positive'")
                        
                        logger.info(
                            f"ML prediction applied for event {event.id}: "
                            f"base={event.impact_score}, ml={ml_prediction.ml_adjusted_score}, "
                            f"delta={ml_prediction.delta_applied:.1f}, conf={ml_prediction.ml_confidence:.2f}"
                        )
                    nested.commit()
                except Exception as inner_e:
                    # Rollback only to the savepoint, preserving the main transaction
                    nested.rollback()
                    raise inner_e
            except Exception as e:
                logger.warning(f"ML scoring failed for event {event.id}: {e}, continuing with deterministic scoring")
        
        return True
            
    except IntegrityError as e:
        logger.warning(f"Integrity error upserting event: {e}")
        session.rollback()
        return False
    except Exception as e:
        logger.error(f"Error upserting event: {e}")
        session.rollback()
        return False


def run_scanner(scanner: ScannerDefinition, tickers: List[str]) -> Dict[str, Any]:
    """
    Execute a single scanner with error handling, circuit breaker, and metrics.
    
    Features:
    - Per-scanner circuit breaker protection
    - Automatic transaction rollback on any error
    - Timeout protection for long-running scans
    - Comprehensive error logging and metrics
    
    Args:
        scanner: Scanner definition
        tickers: List of tickers to scan
        
    Returns:
        Result dict with stats
    """
    start_time = time.time()
    result = {
        "scanner": scanner.key,
        "success": False,
        "events_found": 0,
        "events_ingested": 0,
        "errors": 0,
        "runtime": 0,
        "skipped": False,
        "skip_reason": None,
    }
    
    # Check scanner-specific circuit breaker
    breaker = scanner_breakers.get(scanner.key)
    if not breaker.can_execute():
        logger.warning(f"Circuit breaker OPEN for scanner {scanner.key}, skipping")
        increment_metric("scanner_circuit_breaker_trips", scanner.key)
        result["skipped"] = True
        result["skip_reason"] = f"Circuit breaker {breaker.state}"
        return result
    
    # Check global database circuit breaker
    if not scanner_circuit_breaker.can_execute():
        logger.warning(f"Global database circuit breaker OPEN, skipping scanner {scanner.key}")
        result["skipped"] = True
        result["skip_reason"] = "Database circuit breaker open"
        return result
    
    try:
        logger.info(f"Running scanner: {scanner.label}")
        increment_metric("scanner_runs_total", scanner.key)
        
        # Dynamically import scanner function - map function names to module names
        fn_to_module = {
            "scan_sec_edgar": "sec_edgar",
            "scan_fda": "fda",
            "scan_press": "press",
            "scan_earnings_calls": "earnings",
            "scan_sec_8k": "sec_8k",
            "scan_sec_10q": "sec_10q",
            "scan_guidance": "guidance",
            "scan_product_launch": "product_launch",
            "scan_ma": "ma",
            "scan_dividend_buyback": "dividend"
        }
        
        module_name = fn_to_module.get(scanner.fn_name)
        if not module_name:
            logger.error(f"Unknown scanner function: {scanner.fn_name}")
            increment_metric("scanner_errors_total", scanner.key)
            breaker.record_failure()
            result["errors"] = 1
            return result
        
        try:
            module = importlib.import_module(f"scanners.impl.{module_name}")
            scan_fn = getattr(module, scanner.fn_name)
        except (ImportError, AttributeError) as e:
            logger.error(f"Failed to import {scanner.fn_name} from {module_name}: {e}")
            increment_metric("scanner_errors_total", scanner.key)
            breaker.record_failure()
            result["errors"] = 1
            return result
        
        # Run scanner (this is the HTTP scraping part, outside transaction)
        events = scan_fn(tickers)
        result["events_found"] = len(events)
        
        # Upsert events to database with automatic rollback on error
        try:
            with get_scanner_db_context(scanner.key) as session:
                for event_data in events:
                    try:
                        if upsert_event(session, event_data, scanner.key):
                            result["events_ingested"] += 1
                    except Exception as e:
                        # Log individual event errors but continue with others
                        logger.warning(f"Failed to upsert event for {scanner.key}: {e}")
                        result["errors"] += 1
                
                # Commit is automatic on context exit
                increment_metric("scanner_events_ingested_total", scanner.key, result["events_ingested"])
                
        except DatabaseError as e:
            # Database-level error - update per-scanner circuit breaker
            logger.error(f"Database error for scanner {scanner.key}: {e}")
            increment_metric("scanner_errors_total", scanner.key)
            breaker.record_failure(e)
            result["errors"] = 1
            return result
        
        result["success"] = True
        breaker.record_success()
        logger.info(f"Scanner {scanner.label} completed: {result['events_ingested']} events ingested")
        
    except Exception as e:
        logger.error(f"Scanner {scanner.label} failed: {e}", exc_info=True)
        increment_metric("scanner_errors_total", scanner.key)
        breaker.record_failure(e)
        result["errors"] = 1
    
    finally:
        result["runtime"] = time.time() - start_time
        increment_metric("scanner_runtime_seconds", scanner.key, result["runtime"])
    
    return result


def run_all_scanners(max_workers: int = 4, timeout_per_scanner: int = 300) -> Dict[str, Any]:
    """
    Run all enabled scanners in parallel with bounded concurrency.
    
    Features:
    - Per-scanner timeout protection
    - Health check before starting
    - Idle transaction cleanup
    - Comprehensive error handling
    
    Args:
        max_workers: Maximum number of parallel scanner executions
        timeout_per_scanner: Timeout per scanner in seconds (default 5 minutes)
        
    Returns:
        Aggregated results dict
    """
    start_time = time.time()
    
    # Pre-flight health check
    health = check_db_health()
    if health["status"] == "unhealthy":
        logger.error(f"Database unhealthy, attempting recovery before scanner run")
        if not reset_db_connections():
            logger.error("Database recovery failed, aborting scanner run")
            return {
                "timestamp": datetime.utcnow().isoformat(),
                "total_scanners": 0,
                "successful_scanners": 0,
                "total_events_ingested": 0,
                "total_errors": 1,
                "runtime_seconds": time.time() - start_time,
                "scanner_results": [],
                "error": "Database unhealthy and recovery failed"
            }
    
    # Clean up any idle transactions from previous runs
    cleaned = cleanup_idle_transactions()
    if cleaned > 0:
        logger.info(f"Cleaned up {cleaned} idle transactions before scanner run")
    
    tickers = get_tracked_tickers()
    if not tickers:
        logger.warning("No tracked tickers found, scanner run may produce no results")
    
    enabled_scanners = [s for s in SCANNERS if s.enabled]
    
    logger.info(f"Starting scanner run for {len(tickers)} tracked companies")
    logger.info(f"Running {len(enabled_scanners)} scanners with max {max_workers} workers")
    
    results = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all scanner jobs
        futures = {
            executor.submit(run_scanner, scanner, tickers): scanner
            for scanner in enabled_scanners
        }
        
        # Collect results as they complete with timeout handling
        for future in as_completed(futures, timeout=timeout_per_scanner * len(enabled_scanners)):
            scanner = futures[future]
            try:
                result = future.result(timeout=timeout_per_scanner)
                results.append(result)
            except FuturesTimeoutError:
                logger.error(f"Scanner {scanner.label} timed out after {timeout_per_scanner}s")
                increment_metric("scanner_timeouts_total", scanner.key)
                scanner_breakers.get(scanner.key).record_failure()
                results.append({
                    "scanner": scanner.key,
                    "success": False,
                    "errors": 1,
                    "events_ingested": 0,
                    "skip_reason": "Timeout"
                })
            except Exception as e:
                logger.error(f"Scanner {scanner.label} raised exception: {e}")
                scanner_breakers.get(scanner.key).record_failure(e)
                results.append({
                    "scanner": scanner.key,
                    "success": False,
                    "errors": 1,
                    "events_ingested": 0
                })
    
    # Aggregate results
    total_events = sum(r.get("events_ingested", 0) for r in results)
    total_errors = sum(r.get("errors", 0) for r in results)
    successful = sum(1 for r in results if r.get("success", False))
    skipped = sum(1 for r in results if r.get("skipped", False))
    
    summary = {
        "timestamp": datetime.utcnow().isoformat(),
        "total_scanners": len(results),
        "successful_scanners": successful,
        "skipped_scanners": skipped,
        "total_events_ingested": total_events,
        "total_errors": total_errors,
        "runtime_seconds": time.time() - start_time,
        "scanner_results": results,
        "health": check_db_health(),
        "circuit_breakers": scanner_breakers.get_all_stats(),
    }
    
    logger.info(
        f"Scanner run complete: {total_events} events ingested, "
        f"{total_errors} errors, {skipped} skipped, "
        f"{summary['runtime_seconds']:.2f}s"
    )
    
    return summary


def run_loop(interval_seconds: int = 600):
    """
    Run scanners continuously in a loop.
    
    Features:
    - Periodic health checks
    - Automatic recovery on failure
    - Graceful shutdown handling
    
    Args:
        interval_seconds: Sleep interval between runs (default 10 minutes)
    """
    logger.info(f"Starting continuous scanner loop (interval: {interval_seconds}s)")
    
    consecutive_failures = 0
    max_consecutive_failures = 5
    
    while True:
        try:
            summary = run_all_scanners()
            
            # Check for complete failure
            if summary.get("total_errors", 0) == summary.get("total_scanners", 0) and summary.get("total_scanners", 0) > 0:
                consecutive_failures += 1
                logger.warning(f"All scanners failed ({consecutive_failures}/{max_consecutive_failures})")
                
                if consecutive_failures >= max_consecutive_failures:
                    logger.error("Too many consecutive failures, attempting full reset")
                    reset_db_connections()
                    consecutive_failures = 0
            else:
                consecutive_failures = 0
                
        except Exception as e:
            logger.error(f"Error in scanner loop: {e}", exc_info=True)
            consecutive_failures += 1
            
            if consecutive_failures >= max_consecutive_failures:
                logger.error("Too many consecutive failures, attempting full reset")
                reset_db_connections()
                consecutive_failures = 0
        
        logger.info(f"Sleeping for {interval_seconds} seconds...")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Run Impact Radar scanners")
    parser.add_argument("--loop", action="store_true", help="Run continuously in a loop")
    parser.add_argument("--interval", type=int, default=600, help="Loop interval in seconds (default: 600)")
    parser.add_argument("--health", action="store_true", help="Run health check only")
    parser.add_argument("--reset", action="store_true", help="Reset database connections")
    
    args = parser.parse_args()
    
    if args.health:
        health = check_db_health()
        print("\n" + "="*60)
        print("Database Health Check")
        print("="*60)
        print(f"Status: {health['status']}")
        print(f"Connection Test: {health['connection_test']}")
        print(f"Latency: {health['latency_ms']}ms")
        if health['errors']:
            print(f"Errors: {', '.join(health['errors'])}")
        print("="*60)
    elif args.reset:
        print("Resetting database connections...")
        if reset_db_connections():
            print("Reset successful")
        else:
            print("Reset failed")
    elif args.loop:
        run_loop(interval_seconds=args.interval)
    else:
        summary = run_all_scanners()
        print("\n" + "="*60)
        print("Scanner Run Summary")
        print("="*60)
        print(f"Total scanners run: {summary['total_scanners']}")
        print(f"Successful: {summary['successful_scanners']}")
        print(f"Skipped: {summary.get('skipped_scanners', 0)}")
        print(f"Events ingested: {summary['total_events_ingested']}")
        print(f"Errors: {summary['total_errors']}")
        print(f"Runtime: {summary['runtime_seconds']:.2f}s")
        print("="*60)
