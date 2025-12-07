"""
Re-score events with default scores using raw SQL for robustness.

This script targets events with impact_score=50 AND direction='neutral' and
updates them using the sophisticated Market Echo Engine.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, close_db_session
from analytics.scoring import compute_event_score
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rescore_default_events():
    """Re-score events with default scores (50/neutral)."""
    # Get list of event IDs to process
    db = get_db()
    try:
        result = db.execute(text("""
            SELECT id, ticker, event_type, date, source, sector, info_tier, info_subtype
            FROM events 
            WHERE impact_score = 50 AND direction = 'neutral'
            ORDER BY id
        """))
        events = list(result)
        total = len(events)
        logger.info(f"Found {total} events with default scores to re-score")
    finally:
        close_db_session(db)
    
    updated = 0
    failed = 0
    
    # Process each event
    for i, row in enumerate(events, 1):
        event_id = row[0]
        ticker = row[1]
        event_type = row[2]
        date = row[3]
        source = row[4]
        sector = row[5]
        info_tier = row[6] or 'primary'
        info_subtype = row[7]
        
        # Create new session for this event
        db_session = get_db()
        try:
            # Compute score
            score_result = compute_event_score(
                event_id=event_id,
                ticker=ticker,
                event_type=event_type,
                event_date=date,
                source=source,
                sector=sector,
                db=db_session,
                info_tier=info_tier,
                info_subtype=info_subtype
            )
            
            # Extract values
            impact_score = score_result.get('final_score', 50)
            confidence = score_result.get('confidence', 50) / 100.0
            rationale = '; '.join(score_result.get('rationale', []))
            
            # Determine direction
            rationale_lower = rationale.lower()
            if 'positive' in rationale_lower or impact_score >= 60:
                direction = 'positive'
            elif 'negative' in rationale_lower or impact_score <= 40:
                direction = 'negative'
            else:
                direction = 'neutral'
            
            # Update using raw SQL
            db_session.execute(text("""
                UPDATE events 
                SET impact_score = :score,
                    confidence = :conf,
                    rationale = :rat,
                    direction = :dir,
                    updated_at = NOW()
                WHERE id = :eid
            """), {
                'score': impact_score,
                'conf': confidence,
                'rat': rationale,
                'dir': direction,
                'eid': event_id
            })
            
            db_session.commit()
            updated += 1
            
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{total} ({updated} updated, {failed} failed)")
                
        except Exception as e:
            logger.error(f"Failed to score event {event_id} ({ticker}): {str(e)[:200]}")
            try:
                db_session.rollback()
            except:
                pass
            failed += 1
        finally:
            try:
                close_db_session(db_session)
            except:
                pass
    
    logger.info(f"Re-scoring complete: {updated} events updated, {failed} failed")
    return updated, failed


if __name__ == "__main__":
    logger.info("Starting event re-scoring process...")
    updated, failed = rescore_default_events()
    logger.info(f"Event re-scoring complete! Updated: {updated}, Failed: {failed}")
