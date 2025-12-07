"""
Backfill Contrarian Outcomes - Compute contrarian outcomes for existing events.

This script:
1. Joins events with their EventOutcome data (T+1 price movements)
2. Identifies "contrarian" events where prediction diverged from reality
3. Populates the contrarian fields on the Event model
4. Computes hidden bearish probabilities based on historical patterns

Run this after the ml_learning_pipeline has labeled outcomes.
"""

import os
import sys
from datetime import datetime
from typing import Dict, Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, update, func
from sqlalchemy.dialects.postgresql import insert

from releaseradar.db.models import Event, EventOutcome
from releaseradar.db.session import get_db_transaction
from releaseradar.log_config import configure_logging, logger
from releaseradar.services.contrariance_analyzer import ContrarianAnalyzer, ContrarianSeThresholds

configure_logging()


class ContrarianBackfiller:
    """Backfills contrarian outcome fields for existing events."""
    
    BATCH_SIZE = 500
    
    def __init__(self):
        self.thresholds = ContrarianSeThresholds()
        self.stats = {
            "events_processed": 0,
            "contrarian_detected": 0,
            "hidden_bearish_detected": 0,
            "errors": 0,
            "skipped_no_outcome": 0,
        }
    
    def _determine_realized_direction(self, return_pct: float) -> str:
        """Determine the realized direction from actual return."""
        if return_pct >= 1.0:
            return "positive"
        elif return_pct <= -1.0:
            return "negative"
        else:
            return "neutral"
    
    def _is_contrarian(
        self,
        predicted_direction: str,
        realized_return: float
    ) -> bool:
        """Check if the outcome contradicted the prediction."""
        if predicted_direction in ("positive", "neutral"):
            return realized_return < self.thresholds.MIN_DECLINE_FOR_HIDDEN_BEARISH
        elif predicted_direction == "negative":
            return realized_return > 1.0  # Predicted down, went up
        return False
    
    def backfill_events(
        self,
        ticker: Optional[str] = None,
        event_type: Optional[str] = None,
        dry_run: bool = False
    ) -> Dict:
        """
        Backfill contrarian outcomes for events.
        
        Args:
            ticker: Optional ticker filter
            event_type: Optional event type filter
            dry_run: If True, don't commit changes
            
        Returns:
            Statistics dict
        """
        logger.info(f"Starting contrarian backfill (dry_run={dry_run})")
        
        with get_db_transaction() as db:
            # Query events with their 1d outcomes
            query = (
                select(Event, EventOutcome)
                .join(EventOutcome, Event.id == EventOutcome.event_id)
                .where(EventOutcome.horizon == "1d")
                .where(Event.contrarian_outcome.is_(None))  # Only unprocessed events
            )
            
            if ticker:
                query = query.where(Event.ticker == ticker)
            if event_type:
                query = query.where(Event.event_type == event_type)
            
            results = db.execute(query).all()
            total = len(results)
            
            logger.info(f"Found {total} events to process")
            
            # Compute contrarian patterns for hidden bearish probability
            analyzer = ContrarianAnalyzer(db)
            patterns = analyzer.compute_contrarian_patterns(lookback_days=180)
            
            # Build pattern lookup
            pattern_lookup = {}
            for pattern in patterns:
                key = (pattern.ticker, pattern.event_type)
                pattern_lookup[key] = pattern
            
            logger.info(f"Loaded {len(patterns)} contrarian patterns for lookup")
            
            batch_count = 0
            for event, outcome in results:
                try:
                    self.stats["events_processed"] += 1
                    
                    # Determine realized direction and contrarian status
                    realized_direction = self._determine_realized_direction(outcome.return_pct)
                    is_contrarian = self._is_contrarian(event.direction, outcome.return_pct)
                    
                    # Look up hidden bearish probability from patterns
                    pattern_key = (event.ticker, event.event_type)
                    pattern = pattern_lookup.get(pattern_key)
                    hidden_bearish_prob = pattern.hidden_bearish_probability if pattern else 0.0
                    
                    # Determine if this should be flagged as hidden bearish
                    # A new event is "hidden bearish" if:
                    # 1. Its ticker/event_type has a high contrarian rate (>40%)
                    # 2. AND the pattern has decent confidence (>0.5)
                    hidden_bearish_signal = (
                        hidden_bearish_prob >= 0.4 and 
                        pattern is not None and 
                        pattern.confidence >= 0.5
                    )
                    
                    if is_contrarian:
                        self.stats["contrarian_detected"] += 1
                    
                    if hidden_bearish_signal:
                        self.stats["hidden_bearish_detected"] += 1
                    
                    # Update the event
                    if not dry_run:
                        db.execute(
                            update(Event)
                            .where(Event.id == event.id)
                            .values(
                                contrarian_outcome=is_contrarian,
                                realized_direction=realized_direction,
                                realized_return_1d=outcome.return_pct,
                                hidden_bearish_prob=hidden_bearish_prob,
                                hidden_bearish_signal=hidden_bearish_signal
                            )
                        )
                    
                    batch_count += 1
                    
                    # Commit in batches
                    if batch_count >= self.BATCH_SIZE:
                        if not dry_run:
                            db.commit()
                        logger.info(
                            f"Processed {self.stats['events_processed']}/{total} events, "
                            f"{self.stats['contrarian_detected']} contrarian, "
                            f"{self.stats['hidden_bearish_detected']} hidden bearish"
                        )
                        batch_count = 0
                
                except Exception as e:
                    logger.error(f"Error processing event {event.id}: {e}")
                    self.stats["errors"] += 1
                    continue
            
            # Final commit
            if not dry_run:
                db.commit()
            
            logger.info(f"\nBackfill complete!")
            logger.info(f"  Events processed: {self.stats['events_processed']}")
            logger.info(f"  Contrarian detected: {self.stats['contrarian_detected']}")
            logger.info(f"  Hidden bearish detected: {self.stats['hidden_bearish_detected']}")
            logger.info(f"  Errors: {self.stats['errors']}")
            
            return self.stats


def main():
    """Entry point for the backfill job."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backfill contrarian outcomes for events")
    parser.add_argument("--ticker", type=str, default=None, help="Filter by ticker")
    parser.add_argument("--event-type", type=str, default=None, help="Filter by event type")
    parser.add_argument("--dry-run", action="store_true", help="Don't commit changes")
    
    args = parser.parse_args()
    
    backfiller = ContrarianBackfiller()
    stats = backfiller.backfill_events(
        ticker=args.ticker,
        event_type=args.event_type,
        dry_run=args.dry_run
    )
    
    if stats["errors"] > 0:
        logger.warning(f"Completed with {stats['errors']} errors")
        sys.exit(1)
    else:
        logger.info("Contrarian backfill completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
