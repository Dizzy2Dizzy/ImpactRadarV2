"""
Model training pipeline with XGBoost/LightGBM.

Handles model training, evaluation, and versioning for impact prediction.
"""

import os
import joblib
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb

try:
    import lightgbm as lgb
    LIGHTGBM_AVAILABLE = True
except (ImportError, OSError) as e:
    lgb = None
    LIGHTGBM_AVAILABLE = False

from releaseradar.ml.schemas import EventFeatures, ModelMetrics, TrainingData
from releaseradar.log_config import logger


HORIZON_HYPERPARAMS = {
    "1d": {
        "n_estimators": 100,
        "max_depth": 4,
        "learning_rate": 0.05,
        "reg_alpha": 1.0,
        "reg_lambda": 2.0,
        "min_child_weight": 5,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "gamma": 0.1,
        "max_delta_step": 1,
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
        "gamma": 0.15,
        "max_delta_step": 1,
    },
    "20d": {
        "n_estimators": 150,
        "max_depth": 4,
        "learning_rate": 0.02,
        "reg_alpha": 2.0,
        "reg_lambda": 3.0,
        "min_child_weight": 10,
        "subsample": 0.7,
        "colsample_bytree": 0.7,
        "gamma": 0.2,
        "max_delta_step": 1,
    },
}


class ModelTrainer:
    """Trains and evaluates ML models for impact prediction."""
    
    MODEL_DIR = "backend/models/ml"
    
    def __init__(self, model_type: str = "xgboost", horizon: str = "1d"):
        """
        Initialize trainer.
        
        Args:
            model_type: "xgboost" or "lightgbm"
            horizon: "1d", "5d", or "20d"
        """
        if model_type == "lightgbm" and not LIGHTGBM_AVAILABLE:
            logger.warning("LightGBM not available, falling back to XGBoost")
            model_type = "xgboost"
        
        self.model_type = model_type
        self.horizon = horizon
        self.model = None
        
        # Ensure model directory exists
        Path(self.MODEL_DIR).mkdir(parents=True, exist_ok=True)
    
    def prepare_training_data(
        self,
        features: List[EventFeatures],
        outcomes: List[float]
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Convert features and outcomes to training format.
        
        Args:
            features: List of EventFeatures
            outcomes: List of target values (returns)
            
        Returns:
            Tuple of (X_df, y_array)
        """
        if len(features) != len(outcomes):
            raise ValueError(f"Features ({len(features)}) and outcomes ({len(outcomes)}) length mismatch")
        
        # Convert features to DataFrame
        feature_dicts = [f.to_vector() for f in features]
        X_df = pd.DataFrame(feature_dicts)
        
        # Convert outcomes to numpy array
        y_array = np.array(outcomes)
        
        logger.info(f"Prepared training data: {X_df.shape[0]} samples, {X_df.shape[1]} features")
        
        return X_df, y_array
    
    def train(
        self,
        training_data: TrainingData,
        test_size: float = 0.2,
        random_state: int = 42,
        use_time_split: bool = False
    ) -> ModelMetrics:
        """
        Train ML model on provided data.
        
        Args:
            training_data: TrainingData object with features and outcomes
            test_size: Fraction of data to use for testing
            random_state: Random seed for reproducibility
            use_time_split: If True, use chronological split instead of random
            
        Returns:
            ModelMetrics with performance statistics
        """
        # Prepare data
        X_df, y_array = self.prepare_training_data(
            training_data.features,
            training_data.outcomes
        )
        
        if use_time_split:
            timestamps = [f.extracted_at for f in training_data.features]
            sorted_indices = np.argsort(timestamps)
            X_df = X_df.iloc[sorted_indices].reset_index(drop=True)
            y_array = y_array[sorted_indices]
            
            split_idx = int(len(X_df) * (1 - test_size))
            X_train = X_df.iloc[:split_idx]
            X_test = X_df.iloc[split_idx:]
            y_train = y_array[:split_idx]
            y_test = y_array[split_idx:]
            
            logger.info(f"Using time-based split: train ends at index {split_idx}")
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X_df, y_array,
                test_size=test_size,
                random_state=random_state
            )
        
        logger.info(f"Training {self.model_type} model on {len(X_train)} samples, "
                   f"testing on {len(X_test)} samples")
        
        # Train model with validation set for early stopping
        if self.model_type == "xgboost":
            self.model = self._train_xgboost(X_train, y_train, X_test, y_test)
        elif self.model_type == "lightgbm":
            self.model = self._train_lightgbm(X_train, y_train)
        else:
            raise ValueError(f"Unknown model type: {self.model_type}")
        
        # Evaluate
        metrics = self._evaluate(X_train, y_train, X_test, y_test)
        
        # Add feature importance
        metrics.feature_importance = self._get_feature_importance(X_df.columns)
        
        # Log top 10 most important features
        top_features = sorted(
            metrics.feature_importance.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        logger.info(f"Top 10 features: {[f'{name}={imp:.3f}' for name, imp in top_features]}")
        
        logger.info(f"Model trained successfully. MAE: {metrics.mae:.4f}, "
                   f"R²: {metrics.r2:.4f}, Directional Accuracy: {metrics.directional_accuracy:.2%}")
        
        return metrics
    
    def _train_xgboost(self, X_train: pd.DataFrame, y_train: np.ndarray, X_val: pd.DataFrame = None, y_val: np.ndarray = None):
        """
        Train XGBoost model with horizon-specific hyperparameters.
        
        Uses optimized settings from HORIZON_HYPERPARAMS based on the prediction horizon:
        - 1d: Faster learning, more trees, moderate depth - short-term signal is clearest
        - 5d: Slower learning, more regularization, deeper trees - capture intermediate patterns
        - 20d: Strongest regularization, more trees, slowest learning - prevent overfitting on long horizon
        """
        horizon_params = HORIZON_HYPERPARAMS.get(self.horizon, HORIZON_HYPERPARAMS["1d"])
        
        params = {
            "objective": "reg:squarederror",
            "eval_metric": "rmse",
            "n_estimators": horizon_params["n_estimators"],
            "max_depth": horizon_params["max_depth"],
            "learning_rate": horizon_params["learning_rate"],
            "reg_alpha": horizon_params["reg_alpha"],
            "reg_lambda": horizon_params["reg_lambda"],
            "min_child_weight": horizon_params["min_child_weight"],
            "subsample": horizon_params["subsample"],
            "colsample_bytree": horizon_params["colsample_bytree"],
            "gamma": horizon_params["gamma"],
            "max_delta_step": horizon_params["max_delta_step"],
            "random_state": 42,
            "n_jobs": -1,
        }
        
        logger.info(f"Training XGBoost for horizon '{self.horizon}' with params: "
                   f"n_estimators={params['n_estimators']}, max_depth={params['max_depth']}, "
                   f"lr={params['learning_rate']}, reg_alpha={params['reg_alpha']}, reg_lambda={params['reg_lambda']}")
        
        model = xgb.XGBRegressor(**params)
        
        model.fit(X_train, y_train, verbose=False)
        
        return model
    
    def _train_lightgbm(self, X_train: pd.DataFrame, y_train: np.ndarray):
        """Train LightGBM model."""
        params = {
            "objective": "regression",
            "metric": "rmse",
            "num_leaves": 31,
            "learning_rate": 0.05,
            "n_estimators": 200,
            "subsample": 0.8,
            "colsample_bytree": 0.8,
            "random_state": 42,
            "n_jobs": -1,
            "verbose": -1,
        }
        
        model = lgb.LGBMRegressor(**params)
        model.fit(X_train, y_train)
        
        return model
    
    def _evaluate(
        self,
        X_train: pd.DataFrame,
        y_train: np.ndarray,
        X_test: pd.DataFrame,
        y_test: np.ndarray
    ) -> ModelMetrics:
        """Evaluate model performance."""
        # Predictions
        y_pred_train = self.model.predict(X_train)
        y_pred_test = self.model.predict(X_test)
        
        # Regression metrics
        mae = mean_absolute_error(y_test, y_pred_test)
        rmse = np.sqrt(mean_squared_error(y_test, y_pred_test))
        r2 = r2_score(y_test, y_pred_test)
        max_error = np.max(np.abs(y_test - y_pred_test))
        
        # Directional accuracy (% of correct direction predictions)
        y_test_sign = np.sign(y_test)
        y_pred_sign = np.sign(y_pred_test)
        directional_accuracy = np.mean(y_test_sign == y_pred_sign)
        
        # Sharpe ratio (simplified - annualized returns / std dev)
        sharpe = None
        if len(y_pred_test) > 1:
            pred_returns_std = np.std(y_pred_test)
            if pred_returns_std > 0:
                sharpe = np.mean(y_pred_test) / pred_returns_std * np.sqrt(252)
        
        return ModelMetrics(
            mae=mae,
            rmse=rmse,
            r2=r2,
            directional_accuracy=directional_accuracy,
            sharpe_ratio=sharpe,
            max_error=max_error,
            n_train=len(X_train),
            n_test=len(X_test),
        )
    
    def _get_feature_importance(self, feature_names: List[str]) -> Dict[str, float]:
        """Extract feature importance scores."""
        if self.model is None:
            return {}
        
        try:
            if self.model_type == "xgboost":
                importance = self.model.feature_importances_
            elif self.model_type == "lightgbm":
                importance = self.model.feature_importances_
            else:
                return {}
            
            # Create dict of feature:importance
            feature_importance = dict(zip(feature_names, importance.tolist()))
            
            # Sort by importance
            sorted_features = sorted(feature_importance.items(), key=lambda x: x[1], reverse=True)
            
            # Return top 20
            return dict(sorted_features[:20])
        
        except Exception as e:
            logger.warning(f"Failed to extract feature importance: {e}")
            return {}
    
    def save_model(self, version: str) -> str:
        """
        Save trained model to disk.
        
        Args:
            version: Model version string (e.g., "1.0.0")
            
        Returns:
            Path to saved model file
        """
        if self.model is None:
            raise ValueError("No model to save. Train a model first.")
        
        filename = f"{self.model_type}_impact_{self.horizon}_{version}.joblib"
        model_path = os.path.join(self.MODEL_DIR, filename)
        
        # Save model
        joblib.dump(self.model, model_path)
        
        logger.info(f"Model saved to {model_path}")
        
        return model_path
    
    def load_model(self, model_path: str):
        """Load model from disk."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        self.model = joblib.load(model_path)
        logger.info(f"Model loaded from {model_path}")
    
    def predict(self, features: List[EventFeatures]) -> np.ndarray:
        """
        Make predictions on new data.
        
        Args:
            features: List of EventFeatures to predict on
            
        Returns:
            Array of predicted returns
        """
        if self.model is None:
            raise ValueError("No model loaded. Train or load a model first.")
        
        # Prepare features
        X_df, _ = self.prepare_training_data(features, [0.0] * len(features))
        
        # Get the feature names the model was trained on (for XGBoost/LightGBM)
        try:
            if self.model_type == "xgboost":
                model_feature_names = self.model.get_booster().feature_names
            elif self.model_type == "lightgbm":
                model_feature_names = self.model.feature_name_
            else:
                model_feature_names = None
                
            if model_feature_names:
                # Filter to only the features the model expects
                available_features = [f for f in model_feature_names if f in X_df.columns]
                missing_features = [f for f in model_feature_names if f not in X_df.columns]
                
                if missing_features:
                    logger.warning(f"Missing {len(missing_features)} features expected by model: {missing_features[:5]}...")
                    # Add missing features with default value 0
                    for feat in missing_features:
                        X_df[feat] = 0.0
                
                # Reorder columns to match model's expected order
                X_df = X_df[model_feature_names]
                logger.debug(f"Filtered features to match model: {len(model_feature_names)} features")
        except Exception as e:
            logger.warning(f"Could not align features with model: {e}")
        
        # Predict
        predictions = self.model.predict(X_df)
        
        return predictions
