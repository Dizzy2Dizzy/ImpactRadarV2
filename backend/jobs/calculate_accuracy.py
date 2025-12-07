"""
Automated job to calculate prediction accuracy metrics.

Runs on schedule to calculate real accuracy from event_outcomes table,
updating the prediction_metrics and prediction_snapshots tables.

The event_outcomes table is the CANONICAL source of truth for accuracy data.

Can be run:
- Manually: python backend/jobs/calculate_accuracy.py
- Scheduled via APScheduler in the main application
"""

import sys
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import List, Dict, Any
from collections import defaultdict
import math
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent.parent))

from releaseradar.db.session import get_db_context
from releaseradar.db.models import (
    Event,
    EventOutcome,
    PredictionMetrics,
    PredictionSnapshot,
    ModelRegistry,
)


def calculate_sharpe_ratio(returns: list, risk_free_rate: float = 0.0) -> float:
    """Calculate annualized Sharpe ratio from returns."""
    if not returns or len(returns) < 2:
        return 0.0
    
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    std_dev = math.sqrt(variance) if variance > 0 else 0.0001
    
    sharpe = (mean_return - risk_free_rate) / std_dev if std_dev > 0 else 0.0
    annualized_sharpe = sharpe * math.sqrt(252)
    
    return max(-5.0, min(5.0, annualized_sharpe))


def get_display_model_version(ml_model_version: str) -> str:
    """Map internal ML model version to display version for dashboard."""
    if not ml_model_version:
        return "v1.0-deterministic"
    
    ml_lower = ml_model_version.lower()
    if 'xgboost' in ml_lower or 'neural' in ml_lower or 'ensemble' in ml_lower:
        return "v2.0-market-echo"
    elif 'hybrid' in ml_lower:
        return "v1.5-ml-hybrid"
    else:
        return "v1.5-ml-hybrid"


def normalize_event_type(event_type: str) -> str:
    """Normalize event type names for consistent grouping."""
    if not event_type:
        return "other"
    
    event_lower = event_type.lower()
    
    if 'earning' in event_lower:
        return 'earnings'
    elif 'fda' in event_lower or 'approval' in event_lower:
        return 'fda_approval'
    elif '8k' in event_lower or '8-k' in event_lower:
        return 'sec_8k'
    elif '10q' in event_lower or '10-q' in event_lower:
        return 'sec_10q'
    elif 'insider' in event_lower or 'form4' in event_lower or 'form 4' in event_lower:
        return 'insider_buy'
    elif 'ma' in event_lower or 'merger' in event_lower or 'acquisition' in event_lower:
        return 'ma'
    else:
        return event_type.lower().replace(' ', '_')[:20]


def normalize_horizon(horizon: str) -> str:
    """Normalize horizon strings to standard format."""
    h = horizon.lower().strip()
    if h in ('1d', '1_day', '1day'):
        return '1d'
    elif h in ('5d', '5_day', '5day', '7d', '7_day', '7day'):
        return '7d'
    elif h in ('20d', '20_day', '20day', '30d', '30_day', '30day'):
        return '30d'
    else:
        return h


def get_predicted_return(event) -> float:
    """Derive predicted return from event direction and impact score."""
    direction = (event.direction or '').lower()
    impact_score = event.impact_score or 0
    
    if direction in ('up', 'positive', 'bullish'):
        return impact_score / 10.0
    elif direction in ('down', 'negative', 'bearish'):
        return -impact_score / 10.0
    else:
        return 0.0


def calculate_metrics_from_outcomes(db) -> Dict[tuple, Dict[str, Any]]:
    """
    Calculate metrics from event_outcomes table (canonical source).
    
    MAE/RMSE are calculated as prediction error (predicted return - actual return).
    
    Returns:
        Dictionary keyed by (model_version, event_type, horizon) with metric data.
    """
    logger.info("Calculating metrics from event_outcomes table (canonical source)")
    
    outcomes = db.query(EventOutcome, Event).join(
        Event, EventOutcome.event_id == Event.id
    ).all()
    
    if not outcomes:
        logger.warning("No event outcomes found")
        return {}
    
    logger.info(f"Processing {len(outcomes)} event outcomes")
    
    metrics_by_key = defaultdict(lambda: {
        'wins': 0,
        'total': 0,
        'returns': [],
        'errors': [],
        'confidences': [],
        'high_conf_wins': 0,
        'high_conf_total': 0,
        'med_conf_wins': 0,
        'med_conf_total': 0,
        'low_conf_wins': 0,
        'low_conf_total': 0,
    })
    
    for outcome, event in outcomes:
        display_model = get_display_model_version(event.ml_model_version)
        event_type = normalize_event_type(event.event_type)
        horizon = normalize_horizon(outcome.horizon)
        
        is_win = outcome.direction_correct is True
        confidence = event.ml_confidence or event.confidence or 0.5
        actual_return = outcome.return_pct or 0.0
        predicted_return = get_predicted_return(event)
        
        prediction_error = abs(predicted_return - actual_return)
        
        key = (display_model, event_type, horizon)
        
        metrics_by_key[key]['total'] += 1
        if is_win:
            metrics_by_key[key]['wins'] += 1
        
        metrics_by_key[key]['returns'].append(actual_return)
        metrics_by_key[key]['errors'].append(prediction_error)
        metrics_by_key[key]['confidences'].append(confidence)
        
        if confidence > 0.7:
            metrics_by_key[key]['high_conf_total'] += 1
            if is_win:
                metrics_by_key[key]['high_conf_wins'] += 1
        elif confidence > 0.4:
            metrics_by_key[key]['med_conf_total'] += 1
            if is_win:
                metrics_by_key[key]['med_conf_wins'] += 1
        else:
            metrics_by_key[key]['low_conf_total'] += 1
            if is_win:
                metrics_by_key[key]['low_conf_wins'] += 1
    
    return dict(metrics_by_key)


def update_prediction_metrics(db, metrics_by_key: Dict[tuple, Dict[str, Any]]) -> int:
    """
    Update prediction_metrics table with calculated metrics.
    
    Args:
        db: Database session
        metrics_by_key: Metrics dictionary from calculate_metrics_from_outcomes
    
    Returns:
        Number of metrics records created/updated
    """
    logger.info("Updating prediction_metrics table")
    
    today = date.today()
    metrics_updated = 0
    
    for (model_version, event_type, horizon), data in metrics_by_key.items():
        if data['total'] == 0:
            continue
        
        win_rate = data['wins'] / data['total']
        
        errors = data['errors']
        mae = sum(errors) / len(errors) if errors else 0.0
        rmse = math.sqrt(sum(e**2 for e in errors) / len(errors)) if errors else 0.0
        
        sharpe = calculate_sharpe_ratio(data['returns'])
        
        avg_conf = sum(data['confidences']) / len(data['confidences']) if data['confidences'] else 0.5
        
        high_wr = data['high_conf_wins'] / data['high_conf_total'] if data['high_conf_total'] > 0 else None
        med_wr = data['med_conf_wins'] / data['med_conf_total'] if data['med_conf_total'] > 0 else None
        low_wr = data['low_conf_wins'] / data['low_conf_total'] if data['low_conf_total'] > 0 else None
        
        existing = db.query(PredictionMetrics).filter(
            PredictionMetrics.model_version == model_version,
            PredictionMetrics.event_type == event_type,
            PredictionMetrics.horizon == horizon,
            PredictionMetrics.date == today
        ).first()
        
        if existing:
            existing.total_predictions = data['total']
            existing.correct_direction = data['wins']
            existing.win_rate = round(win_rate, 4)
            existing.mae = round(mae, 4)
            existing.rmse = round(rmse, 4)
            existing.sharpe_ratio = round(sharpe, 4)
            existing.avg_confidence = round(avg_conf, 4)
            existing.high_conf_win_rate = round(high_wr, 4) if high_wr is not None else None
            existing.med_conf_win_rate = round(med_wr, 4) if med_wr is not None else None
            existing.low_conf_win_rate = round(low_wr, 4) if low_wr is not None else None
        else:
            metric = PredictionMetrics(
                model_version=model_version,
                event_type=event_type,
                horizon=horizon,
                date=today,
                total_predictions=data['total'],
                correct_direction=data['wins'],
                win_rate=round(win_rate, 4),
                mae=round(mae, 4),
                rmse=round(rmse, 4),
                sharpe_ratio=round(sharpe, 4),
                avg_confidence=round(avg_conf, 4),
                high_conf_win_rate=round(high_wr, 4) if high_wr is not None else None,
                med_conf_win_rate=round(med_wr, 4) if med_wr is not None else None,
                low_conf_win_rate=round(low_wr, 4) if low_wr is not None else None,
            )
            db.add(metric)
        
        metrics_updated += 1
    
    db.commit()
    logger.info(f"Updated {metrics_updated} prediction metrics")
    
    return metrics_updated


def update_prediction_snapshots(db, metrics_by_key: Dict[tuple, Dict[str, Any]]) -> int:
    """
    Update prediction_snapshots table with aggregated metrics.
    
    Args:
        db: Database session
        metrics_by_key: Metrics dictionary from calculate_metrics_from_outcomes
    
    Returns:
        Number of snapshots created/updated
    """
    logger.info("Updating prediction_snapshots table")
    
    model_aggregates = defaultdict(lambda: {
        'wins': 0,
        'total': 0,
        'errors': [],
    })
    
    for (model_version, event_type, horizon), data in metrics_by_key.items():
        if horizon == '1d':
            model_aggregates[model_version]['wins'] += data['wins']
            model_aggregates[model_version]['total'] += data['total']
            model_aggregates[model_version]['errors'].extend(data['errors'])
    
    now = datetime.utcnow()
    snapshots_updated = 0
    
    for model_version, data in model_aggregates.items():
        if data['total'] == 0:
            continue
        
        win_rate = data['wins'] / data['total']
        mae = sum(data['errors']) / len(data['errors']) if data['errors'] else 0.0
        
        snapshot = PredictionSnapshot(
            model_version=model_version,
            timestamp=now,
            overall_win_rate=round(win_rate, 4),
            overall_mae=round(mae, 4),
            total_events_scored=data['total'],
            metrics_json={
                'calculated_at': now.isoformat(),
                'source': 'event_outcomes',
                'wins': data['wins'],
                'total': data['total'],
                'job': 'calculate_accuracy',
            }
        )
        db.add(snapshot)
        snapshots_updated += 1
    
    db.commit()
    logger.info(f"Created {snapshots_updated} prediction snapshots")
    
    return snapshots_updated


def calculate_accuracy_job():
    """
    Main job function to calculate prediction accuracy from event_outcomes.
    
    This job:
    1. Reads outcomes from event_outcomes table (canonical source)
    2. Calculates win rates, MAE, RMSE, Sharpe by model/event_type/horizon
    3. Updates prediction_metrics table
    4. Creates new prediction_snapshots entries
    
    Safe to run multiple times - will update existing records for today.
    """
    logger.info("=" * 80)
    logger.info("PREDICTION ACCURACY CALCULATION JOB")
    logger.info(f"Started at: {datetime.utcnow().isoformat()}")
    logger.info("Data source: event_outcomes table (canonical)")
    logger.info("=" * 80)
    
    start_time = datetime.utcnow()
    
    try:
        with get_db_context() as db:
            metrics_by_key = calculate_metrics_from_outcomes(db)
            
            if not metrics_by_key:
                logger.warning("No metrics calculated - no event outcomes available")
                return
            
            total_outcomes = sum(d['total'] for d in metrics_by_key.values())
            total_wins = sum(d['wins'] for d in metrics_by_key.values())
            
            logger.info(
                f"Calculated metrics from {total_outcomes} outcomes, "
                f"overall {total_wins}/{total_outcomes} wins "
                f"({total_wins/total_outcomes*100:.1f}% win rate)"
            )
            
            metrics_count = update_prediction_metrics(db, metrics_by_key)
            snapshot_count = update_prediction_snapshots(db, metrics_by_key)
            
            elapsed = (datetime.utcnow() - start_time).total_seconds()
            
            logger.info("=" * 80)
            logger.info(
                f"Job completed successfully in {elapsed:.2f}s. "
                f"Updated {metrics_count} metrics, created {snapshot_count} snapshots."
            )
            logger.info("=" * 80)
    
    except Exception as e:
        logger.error(f"Accuracy calculation job failed: {e}", exc_info=True)
        raise


def main():
    """Entry point for manual or scheduled execution."""
    try:
        calculate_accuracy_job()
    except Exception as e:
        logger.error(f"Job failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
