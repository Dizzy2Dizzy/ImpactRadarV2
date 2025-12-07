"""
Drift monitoring module for ML model performance tracking.

Compares ML predictions vs actual outcomes to detect performance degradation.
Generates drift alerts when accuracy drops >5% or calibration error spikes.
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

import numpy as np
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from releaseradar.db.models import (
    Event, 
    EventOutcome, 
    ModelRegistry,
    ModelPerformanceSnapshot,
    DriftAlert,
)
from releaseradar.db.session import get_db_transaction
from releaseradar.log_config import logger


class DriftMonitor:
    """Monitors ML model drift by comparing predictions to actual outcomes.
    
    Computes drift statistics including MAE drift, direction accuracy by horizon,
    and calibration error. Tracks rolling window performance (7d, 30d, 90d) and
    detects when model performance degrades significantly (>5% accuracy drop).
    """
    
    HORIZONS = ["1d", "5d"]
    WINDOW_DAYS = [7, 30, 90]
    ACCURACY_DROP_THRESHOLD = 0.05
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._cached_baseline: Dict[str, Dict] = {}
    
    def compute_drift_statistics(
        self,
        model_id: int,
        horizon: str,
        window_days: int = 30,
        reference_date: Optional[date] = None
    ) -> Dict:
        """
        Compute drift statistics for a model within a rolling window.
        
        Args:
            model_id: Model registry ID
            horizon: Time horizon ("1d", "5d")
            window_days: Rolling window size in days
            reference_date: End date for window (defaults to today)
            
        Returns:
            Dict with drift metrics:
                - direction_accuracy: % of correct direction predictions
                - mae: Mean Absolute Error
                - rmse: Root Mean Squared Error
                - sample_count: Number of samples in window
                - calibration_error: Average calibration error
        """
        if reference_date is None:
            reference_date = date.today()
        
        window_start = reference_date - timedelta(days=window_days)
        
        model = self.db.execute(
            select(ModelRegistry)
            .where(ModelRegistry.id == model_id)
        ).scalar_one_or_none()
        
        if not model:
            logger.warning(f"Model {model_id} not found")
            return self._empty_metrics()
        
        model_name = model.name
        
        events_with_outcomes = self.db.execute(
            select(Event, EventOutcome)
            .join(EventOutcome, Event.id == EventOutcome.event_id)
            .where(Event.ml_model_version.like(f"%{model_name}%"))
            .where(Event.ml_adjusted_score.isnot(None))
            .where(EventOutcome.horizon == horizon)
            .where(Event.date >= window_start)
            .where(Event.date <= reference_date)
        ).all()
        
        if not events_with_outcomes:
            logger.debug(f"No data for model {model_id}, horizon {horizon}, window {window_days}d")
            return self._empty_metrics()
        
        predictions = []
        actuals = []
        direction_predictions = []
        direction_actuals = []
        
        for event, outcome in events_with_outcomes:
            pred_return = (event.ml_adjusted_score - 50) / 10.0
            predictions.append(pred_return)
            actuals.append(outcome.return_pct)
            
            pred_dir = 1 if pred_return > 0 else (-1 if pred_return < 0 else 0)
            actual_dir = 1 if outcome.return_pct > 0 else (-1 if outcome.return_pct < 0 else 0)
            direction_predictions.append(pred_dir)
            direction_actuals.append(actual_dir)
        
        predictions_arr = np.array(predictions)
        actuals_arr = np.array(actuals)
        
        errors = predictions_arr - actuals_arr
        mae = float(np.mean(np.abs(errors)))
        rmse = float(np.sqrt(np.mean(errors ** 2)))
        
        direction_correct = sum(
            1 for p, a in zip(direction_predictions, direction_actuals)
            if p == a
        )
        direction_accuracy = direction_correct / len(direction_predictions)
        
        calibration_error = self._compute_simple_calibration_error(
            predictions_arr, actuals_arr
        )
        
        return {
            "direction_accuracy": float(direction_accuracy),
            "mae": mae,
            "rmse": rmse,
            "sample_count": len(predictions),
            "calibration_error": calibration_error,
            "window_days": window_days,
            "reference_date": reference_date.isoformat(),
        }
    
    def _compute_simple_calibration_error(
        self, 
        predictions: np.ndarray, 
        actuals: np.ndarray,
        n_bins: int = 10
    ) -> float:
        """Compute simplified calibration error based on predicted magnitude vs actual."""
        if len(predictions) < n_bins:
            return 0.0
        
        sorted_idx = np.argsort(np.abs(predictions))
        sorted_preds = np.abs(predictions[sorted_idx])
        sorted_actuals = np.abs(actuals[sorted_idx])
        
        bin_size = len(predictions) // n_bins
        calibration_errors = []
        
        for i in range(n_bins):
            start = i * bin_size
            end = start + bin_size if i < n_bins - 1 else len(predictions)
            
            bin_pred_mean = np.mean(sorted_preds[start:end])
            bin_actual_mean = np.mean(sorted_actuals[start:end])
            
            calibration_errors.append(abs(bin_pred_mean - bin_actual_mean))
        
        return float(np.mean(calibration_errors))
    
    def _empty_metrics(self) -> Dict:
        """Return empty metrics dict."""
        return {
            "direction_accuracy": None,
            "mae": None,
            "rmse": None,
            "sample_count": 0,
            "calibration_error": None,
            "window_days": None,
            "reference_date": None,
        }
    
    def detect_drift(
        self,
        model_id: int,
        horizon: str,
        baseline_window_days: int = 30,
        current_window_days: int = 7,
        reference_date: Optional[date] = None
    ) -> Dict:
        """
        Detect if model performance has degraded significantly.
        
        Compares current (recent) performance against baseline (historical).
        Flags drift if accuracy drops >5%.
        
        Args:
            model_id: Model registry ID
            horizon: Time horizon ("1d", "5d")
            baseline_window_days: Days for baseline window (default 30)
            current_window_days: Days for current window (default 7)
            reference_date: End date (defaults to today)
            
        Returns:
            Dict with drift detection results:
                - has_drift: Boolean indicating if drift detected
                - drift_type: Type of drift if detected
                - severity: "low", "medium", "high"
                - baseline_metrics: Baseline performance
                - current_metrics: Current performance
                - delta: Difference in key metrics
        """
        if reference_date is None:
            reference_date = date.today()
        
        baseline_end = reference_date - timedelta(days=current_window_days)
        
        baseline_metrics = self.compute_drift_statistics(
            model_id=model_id,
            horizon=horizon,
            window_days=baseline_window_days,
            reference_date=baseline_end
        )
        
        current_metrics = self.compute_drift_statistics(
            model_id=model_id,
            horizon=horizon,
            window_days=current_window_days,
            reference_date=reference_date
        )
        
        if baseline_metrics["sample_count"] < 10 or current_metrics["sample_count"] < 5:
            return {
                "has_drift": False,
                "drift_type": None,
                "severity": None,
                "baseline_metrics": baseline_metrics,
                "current_metrics": current_metrics,
                "delta": None,
                "reason": "insufficient_data"
            }
        
        has_drift = False
        drift_type = None
        severity = "low"
        
        accuracy_delta = None
        if baseline_metrics["direction_accuracy"] and current_metrics["direction_accuracy"]:
            accuracy_delta = baseline_metrics["direction_accuracy"] - current_metrics["direction_accuracy"]
            
            if accuracy_delta > self.ACCURACY_DROP_THRESHOLD:
                has_drift = True
                drift_type = "accuracy_drop"
                
                if accuracy_delta > 0.15:
                    severity = "high"
                elif accuracy_delta > 0.10:
                    severity = "medium"
                else:
                    severity = "low"
        
        mae_delta = None
        if not has_drift and baseline_metrics["mae"] and current_metrics["mae"]:
            mae_delta = current_metrics["mae"] - baseline_metrics["mae"]
            mae_pct_change = mae_delta / baseline_metrics["mae"] if baseline_metrics["mae"] > 0 else 0
            
            if mae_pct_change > 0.25:
                has_drift = True
                drift_type = "mae_spike"
                severity = "medium" if mae_pct_change > 0.50 else "low"
        
        calibration_delta = None
        if not has_drift and baseline_metrics["calibration_error"] and current_metrics["calibration_error"]:
            calibration_delta = current_metrics["calibration_error"] - baseline_metrics["calibration_error"]
            
            if calibration_delta > 2.0:
                has_drift = True
                drift_type = "calibration_drift"
                severity = "medium" if calibration_delta > 5.0 else "low"
        
        if has_drift:
            logger.warning(
                f"Drift detected for model {model_id}/{horizon}: "
                f"type={drift_type}, severity={severity}, "
                f"accuracy_delta={accuracy_delta}, mae_delta={mae_delta}"
            )
        
        return {
            "has_drift": has_drift,
            "drift_type": drift_type,
            "severity": severity,
            "baseline_metrics": baseline_metrics,
            "current_metrics": current_metrics,
            "delta": {
                "accuracy": accuracy_delta,
                "mae": mae_delta,
                "calibration": calibration_delta,
            },
            "reason": None
        }
    
    def store_performance_snapshot(
        self,
        model_id: int,
        horizon: str,
        window_days: int,
        snapshot_date: Optional[date] = None
    ) -> Optional[ModelPerformanceSnapshot]:
        """
        Compute and store a performance snapshot in the database.
        
        Args:
            model_id: Model registry ID
            horizon: Time horizon
            window_days: Rolling window size
            snapshot_date: Date of snapshot (defaults to today)
            
        Returns:
            Created ModelPerformanceSnapshot or None
        """
        if snapshot_date is None:
            snapshot_date = date.today()
        
        metrics = self.compute_drift_statistics(
            model_id=model_id,
            horizon=horizon,
            window_days=window_days,
            reference_date=snapshot_date
        )
        
        if metrics["sample_count"] == 0:
            logger.debug(f"No samples for snapshot: model={model_id}, horizon={horizon}")
            return None
        
        stmt = insert(ModelPerformanceSnapshot).values(
            model_id=model_id,
            horizon=horizon,
            snapshot_date=snapshot_date,
            direction_accuracy=metrics["direction_accuracy"],
            mae=metrics["mae"],
            rmse=metrics["rmse"],
            calibration_error=metrics["calibration_error"],
            sample_count=metrics["sample_count"],
            window_days=window_days,
        )
        
        stmt = stmt.on_conflict_do_update(
            constraint="uq_model_perf_snapshot",
            set_={
                "direction_accuracy": stmt.excluded.direction_accuracy,
                "mae": stmt.excluded.mae,
                "rmse": stmt.excluded.rmse,
                "calibration_error": stmt.excluded.calibration_error,
                "sample_count": stmt.excluded.sample_count,
            }
        )
        
        result = self.db.execute(stmt)
        self.db.commit()
        
        snapshot = self.db.execute(
            select(ModelPerformanceSnapshot)
            .where(ModelPerformanceSnapshot.model_id == model_id)
            .where(ModelPerformanceSnapshot.horizon == horizon)
            .where(ModelPerformanceSnapshot.snapshot_date == snapshot_date)
            .where(ModelPerformanceSnapshot.window_days == window_days)
        ).scalar_one_or_none()
        
        logger.info(
            f"Stored performance snapshot: model={model_id}, horizon={horizon}, "
            f"window={window_days}d, accuracy={metrics['direction_accuracy']:.2%}"
        )
        
        return snapshot
    
    def create_drift_alert(
        self,
        model_id: int,
        horizon: str,
        alert_type: str,
        severity: str,
        metrics_before: Dict,
        metrics_after: Dict
    ) -> DriftAlert:
        """
        Create and store a drift alert.
        
        Args:
            model_id: Model registry ID
            horizon: Time horizon
            alert_type: Type of drift ("accuracy_drop", "calibration_drift", "mae_spike")
            severity: Alert severity ("low", "medium", "high")
            metrics_before: Baseline metrics
            metrics_after: Current metrics
            
        Returns:
            Created DriftAlert
        """
        alert = DriftAlert(
            model_id=model_id,
            horizon=horizon,
            alert_type=alert_type,
            severity=severity,
            metrics_before=metrics_before,
            metrics_after=metrics_after,
            detected_at=datetime.utcnow(),
        )
        
        self.db.add(alert)
        self.db.commit()
        self.db.refresh(alert)
        
        logger.warning(
            f"Drift alert created: model={model_id}, horizon={horizon}, "
            f"type={alert_type}, severity={severity}"
        )
        
        return alert
    
    def run_drift_check(
        self,
        model_id: Optional[int] = None,
        horizons: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Run complete drift check for models and horizons.
        
        If model_id is None, checks all active models.
        Creates alerts and snapshots as needed.
        
        Args:
            model_id: Optional specific model ID
            horizons: List of horizons to check (defaults to ["1d", "5d"])
            
        Returns:
            List of drift check results
        """
        horizons = horizons or self.HORIZONS
        results = []
        
        if model_id:
            models = [self.db.execute(
                select(ModelRegistry)
                .where(ModelRegistry.id == model_id)
            ).scalar_one_or_none()]
            models = [m for m in models if m]
        else:
            models = self.db.execute(
                select(ModelRegistry)
                .where(ModelRegistry.status == "active")
            ).scalars().all()
        
        if not models:
            logger.info("No active models to check for drift")
            return results
        
        for model in models:
            for horizon in horizons:
                for window_days in self.WINDOW_DAYS:
                    self.store_performance_snapshot(
                        model_id=model.id,
                        horizon=horizon,
                        window_days=window_days
                    )
                
                drift_result = self.detect_drift(
                    model_id=model.id,
                    horizon=horizon
                )
                
                if drift_result["has_drift"]:
                    self.create_drift_alert(
                        model_id=model.id,
                        horizon=horizon,
                        alert_type=drift_result["drift_type"],
                        severity=drift_result["severity"],
                        metrics_before=drift_result["baseline_metrics"],
                        metrics_after=drift_result["current_metrics"]
                    )
                
                results.append({
                    "model_id": model.id,
                    "model_name": model.name,
                    "horizon": horizon,
                    **drift_result
                })
        
        return results
    
    def compare_prediction_with_outcome(
        self,
        event: Event,
        outcome: EventOutcome
    ) -> Dict:
        """
        Compare a single prediction with its actual outcome.
        
        Args:
            event: Event with ML prediction
            outcome: Realized outcome
            
        Returns:
            Dict with comparison metrics:
                - prediction: Predicted return
                - actual: Actual return
                - error: Prediction error
                - direction_correct: Whether direction was correct
                - is_contrarian: True if prediction was significantly wrong
        """
        if event.ml_adjusted_score is None:
            return {
                "prediction": None,
                "actual": outcome.return_pct,
                "error": None,
                "direction_correct": None,
                "is_contrarian": False,
            }
        
        pred_return = (event.ml_adjusted_score - 50) / 10.0
        actual_return = outcome.return_pct
        error = pred_return - actual_return
        
        pred_dir = 1 if pred_return > 0 else (-1 if pred_return < 0 else 0)
        actual_dir = 1 if actual_return > 0 else (-1 if actual_return < 0 else 0)
        direction_correct = pred_dir == actual_dir
        
        is_contrarian = (
            abs(error) > 5.0 and
            not direction_correct and
            abs(actual_return) > 2.0
        )
        
        return {
            "prediction": pred_return,
            "actual": actual_return,
            "error": error,
            "direction_correct": direction_correct,
            "is_contrarian": is_contrarian,
        }
    
    def get_contrarian_events(
        self,
        horizon: str,
        lookback_days: int = 30,
        min_error: float = 5.0
    ) -> List[Dict]:
        """
        Find events where ML predictions were significantly wrong.
        
        These contrarian events are valuable for model improvement.
        
        Args:
            horizon: Time horizon
            lookback_days: Days to look back
            min_error: Minimum prediction error to flag
            
        Returns:
            List of contrarian events with details
        """
        cutoff = date.today() - timedelta(days=lookback_days)
        
        events_with_outcomes = self.db.execute(
            select(Event, EventOutcome)
            .join(EventOutcome, Event.id == EventOutcome.event_id)
            .where(Event.ml_adjusted_score.isnot(None))
            .where(EventOutcome.horizon == horizon)
            .where(Event.date >= cutoff)
        ).all()
        
        contrarian_events = []
        
        for event, outcome in events_with_outcomes:
            comparison = self.compare_prediction_with_outcome(event, outcome)
            
            if comparison["is_contrarian"] or (
                comparison["error"] is not None and 
                abs(comparison["error"]) > min_error
            ):
                contrarian_events.append({
                    "event_id": event.id,
                    "ticker": event.ticker,
                    "event_type": event.event_type,
                    "event_date": event.date.isoformat() if event.date else None,
                    "horizon": horizon,
                    **comparison
                })
        
        contrarian_events.sort(key=lambda x: abs(x.get("error", 0) or 0), reverse=True)
        
        logger.info(f"Found {len(contrarian_events)} contrarian events for {horizon}")
        
        return contrarian_events


def run_drift_monitoring():
    """Entry point for scheduled drift monitoring job."""
    logger.info("Starting drift monitoring job...")
    
    with get_db_transaction() as db:
        monitor = DriftMonitor(db=db)
        results = monitor.run_drift_check()
        
        drift_count = sum(1 for r in results if r.get("has_drift"))
        logger.info(f"Drift check complete: {len(results)} checks, {drift_count} drifts detected")
        
        return {
            "total_checks": len(results),
            "drifts_detected": drift_count,
            "results": results
        }


if __name__ == "__main__":
    run_drift_monitoring()
