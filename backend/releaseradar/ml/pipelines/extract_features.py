"""
Feature extraction pipeline - generates feature snapshots from events.

Extracts features for events that have outcomes, preparing data for ML training.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
import json

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from releaseradar.db.models import Event, EventOutcome, ModelFeature
from releaseradar.db.session import get_db_transaction
from releaseradar.ml.features import FeatureExtractor
from releaseradar.log_config import logger


class FeaturePipeline:
    """Extracts and stores features for events with outcomes."""
    
    FEATURE_VERSION = "v1.0"
    HORIZONS = ["1d", "5d", "20d"]
    
    def __init__(self):
        pass
    
    def extract_features_for_events(
        self,
        lookback_days: int = 60,
        ticker: Optional[str] = None
    ) -> dict:
        """
        Extract features for events with outcomes.
        
        Args:
            lookback_days: How many days back to process
            ticker: Optional ticker filter
            
        Returns:
            Statistics dict
        """
        with get_db_transaction() as db:
            stats = {
                "events_processed": 0,
                "features_created": 0,
                "features_skipped": 0,
                "errors": 0,
            }
            
            # Get events with outcomes from lookback window
            cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
            
            # Find events that have at least one outcome
            query = (
                select(Event)
                .join(EventOutcome, Event.id == EventOutcome.event_id)
                .where(Event.date >= cutoff_date)
                .distinct()
            )
            
            if ticker:
                query = query.where(Event.ticker == ticker)
            
            events = db.execute(query).scalars().all()
            
            logger.info(f"Extracting features for {len(events)} events")
            
            # Create feature extractor
            extractor = FeatureExtractor(db)
            
            for event in events:
                try:
                    stats["events_processed"] += 1
                    
                    # Extract features for this event
                    features = extractor.extract_features(event.id)
                    
                    if features is None:
                        logger.warning(f"Failed to extract features for event {event.id}")
                        stats["errors"] += 1
                        continue
                    
                    # Convert features to dict
                    feature_vector = features.to_vector()
                    
                    # Store features for each horizon
                    for horizon in self.HORIZONS:
                        # Check if feature already exists
                        existing = db.execute(
                            select(ModelFeature)
                            .where(ModelFeature.event_id == event.id)
                            .where(ModelFeature.horizon == horizon)
                        ).scalar_one_or_none()
                        
                        if existing:
                            stats["features_skipped"] += 1
                            continue
                        
                        # Create feature record
                        feature_data = {
                            "event_id": event.id,
                            "horizon": horizon,
                            "features": feature_vector,
                            "feature_version": self.FEATURE_VERSION,
                            "base_score": features.base_score,
                            "sector": features.sector,
                            "event_type": features.event_type,
                            "market_vol": features.market_vol,
                            "info_tier": features.info_tier,
                        }
                        
                        # Upsert feature
                        stmt = insert(ModelFeature).values(feature_data)
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["event_id", "horizon"],
                            set_={
                                "features": stmt.excluded.features,
                                "feature_version": stmt.excluded.feature_version,
                                "base_score": stmt.excluded.base_score,
                                "sector": stmt.excluded.sector,
                                "event_type": stmt.excluded.event_type,
                                "market_vol": stmt.excluded.market_vol,
                                "info_tier": stmt.excluded.info_tier,
                                "extracted_at": datetime.utcnow(),
                            }
                        )
                        db.execute(stmt)
                        stats["features_created"] += 1
                    
                    # Commit every 50 events
                    if stats["events_processed"] % 50 == 0:
                        db.commit()
                        logger.info(f"Processed {stats['events_processed']} events, "
                                   f"created {stats['features_created']} feature records")
                
                except Exception as e:
                    logger.error(f"Error extracting features for event {event.id}: {e}")
                    stats["errors"] += 1
                    db.rollback()
                    continue
            
            # Final commit
            db.commit()
            
            logger.info(f"Feature extraction complete: {stats}")
            
            return stats


def main():
    """Entry point for scheduled job."""
    logger.info("Starting feature extraction job")
    
    pipeline = FeaturePipeline()
    
    # Extract features for events from last 90 days
    stats = pipeline.extract_features_for_events(lookback_days=90)
    
    if stats["errors"] > 0:
        logger.warning(f"Completed with {stats['errors']} errors")
        sys.exit(1)
    else:
        logger.info("Feature extraction job completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
