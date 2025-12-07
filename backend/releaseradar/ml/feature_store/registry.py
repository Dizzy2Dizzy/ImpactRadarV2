"""
Feature Registry for Impact Radar ML System.

Manages feature definitions, versions, and importance scores across ML models.
Provides a centralized catalog of all features used in the prediction pipeline.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from enum import Enum
import json

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from releaseradar.log_config import logger


class FeatureType(str, Enum):
    """Feature data types."""
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    BINARY = "binary"
    ORDINAL = "ordinal"
    TEXT = "text"


class ExtractionMethod(str, Enum):
    """How the feature is extracted."""
    DIRECT = "direct"  # Directly from event/score data
    COMPUTED = "computed"  # Computed from other features
    MARKET = "market"  # From market data (prices, volatility)
    TOPOLOGY = "topology"  # From topological data analysis
    SENTIMENT = "sentiment"  # From sentiment analysis
    HISTORICAL = "historical"  # From historical aggregates


@dataclass
class FeatureDefinition:
    """Definition of a single feature."""
    name: str
    feature_type: FeatureType
    extraction_method: ExtractionMethod
    description: str
    default_value: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    dependencies: List[str] = field(default_factory=list)
    is_required: bool = False
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "feature_type": self.feature_type.value,
            "extraction_method": self.extraction_method.value,
            "description": self.description,
            "default_value": self.default_value,
            "min_value": self.min_value,
            "max_value": self.max_value,
            "dependencies": self.dependencies,
            "is_required": self.is_required,
            "created_at": self.created_at.isoformat(),
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "FeatureDefinition":
        return cls(
            name=data["name"],
            feature_type=FeatureType(data["feature_type"]),
            extraction_method=ExtractionMethod(data["extraction_method"]),
            description=data["description"],
            default_value=data.get("default_value"),
            min_value=data.get("min_value"),
            max_value=data.get("max_value"),
            dependencies=data.get("dependencies", []),
            is_required=data.get("is_required", False),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else datetime.utcnow(),
        )


@dataclass
class FeatureVersion:
    """Versioned snapshot of the feature schema."""
    version: str
    features: List[FeatureDefinition]
    created_at: datetime = field(default_factory=datetime.utcnow)
    description: str = ""
    is_active: bool = True
    
    @property
    def feature_count(self) -> int:
        return len(self.features)
    
    @property
    def feature_names(self) -> List[str]:
        return [f.name for f in self.features]
    
    def to_dict(self) -> Dict:
        return {
            "version": self.version,
            "features": [f.to_dict() for f in self.features],
            "created_at": self.created_at.isoformat(),
            "description": self.description,
            "is_active": self.is_active,
            "feature_count": self.feature_count,
        }


@dataclass
class FeatureImportance:
    """Feature importance scores from a trained model."""
    feature_name: str
    importance_score: float
    model_name: str
    model_version: str
    horizon: str
    computed_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict:
        return {
            "feature_name": self.feature_name,
            "importance_score": self.importance_score,
            "model_name": self.model_name,
            "model_version": self.model_version,
            "horizon": self.horizon,
            "computed_at": self.computed_at.isoformat(),
        }


class FeatureRegistry:
    """
    Central registry for feature definitions and versions.
    
    Manages:
    - Feature definitions (name, type, extraction method)
    - Feature versioning (v1.0, v1.1, etc.)
    - Feature importance scores from models
    - Feature metadata and documentation
    """
    
    CURRENT_VERSION = "v1.3"  # Current feature schema version
    
    def __init__(self, db: Optional[Session] = None):
        self.db = db
        self._versions: Dict[str, FeatureVersion] = {}
        self._importance_scores: Dict[str, List[FeatureImportance]] = {}
        self._initialize_base_features()
    
    def _initialize_base_features(self):
        """Initialize feature definitions for all versions."""
        
        # v1.0 - Base features
        v1_0_features = self._get_v1_0_features()
        self._versions["v1.0"] = FeatureVersion(
            version="v1.0",
            features=v1_0_features,
            description="Base feature set with deterministic scoring and market context",
            is_active=False,
        )
        
        # v1.1 - Enhanced features (volatility, sector momentum, regime)
        v1_1_features = v1_0_features + self._get_v1_1_features()
        self._versions["v1.1"] = FeatureVersion(
            version="v1.1",
            features=v1_1_features,
            description="Enhanced with volatility term structure, sector momentum, market regime",
            is_active=False,
        )
        
        # v1.2 - Topology features
        v1_2_features = v1_1_features + self._get_v1_2_features()
        self._versions["v1.2"] = FeatureVersion(
            version="v1.2",
            features=v1_2_features,
            description="Added correlation clustering and regime detection topology features",
            is_active=False,
        )
        
        # v1.3 - Persistent homology features (current)
        v1_3_features = v1_2_features + self._get_v1_3_features()
        self._versions["v1.3"] = FeatureVersion(
            version="v1.3",
            features=v1_3_features,
            description="Added persistent homology features (Betti numbers, persistence entropy)",
            is_active=True,
        )
        
        logger.info(f"Feature Registry initialized with {len(self._versions)} versions, current: {self.CURRENT_VERSION}")
    
    def _get_v1_0_features(self) -> List[FeatureDefinition]:
        """Base feature definitions (v1.0)."""
        return [
            FeatureDefinition(
                name="base_score",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.DIRECT,
                description="Deterministic base impact score (0-100)",
                min_value=0,
                max_value=100,
                is_required=True,
            ),
            FeatureDefinition(
                name="context_score",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.COMPUTED,
                description="Context-adjusted impact score",
                min_value=0,
                max_value=100,
            ),
            FeatureDefinition(
                name="confidence",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.DIRECT,
                description="Prediction confidence (0-1)",
                min_value=0,
                max_value=1,
                is_required=True,
            ),
            FeatureDefinition(
                name="market_vol",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.MARKET,
                description="Market volatility (SPY std dev of returns)",
                default_value=0.02,
            ),
            FeatureDefinition(
                name="spy_returns_5d",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.MARKET,
                description="SPY 5-day return",
                default_value=0.0,
            ),
            FeatureDefinition(
                name="spy_returns_20d",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.MARKET,
                description="SPY 20-day return",
                default_value=0.0,
            ),
            FeatureDefinition(
                name="hour_of_day",
                feature_type=FeatureType.ORDINAL,
                extraction_method=ExtractionMethod.DIRECT,
                description="Hour when event occurred (0-23)",
                min_value=0,
                max_value=23,
            ),
            FeatureDefinition(
                name="day_of_week",
                feature_type=FeatureType.ORDINAL,
                extraction_method=ExtractionMethod.DIRECT,
                description="Day of week (0=Monday, 6=Sunday)",
                min_value=0,
                max_value=6,
            ),
            FeatureDefinition(
                name="after_hours",
                feature_type=FeatureType.BINARY,
                extraction_method=ExtractionMethod.COMPUTED,
                description="Whether event occurred after market hours",
                default_value=0,
            ),
            FeatureDefinition(
                name="ticker_event_count",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.HISTORICAL,
                description="Count of similar historical events for ticker",
                default_value=0,
            ),
            FeatureDefinition(
                name="sector_avg_impact",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.HISTORICAL,
                description="Average impact for this sector",
                default_value=2.0,
            ),
            FeatureDefinition(
                name="event_type_avg_impact",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.HISTORICAL,
                description="Average impact for this event type",
                default_value=2.0,
            ),
        ]
    
    def _get_v1_1_features(self) -> List[FeatureDefinition]:
        """Enhanced features (v1.1)."""
        return [
            FeatureDefinition(
                name="vol_5d",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.MARKET,
                description="5-day realized volatility",
                default_value=0.02,
            ),
            FeatureDefinition(
                name="vol_10d",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.MARKET,
                description="10-day realized volatility",
                default_value=0.02,
            ),
            FeatureDefinition(
                name="vol_20d",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.MARKET,
                description="20-day realized volatility",
                default_value=0.02,
            ),
            FeatureDefinition(
                name="vol_ratio_5_20",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.COMPUTED,
                description="Short/long volatility ratio (mean reversion signal)",
                default_value=1.0,
            ),
            FeatureDefinition(
                name="sector_return_5d",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.MARKET,
                description="Sector ETF 5-day return",
                default_value=0.0,
            ),
            FeatureDefinition(
                name="sector_momentum_zscore",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.COMPUTED,
                description="Sector momentum z-score",
                default_value=0.0,
            ),
            FeatureDefinition(
                name="regime_strength",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.COMPUTED,
                description="Market regime classification strength (0-1)",
                default_value=0.5,
            ),
            FeatureDefinition(
                name="vix_level",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.MARKET,
                description="VIX or volatility index proxy",
                default_value=20.0,
            ),
            FeatureDefinition(
                name="contrarian_rate",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.HISTORICAL,
                description="Historical contrarian outcome rate",
                default_value=0.0,
            ),
            FeatureDefinition(
                name="hidden_bearish_prob",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.COMPUTED,
                description="Probability of hidden bearish outcome",
                default_value=0.0,
            ),
        ]
    
    def _get_v1_2_features(self) -> List[FeatureDefinition]:
        """Topology features (v1.2)."""
        return [
            FeatureDefinition(
                name="topology_cluster_id",
                feature_type=FeatureType.CATEGORICAL,
                extraction_method=ExtractionMethod.TOPOLOGY,
                description="Price correlation cluster assignment",
                default_value=0,
            ),
            FeatureDefinition(
                name="topology_cluster_size",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.TOPOLOGY,
                description="Number of stocks in the correlation cluster",
                default_value=0,
            ),
            FeatureDefinition(
                name="topology_cluster_volatility",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.TOPOLOGY,
                description="Average volatility of cluster members",
                default_value=0.02,
            ),
            FeatureDefinition(
                name="topology_regime_confidence",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.TOPOLOGY,
                description="Confidence in topology-based regime classification",
                default_value=0.5,
            ),
            FeatureDefinition(
                name="topology_regime_breadth",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.TOPOLOGY,
                description="Market breadth indicator from topology",
                default_value=0.5,
            ),
        ]
    
    def _get_v1_3_features(self) -> List[FeatureDefinition]:
        """Persistent homology features (v1.3)."""
        return [
            FeatureDefinition(
                name="persistent_betti0_count",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.TOPOLOGY,
                description="Count of significant H0 features (connected components)",
                default_value=0,
            ),
            FeatureDefinition(
                name="persistent_betti1_count",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.TOPOLOGY,
                description="Count of significant H1 features (loops/cycles) - key predictor",
                default_value=0,
            ),
            FeatureDefinition(
                name="persistent_max_lifetime_h0",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.TOPOLOGY,
                description="Maximum lifetime of H0 features",
                default_value=0.0,
            ),
            FeatureDefinition(
                name="persistent_max_lifetime_h1",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.TOPOLOGY,
                description="Maximum lifetime of H1 features (persistence)",
                default_value=0.0,
            ),
            FeatureDefinition(
                name="persistent_entropy",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.TOPOLOGY,
                description="Normalized persistence entropy (market chaos indicator)",
                default_value=0.0,
            ),
            FeatureDefinition(
                name="persistent_complexity",
                feature_type=FeatureType.NUMERIC,
                extraction_method=ExtractionMethod.TOPOLOGY,
                description="Combined topological complexity score",
                default_value=0.0,
            ),
        ]
    
    def get_version(self, version: str) -> Optional[FeatureVersion]:
        """Get feature schema for a specific version."""
        return self._versions.get(version)
    
    def get_current_version(self) -> FeatureVersion:
        """Get the current active feature version."""
        return self._versions[self.CURRENT_VERSION]
    
    def get_all_versions(self) -> List[FeatureVersion]:
        """Get all feature versions."""
        return list(self._versions.values())
    
    def get_feature_definition(self, name: str, version: Optional[str] = None) -> Optional[FeatureDefinition]:
        """Get definition for a specific feature."""
        version = version or self.CURRENT_VERSION
        fv = self._versions.get(version)
        if not fv:
            return None
        
        for feat in fv.features:
            if feat.name == name:
                return feat
        return None
    
    def get_features_by_method(self, method: ExtractionMethod, version: Optional[str] = None) -> List[FeatureDefinition]:
        """Get all features extracted by a specific method."""
        version = version or self.CURRENT_VERSION
        fv = self._versions.get(version)
        if not fv:
            return []
        
        return [f for f in fv.features if f.extraction_method == method]
    
    def get_topology_features(self, version: Optional[str] = None) -> List[FeatureDefinition]:
        """Get all topology-related features."""
        return self.get_features_by_method(ExtractionMethod.TOPOLOGY, version)
    
    def store_feature_importance(
        self,
        importance_dict: Dict[str, float],
        model_name: str,
        model_version: str,
        horizon: str
    ):
        """Store feature importance scores from a trained model."""
        key = f"{model_name}_{model_version}_{horizon}"
        
        self._importance_scores[key] = [
            FeatureImportance(
                feature_name=name,
                importance_score=score,
                model_name=model_name,
                model_version=model_version,
                horizon=horizon,
            )
            for name, score in importance_dict.items()
        ]
        
        logger.info(f"Stored {len(importance_dict)} feature importance scores for {key}")
    
    def get_feature_importance(
        self,
        model_name: str,
        model_version: str,
        horizon: str,
        top_k: Optional[int] = None
    ) -> List[FeatureImportance]:
        """Get stored feature importance scores for a model."""
        key = f"{model_name}_{model_version}_{horizon}"
        scores = self._importance_scores.get(key, [])
        
        if top_k:
            scores = sorted(scores, key=lambda x: x.importance_score, reverse=True)[:top_k]
        
        return scores
    
    def get_top_features(self, horizon: str = "1d", top_k: int = 20) -> List[Tuple[str, float]]:
        """Get top features across all models for a horizon."""
        feature_scores: Dict[str, List[float]] = {}
        
        for key, scores in self._importance_scores.items():
            if horizon in key:
                for imp in scores:
                    if imp.feature_name not in feature_scores:
                        feature_scores[imp.feature_name] = []
                    feature_scores[imp.feature_name].append(imp.importance_score)
        
        avg_scores = [
            (name, sum(scores) / len(scores))
            for name, scores in feature_scores.items()
        ]
        
        avg_scores.sort(key=lambda x: x[1], reverse=True)
        return avg_scores[:top_k]
    
    def validate_feature_vector(self, features: Dict[str, Any], version: Optional[str] = None) -> Tuple[bool, List[str]]:
        """Validate a feature vector against the schema."""
        version = version or self.CURRENT_VERSION
        fv = self._versions.get(version)
        if not fv:
            return False, [f"Unknown version: {version}"]
        
        errors = []
        feature_names = set(f.name for f in fv.features)
        
        for feat in fv.features:
            if feat.is_required and feat.name not in features:
                errors.append(f"Missing required feature: {feat.name}")
            
            if feat.name in features:
                value = features[feat.name]
                
                if feat.min_value is not None and value < feat.min_value:
                    errors.append(f"{feat.name} below minimum ({value} < {feat.min_value})")
                
                if feat.max_value is not None and value > feat.max_value:
                    errors.append(f"{feat.name} above maximum ({value} > {feat.max_value})")
        
        return len(errors) == 0, errors
    
    def compare_versions(self, v1: str, v2: str) -> Dict:
        """Compare two feature versions."""
        fv1 = self._versions.get(v1)
        fv2 = self._versions.get(v2)
        
        if not fv1 or not fv2:
            return {"error": "One or both versions not found"}
        
        names1 = set(f.name for f in fv1.features)
        names2 = set(f.name for f in fv2.features)
        
        return {
            "version_1": v1,
            "version_2": v2,
            "features_in_v1": len(names1),
            "features_in_v2": len(names2),
            "added_in_v2": list(names2 - names1),
            "removed_in_v2": list(names1 - names2),
            "unchanged": list(names1 & names2),
        }
    
    def to_dict(self) -> Dict:
        """Export registry to dictionary."""
        return {
            "current_version": self.CURRENT_VERSION,
            "versions": {k: v.to_dict() for k, v in self._versions.items()},
            "importance_scores": {
                k: [i.to_dict() for i in v] 
                for k, v in self._importance_scores.items()
            },
        }
