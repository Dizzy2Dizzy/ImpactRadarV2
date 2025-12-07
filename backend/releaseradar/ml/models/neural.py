"""
PyTorch Neural Network Model for Market Echo Engine.

This module implements a multi-layer perceptron with gated attention
for event impact prediction, designed to work alongside XGBoost in an ensemble.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
import numpy as np
from pathlib import Path
import json
import pickle
from datetime import datetime

from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression

from releaseradar.log_config import logger


@dataclass
class NeuralModelConfig:
    """Configuration for the neural network model."""
    input_dim: int = 60
    hidden_dims: List[int] = field(default_factory=lambda: [128, 64, 32])
    dropout_rate: float = 0.3
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 100
    early_stopping_patience: int = 10
    attention_heads: int = 4
    use_attention: bool = True
    weight_decay: float = 1e-4
    direction_loss_weight: float = 0.3
    calibration_method: str = "platt"
    
    def to_dict(self) -> Dict:
        return {
            "input_dim": self.input_dim,
            "hidden_dims": self.hidden_dims,
            "dropout_rate": self.dropout_rate,
            "learning_rate": self.learning_rate,
            "batch_size": self.batch_size,
            "epochs": self.epochs,
            "early_stopping_patience": self.early_stopping_patience,
            "attention_heads": self.attention_heads,
            "use_attention": self.use_attention,
            "weight_decay": self.weight_decay,
            "direction_loss_weight": self.direction_loss_weight,
            "calibration_method": self.calibration_method
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "NeuralModelConfig":
        valid_keys = {
            "input_dim", "hidden_dims", "dropout_rate", "learning_rate",
            "batch_size", "epochs", "early_stopping_patience", "attention_heads",
            "use_attention", "weight_decay", "direction_loss_weight", "calibration_method"
        }
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class NeuralPrediction:
    """Prediction output from neural model."""
    ml_adjusted_score: int
    predicted_return: float
    confidence: float
    direction_probability: float
    model_source: str = "neural"
    
    def to_dict(self) -> Dict:
        return {
            "ml_adjusted_score": self.ml_adjusted_score,
            "predicted_return": round(self.predicted_return, 4),
            "confidence": round(self.confidence, 3),
            "direction_probability": round(self.direction_probability, 3),
            "model_source": self.model_source
        }


class GatedAttentionBlock(nn.Module):
    """Gated attention mechanism for feature weighting."""
    
    def __init__(self, input_dim: int, num_heads: int = 4):
        super().__init__()
        self.input_dim = input_dim
        self.num_heads = min(num_heads, input_dim)
        self.head_dim = max(1, input_dim // self.num_heads)
        inner_dim = self.num_heads * self.head_dim
        
        self.query = nn.Linear(input_dim, inner_dim)
        self.key = nn.Linear(input_dim, inner_dim)
        self.value = nn.Linear(input_dim, inner_dim)
        self.gate = nn.Linear(input_dim, input_dim)
        self.output = nn.Linear(inner_dim, input_dim)
        self.layer_norm = nn.LayerNorm(input_dim)
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch_size = x.size(0)
        
        q = self.query(x).view(batch_size, self.num_heads, self.head_dim)
        k = self.key(x).view(batch_size, self.num_heads, self.head_dim)
        v = self.value(x).view(batch_size, self.num_heads, self.head_dim)
        
        attn_weights = F.softmax(
            torch.bmm(q, k.transpose(1, 2)) / np.sqrt(self.head_dim),
            dim=-1
        )
        
        attended = torch.bmm(attn_weights, v).view(batch_size, -1)
        
        gate = torch.sigmoid(self.gate(x))
        gated_output = gate * self.output(attended)
        
        return self.layer_norm(x + gated_output)


class NeuralImpactNetwork(nn.Module):
    """
    Multi-layer perceptron with optional gated attention for event impact prediction.
    
    Architecture:
    - Input layer with batch normalization
    - Optional gated attention block
    - Multiple hidden layers with dropout and residual connections
    - Output layer for regression (predicted return)
    - Direction layer for binary classification (up/down)
    """
    
    def __init__(self, config: NeuralModelConfig):
        super().__init__()
        self.config = config
        
        self.input_norm = nn.BatchNorm1d(config.input_dim)
        
        if config.use_attention:
            self.attention = GatedAttentionBlock(config.input_dim, config.attention_heads)
        else:
            self.attention = None
        
        layers = []
        prev_dim = config.input_dim
        
        for i, hidden_dim in enumerate(config.hidden_dims):
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(config.dropout_rate)
            ])
            prev_dim = hidden_dim
        
        self.hidden_layers = nn.Sequential(*layers)
        
        self.output_layer = nn.Linear(prev_dim, 1)
        
        self.direction_layer = nn.Sequential(
            nn.Linear(prev_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1)
        )
        
        self.confidence_layer = nn.Sequential(
            nn.Linear(prev_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
        
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            x: Input features tensor (batch_size, input_dim)
            
        Returns:
            Tuple of (predicted_return, direction_logit, confidence)
        """
        x = self.input_norm(x)
        
        if self.attention is not None:
            x = self.attention(x)
        
        hidden = self.hidden_layers(x)
        
        prediction = self.output_layer(hidden)
        direction_logit = self.direction_layer(hidden)
        confidence = self.confidence_layer(hidden)
        
        return prediction.squeeze(-1), direction_logit.squeeze(-1), confidence.squeeze(-1)


class ConfidenceCalibrator:
    """
    Confidence calibration using Platt scaling or isotonic regression.
    
    Platt scaling fits a logistic regression to map raw confidences
    to calibrated probabilities. Isotonic regression fits a 
    non-parametric monotonic function.
    """
    
    def __init__(self, method: str = "platt"):
        self.method = method
        self.calibrator = None
        self.is_fitted = False
    
    def fit(self, raw_confidences: np.ndarray, correct_predictions: np.ndarray):
        """
        Fit the calibrator on validation data.
        
        Args:
            raw_confidences: Model confidence scores (0 to 1)
            correct_predictions: Binary array (1 if prediction was correct, 0 otherwise)
        """
        if len(raw_confidences) < 10:
            logger.warning("Insufficient data for calibration, using identity mapping")
            self.is_fitted = False
            return
        
        raw_confidences = np.clip(raw_confidences, 0.001, 0.999)
        
        if self.method == "platt":
            self.calibrator = LogisticRegression(solver='lbfgs', max_iter=1000)
            self.calibrator.fit(raw_confidences.reshape(-1, 1), correct_predictions)
        elif self.method == "isotonic":
            self.calibrator = IsotonicRegression(y_min=0.0, y_max=1.0, out_of_bounds='clip')
            self.calibrator.fit(raw_confidences, correct_predictions)
        else:
            raise ValueError(f"Unknown calibration method: {self.method}")
        
        self.is_fitted = True
        logger.info(f"Confidence calibrator fitted using {self.method} scaling")
    
    def calibrate(self, raw_confidences: np.ndarray) -> np.ndarray:
        """
        Apply calibration to raw confidence scores.
        
        Args:
            raw_confidences: Raw model confidence scores
            
        Returns:
            Calibrated confidence scores
        """
        if not self.is_fitted or self.calibrator is None:
            return raw_confidences
        
        raw_confidences = np.clip(raw_confidences, 0.001, 0.999)
        
        if self.method == "platt":
            calibrated = self.calibrator.predict_proba(raw_confidences.reshape(-1, 1))[:, 1]
        else:
            calibrated = self.calibrator.predict(raw_confidences)
        
        return np.clip(calibrated, 0.0, 1.0)
    
    def save(self, path: Path):
        """Save calibrator state to disk."""
        state = {
            "method": self.method,
            "is_fitted": self.is_fitted,
            "calibrator": self.calibrator
        }
        with open(path, 'wb') as f:
            pickle.dump(state, f)
    
    @classmethod
    def load(cls, path: Path) -> "ConfidenceCalibrator":
        """Load calibrator from disk."""
        with open(path, 'rb') as f:
            state = pickle.load(f)
        
        instance = cls(method=state["method"])
        instance.is_fitted = state["is_fitted"]
        instance.calibrator = state["calibrator"]
        return instance


class NeuralImpactModel:
    """
    Wrapper class for training and inference with the neural network model.
    
    Provides methods for:
    - Training with early stopping and BCE+MSE loss
    - Prediction with calibrated confidence scores
    - Model persistence (save/load)
    - Online learning updates
    - Incremental learning from market data
    """
    
    MODEL_DIR = Path("backend/models/neural")
    
    def __init__(self, config: Optional[NeuralModelConfig] = None):
        self.config = config or NeuralModelConfig()
        self.model = NeuralImpactNetwork(self.config)
        self.optimizer = None
        self.scheduler = None
        self.training_history: List[Dict] = []
        self.best_val_loss = float('inf')
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.calibrator = ConfidenceCalibrator(method=self.config.calibration_method)
        
        self._best_model_state: Optional[Dict] = None
        self._update_count: int = 0
        self._last_update_time: Optional[datetime] = None
        
        self.model.to(self.device)
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        
    def _init_optimizer(self):
        """Initialize optimizer and scheduler."""
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=5, min_lr=1e-6
        )
        
    def train(
        self,
        X_train: np.ndarray,
        y_train: np.ndarray,
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[np.ndarray] = None,
        verbose: bool = True
    ) -> Dict:
        """
        Train the neural network model with MSE + BCE loss.
        
        Args:
            X_train: Training features (n_samples, n_features)
            y_train: Training targets (n_samples,) - returns as decimals
            X_val: Validation features (optional)
            y_val: Validation targets (optional)
            verbose: Whether to log progress
            
        Returns:
            Training metrics dictionary
        """
        self._init_optimizer()
        self.model.train()
        
        X_train_t = torch.FloatTensor(X_train).to(self.device)
        y_train_t = torch.FloatTensor(y_train).to(self.device)
        
        if X_val is not None and y_val is not None:
            X_val_t = torch.FloatTensor(X_val).to(self.device)
            y_val_t = torch.FloatTensor(y_val).to(self.device)
        else:
            split_idx = int(len(X_train) * 0.8)
            indices = torch.randperm(len(X_train))
            train_idx, val_idx = indices[:split_idx], indices[split_idx:]
            X_val_t, y_val_t = X_train_t[val_idx], y_train_t[val_idx]
            X_train_t, y_train_t = X_train_t[train_idx], y_train_t[train_idx]
        
        y_train_direction = (y_train_t > 0).float()
        y_val_direction = (y_val_t > 0).float()
        
        dataset = torch.utils.data.TensorDataset(X_train_t, y_train_t, y_train_direction)
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=self.config.batch_size, shuffle=True
        )
        
        best_val_loss = float('inf')
        patience_counter = 0
        self._best_model_state = None
        
        for epoch in range(self.config.epochs):
            self.model.train()
            epoch_mse_loss = 0.0
            epoch_bce_loss = 0.0
            epoch_total_loss = 0.0
            n_batches = 0
            
            for batch_X, batch_y, batch_direction in dataloader:
                self.optimizer.zero_grad()
                
                pred, direction_logit, conf = self.model(batch_X)
                
                mse_loss = F.mse_loss(pred, batch_y)
                
                bce_loss = F.binary_cross_entropy_with_logits(direction_logit, batch_direction)
                
                errors = torch.abs(pred - batch_y)
                conf_target = torch.exp(-errors * 10)
                conf_loss = F.mse_loss(conf, conf_target.detach())
                
                total_loss = mse_loss + self.config.direction_loss_weight * bce_loss + 0.1 * conf_loss
                
                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
                
                epoch_mse_loss += mse_loss.item()
                epoch_bce_loss += bce_loss.item()
                epoch_total_loss += total_loss.item()
                n_batches += 1
            
            avg_train_loss = epoch_total_loss / n_batches
            avg_mse_loss = epoch_mse_loss / n_batches
            avg_bce_loss = epoch_bce_loss / n_batches
            
            self.model.eval()
            with torch.no_grad():
                val_pred, val_direction_logit, val_conf = self.model(X_val_t)
                val_mse = F.mse_loss(val_pred, y_val_t).item()
                val_bce = F.binary_cross_entropy_with_logits(val_direction_logit, y_val_direction).item()
                val_loss = val_mse + self.config.direction_loss_weight * val_bce
                
                val_direction_pred = (torch.sigmoid(val_direction_logit) > 0.5).float()
                directional_acc = (val_direction_pred == y_val_direction).float().mean().item()
                
                direction_probs = torch.sigmoid(val_direction_logit)
            
            self.scheduler.step(val_loss)
            
            self.training_history.append({
                "epoch": epoch + 1,
                "train_loss": avg_train_loss,
                "train_mse": avg_mse_loss,
                "train_bce": avg_bce_loss,
                "val_loss": val_loss,
                "val_mse": val_mse,
                "val_bce": val_bce,
                "directional_accuracy": directional_acc,
                "lr": self.optimizer.param_groups[0]['lr']
            })
            
            if verbose and (epoch + 1) % 10 == 0:
                logger.info(
                    f"Epoch {epoch+1}/{self.config.epochs}: "
                    f"train_loss={avg_train_loss:.4f} (mse={avg_mse_loss:.4f}, bce={avg_bce_loss:.4f}), "
                    f"val_loss={val_loss:.4f}, dir_acc={directional_acc:.2%}"
                )
            
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self.best_val_loss = val_loss
                self._best_model_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
            else:
                patience_counter += 1
                if patience_counter >= self.config.early_stopping_patience:
                    if verbose:
                        logger.info(f"Early stopping at epoch {epoch+1}")
                    break
        
        if self._best_model_state is not None:
            self.model.load_state_dict(self._best_model_state)
            self.model.to(self.device)
        
        self._calibrate_confidence(X_val_t, y_val_t)
        
        final_metrics = self._evaluate(X_val_t, y_val_t)
        final_metrics["epochs_trained"] = epoch + 1
        final_metrics["best_val_loss"] = best_val_loss
        
        return final_metrics
    
    def _calibrate_confidence(self, X_val: torch.Tensor, y_val: torch.Tensor):
        """Fit confidence calibrator using validation data."""
        self.model.eval()
        with torch.no_grad():
            pred, direction_logit, conf = self.model(X_val)
            
            pred_sign = torch.sign(pred)
            actual_sign = torch.sign(y_val)
            correct = (pred_sign == actual_sign).float().cpu().numpy()
            
            raw_conf = conf.cpu().numpy()
        
        self.calibrator.fit(raw_conf, correct)
    
    def _evaluate(self, X: torch.Tensor, y: torch.Tensor) -> Dict:
        """Evaluate model on given data."""
        self.model.eval()
        with torch.no_grad():
            pred, direction_logit, conf = self.model(X)
            
            mse = F.mse_loss(pred, y).item()
            mae = torch.abs(pred - y).mean().item()
            rmse = np.sqrt(mse)
            
            direction_pred = (torch.sigmoid(direction_logit) > 0.5).float()
            actual_direction = (y > 0).float()
            directional_accuracy = (direction_pred == actual_direction).float().mean().item()
            
            pred_np = pred.cpu().numpy()
            sharpe = None
            if len(pred_np) > 1 and np.std(pred_np) > 0:
                sharpe = np.mean(pred_np) / np.std(pred_np) * np.sqrt(252)
            
            raw_conf = conf.cpu().numpy()
            calibrated_conf = self.calibrator.calibrate(raw_conf)
            avg_confidence = float(np.mean(calibrated_conf))
            
            bce = F.binary_cross_entropy_with_logits(direction_logit, actual_direction).item()
        
        return {
            "mse": mse,
            "mae": mae,
            "rmse": rmse,
            "bce": bce,
            "directional_accuracy": directional_accuracy,
            "sharpe_ratio": sharpe,
            "avg_confidence": avg_confidence,
            "n_samples": len(y),
            "calibration_fitted": self.calibrator.is_fitted
        }
    
    def predict(self, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions (raw values).
        
        Args:
            X: Feature array (n_samples, n_features)
            
        Returns:
            Tuple of (predictions, calibrated_confidence_scores)
        """
        self.model.eval()
        X_t = torch.FloatTensor(X).to(self.device)
        
        with torch.no_grad():
            pred, direction_logit, conf = self.model(X_t)
        
        raw_conf = conf.cpu().numpy()
        calibrated_conf = self.calibrator.calibrate(raw_conf)
        
        return pred.cpu().numpy(), calibrated_conf
    
    def predict_single(self, features: np.ndarray) -> Tuple[float, float]:
        """
        Make a single prediction.
        
        Args:
            features: Feature vector (n_features,)
            
        Returns:
            Tuple of (prediction, calibrated_confidence)
        """
        X = features.reshape(1, -1)
        pred, conf = self.predict(X)
        return float(pred[0]), float(conf[0])
    
    def predict_full(self, features: np.ndarray) -> NeuralPrediction:
        """
        Make a prediction with full output including ml_adjusted_score.
        
        Args:
            features: Feature vector (n_features,)
            
        Returns:
            NeuralPrediction with ml_adjusted_score, predicted_return, confidence, direction_probability
        """
        X = features.reshape(1, -1)
        self.model.eval()
        X_t = torch.FloatTensor(X).to(self.device)
        
        with torch.no_grad():
            pred, direction_logit, conf = self.model(X_t)
        
        predicted_return = float(pred.cpu().numpy()[0])
        raw_conf = float(conf.cpu().numpy()[0])
        calibrated_conf = float(self.calibrator.calibrate(np.array([raw_conf]))[0])
        direction_prob = float(torch.sigmoid(direction_logit).cpu().numpy()[0])
        
        ml_adjusted_score = int(np.clip(50 + predicted_return * 800, 1, 100))
        
        return NeuralPrediction(
            ml_adjusted_score=ml_adjusted_score,
            predicted_return=predicted_return,
            confidence=calibrated_conf,
            direction_probability=direction_prob,
            model_source="neural"
        )
    
    def online_update(
        self,
        X: np.ndarray,
        y: np.ndarray,
        learning_rate: Optional[float] = None
    ) -> float:
        """
        Perform online learning update with new data.
        
        Args:
            X: New feature samples
            y: New target values
            learning_rate: Optional override for learning rate
            
        Returns:
            Loss after update
        """
        if self.optimizer is None:
            self._init_optimizer()
        
        if learning_rate is not None:
            for param_group in self.optimizer.param_groups:
                param_group['lr'] = learning_rate
        
        self.model.train()
        X_t = torch.FloatTensor(X).to(self.device)
        y_t = torch.FloatTensor(y).to(self.device)
        y_direction = (y_t > 0).float()
        
        self.optimizer.zero_grad()
        pred, direction_logit, conf = self.model(X_t)
        
        mse_loss = F.mse_loss(pred, y_t)
        bce_loss = F.binary_cross_entropy_with_logits(direction_logit, y_direction)
        loss = mse_loss + self.config.direction_loss_weight * bce_loss
        
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
        self.optimizer.step()
        
        return loss.item()
    
    def incremental_update(
        self,
        X: np.ndarray,
        y: np.ndarray,
        n_epochs: int = 5,
        learning_rate: Optional[float] = None,
        recalibrate: bool = True
    ) -> Dict:
        """
        Perform incremental learning from new market data.
        
        This method is designed for continuous learning, where new data
        arrives periodically and the model needs to adapt without full retraining.
        
        Args:
            X: New feature samples (n_samples, n_features)
            y: New target values (n_samples,) - returns as decimals
            n_epochs: Number of epochs to train on new data
            learning_rate: Optional learning rate (default: 10% of original)
            recalibrate: Whether to recalibrate confidence after update
            
        Returns:
            Dict with update metrics
        """
        if len(X) == 0:
            return {"status": "skipped", "reason": "no samples"}
        
        if self.optimizer is None:
            self._init_optimizer()
        
        incremental_lr = learning_rate or (self.config.learning_rate * 0.1)
        original_lr = self.optimizer.param_groups[0]['lr']
        
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = incremental_lr
        
        X_t = torch.FloatTensor(X).to(self.device)
        y_t = torch.FloatTensor(y).to(self.device)
        y_direction = (y_t > 0).float()
        
        dataset = torch.utils.data.TensorDataset(X_t, y_t, y_direction)
        batch_size = min(self.config.batch_size, len(X))
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)
        
        total_loss = 0.0
        total_batches = 0
        
        self.model.train()
        for epoch in range(n_epochs):
            epoch_loss = 0.0
            n_batches = 0
            
            for batch_X, batch_y, batch_dir in dataloader:
                self.optimizer.zero_grad()
                
                pred, direction_logit, conf = self.model(batch_X)
                
                mse_loss = F.mse_loss(pred, batch_y)
                bce_loss = F.binary_cross_entropy_with_logits(direction_logit, batch_dir)
                loss = mse_loss + self.config.direction_loss_weight * bce_loss
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 0.5)
                self.optimizer.step()
                
                epoch_loss += loss.item()
                n_batches += 1
            
            total_loss += epoch_loss
            total_batches += n_batches
        
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = original_lr
        
        if recalibrate and len(X) >= 20:
            self._calibrate_confidence(X_t, y_t)
        
        self._update_count += 1
        self._last_update_time = datetime.utcnow()
        
        self.model.eval()
        with torch.no_grad():
            final_pred, final_dir, final_conf = self.model(X_t)
            final_mse = F.mse_loss(final_pred, y_t).item()
            dir_pred = (torch.sigmoid(final_dir) > 0.5).float()
            dir_acc = (dir_pred == y_direction).float().mean().item()
        
        return {
            "status": "success",
            "n_samples": len(X),
            "n_epochs": n_epochs,
            "avg_loss": total_loss / max(1, total_batches),
            "final_mse": final_mse,
            "directional_accuracy": dir_acc,
            "learning_rate_used": incremental_lr,
            "update_count": self._update_count,
            "recalibrated": recalibrate and len(X) >= 20
        }
    
    def save(self, name: str, version: str = "1.0.0") -> Path:
        """
        Save model to disk.
        
        Args:
            name: Model name
            version: Model version
            
        Returns:
            Path to saved model directory
        """
        model_path = self.MODEL_DIR / f"{name}_{version}"
        model_path.mkdir(parents=True, exist_ok=True)
        
        torch.save(self.model.state_dict(), model_path / "model.pt")
        
        with open(model_path / "config.json", "w") as f:
            json.dump(self.config.to_dict(), f, indent=2)
        
        with open(model_path / "training_history.json", "w") as f:
            json.dump(self.training_history, f, indent=2)
        
        self.calibrator.save(model_path / "calibrator.pkl")
        
        metadata = {
            "update_count": self._update_count,
            "last_update_time": self._last_update_time.isoformat() if self._last_update_time else None,
            "best_val_loss": self.best_val_loss
        }
        with open(model_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved neural model to {model_path}")
        return model_path
    
    @classmethod
    def load(cls, name: str, version: str = "1.0.0") -> "NeuralImpactModel":
        """
        Load model from disk.
        
        Args:
            name: Model name
            version: Model version
            
        Returns:
            Loaded NeuralImpactModel instance
        """
        model_path = cls.MODEL_DIR / f"{name}_{version}"
        
        with open(model_path / "config.json", "r") as f:
            config = NeuralModelConfig.from_dict(json.load(f))
        
        instance = cls(config)
        
        state_dict = torch.load(model_path / "model.pt", map_location=instance.device, weights_only=False)
        instance.model.load_state_dict(state_dict)
        
        history_path = model_path / "training_history.json"
        if history_path.exists():
            with open(history_path, "r") as f:
                instance.training_history = json.load(f)
        
        calibrator_path = model_path / "calibrator.pkl"
        if calibrator_path.exists():
            instance.calibrator = ConfidenceCalibrator.load(calibrator_path)
        
        metadata_path = model_path / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                instance._update_count = metadata.get("update_count", 0)
                if metadata.get("last_update_time"):
                    instance._last_update_time = datetime.fromisoformat(metadata["last_update_time"])
                instance.best_val_loss = metadata.get("best_val_loss", float('inf'))
        
        logger.info(f"Loaded neural model from {model_path}")
        return instance
    
    @classmethod
    def save_model(cls, model: "NeuralImpactModel", name: str, version: str = "1.0.0") -> Path:
        """
        Class method to save a model instance.
        
        Args:
            model: NeuralImpactModel instance to save
            name: Model name
            version: Model version
            
        Returns:
            Path to saved model directory
        """
        return model.save(name, version)
    
    @classmethod
    def load_model(cls, name: str, version: str = "1.0.0") -> "NeuralImpactModel":
        """
        Class method to load a model from disk.
        
        Args:
            name: Model name
            version: Model version
            
        Returns:
            Loaded NeuralImpactModel instance
        """
        return cls.load(name, version)


@dataclass
class MultiHorizonNeuralConfig(NeuralModelConfig):
    """
    Configuration for multi-horizon neural network model.
    
    Extends NeuralModelConfig with horizon-specific parameters for
    multi-task learning across different prediction windows.
    """
    horizons: List[str] = field(default_factory=lambda: ["1d", "5d", "20d"])
    horizon_head_dims: List[int] = field(default_factory=lambda: [32, 16])
    horizon_loss_weights: Dict[str, float] = field(
        default_factory=lambda: {"1d": 1.0, "5d": 0.8, "20d": 0.6}
    )
    
    def to_dict(self) -> Dict:
        base_dict = super().to_dict()
        base_dict.update({
            "horizons": self.horizons,
            "horizon_head_dims": self.horizon_head_dims,
            "horizon_loss_weights": self.horizon_loss_weights
        })
        return base_dict
    
    @classmethod
    def from_dict(cls, d: Dict) -> "MultiHorizonNeuralConfig":
        valid_keys = {
            "input_dim", "hidden_dims", "dropout_rate", "learning_rate",
            "batch_size", "epochs", "early_stopping_patience", "attention_heads",
            "use_attention", "weight_decay", "direction_loss_weight", "calibration_method",
            "horizons", "horizon_head_dims", "horizon_loss_weights"
        }
        filtered = {k: v for k, v in d.items() if k in valid_keys}
        return cls(**filtered)


@dataclass
class MultiHorizonPrediction:
    """Prediction output from multi-horizon neural model for a single horizon."""
    horizon: str
    ml_adjusted_score: int
    predicted_return: float
    confidence: float
    direction_probability: float
    model_source: str = "neural_multi_horizon"
    
    def to_dict(self) -> Dict:
        return {
            "horizon": self.horizon,
            "ml_adjusted_score": self.ml_adjusted_score,
            "predicted_return": round(self.predicted_return, 4),
            "confidence": round(self.confidence, 3),
            "direction_probability": round(self.direction_probability, 3),
            "model_source": self.model_source
        }


class HorizonHead(nn.Module):
    """
    Horizon-specific output head for multi-horizon model.
    
    Each head produces prediction, direction, and confidence outputs
    for a specific time horizon.
    """
    
    def __init__(self, input_dim: int, head_dims: List[int]):
        super().__init__()
        
        layers = []
        prev_dim = input_dim
        for dim in head_dims:
            layers.extend([
                nn.Linear(prev_dim, dim),
                nn.ReLU(),
                nn.Dropout(0.2)
            ])
            prev_dim = dim
        self.head_layers = nn.Sequential(*layers) if layers else nn.Identity()
        
        final_dim = head_dims[-1] if head_dims else input_dim
        
        self.prediction_layer = nn.Linear(final_dim, 1)
        self.direction_layer = nn.Sequential(
            nn.Linear(final_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1)
        )
        self.confidence_layer = nn.Sequential(
            nn.Linear(final_dim, 16),
            nn.ReLU(),
            nn.Linear(16, 1),
            nn.Sigmoid()
        )
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass for a single horizon head.
        
        Args:
            x: Shared trunk output (batch_size, trunk_output_dim)
            
        Returns:
            Tuple of (prediction, direction_logit, confidence)
        """
        h = self.head_layers(x)
        prediction = self.prediction_layer(h).squeeze(-1)
        direction_logit = self.direction_layer(h).squeeze(-1)
        confidence = self.confidence_layer(h).squeeze(-1)
        return prediction, direction_logit, confidence


class MultiHorizonNeuralNetwork(nn.Module):
    """
    Multi-task neural network with shared trunk and horizon-specific heads.
    
    Architecture:
    - Shared trunk: input_norm -> attention -> hidden_layers
    - Horizon-specific heads: separate prediction/direction/confidence per horizon
    
    Key insight: The shared trunk learns common patterns across all horizons,
    while the horizon-specific heads specialize for each time window.
    This enables knowledge transfer while allowing specialization.
    """
    
    def __init__(self, config: MultiHorizonNeuralConfig):
        super().__init__()
        self.config = config
        self.horizons = config.horizons
        
        self.input_norm = nn.BatchNorm1d(config.input_dim)
        
        if config.use_attention:
            self.attention = GatedAttentionBlock(config.input_dim, config.attention_heads)
        else:
            self.attention = None
        
        layers = []
        prev_dim = config.input_dim
        for hidden_dim in config.hidden_dims:
            layers.extend([
                nn.Linear(prev_dim, hidden_dim),
                nn.BatchNorm1d(hidden_dim),
                nn.ReLU(),
                nn.Dropout(config.dropout_rate)
            ])
            prev_dim = hidden_dim
        self.hidden_layers = nn.Sequential(*layers)
        
        trunk_output_dim = config.hidden_dims[-1] if config.hidden_dims else config.input_dim
        
        self.horizon_heads = nn.ModuleDict({
            horizon: HorizonHead(trunk_output_dim, config.horizon_head_dims)
            for horizon in config.horizons
        })
    
    def forward_trunk(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass through shared trunk only.
        
        Args:
            x: Input features tensor (batch_size, input_dim)
            
        Returns:
            Trunk output tensor (batch_size, trunk_output_dim)
        """
        x = self.input_norm(x)
        if self.attention is not None:
            x = self.attention(x)
        return self.hidden_layers(x)
    
    def forward(self, x: torch.Tensor) -> Dict[str, Tuple[torch.Tensor, torch.Tensor, torch.Tensor]]:
        """
        Forward pass through shared trunk and all horizon heads.
        
        Args:
            x: Input features tensor (batch_size, input_dim)
            
        Returns:
            Dict mapping horizon names to (prediction, direction_logit, confidence) tuples
        """
        trunk_output = self.forward_trunk(x)
        
        outputs = {}
        for horizon in self.horizons:
            outputs[horizon] = self.horizon_heads[horizon](trunk_output)
        
        return outputs
    
    def forward_horizon(self, x: torch.Tensor, horizon: str) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """
        Forward pass for a single horizon.
        
        Args:
            x: Input features tensor (batch_size, input_dim)
            horizon: Target horizon (e.g., "1d", "5d", "20d")
            
        Returns:
            Tuple of (prediction, direction_logit, confidence)
        """
        if horizon not in self.horizon_heads:
            raise ValueError(f"Unknown horizon: {horizon}. Valid horizons: {self.horizons}")
        
        trunk_output = self.forward_trunk(x)
        return self.horizon_heads[horizon](trunk_output)


class MultiHorizonNeuralModel:
    """
    Wrapper class for training and inference with multi-horizon neural network.
    
    Provides methods for:
    - Multi-task training with horizon-specific loss weighting
    - Single-horizon inference (predict_horizon)
    - All-horizon inference (predict_all)
    - Model persistence with multi-horizon structure
    - Incremental learning across horizons
    """
    
    MODEL_DIR = Path("backend/models/neural")
    
    def __init__(self, config: Optional[MultiHorizonNeuralConfig] = None):
        self.config = config or MultiHorizonNeuralConfig()
        self.model = MultiHorizonNeuralNetwork(self.config)
        self.optimizer = None
        self.scheduler = None
        self.training_history: List[Dict] = []
        self.best_val_loss = float('inf')
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        self.calibrators: Dict[str, ConfidenceCalibrator] = {
            horizon: ConfidenceCalibrator(method=self.config.calibration_method)
            for horizon in self.config.horizons
        }
        
        self._best_model_state: Optional[Dict] = None
        self._update_count: int = 0
        self._last_update_time: Optional[datetime] = None
        
        self.model.to(self.device)
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    def _init_optimizer(self):
        """Initialize optimizer and scheduler."""
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(),
            lr=self.config.learning_rate,
            weight_decay=self.config.weight_decay
        )
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode='min', factor=0.5, patience=5, min_lr=1e-6
        )
    
    def train(
        self,
        X_train: np.ndarray,
        y_train: Dict[str, np.ndarray],
        X_val: Optional[np.ndarray] = None,
        y_val: Optional[Dict[str, np.ndarray]] = None,
        verbose: bool = True
    ) -> Dict:
        """
        Train the multi-horizon neural network with horizon-weighted losses.
        
        Args:
            X_train: Training features (n_samples, n_features)
            y_train: Dict mapping horizon names to target arrays (n_samples,)
            X_val: Validation features (optional)
            y_val: Dict mapping horizon names to validation targets (optional)
            verbose: Whether to log progress
            
        Returns:
            Training metrics dictionary
        """
        self._init_optimizer()
        self.model.train()
        
        X_train_t = torch.FloatTensor(X_train).to(self.device)
        y_train_tensors = {
            h: torch.FloatTensor(y).to(self.device) for h, y in y_train.items()
        }
        
        if X_val is not None and y_val is not None:
            X_val_t = torch.FloatTensor(X_val).to(self.device)
            y_val_tensors = {
                h: torch.FloatTensor(y).to(self.device) for h, y in y_val.items()
            }
        else:
            split_idx = int(len(X_train) * 0.8)
            indices = torch.randperm(len(X_train))
            train_idx, val_idx = indices[:split_idx], indices[split_idx:]
            X_val_t = X_train_t[val_idx]
            y_val_tensors = {h: y[val_idx] for h, y in y_train_tensors.items()}
            X_train_t = X_train_t[train_idx]
            y_train_tensors = {h: y[train_idx] for h, y in y_train_tensors.items()}
        
        y_train_directions = {
            h: (y > 0).float() for h, y in y_train_tensors.items()
        }
        y_val_directions = {
            h: (y > 0).float() for h, y in y_val_tensors.items()
        }
        
        first_horizon = self.config.horizons[0]
        dataset = torch.utils.data.TensorDataset(
            X_train_t,
            y_train_tensors[first_horizon],
            y_train_directions[first_horizon]
        )
        dataloader = torch.utils.data.DataLoader(
            dataset, batch_size=self.config.batch_size, shuffle=True
        )
        
        best_val_loss = float('inf')
        patience_counter = 0
        self._best_model_state = None
        
        for epoch in range(self.config.epochs):
            self.model.train()
            epoch_losses = {h: 0.0 for h in self.config.horizons}
            epoch_total_loss = 0.0
            n_batches = 0
            
            for batch_idx, _ in enumerate(dataloader):
                start = batch_idx * self.config.batch_size
                end = min(start + self.config.batch_size, len(X_train_t))
                batch_X = X_train_t[start:end]
                
                self.optimizer.zero_grad()
                outputs = self.model(batch_X)
                
                total_loss = torch.tensor(0.0, device=self.device)
                for horizon in self.config.horizons:
                    pred, direction_logit, conf = outputs[horizon]
                    batch_y = y_train_tensors[horizon][start:end]
                    batch_direction = y_train_directions[horizon][start:end]
                    
                    mse_loss = F.mse_loss(pred, batch_y)
                    bce_loss = F.binary_cross_entropy_with_logits(direction_logit, batch_direction)
                    
                    errors = torch.abs(pred - batch_y)
                    conf_target = torch.exp(-errors * 10)
                    conf_loss = F.mse_loss(conf, conf_target.detach())
                    
                    horizon_loss = mse_loss + self.config.direction_loss_weight * bce_loss + 0.1 * conf_loss
                    weight = self.config.horizon_loss_weights.get(horizon, 1.0)
                    total_loss = total_loss + weight * horizon_loss
                    
                    epoch_losses[horizon] += horizon_loss.item()
                
                total_loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                self.optimizer.step()
                
                epoch_total_loss += total_loss.item()
                n_batches += 1
            
            avg_train_loss = epoch_total_loss / max(1, n_batches)
            
            self.model.eval()
            with torch.no_grad():
                val_outputs = self.model(X_val_t)
                val_loss = 0.0
                val_metrics = {}
                
                for horizon in self.config.horizons:
                    pred, direction_logit, conf = val_outputs[horizon]
                    y_val_h = y_val_tensors[horizon]
                    y_val_dir = y_val_directions[horizon]
                    
                    val_mse = F.mse_loss(pred, y_val_h).item()
                    val_bce = F.binary_cross_entropy_with_logits(direction_logit, y_val_dir).item()
                    horizon_val_loss = val_mse + self.config.direction_loss_weight * val_bce
                    
                    weight = self.config.horizon_loss_weights.get(horizon, 1.0)
                    val_loss += weight * horizon_val_loss
                    
                    dir_pred = (torch.sigmoid(direction_logit) > 0.5).float()
                    dir_acc = (dir_pred == y_val_dir).float().mean().item()
                    
                    val_metrics[horizon] = {
                        "val_mse": val_mse,
                        "val_bce": val_bce,
                        "directional_accuracy": dir_acc
                    }
            
            self.scheduler.step(val_loss)
            
            history_entry = {
                "epoch": epoch + 1,
                "train_loss": avg_train_loss,
                "val_loss": val_loss,
                "lr": self.optimizer.param_groups[0]['lr'],
                "horizon_metrics": val_metrics
            }
            self.training_history.append(history_entry)
            
            if verbose and (epoch + 1) % 10 == 0:
                horizon_accs = ", ".join([
                    f"{h}={val_metrics[h]['directional_accuracy']:.2%}"
                    for h in self.config.horizons
                ])
                logger.info(
                    f"Epoch {epoch+1}/{self.config.epochs}: "
                    f"train_loss={avg_train_loss:.4f}, val_loss={val_loss:.4f}, "
                    f"dir_acc: [{horizon_accs}]"
                )
            
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                self.best_val_loss = val_loss
                self._best_model_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
            else:
                patience_counter += 1
                if patience_counter >= self.config.early_stopping_patience:
                    if verbose:
                        logger.info(f"Early stopping at epoch {epoch+1}")
                    break
        
        if self._best_model_state is not None:
            self.model.load_state_dict(self._best_model_state)
            self.model.to(self.device)
        
        for horizon in self.config.horizons:
            self._calibrate_confidence_horizon(X_val_t, y_val_tensors[horizon], horizon)
        
        final_metrics = self._evaluate_all(X_val_t, y_val_tensors)
        final_metrics["epochs_trained"] = epoch + 1
        final_metrics["best_val_loss"] = best_val_loss
        
        return final_metrics
    
    def _calibrate_confidence_horizon(self, X_val: torch.Tensor, y_val: torch.Tensor, horizon: str):
        """Fit confidence calibrator for a specific horizon."""
        self.model.eval()
        with torch.no_grad():
            pred, direction_logit, conf = self.model.forward_horizon(X_val, horizon)
            
            pred_sign = torch.sign(pred)
            actual_sign = torch.sign(y_val)
            correct = (pred_sign == actual_sign).float().cpu().numpy()
            raw_conf = conf.cpu().numpy()
        
        self.calibrators[horizon].fit(raw_conf, correct)
    
    def _evaluate_all(self, X: torch.Tensor, y_dict: Dict[str, torch.Tensor]) -> Dict:
        """Evaluate model across all horizons."""
        self.model.eval()
        results = {}
        
        with torch.no_grad():
            outputs = self.model(X)
            
            for horizon in self.config.horizons:
                pred, direction_logit, conf = outputs[horizon]
                y = y_dict[horizon]
                
                mse = F.mse_loss(pred, y).item()
                mae = torch.abs(pred - y).mean().item()
                rmse = np.sqrt(mse)
                
                direction_pred = (torch.sigmoid(direction_logit) > 0.5).float()
                actual_direction = (y > 0).float()
                dir_acc = (direction_pred == actual_direction).float().mean().item()
                
                bce = F.binary_cross_entropy_with_logits(direction_logit, actual_direction).item()
                
                raw_conf = conf.cpu().numpy()
                calibrated_conf = self.calibrators[horizon].calibrate(raw_conf)
                avg_conf = float(np.mean(calibrated_conf))
                
                results[horizon] = {
                    "mse": mse,
                    "mae": mae,
                    "rmse": rmse,
                    "bce": bce,
                    "directional_accuracy": dir_acc,
                    "avg_confidence": avg_conf,
                    "n_samples": len(y),
                    "calibration_fitted": self.calibrators[horizon].is_fitted
                }
        
        return results
    
    def predict_horizon(self, X: np.ndarray, horizon: str) -> Tuple[np.ndarray, np.ndarray]:
        """
        Make predictions for a specific horizon.
        
        Args:
            X: Feature array (n_samples, n_features)
            horizon: Target horizon (e.g., "1d", "5d", "20d")
            
        Returns:
            Tuple of (predictions, calibrated_confidence_scores)
        """
        if horizon not in self.config.horizons:
            raise ValueError(f"Unknown horizon: {horizon}. Valid horizons: {self.config.horizons}")
        
        self.model.eval()
        X_t = torch.FloatTensor(X).to(self.device)
        
        with torch.no_grad():
            pred, direction_logit, conf = self.model.forward_horizon(X_t, horizon)
        
        raw_conf = conf.cpu().numpy()
        calibrated_conf = self.calibrators[horizon].calibrate(raw_conf)
        
        return pred.cpu().numpy(), calibrated_conf
    
    def predict_all(self, X: np.ndarray) -> Dict[str, Tuple[np.ndarray, np.ndarray]]:
        """
        Make predictions for all horizons at once.
        
        Args:
            X: Feature array (n_samples, n_features)
            
        Returns:
            Dict mapping horizon names to (predictions, calibrated_confidence) tuples
        """
        self.model.eval()
        X_t = torch.FloatTensor(X).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(X_t)
        
        results = {}
        for horizon in self.config.horizons:
            pred, direction_logit, conf = outputs[horizon]
            raw_conf = conf.cpu().numpy()
            calibrated_conf = self.calibrators[horizon].calibrate(raw_conf)
            results[horizon] = (pred.cpu().numpy(), calibrated_conf)
        
        return results
    
    def predict_full_horizon(self, features: np.ndarray, horizon: str) -> MultiHorizonPrediction:
        """
        Make a full prediction for a specific horizon.
        
        Args:
            features: Feature vector (n_features,)
            horizon: Target horizon (e.g., "1d", "5d", "20d")
            
        Returns:
            MultiHorizonPrediction with all output fields
        """
        X = features.reshape(1, -1)
        self.model.eval()
        X_t = torch.FloatTensor(X).to(self.device)
        
        with torch.no_grad():
            pred, direction_logit, conf = self.model.forward_horizon(X_t, horizon)
        
        predicted_return = float(pred.cpu().numpy()[0])
        raw_conf = float(conf.cpu().numpy()[0])
        calibrated_conf = float(self.calibrators[horizon].calibrate(np.array([raw_conf]))[0])
        direction_prob = float(torch.sigmoid(direction_logit).cpu().numpy()[0])
        
        ml_adjusted_score = int(np.clip(50 + predicted_return * 800, 1, 100))
        
        return MultiHorizonPrediction(
            horizon=horizon,
            ml_adjusted_score=ml_adjusted_score,
            predicted_return=predicted_return,
            confidence=calibrated_conf,
            direction_probability=direction_prob,
            model_source="neural_multi_horizon"
        )
    
    def predict_full_all(self, features: np.ndarray) -> Dict[str, MultiHorizonPrediction]:
        """
        Make full predictions for all horizons.
        
        Args:
            features: Feature vector (n_features,)
            
        Returns:
            Dict mapping horizon names to MultiHorizonPrediction objects
        """
        X = features.reshape(1, -1)
        self.model.eval()
        X_t = torch.FloatTensor(X).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(X_t)
        
        results = {}
        for horizon in self.config.horizons:
            pred, direction_logit, conf = outputs[horizon]
            
            predicted_return = float(pred.cpu().numpy()[0])
            raw_conf = float(conf.cpu().numpy()[0])
            calibrated_conf = float(self.calibrators[horizon].calibrate(np.array([raw_conf]))[0])
            direction_prob = float(torch.sigmoid(direction_logit).cpu().numpy()[0])
            
            ml_adjusted_score = int(np.clip(50 + predicted_return * 800, 1, 100))
            
            results[horizon] = MultiHorizonPrediction(
                horizon=horizon,
                ml_adjusted_score=ml_adjusted_score,
                predicted_return=predicted_return,
                confidence=calibrated_conf,
                direction_probability=direction_prob,
                model_source="neural_multi_horizon"
            )
        
        return results
    
    def incremental_update(
        self,
        X: np.ndarray,
        y_dict: Dict[str, np.ndarray],
        n_epochs: int = 5,
        learning_rate: Optional[float] = None,
        recalibrate: bool = True
    ) -> Dict:
        """
        Perform incremental learning from new market data for all horizons.
        
        Args:
            X: New feature samples (n_samples, n_features)
            y_dict: Dict mapping horizon names to target arrays
            n_epochs: Number of epochs to train
            learning_rate: Optional learning rate override
            recalibrate: Whether to recalibrate confidence after update
            
        Returns:
            Dict with update metrics
        """
        if len(X) == 0:
            return {"status": "skipped", "reason": "no samples"}
        
        if self.optimizer is None:
            self._init_optimizer()
        
        incremental_lr = learning_rate or (self.config.learning_rate * 0.1)
        original_lr = self.optimizer.param_groups[0]['lr']
        
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = incremental_lr
        
        X_t = torch.FloatTensor(X).to(self.device)
        y_tensors = {h: torch.FloatTensor(y).to(self.device) for h, y in y_dict.items()}
        y_directions = {h: (y > 0).float() for h, y in y_tensors.items()}
        
        batch_size = min(self.config.batch_size, len(X))
        n_batches = max(1, len(X) // batch_size)
        
        total_loss = 0.0
        total_batch_count = 0
        
        self.model.train()
        for epoch in range(n_epochs):
            epoch_loss = 0.0
            
            for batch_idx in range(n_batches):
                start = batch_idx * batch_size
                end = min(start + batch_size, len(X_t))
                batch_X = X_t[start:end]
                
                self.optimizer.zero_grad()
                outputs = self.model(batch_X)
                
                batch_loss = torch.tensor(0.0, device=self.device)
                for horizon in self.config.horizons:
                    if horizon not in y_tensors:
                        continue
                    
                    pred, direction_logit, conf = outputs[horizon]
                    batch_y = y_tensors[horizon][start:end]
                    batch_dir = y_directions[horizon][start:end]
                    
                    mse_loss = F.mse_loss(pred, batch_y)
                    bce_loss = F.binary_cross_entropy_with_logits(direction_logit, batch_dir)
                    horizon_loss = mse_loss + self.config.direction_loss_weight * bce_loss
                    
                    weight = self.config.horizon_loss_weights.get(horizon, 1.0)
                    batch_loss = batch_loss + weight * horizon_loss
                
                batch_loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 0.5)
                self.optimizer.step()
                
                epoch_loss += batch_loss.item()
                total_batch_count += 1
            
            total_loss += epoch_loss
        
        for param_group in self.optimizer.param_groups:
            param_group['lr'] = original_lr
        
        if recalibrate and len(X) >= 20:
            for horizon in self.config.horizons:
                if horizon in y_tensors:
                    self._calibrate_confidence_horizon(X_t, y_tensors[horizon], horizon)
        
        self._update_count += 1
        self._last_update_time = datetime.utcnow()
        
        self.model.eval()
        final_metrics = {}
        with torch.no_grad():
            outputs = self.model(X_t)
            for horizon in self.config.horizons:
                if horizon not in y_tensors:
                    continue
                pred, direction_logit, conf = outputs[horizon]
                y = y_tensors[horizon]
                y_dir = y_directions[horizon]
                
                mse = F.mse_loss(pred, y).item()
                dir_pred = (torch.sigmoid(direction_logit) > 0.5).float()
                dir_acc = (dir_pred == y_dir).float().mean().item()
                
                final_metrics[horizon] = {
                    "final_mse": mse,
                    "directional_accuracy": dir_acc
                }
        
        return {
            "status": "success",
            "n_samples": len(X),
            "n_epochs": n_epochs,
            "avg_loss": total_loss / max(1, total_batch_count),
            "horizon_metrics": final_metrics,
            "learning_rate_used": incremental_lr,
            "update_count": self._update_count,
            "recalibrated": recalibrate and len(X) >= 20
        }
    
    def save(self, name: str, version: str = "1.0.0") -> Path:
        """
        Save multi-horizon model to disk.
        
        Args:
            name: Model name
            version: Model version
            
        Returns:
            Path to saved model directory
        """
        model_path = self.MODEL_DIR / f"{name}_multi_horizon_{version}"
        model_path.mkdir(parents=True, exist_ok=True)
        
        torch.save(self.model.state_dict(), model_path / "model.pt")
        
        with open(model_path / "config.json", "w") as f:
            json.dump(self.config.to_dict(), f, indent=2)
        
        with open(model_path / "training_history.json", "w") as f:
            json.dump(self.training_history, f, indent=2)
        
        calibrators_dir = model_path / "calibrators"
        calibrators_dir.mkdir(exist_ok=True)
        for horizon, calibrator in self.calibrators.items():
            calibrator.save(calibrators_dir / f"{horizon}.pkl")
        
        metadata = {
            "update_count": self._update_count,
            "last_update_time": self._last_update_time.isoformat() if self._last_update_time else None,
            "best_val_loss": self.best_val_loss,
            "horizons": self.config.horizons,
            "model_type": "multi_horizon"
        }
        with open(model_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"Saved multi-horizon neural model to {model_path}")
        return model_path
    
    @classmethod
    def load(cls, name: str, version: str = "1.0.0") -> "MultiHorizonNeuralModel":
        """
        Load multi-horizon model from disk.
        
        Args:
            name: Model name
            version: Model version
            
        Returns:
            Loaded MultiHorizonNeuralModel instance
        """
        model_path = cls.MODEL_DIR / f"{name}_multi_horizon_{version}"
        
        with open(model_path / "config.json", "r") as f:
            config = MultiHorizonNeuralConfig.from_dict(json.load(f))
        
        instance = cls(config)
        
        state_dict = torch.load(model_path / "model.pt", map_location=instance.device, weights_only=False)
        instance.model.load_state_dict(state_dict)
        
        history_path = model_path / "training_history.json"
        if history_path.exists():
            with open(history_path, "r") as f:
                instance.training_history = json.load(f)
        
        calibrators_dir = model_path / "calibrators"
        if calibrators_dir.exists():
            for horizon in config.horizons:
                calibrator_path = calibrators_dir / f"{horizon}.pkl"
                if calibrator_path.exists():
                    instance.calibrators[horizon] = ConfidenceCalibrator.load(calibrator_path)
        
        metadata_path = model_path / "metadata.json"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                metadata = json.load(f)
                instance._update_count = metadata.get("update_count", 0)
                if metadata.get("last_update_time"):
                    instance._last_update_time = datetime.fromisoformat(metadata["last_update_time"])
                instance.best_val_loss = metadata.get("best_val_loss", float('inf'))
        
        logger.info(f"Loaded multi-horizon neural model from {model_path}")
        return instance
    
    @classmethod
    def save_model(cls, model: "MultiHorizonNeuralModel", name: str, version: str = "1.0.0") -> Path:
        """Class method to save a model instance."""
        return model.save(name, version)
    
    @classmethod
    def load_model(cls, name: str, version: str = "1.0.0") -> "MultiHorizonNeuralModel":
        """Class method to load a model from disk."""
        return cls.load(name, version)
