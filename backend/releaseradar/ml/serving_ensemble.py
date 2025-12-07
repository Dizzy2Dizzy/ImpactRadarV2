"""
Ensemble Scoring Service for Market Echo Engine.

Dynamically combines predictions from neural network and XGBoost models,
emphasizing whichever model is more accurate based on rolling performance metrics.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple, List
from datetime import datetime, timedelta
import numpy as np

from sqlalchemy.orm import Session
from sqlalchemy import select, func

from releaseradar.db.models import Event, EventOutcome
from releaseradar.ml.serving import MLScoringService
from releaseradar.ml.models.neural import NeuralImpactModel, NeuralModelConfig, MultiHorizonNeuralModel, MultiHorizonNeuralConfig
from releaseradar.ml.features import FeatureExtractor
from releaseradar.log_config import logger


@dataclass
class ModelPerformance:
    """Performance metrics for a model."""
    model_name: str
    model_type: str
    horizon: str
    directional_accuracy: float
    mae: float
    rmse: float
    sharpe_ratio: Optional[float]
    n_samples: int
    last_updated: datetime
    weight: float = 0.5
    regime: Optional[str] = None  # Market regime during evaluation


@dataclass
class RegimePerformanceStats:
    """Performance statistics by market regime."""
    regime: str
    xgboost_accuracy: Optional[float]
    neural_accuracy: Optional[float]
    xgboost_samples: int
    neural_samples: int
    recommended_xgb_weight: float
    recommended_nn_weight: float


@dataclass
class EnsemblePrediction:
    """Combined prediction from ensemble."""
    ml_adjusted_score: int
    predicted_return: float
    confidence: float
    
    xgboost_prediction: Optional[float]
    xgboost_weight: float
    xgboost_confidence: Optional[float]
    
    neural_prediction: Optional[float]
    neural_weight: float
    neural_confidence: Optional[float]
    
    primary_model: str
    model_source: str = "ensemble"
    
    def to_dict(self) -> Dict:
        return {
            "ml_adjusted_score": self.ml_adjusted_score,
            "predicted_return": round(self.predicted_return, 4),
            "confidence": round(self.confidence, 3),
            "xgboost_prediction": round(self.xgboost_prediction, 4) if self.xgboost_prediction else None,
            "xgboost_weight": round(self.xgboost_weight, 3),
            "neural_prediction": round(self.neural_prediction, 4) if self.neural_prediction else None,
            "neural_weight": round(self.neural_weight, 3),
            "primary_model": self.primary_model,
            "model_source": self.model_source
        }


class ModelPerformanceTracker:
    """
    Tracks rolling performance of ML models for ensemble weighting.
    
    Uses directional accuracy as primary metric for weight calculation.
    """
    
    LOOKBACK_DAYS = 30
    MIN_SAMPLES = 20
    
    def __init__(self, db: Session):
        self.db = db
        self._performance_cache: Dict[str, ModelPerformance] = {}
        self._last_cache_update: Optional[datetime] = None
        self._cache_ttl_minutes = 60
    
    def get_model_performance(
        self,
        model_name: str,
        horizon: str = "1d"
    ) -> Optional[ModelPerformance]:
        """Get cached or calculate performance for a model."""
        cache_key = f"{model_name}_{horizon}"
        
        if self._is_cache_valid(cache_key):
            return self._performance_cache.get(cache_key)
        
        performance = self._calculate_performance(model_name, horizon)
        if performance:
            self._performance_cache[cache_key] = performance
            self._last_cache_update = datetime.utcnow()
        
        return performance
    
    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cache is still valid."""
        if cache_key not in self._performance_cache:
            return False
        if self._last_cache_update is None:
            return False
        
        age = (datetime.utcnow() - self._last_cache_update).total_seconds() / 60
        return age < self._cache_ttl_minutes
    
    def _calculate_performance(
        self,
        model_name: str,
        horizon: str
    ) -> Optional[ModelPerformance]:
        """Calculate rolling performance metrics for a model."""
        cutoff = datetime.utcnow() - timedelta(days=self.LOOKBACK_DAYS)
        
        results = self.db.execute(
            select(Event, EventOutcome)
            .join(EventOutcome, Event.id == EventOutcome.event_id)
            .where(Event.ml_model_version.ilike(f"%{model_name}%"))
            .where(Event.ml_adjusted_score.isnot(None))
            .where(EventOutcome.horizon == horizon)
            .where(Event.date >= cutoff)
        ).all()
        
        if len(results) < self.MIN_SAMPLES:
            logger.debug(f"Insufficient samples for {model_name}: {len(results)}")
            return None
        
        predictions = []
        actuals = []
        
        for event, outcome in results:
            pred_return = (event.ml_adjusted_score - 50) / 800
            predictions.append(pred_return)
            actuals.append(outcome.return_pct / 100)
        
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        pred_signs = np.sign(predictions)
        actual_signs = np.sign(actuals)
        directional_accuracy = np.mean(pred_signs == actual_signs)
        
        mae = np.mean(np.abs(predictions - actuals))
        rmse = np.sqrt(np.mean((predictions - actuals) ** 2))
        
        sharpe = None
        if np.std(predictions) > 0:
            sharpe = np.mean(predictions) / np.std(predictions) * np.sqrt(252)
        
        base_weight = directional_accuracy
        
        return ModelPerformance(
            model_name=model_name,
            model_type="xgboost" if "xgboost" in model_name.lower() else "neural",
            horizon=horizon,
            directional_accuracy=directional_accuracy,
            mae=mae,
            rmse=rmse,
            sharpe_ratio=sharpe,
            n_samples=len(results),
            last_updated=datetime.utcnow(),
            weight=base_weight
        )
    
    def calculate_ensemble_weights(
        self,
        xgboost_perf: Optional[ModelPerformance],
        neural_perf: Optional[ModelPerformance],
        regime: Optional[str] = None
    ) -> Tuple[float, float]:
        """
        Calculate weights for ensemble based on performance and market regime.
        
        Args:
            xgboost_perf: XGBoost model performance
            neural_perf: Neural network performance
            regime: Current market regime ("bull", "bear", "neutral", "high_vol")
        
        Returns:
            Tuple of (xgboost_weight, neural_weight) that sum to 1.0
        """
        if xgboost_perf is None and neural_perf is None:
            return (0.5, 0.5)
        
        if xgboost_perf is None:
            return (0.0, 1.0)
        
        if neural_perf is None:
            return (1.0, 0.0)
        
        # Base scoring from performance metrics
        xgb_score = xgboost_perf.directional_accuracy * np.sqrt(xgboost_perf.n_samples / 100)
        nn_score = neural_perf.directional_accuracy * np.sqrt(neural_perf.n_samples / 100)
        
        # Apply regime-based adjustments
        # These adjustments are based on empirical observations:
        # - XGBoost tends to perform better in trending (bull/bear) markets
        # - Neural networks often handle high-volatility regimes better
        # - Both perform similarly in neutral markets
        regime_adjustments = {
            "bull": (1.1, 0.95),      # XGBoost +10%, NN -5%
            "bear": (1.15, 0.90),     # XGBoost +15%, NN -10% (bearish patterns clearer)
            "neutral": (1.0, 1.0),    # No adjustment
            "high_vol": (0.90, 1.15), # XGBoost -10%, NN +15% (NN captures nonlinear patterns)
        }
        
        if regime and regime in regime_adjustments:
            xgb_adj, nn_adj = regime_adjustments[regime]
            xgb_score *= xgb_adj
            nn_score *= nn_adj
        
        total = xgb_score + nn_score
        if total == 0:
            return (0.5, 0.5)
        
        xgb_weight = xgb_score / total
        nn_weight = nn_score / total
        
        # Apply floor and ceiling (minimum 10%, maximum 90% per model)
        xgb_weight = 0.1 + 0.8 * xgb_weight
        nn_weight = 0.1 + 0.8 * nn_weight
        
        total = xgb_weight + nn_weight
        return (xgb_weight / total, nn_weight / total)
    
    def get_regime_performance(self, horizon: str = "1d") -> Dict[str, RegimePerformanceStats]:
        """
        Get performance statistics broken down by market regime.
        
        Returns:
            Dict mapping regime names to performance stats
        """
        from releaseradar.ml.features import MarketRegimeDetector
        
        results = {}
        regimes = ["bull", "bear", "neutral", "high_vol"]
        
        for regime in regimes:
            # This would require historical regime tagging of events
            # For now, return default stats
            xgb_weight, nn_weight = self.calculate_ensemble_weights(
                ModelPerformance(
                    model_name="xgboost", model_type="xgboost", horizon=horizon,
                    directional_accuracy=0.55, mae=0.02, rmse=0.03, sharpe_ratio=1.0,
                    n_samples=100, last_updated=datetime.utcnow()
                ),
                ModelPerformance(
                    model_name="neural", model_type="neural", horizon=horizon,
                    directional_accuracy=0.55, mae=0.02, rmse=0.03, sharpe_ratio=1.0,
                    n_samples=100, last_updated=datetime.utcnow()
                ),
                regime=regime
            )
            
            results[regime] = RegimePerformanceStats(
                regime=regime,
                xgboost_accuracy=None,  # Would be populated from actual data
                neural_accuracy=None,
                xgboost_samples=0,
                neural_samples=0,
                recommended_xgb_weight=xgb_weight,
                recommended_nn_weight=nn_weight
            )
        
        return results


class EnsembleScoringService:
    """
    Combines predictions from neural network and XGBoost models.
    
    Features:
    - Dynamic weighting based on rolling accuracy
    - Fallback to single model if one is unavailable
    - Confidence calibration across models
    - Performance tracking and model selection
    """
    
    def __init__(self, db: Session):
        self.db = db
        self.xgboost_service = MLScoringService(db)
        self.feature_extractor = FeatureExtractor(db)
        self.performance_tracker = ModelPerformanceTracker(db)
        
        self.neural_model: Optional[NeuralImpactModel] = None
        self.multi_horizon_model: Optional[MultiHorizonNeuralModel] = None
        self._load_neural_models()
    
    def _load_neural_models(self):
        """Load trained neural models if available."""
        # Try to load multi-horizon model first (preferred)
        try:
            self.multi_horizon_model = MultiHorizonNeuralModel.load("impact_multi_horizon", "1.0.0")
            logger.info("Multi-horizon neural model loaded for ensemble")
        except Exception as e:
            logger.debug(f"Multi-horizon model not available: {e}")
            self.multi_horizon_model = None
        
        # Fallback to legacy single-horizon model
        try:
            self.neural_model = NeuralImpactModel.load("impact_neural", "1.0.0")
            logger.info("Legacy neural model loaded for ensemble")
        except Exception as e:
            logger.debug(f"Legacy neural model not available: {e}")
            self.neural_model = None
    
    def predict_single(
        self,
        event_id: int,
        horizon: str = "1d"
    ) -> Optional[EnsemblePrediction]:
        """
        Generate ensemble prediction for a single event.
        
        Args:
            event_id: Event ID to predict
            horizon: Prediction horizon
            
        Returns:
            EnsemblePrediction or None if prediction fails
        """
        features = self.feature_extractor.extract_features(event_id)
        if features is None:
            return None
        
        xgb_pred = self.xgboost_service.predict_single(
            event_id=event_id,
            horizon=horizon
        )
        
        xgb_return = None
        xgb_confidence = None
        if xgb_pred:
            xgb_return = (xgb_pred.ml_adjusted_score - 50) / 800
            xgb_confidence = xgb_pred.ml_confidence
        
        nn_return = None
        nn_confidence = None
        # Try multi-horizon model first, then fallback to legacy
        if self.multi_horizon_model is not None:
            try:
                feature_vector = np.array(list(features.to_vector().values()))
                prediction = self.multi_horizon_model.predict_full_horizon(feature_vector, horizon)
                nn_return = prediction.predicted_return
                nn_confidence = prediction.confidence
            except Exception as e:
                logger.warning(f"Multi-horizon neural prediction failed: {e}")
        elif self.neural_model is not None:
            try:
                feature_vector = np.array(list(features.to_vector().values()))
                nn_return, nn_confidence = self.neural_model.predict_single(feature_vector)
            except Exception as e:
                logger.warning(f"Neural prediction failed: {e}")
        
        xgb_perf = self.performance_tracker.get_model_performance("xgboost_impact", horizon)
        nn_perf = self.performance_tracker.get_model_performance("neural_impact", horizon)
        
        # Use regime-aware weighting if market regime is available
        current_regime = getattr(features, 'market_regime', None)
        xgb_weight, nn_weight = self.performance_tracker.calculate_ensemble_weights(
            xgb_perf, nn_perf, regime=current_regime
        )
        
        if xgb_return is not None and nn_return is not None:
            ensemble_return = xgb_weight * xgb_return + nn_weight * nn_return
            
            if xgb_confidence and nn_confidence:
                ensemble_confidence = xgb_weight * xgb_confidence + nn_weight * nn_confidence
            else:
                ensemble_confidence = xgb_confidence or nn_confidence or 0.5
            
            primary_model = "xgboost" if xgb_weight >= nn_weight else "neural"
            model_source = "ensemble"
            
        elif xgb_return is not None:
            ensemble_return = xgb_return
            ensemble_confidence = xgb_confidence or 0.5
            primary_model = "xgboost"
            model_source = "xgboost-only"
            xgb_weight, nn_weight = 1.0, 0.0
            
        elif nn_return is not None:
            ensemble_return = nn_return
            ensemble_confidence = nn_confidence or 0.5
            primary_model = "neural"
            model_source = "neural-only"
            xgb_weight, nn_weight = 0.0, 1.0
            
        else:
            return None
        
        ml_adjusted_score = int(np.clip(50 + ensemble_return * 800, 1, 100))
        
        return EnsemblePrediction(
            ml_adjusted_score=ml_adjusted_score,
            predicted_return=ensemble_return,
            confidence=ensemble_confidence,
            xgboost_prediction=xgb_return,
            xgboost_weight=xgb_weight,
            xgboost_confidence=xgb_confidence,
            neural_prediction=nn_return,
            neural_weight=nn_weight,
            neural_confidence=nn_confidence,
            primary_model=primary_model,
            model_source=model_source
        )
    
    def get_model_comparison(self, horizon: str = "1d") -> Dict:
        """
        Get comparison of model performances for dashboard.
        
        Returns:
            Dict with performance metrics for each model
        """
        xgb_perf = self.performance_tracker.get_model_performance("xgboost_impact", horizon)
        nn_perf = self.performance_tracker.get_model_performance("neural_impact", horizon)
        
        xgb_weight, nn_weight = self.performance_tracker.calculate_ensemble_weights(
            xgb_perf, nn_perf
        )
        
        return {
            "xgboost": {
                "available": xgb_perf is not None,
                "directional_accuracy": xgb_perf.directional_accuracy if xgb_perf else None,
                "mae": xgb_perf.mae if xgb_perf else None,
                "sharpe_ratio": xgb_perf.sharpe_ratio if xgb_perf else None,
                "n_samples": xgb_perf.n_samples if xgb_perf else 0,
                "weight": xgb_weight
            },
            "neural": {
                "available": nn_perf is not None,
                "directional_accuracy": nn_perf.directional_accuracy if nn_perf else None,
                "mae": nn_perf.mae if nn_perf else None,
                "sharpe_ratio": nn_perf.sharpe_ratio if nn_perf else None,
                "n_samples": nn_perf.n_samples if nn_perf else 0,
                "weight": nn_weight
            },
            "ensemble_mode": "both" if (xgb_perf and nn_perf) else (
                "xgboost" if xgb_perf else ("neural" if nn_perf else "none")
            ),
            "primary_model": "xgboost" if xgb_weight >= nn_weight else "neural"
        }
    
    def retrain_neural_model(
        self,
        lookback_days: int = 365,
        min_samples: int = 500
    ) -> Dict:
        """
        Retrain neural model on recent data.
        
        Returns:
            Training metrics
        """
        from releaseradar.ml.pipelines.extract_features import FeaturePipeline
        from releaseradar.db.models import ModelFeature
        
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        
        samples = self.db.execute(
            select(ModelFeature, EventOutcome)
            .join(EventOutcome, ModelFeature.event_id == EventOutcome.event_id)
            .where(ModelFeature.horizon == "1d")
            .where(ModelFeature.extracted_at >= cutoff)
        ).all()
        
        if len(samples) < min_samples:
            return {"error": f"Insufficient samples: {len(samples)} < {min_samples}"}
        
        X = []
        y = []
        
        for feature_record, outcome in samples:
            features = feature_record.features
            if features:
                X.append(list(features.values()))
                y.append(outcome.return_pct / 100)
        
        X = np.array(X)
        y = np.array(y)
        
        config = NeuralModelConfig(
            input_dim=X.shape[1],
            hidden_dims=[128, 64, 32],
            dropout_rate=0.3,
            epochs=100,
            early_stopping_patience=15
        )
        
        self.neural_model = NeuralImpactModel(config)
        metrics = self.neural_model.train(X, y, verbose=True)
        
        self.neural_model.save("impact_neural", "1.0.0")
        
        return {
            "status": "success",
            "samples_used": len(X),
            "metrics": metrics
        }
