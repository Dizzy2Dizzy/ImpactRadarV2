"""
Calculate REAL prediction accuracy metrics from event_outcomes table.

This script calculates genuine metrics from:
- event_outcomes.direction_correct (boolean - properly calculated)
- event_outcomes.return_pct (actual returns by horizon)
- events.ml_model_version (actual model versions)

The event_outcomes table is the CANONICAL source of truth for accuracy data.

Run with: python backend/scripts/calculate_real_accuracy.py
"""

import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from collections import defaultdict
import math

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
from releaseradar.db.models import (
    Event,
    EventOutcome,
    PredictionMetrics,
    PredictionSnapshot,
)
from releaseradar.db.session import get_db


def calculate_sharpe_ratio(returns: list, risk_free_rate: float = 0.0) -> float:
    """Calculate Sharpe ratio from a list of returns."""
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


def calculate_real_metrics_from_outcomes(session: Session, verbose: bool = True):
    """
    Calculate real prediction metrics from event_outcomes table.
    
    This is the CANONICAL source of truth for accuracy data.
    MAE/RMSE are calculated as prediction error (predicted return - actual return).
    """
    
    if verbose:
        print("=" * 60)
        print("CALCULATING REAL PREDICTION ACCURACY FROM EVENT_OUTCOMES")
        print("=" * 60)
    
    outcomes = session.query(EventOutcome, Event).join(
        Event, EventOutcome.event_id == Event.id
    ).all()
    
    if verbose:
        print(f"\nFound {len(outcomes)} event outcomes")
    
    if not outcomes:
        print("ERROR: No event outcomes found!")
        return None
    
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
    
    return metrics_by_key


def populate_real_metrics(session: Session, metrics_by_key: dict, verbose: bool = True):
    """Clear synthetic data and populate with real metrics from event_outcomes."""
    
    if verbose:
        print("\n" + "=" * 60)
        print("POPULATING PREDICTION_METRICS WITH REAL DATA")
        print("=" * 60)
    
    session.query(PredictionMetrics).delete()
    session.commit()
    if verbose:
        print("Cleared existing prediction_metrics")
    
    today = date.today()
    metrics_created = 0
    
    for (model_version, event_type, horizon), data in metrics_by_key.items():
        if data['total'] == 0:
            continue
        
        win_rate = data['wins'] / data['total']
        
        errors = data['errors']
        mae = sum(errors) / len(errors) if errors else 0.0
        rmse = math.sqrt(sum(e**2 for e in errors) / len(errors)) if errors else 0.0
        
        sharpe = calculate_sharpe_ratio(data['returns'])
        
        avg_confidence = sum(data['confidences']) / len(data['confidences']) if data['confidences'] else 0.5
        
        high_conf_wr = data['high_conf_wins'] / data['high_conf_total'] if data['high_conf_total'] > 0 else None
        med_conf_wr = data['med_conf_wins'] / data['med_conf_total'] if data['med_conf_total'] > 0 else None
        low_conf_wr = data['low_conf_wins'] / data['low_conf_total'] if data['low_conf_total'] > 0 else None
        
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
            avg_confidence=round(avg_confidence, 4),
            high_conf_win_rate=round(high_conf_wr, 4) if high_conf_wr is not None else None,
            med_conf_win_rate=round(med_conf_wr, 4) if med_conf_wr is not None else None,
            low_conf_win_rate=round(low_conf_wr, 4) if low_conf_wr is not None else None,
        )
        session.add(metric)
        metrics_created += 1
    
    session.commit()
    
    if verbose:
        print(f"Created {metrics_created} real prediction metrics")
    
    return metrics_created


def populate_real_snapshots(session: Session, metrics_by_key: dict, verbose: bool = True):
    """Clear synthetic snapshots and populate with real aggregated data."""
    
    if verbose:
        print("\n" + "=" * 60)
        print("POPULATING PREDICTION_SNAPSHOTS WITH REAL DATA")
        print("=" * 60)
    
    session.query(PredictionSnapshot).delete()
    session.commit()
    if verbose:
        print("Cleared existing prediction_snapshots")
    
    model_aggregates = defaultdict(lambda: {
        'wins': 0,
        'total': 0,
        'errors': [],
        'returns': [],
    })
    
    for (model_version, event_type, horizon), data in metrics_by_key.items():
        if horizon == '1d':
            model_aggregates[model_version]['wins'] += data['wins']
            model_aggregates[model_version]['total'] += data['total']
            model_aggregates[model_version]['errors'].extend(data['errors'])
            model_aggregates[model_version]['returns'].extend(data['returns'])
    
    now = datetime.utcnow()
    snapshots_created = 0
    
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
                'data_source': 'canonical',
            }
        )
        session.add(snapshot)
        snapshots_created += 1
    
    session.commit()
    
    if verbose:
        print(f"Created {snapshots_created} real prediction snapshots")
    
    return snapshots_created


def print_summary(metrics_by_key: dict):
    """Print summary of real accuracy metrics."""
    
    print("\n" + "=" * 60)
    print("REAL ACCURACY SUMMARY BY MODEL VERSION & HORIZON")
    print("=" * 60)
    
    model_horizon_summary = defaultdict(lambda: defaultdict(lambda: {'wins': 0, 'total': 0, 'errors': []}))
    
    for (model_version, event_type, horizon), data in metrics_by_key.items():
        model_horizon_summary[model_version][horizon]['wins'] += data['wins']
        model_horizon_summary[model_version][horizon]['total'] += data['total']
        model_horizon_summary[model_version][horizon]['errors'].extend(data['errors'])
    
    for model_version in sorted(model_horizon_summary.keys()):
        print(f"\n{model_version}:")
        
        for horizon in ['1d', '7d', '30d']:
            data = model_horizon_summary[model_version].get(horizon)
            if not data or data['total'] == 0:
                continue
            
            win_rate = data['wins'] / data['total'] * 100
            mae = sum(data['errors']) / len(data['errors']) if data['errors'] else 0.0
            
            print(f"  {horizon}: {win_rate:.1f}% win rate ({data['wins']}/{data['total']}), MAE: {mae:.4f}")
    
    total_wins_1d = sum(d['1d']['wins'] for d in model_horizon_summary.values() if '1d' in d)
    total_preds_1d = sum(d['1d']['total'] for d in model_horizon_summary.values() if '1d' in d)
    
    if total_preds_1d > 0:
        overall_wr = total_wins_1d / total_preds_1d * 100
        print(f"\n{'='*60}")
        print(f"OVERALL (1d horizon): {overall_wr:.1f}% win rate ({total_wins_1d}/{total_preds_1d} predictions)")
        print(f"{'='*60}")


def main():
    """Main function to calculate and populate real metrics from event_outcomes."""
    print("\n" + "=" * 60)
    print("REAL ACCURACY CALCULATION SCRIPT")
    print("Using event_outcomes table (CANONICAL source)")
    print(f"Running at: {datetime.now().isoformat()}")
    print("=" * 60)
    
    session = get_db()
    
    try:
        metrics_by_key = calculate_real_metrics_from_outcomes(session)
        
        if not metrics_by_key:
            print("\nERROR: Could not calculate metrics - no data available")
            return
        
        print_summary(metrics_by_key)
        
        populate_real_metrics(session, metrics_by_key)
        populate_real_snapshots(session, metrics_by_key)
        
        print("\n" + "=" * 60)
        print("SUCCESS: Real accuracy metrics have been populated!")
        print("Data source: event_outcomes table (canonical)")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nERROR: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
