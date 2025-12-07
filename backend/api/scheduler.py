"""Background scheduler for scanners - refactored to use scanner catalog with rate limiting"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from sqlalchemy.exc import IntegrityError

from backend.database import SessionLocal, close_db_session
from backend.releaseradar.db.models import Event, Company, InsiderTransaction
from api.routers.stream import event_queue

# Import scanner catalog and implementations
from backend.scanners.catalog import SCANNERS
from backend.scanners.impl.sec_edgar import scan_sec_edgar
from backend.scanners.impl.sec_8k import scan_sec_8k
from backend.scanners.impl.sec_10q import scan_sec_10q
from backend.scanners.impl.earnings import scan_earnings_calls
from backend.scanners.impl.guidance import scan_guidance
from backend.scanners.impl.ma import scan_ma
from backend.scanners.impl.product_launch import scan_product_launch
from backend.scanners.impl.dividend import scan_dividend_buyback
from backend.scanners.impl.fda import scan_fda
from backend.scanners.impl.press import scan_press
from backend.releaseradar.scanners.form4_scanner import scan_form4_filings

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

# ============================================================================
# THREAD POOL ARCHITECTURE FOR SCANNER EXECUTION
# ============================================================================
# 
# Problem: Heavy SEC scanners were blocking fast scanners due to shared
# default thread pool, causing scanner interval violations (e.g., 15-min
# SEC 8-K scanner would be delayed by slow SEC EDGAR scans).
#
# Solution: Dedicated thread pools with timeout protection:
# - FAST_SCANNER_POOL: For scanners with 15-60 min intervals (4 workers)
# - SLOW_SCANNER_POOL: For heavy SEC scanners 120+ min intervals (8 workers)
#
# This ensures:
# 1. SEC scanners don't block other scanners
# 2. Scanner intervals are honored (15min for 8-K stays 15min)
# 3. Timeout protection prevents indefinite hangs
# 4. Error in one scanner doesn't crash others
#
# Future optimization: Convert SEC service to async httpx for true
# non-blocking I/O. Current thread pool approach is proven and stable.
# ============================================================================

FAST_SCANNER_POOL = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="scanner-fast-"
)
SLOW_SCANNER_POOL = ThreadPoolExecutor(
    max_workers=8,
    thread_name_prefix="scanner-slow-"
)

# Dedicated pool for ML pipeline jobs to prevent scanner starvation
# These jobs run at scheduled times and don't need to share with scanners
try:
    ML_JOB_POOL = ThreadPoolExecutor(
        max_workers=2,
        thread_name_prefix="ml-job-"
    )
except Exception as e:
    logger.warning(f"Failed to create ML_JOB_POOL, falling back to SLOW_SCANNER_POOL: {e}")
    ML_JOB_POOL = SLOW_SCANNER_POOL  # Fallback to shared pool if creation fails

# Track shutdown state to prevent repeated shutdown calls
_pools_shutdown = False

# Timeout configuration (in seconds)
FAST_SCANNER_TIMEOUT = 120  # 2 minutes for fast scanners
SLOW_SCANNER_TIMEOUT = 1800  # 30 minutes for slow scanners (needed for 1000+ companies)

# Scanner function registry mapping fn_name to actual function
SCANNER_FUNCTIONS: Dict[str, Callable] = {
    'scan_sec_edgar': scan_sec_edgar,
    'scan_sec_8k': scan_sec_8k,
    'scan_sec_10q': scan_sec_10q,
    'scan_earnings_calls': scan_earnings_calls,
    'scan_guidance': scan_guidance,
    'scan_ma': scan_ma,
    'scan_product_launch': scan_product_launch,
    'scan_dividend_buyback': scan_dividend_buyback,
    'scan_fda': scan_fda,
    'scan_press': scan_press,
    'scan_form4_filings': scan_form4_filings
}


async def run_scanner(
    scanner_key: str,
    scanner_fn: Callable,
    scanner_label: str,
    scanner_interval: int,
    use_slow_pool: bool = False
):
    """
    Generic async wrapper to run any scanner from the catalog.
    
    This function:
    1. Fetches tracked companies from the database
    2. Calls the scanner function (which returns normalized events)
    3. Inserts events into the database with deduplication via raw_id
    4. Pushes new events to the SSE queue for live updates
    
    Features dedicated thread pools and timeout protection to prevent
    heavy scanners from blocking fast scanners.
    
    Args:
        scanner_key: Scanner key from catalog (e.g., 'sec_8k')
        scanner_fn: Scanner function to call
        scanner_label: Human-readable scanner label (e.g., 'SEC 8-K')
        scanner_interval: Scanner interval in minutes (used to determine pool/timeout)
        use_slow_pool: Force slow pool for heavy scanners regardless of interval
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Running {scanner_label} scanner...")
        
        # Fetch tracked companies
        companies = db.query(Company).filter(Company.tracked.is_(True)).all()
        
        if not companies:
            logger.warning(f"{scanner_label}: No tracked companies found")
            return
                
        # Convert companies to format expected by scanners
        tickers = [c.ticker for c in companies]
        company_dict = {
            c.ticker: {
                'name': c.name,
                'sector': c.sector if c.sector is not None else 'Unknown',
                'industry': c.industry
            }
            for c in companies
        }
        
        logger.info(f"{scanner_label}: Scanning {len(tickers)} companies")
        
        # Determine thread pool and timeout based on scanner configuration
        # use_slow_pool flag forces slow pool for heavy scanners (like SEC 8-K with 1000+ companies)
        # Fast scanners (interval <= 60 min) use fast pool, unless use_slow_pool is set
        # Slow scanners (interval > 60 min) always use slow pool
        if use_slow_pool or scanner_interval > 60:
            executor = SLOW_SCANNER_POOL
            timeout = SLOW_SCANNER_TIMEOUT
            pool_type = "slow"
        else:
            executor = FAST_SCANNER_POOL
            timeout = FAST_SCANNER_TIMEOUT
            pool_type = "fast"
        
        logger.debug(
            f"{scanner_label}: Using {pool_type} pool "
            f"(interval={scanner_interval}min, timeout={timeout}s)"
        )
        
        # Call the scanner function with dedicated thread pool and timeout protection
        loop = asyncio.get_event_loop()
        try:
            normalized_events = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    scanner_fn,
                    tickers,
                    company_dict
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(
                f"{scanner_label} timed out after {timeout}s - "
                f"This indicates the scanner is taking too long. "
                f"Consider optimizing or increasing timeout."
            )
            return
        except Exception as e:
            logger.error(
                f"{scanner_label} execution failed: {e}",
                exc_info=True
            )
            return
        
        if not normalized_events:
            logger.info(f"{scanner_label}: No new events found")
            return
                
        # Insert events into database with deduplication
        new_event_count = 0
        duplicate_count = 0
        
        for event_data in normalized_events:
            try:
                # Check if event already exists by raw_id (primary deduplication)
                existing_event = db.query(Event).filter(
                    Event.raw_id == event_data.get('raw_id')
                ).first()
                
                if existing_event:
                    duplicate_count += 1
                    continue
                
                # Create new event from normalized data
                event = Event(
                    ticker=event_data['ticker'],
                    company_name=event_data['company_name'],
                    event_type=event_data['event_type'],
                    title=event_data['title'],
                    description=event_data.get('description'),
                    date=event_data['date'],
                    source=event_data['source'],
                    source_url=event_data.get('source_url'),
                    raw_id=event_data.get('raw_id'),
                    source_scanner=event_data.get('source_scanner'),
                    sector=event_data.get('sector'),
                    # Info tier classification (already set by normalize_event)
                    info_tier=event_data.get('info_tier', 'primary'),
                    info_subtype=event_data.get('info_subtype'),
                    # Default scoring values (will be updated below)
                    impact_score=50,
                    direction='neutral',
                    confidence=0.5
                )
                
                db.add(event)
                db.flush()  # Flush to get event ID without committing
                
                # Apply deterministic impact scoring (primary scoring with proper direction analysis)
                try:
                    from backend.impact_scoring import score_event as impact_score_event
                    
                    # Get metadata from event_data (includes 8k_items for SEC filings)
                    metadata = event_data.get('metadata', {})
                    
                    # Use the fixed impact scoring system for consistent direction/confidence
                    impact_result = impact_score_event(
                        event_type=event.event_type,
                        title=event.title,
                        description=event.description or "",
                        sector=event.sector,
                        metadata=metadata
                    )
                    
                    # Apply impact scoring results
                    event.impact_score = impact_result.get('impact_score', 50)
                    event.direction = impact_result.get('direction', 'neutral')
                    event.confidence = impact_result.get('confidence', 0.5)
                    event.rationale = impact_result.get('rationale', '')
                    
                    logger.info(f"Impact scored event {event.id} ({event.ticker} {event.event_type}): score={event.impact_score}, direction={event.direction}, confidence={event.confidence:.2f}")
                    
                except Exception as e:
                    logger.warning(f"Impact scoring failed for event {event.ticker} {event.event_type}: {e}, trying context scoring")
                
                # Enhance with context-aware scoring (market factors, sector beta, etc.)
                try:
                    from backend.analytics.scoring import compute_event_score
                    
                    score_result = compute_event_score(
                        event_id=event.id,
                        ticker=event.ticker,
                        event_type=event.event_type,
                        event_date=event.date,
                        source=event.source,
                        sector=event.sector,
                        db=db
                    )
                    
                    # Use context score if higher than impact score (context can boost but not reduce)
                    context_score = score_result.get('final_score', 50)
                    if context_score > event.impact_score:
                        event.impact_score = context_score
                        # Append context rationale
                        context_rationale = '; '.join(score_result.get('rationale', []))
                        if context_rationale:
                            event.rationale = f"{event.rationale}; Context: {context_rationale}"
                    
                    # Update confidence if context provides higher confidence
                    context_confidence = score_result.get('confidence', 50) / 100.0
                    if context_confidence > event.confidence:
                        event.confidence = context_confidence
                    
                    logger.debug(f"Context scored event {event.id} ({event.ticker} {event.event_type}): score={event.impact_score}, direction={event.direction}")
                except Exception as e:
                    logger.warning(f"Context scoring failed for event {event.ticker} {event.event_type}: {e}")
                
                # Apply ML predictions
                try:
                    from releaseradar.ml.serving import MLScoringService
                    ml_service = MLScoringService(db)
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
                                logger.debug(f"ML predicted negative return ({ml_prediction.predicted_return_1d:.2f}%), overriding direction to 'negative'")
                            elif ml_prediction.predicted_return_1d > 1.0 and ml_prediction.ml_confidence > 0.5:
                                event.direction = 'positive'
                                logger.debug(f"ML predicted positive return ({ml_prediction.predicted_return_1d:.2f}%), overriding direction to 'positive'")
                        
                        logger.info(
                            f"ML prediction applied for event {event.id}: "
                            f"base={event.impact_score}, ml={ml_prediction.ml_adjusted_score}, "
                            f"delta={ml_prediction.delta_applied:.1f}, conf={ml_prediction.ml_confidence:.2f}, "
                            f"source={ml_prediction.model_source}"
                        )
                    else:
                        logger.debug(f"No ML prediction available for event {event.id} ({event.event_type}), using deterministic scoring only")
                except Exception as e:
                    logger.warning(f"ML scoring failed for event {event.id}: {e}, continuing with deterministic scoring")
                
                db.commit()
                db.refresh(event)
                
                # Push to SSE queue for live updates
                await event_queue.put({
                    "type": "discovery",
                    "ticker": event.ticker,
                    "company_name": event.company_name,
                    "title": event.title,
                    "event_type": event.event_type,
                    "info_tier": event.info_tier,
                    "info_subtype": event.info_subtype,
                    "impact_score": event.impact_score,
                    "direction": event.direction,
                    "timestamp": event.date.isoformat()
                })
                
                new_event_count += 1
                logger.info(f"{scanner_label}: Created event for {event.ticker}: {event.title[:60]}")
                
            except IntegrityError as e:
                # Unique constraint violation (duplicate)
                db.rollback()
                duplicate_count += 1
                logger.debug(f"{scanner_label}: Duplicate event skipped: {event_data.get('title', 'Unknown')[:50]}")
                continue
            except Exception as e:
                db.rollback()
                logger.error(f"{scanner_label}: Error inserting event: {e}")
                continue
        
        # Log completion
        logger.info(
            f"{scanner_label} completed: {new_event_count} new events, "
            f"{duplicate_count} duplicates skipped"
        )
        
    except Exception as e:
        logger.error(f"{scanner_label} failed: {e}", exc_info=True)
    finally:
        close_db_session(db)


async def run_form4_scanner(
    scanner_key: str,
    scanner_fn: Callable,
    scanner_label: str,
    scanner_interval: int
):
    """
    Specialized async wrapper for Form 4 insider trading scanner.
    
    Handles InsiderTransaction records instead of Event records.
    Also creates Event records for significant insider activity.
    
    Features dedicated thread pools and timeout protection.
    
    Args:
        scanner_key: Scanner key ('form4_insider')
        scanner_fn: Form 4 scanner function
        scanner_label: Human-readable label ('Form 4 Insider Trading')
        scanner_interval: Scanner interval in minutes (used to determine pool/timeout)
    """
    db = SessionLocal()
    
    try:
        logger.info(f"Running {scanner_label} scanner...")
        
        # Form4 is a slow scanner (360 min interval) - use slow pool
        executor = SLOW_SCANNER_POOL
        timeout = SLOW_SCANNER_TIMEOUT
        
        logger.debug(
            f"{scanner_label}: Using slow pool "
            f"(interval={scanner_interval}min, timeout={timeout}s)"
        )
        
        # Call the Form 4 scanner function with timeout protection
        loop = asyncio.get_event_loop()
        try:
            insider_transactions = await asyncio.wait_for(
                loop.run_in_executor(
                    executor,
                    scanner_fn,
                    None,  # tickers (not used by Form 4 scanner)
                    None   # companies (not used by Form 4 scanner)
                ),
                timeout=timeout
            )
        except asyncio.TimeoutError:
            logger.error(
                f"{scanner_label} timed out after {timeout}s - "
                f"This indicates the scanner is taking too long."
            )
            return
        except Exception as e:
            logger.error(
                f"{scanner_label} execution failed: {e}",
                exc_info=True
            )
            return
        
        if not insider_transactions:
            logger.info(f"{scanner_label}: No new transactions found")
            return
        
        # Insert insider transactions into database
        inserted_count = 0
        duplicate_count = 0
        events_created_count = 0
        
        for trans_data in insider_transactions:
            try:
                # Check for duplicate using unique constraint
                existing = db.query(InsiderTransaction).filter(
                    InsiderTransaction.ticker == trans_data['ticker'],
                    InsiderTransaction.transaction_date == trans_data['transaction_date'],
                    InsiderTransaction.insider_name == trans_data['insider_name'],
                    InsiderTransaction.transaction_code == trans_data['transaction_code'],
                    InsiderTransaction.shares == trans_data['shares']
                ).first()
                
                if existing:
                    duplicate_count += 1
                    continue
                
                # Create InsiderTransaction record
                insider_transaction = InsiderTransaction(**trans_data)
                db.add(insider_transaction)
                db.flush()
                
                inserted_count += 1
                
                # Create Event for significant insider activity (sentiment > 0.7 or < -0.7)
                sentiment_score = trans_data.get('sentiment_score', 0)
                if abs(sentiment_score) >= 0.7:
                    # Check if company exists
                    company = db.query(Company).filter(Company.ticker == trans_data['ticker']).first()
                    sector = company.sector if company else None
                    
                    # Determine event type and direction
                    if sentiment_score >= 0.7:
                        event_type = 'insider_buy'
                        direction = 'positive'
                        title = f"Significant Insider Purchase by {trans_data['insider_title'] or trans_data['insider_name']}"
                    else:
                        event_type = 'insider_sell'
                        direction = 'negative'
                        title = f"Significant Insider Sale by {trans_data['insider_title'] or trans_data['insider_name']}"
                    
                    # Create unique raw_id for event
                    raw_id = f"form4_{trans_data['ticker']}_{trans_data['transaction_date']}_{trans_data['insider_name']}_{trans_data['transaction_code']}"
                    
                    # Check if event already exists
                    existing_event = db.query(Event).filter(Event.raw_id == raw_id).first()
                    
                    if not existing_event:
                        # Create Event record
                        from datetime import timezone as tz
                        event = Event(
                            ticker=trans_data['ticker'],
                            company_name=trans_data['company_name'],
                            event_type=event_type,
                            title=title,
                            description=trans_data['sentiment_rationale'],
                            date=datetime.combine(trans_data['transaction_date'], datetime.min.time()).replace(tzinfo=tz.utc),
                            source='SEC Form 4',
                            source_url=trans_data['form_4_url'],
                            raw_id=raw_id,
                            source_scanner='form4',
                            sector=sector,
                            impact_score=int(abs(sentiment_score) * 100),
                            direction=direction,
                            confidence=abs(sentiment_score),
                            rationale=trans_data['sentiment_rationale'],
                            info_tier='secondary',
                            info_subtype='insider_trading'
                        )
                        
                        db.add(event)
                        events_created_count += 1
                        
                        # Push to SSE queue for live updates
                        await event_queue.put({
                            "type": "insider_activity",
                            "ticker": event.ticker,
                            "company_name": event.company_name,
                            "title": event.title,
                            "event_type": event.event_type,
                            "sentiment_score": sentiment_score,
                            "impact_score": event.impact_score,
                            "direction": event.direction,
                            "timestamp": event.date.isoformat()
                        })
                
                db.commit()
            
            except IntegrityError:
                db.rollback()
                duplicate_count += 1
                logger.debug(f"{scanner_label}: Duplicate transaction skipped: {trans_data['ticker']} {trans_data['insider_name']}")
            except Exception as e:
                db.rollback()
                logger.error(f"{scanner_label}: Error saving transaction: {e}")
                continue
        
        # Log completion
        logger.info(
            f"{scanner_label} completed: {inserted_count} transactions inserted, "
            f"{duplicate_count} duplicates skipped, {events_created_count} events created"
        )
        
    except Exception as e:
        logger.error(f"{scanner_label} failed: {e}", exc_info=True)
    finally:
        close_db_session(db)


async def test_scheduler_job():
    """Test job that runs every 30 seconds to verify scheduler is working"""
    logger.info("✅ SCHEDULER TEST JOB EXECUTED - Scheduler is working!")


async def run_ml_scoring_job():
    """
    Apply Market Echo Engine ML scores to new events.
    
    This job runs hourly to ensure all newly ingested events receive ML-adjusted scores.
    The Market Echo Engine provides probabilistic predictions based on historical patterns.
    """
    import sys
    sys.path.insert(0, 'backend')
    
    loop = asyncio.get_event_loop()
    
    try:
        def _score_events():
            """Run ML scoring in thread pool to avoid blocking"""
            from sqlalchemy import select
            from releaseradar.db.session import get_db_transaction
            from releaseradar.db.models import Event
            from releaseradar.ml.serving import MLScoringService
            from datetime import datetime, timedelta
            
            success_count = 0
            fail_count = 0
            
            with get_db_transaction() as db:
                # Get events from last 7 days that need ML scoring
                cutoff = datetime.utcnow() - timedelta(days=7)
                events = list(db.execute(
                    select(Event)
                    .where(Event.date >= cutoff)
                    .where(Event.ml_adjusted_score.is_(None))
                    .order_by(Event.date.desc())
                ).scalars().all())
                
                if not events:
                    logger.info("ML Scoring: No events need scoring")
                    return {"success": True, "scored": 0, "failed": 0}
                
                logger.info(f"ML Scoring: Found {len(events)} events to score")
                
                scoring_service = MLScoringService(db)
                
                for event in events:
                    try:
                        prediction = scoring_service.predict_single(
                            event.id, 
                            horizon='1d', 
                            confidence_threshold=0.1
                        )
                        
                        if prediction:
                            event.ml_adjusted_score = prediction.ml_adjusted_score
                            event.ml_confidence = prediction.ml_confidence
                            event.ml_model_version = prediction.ml_model_version
                            success_count += 1
                    except Exception as e:
                        logger.warning(f"ML Scoring: Error scoring event {event.id}: {e}")
                        fail_count += 1
                
                db.commit()
                
            return {"success": True, "scored": success_count, "failed": fail_count}
        
        # Run in thread pool to avoid blocking the async event loop
        result = await loop.run_in_executor(SLOW_SCANNER_POOL, _score_events)
        
        logger.info(
            f"ML Scoring completed: {result['scored']} events scored, "
            f"{result['failed']} failed"
        )
        
    except Exception as e:
        logger.error(f"ML Scoring job failed: {e}", exc_info=True)


async def run_ml_etl_pipeline_job():
    """
    Run the ML ETL pipeline to label outcomes and extract features.
    
    This job runs daily at 6 AM UTC to:
    1. Label yesterday's events with realized price movements
    2. Compute EventStats from labeled outcomes
    3. Extract ML features for training
    
    Critical for the Market Echo Engine's accuracy tracking promise.
    Uses dedicated ML_JOB_POOL to prevent scanner starvation.
    """
    import sys
    sys.path.insert(0, 'backend')
    
    loop = asyncio.get_event_loop()
    
    try:
        def _run_etl():
            """Run ETL pipeline in dedicated ML thread pool"""
            try:
                from jobs.ml_learning_pipeline import run_ml_etl_pipeline
                return run_ml_etl_pipeline(lookback_days=60)
            except Exception as e:
                logger.error(f"ML ETL Pipeline execution error: {e}", exc_info=True)
                return {"success": False, "error": str(e)}
        
        result = await loop.run_in_executor(ML_JOB_POOL, _run_etl)
        
        if result.get('success'):
            stages = result.get('stages', {})
            outcomes = stages.get('label_outcomes', {})
            logger.info(
                f"ML ETL Pipeline completed: "
                f"{outcomes.get('outcomes_created', 0)} outcomes labeled, "
                f"{outcomes.get('outcomes_skipped', 0)} skipped"
            )
        else:
            logger.warning(f"ML ETL Pipeline completed with issues: {result}")
            
    except Exception as e:
        logger.error(f"ML ETL Pipeline job failed: {e}", exc_info=True)


async def run_drift_monitoring_job():
    """
    Run drift monitoring to track model performance.
    
    Computes rolling window accuracy metrics (7d, 30d, 90d) and creates 
    alerts when accuracy drops >5% from baseline.
    
    Critical for the accuracy tracking promise in marketing.
    Uses dedicated ML_JOB_POOL with proper DB session cleanup.
    """
    import sys
    sys.path.insert(0, 'backend')
    
    loop = asyncio.get_event_loop()
    
    try:
        def _run_drift_check():
            """Run drift monitoring in dedicated ML thread pool with safe DB handling"""
            from releaseradar.db.session import get_db_transaction
            from releaseradar.ml.monitoring.drift_monitor import DriftMonitor
            
            db = None
            try:
                with get_db_transaction() as db:
                    monitor = DriftMonitor(db)
                    
                    # run_drift_check with no args checks all active models for all horizons
                    results = monitor.run_drift_check()
                    
                    # Count results
                    alerts_created = sum(1 for r in results if r.get('has_drift', False))
                    models_checked = len(set((r.get('model_id'), r.get('horizon')) for r in results))
                    
                    return {
                        "success": True, 
                        "models_checked": models_checked,
                        "alerts_created": alerts_created,
                        "results": results
                    }
            except Exception as e:
                logger.error(f"Drift monitoring execution error: {e}", exc_info=True)
                return {
                    "success": False, 
                    "error": str(e),
                    "models_checked": 0,
                    "alerts_created": 0
                }
        
        result = await loop.run_in_executor(ML_JOB_POOL, _run_drift_check)
        
        if result.get('success'):
            logger.info(
                f"Drift Monitoring completed: "
                f"{result.get('models_checked', 0)} model/horizon combos checked, "
                f"{result.get('alerts_created', 0)} drift alerts"
            )
        else:
            logger.warning(f"Drift Monitoring completed with error: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Drift Monitoring job failed: {e}", exc_info=True)


async def run_model_retraining_job():
    """
    Check if model retraining is needed and run if recommended.
    
    This job runs weekly to:
    1. Check if enough new labeled data exists (>100 samples)
    2. Evaluate if model performance has degraded
    3. Retrain models if improvement is expected
    
    Delivers on the "continuously improving predictions" promise.
    Uses dedicated ML_JOB_POOL with proper error handling.
    """
    import sys
    sys.path.insert(0, 'backend')
    
    loop = asyncio.get_event_loop()
    
    try:
        def _run_retraining():
            """Run retraining check in dedicated ML thread pool"""
            try:
                from jobs.daily_ml_retraining import check_retraining_needed, run_daily_ml_retraining
                
                # Check if retraining is recommended
                rec_1d = check_retraining_needed("1d")
                rec_5d = check_retraining_needed("5d")
                
                if rec_1d.get('should_retrain') or rec_5d.get('should_retrain'):
                    logger.info(
                        f"Retraining recommended - 1d: {rec_1d.get('reason', 'N/A')}, "
                        f"5d: {rec_5d.get('reason', 'N/A')}"
                    )
                    result = run_daily_ml_retraining()
                    return {"success": result.get('success', False), "retrained": True, "result": result}
                else:
                    return {
                        "success": True, 
                        "retrained": False, 
                        "reason": f"1d: {rec_1d.get('reason', 'N/A')}, 5d: {rec_5d.get('reason', 'N/A')}"
                    }
            except Exception as e:
                logger.error(f"Model retraining execution error: {e}", exc_info=True)
                return {"success": False, "retrained": False, "error": str(e)}
        
        result = await loop.run_in_executor(ML_JOB_POOL, _run_retraining)
        
        if result.get('success'):
            if result.get('retrained'):
                logger.info(f"Model Retraining completed: {result.get('result', {})}")
            else:
                logger.info(f"Model Retraining skipped: {result.get('reason', 'Not needed')}")
        else:
            logger.warning(f"Model Retraining failed: {result.get('error')}")
            
    except Exception as e:
        logger.error(f"Model Retraining job failed: {e}", exc_info=True)


def start_scheduler():
    """
    Start the background scheduler with all scanners from the catalog.
    
    Registers all enabled scanners from SCANNERS with their configured intervals.
    Each scanner uses the shared SEC service and info_tier classification.
    """
    registered_count = 0
    
    # Add a test job that runs every 30 seconds to verify scheduler is working
    scheduler.add_job(
        test_scheduler_job,
        trigger=IntervalTrigger(seconds=30),
        id='test_scheduler',
        name='Scheduler Test Job',
        replace_existing=True
    )
    logger.info("Added test job to verify scheduler execution (runs every 30 seconds)")
    
    # Add ML scoring job to run every hour - applies Market Echo Engine scores to new events
    scheduler.add_job(
        run_ml_scoring_job,
        trigger=IntervalTrigger(hours=1),
        id='ml_scoring',
        name='Market Echo ML Scoring',
        replace_existing=True
    )
    logger.info("Added Market Echo ML Scoring job (runs every hour)")
    
    # Add ML ETL Pipeline - runs daily at 6 AM UTC to label outcomes and extract features
    # Critical for collecting price movements needed for accuracy tracking
    scheduler.add_job(
        run_ml_etl_pipeline_job,
        trigger=CronTrigger(hour=6, minute=0),
        id='ml_etl_pipeline',
        name='ML ETL Pipeline (Outcome Labeling)',
        replace_existing=True
    )
    logger.info("Added ML ETL Pipeline job (runs daily at 6 AM UTC)")
    
    # Add Drift Monitoring - runs daily at 9 AM UTC after ETL completes
    # Tracks model accuracy over rolling windows (7d, 30d, 90d)
    scheduler.add_job(
        run_drift_monitoring_job,
        trigger=CronTrigger(hour=9, minute=0),
        id='drift_monitoring',
        name='Model Drift Monitoring',
        replace_existing=True
    )
    logger.info("Added Drift Monitoring job (runs daily at 9 AM UTC)")
    
    # Add Model Retraining - runs weekly on Sunday at 7 AM UTC
    # Automatically retrains models when enough new data is available
    scheduler.add_job(
        run_model_retraining_job,
        trigger=CronTrigger(day_of_week='sun', hour=7, minute=0),
        id='model_retraining',
        name='Weekly Model Retraining',
        replace_existing=True
    )
    logger.info("Added Model Retraining job (runs weekly on Sunday at 7 AM UTC)")
    
    def _create_scanner_wrapper(
        key: str,
        fn: callable,
        label: str,
        interval: int,
        is_form4: bool = False,
        use_slow_pool: bool = False
    ):
        """Factory function to create properly-scoped scanner job functions"""
        if is_form4:
            async def scanner_job():
                await run_form4_scanner(key, fn, label, interval)
        else:
            async def scanner_job():
                await run_scanner(key, fn, label, interval, use_slow_pool)
        return scanner_job
    
    for scanner in SCANNERS:
        if not scanner.enabled:
            logger.info(f"Skipping disabled scanner: {scanner.label}")
            continue
        
        # Get scanner function
        scanner_fn = SCANNER_FUNCTIONS.get(scanner.fn_name)
        
        if scanner_fn is None:
            logger.warning(f"Scanner function not found: {scanner.fn_name} for {scanner.label}")
            continue
        
        # Create async wrapper with scanner-specific context using factory function
        # This ensures each scanner gets its own properly-scoped function
        # Interval is passed to determine thread pool and timeout
        scanner_job_fn = _create_scanner_wrapper(
            key=scanner.key,
            fn=scanner_fn,
            label=scanner.label,
            interval=scanner.interval_minutes,
            is_form4=(scanner.key == 'form4_insider'),
            use_slow_pool=scanner.use_slow_pool
        )
        
        # Register scanner with APScheduler
        scheduler.add_job(
            scanner_job_fn,
            trigger=IntervalTrigger(minutes=scanner.interval_minutes),
            id=scanner.key,
            name=scanner.label,
            replace_existing=True
        )
        
        registered_count += 1
        logger.info(
            f"Registered scanner: {scanner.label} "
            f"(key={scanner.key}, interval={scanner.interval_minutes}min)"
        )
    
    scheduler.start()
    logger.info(f"Scheduler started with {registered_count} scanners")
    logger.info(f"Scheduler state: {scheduler.state}")
    logger.info(f"Total jobs registered: {len(scheduler.get_jobs())}")
    
    # Log all registered scanners
    for scanner in SCANNERS:
        if scanner.enabled and scanner.fn_name in SCANNER_FUNCTIONS:
            logger.info(f"  - {scanner.label} ({scanner.interval_minutes} min)")
    
    logger.info("Background scanners started")
    
    # Schedule immediate execution of all scanners with staggered delays
    # This ensures scanners run on startup without waiting for the first interval
    async def run_initial_scans():
        """Run all scanners on startup with staggered delays to avoid overwhelming APIs"""
        import asyncio
        
        delay_seconds = 60  # Start 1 minute after server startup
        stagger_seconds = 30  # 30 seconds between each scanner
        
        logger.info(f"Scheduling initial scanner runs starting in {delay_seconds} seconds...")
        
        await asyncio.sleep(delay_seconds)
        
        for scanner in SCANNERS:
            if not scanner.enabled:
                continue
            
            scanner_fn = SCANNER_FUNCTIONS.get(scanner.fn_name)
            if scanner_fn is None:
                continue
            
            try:
                logger.info(f"Initial scan: Running {scanner.label}...")
                if scanner.key == 'form4_insider':
                    await run_form4_scanner(scanner.key, scanner_fn, scanner.label, scanner.interval_minutes)
                else:
                    await run_scanner(scanner.key, scanner_fn, scanner.label, scanner.interval_minutes, scanner.use_slow_pool)
                logger.info(f"Initial scan: {scanner.label} completed")
            except Exception as e:
                logger.error(f"Initial scan: {scanner.label} failed: {e}")
            
            # Stagger to avoid rate limiting
            await asyncio.sleep(stagger_seconds)
        
        logger.info("Initial scanner runs completed")
    
    # Start the initial scans in background
    asyncio.create_task(run_initial_scans())


def stop_scheduler():
    """Stop the background scheduler and cleanup thread pools"""
    global _pools_shutdown
    
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler stopped")
    
    # Guard against repeated shutdown calls
    if _pools_shutdown:
        logger.debug("Thread pools already shut down")
        return
    
    # Cleanup thread pools with safe shutdown handling
    logger.info("Shutting down thread pools...")
    try:
        FAST_SCANNER_POOL.shutdown(wait=True, cancel_futures=True)
    except RuntimeError as e:
        logger.debug(f"FAST_SCANNER_POOL shutdown skipped: {e}")
    
    try:
        SLOW_SCANNER_POOL.shutdown(wait=True, cancel_futures=True)
    except RuntimeError as e:
        logger.debug(f"SLOW_SCANNER_POOL shutdown skipped: {e}")
    
    try:
        # Only shutdown ML_JOB_POOL if it's not a fallback to SLOW_SCANNER_POOL
        if ML_JOB_POOL is not SLOW_SCANNER_POOL:
            ML_JOB_POOL.shutdown(wait=True, cancel_futures=True)
    except RuntimeError as e:
        logger.debug(f"ML_JOB_POOL shutdown skipped: {e}")
    
    _pools_shutdown = True
    logger.info("Thread pools shut down successfully")
