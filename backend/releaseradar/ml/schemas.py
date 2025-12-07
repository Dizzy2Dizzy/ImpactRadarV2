"""
Pydantic schemas for ML features and predictions.

Defines the structure of feature vectors, training data, and prediction outputs.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class EventFeatures(BaseModel):
    """Feature vector for a single event."""
    
    event_id: int
    ticker: str
    event_type: str
    
    # Deterministic scoring features
    base_score: int
    context_score: Optional[int] = None
    confidence: float
    
    # Sector and categorization
    sector: Optional[str] = None
    info_tier: str = "primary"
    
    # Market context features
    market_vol: Optional[float] = None  # VIX or market volatility
    beta: Optional[float] = None
    atr_percentile: Optional[float] = None
    spy_returns_5d: Optional[float] = None
    spy_returns_20d: Optional[float] = None
    
    # Enhanced benchmark features (IMPROVEMENT #4)
    spy_return_1d: Optional[float] = None
    market_vol_20d: Optional[float] = None  # SPY 20-day rolling volatility
    trend_20d: Optional[float] = None  # SPY 20-day return
    
    # Pre-event context features (IMPROVEMENT #4)
    stock_vol_pre_event: Optional[float] = None  # 20-day volatility before event
    stock_trend_pre_event: Optional[float] = None  # 20-day return before event
    
    # Volatility Term Structure Features (v1.1)
    vol_5d: Optional[float] = None  # 5-day realized volatility
    vol_10d: Optional[float] = None  # 10-day realized volatility
    vol_20d: Optional[float] = None  # 20-day realized volatility
    vol_ratio_5_20: Optional[float] = None  # Short/long vol ratio (mean reversion signal)
    vol_percentile_90d: Optional[float] = None  # Current vol percentile vs 90-day history
    
    # Sector Momentum Features (v1.1)
    sector_return_5d: Optional[float] = None  # Sector ETF 5-day return
    sector_return_20d: Optional[float] = None  # Sector ETF 20-day return  
    sector_momentum_zscore: Optional[float] = None  # Sector momentum z-score vs market
    sector_relative_strength: Optional[float] = None  # Sector vs SPY relative performance
    
    # Market Regime Features (v1.1)
    market_regime: Optional[str] = None  # "bull", "bear", "neutral", "high_vol"
    regime_strength: Optional[float] = None  # Confidence in regime classification (0-1)
    vix_level: Optional[float] = None  # VIX or volatility index proxy
    vix_percentile_252d: Optional[float] = None  # VIX percentile vs 1-year history
    trend_strength_20d: Optional[float] = None  # ADX-like trend strength indicator
    
    # Sentiment Trend Features (v1.1)
    sentiment_current: Optional[float] = None  # Current sentiment score
    sentiment_change_3d: Optional[float] = None  # 3-day sentiment change
    sentiment_change_7d: Optional[float] = None  # 7-day sentiment change
    sentiment_momentum: Optional[float] = None  # Sentiment trend momentum
    
    # Event timing features
    hour_of_day: Optional[int] = None
    day_of_week: Optional[int] = None
    after_hours: bool = False
    
    # Historical features
    ticker_event_count: Optional[int] = None  # How many similar events for this ticker
    sector_avg_impact: Optional[float] = None
    event_type_avg_impact: Optional[float] = None
    
    # Probabilistic scoring features (if available)
    impact_p_move: Optional[float] = None
    impact_p_up: Optional[float] = None
    impact_p_down: Optional[float] = None
    
    # Factor contributions
    factor_sector: Optional[int] = None
    factor_volatility: Optional[int] = None
    factor_earnings_proximity: Optional[int] = None
    factor_market_mood: Optional[int] = None
    
    # Data quality flags
    has_price_history: bool = False
    has_event_stats: bool = False
    has_market_data: bool = False
    
    # Event type family (for global models)
    event_type_family: Optional[int] = None  # Numeric family ID for global models
    
    # Contrarian/Hidden Bearish features (Market Echo Engine learning from outcomes)
    contrarian_rate: Optional[float] = None  # Historical contrarian rate for ticker+event_type
    hidden_bearish_prob: Optional[float] = None  # Probability of hidden bearish outcome
    avg_contrarian_return: Optional[float] = None  # Average decline when contrarian occurs
    contrarian_sample_size: Optional[int] = None  # Number of historical samples for pattern
    has_contrarian_history: bool = False  # Whether we have contrarian pattern data
    
    # Topology Features (v1.2) - ADDITIVE to existing features
    # Correlation clustering context
    topology_cluster_id: Optional[int] = None  # Cluster assignment based on price correlation
    topology_cluster_size: Optional[int] = None  # Number of stocks in the cluster
    topology_cluster_volatility: Optional[float] = None  # Average volatility of cluster members
    topology_cluster_return_5d: Optional[float] = None  # 5-day return of cluster
    topology_cluster_correlation: Optional[float] = None  # Intra-cluster correlation
    # Regime detection context
    topology_regime: Optional[str] = None  # "risk_on" or "risk_off"
    topology_regime_confidence: Optional[float] = None  # Confidence in regime classification (0-1)
    topology_regime_volatility: Optional[float] = None  # Market-wide volatility indicator
    topology_regime_breadth: Optional[float] = None  # % of stocks with positive returns
    has_topology_context: bool = False  # Whether topology features are available
    
    # Persistent Homology Features (v1.3) - Topological Data Analysis
    # These capture the "shape" of price patterns using algebraic topology
    # Betti numbers: β₀ = connected components, β₁ = loops/cycles
    persistent_betti0_count: Optional[int] = None  # Number of significant H0 features
    persistent_betti1_count: Optional[int] = None  # Number of significant H1 features (loops)
    persistent_max_lifetime_h0: Optional[float] = None  # Longest-lived connected component
    persistent_max_lifetime_h1: Optional[float] = None  # Longest-lived loop
    persistent_mean_lifetime_h0: Optional[float] = None  # Average H0 lifetime
    persistent_mean_lifetime_h1: Optional[float] = None  # Average H1 lifetime
    persistent_total_h0: Optional[float] = None  # Total persistence in H0
    persistent_total_h1: Optional[float] = None  # Total persistence in H1
    persistent_entropy: Optional[float] = None  # Normalized persistence entropy (complexity)
    persistent_complexity: Optional[float] = None  # Combined topological complexity score
    has_persistent_features: bool = False  # Whether persistent homology was computed
    
    # Options-Implied Volatility Features (v1.4) - Market expectations
    implied_volatility_atm: Optional[float] = None  # ATM IV from options market
    iv_percentile_30d: Optional[float] = None  # IV percentile vs 30-day history (0-100)
    put_call_ratio: Optional[float] = None  # Put/call volume ratio (sentiment)
    iv_skew: Optional[float] = None  # Put IV - Call IV at same delta
    has_options_data: bool = False  # Whether options data was available
    
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_vector(self) -> Dict[str, float]:
        """Convert to flat feature vector for ML model."""
        features = {
            "base_score": float(self.base_score),
            "context_score": float(self.context_score or 0),
            "confidence": self.confidence,
            "market_vol": self.market_vol or 0.0,
            "beta": self.beta or 1.0,
            "atr_percentile": self.atr_percentile or 50.0,
            "spy_returns_5d": self.spy_returns_5d or 0.0,
            "spy_returns_20d": self.spy_returns_20d or 0.0,
            "spy_return_1d": self.spy_return_1d or 0.0,
            "market_vol_20d": self.market_vol_20d or 0.02,
            "trend_20d": self.trend_20d or 0.0,
            "stock_vol_pre_event": self.stock_vol_pre_event or 0.02,
            "stock_trend_pre_event": self.stock_trend_pre_event or 0.0,
            "hour_of_day": float(self.hour_of_day or 12),
            "day_of_week": float(self.day_of_week or 3),
            "after_hours": float(self.after_hours),
            "ticker_event_count": float(self.ticker_event_count or 0),
            "sector_avg_impact": self.sector_avg_impact or 0.0,
            "event_type_avg_impact": self.event_type_avg_impact or 0.0,
            "impact_p_move": self.impact_p_move or 0.5,
            "impact_p_up": self.impact_p_up or 0.25,
            "impact_p_down": self.impact_p_down or 0.25,
            "factor_sector": float(self.factor_sector or 0),
            "factor_volatility": float(self.factor_volatility or 0),
            "factor_earnings_proximity": float(self.factor_earnings_proximity or 0),
            "factor_market_mood": float(self.factor_market_mood or 0),
            "has_price_history": float(self.has_price_history),
            "has_event_stats": float(self.has_event_stats),
            "has_market_data": float(self.has_market_data),
            # Contrarian/Hidden Bearish features
            "contrarian_rate": self.contrarian_rate or 0.0,
            "hidden_bearish_prob": self.hidden_bearish_prob or 0.0,
            "avg_contrarian_return": self.avg_contrarian_return or 0.0,
            "contrarian_sample_size": float(self.contrarian_sample_size or 0),
            "has_contrarian_history": float(self.has_contrarian_history),
            # Volatility Term Structure (v1.1)
            "vol_5d": self.vol_5d or 0.02,
            "vol_10d": self.vol_10d or 0.02,
            "vol_20d": self.vol_20d or 0.02,
            "vol_ratio_5_20": self.vol_ratio_5_20 or 1.0,
            "vol_percentile_90d": self.vol_percentile_90d or 50.0,
            # Sector Momentum (v1.1)
            "sector_return_5d": self.sector_return_5d or 0.0,
            "sector_return_20d": self.sector_return_20d or 0.0,
            "sector_momentum_zscore": self.sector_momentum_zscore or 0.0,
            "sector_relative_strength": self.sector_relative_strength or 0.0,
            # Market Regime (v1.1)
            "regime_bull": float(self.market_regime == "bull") if self.market_regime else 0.0,
            "regime_bear": float(self.market_regime == "bear") if self.market_regime else 0.0,
            "regime_neutral": float(self.market_regime == "neutral") if self.market_regime else 1.0,
            "regime_high_vol": float(self.market_regime == "high_vol") if self.market_regime else 0.0,
            "regime_strength": self.regime_strength or 0.5,
            "vix_level": self.vix_level or 20.0,
            "vix_percentile_252d": self.vix_percentile_252d or 50.0,
            "trend_strength_20d": self.trend_strength_20d or 0.0,
            # Sentiment Trends (v1.1)
            "sentiment_current": self.sentiment_current or 0.0,
            "sentiment_change_3d": self.sentiment_change_3d or 0.0,
            "sentiment_change_7d": self.sentiment_change_7d or 0.0,
            "sentiment_momentum": self.sentiment_momentum or 0.0,
            # Topology Features (v1.2) - ADDITIVE
            "topology_cluster_id": float(self.topology_cluster_id or 0),
            "topology_cluster_size": float(self.topology_cluster_size or 0),
            "topology_cluster_volatility": self.topology_cluster_volatility or 0.02,
            "topology_cluster_return_5d": self.topology_cluster_return_5d or 0.0,
            "topology_cluster_correlation": self.topology_cluster_correlation or 0.5,
            "topology_regime_risk_on": float(self.topology_regime == "risk_on") if self.topology_regime else 0.5,
            "topology_regime_risk_off": float(self.topology_regime == "risk_off") if self.topology_regime else 0.5,
            "topology_regime_confidence": self.topology_regime_confidence or 0.5,
            "topology_regime_volatility": self.topology_regime_volatility or 0.02,
            "topology_regime_breadth": self.topology_regime_breadth or 0.5,
            "has_topology_context": float(self.has_topology_context),
            # Persistent Homology Features (v1.3)
            "persistent_betti0_count": float(self.persistent_betti0_count or 0),
            "persistent_betti1_count": float(self.persistent_betti1_count or 0),
            "persistent_max_lifetime_h0": self.persistent_max_lifetime_h0 or 0.0,
            "persistent_max_lifetime_h1": self.persistent_max_lifetime_h1 or 0.0,
            "persistent_mean_lifetime_h0": self.persistent_mean_lifetime_h0 or 0.0,
            "persistent_mean_lifetime_h1": self.persistent_mean_lifetime_h1 or 0.0,
            "persistent_total_h0": self.persistent_total_h0 or 0.0,
            "persistent_total_h1": self.persistent_total_h1 or 0.0,
            "persistent_entropy": self.persistent_entropy or 0.0,
            "persistent_complexity": self.persistent_complexity or 0.0,
            "has_persistent_features": float(self.has_persistent_features),
            # Options-Implied Volatility Features (v1.4)
            "implied_volatility_atm": self.implied_volatility_atm or 0.30,  # Default ~30% annualized
            "iv_percentile_30d": self.iv_percentile_30d or 50.0,  # Default median
            "put_call_ratio": self.put_call_ratio or 1.0,  # Default neutral
            "iv_skew": self.iv_skew or 0.0,  # Default no skew
            "has_options_data": float(self.has_options_data),
        }
        
        # Add categorical encodings
        features.update(self._encode_sector())
        features.update(self._encode_event_type())
        features.update(self._encode_info_tier())
        
        # Add event_type_family if present (for global models)
        if self.event_type_family is not None:
            features["event_type_family"] = float(self.event_type_family)
        
        return features
    
    def _encode_sector(self) -> Dict[str, float]:
        """One-hot encode sector."""
        sectors = ["Healthcare", "Technology", "Finance", "Energy", "Consumer", "Industrial", "Other"]
        return {f"sector_{s.lower()}": float(self.sector == s) for s in sectors}
    
    def _encode_event_type(self) -> Dict[str, float]:
        """One-hot encode event type."""
        event_types = ["earnings", "fda_approval", "sec_8k", "sec_10q", "product_launch", 
                       "guidance", "dividend", "ma", "press", "other"]
        return {f"event_type_{et}": float(self.event_type == et) for et in event_types}
    
    def _encode_info_tier(self) -> Dict[str, float]:
        """Encode info tier."""
        return {"info_tier_primary": float(self.info_tier == "primary")}


class MLPrediction(BaseModel):
    """ML model prediction output with transparency fields."""
    
    event_id: int
    ml_adjusted_score: int = Field(ge=0, le=100)
    ml_confidence: float = Field(ge=0.0, le=1.0)
    ml_model_version: str
    model_source: str = Field(default="deterministic")  # "family-specific", "global", or "deterministic"
    base_score: Optional[int] = Field(None, ge=0, le=100)
    ml_prediction_raw: Optional[int] = Field(None, ge=0, le=100)
    delta_applied: Optional[float] = None
    predicted_return_1d: Optional[float] = None
    predicted_return_5d: Optional[float] = None
    predicted_return_20d: Optional[float] = None
    predicted_at: datetime = Field(default_factory=datetime.utcnow)


class TrainingData(BaseModel):
    """Training dataset for ML model."""
    
    features: List[Any]  # EventFeatures or any object with to_vector() method
    outcomes: List[float]  # Target variable (returns)
    horizon: str  # "1d", "5d", or "20d"
    n_samples: int
    feature_version: str = "v1.0"
    
    class Config:
        arbitrary_types_allowed = True


class ModelMetrics(BaseModel):
    """Performance metrics for trained model."""
    
    mae: float  # Mean Absolute Error
    rmse: float  # Root Mean Squared Error
    r2: float  # R-squared
    directional_accuracy: float  # % of correct direction predictions
    sharpe_ratio: Optional[float] = None
    max_error: float
    n_train: int
    n_test: int
    feature_importance: Dict[str, float] = Field(default_factory=dict)


class ModelInfo(BaseModel):
    """Model registry information."""
    
    name: str
    version: str
    status: str  # "staging", "active", "archived"
    model_path: str
    metrics: ModelMetrics
    feature_version: str
    trained_at: datetime
    promoted_at: Optional[datetime] = None
    cohort_pct: Optional[float] = None


class ProbabilisticPrediction(BaseModel):
    """
    Probabilistic prediction with uncertainty intervals (v1.4).
    
    Provides prediction intervals instead of just point estimates,
    enabling better uncertainty quantification for trading decisions.
    
    Example output: "Stock expected to move +2% to +8% (90% confidence)"
    """
    
    event_id: int
    horizon: str  # "1d" or "5d"
    
    # Point estimate (median prediction)
    point_estimate: float  # Predicted return (e.g., 0.05 for 5%)
    
    # Prediction intervals (from quantile regression)
    lower_bound: float  # 10th percentile
    q25: Optional[float] = None  # 25th percentile
    q75: Optional[float] = None  # 75th percentile
    upper_bound: float  # 90th percentile
    
    # Interval width metrics
    confidence_interval: float  # Width of 80% interval (q10 to q90)
    iqr: Optional[float] = None  # Interquartile range (q25 to q75)
    
    # Options-implied volatility data (when available)
    implied_volatility: Optional[float] = None  # ATM IV from options market
    iv_percentile: Optional[float] = None  # IV percentile vs 30-day history
    iv_adjustment: float = 0.0  # Adjustment applied based on IV
    
    # Calibration information
    coverage_level: float = 0.80  # Nominal coverage (e.g., 0.80 for 80% interval)
    is_calibrated: bool = False  # Whether conformal calibration was applied
    calibration_adjustment: float = 0.0  # Conformal adjustment applied
    
    # Confidence and quality
    prediction_confidence: float = Field(ge=0.0, le=1.0)  # Overall confidence
    has_sufficient_data: bool = True  # Whether we had enough data for reliable prediction
    
    # Directional probabilities
    prob_positive: Optional[float] = None  # P(return > 0)
    prob_negative: Optional[float] = None  # P(return < 0)
    prob_significant_move: Optional[float] = None  # P(|return| > 2%)
    
    # Model information
    model_version: str = "v1.4"
    predicted_at: datetime = Field(default_factory=datetime.utcnow)
    
    def format_interval(self) -> str:
        """Format prediction interval as human-readable string."""
        lower_pct = self.lower_bound * 100
        upper_pct = self.upper_bound * 100
        coverage_pct = int(self.coverage_level * 100)
        
        if lower_pct >= 0:
            return f"+{lower_pct:.1f}% to +{upper_pct:.1f}% ({coverage_pct}% confidence)"
        elif upper_pct <= 0:
            return f"{lower_pct:.1f}% to {upper_pct:.1f}% ({coverage_pct}% confidence)"
        else:
            return f"{lower_pct:.1f}% to +{upper_pct:.1f}% ({coverage_pct}% confidence)"
    
    def get_risk_assessment(self) -> str:
        """Get a qualitative risk assessment based on interval width."""
        width = self.confidence_interval * 100  # Convert to percentage
        
        if width < 3:
            return "low_uncertainty"
        elif width < 6:
            return "moderate_uncertainty"
        elif width < 10:
            return "high_uncertainty"
        else:
            return "very_high_uncertainty"
    
    def expected_direction(self) -> str:
        """Get expected move direction based on median and bounds."""
        if self.point_estimate > 0 and self.lower_bound > -0.01:
            return "bullish"
        elif self.point_estimate < 0 and self.upper_bound < 0.01:
            return "bearish"
        else:
            return "uncertain"
