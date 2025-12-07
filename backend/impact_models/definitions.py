from dataclasses import dataclass


@dataclass
class ImpactTargetConfig:
    """Configuration for what we're predicting"""
    horizon_days: int          # e.g. 1-day horizon
    threshold_pct: float       # e.g. 3.0 = 3%
    benchmark: str             # e.g. "SPY" or sector ETF ticker


DEFAULT_IMPACT_TARGET = ImpactTargetConfig(
    horizon_days=1,
    threshold_pct=3.0,
    benchmark="SPY",
)
