"""
Calibration service for ML model reliability tracking.

Tracks predicted probability vs actual frequency (calibration).
Computes Expected Calibration Error (ECE) for each horizon.
Supports reliability diagram data and stores calibration snapshots over time.
"""

from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import select, and_, func
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert

from releaseradar.db.models import (
    Event,
    EventOutcome,
    ModelRegistry,
    CalibrationSnapshot,
)
from releaseradar.db.session import get_db_transaction
from releaseradar.log_config import logger


class CalibrationService:
    """Service for computing and tracking model calibration.
    
    Calibration measures how well predicted probabilities match actual outcomes.
    A well-calibrated model with 70% confidence should be correct 70% of the time.
    """
    
    DEFAULT_N_BINS = 10
    HORIZONS = ["1d", "5d"]
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
    
    def compute_calibration_data(
        self,
        model_id: int,
        horizon: str,
        window_days: int = 30,
        n_bins: int = DEFAULT_N_BINS,
        reference_date: Optional[date] = None
    ) -> Dict:
        """
        Compute calibration metrics and bin data for reliability diagrams.
        
        Args:
            model_id: Model registry ID
            horizon: Time horizon ("1d", "5d")
            window_days: Rolling window for data
            n_bins: Number of bins for calibration analysis
            reference_date: End date for window
            
        Returns:
            Dict with:
                - ece: Expected Calibration Error
                - mce: Maximum Calibration Error
                - bin_data: List of bin statistics for reliability diagram
                - sample_count: Total samples
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
            return self._empty_calibration_data()
        
        model_name = model.name
        
        events_with_outcomes = self.db.execute(
            select(Event, EventOutcome)
            .join(EventOutcome, Event.id == EventOutcome.event_id)
            .where(Event.ml_model_version.like(f"%{model_name}%"))
            .where(Event.ml_confidence.isnot(None))
            .where(EventOutcome.horizon == horizon)
            .where(Event.date >= window_start)
            .where(Event.date <= reference_date)
        ).all()
        
        if not events_with_outcomes:
            logger.debug(f"No calibration data for model {model_id}, horizon {horizon}")
            return self._empty_calibration_data()
        
        confidences = []
        correct_predictions = []
        
        for event, outcome in events_with_outcomes:
            conf = event.ml_confidence
            confidences.append(conf)
            
            pred_return = (event.ml_adjusted_score - 50) / 10.0 if event.ml_adjusted_score else 0
            actual_return = outcome.return_pct
            
            pred_dir = 1 if pred_return > 0 else (-1 if pred_return < 0 else 0)
            actual_dir = 1 if actual_return > 0 else (-1 if actual_return < 0 else 0)
            
            correct_predictions.append(1 if pred_dir == actual_dir else 0)
        
        confidences = np.array(confidences)
        correct_predictions = np.array(correct_predictions)
        
        bin_data = self._compute_bin_data(confidences, correct_predictions, n_bins)
        ece = self._compute_ece(bin_data)
        mce = self._compute_mce(bin_data)
        
        return {
            "ece": ece,
            "mce": mce,
            "bin_data": bin_data,
            "sample_count": len(confidences),
            "window_days": window_days,
            "reference_date": reference_date.isoformat(),
        }
    
    def _compute_bin_data(
        self,
        confidences: np.ndarray,
        correct_predictions: np.ndarray,
        n_bins: int
    ) -> List[Dict]:
        """
        Compute bin statistics for reliability diagram.
        
        Each bin contains:
        - confidence_avg: Average predicted confidence in bin
        - accuracy: Actual accuracy in bin
        - count: Number of samples in bin
        - gap: Difference between confidence and accuracy
        """
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_data = []
        
        for i in range(n_bins):
            lower = bin_edges[i]
            upper = bin_edges[i + 1]
            
            mask = (confidences >= lower) & (confidences < upper)
            if i == n_bins - 1:
                mask = (confidences >= lower) & (confidences <= upper)
            
            count = np.sum(mask)
            
            if count > 0:
                bin_confidences = confidences[mask]
                bin_correct = correct_predictions[mask]
                
                confidence_avg = float(np.mean(bin_confidences))
                accuracy = float(np.mean(bin_correct))
                gap = confidence_avg - accuracy
            else:
                confidence_avg = (lower + upper) / 2
                accuracy = 0.0
                gap = 0.0
            
            bin_data.append({
                "bin_id": i,
                "lower": float(lower),
                "upper": float(upper),
                "confidence_avg": confidence_avg,
                "accuracy": accuracy,
                "count": int(count),
                "gap": float(gap),
            })
        
        return bin_data
    
    def _compute_ece(self, bin_data: List[Dict]) -> float:
        """
        Compute Expected Calibration Error (ECE).
        
        ECE = sum(|accuracy - confidence| * weight) for each bin
        where weight = count / total_count
        """
        total_count = sum(b["count"] for b in bin_data)
        
        if total_count == 0:
            return 0.0
        
        ece = 0.0
        for bin_info in bin_data:
            weight = bin_info["count"] / total_count
            ece += weight * abs(bin_info["gap"])
        
        return float(ece)
    
    def _compute_mce(self, bin_data: List[Dict]) -> float:
        """Compute Maximum Calibration Error (MCE)."""
        if not bin_data:
            return 0.0
        
        return float(max(abs(b["gap"]) for b in bin_data if b["count"] > 0) or 0.0)
    
    def _empty_calibration_data(self) -> Dict:
        """Return empty calibration data."""
        return {
            "ece": None,
            "mce": None,
            "bin_data": [],
            "sample_count": 0,
            "window_days": None,
            "reference_date": None,
        }
    
    def get_reliability_diagram_data(
        self,
        model_id: int,
        horizon: str,
        window_days: int = 30
    ) -> Dict:
        """
        Get data formatted for plotting a reliability diagram.
        
        Args:
            model_id: Model registry ID
            horizon: Time horizon
            window_days: Rolling window
            
        Returns:
            Dict with x (confidence), y (accuracy), and counts for plotting
        """
        cal_data = self.compute_calibration_data(
            model_id=model_id,
            horizon=horizon,
            window_days=window_days
        )
        
        if not cal_data["bin_data"]:
            return {
                "x": [],
                "y": [],
                "counts": [],
                "ece": None,
                "perfect_line": [[0, 0], [1, 1]],
            }
        
        x = [b["confidence_avg"] for b in cal_data["bin_data"]]
        y = [b["accuracy"] for b in cal_data["bin_data"]]
        counts = [b["count"] for b in cal_data["bin_data"]]
        
        return {
            "x": x,
            "y": y,
            "counts": counts,
            "ece": cal_data["ece"],
            "mce": cal_data["mce"],
            "perfect_line": [[0, 0], [1, 1]],
            "sample_count": cal_data["sample_count"],
        }
    
    def store_calibration_snapshot(
        self,
        model_id: int,
        horizon: str,
        window_days: int = 30,
        snapshot_date: Optional[date] = None
    ) -> Optional[CalibrationSnapshot]:
        """
        Compute and store a calibration snapshot in the database.
        
        Args:
            model_id: Model registry ID
            horizon: Time horizon
            window_days: Rolling window
            snapshot_date: Date of snapshot
            
        Returns:
            Created CalibrationSnapshot or None
        """
        if snapshot_date is None:
            snapshot_date = date.today()
        
        cal_data = self.compute_calibration_data(
            model_id=model_id,
            horizon=horizon,
            window_days=window_days,
            reference_date=snapshot_date
        )
        
        if cal_data["sample_count"] == 0:
            logger.debug(f"No samples for calibration snapshot: model={model_id}, horizon={horizon}")
            return None
        
        stmt = insert(CalibrationSnapshot).values(
            model_id=model_id,
            horizon=horizon,
            snapshot_date=snapshot_date,
            expected_calibration_error=cal_data["ece"],
            max_calibration_error=cal_data["mce"],
            bin_data=cal_data["bin_data"],
            sample_count=cal_data["sample_count"],
            window_days=window_days,
        )
        
        stmt = stmt.on_conflict_do_update(
            constraint="uq_calibration_snapshot",
            set_={
                "expected_calibration_error": stmt.excluded.expected_calibration_error,
                "max_calibration_error": stmt.excluded.max_calibration_error,
                "bin_data": stmt.excluded.bin_data,
                "sample_count": stmt.excluded.sample_count,
            }
        )
        
        self.db.execute(stmt)
        self.db.commit()
        
        snapshot = self.db.execute(
            select(CalibrationSnapshot)
            .where(CalibrationSnapshot.model_id == model_id)
            .where(CalibrationSnapshot.horizon == horizon)
            .where(CalibrationSnapshot.snapshot_date == snapshot_date)
        ).scalar_one_or_none()
        
        logger.info(
            f"Stored calibration snapshot: model={model_id}, horizon={horizon}, "
            f"ECE={cal_data['ece']:.4f}, samples={cal_data['sample_count']}"
        )
        
        return snapshot
    
    def get_calibration_trend(
        self,
        model_id: int,
        horizon: str,
        lookback_days: int = 90
    ) -> List[Dict]:
        """
        Get historical calibration trend from stored snapshots.
        
        Args:
            model_id: Model registry ID
            horizon: Time horizon
            lookback_days: Days of history to retrieve
            
        Returns:
            List of calibration snapshots with ECE over time
        """
        cutoff = date.today() - timedelta(days=lookback_days)
        
        snapshots = self.db.execute(
            select(CalibrationSnapshot)
            .where(CalibrationSnapshot.model_id == model_id)
            .where(CalibrationSnapshot.horizon == horizon)
            .where(CalibrationSnapshot.snapshot_date >= cutoff)
            .order_by(CalibrationSnapshot.snapshot_date)
        ).scalars().all()
        
        return [
            {
                "date": s.snapshot_date.isoformat(),
                "ece": s.expected_calibration_error,
                "mce": s.max_calibration_error,
                "sample_count": s.sample_count,
            }
            for s in snapshots
        ]
    
    def is_well_calibrated(
        self,
        model_id: int,
        horizon: str,
        ece_threshold: float = 0.1
    ) -> Tuple[bool, float]:
        """
        Check if model is well-calibrated.
        
        A model is considered well-calibrated if ECE < threshold.
        
        Args:
            model_id: Model registry ID
            horizon: Time horizon
            ece_threshold: Maximum acceptable ECE (default 0.1 = 10%)
            
        Returns:
            Tuple of (is_calibrated, ece_value)
        """
        cal_data = self.compute_calibration_data(
            model_id=model_id,
            horizon=horizon,
            window_days=30
        )
        
        if cal_data["ece"] is None:
            return False, 0.0
        
        is_calibrated = cal_data["ece"] < ece_threshold
        
        return is_calibrated, cal_data["ece"]
    
    def run_calibration_analysis(
        self,
        model_id: Optional[int] = None,
        horizons: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Run complete calibration analysis for models.
        
        Args:
            model_id: Optional specific model ID
            horizons: List of horizons to analyze
            
        Returns:
            List of calibration analysis results
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
        
        for model in models:
            for horizon in horizons:
                snapshot = self.store_calibration_snapshot(
                    model_id=model.id,
                    horizon=horizon
                )
                
                is_calibrated, ece = self.is_well_calibrated(
                    model_id=model.id,
                    horizon=horizon
                )
                
                results.append({
                    "model_id": model.id,
                    "model_name": model.name,
                    "horizon": horizon,
                    "ece": ece,
                    "is_calibrated": is_calibrated,
                    "snapshot_id": snapshot.id if snapshot else None,
                })
        
        return results


def run_calibration_tracking():
    """Entry point for scheduled calibration tracking job."""
    logger.info("Starting calibration tracking job...")
    
    with get_db_transaction() as db:
        service = CalibrationService(db=db)
        results = service.run_calibration_analysis()
        
        calibrated_count = sum(1 for r in results if r.get("is_calibrated"))
        logger.info(
            f"Calibration tracking complete: {len(results)} models, "
            f"{calibrated_count} well-calibrated"
        )
        
        return {
            "total_models": len(results),
            "calibrated_models": calibrated_count,
            "results": results
        }


if __name__ == "__main__":
    run_calibration_tracking()
