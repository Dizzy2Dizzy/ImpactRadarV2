"""
Model retraining pipeline - orchestrates hierarchical training by event type family.

Implements:
- Global baseline models trained on all event types
- Per-family models trained when sufficient data exists
- Cohort discovery with sample and ticker diversity requirements
- Proper model registration with family and horizon metadata
"""

import os
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy import select, and_, func

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))

from releaseradar.db.models import Event, EventOutcome, ModelFeature, ModelRegistry
from releaseradar.db.session import get_db_transaction
from releaseradar.ml.training import ModelTrainer
from releaseradar.ml.schemas import TrainingData, EventFeatures, ModelMetrics
from releaseradar.ml.event_type_families import (
    get_event_family, 
    get_family_display_name,
    get_family_id,
    MIN_SAMPLES_PRODUCTION,
    MIN_SAMPLES_EXPERIMENTAL,
)
from releaseradar.ml.label_filter import filter_overlapping_events, get_overlap_statistics
from releaseradar.ml.feature_store.registry import FeatureRegistry
from releaseradar.ml.ensembles.stacked_impact import (
    StackedImpactEnsemble,
    StackedEnsembleConfig,
    EnsembleMetrics,
)
from releaseradar.log_config import logger


# Minimum unique tickers required for training (ticker diversity)
MIN_UNIQUE_TICKERS = 75


@dataclass
class CohortInfo:
    """Statistics for a training cohort (event_type_family, horizon)."""
    family: str
    horizon: str
    sample_count: int
    unique_tickers: int
    status: str  # "production", "experimental", "insufficient"
    reason: Optional[str] = None


class StoredFeatures:
    """Wrapper for pre-vectorized features from database."""
    
    def __init__(self, features_dict: dict):
        self._features = features_dict
    
    def to_vector(self) -> dict:
        """Return the stored feature vector."""
        return self._features


class HierarchicalRetrainingPipeline:
    """Orchestrates hierarchical model retraining by event type family."""
    
    TRAINING_WINDOW_DAYS = 365  # 12 months
    IMPROVEMENT_THRESHOLD = 0.02  # 2% improvement in directional accuracy required
    
    STACKED_ENSEMBLE_HORIZONS = ["1d", "5d"]
    
    def __init__(
        self, 
        horizon: str = "1d", 
        model_type: str = "xgboost",
        train_stacked_ensemble: bool = True
    ):
        self.horizon = horizon
        self.model_type = model_type
        self.train_stacked_ensemble = train_stacked_ensemble and horizon in self.STACKED_ENSEMBLE_HORIZONS
        
        self._feature_registry = FeatureRegistry()
    
    def discover_cohorts(self, db) -> List[CohortInfo]:
        """
        Discover available training cohorts with sample and ticker counts.
        
        Args:
            db: Database session
            
        Returns:
            List of CohortInfo objects with statistics
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.TRAINING_WINDOW_DAYS)
        
        logger.info(f"Discovering cohorts for horizon={self.horizon}, cutoff_date={cutoff_date.date()}")
        
        # Fetch all labeled events with features for this horizon
        results = db.execute(
            select(ModelFeature, Event)
            .join(Event, ModelFeature.event_id == Event.id)
            .join(EventOutcome, and_(
                ModelFeature.event_id == EventOutcome.event_id,
                ModelFeature.horizon == EventOutcome.horizon
            ))
            .where(ModelFeature.horizon == self.horizon)
            .where(ModelFeature.extracted_at >= cutoff_date)
        ).all()
        
        logger.info(f"Found {len(results)} total labeled samples for {self.horizon}")
        
        # Group by event_type_family
        family_stats: Dict[str, Dict] = {}
        
        for model_feature, event in results:
            # Get family from event_type (stored in ModelFeature)
            event_type = model_feature.event_type or event.event_type
            family = get_event_family(event_type)
            
            if family not in family_stats:
                family_stats[family] = {
                    "count": 0,
                    "tickers": set()
                }
            
            family_stats[family]["count"] += 1
            family_stats[family]["tickers"].add(event.ticker)
        
        # Convert to CohortInfo objects with status classification
        cohorts = []
        
        for family, stats in family_stats.items():
            sample_count = stats["count"]
            unique_tickers = len(stats["tickers"])
            
            # Determine status based on thresholds
            if sample_count >= MIN_SAMPLES_PRODUCTION and unique_tickers >= MIN_UNIQUE_TICKERS:
                status = "production"
                reason = None
            elif sample_count >= MIN_SAMPLES_EXPERIMENTAL and unique_tickers >= MIN_UNIQUE_TICKERS:
                status = "experimental"
                reason = None
            else:
                status = "insufficient"
                reasons = []
                if sample_count < MIN_SAMPLES_EXPERIMENTAL:
                    reasons.append(f"only {sample_count} samples (need ≥{MIN_SAMPLES_EXPERIMENTAL})")
                if unique_tickers < MIN_UNIQUE_TICKERS:
                    reasons.append(f"only {unique_tickers} tickers (need ≥{MIN_UNIQUE_TICKERS})")
                reason = ", ".join(reasons)
            
            cohort = CohortInfo(
                family=family,
                horizon=self.horizon,
                sample_count=sample_count,
                unique_tickers=unique_tickers,
                status=status,
                reason=reason
            )
            cohorts.append(cohort)
        
        # Sort by sample count descending
        cohorts.sort(key=lambda c: c.sample_count, reverse=True)
        
        # Log cohort summary
        logger.info(f"\n{'='*80}")
        logger.info(f"Cohort Discovery Summary for {self.horizon} horizon:")
        logger.info(f"{'='*80}")
        
        for cohort in cohorts:
            display_name = get_family_display_name(cohort.family)
            status_emoji = {
                "production": "✓",
                "experimental": "⚠",
                "insufficient": "✗"
            }[cohort.status]
            
            logger.info(
                f"{status_emoji} {display_name:40s} | "
                f"Samples: {cohort.sample_count:4d} | "
                f"Tickers: {cohort.unique_tickers:3d} | "
                f"Status: {cohort.status:13s}"
                f"{' | Reason: ' + cohort.reason if cohort.reason else ''}"
            )
        
        logger.info(f"{'='*80}\n")
        
        return cohorts
    
    def get_training_data_for_family(
        self, 
        db, 
        event_type_family: Optional[str] = None,
        filter_overlaps: bool = True
    ) -> Optional[TrainingData]:
        """
        Fetch training data for a specific event type family or all families.
        
        Args:
            db: Database session
            event_type_family: Family to filter by, or None for all families (global model)
            filter_overlaps: If True, filter out events with confounding overlaps (same ticker ±days)
            
        Returns:
            TrainingData object or None if insufficient data
        """
        cutoff_date = datetime.utcnow() - timedelta(days=self.TRAINING_WINDOW_DAYS)
        
        # Build query
        query = (
            select(ModelFeature, EventOutcome, Event)
            .join(EventOutcome, and_(
                ModelFeature.event_id == EventOutcome.event_id,
                ModelFeature.horizon == EventOutcome.horizon
            ))
            .join(Event, ModelFeature.event_id == Event.id)
            .where(ModelFeature.horizon == self.horizon)
            .where(ModelFeature.extracted_at >= cutoff_date)
        )
        
        # Fetch all results
        results = db.execute(query).all()
        
        # Filter by family if specified
        if event_type_family is not None and event_type_family != "all":
            filtered_results = []
            for model_feature, event_outcome, event in results:
                event_type = model_feature.event_type or event.event_type
                family = get_event_family(event_type)
                if family == event_type_family:
                    filtered_results.append((model_feature, event_outcome, event))
            results = filtered_results
        
        if len(results) == 0:
            logger.warning(
                f"No training data for family={event_type_family}, horizon={self.horizon}"
            )
            return None
        
        # Apply overlap filtering to remove events with confounding overlaps
        if filter_overlaps:
            # Build list of (event_id, ticker, occurred_at) for filtering
            event_data = [(event.id, event.ticker, event.occurred_at) for _, _, event in results]
            
            # Log pre-filter stats
            pre_filter_count = len(results)
            
            # Filter and get clean event IDs
            clean_events = filter_overlapping_events(event_data)
            clean_event_ids = {event_id for event_id, _, _ in clean_events}
            
            # Filter results to keep only clean events
            results = [(mf, eo, e) for mf, eo, e in results if e.id in clean_event_ids]
            
            # Log filtering stats
            removed = pre_filter_count - len(results)
            if removed > 0:
                overlap_rate = removed / pre_filter_count
                logger.info(
                    f"Overlap filtering: removed {removed} of {pre_filter_count} events ({overlap_rate:.1%})"
                )
        
        if len(results) == 0:
            logger.warning(
                f"No training data remaining after overlap filtering for family={event_type_family}"
            )
            return None
        
        # Convert to EventFeatures and outcomes
        features_list = []
        outcomes_list = []
        
        for model_feature, event_outcome, event in results:
            # Use pre-vectorized features from database
            features_dict = model_feature.features.copy()
            
            # For global models, add event_type_family as a numeric feature
            if event_type_family == "all" or event_type_family is None:
                event_type = model_feature.event_type or event.event_type
                family = get_event_family(event_type)
                features_dict["event_type_family"] = get_family_id(family)
            
            feature_obj = StoredFeatures(features_dict)
            features_list.append(feature_obj)
            
            # Outcome as decimal (convert from percentage)
            outcomes_list.append(event_outcome.return_pct / 100)
        
        training_data = TrainingData(
            features=features_list,
            outcomes=outcomes_list,
            horizon=self.horizon,
            n_samples=len(features_list),
            feature_version="v1.1",  # Updated feature version
        )
        
        family_str = event_type_family or "all families"
        logger.info(
            f"Prepared training data for {family_str}: "
            f"{training_data.n_samples} samples, {self.horizon} horizon"
        )
        
        return training_data
    
    def train_model(
        self, 
        training_data: TrainingData,
        event_type_family: str
    ) -> Tuple[Optional[ModelTrainer], Optional[ModelMetrics]]:
        """
        Train model on provided data.
        
        Args:
            training_data: TrainingData object
            event_type_family: Family identifier (or "all" for global)
            
        Returns:
            Tuple of (trained_model, metrics) or (None, None) if training fails
        """
        trainer = ModelTrainer(model_type=self.model_type, horizon=self.horizon)
        
        try:
            metrics = trainer.train(training_data)
            
            logger.info(
                f"Model training complete for {event_type_family}. "
                f"MAE={metrics.mae:.4f}, R²={metrics.r2:.4f}, "
                f"Directional Accuracy={metrics.directional_accuracy:.2%}"
            )
            
            return trainer, metrics
        
        except Exception as e:
            logger.error(f"Model training failed for {event_type_family}: {e}")
            return None, None
    
    def register_model(
        self,
        db,
        trainer: ModelTrainer,
        metrics: ModelMetrics,
        event_type_family: str,
        status: str,
    ) -> Optional[ModelRegistry]:
        """
        Register trained model in database.
        
        Args:
            db: Database session
            trainer: Trained ModelTrainer
            metrics: Model performance metrics
            event_type_family: Event family (or "all" for global)
            status: "active" or "staging"
            
        Returns:
            ModelRegistry object or None if registration fails
        """
        # Generate model name
        if event_type_family == "all":
            model_name = f"{self.model_type}_impact_{self.horizon}_global"
        else:
            model_name = f"{self.model_type}_impact_{self.horizon}_{event_type_family}"
        
        # Check for existing models with same family and horizon (regardless of name)
        # This ensures ALL active models for a family+horizon are archived when a new one is promoted,
        # regardless of naming conventions (e.g., old "xgboost_impact_1d" vs new "xgboost_impact_1d_sec_8k")
        existing_models = db.execute(
            select(ModelRegistry)
            .where(ModelRegistry.event_type_family == event_type_family)
            .where(ModelRegistry.horizon == self.horizon)
            .order_by(ModelRegistry.trained_at.desc())
        ).scalars().all()
        
        # Generate version number
        if existing_models:
            latest = existing_models[0]
            major, minor, patch = latest.version.split(".")
            new_version = f"{major}.{minor}.{int(patch) + 1}"
        else:
            new_version = "1.0.0"
        
        # Save model to disk
        try:
            model_path = trainer.save_model(new_version)
        except Exception as e:
            logger.error(f"Failed to save model {model_name}: {e}")
            return None
        
        # Create registry entry
        new_model = ModelRegistry(
            name=model_name,
            version=new_version,
            event_type_family=event_type_family,
            horizon=self.horizon,
            status=status,
            model_path=model_path,
            metrics={
                "mae": metrics.mae,
                "rmse": metrics.rmse,
                "r2": metrics.r2,
                "directional_accuracy": metrics.directional_accuracy,
                "sharpe_ratio": metrics.sharpe_ratio,
                "max_error": metrics.max_error,
                "n_train": metrics.n_train,
                "n_test": metrics.n_test,
                "feature_importance": metrics.feature_importance,
            },
            feature_version="v1.0",
            trained_at=datetime.utcnow(),
        )
        
        # If promoting to active, archive previous active models for this family
        if status == "active":
            for existing in existing_models:
                if existing.status == "active":
                    existing.status = "archived"
                    logger.info(
                        f"Archived previous active model: {existing.name} v{existing.version}"
                    )
            
            new_model.promoted_at = datetime.utcnow()
        
        db.add(new_model)
        db.commit()
        
        logger.info(
            f"Registered model: {model_name} v{new_version} "
            f"(family={event_type_family}, horizon={self.horizon}, status={status})"
        )
        
        return new_model
    
    def train_global_model(self, db) -> dict:
        """
        Train global baseline model using all event types.
        
        Args:
            db: Database session
            
        Returns:
            Stats dict
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Training GLOBAL baseline model for {self.horizon} horizon")
        logger.info(f"{'='*80}\n")
        
        stats = {
            "trained": False,
            "registered": False,
            "model_name": None,
            "version": None,
            "metrics": None,
            "error": None,
        }
        
        # Get training data for all families
        training_data = self.get_training_data_for_family(db, event_type_family="all")
        
        if training_data is None:
            stats["error"] = "insufficient_data"
            logger.warning("Skipping global model - insufficient data")
            return stats
        
        # Train model
        trainer, metrics = self.train_model(training_data, event_type_family="all")
        
        if trainer is None or metrics is None:
            stats["error"] = "training_failed"
            return stats
        
        stats["trained"] = True
        stats["metrics"] = {
            "mae": metrics.mae,
            "rmse": metrics.rmse,
            "r2": metrics.r2,
            "directional_accuracy": metrics.directional_accuracy,
            "n_train": metrics.n_train,
            "n_test": metrics.n_test,
        }
        
        # Register model (always as active - it's the global fallback)
        new_model = self.register_model(
            db, trainer, metrics, 
            event_type_family="all",
            status="active"
        )
        
        if new_model:
            stats["registered"] = True
            stats["model_name"] = new_model.name
            stats["version"] = new_model.version
        else:
            stats["error"] = "registration_failed"
        
        return stats
    
    def train_family_model(self, db, cohort: CohortInfo) -> dict:
        """
        Train family-specific model.
        
        Args:
            db: Database session
            cohort: CohortInfo for this family
            
        Returns:
            Stats dict
        """
        display_name = get_family_display_name(cohort.family)
        
        logger.info(f"\n{'-'*80}")
        logger.info(
            f"Training {cohort.status.upper()} model: {display_name} "
            f"({cohort.sample_count} samples, {cohort.unique_tickers} tickers)"
        )
        logger.info(f"{'-'*80}\n")
        
        stats = {
            "family": cohort.family,
            "trained": False,
            "registered": False,
            "model_name": None,
            "version": None,
            "status": cohort.status,
            "metrics": None,
            "error": None,
        }
        
        # Get training data for this family
        training_data = self.get_training_data_for_family(db, event_type_family=cohort.family)
        
        if training_data is None:
            stats["error"] = "no_data"
            return stats
        
        # Train model
        trainer, metrics = self.train_model(training_data, event_type_family=cohort.family)
        
        if trainer is None or metrics is None:
            stats["error"] = "training_failed"
            return stats
        
        stats["trained"] = True
        stats["metrics"] = {
            "mae": metrics.mae,
            "rmse": metrics.rmse,
            "r2": metrics.r2,
            "directional_accuracy": metrics.directional_accuracy,
            "n_train": metrics.n_train,
            "n_test": metrics.n_test,
        }
        
        # Determine status for registration
        # Production models (≥150 samples): active
        # Experimental models (50-149 samples): staging
        registration_status = "active" if cohort.status == "production" else "staging"
        
        # Register model
        new_model = self.register_model(
            db, trainer, metrics,
            event_type_family=cohort.family,
            status=registration_status
        )
        
        if new_model:
            stats["registered"] = True
            stats["model_name"] = new_model.name
            stats["version"] = new_model.version
        else:
            stats["error"] = "registration_failed"
        
        return stats
    
    def train_stacked_ensemble(
        self, 
        db, 
        baseline_metrics: Optional[Dict] = None
    ) -> dict:
        """
        Train stacked ensemble model combining XGBoost, LightGBM, and topology.
        
        Args:
            db: Database session
            baseline_metrics: Baseline XGBoost metrics for comparison
            
        Returns:
            Stats dict with ensemble training results
        """
        logger.info(f"\n{'='*80}")
        logger.info(f"Training STACKED ENSEMBLE model for {self.horizon} horizon")
        logger.info(f"{'='*80}\n")
        
        stats = {
            "trained": False,
            "registered": False,
            "model_name": None,
            "version": None,
            "metrics": None,
            "improvement_over_baseline": None,
            "feature_version": self._feature_registry.CURRENT_VERSION,
            "error": None,
        }
        
        training_data = self.get_training_data_for_family(db, event_type_family="all")
        
        if training_data is None:
            stats["error"] = "insufficient_data"
            logger.warning("Skipping stacked ensemble - insufficient data")
            return stats
        
        try:
            config = StackedEnsembleConfig.for_horizon(self.horizon)
            ensemble = StackedImpactEnsemble(config=config)
            
            metrics = ensemble.train(training_data, test_size=0.2)
            
            stats["trained"] = True
            stats["metrics"] = {
                "mae": metrics.mae,
                "rmse": metrics.rmse,
                "r2": metrics.r2,
                "directional_accuracy": metrics.directional_accuracy,
                "xgb_weight": metrics.xgb_weight,
                "lgb_weight": metrics.lgb_weight,
                "topology_impact": metrics.topology_impact,
                "n_train": metrics.n_train,
                "n_test": metrics.n_test,
            }
            
            if baseline_metrics:
                baseline_da = baseline_metrics.get("directional_accuracy", 0.5)
                improvement = metrics.directional_accuracy - baseline_da
                stats["improvement_over_baseline"] = improvement
                
                logger.info(
                    f"Ensemble vs XGBoost baseline: "
                    f"{improvement:+.2%} improvement in directional accuracy"
                )
            
            self._feature_registry.store_feature_importance(
                importance_dict=metrics.feature_importance,
                model_name="stacked_ensemble",
                model_version="1.0.0",
                horizon=self.horizon,
            )
            
            new_model = self.register_stacked_ensemble(
                db, ensemble, metrics,
                status="active" if stats.get("improvement_over_baseline", 0) > 0 else "staging"
            )
            
            if new_model:
                stats["registered"] = True
                stats["model_name"] = new_model.name
                stats["version"] = new_model.version
            else:
                stats["error"] = "registration_failed"
            
        except Exception as e:
            logger.error(f"Stacked ensemble training failed: {e}")
            stats["error"] = str(e)
        
        return stats
    
    def register_stacked_ensemble(
        self,
        db,
        ensemble: StackedImpactEnsemble,
        metrics: EnsembleMetrics,
        status: str = "staging"
    ) -> Optional[ModelRegistry]:
        """
        Register trained stacked ensemble in database.
        
        Args:
            db: Database session
            ensemble: Trained StackedImpactEnsemble
            metrics: Ensemble performance metrics
            status: "active" or "staging"
            
        Returns:
            ModelRegistry object or None if registration fails
        """
        model_name = f"stacked_ensemble_impact_{self.horizon}"
        
        existing_models = db.execute(
            select(ModelRegistry)
            .where(ModelRegistry.name == model_name)
            .order_by(ModelRegistry.trained_at.desc())
        ).scalars().all()
        
        if existing_models:
            latest = existing_models[0]
            major, minor, patch = latest.version.split(".")
            new_version = f"{major}.{minor}.{int(patch) + 1}"
        else:
            new_version = "1.0.0"
        
        try:
            model_path = ensemble.save(new_version)
        except Exception as e:
            logger.error(f"Failed to save stacked ensemble: {e}")
            return None
        
        new_model = ModelRegistry(
            name=model_name,
            version=new_version,
            event_type_family="all",
            horizon=self.horizon,
            status=status,
            model_path=model_path,
            metrics=metrics.to_dict(),
            feature_version=self._feature_registry.CURRENT_VERSION,
            trained_at=datetime.utcnow(),
        )
        
        if status == "active":
            for existing in existing_models:
                if existing.status == "active":
                    existing.status = "archived"
                    logger.info(
                        f"Archived previous stacked ensemble: {existing.name} v{existing.version}"
                    )
            
            new_model.promoted_at = datetime.utcnow()
        
        db.add(new_model)
        db.commit()
        
        logger.info(
            f"Registered stacked ensemble: {model_name} v{new_version} "
            f"(horizon={self.horizon}, status={status})"
        )
        
        return new_model
    
    def run(self) -> dict:
        """
        Execute complete hierarchical training pipeline.
        
        Returns:
            Complete pipeline statistics
        """
        with get_db_transaction() as db:
            results = {
                "horizon": self.horizon,
                "feature_version": self._feature_registry.CURRENT_VERSION,
                "global_model": None,
                "stacked_ensemble": None,
                "family_models": [],
                "cohorts_discovered": 0,
                "cohorts_trained": 0,
                "cohorts_skipped": 0,
            }
            
            cohorts = self.discover_cohorts(db)
            results["cohorts_discovered"] = len(cohorts)
            
            logger.info(f"\n{'#'*80}")
            logger.info(f"# PHASE 1: GLOBAL BASELINE MODEL")
            logger.info(f"{'#'*80}\n")
            
            global_stats = self.train_global_model(db)
            results["global_model"] = global_stats
            
            if self.train_stacked_ensemble:
                logger.info(f"\n{'#'*80}")
                logger.info(f"# PHASE 2: STACKED ENSEMBLE MODEL")
                logger.info(f"{'#'*80}\n")
                
                baseline_metrics = global_stats.get("metrics")
                ensemble_stats = self.train_stacked_ensemble(db, baseline_metrics)
                results["stacked_ensemble"] = ensemble_stats
            
            logger.info(f"\n{'#'*80}")
            logger.info(f"# PHASE 3: PER-FAMILY MODELS")
            logger.info(f"{'#'*80}\n")
            
            for cohort in cohorts:
                if cohort.status == "insufficient":
                    display_name = get_family_display_name(cohort.family)
                    logger.info(
                        f"✗ Skipping {display_name}: {cohort.reason}"
                    )
                    results["cohorts_skipped"] += 1
                    results["family_models"].append({
                        "family": cohort.family,
                        "status": "skipped",
                        "reason": cohort.reason,
                    })
                else:
                    family_stats = self.train_family_model(db, cohort)
                    results["family_models"].append(family_stats)
                    if family_stats["trained"]:
                        results["cohorts_trained"] += 1
            
            return results


def main():
    """Entry point for scheduled job."""
    logger.info("\n" + "="*80)
    logger.info("HIERARCHICAL MODEL RETRAINING PIPELINE (with Stacked Ensemble)")
    logger.info("="*80 + "\n")
    
    all_results = {}
    
    for horizon in ["1d", "5d", "20d"]:
        logger.info(f"\n{'█'*80}")
        logger.info(f"█ HORIZON: {horizon}")
        logger.info(f"{'█'*80}\n")
        
        pipeline = HierarchicalRetrainingPipeline(
            horizon=horizon, 
            model_type="xgboost",
            train_stacked_ensemble=True  # Enable stacked ensemble for 1d/5d
        )
        results = pipeline.run()
        
        all_results[horizon] = results
    
    logger.info(f"\n{'='*80}")
    logger.info("FINAL SUMMARY")
    logger.info(f"{'='*80}\n")
    
    for horizon, results in all_results.items():
        global_ok = "✓" if results["global_model"]["trained"] else "✗"
        
        logger.info(f"{horizon} horizon (Feature Version: {results.get('feature_version', 'N/A')}):")
        logger.info(f"  Global model: {global_ok}")
        
        if results.get("stacked_ensemble"):
            ensemble = results["stacked_ensemble"]
            ensemble_ok = "✓" if ensemble.get("trained") else "✗"
            improvement = ensemble.get("improvement_over_baseline")
            improvement_str = f" ({improvement:+.2%})" if improvement is not None else ""
            logger.info(f"  Stacked Ensemble: {ensemble_ok}{improvement_str}")
            
            if ensemble.get("metrics"):
                metrics = ensemble["metrics"]
                logger.info(f"    - Directional Accuracy: {metrics['directional_accuracy']:.2%}")
                logger.info(f"    - XGB Weight: {metrics.get('xgb_weight', 0):.2%}")
                lgb_weight = metrics.get('lgb_weight')
                if lgb_weight:
                    logger.info(f"    - LGB Weight: {lgb_weight:.2%}")
                logger.info(f"    - Topology Impact: {metrics.get('topology_impact', 0):.4f}")
        
        logger.info(f"  Cohorts discovered: {results['cohorts_discovered']}")
        logger.info(f"  Family models trained: {results['cohorts_trained']}")
        logger.info(f"  Family models skipped: {results['cohorts_skipped']}")
        
        trained_families = [
            fm for fm in results["family_models"] 
            if fm.get("trained", False)
        ]
        
        if trained_families:
            logger.info(f"  Trained families:")
            for fm in trained_families:
                status_label = "PRODUCTION" if fm["status"] == "production" else "EXPERIMENTAL"
                logger.info(
                    f"    - {get_family_display_name(fm['family'])} "
                    f"[{status_label}] v{fm['version']}"
                )
        
        logger.info("")
    
    logger.info("="*80)
    logger.info("Retraining pipeline complete!")
    logger.info("="*80 + "\n")
    
    sys.exit(0)


if __name__ == "__main__":
    main()
