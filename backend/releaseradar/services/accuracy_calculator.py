"""
Accuracy calculation service for Impact Radar prediction metrics.

Calculates win rates, MAE, RMSE, and Sharpe ratios by comparing
predicted event impacts to actual price movements from EventOutcome data.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
import numpy as np
from sqlalchemy import and_, func, desc
from sqlalchemy.orm import Session
from loguru import logger

from releaseradar.db.models import (
    Event,
    EventOutcome,
    PredictionMetrics,
    PredictionSnapshot,
)


def calculate_prediction_metrics(
    db: Session,
    model_version: str,
    event_type: Optional[str] = None,
    horizon: str = "5d",
    calculation_date: Optional[date] = None,
) -> Optional[PredictionMetrics]:
    """
    Retrieve or calculate prediction accuracy metrics for a specific model, event type, and horizon.
    
    First attempts to retrieve existing pre-calculated metrics from the PredictionMetrics table.
    If no exact match is found, tries to find the most recent metrics for the same parameters.
    Only falls back to calculating from EventOutcome data if no existing metrics are found.
    
    Args:
        db: Database session
        model_version: Model version to evaluate (e.g., "v1.0", "xgboost_1.0.0")
        event_type: Optional event type filter (e.g., "earnings", "fda_approval")
        horizon: Time horizon to evaluate ("1d", "5d", "7d", "20d", "30d")
        calculation_date: Date of calculation (defaults to today)
    
    Returns:
        PredictionMetrics object with metrics, or None if no data available
    """
    if calculation_date is None:
        calculation_date = date.today()
    
    event_type_key = event_type or "all"
    is_aggregate_query = event_type is None or event_type == "all"
    
    # First, try to retrieve existing metrics from PredictionMetrics table for exact date
    existing_metrics = db.query(PredictionMetrics).filter(
        and_(
            PredictionMetrics.model_version == model_version,
            PredictionMetrics.event_type == event_type_key,
            PredictionMetrics.horizon == horizon,
            PredictionMetrics.date == calculation_date
        )
    ).first()
    
    if existing_metrics:
        logger.info(
            f"Retrieved existing PredictionMetrics: model={model_version}, type={event_type_key}, "
            f"horizon={horizon}, date={calculation_date}, win_rate={existing_metrics.win_rate:.2f}%"
        )
        return existing_metrics
    
    # If no exact match for the requested date, try to get the most recent metrics
    # (within last 30 days to avoid returning stale data)
    recent_cutoff = calculation_date - timedelta(days=30)
    recent_metrics = db.query(PredictionMetrics).filter(
        and_(
            PredictionMetrics.model_version == model_version,
            PredictionMetrics.event_type == event_type_key,
            PredictionMetrics.horizon == horizon,
            PredictionMetrics.date >= recent_cutoff,
            PredictionMetrics.date <= calculation_date
        )
    ).order_by(desc(PredictionMetrics.date)).first()
    
    if recent_metrics:
        logger.info(
            f"Retrieved recent PredictionMetrics: model={model_version}, type={event_type_key}, "
            f"horizon={horizon}, date={recent_metrics.date}, win_rate={recent_metrics.win_rate:.2f}%"
        )
        return recent_metrics
    
    # For aggregate queries (None or "all"), try to aggregate from existing event type metrics
    if is_aggregate_query:
        logger.info(
            f"No 'all' metrics found, attempting to aggregate from individual event type metrics: "
            f"model={model_version}, horizon={horizon}"
        )
        
        # Get all metrics for this model/horizon across all event types
        event_type_metrics = db.query(PredictionMetrics).filter(
            and_(
                PredictionMetrics.model_version == model_version,
                PredictionMetrics.event_type != "all",
                PredictionMetrics.horizon == horizon,
                PredictionMetrics.date >= recent_cutoff,
                PredictionMetrics.date <= calculation_date
            )
        ).all()
        
        if event_type_metrics:
            # Aggregate metrics across all event types
            total_predictions = 0
            total_correct = 0
            total_mae_weighted = 0.0
            total_rmse_weighted = 0.0
            total_sharpe_weighted = 0.0
            total_confidence_weighted = 0.0
            
            high_conf_total = 0
            high_conf_correct = 0
            med_conf_total = 0
            med_conf_correct = 0
            low_conf_total = 0
            low_conf_correct = 0
            
            sharpe_count = 0
            
            for metric in event_type_metrics:
                count = metric.total_predictions or 0
                if count == 0:
                    continue
                
                total_predictions += count
                total_correct += metric.correct_direction or 0
                total_mae_weighted += (metric.mae or 0.0) * count
                total_rmse_weighted += (metric.rmse or 0.0) * count
                
                if metric.sharpe_ratio is not None:
                    total_sharpe_weighted += metric.sharpe_ratio * count
                    sharpe_count += count
                
                total_confidence_weighted += (metric.avg_confidence or 0.0) * count
                
                # Aggregate confidence buckets (approximate from win rates)
                if metric.high_conf_win_rate is not None:
                    # Estimate count from overall total * typical high conf proportion (~30%)
                    est_high_count = int(count * 0.3)
                    high_conf_total += est_high_count
                    high_conf_correct += int(est_high_count * metric.high_conf_win_rate / 100)
                
                if metric.med_conf_win_rate is not None:
                    est_med_count = int(count * 0.5)
                    med_conf_total += est_med_count
                    med_conf_correct += int(est_med_count * metric.med_conf_win_rate / 100)
                
                if metric.low_conf_win_rate is not None:
                    est_low_count = int(count * 0.2)
                    low_conf_total += est_low_count
                    low_conf_correct += int(est_low_count * metric.low_conf_win_rate / 100)
            
            if total_predictions > 0:
                aggregated_win_rate = (total_correct / total_predictions * 100)
                aggregated_mae = total_mae_weighted / total_predictions
                aggregated_rmse = total_rmse_weighted / total_predictions
                aggregated_sharpe = total_sharpe_weighted / sharpe_count if sharpe_count > 0 else None
                aggregated_confidence = total_confidence_weighted / total_predictions
                
                aggregated_high_conf_win_rate = (high_conf_correct / high_conf_total * 100) if high_conf_total > 0 else None
                aggregated_med_conf_win_rate = (med_conf_correct / med_conf_total * 100) if med_conf_total > 0 else None
                aggregated_low_conf_win_rate = (low_conf_correct / low_conf_total * 100) if low_conf_total > 0 else None
                
                # Create aggregated metric record
                metrics = PredictionMetrics(
                    model_version=model_version,
                    event_type="all",
                    horizon=horizon,
                    date=calculation_date,
                    total_predictions=total_predictions,
                    correct_direction=total_correct,
                    win_rate=aggregated_win_rate,
                    mae=aggregated_mae,
                    rmse=aggregated_rmse,
                    sharpe_ratio=aggregated_sharpe,
                    avg_confidence=aggregated_confidence,
                    high_conf_win_rate=aggregated_high_conf_win_rate,
                    med_conf_win_rate=aggregated_med_conf_win_rate,
                    low_conf_win_rate=aggregated_low_conf_win_rate,
                )
                
                db.add(metrics)
                db.commit()
                db.refresh(metrics)
                
                logger.info(
                    f"Created aggregated PredictionMetrics from {len(event_type_metrics)} event type metrics: "
                    f"model={model_version}, horizon={horizon}, win_rate={aggregated_win_rate:.2f}%, "
                    f"total_predictions={total_predictions}"
                )
                
                return metrics
    
    # Fall back to calculating from EventOutcome data if no existing metrics found
    logger.info(
        f"No existing metrics found, attempting to calculate from EventOutcome data: "
        f"model={model_version}, type={event_type_key}, horizon={horizon}"
    )
    
    # Build query to join Events with EventOutcomes
    query = db.query(Event, EventOutcome).join(
        EventOutcome,
        and_(
            EventOutcome.event_id == Event.id,
            EventOutcome.horizon == horizon
        )
    ).filter(
        Event.ml_model_version == model_version
    )
    
    # Apply event_type filter only if a specific type is requested (not None or "all")
    if event_type and event_type != "all":
        query = query.filter(Event.event_type == event_type)
    
    # Execute query
    results = query.all()
    
    if not results:
        logger.warning(
            f"No EventOutcome data found for model={model_version}, event_type={event_type}, horizon={horizon}"
        )
        return None
    
    # Extract data for calculations
    predicted_returns = []
    actual_returns = []
    confidences = []
    correct_directions = []
    
    high_conf_correct = []  # confidence > 0.7
    med_conf_correct = []   # 0.4 < confidence <= 0.7
    low_conf_correct = []   # confidence <= 0.4
    
    for event, outcome in results:
        # Get predicted return from direction and impact score
        # Direction: "up" = positive, "down" = negative, "neutral" = 0
        predicted_return = 0.0
        if event.direction == "up":
            predicted_return = event.impact_score / 10.0  # Normalize to approximate %
        elif event.direction == "down":
            predicted_return = -event.impact_score / 10.0
        
        predicted_returns.append(predicted_return)
        actual_returns.append(outcome.return_pct)
        
        # Confidence (use ml_confidence or fallback to confidence)
        confidence = event.ml_confidence if event.ml_confidence else event.confidence
        confidences.append(confidence)
        
        # Direction correctness
        is_correct = outcome.direction_correct if outcome.direction_correct is not None else False
        correct_directions.append(is_correct)
        
        # Bucket by confidence
        if confidence > 0.7:
            high_conf_correct.append(is_correct)
        elif confidence > 0.4:
            med_conf_correct.append(is_correct)
        else:
            low_conf_correct.append(is_correct)
    
    # Calculate metrics
    total_predictions = len(results)
    correct_direction_count = sum(correct_directions)
    win_rate = (correct_direction_count / total_predictions * 100) if total_predictions > 0 else 0.0
    
    # MAE (Mean Absolute Error)
    errors = [abs(pred - actual) for pred, actual in zip(predicted_returns, actual_returns)]
    mae = float(np.mean(errors)) if errors else 0.0
    
    # RMSE (Root Mean Squared Error)
    squared_errors = [(pred - actual) ** 2 for pred, actual in zip(predicted_returns, actual_returns)]
    rmse = float(np.sqrt(np.mean(squared_errors))) if squared_errors else 0.0
    
    # Sharpe Ratio (annualized)
    # Sharpe = mean(returns) / std(returns) * sqrt(252)
    sharpe_ratio = None
    if len(actual_returns) > 1:
        mean_return = np.mean(actual_returns)
        std_return = np.std(actual_returns)
        if std_return > 0:
            # Annualize based on horizon
            horizon_days = int(horizon.replace("d", ""))
            scaling_factor = np.sqrt(252 / horizon_days)
            sharpe_ratio = float((mean_return / std_return) * scaling_factor)
    
    # Average confidence
    avg_confidence = float(np.mean(confidences)) if confidences else 0.0
    
    # Confidence bucket win rates
    high_conf_win_rate = (sum(high_conf_correct) / len(high_conf_correct) * 100) if high_conf_correct else None
    med_conf_win_rate = (sum(med_conf_correct) / len(med_conf_correct) * 100) if med_conf_correct else None
    low_conf_win_rate = (sum(low_conf_correct) / len(low_conf_correct) * 100) if low_conf_correct else None
    
    # Create or update PredictionMetrics record
    event_type_key = event_type or "all"
    
    # Check if record exists
    existing = db.query(PredictionMetrics).filter(
        and_(
            PredictionMetrics.model_version == model_version,
            PredictionMetrics.event_type == event_type_key,
            PredictionMetrics.horizon == horizon,
            PredictionMetrics.date == calculation_date
        )
    ).first()
    
    if existing:
        # Update existing record
        existing.total_predictions = total_predictions
        existing.correct_direction = correct_direction_count
        existing.win_rate = win_rate
        existing.mae = mae
        existing.rmse = rmse
        existing.sharpe_ratio = sharpe_ratio
        existing.avg_confidence = avg_confidence
        existing.high_conf_win_rate = high_conf_win_rate
        existing.med_conf_win_rate = med_conf_win_rate
        existing.low_conf_win_rate = low_conf_win_rate
        existing.updated_at = datetime.utcnow()
        
        logger.info(
            f"Updated PredictionMetrics: model={model_version}, type={event_type_key}, "
            f"horizon={horizon}, win_rate={win_rate:.2f}%, mae={mae:.2f}"
        )
        
        db.commit()
        return existing
    else:
        # Create new record
        metrics = PredictionMetrics(
            model_version=model_version,
            event_type=event_type_key,
            horizon=horizon,
            date=calculation_date,
            total_predictions=total_predictions,
            correct_direction=correct_direction_count,
            win_rate=win_rate,
            mae=mae,
            rmse=rmse,
            sharpe_ratio=sharpe_ratio,
            avg_confidence=avg_confidence,
            high_conf_win_rate=high_conf_win_rate,
            med_conf_win_rate=med_conf_win_rate,
            low_conf_win_rate=low_conf_win_rate,
        )
        
        db.add(metrics)
        db.commit()
        db.refresh(metrics)
        
        logger.info(
            f"Created PredictionMetrics: model={model_version}, type={event_type_key}, "
            f"horizon={horizon}, win_rate={win_rate:.2f}%, mae={mae:.2f}"
        )
        
        return metrics


def create_snapshot(
    db: Session,
    model_version: str,
    snapshot_time: Optional[datetime] = None,
) -> PredictionSnapshot:
    """
    Retrieve or create a point-in-time snapshot of overall prediction accuracy.
    
    First attempts to retrieve an existing snapshot from the PredictionSnapshot table.
    If no recent snapshot exists, aggregates metrics from PredictionMetrics table.
    Only falls back to calculating from EventOutcome data if no existing data is found.
    
    Args:
        db: Database session
        model_version: Model version to snapshot
        snapshot_time: Timestamp for snapshot (defaults to now)
    
    Returns:
        PredictionSnapshot object
    """
    if snapshot_time is None:
        snapshot_time = datetime.utcnow()
    
    # First, try to retrieve the most recent snapshot for this model
    # (within last 24 hours to get fresh data)
    recent_cutoff = snapshot_time - timedelta(hours=24)
    existing_snapshot = db.query(PredictionSnapshot).filter(
        and_(
            PredictionSnapshot.model_version == model_version,
            PredictionSnapshot.timestamp >= recent_cutoff,
            PredictionSnapshot.timestamp <= snapshot_time
        )
    ).order_by(desc(PredictionSnapshot.timestamp)).first()
    
    if existing_snapshot:
        logger.info(
            f"Retrieved existing PredictionSnapshot: model={model_version}, "
            f"timestamp={existing_snapshot.timestamp}, win_rate={existing_snapshot.overall_win_rate:.2f}%"
        )
        return existing_snapshot
    
    # If no recent snapshot, try to aggregate from PredictionMetrics table
    logger.info(
        f"No recent snapshot found, attempting to aggregate from PredictionMetrics: "
        f"model={model_version}"
    )
    
    # Get all metrics for this model version from the last 7 days
    recent_date_cutoff = date.today() - timedelta(days=7)
    metrics_query = db.query(PredictionMetrics).filter(
        and_(
            PredictionMetrics.model_version == model_version,
            PredictionMetrics.date >= recent_date_cutoff
        )
    ).all()
    
    if metrics_query:
        # Aggregate metrics from PredictionMetrics table
        total_predictions = 0
        total_correct = 0
        total_mae_weighted = 0.0
        metrics_by_horizon = {}
        
        for metric in metrics_query:
            if metric.event_type == "all":  # Only use overall metrics
                horizon = metric.horizon
                if horizon not in metrics_by_horizon:
                    metrics_by_horizon[horizon] = {
                        "win_rate": metric.win_rate or 0.0,
                        "mae": metric.mae or 0.0,
                        "count": metric.total_predictions or 0,
                    }
                
                # Aggregate for overall metrics
                total_predictions += metric.total_predictions or 0
                total_correct += metric.correct_direction or 0
                total_mae_weighted += (metric.mae or 0.0) * (metric.total_predictions or 0)
        
        overall_win_rate = (total_correct / total_predictions * 100) if total_predictions > 0 else 0.0
        overall_mae = total_mae_weighted / total_predictions if total_predictions > 0 else 0.0
        
        # Build metrics JSON
        metrics_json = {
            "by_horizon": metrics_by_horizon,
            "timestamp": snapshot_time.isoformat(),
            "total_events": total_predictions,
        }
        
        # Create snapshot from aggregated metrics
        snapshot = PredictionSnapshot(
            model_version=model_version,
            timestamp=snapshot_time,
            overall_win_rate=overall_win_rate,
            overall_mae=overall_mae,
            total_events_scored=total_predictions,
            metrics_json=metrics_json,
        )
        
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        
        logger.info(
            f"Created PredictionSnapshot from PredictionMetrics: model={model_version}, "
            f"win_rate={overall_win_rate:.2f}%, events={total_predictions}"
        )
        
        return snapshot
    
    # Fall back to calculating from EventOutcome data
    logger.info(
        f"No PredictionMetrics found, attempting to calculate from EventOutcome data: "
        f"model={model_version}"
    )
    
    # Query all outcomes for this model version
    query = db.query(Event, EventOutcome).join(
        EventOutcome,
        EventOutcome.event_id == Event.id
    ).filter(
        Event.ml_model_version == model_version
    )
    
    results = query.all()
    
    if not results:
        logger.warning(f"No EventOutcome data found for model={model_version}")
        # Create empty snapshot
        snapshot = PredictionSnapshot(
            model_version=model_version,
            timestamp=snapshot_time,
            overall_win_rate=0.0,
            overall_mae=0.0,
            total_events_scored=0,
            metrics_json={},
        )
        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)
        return snapshot
    
    # Calculate overall metrics
    predicted_returns = []
    actual_returns = []
    correct_directions = []
    
    metrics_by_horizon = {}
    
    for event, outcome in results:
        # Predicted return
        predicted_return = 0.0
        if event.direction == "up":
            predicted_return = event.impact_score / 10.0
        elif event.direction == "down":
            predicted_return = -event.impact_score / 10.0
        
        predicted_returns.append(predicted_return)
        actual_returns.append(outcome.return_pct)
        
        # Direction correctness
        is_correct = outcome.direction_correct if outcome.direction_correct is not None else False
        correct_directions.append(is_correct)
        
        # Track by horizon
        horizon = outcome.horizon
        if horizon not in metrics_by_horizon:
            metrics_by_horizon[horizon] = {
                "predicted": [],
                "actual": [],
                "correct": [],
            }
        metrics_by_horizon[horizon]["predicted"].append(predicted_return)
        metrics_by_horizon[horizon]["actual"].append(outcome.return_pct)
        metrics_by_horizon[horizon]["correct"].append(is_correct)
    
    # Overall metrics
    total_events_scored = len(results)
    overall_win_rate = (sum(correct_directions) / total_events_scored * 100) if total_events_scored > 0 else 0.0
    
    errors = [abs(pred - actual) for pred, actual in zip(predicted_returns, actual_returns)]
    overall_mae = float(np.mean(errors)) if errors else 0.0
    
    # Build detailed metrics JSON
    metrics_json = {
        "by_horizon": {},
        "timestamp": snapshot_time.isoformat(),
        "total_events": total_events_scored,
    }
    
    for horizon, data in metrics_by_horizon.items():
        horizon_win_rate = (sum(data["correct"]) / len(data["correct"]) * 100) if data["correct"] else 0.0
        horizon_errors = [abs(p - a) for p, a in zip(data["predicted"], data["actual"])]
        horizon_mae = float(np.mean(horizon_errors)) if horizon_errors else 0.0
        
        metrics_json["by_horizon"][horizon] = {
            "win_rate": horizon_win_rate,
            "mae": horizon_mae,
            "count": len(data["correct"]),
        }
    
    # Create snapshot
    snapshot = PredictionSnapshot(
        model_version=model_version,
        timestamp=snapshot_time,
        overall_win_rate=overall_win_rate,
        overall_mae=overall_mae,
        total_events_scored=total_events_scored,
        metrics_json=metrics_json,
    )
    
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    
    logger.info(
        f"Created PredictionSnapshot: model={model_version}, "
        f"win_rate={overall_win_rate:.2f}%, events={total_events_scored}"
    )
    
    return snapshot


def calculate_all_metrics(
    db: Session,
    model_version: str,
    horizons: Optional[List[str]] = None,
    event_types: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Retrieve all prediction metrics for a model across multiple dimensions.
    
    First attempts to retrieve existing metrics from PredictionMetrics table.
    Falls back to calculating from EventOutcome data if no existing metrics found.
    
    Args:
        db: Database session
        model_version: Model version to evaluate
        horizons: List of horizons to evaluate (defaults to ["1d", "5d", "7d", "30d"])
        event_types: List of event types to evaluate (defaults to all unique types)
    
    Returns:
        Dictionary with summary of calculations
    """
    if horizons is None:
        horizons = ["1d", "5d", "7d", "30d"]
    
    # Get unique event types if not provided
    if event_types is None:
        # First try to get event types from PredictionMetrics
        metrics_event_types_query = db.query(PredictionMetrics.event_type).filter(
            and_(
                PredictionMetrics.model_version == model_version,
                PredictionMetrics.event_type != "all"
            )
        ).distinct()
        event_types = [row[0] for row in metrics_event_types_query.all()]
        
        # If no event types in PredictionMetrics, try Event table
        if not event_types:
            event_types_query = db.query(Event.event_type).filter(
                Event.ml_model_version == model_version
            ).distinct()
            event_types = [row[0] for row in event_types_query.all()]
    
    calculation_date = date.today()
    results = {
        "model_version": model_version,
        "calculation_date": calculation_date.isoformat(),
        "metrics_calculated": [],
    }
    
    # Calculate metrics for each combination
    for horizon in horizons:
        # Overall metrics (all event types)
        metric = calculate_prediction_metrics(
            db=db,
            model_version=model_version,
            event_type=None,
            horizon=horizon,
            calculation_date=calculation_date,
        )
        if metric:
            results["metrics_calculated"].append({
                "event_type": "all",
                "horizon": horizon,
                "win_rate": metric.win_rate,
                "mae": metric.mae,
            })
        
        # Per event type
        for event_type in event_types:
            metric = calculate_prediction_metrics(
                db=db,
                model_version=model_version,
                event_type=event_type,
                horizon=horizon,
                calculation_date=calculation_date,
            )
            if metric:
                results["metrics_calculated"].append({
                    "event_type": event_type,
                    "horizon": horizon,
                    "win_rate": metric.win_rate,
                    "mae": metric.mae,
                })
    
    # Create snapshot
    snapshot = create_snapshot(db=db, model_version=model_version)
    results["snapshot"] = {
        "overall_win_rate": snapshot.overall_win_rate,
        "overall_mae": snapshot.overall_mae,
        "total_events": snapshot.total_events_scored,
    }
    
    logger.info(f"Completed metric calculation for model={model_version}")
    
    return results
