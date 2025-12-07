"""
Re-score events with content-based analysis using impact_scoring module.

This script properly analyzes event titles, descriptions, and 8-K items
to compute accurate impact scores and direction.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import psycopg2
from datetime import datetime
from impact_scoring import score_event
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_connection_string():
    """Get PostgreSQL connection string from environment."""
    return os.getenv('DATABASE_URL')


def extract_8k_items_from_title(title: str) -> list:
    """Extract 8-K item numbers from event title."""
    import re
    items = []
    
    title_lower = title.lower()
    
    item_patterns = {
        'Entry into Material Agreement': '1.01',
        'Material Agreement': '1.01',
        'Termination of Material Agreement': '1.02',
        'Bankruptcy': '1.03',
        'Completion of Acquisition': '2.01',
        'Results of Operations': '2.02',
        'Financial Statements': '2.02',
        'Material Obligations': '2.03',
        'Triggering Events': '2.04',
        'Exit Activities': '2.05',
        'Material Impairment': '2.06',
        'Delisting': '3.01',
        'Notice of Delisting': '3.01',
        'Unregistered Sales': '3.02',
        'Material Modification': '3.03',
        'Auditor Change': '4.01',
        'Non-Reliance': '4.02',
        'Controls and Procedures': '4.02',
        'Change in Directors': '5.02',
        'Departure': '5.02',
        'Election of Directors': '5.02',
        'Amendments to Articles': '5.03',
        'Temporary Suspension': '5.04',
        'Compensation': '5.02',
        'Executive Compensation': '5.02',
        'Submission of Matters to Vote': '5.07',
        'Shareholder Vote': '5.07',
        'Other Events': '8.01',
        'Regulation FD': '7.01',
        'FD Disclosure': '7.01',
    }
    
    for pattern, item in item_patterns.items():
        if pattern.lower() in title_lower:
            if item not in items:
                items.append(item)
    
    return items


def rescore_events_with_content():
    """Re-score events using content-based impact scoring."""
    conn_string = get_connection_string()
    if not conn_string:
        raise ValueError("DATABASE_URL not set")
    
    conn = psycopg2.connect(conn_string)
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, ticker, event_type, title, description, sector
            FROM events 
            WHERE impact_score = 50 AND direction = 'neutral'
            ORDER BY id DESC
            LIMIT 5000
        """)
        events = cur.fetchall()
        cur.close()
        logger.info(f"Found {len(events)} events with default scores to re-score")
    finally:
        conn.close()
    
    updated = 0
    failed = 0
    total = len(events)
    
    for i, row in enumerate(events, 1):
        event_id, ticker, event_type, title, description, sector = row
        
        try:
            metadata = {}
            
            if event_type in ['sec_8k', 'ma']:
                items = extract_8k_items_from_title(title or '')
                if items:
                    metadata['8k_items'] = items
            
            result = score_event(
                event_type=event_type or 'press_release',
                title=title or '',
                description=description or '',
                sector=sector or 'Unknown',
                metadata=metadata
            )
            
            impact_score = result.get('impact_score', 50)
            direction = result.get('direction', 'neutral')
            confidence = result.get('confidence', 0.5)
            rationale = result.get('rationale', '')
            
            conn = psycopg2.connect(conn_string)
            try:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE events 
                    SET impact_score = %s,
                        direction = %s,
                        confidence = %s,
                        rationale = %s,
                        updated_at = NOW()
                    WHERE id = %s
                """, (impact_score, direction, confidence, rationale, event_id))
                conn.commit()
                cur.close()
                updated += 1
                
                if i % 50 == 0:
                    logger.info(f"Progress: {i}/{total} ({updated} updated, {failed} failed)")
                    
            except Exception as e:
                logger.error(f"Failed to update event {event_id} ({ticker}): {str(e)[:200]}")
                conn.rollback()
                failed += 1
            finally:
                conn.close()
                
        except Exception as e:
            logger.error(f"Failed to compute score for event {event_id} ({ticker}): {str(e)[:200]}")
            failed += 1
            continue
    
    logger.info(f"Re-scoring complete: {updated} events updated, {failed} failed")
    return updated, failed


if __name__ == "__main__":
    logger.info("Starting content-based event re-scoring process...")
    updated, failed = rescore_events_with_content()
    logger.info(f"Event re-scoring complete! Updated: {updated}, Failed: {failed}")
