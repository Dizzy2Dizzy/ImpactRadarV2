"""
Re-score events with default scores using direct database connections.

Bypasses SQLAlchemy ORM to avoid session management issues.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from datetime import datetime
from database import get_db, close_db_session
from analytics.scoring import compute_event_score
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection_string():
    """Get PostgreSQL connection string from environment."""
    import os
    return os.getenv('DATABASE_URL')


def rescore_with_direct_connection():
    """Re-score events using direct psycopg2 connections."""
    conn_string = get_connection_string()
    if not conn_string:
        raise ValueError("DATABASE_URL not set")
    
    # Get list of events to process
    conn = psycopg2.connect(conn_string)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, ticker, event_type, date, source, sector, info_tier, info_subtype
            FROM events 
            WHERE impact_score = 50 AND direction = 'neutral'
            ORDER BY id
        """)
        events = cur.fetchall()
        cur.close()
        logger.info(f"Found {len(events)} events with default scores to re-score")
    finally:
        conn.close()
    
    updated = 0
    failed = 0
    total = len(events)
    
    # Process each event
    for i, row in enumerate(events, 1):
        event_id, ticker, event_type, date, source, sector, info_tier, info_subtype = row
        info_tier = info_tier or 'primary'
        
        # Get a SQLAlchemy session for scoring queries
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
            
        except Exception as e:
            logger.error(f"Failed to compute score for event {event_id} ({ticker}): {str(e)[:200]}")
            failed += 1
            continue
        finally:
            close_db_session(db_session)
        
        # Update using separate connection
        conn = psycopg2.connect(conn_string)
        try:
            cur = conn.cursor()
            cur.execute("""
                UPDATE events 
                SET impact_score = %s,
                    confidence = %s,
                    rationale = %s,
                    direction = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (impact_score, confidence, rationale, direction, event_id))
            conn.commit()
            cur.close()
            updated += 1
            
            if i % 100 == 0:
                logger.info(f"Progress: {i}/{total} ({updated} updated, {failed} failed)")
                
        except Exception as e:
            logger.error(f"Failed to update event {event_id} ({ticker}): {str(e)[:200]}")
            conn.rollback()
            failed += 1
        finally:
            conn.close()
    
    logger.info(f"Re-scoring complete: {updated} events updated, {failed} failed")
    return updated, failed


if __name__ == "__main__":
    logger.info("Starting event re-scoring process...")
    updated, failed = rescore_with_direct_connection()
    logger.info(f"Event re-scoring complete! Updated: {updated}, Failed: {failed}")
