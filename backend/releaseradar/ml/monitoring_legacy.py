"""
Drift detection and performance tracking for ML models.

Monitors model performance over time and detects feature/prediction drift.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional

import numpy as np
from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from releaseradar.db.models import EventOutcome, ModelFeature, ModelRegistry, Event
from releaseradar.log_config import logger


class ModelMonitor:
    """Monitors ML model performance and drift."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def calculate_psi(
        self,
        baseline_values: List[float],
        current_values: List[float],
        n_bins: int = 10
    ) -> float:
        """
        Calculate Population Stability Index (PSI) for drift detection.
        
        PSI measures distribution shift between baseline and current data.
        PSI < 0.1: No significant change
        PSI 0.1-0.2: Small change, monitor
        PSI > 0.2: Significant change, investigate/retrain
        
        Args:
            baseline_values: Historical feature values
            current_values: Recent feature values
            n_bins: Number of bins for histogram
            
        Returns:
            PSI value
        """
        if not baseline_values or not current_values:
            return 0.0
        
        # Create bins based on baseline distribution
        baseline_array = np.array(baseline_values)
        current_array = np.array(current_values)
        
        # Calculate percentile-based bins
        breakpoints = np.percentile(baseline_array, np.linspace(0, 100, n_bins + 1))
        
        # Ensure unique breakpoints
        breakpoints = np.unique(breakpoints)
        if len(breakpoints) < 2:
            return 0.0
        
        # Calculate distributions
        baseline_dist, _ = np.histogram(baseline_array, bins=breakpoints)
        current_dist, _ = np.histogram(current_array, bins=breakpoints)
        
        # Normalize to get percentages
        baseline_pct = baseline_dist / len(baseline_array)
        current_pct = current_dist / len(current_array)
        
        # Avoid division by zero
        baseline_pct = np.where(baseline_pct == 0, 0.0001, baseline_pct)
        current_pct = np.where(current_pct == 0, 0.0001, current_pct)
        
        # Calculate PSI
        psi = np.sum((current_pct - baseline_pct) * np.log(current_pct / baseline_pct))
        
        return float(psi)
    
    def check_feature_drift(
        self,
        feature_name: str,
        horizon: str = "1d",
        lookback_days: int = 30
    ) -> Dict[str, float]:
        """
        Check for drift in a specific feature.
        
        Args:
            feature_name: Name of feature to check
            horizon: Time horizon
            lookback_days: Days to look back for comparison
            
        Returns:
            Dict with PSI and drift status
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Get baseline (older) features
        baseline_features = self.db.execute(
            select(ModelFeature)
            .where(ModelFeature.horizon == horizon)
            .where(ModelFeature.extracted_at < cutoff_date)
            .order_by(ModelFeature.extracted_at.asc())
            .limit(1000)
        ).scalars().all()
        
        # Get current (recent) features
        current_features = self.db.execute(
            select(ModelFeature)
            .where(ModelFeature.horizon == horizon)
            .where(ModelFeature.extracted_at >= cutoff_date)
            .order_by(ModelFeature.extracted_at.desc())
            .limit(1000)
        ).scalars().all()
        
        if not baseline_features or not current_features:
            return {"psi": 0.0, "status": "insufficient_data"}
        
        # Extract feature values
        baseline_values = [
            f.features.get(feature_name, 0) 
            for f in baseline_features 
            if feature_name in f.features
        ]
        
        current_values = [
            f.features.get(feature_name, 0)
            for f in current_features
            if feature_name in f.features
        ]
        
        # Calculate PSI
        psi = self.calculate_psi(baseline_values, current_values)
        
        # Determine status
        if psi < 0.1:
            status = "stable"
        elif psi < 0.2:
            status = "minor_drift"
        else:
            status = "significant_drift"
        
        logger.info(f"Feature drift for {feature_name}: PSI={psi:.4f}, status={status}")
        
        return {
            "psi": psi,
            "status": status,
            "baseline_n": len(baseline_values),
            "current_n": len(current_values),
        }
    
    def calculate_recent_accuracy(
        self,
        model_name: str,
        horizon: str = "1d",
        lookback_days: int = 30
    ) -> Dict[str, float]:
        """
        Calculate recent model accuracy metrics.
        
        Args:
            model_name: Name of model to evaluate
            horizon: Time horizon
            lookback_days: Days to look back
            
        Returns:
            Dict with accuracy metrics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)
        
        # Get recent events with outcomes and ML predictions
        events_with_outcomes = self.db.execute(
            select(Event, EventOutcome)
            .join(EventOutcome, Event.id == EventOutcome.event_id)
            .where(Event.ml_model_version.like(f"{model_name}%"))
            .where(Event.ml_adjusted_score.isnot(None))
            .where(EventOutcome.horizon == horizon)
            .where(Event.date >= cutoff_date)
        ).all()
        
        if not events_with_outcomes:
            return {
                "n_samples": 0,
                "mae": None,
                "directional_accuracy": None,
                "status": "insufficient_data",
            }
        
        # Extract predictions and actuals
        predictions = []
        actuals = []
        
        for event, outcome in events_with_outcomes:
            # Convert ML score back to predicted return
            pred_return = (event.ml_adjusted_score - 50) / 800
            predictions.append(pred_return)
            actuals.append(outcome.return_pct / 100)  # Convert % to decimal
        
        # Calculate metrics
        predictions_arr = np.array(predictions)
        actuals_arr = np.array(actuals)
        
        mae = np.mean(np.abs(predictions_arr - actuals_arr))
        
        # Directional accuracy
        pred_signs = np.sign(predictions_arr)
        actual_signs = np.sign(actuals_arr)
        directional_accuracy = np.mean(pred_signs == actual_signs)
        
        logger.info(f"Recent accuracy for {model_name}: MAE={mae:.4f}, "
                   f"Directional Accuracy={directional_accuracy:.2%}")
        
        return {
            "n_samples": len(predictions),
            "mae": float(mae),
            "directional_accuracy": float(directional_accuracy),
            "status": "active",
        }
    
    def should_retrain(
        self,
        model_name: str,
        horizon: str = "1d",
        min_new_samples: int = 100,
        max_days_since_training: int = 30,
        accuracy_degradation_threshold: float = 0.1
    ) -> Dict[str, any]:
        """
        Determine if model should be retrained.
        
        Args:
            model_name: Name of model
            horizon: Time horizon
            min_new_samples: Minimum new labeled samples required
            max_days_since_training: Maximum days since last training
            accuracy_degradation_threshold: Max acceptable accuracy drop
            
        Returns:
            Dict with retraining recommendation
        """
        # Get active model
        active_model = self.db.execute(
            select(ModelRegistry)
            .where(ModelRegistry.name == model_name)
            .where(ModelRegistry.status == "active")
            .order_by(ModelRegistry.promoted_at.desc())
        ).scalar_one_or_none()
        
        if not active_model:
            return {
                "should_retrain": True,
                "reason": "no_active_model",
                "priority": "high",
            }
        
        reasons = []
        priority = "low"
        
        # Check 1: Time since last training
        days_since_training = (datetime.utcnow() - active_model.trained_at).days
        if days_since_training > max_days_since_training:
            reasons.append(f"stale_model ({days_since_training} days old)")
            priority = "medium"
        
        # Check 2: New labeled samples available
        new_samples_count = self.db.execute(
            select(EventOutcome)
            .where(EventOutcome.horizon == horizon)
            .where(EventOutcome.created_at > active_model.trained_at)
        ).scalars().all()
        
        if len(new_samples_count) >= min_new_samples:
            reasons.append(f"new_data_available ({len(new_samples_count)} samples)")
            if len(new_samples_count) >= min_new_samples * 2:
                priority = "high"
        
        # Check 3: Accuracy degradation
        recent_accuracy = self.calculate_recent_accuracy(model_name, horizon, lookback_days=7)
        if recent_accuracy["directional_accuracy"] is not None:
            baseline_accuracy = active_model.metrics.get("directional_accuracy", 0.5)
            accuracy_drop = baseline_accuracy - recent_accuracy["directional_accuracy"]
            
            if accuracy_drop > accuracy_degradation_threshold:
                reasons.append(f"accuracy_degradation ({accuracy_drop:.2%} drop)")
                priority = "high"
        
        # Decision
        should_retrain = len(reasons) > 0
        
        return {
            "should_retrain": should_retrain,
            "reasons": reasons,
            "priority": priority,
            "days_since_training": days_since_training,
            "new_samples": len(new_samples_count),
            "recent_accuracy": recent_accuracy,
        }
    
    def get_model_health(self, model_name: str, horizon: str = "1d") -> Dict[str, any]:
        """
        Get comprehensive model health report.
        
        Args:
            model_name: Name of model
            horizon: Time horizon
            
        Returns:
            Dict with health metrics
        """
        # Get active model
        active_model = self.db.execute(
            select(ModelRegistry)
            .where(ModelRegistry.name == model_name)
            .where(ModelRegistry.status == "active")
        ).scalar_one_or_none()
        
        if not active_model:
            return {"status": "no_active_model"}
        
        # Recent accuracy
        accuracy_metrics = self.calculate_recent_accuracy(model_name, horizon)
        
        # Feature drift for key features
        key_features = ["base_score", "context_score", "market_vol", "confidence"]
        drift_metrics = {}
        
        for feature in key_features:
            drift_metrics[feature] = self.check_feature_drift(feature, horizon)
        
        # Retraining recommendation
        retrain_recommendation = self.should_retrain(model_name, horizon)
        
        # Overall health status
        overall_status = "healthy"
        if retrain_recommendation["priority"] == "high":
            overall_status = "needs_attention"
        elif retrain_recommendation["priority"] == "medium":
            overall_status = "monitoring"
        
        return {
            "status": overall_status,
            "model_info": {
                "name": active_model.name,
                "version": active_model.version,
                "trained_at": active_model.trained_at.isoformat(),
                "promoted_at": active_model.promoted_at.isoformat() if active_model.promoted_at else None,
            },
            "accuracy_metrics": accuracy_metrics,
            "drift_metrics": drift_metrics,
            "retrain_recommendation": retrain_recommendation,
        }
