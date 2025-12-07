"""
Stacked Ensemble Model for Impact Radar ML System.

Combines XGBoost, LightGBM, and topology features using stacked generalization
with out-of-fold predictions to avoid overfitting.

Architecture:
    Level 0 (Base Learners):
        - XGBoost Regressor (strong baseline)
        - LightGBM Regressor (complementary to XGBoost)
        - Topology-weighted features (optional boost)
    
    Level 1 (Meta-Learner):
        - Ridge Regression for optimal blending
        
Uses K-fold cross-validation for generating out-of-fold predictions.
"""

import os
import joblib
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except (ImportError, OSError):
    lgb = None
    LIGHTGBM_AVAILABLE = False

from releaseradar.ml.schemas import TrainingData, ModelMetrics
from releaseradar.log_config import logger


@dataclass
class StackedEnsembleConfig:
    """Configuration for stacked ensemble."""
    n_folds: int = 5
    horizon: str = "1d"
    
    xgb_params: Dict[str, Any] = field(default_factory=lambda: {
        "n_estimators": 100,
        "max_depth": 4,
        "learning_rate": 0.05,
        "reg_alpha": 1.0,
        "reg_lambda": 2.0,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "gamma": 0.1,
        "random_state": 42,
        "n_jobs": -1,
    })
    
    lgb_params: Dict[str, Any] = field(default_factory=lambda: {
        "n_estimators": 100,
        "num_leaves": 31,
        "max_depth": 5,
        "learning_rate": 0.05,
        "reg_alpha": 1.0,
        "reg_lambda": 1.0,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "random_state": 42,
        "n_jobs": -1,
        "verbose": -1,
    })
    
    ridge_alpha: float = 1.0
    use_topology_boost: bool = True
    topology_weight: float = 0.1
    
    @classmethod
    def for_horizon(cls, horizon: str) -> "StackedEnsembleConfig":
        """Get optimized config for specific horizon."""
        if horizon == "1d":
            return cls(
                horizon="1d",
                xgb_params={
                    "n_estimators": 100,
                    "max_depth": 4,
                    "learning_rate": 0.05,
                    "reg_alpha": 1.0,
                    "reg_lambda": 2.0,
                    "min_child_weight": 5,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8,
                    "gamma": 0.1,
                    "random_state": 42,
                    "n_jobs": -1,
                },
                lgb_params={
                    "n_estimators": 100,
                    "num_leaves": 31,
                    "max_depth": 5,
                    "learning_rate": 0.05,
                    "reg_alpha": 1.0,
                    "reg_lambda": 1.0,
                    "subsample": 0.8,
                    "colsample_bytree": 0.8,
                    "random_state": 42,
                    "n_jobs": -1,
                    "verbose": -1,
                },
                ridge_alpha=1.0,
                topology_weight=0.1,
            )
        elif horizon == "5d":
            return cls(
                horizon="5d",
                xgb_params={
                    "n_estimators": 120,
                    "max_depth": 5,
                    "learning_rate": 0.03,
                    "reg_alpha": 1.5,
                    "reg_lambda": 2.5,
                    "min_child_weight": 7,
                    "subsample": 0.75,
                    "colsample_bytree": 0.75,
                    "gamma": 0.15,
                    "random_state": 42,
                    "n_jobs": -1,
                },
                lgb_params={
                    "n_estimators": 120,
                    "num_leaves": 25,
                    "max_depth": 6,
                    "learning_rate": 0.03,
                    "reg_alpha": 1.5,
                    "reg_lambda": 1.5,
                    "subsample": 0.75,
                    "colsample_bytree": 0.75,
                    "random_state": 42,
                    "n_jobs": -1,
                    "verbose": -1,
                },
                ridge_alpha=1.5,
                topology_weight=0.15,
            )
        else:
            return cls(horizon=horizon)


@dataclass
class StackedPrediction:
    """Prediction from stacked ensemble."""
    final_prediction: float
    xgb_prediction: float
    lgb_prediction: Optional[float]
    meta_weights: Dict[str, float]
    topology_boost: float = 0.0
    confidence: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "final_prediction": round(self.final_prediction, 6),
            "xgb_prediction": round(self.xgb_prediction, 6),
            "lgb_prediction": round(self.lgb_prediction, 6) if self.lgb_prediction else None,
            "topology_boost": round(self.topology_boost, 6),
            "confidence": round(self.confidence, 4),
            "meta_weights": {k: round(v, 4) for k, v in self.meta_weights.items()},
        }


@dataclass
class EnsembleMetrics:
    """Performance metrics for the stacked ensemble."""
    mae: float
    rmse: float
    r2: float
    directional_accuracy: float
    improvement_over_xgb: float
    improvement_over_lgb: Optional[float]
    n_train: int
    n_test: int
    xgb_weight: float
    lgb_weight: Optional[float]
    topology_impact: float
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    def to_model_metrics(self) -> ModelMetrics:
        """Convert to ModelMetrics for compatibility."""
        return ModelMetrics(
            mae=self.mae,
            rmse=self.rmse,
            r2=self.r2,
            directional_accuracy=self.directional_accuracy,
            sharpe_ratio=None,
            max_error=0.0,
            n_train=self.n_train,
            n_test=self.n_test,
            feature_importance=self.feature_importance,
        )
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "mae": round(self.mae, 6),
            "rmse": round(self.rmse, 6),
            "r2": round(self.r2, 4),
            "directional_accuracy": round(self.directional_accuracy, 4),
            "improvement_over_xgb": round(self.improvement_over_xgb, 4),
            "improvement_over_lgb": round(self.improvement_over_lgb, 4) if self.improvement_over_lgb else None,
            "n_train": self.n_train,
            "n_test": self.n_test,
            "xgb_weight": round(self.xgb_weight, 4),
            "lgb_weight": round(self.lgb_weight, 4) if self.lgb_weight else None,
            "topology_impact": round(self.topology_impact, 4),
        }


class StackedImpactEnsemble:
    """
    Stacked ensemble combining XGBoost, LightGBM, and topology features.
    
    Training Process:
    1. Generate out-of-fold predictions from base learners using K-fold CV
    2. Stack OOF predictions as meta-features
    3. Train Ridge regression meta-learner on stacked features
    4. Optionally apply topology-based boost
    
    Prediction Process:
    1. Get predictions from all base learners
    2. Stack predictions and pass through meta-learner
    3. Apply topology boost if enabled
    """
    
    MODEL_DIR = "backend/models/ml/ensemble"
    
    TOPOLOGY_FEATURES = [
        "persistent_betti0_count",
        "persistent_betti1_count",
        "persistent_max_lifetime_h0",
        "persistent_max_lifetime_h1",
        "persistent_entropy",
        "persistent_complexity",
        "has_persistent_features",
    ]
    
    def __init__(self, config: Optional[StackedEnsembleConfig] = None):
        self.config = config or StackedEnsembleConfig()
        
        self.xgb_model: Optional[xgb.XGBRegressor] = None
        self.lgb_model = None
        self.meta_learner: Optional[Ridge] = None
        
        self._use_lgb = LIGHTGBM_AVAILABLE
        self._trained = False
        self._feature_names: List[str] = []
        self._meta_weights: Dict[str, float] = {}
        
        Path(self.MODEL_DIR).mkdir(parents=True, exist_ok=True)
    
    def _prepare_data(
        self,
        training_data: TrainingData
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """Prepare features and targets from training data."""
        feature_dicts = [f.to_vector() for f in training_data.features]
        X_df = pd.DataFrame(feature_dicts)
        y_array = np.array(training_data.outcomes)
        
        self._feature_names = list(X_df.columns)
        
        logger.info(f"Prepared data: {X_df.shape[0]} samples, {X_df.shape[1]} features")
        return X_df, y_array
    
    def _extract_topology_features(self, X: pd.DataFrame) -> np.ndarray:
        """Extract topology features for boost calculation."""
        topo_cols = [c for c in self.TOPOLOGY_FEATURES if c in X.columns]
        if not topo_cols:
            return np.zeros(len(X))
        
        topo_df = X[topo_cols].fillna(0)
        
        weights = {
            "persistent_betti1_count": 0.25,
            "persistent_entropy": 0.25,
            "persistent_max_lifetime_h1": 0.20,
            "persistent_complexity": 0.15,
            "persistent_betti0_count": 0.05,
            "persistent_max_lifetime_h0": 0.05,
            "has_persistent_features": 0.05,
        }
        
        topo_score = np.zeros(len(X))
        for col in topo_cols:
            if col in weights:
                values = topo_df[col].values
                if np.std(values) > 0:
                    normalized = (values - np.mean(values)) / np.std(values)
                else:
                    normalized = np.zeros_like(values)
                topo_score += weights.get(col, 0.1) * normalized
        
        return topo_score
    
    def _generate_oof_predictions(
        self,
        X: pd.DataFrame,
        y: np.ndarray,
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate out-of-fold predictions using K-fold cross-validation.
        
        Returns:
            Tuple of (xgb_oof_preds, lgb_oof_preds)
        """
        kf = KFold(n_splits=self.config.n_folds, shuffle=True, random_state=42)
        
        xgb_oof = np.zeros(len(X))
        lgb_oof = np.zeros(len(X)) if self._use_lgb else None
        
        for fold, (train_idx, val_idx) in enumerate(kf.split(X)):
            X_train_fold = X.iloc[train_idx]
            X_val_fold = X.iloc[val_idx]
            y_train_fold = y[train_idx]
            
            xgb_fold = xgb.XGBRegressor(**self.config.xgb_params)
            xgb_fold.fit(X_train_fold, y_train_fold, verbose=False)
            xgb_oof[val_idx] = xgb_fold.predict(X_val_fold)
            
            if self._use_lgb and lgb is not None:
                lgb_fold = lgb.LGBMRegressor(**self.config.lgb_params)
                lgb_fold.fit(X_train_fold, y_train_fold)
                lgb_oof[val_idx] = lgb_fold.predict(X_val_fold)
            
            logger.debug(f"Fold {fold + 1}/{self.config.n_folds} complete")
        
        return xgb_oof, lgb_oof
    
    def train(
        self,
        training_data: TrainingData,
        test_size: float = 0.2,
    ) -> EnsembleMetrics:
        """
        Train the stacked ensemble.
        
        Args:
            training_data: TrainingData with features and outcomes
            test_size: Fraction for validation
            
        Returns:
            EnsembleMetrics with performance statistics
        """
        X, y = self._prepare_data(training_data)
        
        n_test = int(len(X) * test_size)
        X_train, X_test = X.iloc[:-n_test], X.iloc[-n_test:]
        y_train, y_test = y[:-n_test], y[-n_test:]
        
        logger.info(f"Training stacked ensemble: {len(X_train)} train, {len(X_test)} test")
        
        logger.info("Generating out-of-fold predictions...")
        xgb_oof, lgb_oof = self._generate_oof_predictions(X_train, y_train)
        
        if self._use_lgb and lgb_oof is not None:
            meta_features = np.column_stack([xgb_oof, lgb_oof])
            meta_cols = ["xgb_pred", "lgb_pred"]
        else:
            meta_features = xgb_oof.reshape(-1, 1)
            meta_cols = ["xgb_pred"]
        
        if self.config.use_topology_boost:
            topo_boost = self._extract_topology_features(X_train)
            meta_features = np.column_stack([meta_features, topo_boost])
            meta_cols.append("topo_boost")
        
        logger.info("Training meta-learner (Ridge regression)...")
        self.meta_learner = Ridge(alpha=self.config.ridge_alpha)
        self.meta_learner.fit(meta_features, y_train)
        
        self._meta_weights = dict(zip(meta_cols, self.meta_learner.coef_.tolist()))
        logger.info(f"Meta-learner weights: {self._meta_weights}")
        
        logger.info("Training final base learners on full training data...")
        self.xgb_model = xgb.XGBRegressor(**self.config.xgb_params)
        self.xgb_model.fit(X_train, y_train, verbose=False)
        
        if self._use_lgb and lgb is not None:
            self.lgb_model = lgb.LGBMRegressor(**self.config.lgb_params)
            self.lgb_model.fit(X_train, y_train)
        
        self._trained = True
        
        metrics = self._evaluate(X_train, y_train, X_test, y_test)
        
        return metrics
    
    def _evaluate(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray,
    ) -> EnsembleMetrics:
        """Evaluate ensemble performance."""
        xgb_pred_test = self.xgb_model.predict(X_test)
        xgb_da = np.mean(np.sign(xgb_pred_test) == np.sign(y_test))
        
        lgb_pred_test = None
        lgb_da = None
        if self.lgb_model is not None:
            lgb_pred_test = self.lgb_model.predict(X_test)
            lgb_da = np.mean(np.sign(lgb_pred_test) == np.sign(y_test))
        
        ensemble_pred_test = self.predict_batch(X_test)
        
        ensemble_da = np.mean(np.sign(ensemble_pred_test) == np.sign(y_test))
        
        mae = mean_absolute_error(y_test, ensemble_pred_test)
        rmse = np.sqrt(mean_squared_error(y_test, ensemble_pred_test))
        r2 = r2_score(y_test, ensemble_pred_test)
        
        improvement_xgb = ensemble_da - xgb_da
        improvement_lgb = (ensemble_da - lgb_da) if lgb_da else None
        
        topo_impact = 0.0
        if self.config.use_topology_boost and "topo_boost" in self._meta_weights:
            topo_impact = self._meta_weights["topo_boost"]
        
        feature_importance = {}
        if hasattr(self.xgb_model, 'feature_importances_'):
            importance = self.xgb_model.feature_importances_
            for i, name in enumerate(self._feature_names):
                if i < len(importance):
                    feature_importance[name] = float(importance[i])
            feature_importance = dict(sorted(
                feature_importance.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:20])
        
        metrics = EnsembleMetrics(
            mae=mae,
            rmse=rmse,
            r2=r2,
            directional_accuracy=ensemble_da,
            improvement_over_xgb=improvement_xgb,
            improvement_over_lgb=improvement_lgb,
            n_train=len(X_train),
            n_test=len(X_test),
            xgb_weight=self._meta_weights.get("xgb_pred", 0.5),
            lgb_weight=self._meta_weights.get("lgb_pred"),
            topology_impact=topo_impact,
            feature_importance=feature_importance,
        )
        
        logger.info(
            f"Ensemble Evaluation:\n"
            f"  MAE: {mae:.4f}\n"
            f"  RMSE: {rmse:.4f}\n"
            f"  R²: {r2:.4f}\n"
            f"  Directional Accuracy: {ensemble_da:.2%}\n"
            f"  XGBoost DA: {xgb_da:.2%}\n"
            f"  LightGBM DA: {lgb_da:.2% if lgb_da else 'N/A'}\n"
            f"  Improvement over XGB: {improvement_xgb:+.2%}\n"
            f"  Improvement over LGB: {improvement_lgb:+.2% if improvement_lgb else 'N/A'}"
        )
        
        return metrics
    
    def predict_single(self, features: Dict[str, float]) -> StackedPrediction:
        """
        Generate prediction for a single event.
        
        Args:
            features: Feature dictionary
            
        Returns:
            StackedPrediction with ensemble output
        """
        if not self._trained:
            raise ValueError("Model not trained. Call train() first.")
        
        X = pd.DataFrame([features])
        
        for col in self._feature_names:
            if col not in X.columns:
                X[col] = 0.0
        X = X[self._feature_names]
        
        xgb_pred = float(self.xgb_model.predict(X)[0])
        
        lgb_pred = None
        if self.lgb_model is not None:
            lgb_pred = float(self.lgb_model.predict(X)[0])
        
        if lgb_pred is not None:
            meta_features = np.array([[xgb_pred, lgb_pred]])
        else:
            meta_features = np.array([[xgb_pred]])
        
        topo_boost = 0.0
        if self.config.use_topology_boost:
            topo_boost = float(self._extract_topology_features(X)[0])
            meta_features = np.column_stack([meta_features, [[topo_boost]]])
        
        final_pred = float(self.meta_learner.predict(meta_features)[0])
        
        confidence = 1.0 / (1.0 + abs(xgb_pred - (lgb_pred or xgb_pred)))
        
        return StackedPrediction(
            final_prediction=final_pred,
            xgb_prediction=xgb_pred,
            lgb_prediction=lgb_pred,
            topology_boost=topo_boost * self.config.topology_weight,
            confidence=confidence,
            meta_weights=self._meta_weights.copy(),
        )
    
    def predict_batch(self, X: pd.DataFrame) -> np.ndarray:
        """Generate predictions for a batch of events."""
        if not self._trained:
            raise ValueError("Model not trained. Call train() first.")
        
        for col in self._feature_names:
            if col not in X.columns:
                X[col] = 0.0
        X = X[self._feature_names]
        
        xgb_preds = self.xgb_model.predict(X)
        
        if self.lgb_model is not None:
            lgb_preds = self.lgb_model.predict(X)
            meta_features = np.column_stack([xgb_preds, lgb_preds])
        else:
            meta_features = xgb_preds.reshape(-1, 1)
        
        if self.config.use_topology_boost:
            topo_boost = self._extract_topology_features(X)
            meta_features = np.column_stack([meta_features, topo_boost])
        
        return self.meta_learner.predict(meta_features)
    
    def save(self, version: str) -> str:
        """
        Save the ensemble model to disk.
        
        Args:
            version: Model version string
            
        Returns:
            Path to saved model directory
        """
        if not self._trained:
            raise ValueError("Model not trained. Call train() first.")
        
        save_dir = os.path.join(
            self.MODEL_DIR, 
            f"stacked_impact_{self.config.horizon}_{version}"
        )
        Path(save_dir).mkdir(parents=True, exist_ok=True)
        
        joblib.dump(self.xgb_model, os.path.join(save_dir, "xgb_model.joblib"))
        
        if self.lgb_model is not None:
            joblib.dump(self.lgb_model, os.path.join(save_dir, "lgb_model.joblib"))
        
        joblib.dump(self.meta_learner, os.path.join(save_dir, "meta_learner.joblib"))
        
        metadata = {
            "version": version,
            "horizon": self.config.horizon,
            "n_folds": self.config.n_folds,
            "use_lgb": self._use_lgb,
            "use_topology_boost": self.config.use_topology_boost,
            "feature_names": self._feature_names,
            "meta_weights": self._meta_weights,
            "trained_at": datetime.utcnow().isoformat(),
        }
        joblib.dump(metadata, os.path.join(save_dir, "metadata.joblib"))
        
        logger.info(f"Ensemble saved to {save_dir}")
        return save_dir
    
    @classmethod
    def load(cls, horizon: str, version: str) -> "StackedImpactEnsemble":
        """
        Load a saved ensemble model.
        
        Args:
            horizon: Model horizon ("1d", "5d")
            version: Model version
            
        Returns:
            Loaded StackedImpactEnsemble
        """
        load_dir = os.path.join(
            cls.MODEL_DIR,
            f"stacked_impact_{horizon}_{version}"
        )
        
        if not os.path.exists(load_dir):
            raise FileNotFoundError(f"Model not found: {load_dir}")
        
        metadata = joblib.load(os.path.join(load_dir, "metadata.joblib"))
        
        config = StackedEnsembleConfig.for_horizon(horizon)
        config.use_topology_boost = metadata.get("use_topology_boost", True)
        
        ensemble = cls(config=config)
        
        ensemble.xgb_model = joblib.load(os.path.join(load_dir, "xgb_model.joblib"))
        
        lgb_path = os.path.join(load_dir, "lgb_model.joblib")
        if os.path.exists(lgb_path):
            ensemble.lgb_model = joblib.load(lgb_path)
        
        ensemble.meta_learner = joblib.load(os.path.join(load_dir, "meta_learner.joblib"))
        
        ensemble._feature_names = metadata.get("feature_names", [])
        ensemble._meta_weights = metadata.get("meta_weights", {})
        ensemble._use_lgb = metadata.get("use_lgb", False)
        ensemble._trained = True
        
        logger.info(f"Ensemble loaded from {load_dir}")
        return ensemble
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get model metadata."""
        return {
            "trained": self._trained,
            "horizon": self.config.horizon,
            "n_folds": self.config.n_folds,
            "use_lgb": self._use_lgb,
            "use_topology_boost": self.config.use_topology_boost,
            "meta_weights": self._meta_weights,
            "n_features": len(self._feature_names),
            "topology_features": [f for f in self.TOPOLOGY_FEATURES if f in self._feature_names],
        }
