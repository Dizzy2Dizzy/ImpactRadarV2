"""
Re-score all events using the sophisticated Market Echo Engine - Version 2.

This version uses separate database sessions to avoid transaction conflicts.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, close_db_session, Event
from analytics.scoring import compute_event_score
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_events_to_rescore(db):
    """Get list of event IDs that need rescoring."""
    result = db.execute(text("""
        SELECT id, ticker, event_type, date, source, sector, info_tier, info_subtype
        FROM events
        WHERE impact_score = 50 AND confidence = 0.5
        ORDER BY id
    """))
    return [dict(row._mapping) for row in result]


def rescore_single_event(event_data):
    """Re-score a single event using its own database session."""
    db = get_db()
    try:
        # Compute sophisticated score
        score_result = compute_event_score(
            event_id=event_data['id'],
            ticker=event_data['ticker'],
            event_type=event_data['event_type'],
            event_date=event_data['date'],
            source=event_data['source'],
            sector=event_data['sector'],
            db=db,
            info_tier=event_data['info_tier'] or 'primary',
            info_subtype=event_data['info_subtype']
        )
        
        # Update event with computed scores
        impact_score = score_result.get('final_score', 50)
        confidence = score_result.get('confidence', 50) / 100.0
        rationale = '; '.join(score_result.get('rationale', []))
        
        # Determine direction from score and rationale
        rationale_text = rationale.lower() if rationale else ''
        if 'positive' in rationale_text or impact_score >= 60:
            direction = 'positive'
        elif 'negative' in rationale_text or impact_score <= 40:
            direction = 'negative'
        else:
            direction = 'neutral'
        
        # Update using SQL to avoid ORM transaction issues
        db.execute(text("""
            UPDATE events
            SET impact_score = :score,
                confidence = :conf,
                direction = :dir,
                rationale = :rat
            WHERE id = :event_id
        """), {
            'score': impact_score,
            'conf': confidence,
            'dir': direction,
            'rat': rationale,
            'event_id': event_data['id']
        })
        
        db.commit()
        return True, f"Score: {impact_score}, Conf: {confidence*100:.0f}%"
        
    except Exception as e:
        db.rollback()
        return False, str(e)
    finally:
        close_db_session(db)


def rescore_all_events():
    """Re-score all events in the database using the sophisticated scoring engine."""
    # Get list of events to rescore
    logger.info("Fetching events that need rescoring...")
    db = get_db()
    try:
        events_to_rescore = get_events_to_rescore(db)
        total = len(events_to_rescore)
    finally:
        close_db_session(db)
    
    logger.info(f"Found {total} events to re-score")
    
    updated = 0
    failed = 0
    
    for i, event_data in enumerate(events_to_rescore, 1):
        try:
            success, message = rescore_single_event(event_data)
            if success:
                updated += 1
                if i % 50 == 0:
                    logger.info(f"Progress: {i}/{total} events processed ({updated} updated, {failed} failed)")
            else:
                failed += 1
                logger.error(f"Failed to score event {event_data['id']} ({event_data['ticker']}): {message}")
        except Exception as e:
            failed += 1
            logger.error(f"Exception scoring event {event_data['id']}: {e}")
            continue
    
    logger.info(f"Re-scoring complete: {updated} events updated, {failed} failed")


if __name__ == "__main__":
    logger.info("Starting event re-scoring process...")
    rescore_all_events()
    logger.info("Event re-scoring complete!")
