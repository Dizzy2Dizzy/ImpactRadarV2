"""
ML Scores API Router - Endpoints for ML-adjusted impact scoring.

Provides endpoints for:
- Getting ML predictions for events
- Viewing active model information
- Tracking model performance over time
"""

from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from api.dependencies import get_db, get_data_manager
from api.utils.auth import get_current_user_with_plan
from releaseradar.db.models import Event, ModelRegistry, EventOutcome, ModelFeature
from releaseradar.ml.serving import MLScoringService
from releaseradar.ml.monitoring import ModelMonitor
from releaseradar.ml.event_type_families import get_event_family, EVENT_TYPE_FAMILIES, get_family_display_name
from releaseradar.log_config import logger


router = APIRouter(prefix="/ml-scores", tags=["ML Scoring"])


# Response schemas
class MLPredictionResponse(BaseModel):
    """ML prediction for an event with transparency fields."""
    event_id: int
    ticker: str
    event_type: str
    base_score: int = Field(ge=0, le=100)
    ml_prediction: int = Field(ge=0, le=100)
    ml_adjusted_score: int = Field(ge=0, le=100)
    ml_confidence: float = Field(ge=0.0, le=1.0)
    delta_applied: float
    max_delta_allowed: int = 20
    ml_model_version: str
    model_source: str = "deterministic"  # "family-specific", "global", or "deterministic"
    predicted_return_1d: Optional[float] = None
    predicted_at: datetime


class ActiveModelInfo(BaseModel):
    """Active model metadata."""
    name: str
    version: str
    status: str
    feature_version: str
    event_type_family: Optional[str] = None
    horizon: Optional[str] = None
    trained_at: datetime
    promoted_at: Optional[datetime]
    metrics: dict


class FamilyModelInfo(BaseModel):
    """Model information grouped by event type family."""
    family: str
    display_name: str
    has_dedicated_model: bool
    model: Optional[ActiveModelInfo] = None
    sample_count: int = 0
    event_types_in_family: List[str] = []


class GroupedModelInfo(BaseModel):
    """Models grouped by event type family with coverage info."""
    families: List[FamilyModelInfo]
    total_families: int
    families_with_models: int
    global_model: Optional[ActiveModelInfo] = None


class ModelPerformanceResponse(BaseModel):
    """Model performance metrics over time."""
    model_name: str
    horizon: str
    recent_accuracy: dict
    drift_metrics: dict
    health_status: str
    recommendation: dict


@router.get("/predict/{event_id}", response_model=MLPredictionResponse)
def get_ml_prediction(
    event_id: int,
    horizon: str = Query("1d", regex="^(1d|5d|20d)$"),
    db: Session = Depends(get_db)
):
    """
    Get ML prediction for a specific event.
    
    Args:
        event_id: Event ID to score
        horizon: Time horizon for prediction (1d, 5d, 20d)
        db: Database session
        
    Returns:
        ML prediction with score and confidence
    """
    # Check if event exists
    event = db.execute(
        select(Event).where(Event.id == event_id)
    ).scalar_one_or_none()
    
    if not event:
        raise HTTPException(status_code=404, detail=f"Event {event_id} not found")
    
    # Generate ML prediction
    scoring_service = MLScoringService(db)
    
    try:
        prediction = scoring_service.predict_single(event_id, horizon=horizon)
        
        if not prediction:
            raise HTTPException(
                status_code=503,
                detail=f"ML prediction not available (model may not be active or confidence too low)"
            )
        
        return MLPredictionResponse(
            event_id=event.id,
            ticker=event.ticker,
            event_type=event.event_type,
            base_score=prediction.base_score or event.impact_score,
            ml_prediction=prediction.ml_prediction_raw or prediction.ml_adjusted_score,
            ml_adjusted_score=prediction.ml_adjusted_score,
            ml_confidence=prediction.ml_confidence,
            delta_applied=prediction.delta_applied or 0.0,
            max_delta_allowed=20,
            ml_model_version=prediction.ml_model_version,
            model_source=prediction.model_source,
            predicted_return_1d=prediction.predicted_return_1d,
            predicted_at=prediction.predicted_at,
        )
    
    except Exception as e:
        logger.error(f"ML prediction failed for event {event_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")


@router.post("/predict/batch", response_model=List[MLPredictionResponse])
def get_ml_predictions_batch(
    event_ids: List[int],
    horizon: str = Query("1d", regex="^(1d|5d|20d)$"),
    db: Session = Depends(get_db)
):
    """
    Get ML predictions for multiple events.
    
    Args:
        event_ids: List of event IDs to score
        horizon: Time horizon for predictions
        db: Database session
        
    Returns:
        List of ML predictions
    """
    if len(event_ids) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 events per batch request")
    
    scoring_service = MLScoringService(db)
    
    try:
        predictions = scoring_service.predict_batch(event_ids, horizon=horizon)
        
        # Convert to response format
        responses = []
        for pred in predictions:
            event = db.execute(
                select(Event).where(Event.id == pred.event_id)
            ).scalar_one()
            
            responses.append(MLPredictionResponse(
                event_id=event.id,
                ticker=event.ticker,
                event_type=event.event_type,
                base_score=pred.base_score or event.impact_score,
                ml_prediction=pred.ml_prediction_raw or pred.ml_adjusted_score,
                ml_adjusted_score=pred.ml_adjusted_score,
                ml_confidence=pred.ml_confidence,
                delta_applied=pred.delta_applied or 0.0,
                max_delta_allowed=20,
                ml_model_version=pred.ml_model_version,
                model_source=pred.model_source,
                predicted_return_1d=pred.predicted_return_1d,
                predicted_at=pred.predicted_at,
            ))
        
        return responses
    
    except Exception as e:
        logger.error(f"Batch ML prediction failed: {e}")
        raise HTTPException(status_code=500, detail=f"Batch prediction failed: {str(e)}")


@router.get("/model-info", response_model=GroupedModelInfo)
def get_active_models(
    horizon: str = Query("1d", regex="^(1d|5d|20d)$"),
    db: Session = Depends(get_db)
):
    """
    Get information about active ML models grouped by event type family.
    
    Shows which families have dedicated models vs rely on global fallback,
    and includes sample counts per family from the training data.
    
    Args:
        horizon: Time horizon filter (1d, 5d, or 20d)
        db: Database session
        
    Returns:
        Grouped model information with coverage statistics
    """
    # Get all active models for this horizon
    active_models = db.execute(
        select(ModelRegistry)
        .where(ModelRegistry.status == "active")
        .where(ModelRegistry.horizon == horizon)
        .order_by(ModelRegistry.promoted_at.desc())
    ).scalars().all()
    
    # Build lookup by family
    models_by_family = {}
    global_model = None
    
    for model in active_models:
        if model.event_type_family == "all":
            global_model = ActiveModelInfo(
                name=model.name,
                version=model.version,
                status=model.status,
                feature_version=model.feature_version,
                event_type_family=model.event_type_family,
                horizon=model.horizon,
                trained_at=model.trained_at,
                promoted_at=model.promoted_at,
                metrics=model.metrics,
            )
        elif model.event_type_family:
            models_by_family[model.event_type_family] = ActiveModelInfo(
                name=model.name,
                version=model.version,
                status=model.status,
                feature_version=model.feature_version,
                event_type_family=model.event_type_family,
                horizon=model.horizon,
                trained_at=model.trained_at,
                promoted_at=model.promoted_at,
                metrics=model.metrics,
            )
    
    # Get sample counts per family from event outcomes
    # Use JOIN to fetch outcomes and events in a single query (avoids N+1)
    sample_counts = {}
    outcomes_with_events = db.execute(
        select(EventOutcome, Event)
        .join(Event, EventOutcome.event_id == Event.id)
        .where(EventOutcome.horizon == horizon)
    ).all()
    
    for outcome, event in outcomes_with_events:
        family = get_event_family(event.event_type)
        sample_counts[family] = sample_counts.get(family, 0) + 1
    
    # Build family info
    family_infos = []
    for family, event_types in EVENT_TYPE_FAMILIES.items():
        model = models_by_family.get(family)
        family_info = FamilyModelInfo(
            family=family,
            display_name=get_family_display_name(family),
            has_dedicated_model=model is not None,
            model=model,
            sample_count=sample_counts.get(family, 0),
            event_types_in_family=event_types,
        )
        family_infos.append(family_info)
    
    # Sort by sample count descending
    family_infos.sort(key=lambda x: x.sample_count, reverse=True)
    
    return GroupedModelInfo(
        families=family_infos,
        total_families=len(family_infos),
        families_with_models=len(models_by_family),
        global_model=global_model,
    )


@router.get("/model-info/{horizon}", response_model=ActiveModelInfo)
def get_active_model_by_horizon(
    horizon: str = Path(..., pattern="^(1d|5d|20d)$"),
    db: Session = Depends(get_db)
):
    """
    Get active model for specific horizon.
    
    Args:
        horizon: Time horizon
        db: Database session
        
    Returns:
        Active model information
    """
    model_name = f"xgboost_impact_{horizon}"
    
    model = db.execute(
        select(ModelRegistry)
        .where(ModelRegistry.name == model_name)
        .where(ModelRegistry.status == "active")
        .order_by(ModelRegistry.promoted_at.desc())
    ).scalar_one_or_none()
    
    if not model:
        raise HTTPException(status_code=404, detail=f"No active model found for {horizon}")
    
    return ActiveModelInfo(
        name=model.name,
        version=model.version,
        status=model.status,
        feature_version=model.feature_version,
        event_type_family=model.event_type_family,
        horizon=model.horizon,
        trained_at=model.trained_at,
        promoted_at=model.promoted_at,
        metrics=model.metrics,
    )


@router.get("/performance/{horizon}", response_model=ModelPerformanceResponse)
def get_model_performance(
    horizon: str = Path(..., pattern="^(1d|5d|20d)$"),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive model performance and health metrics.
    
    Args:
        horizon: Time horizon
        db: Database session
        
    Returns:
        Model performance report
    """
    model_name = f"xgboost_impact_{horizon}"
    
    monitor = ModelMonitor(db)
    
    try:
        health_report = monitor.get_model_health(model_name, horizon)
        
        if "status" not in health_report or health_report["status"] == "no_active_model":
            raise HTTPException(status_code=404, detail=f"No active model found for {horizon}")
        
        return ModelPerformanceResponse(
            model_name=model_name,
            horizon=horizon,
            recent_accuracy=health_report.get("accuracy_metrics", {}),
            drift_metrics=health_report.get("drift_metrics", {}),
            health_status=health_report.get("status", "unknown"),
            recommendation=health_report.get("retrain_recommendation", {}),
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get performance: {str(e)}")


@router.get("/stats", response_model=dict)
def get_ml_stats(
    db: Session = Depends(get_db)
):
    """
    Get overall ML system statistics.
    
    Args:
        db: Database session
        
    Returns:
        Statistics about the ML system
    """
    # Count labeled outcomes
    outcome_count = db.execute(
        select(EventOutcome)
    ).scalars().all()
    
    outcomes_by_horizon = {
        "1d": len([o for o in outcome_count if o.horizon == "1d"]),
        "5d": len([o for o in outcome_count if o.horizon == "5d"]),
        "20d": len([o for o in outcome_count if o.horizon == "20d"]),
    }
    
    # Count features
    feature_count = db.execute(
        select(ModelFeature)
    ).scalars().all()
    
    features_by_horizon = {
        "1d": len([f for f in feature_count if f.horizon == "1d"]),
        "5d": len([f for f in feature_count if f.horizon == "5d"]),
        "20d": len([f for f in feature_count if f.horizon == "20d"]),
    }
    
    # Count events with ML scores
    events_with_ml = db.execute(
        select(Event).where(Event.ml_adjusted_score.isnot(None))
    ).scalars().all()
    
    # Count models
    models = db.execute(
        select(ModelRegistry)
    ).scalars().all()
    
    models_by_status = {
        "active": len([m for m in models if m.status == "active"]),
        "staging": len([m for m in models if m.status == "staging"]),
        "archived": len([m for m in models if m.status == "archived"]),
    }
    
    return {
        "total_labeled_outcomes": len(outcome_count),
        "outcomes_by_horizon": outcomes_by_horizon,
        "total_feature_records": len(feature_count),
        "features_by_horizon": features_by_horizon,
        "events_with_ml_scores": len(events_with_ml),
        "total_models": len(models),
        "models_by_status": models_by_status,
        "last_updated": datetime.utcnow().isoformat(),
    }


# ML Monitoring Dashboard Schemas
class LabeledEventsStats(BaseModel):
    """Statistics about labeled training data."""
    total_labeled_events: int
    unique_tickers: int
    labeled_by_family: dict  # {family: {1d: count, 5d: count, 20d: count, tickers: count}}
    labeled_by_horizon: dict  # {1d: count, 5d: count, 20d: count}
    earliest_label_date: Optional[str]
    latest_label_date: Optional[str]


class AccuracyMetricsDetailed(BaseModel):
    """Detailed accuracy metrics for a horizon."""
    horizon: str
    total_samples: int
    directional_accuracy: Optional[float]
    high_confidence_accuracy: Optional[float]
    high_confidence_samples: int
    mae: Optional[float]
    rmse: Optional[float]
    mean_actual_return: Optional[float]
    std_actual_return: Optional[float]


class CalibrationBucket(BaseModel):
    """Calibration data for a prediction score bucket."""
    score_range: str  # e.g., "50-60"
    predicted_avg: float
    actual_avg: float
    sample_count: int
    calibration_error: float


class CalibrationAnalysis(BaseModel):
    """Calibration analysis for each horizon."""
    horizon: str
    buckets: List[CalibrationBucket]
    overall_calibration_error: float


class FamilyModelStatus(BaseModel):
    """Model status for an event family."""
    family: str
    display_name: str
    labeled_events_1d: int
    labeled_events_5d: int
    labeled_events_20d: int
    unique_tickers: int
    model_type_1d: str  # "family-specific" | "global" | "deterministic-only"
    model_type_5d: str
    model_type_20d: str
    model_version_1d: Optional[str]
    model_version_5d: Optional[str]
    model_version_20d: Optional[str]
    health_status_1d: str  # "Production Ready" | "Prototype" | "Insufficient Data"
    health_status_5d: str
    health_status_20d: str
    directional_accuracy_1d: Optional[float]
    directional_accuracy_5d: Optional[float]
    directional_accuracy_20d: Optional[float]


class MLMonitoringDashboard(BaseModel):
    """Complete ML monitoring dashboard data."""
    labeled_events: LabeledEventsStats
    accuracy_by_horizon: List[AccuracyMetricsDetailed]
    calibration_by_horizon: List[CalibrationAnalysis]
    family_model_status: List[FamilyModelStatus]
    generated_at: str


@router.get("/monitoring", response_model=MLMonitoringDashboard)
def get_ml_monitoring_dashboard(
    mode: Optional[str] = Query(None, description="Dashboard mode: watchlist or portfolio"),
    user_data: dict = Depends(get_current_user_with_plan),
    dm = Depends(get_data_manager),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive ML monitoring dashboard data.
    
    This endpoint provides all metrics needed for internal ML monitoring:
    - Labeled training data statistics
    - Out-of-sample accuracy metrics
    - Calibration analysis (predicted vs actual)
    - Per-family model status and health
    
    Supports filtering by dashboard mode (watchlist/portfolio).
    
    Cached for 5 minutes to reduce database load.
    
    Args:
        mode: Dashboard mode for filtering
        user_data: Current user data
        dm: Data manager for getting user tickers
        db: Database session
        
    Returns:
        Complete monitoring dashboard data
    """
    from sqlalchemy import func, case
    import numpy as np
    
    # Get active tickers if mode is specified
    tickers_filter = None
    if mode and mode in ['watchlist', 'portfolio']:
        tickers_filter = dm.get_user_active_tickers(user_data["user_id"], mode)
    
    # === 1. LABELED EVENTS STATISTICS ===
    
    # Get all labeled outcomes with event info (filter by tickers if mode is active)
    query = select(EventOutcome, Event).join(Event, EventOutcome.event_id == Event.id)
    
    # Filter by tickers if provided
    if tickers_filter is not None:
        if len(tickers_filter) == 0:
            # Empty watchlist/portfolio: return empty dashboard
            return MLMonitoringDashboard(
                labeled_events=LabeledEventsStats(
                    total_labeled_events=0,
                    unique_tickers=0,
                    labeled_by_family={},
                    labeled_by_horizon={1: 0, 5: 0, 20: 0},
                    earliest_label_date=None,
                    latest_label_date=None,
                ),
                accuracy_by_horizon=[],
                calibration_by_horizon=[],
                family_model_status=[],
                generated_at=datetime.utcnow().isoformat(),
            )
        else:
            query = query.where(Event.ticker.in_(tickers_filter))
    
    outcomes_with_events = db.execute(query).all()
    
    total_outcomes = len(outcomes_with_events)
    unique_tickers = len(set(event.ticker for _, event in outcomes_with_events))
    
    # Group by family and horizon
    from collections import defaultdict
    family_stats = defaultdict(lambda: {"1d": 0, "5d": 0, "20d": 0, "tickers": set()})
    horizon_stats = defaultdict(int)
    
    earliest_date = None
    latest_date = None
    
    for outcome, event in outcomes_with_events:
        family = get_event_family(event.event_type)
        family_stats[family][outcome.horizon] += 1
        family_stats[family]["tickers"].add(event.ticker)
        horizon_stats[outcome.horizon] += 1
        
        if earliest_date is None or outcome.label_date < earliest_date:
            earliest_date = outcome.label_date
        if latest_date is None or outcome.label_date > latest_date:
            latest_date = outcome.label_date
    
    # Convert to serializable format with NUMERIC keys (fresh dicts to avoid string key pollution)
    # Frontend expects {1: count, 5: count, 20: count} NOT {"1d": count, "5d": count, "20d": count}
    labeled_by_family = {
        family: {
            1: int(stats["1d"]),
            5: int(stats["5d"]),
            20: int(stats["20d"]),
            "tickers": int(len(stats["tickers"]))
        }
        for family, stats in family_stats.items()
    }
    
    # Convert horizon_stats to use numeric keys (fresh dict to avoid string key pollution)
    labeled_by_horizon = {
        1: int(horizon_stats.get("1d", 0)),
        5: int(horizon_stats.get("5d", 0)),
        20: int(horizon_stats.get("20d", 0)),
    }
    
    labeled_events_stats = LabeledEventsStats(
        total_labeled_events=total_outcomes,
        unique_tickers=unique_tickers,
        labeled_by_family=labeled_by_family,
        labeled_by_horizon=labeled_by_horizon,
        earliest_label_date=earliest_date.isoformat() if earliest_date else None,
        latest_label_date=latest_date.isoformat() if latest_date else None,
    )
    
    # === 2. ACCURACY METRICS BY HORIZON ===
    
    accuracy_metrics = []
    
    for horizon in ["1d", "5d", "20d"]:
        horizon_outcomes = [o for o, _ in outcomes_with_events if o.horizon == horizon]
        
        if not horizon_outcomes:
            accuracy_metrics.append(AccuracyMetricsDetailed(
                horizon=horizon,
                total_samples=0,
                directional_accuracy=None,
                high_confidence_accuracy=None,
                high_confidence_samples=0,
                mae=None,
                rmse=None,
                mean_actual_return=None,
                std_actual_return=None,
            ))
            continue
        
        # Directional accuracy (convert to percentage)
        correct_count = sum(1 for o in horizon_outcomes if o.direction_correct)
        directional_accuracy = (correct_count / len(horizon_outcomes) * 100) if horizon_outcomes else None
        
        # High confidence accuracy (events with impact_score >= 70)
        high_conf_outcomes = []
        for outcome, event_pair in outcomes_with_events:
            outcome_obj, event_obj = outcome, event_pair
            if outcome_obj.horizon == horizon and event_obj.impact_score >= 70:
                high_conf_outcomes.append(outcome_obj)
        
        high_conf_correct = sum(1 for o in high_conf_outcomes if o.direction_correct)
        high_conf_accuracy = (high_conf_correct / len(high_conf_outcomes) * 100) if high_conf_outcomes else None
        
        # Magnitude metrics
        returns = [o.return_pct for o in horizon_outcomes]
        mae = np.mean([abs(r) for r in returns]) if returns else None
        rmse = np.sqrt(np.mean([r**2 for r in returns])) if returns else None
        mean_return = np.mean(returns) if returns else None
        std_return = np.std(returns) if returns else None
        
        accuracy_metrics.append(AccuracyMetricsDetailed(
            horizon=horizon,
            total_samples=len(horizon_outcomes),
            directional_accuracy=directional_accuracy,
            high_confidence_accuracy=high_conf_accuracy,
            high_confidence_samples=len(high_conf_outcomes),
            mae=float(mae) if mae is not None else None,
            rmse=float(rmse) if rmse is not None else None,
            mean_actual_return=float(mean_return) if mean_return is not None else None,
            std_actual_return=float(std_return) if std_return is not None else None,
        ))
    
    # === 3. CALIBRATION ANALYSIS ===
    
    calibration_analyses = []
    
    for horizon in ["1d", "5d", "20d"]:
        # Get outcomes with events for this horizon
        horizon_data = [(o, e) for o, e in outcomes_with_events if o.horizon == horizon]
        
        if not horizon_data:
            calibration_analyses.append(CalibrationAnalysis(
                horizon=horizon,
                buckets=[],
                overall_calibration_error=0.0,
            ))
            continue
        
        # Define score buckets
        buckets_def = [
            (0, 40, "0-40"),
            (40, 50, "40-50"),
            (50, 60, "50-60"),
            (60, 70, "60-70"),
            (70, 80, "70-80"),
            (80, 100, "80-100"),
        ]
        
        calibration_buckets = []
        total_calibration_error = 0.0
        
        for min_score, max_score, bucket_name in buckets_def:
            # Get events in this bucket
            bucket_data = [
                (o, e) for o, e in horizon_data
                if e.impact_score >= min_score and e.impact_score < max_score
            ]
            
            if not bucket_data:
                continue
            
            # Calculate average predicted impact (normalize score to %)
            # Use a scaling factor: score 50 = 0%, score 100 = 12%
            predicted_impacts = []
            for outcome, event in bucket_data:
                # Map score to predicted % move: (score / 100) * 12%
                predicted_pct = (event.impact_score / 100.0) * 12.0
                predicted_impacts.append(predicted_pct)
            
            predicted_avg = np.mean(predicted_impacts)
            
            # Calculate average actual return
            actual_returns = [abs(o.return_pct) for o, _ in bucket_data]
            actual_avg = np.mean(actual_returns)
            
            calibration_error = abs(predicted_avg - actual_avg)
            total_calibration_error += calibration_error
            
            calibration_buckets.append(CalibrationBucket(
                score_range=bucket_name,
                predicted_avg=float(predicted_avg),
                actual_avg=float(actual_avg),
                sample_count=len(bucket_data),
                calibration_error=float(calibration_error),
            ))
        
        overall_error = total_calibration_error / len(calibration_buckets) if calibration_buckets else 0.0
        
        calibration_analyses.append(CalibrationAnalysis(
            horizon=horizon,
            buckets=calibration_buckets,
            overall_calibration_error=float(overall_error),
        ))
    
    # === 4. PER-FAMILY MODEL STATUS ===
    
    family_statuses = []
    
    for family, event_types in EVENT_TYPE_FAMILIES.items():
        # Count labeled events for this family
        family_outcomes = [
            (o, e) for o, e in outcomes_with_events
            if get_event_family(e.event_type) == family
        ]
        
        labeled_1d = len([o for o, _ in family_outcomes if o.horizon == "1d"])
        labeled_5d = len([o for o, _ in family_outcomes if o.horizon == "5d"])
        labeled_20d = len([o for o, _ in family_outcomes if o.horizon == "20d"])
        
        unique_tickers_family = len(set(e.ticker for _, e in family_outcomes))
        
        # Determine model type and version for each horizon
        model_info_by_horizon = {}
        
        for horizon in ["1d", "5d", "20d"]:
            # Check for family-specific model
            family_model = db.execute(
                select(ModelRegistry)
                .where(ModelRegistry.event_type_family == family)
                .where(ModelRegistry.horizon == horizon)
                .where(ModelRegistry.status == "active")
                .order_by(ModelRegistry.promoted_at.desc())
            ).scalar_one_or_none()
            
            if family_model:
                model_type = "family-specific"
                model_version = family_model.version
                directional_acc = family_model.metrics.get("directional_accuracy")
            else:
                # Check for global model
                global_model = db.execute(
                    select(ModelRegistry)
                    .where(ModelRegistry.event_type_family == "all")
                    .where(ModelRegistry.horizon == horizon)
                    .where(ModelRegistry.status == "active")
                    .order_by(ModelRegistry.promoted_at.desc())
                ).scalar_one_or_none()
                
                if global_model:
                    model_type = "global"
                    model_version = global_model.version
                    directional_acc = global_model.metrics.get("directional_accuracy")
                else:
                    model_type = "deterministic-only"
                    model_version = None
                    directional_acc = None
            
            model_info_by_horizon[horizon] = {
                "type": model_type,
                "version": model_version,
                "accuracy": directional_acc,
            }
        
        # Determine health status for each horizon
        def get_health_status(labeled_count: int, tickers: int, model_type: str) -> str:
            if model_type == "family-specific" and labeled_count >= 100 and tickers >= 20:
                return "Production Ready"
            elif labeled_count >= 30 and tickers >= 10:
                return "Prototype"
            else:
                return "Insufficient Data"
        
        status_1d = get_health_status(labeled_1d, unique_tickers_family, model_info_by_horizon["1d"]["type"])
        status_5d = get_health_status(labeled_5d, unique_tickers_family, model_info_by_horizon["5d"]["type"])
        status_20d = get_health_status(labeled_20d, unique_tickers_family, model_info_by_horizon["20d"]["type"])
        
        family_statuses.append(FamilyModelStatus(
            family=family,
            display_name=get_family_display_name(family),
            labeled_events_1d=labeled_1d,
            labeled_events_5d=labeled_5d,
            labeled_events_20d=labeled_20d,
            unique_tickers=unique_tickers_family,
            model_type_1d=model_info_by_horizon["1d"]["type"],
            model_type_5d=model_info_by_horizon["5d"]["type"],
            model_type_20d=model_info_by_horizon["20d"]["type"],
            model_version_1d=model_info_by_horizon["1d"]["version"],
            model_version_5d=model_info_by_horizon["5d"]["version"],
            model_version_20d=model_info_by_horizon["20d"]["version"],
            health_status_1d=status_1d,
            health_status_5d=status_5d,
            health_status_20d=status_20d,
            directional_accuracy_1d=model_info_by_horizon["1d"]["accuracy"],
            directional_accuracy_5d=model_info_by_horizon["5d"]["accuracy"],
            directional_accuracy_20d=model_info_by_horizon["20d"]["accuracy"],
        ))
    
    # Sort by total labeled events (descending)
    family_statuses.sort(
        key=lambda f: f.labeled_events_1d + f.labeled_events_5d + f.labeled_events_20d,
        reverse=True
    )
    
    return MLMonitoringDashboard(
        labeled_events=labeled_events_stats,
        accuracy_by_horizon=accuracy_metrics,
        calibration_by_horizon=calibration_analyses,
        family_model_status=family_statuses,
        generated_at=datetime.utcnow().isoformat(),
    )
