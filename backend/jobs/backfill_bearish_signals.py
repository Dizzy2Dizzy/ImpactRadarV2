"""
Backfill Bearish Signals Job

Backfills bearish_signal, bearish_score, bearish_confidence, and bearish_rationale
for all existing events based on the new bearish signal scoring logic.

Includes Signal 8: Hidden Bearish detection using contrarian pattern data
from the Market Echo Engine's contrarian learning system.

Usage:
    python jobs/backfill_bearish_signals.py [--batch-size 500] [--dry-run]
"""

import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, update, select, func
from sqlalchemy.orm import sessionmaker

from releaseradar.db.models import Event
from releaseradar.log_config import logger
from impact_scoring import compute_bearish_signal


def get_db_session():
    """Create database session."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL environment variable not set")
    
    engine = create_engine(database_url)
    Session = sessionmaker(bind=engine)
    return Session()


def get_contrarian_sample_sizes(db) -> Dict[Tuple[str, str], int]:
    """
    Get sample sizes for contrarian patterns from the database.
    
    Returns:
        Dict mapping (ticker, event_type) to sample count
    """
    try:
        from releaseradar.services.contrariance_analyzer import ContrarianAnalyzer
        analyzer = ContrarianAnalyzer(db)
        patterns = analyzer.compute_contrarian_patterns(lookback_days=180)
        
        sample_sizes = {}
        for pattern in patterns:
            sample_sizes[(pattern.ticker, pattern.event_type)] = pattern.total_events
        
        logger.info(f"Loaded {len(sample_sizes)} contrarian patterns for sample size lookup")
        return sample_sizes
    except Exception as e:
        logger.warning(f"Failed to load contrarian patterns: {e}")
        return {}


def backfill_bearish_signals(batch_size: int = 500, dry_run: bool = False):
    """
    Backfill bearish signals for all events.
    
    Includes Signal 8: Hidden Bearish detection using contrarian pattern data.
    
    Args:
        batch_size: Number of events to process per batch
        dry_run: If True, don't commit changes
    """
    db = get_db_session()
    
    try:
        # Load contrarian pattern sample sizes for Signal 8
        contrarian_sample_sizes = get_contrarian_sample_sizes(db)
        
        # Get total count
        total_count = db.execute(select(func.count(Event.id))).scalar()
        logger.info(f"Total events to process: {total_count}")
        
        # Track statistics
        stats = {
            'processed': 0,
            'bearish_detected': 0,
            'hidden_bearish_detected': 0,  # Signal 8 - contrarian learning signals
            'errors': 0,
            'batches': 0
        }
        
        offset = 0
        start_time = datetime.utcnow()
        
        while offset < total_count:
            # Fetch batch
            events = db.execute(
                select(Event)
                .order_by(Event.id)
                .offset(offset)
                .limit(batch_size)
            ).scalars().all()
            
            if not events:
                break
            
            batch_bearish_count = 0
            
            for event in events:
                try:
                    # Get actual contrarian sample size from patterns lookup
                    contrarian_sample_size = None
                    if event.hidden_bearish_prob is not None and event.hidden_bearish_prob > 0:
                        # Look up actual sample size from contrarian patterns
                        pattern_key = (event.ticker, event.event_type)
                        contrarian_sample_size = contrarian_sample_sizes.get(pattern_key, 3)
                    
                    # Compute bearish signal with contrarian learning data
                    bearish_result = compute_bearish_signal(
                        event_type=event.event_type or '',
                        direction=event.direction or 'uncertain',
                        confidence=event.confidence or 0.0,
                        impact_score=event.impact_score or 50,
                        title=event.title or '',
                        description=event.description or '',
                        p_down=event.impact_p_down,
                        p_up=event.impact_p_up,
                        ml_adjusted_score=event.ml_adjusted_score,
                        ml_confidence=event.ml_confidence,
                        metadata=event.metadata,
                        hidden_bearish_prob=event.hidden_bearish_prob,
                        contrarian_sample_size=contrarian_sample_size
                    )
                    
                    # Update event
                    event.bearish_signal = bearish_result['bearish_signal']
                    event.bearish_score = bearish_result['bearish_score']
                    event.bearish_confidence = bearish_result['bearish_confidence']
                    event.bearish_rationale = bearish_result['bearish_rationale']
                    
                    if bearish_result['bearish_signal']:
                        batch_bearish_count += 1
                        # Track Signal 8 (hidden bearish) separately
                        if bearish_result.get('bearish_rationale', '').startswith('Hidden bearish'):
                            stats['hidden_bearish_detected'] += 1
                    
                    stats['processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing event {event.id}: {e}")
                    stats['errors'] += 1
            
            stats['bearish_detected'] += batch_bearish_count
            stats['batches'] += 1
            
            if not dry_run:
                db.commit()
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            rate = stats['processed'] / elapsed if elapsed > 0 else 0
            
            logger.info(
                f"Batch {stats['batches']}: {offset + len(events)}/{total_count} events, "
                f"{batch_bearish_count} bearish in batch, "
                f"{stats['bearish_detected']} total bearish, "
                f"{rate:.1f} events/sec"
            )
            
            offset += batch_size
        
        # Final stats
        elapsed = (datetime.utcnow() - start_time).total_seconds()
        logger.info(
            f"\n{'DRY RUN - ' if dry_run else ''}Backfill complete!\n"
            f"  Processed: {stats['processed']}\n"
            f"  Bearish detected: {stats['bearish_detected']}\n"
            f"  Hidden bearish (Signal 8): {stats['hidden_bearish_detected']}\n"
            f"  Errors: {stats['errors']}\n"
            f"  Total time: {elapsed:.1f}s\n"
            f"  Avg rate: {stats['processed']/elapsed:.1f} events/sec"
        )
        
        # Get distribution of bearish signals
        if not dry_run:
            bearish_count = db.execute(
                select(func.count(Event.id))
                .where(Event.bearish_signal == True)
            ).scalar()
            
            logger.info(f"Total bearish events in database: {bearish_count}")
            
            # Get top bearish event types
            bearish_by_type = db.execute(
                select(Event.event_type, func.count(Event.id))
                .where(Event.bearish_signal == True)
                .group_by(Event.event_type)
                .order_by(func.count(Event.id).desc())
                .limit(10)
            ).all()
            
            if bearish_by_type:
                logger.info("Top bearish event types:")
                for event_type, count in bearish_by_type:
                    logger.info(f"  {event_type}: {count}")
        
        return stats
        
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description='Backfill bearish signals for events')
    parser.add_argument('--batch-size', type=int, default=500,
                        help='Number of events per batch (default: 500)')
    parser.add_argument('--dry-run', action='store_true',
                        help='Run without committing changes')
    
    args = parser.parse_args()
    
    logger.info(f"Starting bearish signal backfill (batch_size={args.batch_size}, dry_run={args.dry_run})")
    
    stats = backfill_bearish_signals(
        batch_size=args.batch_size,
        dry_run=args.dry_run
    )
    
    return 0 if stats['errors'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
