"""
Ensemble Models for Impact Radar ML System.

Provides stacked ensemble combining XGBoost, LightGBM, and topology features.
"""

from .stacked_impact import (
    StackedImpactEnsemble,
    StackedEnsembleConfig,
    StackedPrediction,
    EnsembleMetrics,
)

__all__ = [
    "StackedImpactEnsemble",
    "StackedEnsembleConfig",
    "StackedPrediction",
    "EnsembleMetrics",
]
