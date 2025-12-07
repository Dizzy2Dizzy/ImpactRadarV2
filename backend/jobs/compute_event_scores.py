"""
Nightly job to compute event scores for all events.

Runs as scheduled background task to ensure all events have scores computed.
Idempotent - can be run multiple times safely.

Now includes ML scoring integration (Wave L) - after deterministic scoring,
attempts ML prediction to enhance scores with learned patterns.
"""

import logging
from datetime import datetime
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from releaseradar.db.models import Event, EventScore, EventStats
from releaseradar.db.session import get_db_context, get_db_transaction
from analytics.scoring import compute_event_score
from services.market_data_service import MarketDataService

logger = logging.getLogger(__name__)

# Global market data service instance (reused across events for cache efficiency)
_market_data_service = None


def get_market_data_service() -> MarketDataService:
    """Get or create market data service singleton."""
    global _market_data_service
    if _market_data_service is None:
        _market_data_service = MarketDataService()
    return _market_data_service


def apply_ml_scoring(db: Session, event: Event) -> bool:
    """
    Apply ML scoring enhancement to an event after deterministic scoring.
    
    This function is designed to never break the deterministic scoring flow.
    All exceptions are caught and logged, returning False on failure.
    
    Args:
        db: Database session
        event: Event object to enhance with ML scoring
    
    Returns:
        True if ML scoring was successfully applied, False otherwise
    """
    try:
        from releaseradar.ml.serving import MLScoringService
        
        ml_service = MLScoringService(db)
        
        prediction_1d = ml_service.predict_single(
            event_id=event.id,
            horizon="1d",
            confidence_threshold=0.3,
            max_delta=20,
            use_blending=True
        )
        
        if prediction_1d:
            event.ml_adjusted_score = prediction_1d.ml_adjusted_score
            event.ml_confidence = prediction_1d.ml_confidence
            event.ml_model_version = prediction_1d.ml_model_version
            event.model_source = prediction_1d.model_source
            event.delta_applied = prediction_1d.delta_applied
            
            logger.info(
                f"ML scoring applied to event {event.id} ({event.ticker}): "
                f"base_score={prediction_1d.base_score}, "
                f"ml_adjusted={prediction_1d.ml_adjusted_score}, "
                f"confidence={prediction_1d.ml_confidence:.2f}, "
                f"delta={prediction_1d.delta_applied:.1f}, "
                f"model={prediction_1d.ml_model_version}, "
                f"source={prediction_1d.model_source}"
            )
            
            prediction_5d = ml_service.predict_single(
                event_id=event.id,
                horizon="5d",
                confidence_threshold=0.3,
                max_delta=20,
                use_blending=True
            )
            
            if prediction_5d:
                logger.debug(
                    f"5d ML prediction for event {event.id}: "
                    f"adjusted={prediction_5d.ml_adjusted_score}, "
                    f"confidence={prediction_5d.ml_confidence:.2f}"
                )
            
            return True
        else:
            logger.debug(
                f"No ML prediction available for event {event.id} ({event.ticker}, {event.event_type}) - "
                f"using deterministic scoring only"
            )
            if not event.model_source:
                event.model_source = "deterministic"
            return False
            
    except ImportError as e:
        logger.warning(f"ML scoring module not available: {e} - using deterministic scoring")
        if not event.model_source:
            event.model_source = "deterministic"
        return False
    except Exception as e:
        logger.warning(
            f"ML scoring failed for event {event.id}: {e} - "
            f"deterministic scoring preserved"
        )
        return False


def compute_scores_for_event(db: Session, event: Event) -> Optional[EventScore]:
    """
    Compute and upsert score for a single event.
    
    Args:
        db: Database session
        event: Event object to score
    
    Returns:
        EventScore object (created or updated)
    """
    try:
        # Fetch historical stats for confidence calculation
        stats = db.execute(
            select(EventStats).where(
                EventStats.ticker == event.ticker,
                EventStats.event_type == event.event_type
            )
        ).scalar_one_or_none()
        
        sample_size = stats.sample_size if stats else None
        
        # Fetch market data for enhanced scoring
        market_service = get_market_data_service()
        beta = market_service.get_beta(event.ticker)
        atr_percentile = market_service.get_atr_percentile(event.ticker)
        spy_returns = market_service.get_spy_returns()
        
        # Log market data availability for debugging
        market_data_available = beta is not None or atr_percentile is not None or spy_returns is not None
        if market_data_available:
            logger.debug(
                f"Market data for {event.ticker}: beta={beta:.2f if beta else 'N/A'}, "
                f"atr_pct={atr_percentile:.1f if atr_percentile else 'N/A'}, "
                f"spy_5d={spy_returns.get('5d', 0)*100:.2f}% if spy_returns else 'N/A'"
            )
        
        # Compute score using engine with market data
        score_result = compute_event_score(
            event_id=event.id,
            ticker=event.ticker,
            event_type=event.event_type,
            event_date=event.date,
            source=event.source,
            sector=event.sector,
            db=db,
            sample_size=sample_size,
            beta=beta,
            atr_percentile=atr_percentile,
            spy_returns=spy_returns,
            data_completeness="full" if sample_size and sample_size > 0 else "partial"
        )
        
        # Check if score already exists
        existing_score = db.execute(
            select(EventScore).where(EventScore.event_id == event.id)
        ).scalar_one_or_none()
        
        # Extract factors
        factors = score_result.get("factors", {})
        
        if existing_score:
            # Update existing score
            existing_score.ticker = event.ticker
            existing_score.event_type = event.event_type
            existing_score.base_score = score_result["base_score"]
            existing_score.context_score = score_result["context_score"]
            existing_score.final_score = score_result["final_score"]
            existing_score.confidence = score_result["confidence"]
            existing_score.rationale = "\n".join(score_result["rationale"])
            existing_score.factor_sector = factors.get("sector", 0)
            existing_score.factor_volatility = factors.get("volatility", 0)
            existing_score.factor_earnings_proximity = factors.get("earnings_proximity", 0)
            existing_score.factor_market_mood = factors.get("market_mood", 0)
            existing_score.factor_after_hours = factors.get("after_hours", 0)
            existing_score.factor_duplicate_penalty = factors.get("duplicate_penalty", 0)
            existing_score.computed_at = datetime.utcnow()
            
            # Broadcast score update via WebSocket
            try:
                from api.websocket.hub import broadcast_event_scored_sync
                score_data = {
                    "final_score": score_result["final_score"],
                    "confidence": score_result["confidence"],
                    "direction": event.direction,
                    "computed_at": existing_score.computed_at,
                }
                broadcast_event_scored_sync(event.id, score_data)
            except Exception as e:
                logger.warning(f"Failed to broadcast event.scored via WebSocket: {e}")
            
            # Trigger alert dispatcher for score upgrade
            try:
                from alerts.dispatch import dispatch_alerts_for_event
                dispatch_alerts_for_event(event.id, db)
            except Exception as e:
                logger.warning(f"Failed to dispatch alerts for event {event.id}: {e}")
            
            logger.debug(f"Updated score for event {event.id}: {score_result['final_score']}")
            
            apply_ml_scoring(db, event)
            
            return existing_score
        else:
            # Create new score
            new_score = EventScore(
                event_id=event.id,
                ticker=event.ticker,
                event_type=event.event_type,
                base_score=score_result["base_score"],
                context_score=score_result["context_score"],
                final_score=score_result["final_score"],
                confidence=score_result["confidence"],
                rationale="\n".join(score_result["rationale"]),
                factor_sector=factors.get("sector", 0),
                factor_volatility=factors.get("volatility", 0),
                factor_earnings_proximity=factors.get("earnings_proximity", 0),
                factor_market_mood=factors.get("market_mood", 0),
                factor_after_hours=factors.get("after_hours", 0),
                factor_duplicate_penalty=factors.get("duplicate_penalty", 0),
                computed_at=datetime.utcnow()
            )
            db.add(new_score)
            
            # Broadcast score update via WebSocket
            try:
                from api.websocket.hub import broadcast_event_scored_sync
                score_data = {
                    "final_score": score_result["final_score"],
                    "confidence": score_result["confidence"],
                    "direction": event.direction,
                    "computed_at": new_score.computed_at,
                }
                broadcast_event_scored_sync(event.id, score_data)
            except Exception as e:
                logger.warning(f"Failed to broadcast event.scored via WebSocket: {e}")
            
            # Trigger alert dispatcher for new score
            try:
                from alerts.dispatch import dispatch_alerts_for_event
                dispatch_alerts_for_event(event.id, db)
            except Exception as e:
                logger.warning(f"Failed to dispatch alerts for event {event.id}: {e}")
            
            logger.debug(f"Created score for event {event.id}: {score_result['final_score']}")
            
            apply_ml_scoring(db, event)
            
            return new_score
            
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to compute score for event {event.id}: {e}")
        return None


def recompute_all_scores(
    db: Optional[Session] = None,
    ticker: Optional[str] = None,
    limit: Optional[int] = None,
    force: bool = False
) -> int:
    """
    Recompute scores for all events (or filtered subset).
    
    Args:
        db: Database session (creates new if None)
        ticker: Filter by ticker (optional)
        limit: Maximum number of events to process (optional)
        force: If True, recompute even if score exists
    
    Returns:
        Number of scores computed
    """
    managed_session = db is None
    
    if managed_session:
        with get_db_transaction() as db:
            return _recompute_scores_impl(db, ticker, limit, force, managed_session)
    else:
        return _recompute_scores_impl(db, ticker, limit, force, managed_session)


def _recompute_scores_impl(
    db: Session,
    ticker: Optional[str],
    limit: Optional[int],
    force: bool,
    managed_session: bool
) -> int:
    """Internal implementation of score recomputation."""
    try:
        # Build query
        query = select(Event).order_by(Event.date.desc())
        
        if ticker:
            query = query.where(Event.ticker == ticker)
        
        if not force:
            # Only process events without scores
            query = query.outerjoin(EventScore, Event.id == EventScore.event_id).where(
                EventScore.id.is_(None)
            )
        
        if limit:
            query = query.limit(limit)
        
        events = db.execute(query).scalars().all()
        
        logger.info(f"Processing {len(events)} events for scoring")
        
        processed = 0
        for event in events:
            result = compute_scores_for_event(db, event)
            if result:
                processed += 1
                
                # Commit in batches of 100 (only if we manage the session)
                if managed_session and processed % 100 == 0:
                    db.commit()
                    logger.info(f"Committed batch: {processed} scores processed")
        
        # Final commit (only if we manage the session)
        if managed_session:
            db.commit()
        
        logger.info(f"Completed scoring: {processed} events processed")
        
        return processed
        
    except Exception as e:
        logger.error(f"Error in batch scoring: {e}")
        db.rollback()
        raise


def run_nightly_scoring_job():
    """Main entry point for scheduled nightly scoring job."""
    logger.info("Starting nightly event scoring job")
    
    try:
        with get_db_transaction() as db:
            # Process all events without scores (limit to 1000 per run to avoid long runs)
            count = recompute_all_scores(db=db, limit=1000, force=False)
            
            logger.info(f"Nightly scoring job completed: {count} events scored")
        
    except Exception as e:
        logger.error(f"Nightly scoring job failed: {e}", exc_info=True)


if __name__ == "__main__":
    # For manual testing
    logging.basicConfig(level=logging.INFO)
    run_nightly_scoring_job()
