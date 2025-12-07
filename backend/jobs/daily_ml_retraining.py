"""
Daily ML Retraining Job - Continuous learning pipeline.

This job orchestrates the complete ML lifecycle:
1. Runs ETL to label yesterday's events
2. Checks if retraining threshold is met
3. Trains new models for each horizon
4. Evaluates and promotes models if improvement shown
5. Updates events with ML scores from active models

Run daily to continuously improve model performance as new data arrives.
"""

import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sqlalchemy import select, or_

from releaseradar.ml.pipelines.retrain_model import HierarchicalRetrainingPipeline as RetrainingPipeline
from releaseradar.ml.monitoring import ModelMonitor
from releaseradar.ml.serving import MLScoringService
from releaseradar.ml.event_type_families import get_event_family
from releaseradar.db.models import Event, ModelRegistry
from releaseradar.db.session import get_db_transaction
from releaseradar.log_config import logger
from jobs.ml_learning_pipeline import run_ml_etl_pipeline


def check_retraining_needed(horizon: str = "1d") -> dict:
    """
    Check if retraining is recommended for a given horizon.
    
    Args:
        horizon: Time horizon to check
        
    Returns:
        Dict with retraining recommendation
    """
    with get_db_transaction() as db:
        monitor = ModelMonitor(db)
        model_name = f"xgboost_impact_{horizon}"
        
        recommendation = monitor.should_retrain(
            model_name=model_name,
            horizon=horizon,
            min_new_samples=100,
            max_days_since_training=30,
            accuracy_degradation_threshold=0.1
        )
        
        return recommendation


def apply_ml_scores_to_events(lookback_days: int = 90, batch_size: int = 100) -> dict:
    """
    Apply ML scores to events that need scoring.
    
    Selects events from the last N days that either:
    - Have no ML scores (ml_adjusted_score IS NULL)
    - Have outdated ML model versions
    
    Args:
        lookback_days: Number of days to look back for events (default 90)
        batch_size: Number of events to process per batch (default 100)
        
    Returns:
        Statistics dict with processing results
    """
    stats = {
        "started_at": datetime.utcnow().isoformat(),
        "total_processed": 0,
        "total_updated": 0,
        "total_skipped": 0,
        "by_horizon": {},
        "by_family": defaultdict(lambda: {"processed": 0, "updated": 0}),
        "success": False,
    }
    
    horizons = ["1d", "5d"]
    
    for horizon in horizons:
        stats["by_horizon"][horizon] = {
            "processed": 0,
            "updated": 0,
            "skipped": 0,
            "by_family": defaultdict(lambda: {"processed": 0, "updated": 0}),
        }
    
    logger.info(f"Starting ML score application for events from last {lookback_days} days")
    
    cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
    
    with get_db_transaction() as db:
        # Get current active model versions for each horizon
        active_model_versions = {}
        for horizon in horizons:
            model = db.execute(
                select(ModelRegistry)
                .where(ModelRegistry.status == "active")
                .where(ModelRegistry.horizon == horizon)
                .order_by(ModelRegistry.promoted_at.desc())
                .limit(1)
            ).scalar_one_or_none()
            
            if model:
                active_model_versions[horizon] = f"{model.name}:{model.version}"
                logger.info(f"Active model for {horizon}: {active_model_versions[horizon]}")
            else:
                active_model_versions[horizon] = None
                logger.warning(f"No active model found for {horizon} horizon")
        
        # Skip if no active models
        if not any(active_model_versions.values()):
            logger.warning("No active models found, skipping ML score application")
            stats["success"] = True
            stats["finished_at"] = datetime.utcnow().isoformat()
            return stats
        
        # Create ML scoring service
        scoring_service = MLScoringService(db)
        
        # Query events that need scoring
        # Events with NULL ml_adjusted_score OR outdated model version
        events_query = (
            select(Event)
            .where(Event.date >= cutoff_date)
            .where(
                or_(
                    Event.ml_adjusted_score.is_(None),
                    Event.ml_model_version.is_(None),
                    # Check if model version is outdated (not matching any current active version)
                    ~Event.ml_model_version.in_([v for v in active_model_versions.values() if v])
                )
            )
            .order_by(Event.date.desc())
        )
        
        events = list(db.execute(events_query).scalars().all())
        total_events = len(events)
        
        logger.info(f"Found {total_events} events needing ML scores")
        
        if total_events == 0:
            logger.info("No events need ML scoring")
            stats["success"] = True
            stats["finished_at"] = datetime.utcnow().isoformat()
            return stats
        
        # Process in batches
        batch_count = 0
        for i in range(0, total_events, batch_size):
            batch = events[i:i + batch_size]
            batch_count += 1
            
            logger.info(f"Processing batch {batch_count} ({len(batch)} events)")
            
            for event in batch:
                event_family = get_event_family(event.event_type)
                stats["total_processed"] += 1
                
                # Track best prediction across horizons
                best_prediction = None
                best_horizon = None
                
                # Get predictions for each horizon
                for horizon in horizons:
                    if not active_model_versions.get(horizon):
                        continue
                    
                    stats["by_horizon"][horizon]["processed"] += 1
                    stats["by_horizon"][horizon]["by_family"][event_family]["processed"] += 1
                    
                    try:
                        prediction = scoring_service.predict_single(
                            event_id=event.id,
                            horizon=horizon,
                            confidence_threshold=0.3,
                            max_delta=20,
                            use_blending=True
                        )
                        
                        if prediction:
                            # Use the prediction with highest confidence
                            if best_prediction is None or prediction.ml_confidence > best_prediction.ml_confidence:
                                best_prediction = prediction
                                best_horizon = horizon
                            
                            stats["by_horizon"][horizon]["updated"] += 1
                            stats["by_horizon"][horizon]["by_family"][event_family]["updated"] += 1
                        else:
                            stats["by_horizon"][horizon]["skipped"] += 1
                    
                    except Exception as e:
                        logger.warning(f"Error predicting event {event.id} for {horizon}: {e}")
                        stats["by_horizon"][horizon]["skipped"] += 1
                
                # Update event with best prediction
                if best_prediction:
                    event.ml_adjusted_score = best_prediction.ml_adjusted_score
                    event.ml_confidence = best_prediction.ml_confidence
                    event.ml_model_version = best_prediction.ml_model_version
                    event.model_source = best_prediction.model_source
                    event.delta_applied = best_prediction.delta_applied
                    
                    stats["total_updated"] += 1
                    stats["by_family"][event_family]["updated"] += 1
                else:
                    stats["total_skipped"] += 1
                
                stats["by_family"][event_family]["processed"] += 1
            
            # Commit after each batch
            try:
                db.commit()
                logger.info(f"Batch {batch_count} committed successfully")
            except Exception as e:
                logger.error(f"Error committing batch {batch_count}: {e}")
                db.rollback()
    
    # Convert defaultdicts to regular dicts for JSON serialization
    stats["by_family"] = dict(stats["by_family"])
    for horizon in horizons:
        stats["by_horizon"][horizon]["by_family"] = dict(stats["by_horizon"][horizon]["by_family"])
    
    stats["success"] = True
    stats["finished_at"] = datetime.utcnow().isoformat()
    
    # Log summary by family
    logger.info("\n📊 ML Scoring Summary by Event Family:")
    for family, family_stats in stats["by_family"].items():
        logger.info(f"  {family}: processed={family_stats['processed']}, updated={family_stats['updated']}")
    
    # Log summary by horizon
    logger.info("\n📊 ML Scoring Summary by Horizon:")
    for horizon, horizon_stats in stats["by_horizon"].items():
        logger.info(f"  {horizon}: processed={horizon_stats['processed']}, updated={horizon_stats['updated']}, skipped={horizon_stats['skipped']}")
    
    logger.info(f"\n✅ ML Score Application Complete: {stats['total_updated']}/{stats['total_processed']} events updated")
    
    return stats


def run_daily_ml_retraining() -> dict:
    """
    Run complete daily ML retraining pipeline.
    
    Returns:
        Statistics dict with results from each stage
    """
    pipeline_stats = {
        "started_at": datetime.utcnow().isoformat(),
        "stages": {},
        "success": False,
    }
    
    logger.info("="*80)
    logger.info("Starting Daily ML Retraining Pipeline")
    logger.info("="*80)
    
    # Stage 1: Run ETL to label recent events
    logger.info("\n📊 Stage 1: Running ETL to label recent events")
    
    try:
        # Process last 7 days only (daily incremental updates)
        etl_stats = run_ml_etl_pipeline(lookback_days=7)
        pipeline_stats["stages"]["etl"] = etl_stats
        
        if not etl_stats["success"]:
            logger.error("ETL pipeline failed, aborting retraining")
            return pipeline_stats
        
        logger.info("✅ ETL complete")
    except Exception as e:
        logger.error(f"❌ ETL failed: {e}", exc_info=True)
        pipeline_stats["stages"]["etl"] = {"error": str(e)}
        return pipeline_stats
    
    # Stage 2: Check retraining needs and train models
    logger.info("\n🤖 Stage 2: Checking retraining needs and training models")
    
    retraining_results = {}
    
    for horizon in ["1d", "5d", "20d"]:
        logger.info(f"\n--- Processing {horizon} horizon ---")
        
        try:
            # Check if retraining needed
            recommendation = check_retraining_needed(horizon)
            
            logger.info(f"Retraining recommendation for {horizon}: "
                       f"should_retrain={recommendation['should_retrain']}, "
                       f"priority={recommendation['priority']}, "
                       f"reasons={recommendation['reasons']}")
            
            retraining_results[horizon] = {
                "recommendation": recommendation,
                "trained": False,
                "promoted": False,
            }
            
            # Only retrain if recommended (or force via env var)
            force_retrain = os.getenv("FORCE_ML_RETRAIN", "false").lower() == "true"
            
            if recommendation["should_retrain"] or force_retrain:
                logger.info(f"🔄 Retraining model for {horizon} horizon")
                
                # Run retraining pipeline
                pipeline = RetrainingPipeline(horizon=horizon, model_type="xgboost")
                retrain_stats = pipeline.retrain_and_promote()
                
                retraining_results[horizon].update(retrain_stats)
                
                if retrain_stats["trained"]:
                    logger.info(f"✅ Model trained: {retrain_stats['model_version']}")
                    
                    if retrain_stats["promoted"]:
                        logger.info(f"🎉 Model promoted to active: {retrain_stats['model_version']}")
                    else:
                        logger.info(f"⏸️ Model staged but not promoted (insufficient improvement)")
                else:
                    logger.warning(f"⚠️ Model training failed: {retrain_stats.get('error')}")
            else:
                logger.info(f"⏭️ Skipping retraining for {horizon} (not needed)")
        
        except Exception as e:
            logger.error(f"❌ Error processing {horizon}: {e}", exc_info=True)
            retraining_results[horizon]["error"] = str(e)
    
    pipeline_stats["stages"]["retraining"] = retraining_results
    
    # Stage 3: Model health check
    logger.info("\n🏥 Stage 3: Model Health Check")
    
    health_reports = {}
    
    try:
        with get_db_transaction() as db:
            monitor = ModelMonitor(db)
            
            for horizon in ["1d", "5d", "20d"]:
                model_name = f"xgboost_impact_{horizon}"
                health = monitor.get_model_health(model_name, horizon)
                health_reports[horizon] = health
                
                logger.info(f"{horizon} model health: {health.get('status', 'unknown')}")
        
        pipeline_stats["stages"]["health_check"] = health_reports
    
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}", exc_info=True)
        pipeline_stats["stages"]["health_check"] = {"error": str(e)}
    
    # Stage 5: Apply ML scores to events
    logger.info("\n🎯 Stage 5: Applying ML Scores to Events")
    
    ml_scoring_stats = {}
    
    try:
        ml_scoring_stats = apply_ml_scores_to_events(
            lookback_days=90,
            batch_size=100
        )
        pipeline_stats["stages"]["ml_scoring"] = ml_scoring_stats
        
        if ml_scoring_stats.get("success"):
            logger.info(f"✅ ML Scoring complete: {ml_scoring_stats.get('total_updated', 0)} events updated")
        else:
            logger.warning("⚠️ ML Scoring completed with issues")
    
    except Exception as e:
        logger.error(f"❌ ML Scoring failed: {e}", exc_info=True)
        pipeline_stats["stages"]["ml_scoring"] = {"error": str(e)}
    
    # Success
    pipeline_stats["success"] = True
    pipeline_stats["finished_at"] = datetime.utcnow().isoformat()
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("✅ Daily ML Retraining Pipeline Complete")
    logger.info("="*80)
    
    trained_count = sum(1 for r in retraining_results.values() if r.get("trained"))
    promoted_count = sum(1 for r in retraining_results.values() if r.get("promoted"))
    events_scored = ml_scoring_stats.get("total_updated", 0) if ml_scoring_stats else 0
    
    logger.info(f"Summary:")
    logger.info(f"  Models trained: {trained_count}/3")
    logger.info(f"  Models promoted: {promoted_count}/3")
    logger.info(f"  Events scored with ML: {events_scored}")
    logger.info(f"  Overall health: {[h.get('status', 'unknown') for h in health_reports.values()]}")
    
    return pipeline_stats


def main():
    """Entry point for scheduled job."""
    logger.info("Starting Daily ML Retraining job")
    
    stats = run_daily_ml_retraining()
    
    if not stats["success"]:
        logger.error("Daily ML Retraining failed")
        sys.exit(1)
    else:
        logger.info("Daily ML Retraining completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
