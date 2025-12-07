"""
Strategy Engine for Impact Radar Backtesting

Evaluates trading conditions and calculates position sizes for strategy execution.
"""

from typing import Dict, Any, Optional
from releaseradar.db.models import UserStrategy, Event
import logging

logger = logging.getLogger(__name__)


def evaluate_conditions(conditions_json: Dict[str, Any], event: Event) -> bool:
    """
    Evaluate whether an event matches the given entry/exit conditions.
    
    Args:
        conditions_json: Dictionary of conditions to match
            Example: {
                "event_types": ["fda_approval", "earnings"],
                "min_score": 75,
                "max_score": 100,
                "directions": ["bullish"],
                "sectors": ["Healthcare", "Technology"],
                "min_confidence": 0.7
            }
        event: Event object to evaluate
    
    Returns:
        bool: True if event matches all conditions, False otherwise
    """
    if not conditions_json:
        return True
    
    # Check event types
    if "event_types" in conditions_json:
        event_types = conditions_json["event_types"]
        if event_types and event.event_type not in event_types:
            return False
    
    # Check impact score range
    if "min_score" in conditions_json:
        min_score = conditions_json["min_score"]
        event_score = event.ml_adjusted_score or event.impact_score
        if event_score < min_score:
            return False
    
    if "max_score" in conditions_json:
        max_score = conditions_json["max_score"]
        event_score = event.ml_adjusted_score or event.impact_score
        if event_score > max_score:
            return False
    
    # Check direction
    if "directions" in conditions_json:
        directions = conditions_json["directions"]
        if directions and event.direction not in directions:
            return False
    
    # Check sectors
    if "sectors" in conditions_json:
        sectors = conditions_json["sectors"]
        if sectors and event.sector not in sectors:
            return False
    
    # Check confidence threshold
    if "min_confidence" in conditions_json:
        min_confidence = conditions_json["min_confidence"]
        event_confidence = event.ml_confidence or event.confidence
        if event_confidence < min_confidence:
            return False
    
    # Check information tier
    if "info_tiers" in conditions_json:
        info_tiers = conditions_json["info_tiers"]
        if info_tiers and event.info_tier not in info_tiers:
            return False
    
    # All conditions passed
    return True


def calculate_position_size(strategy: UserStrategy, capital: float, event: Optional[Event] = None) -> float:
    """
    Calculate position size for a trade based on strategy rules.
    
    Args:
        strategy: UserStrategy object with position_sizing JSON
        capital: Available capital for trading
        event: Optional Event object (for event-specific sizing)
    
    Returns:
        float: Position size in dollars
    
    Position sizing strategies:
        - equal_weight: Divide capital equally across max_positions
        - fixed_amount: Use fixed dollar amount
        - percent_capital: Use percentage of total capital
        - score_weighted: Weight by impact score (higher score = larger position)
        - kelly_criterion: Calculate optimal position size (future enhancement)
    """
    if not strategy.position_sizing:
        # Default: equal weight with max 10 positions
        return capital / 10
    
    sizing = strategy.position_sizing
    sizing_type = sizing.get("type", "equal_weight")
    
    if sizing_type == "equal_weight":
        max_positions = sizing.get("max_positions", 10)
        return capital / max_positions
    
    elif sizing_type == "fixed_amount":
        fixed_amount = sizing.get("amount", 10000)
        return min(fixed_amount, capital)
    
    elif sizing_type == "percent_capital":
        percent = sizing.get("percent", 10.0) / 100.0
        return capital * percent
    
    elif sizing_type == "score_weighted":
        # Weight position size by impact score
        # High score (90+) = larger position, low score (50-) = smaller position
        if event is None:
            # Fallback to equal weight if no event provided
            max_positions = sizing.get("max_positions", 10)
            return capital / max_positions
        
        score = event.ml_adjusted_score or event.impact_score
        min_percent = sizing.get("min_percent", 5.0) / 100.0
        max_percent = sizing.get("max_percent", 20.0) / 100.0
        
        # Normalize score (0-100) to position size range
        normalized_score = (score - 0) / 100.0
        position_percent = min_percent + (normalized_score * (max_percent - min_percent))
        
        return capital * position_percent
    
    else:
        # Unknown sizing type, default to equal weight
        logger.warning(f"Unknown position sizing type: {sizing_type}, using equal_weight")
        return capital / 10


def check_exit_condition(
    conditions_json: Optional[Dict[str, Any]], 
    entry_date: Any,
    current_date: Any,
    entry_price: float,
    current_price: float,
    event: Optional[Event] = None
) -> tuple[bool, Optional[str]]:
    """
    Check if exit conditions are met for a position.
    
    Args:
        conditions_json: Dictionary of exit conditions
            Example: {
                "type": "fixed_horizon",
                "days": 7
            } or {
                "type": "take_profit",
                "profit_pct": 10.0
            } or {
                "type": "stop_loss",
                "loss_pct": 5.0
            } or {
                "type": "trailing_stop",
                "trail_pct": 3.0
            }
        entry_date: Date of entry
        current_date: Current date being evaluated
        entry_price: Price at entry
        current_price: Current price
        event: Optional Event object
    
    Returns:
        tuple: (should_exit: bool, exit_reason: str)
    """
    if not conditions_json:
        # Default: exit after 7 days
        holding_days = (current_date - entry_date).days
        if holding_days >= 7:
            return True, "fixed_horizon"
        return False, None
    
    exit_type = conditions_json.get("type", "fixed_horizon")
    
    if exit_type == "fixed_horizon":
        days = conditions_json.get("days", 7)
        holding_days = (current_date - entry_date).days
        if holding_days >= days:
            return True, "fixed_horizon"
    
    elif exit_type == "take_profit":
        profit_pct = conditions_json.get("profit_pct", 10.0)
        current_return = ((current_price - entry_price) / entry_price) * 100
        if current_return >= profit_pct:
            return True, "take_profit"
    
    elif exit_type == "stop_loss":
        loss_pct = conditions_json.get("loss_pct", 5.0)
        current_return = ((current_price - entry_price) / entry_price) * 100
        if current_return <= -loss_pct:
            return True, "stop_loss"
    
    elif exit_type == "combined":
        # Check both take profit and stop loss
        profit_pct = conditions_json.get("profit_pct", 10.0)
        loss_pct = conditions_json.get("loss_pct", 5.0)
        current_return = ((current_price - entry_price) / entry_price) * 100
        
        if current_return >= profit_pct:
            return True, "take_profit"
        elif current_return <= -loss_pct:
            return True, "stop_loss"
    
    return False, None
