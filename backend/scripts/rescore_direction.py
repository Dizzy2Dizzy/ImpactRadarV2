"""
Re-score ALL events to use improved direction classification.

This script updates event directions using the enhanced keyword lexicons
and 8-K text analysis logic to reduce neutral/uncertain classifications.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db, close_db_session, Event
from impact_scoring import ImpactScorer
import re
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def extract_8k_items(title: str, description: str) -> list:
    """Extract 8-K item numbers from title or description."""
    items = []
    text = f"{title or ''} {description or ''}"
    
    pattern = r'\b(\d+\.\d{2})\b'
    matches = re.findall(pattern, text)
    
    valid_items = {'1.01', '1.02', '1.03', '1.04', '2.01', '2.02', '2.03', '2.04', '2.05', '2.06',
                   '3.01', '3.02', '3.03', '4.01', '4.02', '5.01', '5.02', '5.03', '5.04', '5.05',
                   '5.06', '5.07', '5.08', '6.01', '6.02', '6.03', '6.04', '6.05', '7.01', '8.01', '9.01'}
    
    for match in matches:
        if match in valid_items:
            items.append(match)
    
    return list(set(items))


def rescore_all_directions():
    """Re-score all event directions using improved classification."""
    db = get_db()
    try:
        total = db.query(Event).count()
        logger.info(f"Found {total} total events to re-score")
        
        events = db.query(Event).order_by(Event.date.desc()).all()
        
        stats = {'positive': 0, 'negative': 0, 'neutral': 0, 'uncertain': 0, 'updated': 0, 'failed': 0}
        old_stats = {'positive': 0, 'negative': 0, 'neutral': 0, 'uncertain': 0}
        
        for i, event in enumerate(events, 1):
            try:
                old_direction = event.direction or 'neutral'
                old_stats[old_direction] = old_stats.get(old_direction, 0) + 1
                
                metadata = {}
                
                if event.event_type and 'sec_8k' in event.event_type.lower():
                    items = extract_8k_items(event.title, event.description)
                    if items:
                        metadata['8k_items'] = items
                
                new_direction, new_confidence = ImpactScorer._determine_direction(
                    event_type=event.event_type or '',
                    title=event.title or '',
                    description=event.description or '',
                    metadata=metadata
                )
                
                if new_direction != old_direction or abs((event.confidence or 0.5) - new_confidence) > 0.1:
                    event.direction = new_direction
                    event.confidence = new_confidence
                    stats['updated'] += 1
                
                stats[new_direction] = stats.get(new_direction, 0) + 1
                
                if i % 500 == 0:
                    db.commit()
                    logger.info(f"Progress: {i}/{total} events ({stats['updated']} direction changes)")
                    
            except Exception as e:
                logger.error(f"Failed to score event {event.id}: {e}")
                stats['failed'] += 1
        
        db.commit()
        
        logger.info("\n" + "="*60)
        logger.info("DIRECTION DISTRIBUTION COMPARISON")
        logger.info("="*60)
        logger.info(f"\nOLD distribution:")
        for direction, count in old_stats.items():
            pct = (count / total * 100) if total > 0 else 0
            logger.info(f"  {direction}: {count} ({pct:.1f}%)")
        
        logger.info(f"\nNEW distribution:")
        for direction in ['positive', 'negative', 'neutral', 'uncertain']:
            count = stats.get(direction, 0)
            pct = (count / total * 100) if total > 0 else 0
            logger.info(f"  {direction}: {count} ({pct:.1f}%)")
        
        logger.info(f"\nTotal direction changes: {stats['updated']}")
        logger.info(f"Failed events: {stats['failed']}")
        
    except Exception as e:
        logger.error(f"Script failed: {e}")
        db.rollback()
        raise
    finally:
        close_db_session(db)


if __name__ == "__main__":
    logger.info(f"Starting direction re-scoring at {datetime.now()}")
    rescore_all_directions()
    logger.info("Direction re-scoring complete!")
