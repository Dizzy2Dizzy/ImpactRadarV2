"""
ML Learning Pipeline - ETL job for labeling outcomes and extracting features.

This job orchestrates the complete ML data pipeline:
1. Labels events with realized outcomes (T+1 price movements)
2. Extracts features for events with outcomes
3. Prepares data for model training

Run daily to continuously label new events as price data becomes available.
"""

import os
import sys
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from releaseradar.ml.pipelines.label_outcomes import OutcomeLabeler
from releaseradar.ml.pipelines.extract_features import FeaturePipeline
from releaseradar.log_config import logger
from releaseradar.services.quality_metrics import QualityMetricsService
from releaseradar.db.session import get_db_context


def run_ml_etl_pipeline(lookback_days: int = 60) -> dict:
    """
    Run complete ML ETL pipeline.
    
    Args:
        lookback_days: How many days back to process
        
    Returns:
        Statistics dict with results from each stage
    """
    pipeline_stats = {
        "started_at": datetime.utcnow().isoformat(),
        "lookback_days": lookback_days,
        "stages": {},
        "success": False,
    }
    
    logger.info("="*80)
    logger.info("Starting ML Learning Pipeline")
    logger.info("="*80)
    
    # Stage 1: Label outcomes
    logger.info("\n📊 Stage 1: Labeling event outcomes with realized price movements")
    
    try:
        labeler = OutcomeLabeler()
        outcome_stats = labeler.label_events(lookback_days=lookback_days)
        pipeline_stats["stages"]["label_outcomes"] = outcome_stats
        
        logger.info(f"✅ Outcome labeling complete: {outcome_stats}")
    except Exception as e:
        logger.error(f"❌ Outcome labeling failed: {e}", exc_info=True)
        pipeline_stats["stages"]["label_outcomes"] = {"error": str(e)}
        pipeline_stats["finished_at"] = datetime.utcnow().isoformat()
        return pipeline_stats
    
    # Stage 1.5: Compute EventStats from labeled outcomes
    logger.info("\n📈 Stage 1.5: Computing EventStats from labeled outcomes")
    
    try:
        stats_stats = labeler.compute_event_stats()
        pipeline_stats["stages"]["compute_stats"] = stats_stats
        
        logger.info(f"✅ EventStats computation complete: {stats_stats}")
    except Exception as e:
        logger.error(f"❌ EventStats computation failed: {e}", exc_info=True)
        pipeline_stats["stages"]["compute_stats"] = {"error": str(e)}
        pipeline_stats["finished_at"] = datetime.utcnow().isoformat()
        return pipeline_stats
    
    # Stage 2: Extract features
    logger.info("\n🔧 Stage 2: Extracting ML features from events")
    
    try:
        feature_pipeline = FeaturePipeline()
        feature_stats = feature_pipeline.extract_features_for_events(lookback_days=lookback_days)
        pipeline_stats["stages"]["extract_features"] = feature_stats
        
        logger.info(f"✅ Feature extraction complete: {feature_stats}")
    except Exception as e:
        logger.error(f"❌ Feature extraction failed: {e}", exc_info=True)
        pipeline_stats["stages"]["extract_features"] = {"error": str(e)}
        pipeline_stats["finished_at"] = datetime.utcnow().isoformat()
        return pipeline_stats
    
    # Success
    pipeline_stats["success"] = True
    pipeline_stats["finished_at"] = datetime.utcnow().isoformat()
    
    logger.info("\n" + "="*80)
    logger.info("✅ ML Learning Pipeline Complete")
    logger.info("="*80)
    logger.info(f"Summary:")
    logger.info(f"  Outcomes: {outcome_stats['outcomes_created']} created, "
               f"{outcome_stats['outcomes_skipped']} skipped, "
               f"{outcome_stats['errors']} errors")
    logger.info(f"  EventStats: {stats_stats['stats_updated']} updated, "
               f"{stats_stats['errors']} errors")
    logger.info(f"  Features: {feature_stats['features_created']} created, "
               f"{feature_stats['features_skipped']} skipped, "
               f"{feature_stats['errors']} errors")
    
    # Record quality snapshots for ML data
    with get_db_context() as db:
        quality_service = QualityMetricsService(db)
        finished_at = datetime.utcnow()
        
        # Record quality snapshot for outcomes
        if outcome_stats['outcomes_created'] > 0:
            quality_service.record_quality_snapshot(
                metric_key="ml_outcomes_labeled",
                scope="global",
                sample_count=outcome_stats['outcomes_created'],
                freshness_ts=finished_at,
                source_job="ml_learning_pipeline",
                quality_grade="excellent" if outcome_stats['errors'] == 0 else "good",
                summary_json={
                    "outcomes_created": outcome_stats['outcomes_created'],
                    "outcomes_skipped": outcome_stats['outcomes_skipped'],
                    "errors": outcome_stats['errors'],
                    "lookback_days": lookback_days,
                }
            )
        
        # Record quality snapshot for features
        if feature_stats['features_created'] > 0:
            quality_service.record_quality_snapshot(
                metric_key="ml_features_extracted",
                scope="global",
                sample_count=feature_stats['features_created'],
                freshness_ts=finished_at,
                source_job="ml_learning_pipeline",
                quality_grade="excellent" if feature_stats['errors'] == 0 else "good",
                summary_json={
                    "features_created": feature_stats['features_created'],
                    "features_skipped": feature_stats['features_skipped'],
                    "errors": feature_stats['errors'],
                    "lookback_days": lookback_days,
                }
            )
    
    return pipeline_stats


def main():
    """Entry point for scheduled job."""
    logger.info("Starting ML Learning Pipeline job")
    
    # Process last 60 days (allows for 20d horizon labels)
    lookback_days = int(os.getenv("ML_ETL_LOOKBACK_DAYS", "60"))
    
    stats = run_ml_etl_pipeline(lookback_days=lookback_days)
    
    if not stats["success"]:
        logger.error("ML Learning Pipeline failed")
        sys.exit(1)
    else:
        logger.info("ML Learning Pipeline completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
