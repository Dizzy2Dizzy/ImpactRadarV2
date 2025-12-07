"""
Quantile Regression using XGBoost for probabilistic forecasting.

Trains multiple models at different quantiles to produce prediction intervals
instead of point estimates, enabling uncertainty quantification.
"""

import os
import joblib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, NamedTuple

import numpy as np
import pandas as pd
import xgboost as xgb

from releaseradar.ml.schemas import EventFeatures, TrainingData
from releaseradar.log_config import logger


class QuantilePrediction(NamedTuple):
    """Result of quantile regression prediction."""
    lower: float  # 10th percentile
    q25: float  # 25th percentile
    median: float  # 50th percentile (point estimate)
    q75: float  # 75th percentile
    upper: float  # 90th percentile
    confidence_width: float  # upper - lower (interval width)


HORIZON_QUANTILE_PARAMS = {
    "1d": {
        "n_estimators": 100,
        "max_depth": 4,
        "learning_rate": 0.05,
        "reg_alpha": 1.0,
        "reg_lambda": 2.0,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
    },
    "5d": {
        "n_estimators": 100,
        "max_depth": 5,
        "learning_rate": 0.03,
        "reg_alpha": 1.5,
        "reg_lambda": 2.5,
        "min_child_weight": 7,
        "subsample": 0.75,
        "colsample_bytree": 0.75,
    },
}


class QuantileRegressor:
    """
    XGBoost-based quantile regressor for probabilistic impact prediction.
    
    Trains separate models for each quantile [0.1, 0.25, 0.5, 0.75, 0.9]
    to produce prediction intervals with proper uncertainty quantification.
    
    Uses XGBoost's `reg:quantileerror` objective for pinball loss optimization.
    """
    
    MODEL_DIR = "backend/models/probabilistic"
    QUANTILES = [0.1, 0.25, 0.5, 0.75, 0.9]
    
    def __init__(self, horizon: str = "1d"):
        """
        Initialize quantile regressor.
        
        Args:
            horizon: Time horizon for predictions ("1d" or "5d")
        """
        if horizon not in ["1d", "5d"]:
            logger.warning(f"Unsupported horizon {horizon}, defaulting to 1d")
            horizon = "1d"
        
        self.horizon = horizon
        self.models: Dict[float, xgb.XGBRegressor] = {}
        self.feature_names: Optional[List[str]] = None
        self.trained_at: Optional[datetime] = None
        
        Path(self.MODEL_DIR).mkdir(parents=True, exist_ok=True)
    
    def _prepare_data(
        self,
        features: List[EventFeatures],
        outcomes: List[float]
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """Convert features and outcomes to training format."""
        if len(features) != len(outcomes):
            raise ValueError(f"Features ({len(features)}) and outcomes ({len(outcomes)}) length mismatch")
        
        feature_dicts = [f.to_vector() for f in features]
        X_df = pd.DataFrame(feature_dicts)
        y_array = np.array(outcomes)
        
        return X_df, y_array
    
    def train(
        self,
        training_data: TrainingData,
        test_size: float = 0.2,
        random_state: int = 42
    ) -> Dict[float, float]:
        """
        Train quantile regression models for all quantiles.
        
        Args:
            training_data: TrainingData with features and outcomes
            test_size: Fraction for validation
            random_state: Random seed
            
        Returns:
            Dict mapping quantile to pinball loss on validation set
        """
        X_df, y_array = self._prepare_data(
            training_data.features,
            training_data.outcomes
        )
        
        self.feature_names = list(X_df.columns)
        
        from sklearn.model_selection import train_test_split
        X_train, X_val, y_train, y_val = train_test_split(
            X_df, y_array,
            test_size=test_size,
            random_state=random_state
        )
        
        logger.info(f"Training quantile models for horizon {self.horizon} on {len(X_train)} samples")
        
        horizon_params = HORIZON_QUANTILE_PARAMS.get(self.horizon, HORIZON_QUANTILE_PARAMS["1d"])
        losses = {}
        
        for quantile in self.QUANTILES:
            logger.debug(f"Training model for quantile {quantile}")
            
            model = xgb.XGBRegressor(
                objective="reg:quantileerror",
                quantile_alpha=quantile,
                n_estimators=horizon_params["n_estimators"],
                max_depth=horizon_params["max_depth"],
                learning_rate=horizon_params["learning_rate"],
                reg_alpha=horizon_params["reg_alpha"],
                reg_lambda=horizon_params["reg_lambda"],
                min_child_weight=horizon_params["min_child_weight"],
                subsample=horizon_params["subsample"],
                colsample_bytree=horizon_params["colsample_bytree"],
                random_state=random_state,
                n_jobs=-1,
            )
            
            model.fit(X_train, y_train, verbose=False)
            self.models[quantile] = model
            
            y_pred = model.predict(X_val)
            loss = self._pinball_loss(y_val, y_pred, quantile)
            losses[quantile] = loss
            
            logger.debug(f"Quantile {quantile}: pinball loss = {loss:.6f}")
        
        self.trained_at = datetime.utcnow()
        
        coverage = self._calculate_coverage(X_val, y_val)
        logger.info(f"Quantile models trained. 80% interval coverage: {coverage:.2%}")
        
        return losses
    
    def _pinball_loss(self, y_true: np.ndarray, y_pred: np.ndarray, quantile: float) -> float:
        """Calculate pinball (quantile) loss."""
        errors = y_true - y_pred
        return np.mean(np.maximum(quantile * errors, (quantile - 1) * errors))
    
    def _calculate_coverage(self, X: pd.DataFrame, y: np.ndarray) -> float:
        """Calculate empirical coverage of 80% prediction interval (q10 to q90)."""
        if 0.1 not in self.models or 0.9 not in self.models:
            return 0.0
        
        lower = self.models[0.1].predict(X)
        upper = self.models[0.9].predict(X)
        
        in_interval = (y >= lower) & (y <= upper)
        return np.mean(in_interval)
    
    def predict_intervals(self, features: List[EventFeatures]) -> List[QuantilePrediction]:
        """
        Predict quantile intervals for multiple events.
        
        Args:
            features: List of EventFeatures to predict
            
        Returns:
            List of QuantilePrediction with (lower, q25, median, q75, upper, width)
        """
        if not self.models:
            raise ValueError("No models trained. Call train() first.")
        
        X_df, _ = self._prepare_data(features, [0.0] * len(features))
        
        if self.feature_names:
            missing = set(self.feature_names) - set(X_df.columns)
            for feat in missing:
                X_df[feat] = 0.0
            X_df = X_df[self.feature_names]
        
        predictions = {}
        for quantile, model in self.models.items():
            predictions[quantile] = model.predict(X_df)
        
        results = []
        for i in range(len(features)):
            lower = predictions[0.1][i]
            q25 = predictions[0.25][i]
            median = predictions[0.5][i]
            q75 = predictions[0.75][i]
            upper = predictions[0.9][i]
            
            if lower > upper:
                lower, upper = upper, lower
            if q25 > q75:
                q25, q75 = q75, q25
            
            results.append(QuantilePrediction(
                lower=float(lower),
                q25=float(q25),
                median=float(median),
                q75=float(q75),
                upper=float(upper),
                confidence_width=float(upper - lower)
            ))
        
        return results
    
    def predict_single(self, features: EventFeatures) -> QuantilePrediction:
        """Predict intervals for a single event."""
        results = self.predict_intervals([features])
        return results[0]
    
    def save(self, version: str) -> str:
        """
        Save all quantile models to disk.
        
        Args:
            version: Model version string
            
        Returns:
            Path to saved model directory
        """
        if not self.models:
            raise ValueError("No models to save. Train first.")
        
        save_dir = os.path.join(self.MODEL_DIR, f"quantile_{self.horizon}_{version}")
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        for quantile, model in self.models.items():
            model_path = os.path.join(save_dir, f"q{int(quantile*100)}.joblib")
            joblib.dump(model, model_path)
        
        metadata = {
            "horizon": self.horizon,
            "quantiles": self.QUANTILES,
            "feature_names": self.feature_names,
            "trained_at": self.trained_at.isoformat() if self.trained_at else None,
            "version": version,
        }
        metadata_path = os.path.join(save_dir, "metadata.joblib")
        joblib.dump(metadata, metadata_path)
        
        logger.info(f"Quantile models saved to {save_dir}")
        return save_dir
    
    def load(self, model_dir: str) -> None:
        """
        Load quantile models from disk.
        
        Args:
            model_dir: Directory containing saved models
        """
        if not os.path.exists(model_dir):
            raise FileNotFoundError(f"Model directory not found: {model_dir}")
        
        metadata_path = os.path.join(model_dir, "metadata.joblib")
        if os.path.exists(metadata_path):
            metadata = joblib.load(metadata_path)
            self.horizon = metadata.get("horizon", self.horizon)
            self.feature_names = metadata.get("feature_names")
            trained_at_str = metadata.get("trained_at")
            if trained_at_str:
                self.trained_at = datetime.fromisoformat(trained_at_str)
        
        self.models = {}
        for quantile in self.QUANTILES:
            model_path = os.path.join(model_dir, f"q{int(quantile*100)}.joblib")
            if os.path.exists(model_path):
                self.models[quantile] = joblib.load(model_path)
                logger.debug(f"Loaded model for quantile {quantile}")
        
        if not self.models:
            raise ValueError(f"No quantile models found in {model_dir}")
        
        logger.info(f"Loaded {len(self.models)} quantile models from {model_dir}")
    
    def get_feature_importance(self, quantile: float = 0.5) -> Dict[str, float]:
        """Get feature importance from the median (q50) model."""
        if quantile not in self.models:
            return {}
        
        model = self.models[quantile]
        try:
            importance = model.feature_importances_
            if self.feature_names and len(self.feature_names) == len(importance):
                return dict(zip(self.feature_names, importance.tolist()))
            return {f"feature_{i}": float(v) for i, v in enumerate(importance)}
        except Exception as e:
            logger.warning(f"Failed to get feature importance: {e}")
            return {}
