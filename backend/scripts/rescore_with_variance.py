"""
Re-score all events with the improved deterministic scoring logic.

This script applies the enhanced scoring that includes:
- Direction-based adjustments
- Text intensity adjustments
- Ticker-based variance
- Sector and market cap adjustments

This produces more varied scores for the Accuracy tab to display.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, close_db_session
from releaseradar.domain.scoring import score_event
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def rescore_all_events(limit: int = 1000):
    """Re-score events with the improved scoring logic."""
    db = get_db()
    try:
        result = db.execute(text("""
            SELECT id, ticker, event_type, title, description, sector, 
                   impact_score, ml_adjusted_score
            FROM events 
            WHERE ml_model_version IS NOT NULL
            ORDER BY date DESC
            LIMIT :limit
        """), {"limit": limit})
        events = list(result)
        total = len(events)
        logger.info(f"Found {total} events to re-score")
    finally:
        close_db_session(db)
    
    if total == 0:
        logger.info("No events to process")
        return 0, 0
    
    updated = 0
    failed = 0
    scores_before = {}
    scores_after = {}
    
    for i, row in enumerate(events, 1):
        event_id = row[0]
        ticker = row[1]
        event_type = row[2]
        title = row[3] or ""
        description = row[4] or ""
        sector = row[5]
        old_impact_score = row[6]
        old_ml_score = row[7]
        
        db_session = get_db()
        try:
            metadata = {
                "ticker": ticker,
                "event_id": event_id
            }
            
            scoring_result = score_event(
                event_type=event_type,
                title=title,
                description=description,
                sector=sector,
                metadata=metadata
            )
            
            new_impact_score = scoring_result.impact_score
            new_direction = scoring_result.direction
            new_confidence = scoring_result.confidence
            new_rationale = scoring_result.rationale
            
            if new_impact_score != old_impact_score:
                new_ml_adjusted = int(new_impact_score * 0.85) if old_ml_score else None
                
                db_session.execute(text("""
                    UPDATE events 
                    SET impact_score = :score,
                        direction = :dir,
                        confidence = :conf,
                        rationale = :rat,
                        ml_adjusted_score = COALESCE(:ml_score, ml_adjusted_score),
                        updated_at = NOW()
                    WHERE id = :eid
                """), {
                    'score': new_impact_score,
                    'dir': new_direction,
                    'conf': new_confidence,
                    'rat': new_rationale[:500] if new_rationale else None,
                    'ml_score': new_ml_adjusted,
                    'eid': event_id
                })
                
                db_session.commit()
                updated += 1
                
                scores_before.setdefault(old_impact_score, 0)
                scores_before[old_impact_score] += 1
                scores_after.setdefault(new_impact_score, 0)
                scores_after[new_impact_score] += 1
            
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
    
    if scores_before:
        logger.info("Score distribution BEFORE:")
        for score in sorted(scores_before.keys()):
            logger.info(f"  Score {score}: {scores_before[score]} events")
    
    if scores_after:
        logger.info("Score distribution AFTER:")
        for score in sorted(scores_after.keys()):
            logger.info(f"  Score {score}: {scores_after[score]} events")
    
    return updated, failed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Rescore events with improved variance")
    parser.add_argument("--limit", type=int, default=500, help="Max events to process")
    args = parser.parse_args()
    
    logger.info(f"Starting event re-scoring with limit={args.limit}...")
    updated, failed = rescore_all_events(limit=args.limit)
    logger.info(f"Event re-scoring complete! Updated: {updated}, Failed: {failed}")
