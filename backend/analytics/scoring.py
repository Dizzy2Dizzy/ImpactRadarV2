"""
Rule-based dynamic event scoring engine for Wave B.

Computes event scores using base scores by event type plus context multipliers
including sector beta, volatility (ATR), earnings proximity, market regime,
after-hours flag, and duplicate detection.

Invariants (see docs/SCORING.md):
- Final score clamped to [0, 100]
- Confidence bounded to [0, 100]
- Computation is deterministic and idempotent
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Union

import yaml
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class EventContext(BaseModel):
    """
    Context data for event scoring including market data factors.
    
    Attributes:
        sector: Company sector (e.g., "Technology", "Pharma")
        beta: Stock volatility vs market (0.5-2.0 typical). Higher = more volatile.
        atr_percentile: Recent volatility percentile (0-100). Higher = more volatile lately.
        spy_returns: Market returns dict with {"1d": float, "5d": float, "20d": float}
    """
    sector: Optional[str] = None
    beta: Optional[float] = None
    atr_percentile: Optional[float] = None
    spy_returns: Optional[Dict[str, float]] = None

# Config singleton - loaded once at module import
_CONFIG: Optional[Dict] = None


def load_config() -> Dict:
    """Load scoring configuration from YAML file. Cached after first load."""
    global _CONFIG
    if _CONFIG is not None:
        return _CONFIG
    
    config_path = Path(__file__).parent.parent / "config" / "scoring.yml"
    if not config_path.exists():
        logger.warning(f"Scoring config not found at {config_path}, using defaults")
        _CONFIG = _get_default_config()
        return _CONFIG
    
    try:
        with open(config_path, "r") as f:
            _CONFIG = yaml.safe_load(f)
        logger.info(f"Loaded scoring config from {config_path}")
        return _CONFIG
    except Exception as e:
        logger.error(f"Failed to load scoring config: {e}, using defaults")
        _CONFIG = _get_default_config()
        return _CONFIG


def _get_default_config() -> Dict:
    """Fallback configuration if YAML file missing."""
    return {
        "base_scores": {
            "fda_approval": 90,
            "product_launch": 75,
            "earnings": 65,
            "sec_8k": 55,
            "guidance": 70,
            "downgrade": 40,
            "reg_investigation": 25,
            "default": 50
        },
        "context_weights": {
            "sector_beta": {"low": 0, "medium": 5, "high": 10},
            "volatility": {"min": 0, "max": 10},
            "earnings_proximity": 8,
            "market_regime": {"min": -10, "max": 10},
            "after_hours": 4,
            "duplicate_penalty": -8
        },
        "source_credibility": {
            "EDGAR": 100,
            "SEC": 100,
            "FDA": 100,
            "official_newsroom": 85,
            "press_release": 80,
            "third_party": 70,
            "unknown": 60
        },
        "confidence": {
            "sample_size_quantiles": {"q10": 3, "q25": 5, "q50": 10, "q75": 20, "q90": 30},
            "data_completeness": {"full": 100, "partial": 70}
        }
    }


def get_base_score(event_type: str) -> int:
    """Get base score for event type from config."""
    config = load_config()
    base_scores = config.get("base_scores", {})
    return base_scores.get(event_type, base_scores.get("default", 50))


def compute_sector_beta_score(sector: Optional[str] = None, beta: Optional[float] = None) -> int:
    """
    Compute sector beta contribution (+0 to +10).
    
    Args:
        sector: Sector name (if beta not provided, estimated from sector)
        beta: Actual company beta (if available)
    
    Returns:
        Score contribution: 0 (low beta) to 10 (high beta)
    """
    config = load_config()
    weights = config["context_weights"]["sector_beta"]
    
    # If beta provided, use it directly
    if beta is not None:
        if beta < 0.8:
            return weights["low"]
        elif beta <= 1.2:
            return weights["medium"]
        else:
            return weights["high"]
    
    # Estimate from sector (rough heuristics)
    if not sector:
        return weights["medium"]  # Default to medium
    
    sector_lower = sector.lower()
    high_beta_sectors = ["technology", "biotech", "crypto", "fintech"]
    low_beta_sectors = ["utilities", "consumer staples", "healthcare"]
    
    if any(s in sector_lower for s in high_beta_sectors):
        return weights["high"]
    elif any(s in sector_lower for s in low_beta_sectors):
        return weights["low"]
    else:
        return weights["medium"]


def compute_volatility_score(atr_percentile: Optional[float] = None) -> int:
    """
    Compute volatility contribution based on ATR percentile (+0 to +10).
    
    Handles both 0-1 scale (legacy EventStats) and 0-100 scale (new MarketDataService).
    
    Args:
        atr_percentile: ATR percentile as 0-1 ratio or 0-100 percentage
    
    Returns:
        Score contribution: 0 (low volatility) to 10 (high volatility)
    """
    if atr_percentile is None:
        return 5  # Default to middle
    
    config = load_config()
    weights = config["context_weights"]["volatility"]
    min_score = weights["min"]
    max_score = weights["max"]
    
    # Normalize units: handle both 0-1 scale (legacy) and 0-100 scale (new)
    # If value is between 0-1, it's a ratio - convert to percentage
    if atr_percentile > 0 and atr_percentile <= 1.0:
        atr_percentile = atr_percentile * 100.0
    
    # Convert percentile (0-100) to ratio (0-1) and scale to score
    percentile_ratio = atr_percentile / 100.0
    score = int(min_score + (max_score - min_score) * percentile_ratio)
    return max(min_score, min(max_score, score))


def is_near_earnings(event_id: int, event_date: datetime, db: Session, ticker: str) -> bool:
    """
    Check if event is within ±3 trading days of an earnings event.
    
    Args:
        event_id: Current event ID (to exclude self)
        event_date: Date of the event
        db: Database session
        ticker: Stock ticker
    
    Returns:
        True if within ±3 trading days of earnings
    """
    try:
        from releaseradar.db.models import Event
        
        # Check for earnings events within ±5 calendar days (conservative)
        window_start = event_date - timedelta(days=5)
        window_end = event_date + timedelta(days=5)
        
        result = db.execute(
            select(func.count()).select_from(Event).where(
                Event.ticker == ticker,
                Event.event_type == "earnings",
                Event.date >= window_start,
                Event.date <= window_end,
                Event.id != event_id  # Don't count the event itself if it's earnings
            )
        ).scalar()
        
        return result > 0
    except Exception as e:
        logger.debug(f"Failed to check earnings proximity for {ticker}: {e}")
        return False


def compute_earnings_proximity_score(event_id: int, event_date: datetime, db: Session, ticker: str) -> int:
    """Compute earnings proximity bonus (+8 if near earnings, else 0)."""
    config = load_config()
    bonus = config["context_weights"]["earnings_proximity"]
    
    if is_near_earnings(event_id, event_date, db, ticker):
        return bonus
    return 0


def compute_market_regime_score(spy_returns: Optional[Union[float, Dict[str, float]]] = None) -> int:
    """
    Compute market regime contribution based on SPY returns (-10 to +10).
    
    Args:
        spy_returns: Either a single float (legacy: 10-day return) or dict with
                     {"1d": float, "5d": float, "20d": float}. Primarily uses 5d return.
    
    Returns:
        Score contribution: -10 (bearish) to +10 (bullish)
    """
    if spy_returns is None:
        return 0  # Neutral if data unavailable
    
    # Handle both dict (new) and float (legacy) formats
    if isinstance(spy_returns, dict):
        # Use 5-day return as primary indicator
        return_value = spy_returns.get("5d", 0.0)
    else:
        # Legacy: single float value
        return_value = spy_returns
    
    config = load_config()
    weights = config["context_weights"]["market_regime"]
    min_score = weights["min"]
    max_score = weights["max"]
    
    # Map returns to score (rough quantile mapping)
    # Assume typical 5-day returns: -5% to +5%
    if return_value <= -0.05:
        return min_score  # Very bearish
    elif return_value >= 0.05:
        return max_score  # Very bullish
    else:
        # Linear interpolation
        normalized = (return_value + 0.05) / 0.10  # Map [-0.05, 0.05] to [0, 1]
        score = int(min_score + (max_score - min_score) * normalized)
        return max(min_score, min(max_score, score))


def is_after_hours(event_date: datetime) -> bool:
    """
    Check if event occurred after market hours (after 4 PM ET).
    
    Note: This is a simplified check. For production, use market calendar.
    """
    # Check if time component exists and is after 4 PM (16:00) or before 9:30 AM
    if event_date.hour >= 16 or event_date.hour < 9:
        return True
    if event_date.hour == 9 and event_date.minute < 30:
        return True
    return False


def compute_after_hours_score(event_date: datetime) -> int:
    """Compute after-hours bonus (+4 if after hours, else 0)."""
    config = load_config()
    bonus = config["context_weights"]["after_hours"]
    
    if is_after_hours(event_date):
        return bonus
    return 0


def has_recent_duplicate(event_id: int, ticker: str, event_type: str, event_date: datetime, db: Session) -> bool:
    """
    Check if similar event occurred within 7 days.
    
    Args:
        event_id: Current event ID (to exclude self)
        ticker: Stock ticker
        event_type: Event type
        event_date: Event date
        db: Database session
    
    Returns:
        True if duplicate found within 7 days
    """
    try:
        from releaseradar.db.models import Event
        
        window_start = event_date - timedelta(days=7)
        
        result = db.execute(
            select(func.count()).select_from(Event).where(
                Event.ticker == ticker,
                Event.event_type == event_type,
                Event.date >= window_start,
                Event.date < event_date,  # Only look at earlier events
                Event.id != event_id  # Exclude self
            )
        ).scalar()
        
        return result > 0
    except Exception as e:
        logger.debug(f"Failed to check duplicates for {ticker}: {e}")
        return False


def compute_duplicate_penalty(event_id: int, ticker: str, event_type: str, event_date: datetime, db: Session) -> int:
    """Compute duplicate penalty (-8 if duplicate, else 0)."""
    config = load_config()
    penalty = config["context_weights"]["duplicate_penalty"]
    
    if has_recent_duplicate(event_id, ticker, event_type, event_date, db):
        return penalty
    return 0


def compute_confidence(
    sample_size: Optional[int],
    source: str,
    data_completeness: str = "full"
) -> int:
    """
    Compute confidence score (0-100) based on sample size, source credibility, and data completeness.
    
    Args:
        sample_size: Number of historical events for (ticker, event_type) from EventStats
        source: Event source (e.g., "EDGAR", "FDA", "press_release")
        data_completeness: "full" or "partial"
    
    Returns:
        Confidence score (0-100)
    """
    config = load_config()
    
    # 1. Sample size contribution (0-100)
    quantiles = config["confidence"]["sample_size_quantiles"]
    if sample_size is None or sample_size == 0:
        sample_confidence = 40  # Low confidence with no historical data
    elif sample_size >= quantiles["q90"]:
        sample_confidence = 100
    elif sample_size >= quantiles["q75"]:
        sample_confidence = 85
    elif sample_size >= quantiles["q50"]:
        sample_confidence = 70
    elif sample_size >= quantiles["q25"]:
        sample_confidence = 55
    else:
        sample_confidence = 40
    
    # 2. Source credibility (0-100)
    credibility = config["source_credibility"]
    source_confidence = credibility.get(source, credibility.get("unknown", 60))
    
    # 3. Data completeness (0-100)
    completeness = config["confidence"]["data_completeness"]
    completeness_score = completeness.get(data_completeness, completeness["partial"])
    
    # Final confidence: minimum of all three components
    final_confidence = min(sample_confidence, source_confidence, completeness_score)
    
    return max(0, min(100, final_confidence))


def compute_info_tier_factor(info_tier: str = "primary") -> int:
    """
    Compute information tier contribution (0 for primary, reserved for secondary).
    
    Wave J: Primary events are direct market-moving catalysts (SEC, FDA, earnings).
    Secondary events are contextual risk factors (environmental, infrastructure).
    
    Args:
        info_tier: "primary" or "secondary"
        
    Returns:
        Score contribution: 0 for primary (default), reserved for future use
    """
    # Primary events have no modifier (they're the baseline)
    # Secondary tier reserved for future context signals
    if info_tier == "secondary":
        return 0  # Reserved for future use
    return 0


def compute_context_risk_score(ticker: str, event_date: datetime, db: Session, days_window: int = 30) -> int:
    """
    Compute context risk score from ContextSignals within time window.
    
    Wave J: Queries ContextSignal table for environmental, infrastructure, and macro
    risk factors affecting the ticker. Returns aggregate risk score (0-100).
    
    Args:
        ticker: Stock ticker
        event_date: Reference date for the event
        db: Database session
        days_window: Days to look back/forward for context signals (default 30)
        
    Returns:
        Risk score (0-100): 0=low risk, 100=high risk
    """
    try:
        from releaseradar.db.models import ContextSignal
        
        window_start = event_date - timedelta(days=days_window)
        window_end = event_date + timedelta(days=days_window)
        
        # Query relevant context signals
        result = db.execute(
            select(func.count(), func.avg(ContextSignal.severity))
            .select_from(ContextSignal)
            .where(
                ContextSignal.ticker == ticker,
                ContextSignal.observed_at >= window_start,
                ContextSignal.observed_at <= window_end
            )
        ).first()
        
        if result and result[0] > 0:
            count = result[0]
            avg_severity = result[1] or 0
            
            # Combine count and severity into risk score
            # More signals = higher risk, higher average severity = higher risk
            risk_score = min(100, int(avg_severity * (1 + count * 0.1)))
            return risk_score
        
        return 0  # No context signals found
    except Exception as e:
        logger.debug(f"Failed to compute context risk score for {ticker}: {e}")
        return 0


def compute_event_score(
    event_id: int,
    ticker: str,
    event_type: str,
    event_date: datetime,
    source: str,
    sector: Optional[str],
    db: Session,
    # Optional context data
    sample_size: Optional[int] = None,
    beta: Optional[float] = None,
    atr_percentile: Optional[float] = None,
    spy_returns: Optional[Union[float, Dict[str, float]]] = None,
    data_completeness: str = "full",
    info_tier: str = "primary",
    info_subtype: Optional[str] = None
) -> Dict:
    """
    Compute comprehensive event score with context multipliers.
    
    Returns:
        {
            "base_score": int,
            "context_score": int,
            "final_score": int,  # clamped [0, 100]
            "confidence": int,   # [0, 100]
            "rationale": List[str]  # Human-readable explanations
        }
    """
    rationale = []
    
    # 1. Base score
    base_score = get_base_score(event_type)
    rationale.append(f"Base={event_type}({base_score})")
    
    # 2. Context multipliers
    context_score = 0
    
    # Sector beta
    sector_contrib = compute_sector_beta_score(sector, beta)
    if sector_contrib != 0:
        context_score += sector_contrib
        rationale.append(f"Sector beta +{sector_contrib}")
    
    # Volatility (ATR)
    vol_contrib = compute_volatility_score(atr_percentile)
    if vol_contrib != 5:  # Only mention if not default
        context_score += vol_contrib
        if atr_percentile:
            rationale.append(f"ATR p{int(atr_percentile)} +{vol_contrib}")
    
    # Earnings proximity
    earnings_contrib = compute_earnings_proximity_score(event_id, event_date, db, ticker)
    if earnings_contrib != 0:
        context_score += earnings_contrib
        rationale.append(f"Near earnings +{earnings_contrib}")
    
    # Market regime
    regime_contrib = compute_market_regime_score(spy_returns)
    if regime_contrib != 0:
        context_score += regime_contrib
        sign = "+" if regime_contrib > 0 else ""
        rationale.append(f"Market regime {sign}{regime_contrib}")
    
    # After hours
    ah_contrib = compute_after_hours_score(event_date)
    if ah_contrib != 0:
        context_score += ah_contrib
        rationale.append(f"After hours +{ah_contrib}")
    
    # Duplicate penalty
    dup_penalty = compute_duplicate_penalty(event_id, ticker, event_type, event_date, db)
    if dup_penalty != 0:
        context_score += dup_penalty
        rationale.append(f"Recent duplicate {dup_penalty}")
    
    # Info tier factor (Wave J)
    tier_contrib = compute_info_tier_factor(info_tier)
    if tier_contrib != 0:
        context_score += tier_contrib
        rationale.append(f"Info tier {info_tier} {tier_contrib}")
    
    # 3. Final score (clamped)
    final_score = max(0, min(100, base_score + context_score))
    
    # 4. Confidence
    confidence = compute_confidence(sample_size, source, data_completeness)
    rationale.append(f"Confidence: {confidence}%")
    
    # 5. Context risk score (Wave J)
    context_risk_score = compute_context_risk_score(ticker, event_date, db)
    
    # 6. Individual factors breakdown (Wave B + Wave J)
    factors = {
        "sector": sector_contrib,
        "volatility": vol_contrib if vol_contrib != 5 else 0,  # Only report if non-default
        "earnings_proximity": earnings_contrib,
        "market_mood": regime_contrib,
        "after_hours": ah_contrib,
        "duplicate_penalty": dup_penalty,
        "info_tier": tier_contrib,
        "info_subtype": info_subtype
    }
    
    return {
        "base_score": base_score,
        "context_score": context_score,
        "final_score": final_score,
        "confidence": confidence,
        "rationale": rationale,
        "factors": factors,
        "context_risk_score": context_risk_score,
        "info_tier": info_tier,
        "info_subtype": info_subtype
    }
