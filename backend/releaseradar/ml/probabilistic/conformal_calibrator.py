"""
Conformal Prediction Calibrator for valid prediction intervals.

Implements Split Conformal Prediction to ensure prediction intervals
have guaranteed coverage (e.g., 90% of actuals fall within 90% interval).
"""

import os
import joblib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple

import numpy as np

from releaseradar.ml.probabilistic.quantile_regressor import QuantileRegressor, QuantilePrediction
from releaseradar.ml.schemas import EventFeatures
from releaseradar.log_config import logger


class CalibratedInterval(NamedTuple):
    """Calibrated prediction interval with guaranteed coverage."""
    lower: float
    median: float
    upper: float
    coverage_level: float  # Nominal coverage (e.g., 0.9)
    calibration_adjustment: float  # Adjustment applied to raw intervals


class CalibrationMetrics(NamedTuple):
    """Metrics for calibration quality tracking."""
    empirical_coverage: float  # Actual coverage observed
    nominal_coverage: float  # Target coverage level
    coverage_error: float  # Difference (empirical - nominal)
    mean_interval_width: float
    median_interval_width: float
    n_samples: int
    calibrated_at: datetime


class ConformalCalibrator:
    """
    Split Conformal Prediction calibrator for valid prediction intervals.
    
    Ensures that prediction intervals from the quantile regressor have
    guaranteed coverage by computing nonconformity scores on a calibration
    set and adjusting intervals accordingly.
    
    Key concept: If we want 90% coverage, we find the 90th percentile of
    nonconformity scores and use it to widen/adjust intervals.
    """
    
    SAVE_DIR = "backend/models/calibration"
    
    def __init__(self, horizon: str = "1d"):
        """
        Initialize conformal calibrator.
        
        Args:
            horizon: Time horizon ("1d" or "5d")
        """
        self.horizon = horizon
        self.nonconformity_scores: Optional[np.ndarray] = None
        self.calibration_quantiles: Dict[float, float] = {}
        self.calibrated_at: Optional[datetime] = None
        self.n_calibration_samples: int = 0
        
        self._coverage_history: List[CalibrationMetrics] = []
        
        Path(self.SAVE_DIR).mkdir(parents=True, exist_ok=True)
    
    def calibrate(
        self,
        quantile_regressor: QuantileRegressor,
        calibration_features: List[EventFeatures],
        calibration_outcomes: List[float],
        coverage_levels: List[float] = [0.8, 0.9, 0.95]
    ) -> Dict[float, float]:
        """
        Calibrate prediction intervals using split conformal prediction.
        
        Computes nonconformity scores as max(y - upper, lower - y) for each
        calibration sample, then finds the quantile needed for each coverage level.
        
        Args:
            quantile_regressor: Trained QuantileRegressor
            calibration_features: Features for calibration set
            calibration_outcomes: True outcomes for calibration set
            coverage_levels: List of coverage levels to calibrate (e.g., [0.8, 0.9])
            
        Returns:
            Dict mapping coverage level to calibration adjustment
        """
        if len(calibration_features) < 20:
            logger.warning(f"Small calibration set ({len(calibration_features)} samples), results may be unreliable")
        
        predictions = quantile_regressor.predict_intervals(calibration_features)
        outcomes = np.array(calibration_outcomes)
        
        nonconformity_scores = []
        for i, pred in enumerate(predictions):
            y = outcomes[i]
            score = max(y - pred.upper, pred.lower - y)
            nonconformity_scores.append(score)
        
        self.nonconformity_scores = np.array(nonconformity_scores)
        self.n_calibration_samples = len(nonconformity_scores)
        
        self.calibration_quantiles = {}
        for level in coverage_levels:
            quantile_idx = np.ceil((self.n_calibration_samples + 1) * level) / self.n_calibration_samples
            quantile_idx = min(quantile_idx, 1.0)
            
            adjustment = np.quantile(self.nonconformity_scores, quantile_idx)
            self.calibration_quantiles[level] = float(adjustment)
            
            logger.debug(f"Coverage {level:.0%}: adjustment = {adjustment:.4f}")
        
        self.calibrated_at = datetime.utcnow()
        
        logger.info(f"Calibrated on {self.n_calibration_samples} samples for {len(coverage_levels)} coverage levels")
        
        return self.calibration_quantiles
    
    def calibrate_intervals(
        self,
        raw_predictions: List[QuantilePrediction],
        coverage_level: float = 0.9
    ) -> List[CalibratedInterval]:
        """
        Apply conformal calibration to raw quantile predictions.
        
        Widens intervals by the calibration adjustment to ensure
        guaranteed coverage at the specified level.
        
        Args:
            raw_predictions: List of QuantilePrediction from quantile regressor
            coverage_level: Desired coverage level (must have been calibrated)
            
        Returns:
            List of CalibratedInterval with adjusted bounds
        """
        if not self.calibration_quantiles:
            logger.warning("No calibration performed, returning raw predictions as calibrated")
            return [
                CalibratedInterval(
                    lower=p.lower,
                    median=p.median,
                    upper=p.upper,
                    coverage_level=coverage_level,
                    calibration_adjustment=0.0
                )
                for p in raw_predictions
            ]
        
        adjustment = self.calibration_quantiles.get(coverage_level)
        if adjustment is None:
            available = list(self.calibration_quantiles.keys())
            closest = min(available, key=lambda x: abs(x - coverage_level))
            adjustment = self.calibration_quantiles[closest]
            logger.warning(f"Coverage {coverage_level} not calibrated, using closest: {closest}")
        
        results = []
        for pred in raw_predictions:
            calibrated = CalibratedInterval(
                lower=pred.lower - adjustment,
                median=pred.median,
                upper=pred.upper + adjustment,
                coverage_level=coverage_level,
                calibration_adjustment=adjustment
            )
            results.append(calibrated)
        
        return results
    
    def evaluate_coverage(
        self,
        predictions: List[CalibratedInterval],
        actuals: List[float]
    ) -> CalibrationMetrics:
        """
        Evaluate empirical coverage of calibrated predictions.
        
        Args:
            predictions: List of CalibratedInterval
            actuals: List of actual outcomes
            
        Returns:
            CalibrationMetrics with coverage statistics
        """
        if len(predictions) != len(actuals):
            raise ValueError("Predictions and actuals must have same length")
        
        in_interval = []
        widths = []
        
        for pred, actual in zip(predictions, actuals):
            in_interval.append(pred.lower <= actual <= pred.upper)
            widths.append(pred.upper - pred.lower)
        
        empirical_coverage = np.mean(in_interval)
        nominal = predictions[0].coverage_level if predictions else 0.9
        
        metrics = CalibrationMetrics(
            empirical_coverage=float(empirical_coverage),
            nominal_coverage=nominal,
            coverage_error=float(empirical_coverage - nominal),
            mean_interval_width=float(np.mean(widths)),
            median_interval_width=float(np.median(widths)),
            n_samples=len(predictions),
            calibrated_at=datetime.utcnow()
        )
        
        self._coverage_history.append(metrics)
        
        if len(self._coverage_history) > 100:
            self._coverage_history = self._coverage_history[-100:]
        
        return metrics
    
    def get_coverage_trend(self) -> List[CalibrationMetrics]:
        """Get historical coverage metrics for trend analysis."""
        return self._coverage_history.copy()
    
    def is_well_calibrated(self, tolerance: float = 0.05) -> bool:
        """
        Check if recent predictions are well-calibrated.
        
        Args:
            tolerance: Acceptable deviation from nominal coverage
            
        Returns:
            True if empirical coverage is within tolerance of nominal
        """
        if not self._coverage_history:
            return True
        
        recent = self._coverage_history[-10:]
        avg_error = np.mean([abs(m.coverage_error) for m in recent])
        
        return avg_error <= tolerance
    
    def needs_recalibration(self, threshold: float = 0.10) -> bool:
        """
        Check if recalibration is needed based on coverage drift.
        
        Args:
            threshold: Coverage error threshold triggering recalibration
            
        Returns:
            True if coverage has drifted beyond threshold
        """
        if len(self._coverage_history) < 5:
            return False
        
        recent = self._coverage_history[-5:]
        avg_error = np.mean([m.coverage_error for m in recent])
        
        return abs(avg_error) > threshold
    
    def save(self, version: str) -> str:
        """Save calibration state to disk."""
        save_path = os.path.join(self.SAVE_DIR, f"conformal_{self.horizon}_{version}.joblib")
        
        state = {
            "horizon": self.horizon,
            "nonconformity_scores": self.nonconformity_scores,
            "calibration_quantiles": self.calibration_quantiles,
            "calibrated_at": self.calibrated_at.isoformat() if self.calibrated_at else None,
            "n_calibration_samples": self.n_calibration_samples,
            "coverage_history": [
                {
                    "empirical_coverage": m.empirical_coverage,
                    "nominal_coverage": m.nominal_coverage,
                    "coverage_error": m.coverage_error,
                    "mean_interval_width": m.mean_interval_width,
                    "median_interval_width": m.median_interval_width,
                    "n_samples": m.n_samples,
                    "calibrated_at": m.calibrated_at.isoformat(),
                }
                for m in self._coverage_history
            ],
            "version": version,
        }
        
        joblib.dump(state, save_path)
        logger.info(f"Calibration state saved to {save_path}")
        
        return save_path
    
    def load(self, path: str) -> None:
        """Load calibration state from disk."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Calibration file not found: {path}")
        
        state = joblib.load(path)
        
        self.horizon = state.get("horizon", self.horizon)
        self.nonconformity_scores = state.get("nonconformity_scores")
        self.calibration_quantiles = state.get("calibration_quantiles", {})
        self.n_calibration_samples = state.get("n_calibration_samples", 0)
        
        calibrated_at_str = state.get("calibrated_at")
        if calibrated_at_str:
            self.calibrated_at = datetime.fromisoformat(calibrated_at_str)
        
        self._coverage_history = []
        for item in state.get("coverage_history", []):
            self._coverage_history.append(CalibrationMetrics(
                empirical_coverage=item["empirical_coverage"],
                nominal_coverage=item["nominal_coverage"],
                coverage_error=item["coverage_error"],
                mean_interval_width=item["mean_interval_width"],
                median_interval_width=item["median_interval_width"],
                n_samples=item["n_samples"],
                calibrated_at=datetime.fromisoformat(item["calibrated_at"]),
            ))
        
        logger.info(f"Loaded calibration state from {path}")
