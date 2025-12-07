"""
Re-score all events using the sophisticated Market Echo Engine.

This script updates all existing events to use the proper scoring system
with context multipliers instead of placeholder 50/50 scores.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, close_db_session, Event
from analytics.scoring import compute_event_score
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rescore_all_events():
    """Re-score all events in the database using the sophisticated scoring engine."""
    # First, get list of event IDs to process
    db = get_db()
    try:
        # Get event IDs with default scores (impact_score=50 AND direction='neutral')
        event_ids = db.query(Event.id).filter(
            Event.impact_score == 50,
            Event.direction == 'neutral'
        ).all()
        event_ids = [eid[0] for eid in event_ids]
        total = len(event_ids)
        logger.info(f"Found {total} events with default scores to re-score")
    finally:
        close_db_session(db)
    
    updated = 0
    failed = 0
    
    # Process each event with its own session
    for i, event_id in enumerate(event_ids, 1):
        db_session = get_db()
        try:
            # Fetch event
            event = db_session.query(Event).filter(Event.id == event_id).first()
            if not event:
                logger.warning(f"Event {event_id} not found, skipping")
                failed += 1
                close_db_session(db_session)
                continue
            
            # Extract data for scoring
            data = {
                'id': event.id,
                'ticker': event.ticker,
                'event_type': event.event_type,
                'date': event.date,
                'source': event.source,
                'sector': event.sector,
                'info_tier': event.info_tier or 'primary',
                'info_subtype': event.info_subtype
            }
            
            # Compute sophisticated score
            score_result = compute_event_score(
                event_id=data['id'],
                ticker=data['ticker'],
                event_type=data['event_type'],
                event_date=data['date'],
                source=data['source'],
                sector=data['sector'],
                db=db_session,
                info_tier=data['info_tier'],
                info_subtype=data['info_subtype']
            )
            
            # Update event with computed scores
            event.impact_score = score_result.get('final_score', 50)
            event.confidence = score_result.get('confidence', 50) / 100.0
            event.rationale = '; '.join(score_result.get('rationale', []))
            
            # Determine direction from score and rationale
            rationale_text = event.rationale.lower() if event.rationale else ''
            if 'positive' in rationale_text or event.impact_score >= 60:
                event.direction = 'positive'
            elif 'negative' in rationale_text or event.impact_score <= 40:
                event.direction = 'negative'
            else:
                event.direction = 'neutral'
            
            # Commit this event
            db_session.commit()
            updated += 1
            
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{total} events processed ({updated} updated, {failed} failed)")
                
        except Exception as e:
            logger.error(f"Failed to score event {event_id}: {e}")
            db_session.rollback()
            failed += 1
        finally:
            close_db_session(db_session)
    
    logger.info(f"Re-scoring complete: {updated} events updated, {failed} failed")


if __name__ == "__main__":
    logger.info("Starting event re-scoring process...")
    rescore_all_events()
    logger.info("Event re-scoring complete!")
