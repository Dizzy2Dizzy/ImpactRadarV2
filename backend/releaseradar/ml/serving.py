"""
ML prediction service with model loading and caching.

Loads active models and serves predictions for new events.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import numpy as np
from sqlalchemy import select
from sqlalchemy.orm import Session

from releaseradar.db.models import ModelRegistry, Event, EventScore
from releaseradar.ml.features import FeatureExtractor
from releaseradar.ml.schemas import EventFeatures, MLPrediction, ProbabilisticPrediction
from releaseradar.ml.training import ModelTrainer
from releaseradar.ml.event_type_families import get_event_family
from releaseradar.log_config import logger


class MLScoringService:
    """Serves ML predictions with model caching."""
    
    # Class-level cache for model availability to avoid repeated DB lookups
    # Format: {(event_type_family, horizon): model_id or None}
    _model_availability_cache: Dict[Tuple[str, str], Optional[int]] = {}
    
    def __init__(self, db: Session):
        self.db = db
        self.feature_extractor = FeatureExtractor(db)
        self._model_cache: Dict[str, ModelTrainer] = {}
    
    def get_active_model(self, horizon: str = "1d") -> Optional[ModelRegistry]:
        """
        Get active model from registry for specified horizon.
        
        Args:
            horizon: Time horizon ("1d", "5d", "20d")
            
        Returns:
            ModelRegistry object or None
        """
        model_name = f"xgboost_impact_{horizon}"
        
        model_record = self.db.execute(
            select(ModelRegistry)
            .where(ModelRegistry.name == model_name)
            .where(ModelRegistry.status == "active")
            .order_by(ModelRegistry.promoted_at.desc())
        ).scalar_one_or_none()
        
        return model_record
    
    def get_best_model_for_event(
        self, 
        event_type: str, 
        horizon: str = "1d"
    ) -> Tuple[Optional[ModelRegistry], str]:
        """
        Get the best available model for an event using hierarchical lookup with fallback.
        
        Strategy:
        1. Try family-specific model (e.g., "sec_8k" family)
        2. Fall back to global model (event_type_family="all")
        3. Fall back to None (will use deterministic scoring)
        
        CRITICAL: Always validates cached models are still active to prevent serving
        stale predictions from archived models.
        
        Args:
            event_type: Event type string (e.g., "sec_8k", "earnings")
            horizon: Time horizon ("1d", "5d", "20d")
            
        Returns:
            Tuple of (model_record, model_source) where:
            - model_record: ModelRegistry object or None
            - model_source: "family-specific" | "global" | "none"
        """
        # Determine event family
        event_type_family = get_event_family(event_type)
        
        # Check cache first
        cache_key = (event_type_family, horizon)
        if cache_key in self._model_availability_cache:
            cached_id = self._model_availability_cache[cache_key]
            if cached_id is None:
                # Cached negative result, try global
                global_cache_key = ("all", horizon)
                if global_cache_key in self._model_availability_cache:
                    global_id = self._model_availability_cache[global_cache_key]
                    if global_id is None:
                        return None, "none"
                    
                    # CRITICAL: Fetch global model and verify it's still active
                    global_model = self.db.execute(
                        select(ModelRegistry)
                        .where(ModelRegistry.id == global_id)
                        .where(ModelRegistry.status == "active")
                    ).scalar_one_or_none()
                    
                    if not global_model:
                        # Model was archived - invalidate cache and do fresh lookup
                        logger.warning(f"Cached global model {global_id} is no longer active, invalidating cache")
                        del self._model_availability_cache[global_cache_key]
                        # Fall through to fresh lookup below
                    else:
                        return global_model, "global"
            else:
                # CRITICAL: Fetch family model and verify it's still active
                family_model = self.db.execute(
                    select(ModelRegistry)
                    .where(ModelRegistry.id == cached_id)
                    .where(ModelRegistry.status == "active")
                ).scalar_one_or_none()
                
                if not family_model:
                    # Model was archived - invalidate cache and do fresh lookup
                    logger.warning(f"Cached family model {cached_id} is no longer active, invalidating cache")
                    del self._model_availability_cache[cache_key]
                    # Fall through to fresh lookup below
                else:
                    return family_model, "family-specific"
        
        # Step 1: Try exact family match (fresh DB lookup)
        family_model = self.db.execute(
            select(ModelRegistry)
            .where(ModelRegistry.event_type_family == event_type_family)
            .where(ModelRegistry.horizon == horizon)
            .where(ModelRegistry.status == "active")
            .order_by(ModelRegistry.promoted_at.desc())
        ).scalar_one_or_none()
        
        if family_model:
            # Update cache with active model
            self._model_availability_cache[cache_key] = family_model.id
            logger.debug(f"Using family-specific model for {event_type_family}/{horizon}")
            return family_model, "family-specific"
        
        # Cache negative result for family
        self._model_availability_cache[cache_key] = None
        
        # Step 2: Fall back to global model (fresh DB lookup)
        global_model = self.db.execute(
            select(ModelRegistry)
            .where(ModelRegistry.event_type_family == "all")
            .where(ModelRegistry.horizon == horizon)
            .where(ModelRegistry.status == "active")
            .order_by(ModelRegistry.promoted_at.desc())
        ).scalar_one_or_none()
        
        if global_model:
            # Update cache for global with active model
            global_cache_key = ("all", horizon)
            self._model_availability_cache[global_cache_key] = global_model.id
            logger.debug(f"Using global model for {event_type_family}/{horizon}")
            return global_model, "global"
        
        # Cache negative result for global
        global_cache_key = ("all", horizon)
        self._model_availability_cache[global_cache_key] = None
        
        # Step 3: No model available - use deterministic
        logger.debug(f"No ML model available for {event_type_family}/{horizon}, falling back to deterministic")
        return None, "none"
    
    def load_model(self, model_record: ModelRegistry) -> ModelTrainer:
        """
        Load model from disk with caching.
        
        Args:
            model_record: ModelRegistry database record
            
        Returns:
            Loaded ModelTrainer instance
        """
        cache_key = f"{model_record.name}:{model_record.version}"
        
        # Check cache
        if cache_key in self._model_cache:
            logger.debug(f"Using cached model {cache_key}")
            return self._model_cache[cache_key]
        
        # Load model
        logger.info(f"Loading model {cache_key} from {model_record.model_path}")
        
        # Extract horizon from model name
        horizon = model_record.name.split("_")[-1]
        
        trainer = ModelTrainer(model_type="xgboost", horizon=horizon)
        trainer.load_model(model_record.model_path)
        
        # Cache model
        self._model_cache[cache_key] = trainer
        
        return trainer
    
    def predict_single(
        self,
        event_id: int,
        horizon: str = "1d",
        confidence_threshold: float = 0.35,
        max_delta: int = 35,
        use_blending: bool = True
    ) -> Optional[MLPrediction]:
        """
        Generate ML prediction for a single event with optional blending.
        
        Uses hierarchical model lookup:
        1. Try family-specific model (e.g., "sec_8k")
        2. Fall back to global model (event_type_family="all")
        3. Return None if no model available (deterministic fallback)
        
        Args:
            event_id: Event ID to predict
            horizon: Time horizon for prediction
            confidence_threshold: Minimum confidence to return prediction (default 0.35)
            max_delta: Maximum allowed change from base score (default ±35 for more differentiation)
            use_blending: Whether to blend with base score (default True)
            
        Returns:
            MLPrediction with blended score and model provenance, or None if model not available/confident
        """
        # Get event to access base score and event_type
        event = self.db.execute(
            select(Event).where(Event.id == event_id)
        ).scalar_one_or_none()
        
        if not event:
            logger.warning(f"Event {event_id} not found")
            return None
        
        # Get best available model using hierarchical lookup
        model_record, model_source = self.get_best_model_for_event(event.event_type, horizon)
        
        # If no model available, return None (deterministic fallback)
        if not model_record or model_source == "none":
            logger.debug(f"No ML model available for event {event_id} ({event.event_type}), using deterministic scoring")
            return None
        
        # Get base score (deterministic score)
        base_score = event.impact_score
        
        # Check if EventScore exists (more refined scoring)
        event_score = self.db.execute(
            select(EventScore).where(EventScore.event_id == event_id)
        ).scalar_one_or_none()
        
        if event_score:
            base_score = event_score.final_score
        
        # Extract features
        features = self.feature_extractor.extract_features(event_id)
        if not features:
            logger.warning(f"Failed to extract features for event {event_id}")
            return None
        
        # Load model
        try:
            trainer = self.load_model(model_record)
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return None
        
        # Check if global model expects event_type_family feature
        # Only add it if model was trained with it
        if model_source == "global" and trainer.model is not None:
            try:
                model_features = trainer.model.get_booster().feature_names
                if model_features and "event_type_family" in model_features:
                    from releaseradar.ml.event_type_families import get_event_family, get_family_id
                    family = get_event_family(event.event_type)
                    family_id = get_family_id(family)
                    features.event_type_family = family_id
                    logger.debug(f"Added event_type_family={family_id} ({family}) for global model prediction")
            except Exception as e:
                logger.debug(f"Could not check model features: {e}")
        
        # Make prediction
        try:
            predicted_return = trainer.predict([features])[0]
            
            # Convert return to impact score (0-100)
            ml_score_raw = self._return_to_score(predicted_return)
            
            # Estimate confidence based on model metrics and feature quality
            ml_confidence = self._estimate_confidence(features, model_record)
            
            # Only return if confidence meets threshold
            if ml_confidence < confidence_threshold:
                logger.debug(f"ML confidence {ml_confidence:.2f} below threshold {confidence_threshold}")
                return None
            
            # Blend with base score to prevent wild swings
            ml_adjusted_score = ml_score_raw
            delta_applied = 0.0
            
            if use_blending:
                ml_adjusted_score, delta_applied = self.blend_with_base_score(
                    base_score=base_score,
                    ml_prediction=ml_score_raw,
                    confidence=ml_confidence,
                    max_delta=max_delta
                )
            
            prediction = MLPrediction(
                event_id=event_id,
                ml_adjusted_score=ml_adjusted_score,
                ml_confidence=ml_confidence,
                ml_model_version=f"{model_record.name}:{model_record.version}",
                model_source=model_source,
                base_score=base_score,
                ml_prediction_raw=ml_score_raw,
                delta_applied=delta_applied,
            )
            
            # Add horizon-specific return
            if horizon == "1d":
                prediction.predicted_return_1d = predicted_return
            elif horizon == "5d":
                prediction.predicted_return_5d = predicted_return
            elif horizon == "20d":
                prediction.predicted_return_20d = predicted_return
            
            logger.debug(f"ML prediction for event {event_id} ({event.event_type}): "
                        f"base={base_score}, raw_ml={ml_score_raw}, blended={ml_adjusted_score}, "
                        f"confidence={ml_confidence:.2f}, delta={delta_applied:.1f}, "
                        f"source={model_source}")
            
            return prediction
        
        except Exception as e:
            logger.error(f"Prediction failed for event {event_id}: {e}")
            return None
    
    def predict_batch(
        self,
        event_ids: List[int],
        horizon: str = "1d"
    ) -> List[MLPrediction]:
        """
        Generate ML predictions for multiple events.
        
        Args:
            event_ids: List of event IDs
            horizon: Time horizon for predictions
            
        Returns:
            List of MLPrediction objects
        """
        predictions = []
        
        for event_id in event_ids:
            pred = self.predict_single(event_id, horizon=horizon)
            if pred:
                predictions.append(pred)
        
        return predictions
    
    def blend_with_base_score(
        self,
        base_score: int,
        ml_prediction: float,
        confidence: float,
        max_delta: int = 20,
        min_confidence_threshold: float = 0.3
    ) -> Tuple[int, float]:
        """
        Blend ML prediction with base score using confidence weighting.
        
        This prevents the AI from wildly changing scores and maintains user trust
        by limiting adjustments based on model confidence.
        
        Args:
            base_score: Original deterministic impact score (0-100)
            ml_prediction: ML model prediction (0-100)
            confidence: Model confidence (0-1)
            max_delta: Maximum allowed change (default ±20)
            min_confidence_threshold: Below this, use base_score only (default 0.3)
        
        Returns:
            Tuple of (blended_score, delta_applied)
        """
        # If confidence is too low, use base score only
        if confidence < min_confidence_threshold:
            logger.debug(f"Confidence {confidence:.2f} below threshold {min_confidence_threshold}, "
                        f"using base score {base_score}")
            return base_score, 0.0
        
        # Calculate suggested delta
        delta = ml_prediction - base_score
        
        # Cap delta to max_delta range
        capped_delta = np.clip(delta, -max_delta, max_delta)
        
        # Weight by confidence (low confidence = less adjustment)
        weighted_delta = capped_delta * confidence
        
        # Apply to base score
        adjusted_score = base_score + weighted_delta
        
        # Clamp to valid range
        blended_score = int(np.clip(adjusted_score, 0, 100))
        
        logger.debug(f"Blending: base={base_score}, ml={ml_prediction:.1f}, "
                    f"confidence={confidence:.2f}, delta={weighted_delta:.1f}, "
                    f"result={blended_score}")
        
        return blended_score, weighted_delta
    
    def _return_to_score(self, predicted_return: float) -> int:
        """
        Convert predicted return to impact score (0-100).
        
        Scale:
        - 0% return → 50 (neutral)
        - +5% return → 90
        - -5% return → 10
        - ±10%+ → 100/0
        """
        # Scale return to score
        # Formula: score = 50 + (return * 800)
        # This maps -5% to 10, 0% to 50, +5% to 90
        score = 50 + (predicted_return * 800)
        
        # Clamp to [0, 100]
        score = max(0, min(100, int(score)))
        
        return score
    
    def _estimate_confidence(
        self,
        features: EventFeatures,
        model_record: ModelRegistry
    ) -> float:
        """
        Estimate prediction confidence based on model metrics, feature quality,
        and event-specific characteristics to produce varied confidences.
        
        Args:
            features: Event features
            model_record: Model registry record
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Base confidence from model's directional accuracy
        base_confidence = model_record.metrics.get("directional_accuracy", 0.5)
        
        # Adjust based on feature completeness
        feature_completeness = self._calculate_feature_completeness(features)
        
        # Add variance based on feature values to avoid all events having same confidence
        feature_variance = self._calculate_feature_variance(features)
        
        # Weighted average with feature variance for differentiation
        # This produces values in 0-1 range with more spread
        confidence = 0.5 * base_confidence + 0.3 * feature_completeness + 0.2 * feature_variance
        
        # Scale to produce variance in 0.40-0.90 range while preserving order
        # Low-quality predictions (confidence < 0.3 before scaling) will still be filtered
        confidence = max(0.25, min(0.95, confidence))
        
        return float(confidence)
    
    def _calculate_feature_variance(self, features: EventFeatures) -> float:
        """
        Calculate a variance factor based on feature values to differentiate events.
        
        This ensures different events get different confidences even when using
        the same model, by considering the actual feature values.
        
        Args:
            features: Event features
            
        Returns:
            Variance factor (0.0 to 1.0)
        """
        feature_dict = features.to_vector()
        
        # Create a deterministic variance from feature values
        variance_score = 0.0
        
        # Key features that contribute to variance
        key_features = [
            'volatility', 'avg_volume', 'base_score', 'sector_volatility',
            'days_since_last_event', 'market_cap', 'price', 'avg_daily_return'
        ]
        
        for i, key in enumerate(key_features):
            value = feature_dict.get(key, 0)
            if value and value != 0:
                # Normalize and add contribution with different weights
                normalized = (float(value) % 1.0) if abs(float(value)) < 10 else (float(value) / 100) % 1.0
                variance_score += normalized * (0.15 - i * 0.01)
        
        # Clamp to 0-1 range
        return max(0.0, min(1.0, abs(variance_score)))
    
    def _calculate_feature_completeness(self, features: EventFeatures) -> float:
        """
        Calculate what fraction of features are non-null.
        
        Args:
            features: Event features
            
        Returns:
            Completeness ratio (0.0 to 1.0)
        """
        feature_dict = features.to_vector()
        
        # Count non-zero/non-null features
        total_features = len(feature_dict)
        non_null_features = sum(1 for v in feature_dict.values() if v not in [0, 0.0, None])
        
        if total_features == 0:
            return 0.0
        
        return non_null_features / total_features
    
    def update_event_with_ml_score(self, event_id: int, horizon: str = "1d"):
        """
        Update event record with ML prediction.
        
        Args:
            event_id: Event to update
            horizon: Time horizon for prediction
        """
        prediction = self.predict_single(event_id, horizon=horizon)
        
        if not prediction:
            logger.debug(f"No ML prediction for event {event_id}")
            return
        
        # Update event
        event = self.db.execute(
            select(Event).where(Event.id == event_id)
        ).scalar_one_or_none()
        
        if event:
            event.ml_adjusted_score = prediction.ml_adjusted_score
            event.ml_confidence = prediction.ml_confidence
            event.ml_model_version = prediction.ml_model_version
            
            self.db.commit()
            logger.info(f"Updated event {event_id} with ML score {prediction.ml_adjusted_score}")
    
    @classmethod
    def clear_model_cache(cls):
        """
        Clear the model availability cache.
        
        This should be called when:
        - Models are retrained and new versions are promoted
        - Models are archived or status changes
        - Cache becomes stale or needs refresh
        
        This is a class method because the cache is shared across all instances.
        """
        cls._model_availability_cache.clear()
        logger.info("Cleared model availability cache")
    
    def predict_with_intervals(
        self,
        event_id: int,
        horizon: str = "1d",
        coverage_level: float = 0.80,
        incorporate_options_iv: bool = True
    ) -> Optional[ProbabilisticPrediction]:
        """
        Generate probabilistic prediction with uncertainty intervals.
        
        Uses quantile regression for interval predictions and optionally
        incorporates options-implied volatility to adjust interval width.
        
        Args:
            event_id: Event ID to predict
            horizon: Time horizon ("1d" or "5d")
            coverage_level: Target coverage level (0.80 or 0.90)
            incorporate_options_iv: Whether to widen/narrow intervals based on IV
            
        Returns:
            ProbabilisticPrediction with intervals, or None if prediction failed
        """
        if horizon not in ["1d", "5d"]:
            logger.warning(f"Horizon {horizon} not supported for probabilistic prediction, using 1d")
            horizon = "1d"
        
        event = self.db.execute(
            select(Event).where(Event.id == event_id)
        ).scalar_one_or_none()
        
        if not event:
            logger.warning(f"Event {event_id} not found")
            return None
        
        features = self.feature_extractor.extract_features(event_id)
        if not features:
            logger.warning(f"Failed to extract features for event {event_id}")
            return None
        
        try:
            from releaseradar.ml.probabilistic import QuantileRegressor, ConformalCalibrator
            
            quantile_model_dir = f"backend/models/probabilistic/quantile_{horizon}_latest"
            calibration_path = f"backend/models/calibration/conformal_{horizon}_latest.joblib"
            
            quantile_regressor = QuantileRegressor(horizon=horizon)
            conformal_calibrator = ConformalCalibrator(horizon=horizon)
            
            has_trained_model = False
            
            import os
            if os.path.exists(quantile_model_dir):
                try:
                    quantile_regressor.load(quantile_model_dir)
                    has_trained_model = True
                except Exception as e:
                    logger.debug(f"Could not load quantile model: {e}")
            
            if os.path.exists(calibration_path):
                try:
                    conformal_calibrator.load(calibration_path)
                except Exception as e:
                    logger.debug(f"Could not load calibration: {e}")
            
            if has_trained_model:
                quantile_pred = quantile_regressor.predict_single(features)
                
                lower_bound = quantile_pred.lower
                q25 = quantile_pred.q25
                median = quantile_pred.median
                q75 = quantile_pred.q75
                upper_bound = quantile_pred.upper
                interval_width = quantile_pred.confidence_width
            else:
                point_pred = self.predict_single(event_id, horizon=horizon)
                
                if point_pred and point_pred.predicted_return_1d is not None:
                    median = point_pred.predicted_return_1d if horizon == "1d" else (point_pred.predicted_return_5d or 0.0)
                else:
                    base_score = event.impact_score
                    median = (base_score - 50) / 800.0
                
                base_interval = 0.03 if horizon == "1d" else 0.06
                
                lower_bound = median - base_interval
                q25 = median - base_interval * 0.4
                q75 = median + base_interval * 0.4
                upper_bound = median + base_interval
                interval_width = base_interval * 2
            
            iv_adjustment = 0.0
            implied_volatility = None
            iv_percentile = None
            
            if incorporate_options_iv and features.has_options_data:
                implied_volatility = features.implied_volatility_atm
                iv_percentile = features.iv_percentile_30d
                
                if implied_volatility is not None and iv_percentile is not None:
                    if iv_percentile > 70:
                        iv_multiplier = 1.0 + (iv_percentile - 70) / 100.0
                        iv_adjustment = interval_width * (iv_multiplier - 1.0) / 2
                        lower_bound -= iv_adjustment
                        upper_bound += iv_adjustment
                        interval_width = upper_bound - lower_bound
                        logger.debug(f"High IV ({iv_percentile:.0f}%ile), widened interval by {iv_adjustment*100:.2f}%")
                    
                    elif iv_percentile < 30:
                        iv_multiplier = 0.85 + (iv_percentile / 100.0)
                        iv_adjustment = interval_width * (1.0 - iv_multiplier) / 2
                        lower_bound += iv_adjustment
                        upper_bound -= iv_adjustment
                        interval_width = upper_bound - lower_bound
                        iv_adjustment = -iv_adjustment
                        logger.debug(f"Low IV ({iv_percentile:.0f}%ile), narrowed interval by {abs(iv_adjustment)*100:.2f}%")
            
            if conformal_calibrator.calibration_quantiles:
                from releaseradar.ml.probabilistic.quantile_regressor import QuantilePrediction
                raw_pred = QuantilePrediction(
                    lower=lower_bound,
                    q25=q25,
                    median=median,
                    q75=q75,
                    upper=upper_bound,
                    confidence_width=interval_width
                )
                
                calibrated = conformal_calibrator.calibrate_intervals([raw_pred], coverage_level)
                if calibrated:
                    cal = calibrated[0]
                    lower_bound = cal.lower
                    upper_bound = cal.upper
                    interval_width = upper_bound - lower_bound
                    is_calibrated = True
                    calibration_adjustment = cal.calibration_adjustment
                else:
                    is_calibrated = False
                    calibration_adjustment = 0.0
            else:
                is_calibrated = False
                calibration_adjustment = 0.0
            
            prob_positive = None
            prob_negative = None
            prob_significant = None
            
            if lower_bound >= 0:
                prob_positive = 0.9
                prob_negative = 0.1
            elif upper_bound <= 0:
                prob_positive = 0.1
                prob_negative = 0.9
            else:
                ratio_above_zero = upper_bound / (upper_bound - lower_bound)
                prob_positive = min(0.9, max(0.1, ratio_above_zero))
                prob_negative = 1.0 - prob_positive
            
            significant_threshold = 0.02
            if abs(lower_bound) > significant_threshold or abs(upper_bound) > significant_threshold:
                prob_significant = min(0.95, (abs(median) / significant_threshold) * 0.5 + 0.3)
            else:
                prob_significant = max(0.05, abs(median) / significant_threshold * 0.3)
            
            confidence = 0.5
            if has_trained_model:
                confidence = 0.7
            if is_calibrated:
                confidence += 0.1
            if features.has_options_data:
                confidence += 0.05
            if features.has_price_history and features.has_event_stats:
                confidence += 0.1
            
            confidence = min(0.95, confidence)
            
            prediction = ProbabilisticPrediction(
                event_id=event_id,
                horizon=horizon,
                point_estimate=median,
                lower_bound=lower_bound,
                q25=q25,
                q75=q75,
                upper_bound=upper_bound,
                confidence_interval=interval_width,
                iqr=q75 - q25 if q75 is not None and q25 is not None else None,
                implied_volatility=implied_volatility,
                iv_percentile=iv_percentile,
                iv_adjustment=iv_adjustment,
                coverage_level=coverage_level,
                is_calibrated=is_calibrated,
                calibration_adjustment=calibration_adjustment,
                prediction_confidence=confidence,
                has_sufficient_data=features.has_price_history,
                prob_positive=prob_positive,
                prob_negative=prob_negative,
                prob_significant_move=prob_significant,
                model_version="v1.4-probabilistic"
            )
            
            logger.info(
                f"Probabilistic prediction for event {event_id} ({event.ticker}): "
                f"{prediction.format_interval()}, confidence={confidence:.2f}"
            )
            
            return prediction
        
        except Exception as e:
            logger.error(f"Probabilistic prediction failed for event {event_id}: {e}")
            return None
