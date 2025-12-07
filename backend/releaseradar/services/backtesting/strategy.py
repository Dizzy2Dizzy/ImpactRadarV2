"""
Strategy Definition Framework for Market Echo Engine.

Allows users to define custom trading strategies using Market Echo signals,
bearish/bullish indicators, ML predictions, and social sentiment.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Literal
from enum import Enum
import json


class SignalType(str, Enum):
    """Types of signals available for strategy conditions."""
    IMPACT_SCORE = "impact_score"
    ML_ADJUSTED_SCORE = "ml_adjusted_score"
    DIRECTION = "direction"
    CONFIDENCE = "confidence"
    BEARISH_SIGNAL = "bearish_signal"
    BEARISH_SCORE = "bearish_score"
    HIDDEN_BEARISH_PROB = "hidden_bearish_prob"
    ML_CONFIDENCE = "ml_confidence"
    SOCIAL_SENTIMENT = "social_sentiment"
    SOCIAL_VOLUME_ZSCORE = "social_volume_zscore"
    SOCIAL_INFLUENCER_SENTIMENT = "social_influencer_sentiment"
    EVENT_TYPE = "event_type"
    SECTOR = "sector"
    CONTRARIAN_RATE = "contrarian_rate"


class ComparisonOp(str, Enum):
    """Comparison operators for conditions."""
    GREATER_THAN = ">"
    LESS_THAN = "<"
    GREATER_EQUAL = ">="
    LESS_EQUAL = "<="
    EQUALS = "=="
    NOT_EQUALS = "!="
    IN = "in"
    NOT_IN = "not_in"


class LogicalOp(str, Enum):
    """Logical operators for combining conditions."""
    AND = "and"
    OR = "or"


@dataclass
class SignalCondition:
    """A single condition based on a Market Echo signal."""
    signal_type: SignalType
    operator: ComparisonOp
    value: Any
    
    def evaluate(self, event_data: Dict) -> bool:
        """Evaluate this condition against event data."""
        signal_value = event_data.get(self.signal_type.value)
        
        if signal_value is None:
            return False
        
        try:
            if self.operator == ComparisonOp.GREATER_THAN:
                return signal_value > self.value
            elif self.operator == ComparisonOp.LESS_THAN:
                return signal_value < self.value
            elif self.operator == ComparisonOp.GREATER_EQUAL:
                return signal_value >= self.value
            elif self.operator == ComparisonOp.LESS_EQUAL:
                return signal_value <= self.value
            elif self.operator == ComparisonOp.EQUALS:
                return signal_value == self.value
            elif self.operator == ComparisonOp.NOT_EQUALS:
                return signal_value != self.value
            elif self.operator == ComparisonOp.IN:
                return signal_value in self.value
            elif self.operator == ComparisonOp.NOT_IN:
                return signal_value not in self.value
        except (TypeError, ValueError):
            return False
        
        return False
    
    def to_dict(self) -> Dict:
        return {
            "signal_type": self.signal_type.value,
            "operator": self.operator.value,
            "value": self.value
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "SignalCondition":
        return cls(
            signal_type=SignalType(d["signal_type"]),
            operator=ComparisonOp(d["operator"]),
            value=d["value"]
        )


@dataclass
class ConditionGroup:
    """A group of conditions combined with a logical operator."""
    conditions: List[SignalCondition]
    logical_op: LogicalOp = LogicalOp.AND
    
    def evaluate(self, event_data: Dict) -> bool:
        """Evaluate all conditions in this group."""
        results = [c.evaluate(event_data) for c in self.conditions]
        
        if self.logical_op == LogicalOp.AND:
            return all(results)
        else:
            return any(results)
    
    def to_dict(self) -> Dict:
        return {
            "conditions": [c.to_dict() for c in self.conditions],
            "logical_op": self.logical_op.value
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "ConditionGroup":
        return cls(
            conditions=[SignalCondition.from_dict(c) for c in d["conditions"]],
            logical_op=LogicalOp(d.get("logical_op", "and"))
        )


@dataclass
class ExitCondition:
    """Defines when to exit a position."""
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None
    max_holding_days: Optional[int] = None
    trailing_stop_pct: Optional[float] = None
    exit_on_bearish_signal: bool = False
    exit_on_event: Optional[List[str]] = None
    
    def check_exit(
        self,
        current_return_pct: float,
        days_held: int,
        max_return_pct: float,
        has_bearish_signal: bool = False,
        new_event_type: Optional[str] = None
    ) -> tuple[bool, str]:
        """
        Check if position should be exited.
        
        Returns:
            Tuple of (should_exit, exit_reason)
        """
        if self.stop_loss_pct and current_return_pct <= -self.stop_loss_pct:
            return True, f"stop_loss ({current_return_pct:.2f}%)"
        
        if self.take_profit_pct and current_return_pct >= self.take_profit_pct:
            return True, f"take_profit ({current_return_pct:.2f}%)"
        
        if self.max_holding_days and days_held >= self.max_holding_days:
            return True, f"max_holding_days ({days_held}d)"
        
        if self.trailing_stop_pct and max_return_pct > 0:
            trailing_level = max_return_pct - self.trailing_stop_pct
            if current_return_pct < trailing_level:
                return True, f"trailing_stop ({current_return_pct:.2f}% from peak {max_return_pct:.2f}%)"
        
        if self.exit_on_bearish_signal and has_bearish_signal:
            return True, "bearish_signal"
        
        if self.exit_on_event and new_event_type in self.exit_on_event:
            return True, f"exit_event ({new_event_type})"
        
        return False, ""
    
    def to_dict(self) -> Dict:
        return {
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "max_holding_days": self.max_holding_days,
            "trailing_stop_pct": self.trailing_stop_pct,
            "exit_on_bearish_signal": self.exit_on_bearish_signal,
            "exit_on_event": self.exit_on_event
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "ExitCondition":
        return cls(**d)


class PositionSizing(str, Enum):
    """Position sizing methods."""
    FIXED_AMOUNT = "fixed_amount"
    FIXED_PERCENT = "fixed_percent"
    KELLY_CRITERION = "kelly"
    VOLATILITY_ADJUSTED = "volatility_adjusted"
    CONFIDENCE_SCALED = "confidence_scaled"


@dataclass
class PositionConfig:
    """Configuration for position sizing."""
    sizing_method: PositionSizing = PositionSizing.FIXED_PERCENT
    fixed_amount: float = 10000.0
    portfolio_percent: float = 0.1
    max_position_percent: float = 0.25
    min_position_size: float = 100.0
    max_positions: int = 10
    
    def calculate_size(
        self,
        portfolio_value: float,
        confidence: float = 0.5,
        volatility: float = 0.02
    ) -> float:
        """Calculate position size based on method."""
        if self.sizing_method == PositionSizing.FIXED_AMOUNT:
            size = self.fixed_amount
        
        elif self.sizing_method == PositionSizing.FIXED_PERCENT:
            size = portfolio_value * self.portfolio_percent
        
        elif self.sizing_method == PositionSizing.KELLY_CRITERION:
            win_prob = 0.5 + confidence * 0.2
            win_loss_ratio = 1.5
            kelly_fraction = win_prob - ((1 - win_prob) / win_loss_ratio)
            kelly_fraction = max(0, min(0.25, kelly_fraction))
            size = portfolio_value * kelly_fraction
        
        elif self.sizing_method == PositionSizing.VOLATILITY_ADJUSTED:
            target_risk = 0.02
            size = (portfolio_value * target_risk) / max(volatility, 0.005)
        
        elif self.sizing_method == PositionSizing.CONFIDENCE_SCALED:
            base_size = portfolio_value * self.portfolio_percent
            size = base_size * (0.5 + confidence * 0.5)
        
        else:
            size = self.fixed_amount
        
        max_size = portfolio_value * self.max_position_percent
        size = min(size, max_size)
        
        if size < self.min_position_size:
            size = 0
        
        return size
    
    def to_dict(self) -> Dict:
        return {
            "sizing_method": self.sizing_method.value,
            "fixed_amount": self.fixed_amount,
            "portfolio_percent": self.portfolio_percent,
            "max_position_percent": self.max_position_percent,
            "min_position_size": self.min_position_size,
            "max_positions": self.max_positions
        }
    
    @classmethod
    def from_dict(cls, d: Dict) -> "PositionConfig":
        d = d.copy()
        d["sizing_method"] = PositionSizing(d.get("sizing_method", "fixed_percent"))
        return cls(**d)


@dataclass
class StrategyDefinition:
    """
    Complete strategy definition for backtesting.
    
    Includes entry conditions, exit rules, position sizing, and metadata.
    """
    name: str
    description: str = ""
    version: str = "1.0"
    
    entry_conditions: List[ConditionGroup] = field(default_factory=list)
    entry_logic: LogicalOp = LogicalOp.AND
    
    direction: Literal["long", "short", "both"] = "long"
    
    exit_conditions: ExitCondition = field(default_factory=ExitCondition)
    
    position_config: PositionConfig = field(default_factory=PositionConfig)
    
    allowed_event_types: Optional[List[str]] = None
    allowed_sectors: Optional[List[str]] = None
    excluded_tickers: Optional[List[str]] = None
    
    min_days_between_trades: int = 0
    allow_pyramiding: bool = False
    
    created_at: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def check_entry(self, event_data: Dict) -> bool:
        """Check if entry conditions are met for this event."""
        if self.allowed_event_types:
            if event_data.get("event_type") not in self.allowed_event_types:
                return False
        
        if self.allowed_sectors:
            if event_data.get("sector") not in self.allowed_sectors:
                return False
        
        if self.excluded_tickers:
            if event_data.get("ticker") in self.excluded_tickers:
                return False
        
        if not self.entry_conditions:
            return True
        
        group_results = [g.evaluate(event_data) for g in self.entry_conditions]
        
        if self.entry_logic == LogicalOp.AND:
            return all(group_results)
        else:
            return any(group_results)
    
    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "entry_conditions": [g.to_dict() for g in self.entry_conditions],
            "entry_logic": self.entry_logic.value,
            "direction": self.direction,
            "exit_conditions": self.exit_conditions.to_dict(),
            "position_config": self.position_config.to_dict(),
            "allowed_event_types": self.allowed_event_types,
            "allowed_sectors": self.allowed_sectors,
            "excluded_tickers": self.excluded_tickers,
            "min_days_between_trades": self.min_days_between_trades,
            "allow_pyramiding": self.allow_pyramiding,
            "created_at": self.created_at,
            "tags": self.tags
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
    
    @classmethod
    def from_dict(cls, d: Dict) -> "StrategyDefinition":
        return cls(
            name=d["name"],
            description=d.get("description", ""),
            version=d.get("version", "1.0"),
            entry_conditions=[ConditionGroup.from_dict(g) for g in d.get("entry_conditions", [])],
            entry_logic=LogicalOp(d.get("entry_logic", "and")),
            direction=d.get("direction", "long"),
            exit_conditions=ExitCondition.from_dict(d.get("exit_conditions", {})),
            position_config=PositionConfig.from_dict(d.get("position_config", {})),
            allowed_event_types=d.get("allowed_event_types"),
            allowed_sectors=d.get("allowed_sectors"),
            excluded_tickers=d.get("excluded_tickers"),
            min_days_between_trades=d.get("min_days_between_trades", 0),
            allow_pyramiding=d.get("allow_pyramiding", False),
            created_at=d.get("created_at"),
            tags=d.get("tags", [])
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "StrategyDefinition":
        return cls.from_dict(json.loads(json_str))


PRESET_STRATEGIES = {
    "high_impact_momentum": StrategyDefinition(
        name="High Impact Momentum",
        description="Enter on high-impact positive events with strong ML confidence",
        entry_conditions=[
            ConditionGroup(conditions=[
                SignalCondition(SignalType.ML_ADJUSTED_SCORE, ComparisonOp.GREATER_EQUAL, 65),
                SignalCondition(SignalType.DIRECTION, ComparisonOp.EQUALS, "positive"),
                SignalCondition(SignalType.ML_CONFIDENCE, ComparisonOp.GREATER_EQUAL, 0.6)
            ])
        ],
        exit_conditions=ExitCondition(
            stop_loss_pct=5.0,
            take_profit_pct=15.0,
            max_holding_days=10,
            exit_on_bearish_signal=True
        ),
        position_config=PositionConfig(
            sizing_method=PositionSizing.CONFIDENCE_SCALED,
            portfolio_percent=0.1
        ),
        tags=["momentum", "ml-driven"]
    ),
    
    "bearish_fade": StrategyDefinition(
        name="Bearish Signal Fade",
        description="Short positions on strong bearish signals",
        direction="short",
        entry_conditions=[
            ConditionGroup(conditions=[
                SignalCondition(SignalType.BEARISH_SIGNAL, ComparisonOp.EQUALS, True),
                SignalCondition(SignalType.BEARISH_SCORE, ComparisonOp.GREATER_EQUAL, 0.6)
            ])
        ],
        exit_conditions=ExitCondition(
            stop_loss_pct=8.0,
            take_profit_pct=12.0,
            max_holding_days=5
        ),
        position_config=PositionConfig(
            sizing_method=PositionSizing.FIXED_PERCENT,
            portfolio_percent=0.05
        ),
        tags=["bearish", "contrarian"]
    ),
    
    "hidden_bearish_contrarian": StrategyDefinition(
        name="Hidden Bearish Contrarian",
        description="Short events with high hidden bearish probability from Market Echo learning",
        direction="short",
        entry_conditions=[
            ConditionGroup(conditions=[
                SignalCondition(SignalType.HIDDEN_BEARISH_PROB, ComparisonOp.GREATER_EQUAL, 0.5),
                SignalCondition(SignalType.DIRECTION, ComparisonOp.IN, ["positive", "neutral"])
            ])
        ],
        exit_conditions=ExitCondition(
            stop_loss_pct=10.0,
            take_profit_pct=8.0,
            max_holding_days=3
        ),
        position_config=PositionConfig(
            sizing_method=PositionSizing.KELLY_CRITERION
        ),
        tags=["contrarian", "hidden-bearish", "ml-driven"]
    ),
    
    "social_sentiment_surge": StrategyDefinition(
        name="Social Sentiment Surge",
        description="Enter on events with positive social sentiment and high volume",
        entry_conditions=[
            ConditionGroup(conditions=[
                SignalCondition(SignalType.SOCIAL_SENTIMENT, ComparisonOp.GREATER_EQUAL, 0.4),
                SignalCondition(SignalType.SOCIAL_VOLUME_ZSCORE, ComparisonOp.GREATER_EQUAL, 2.0),
                SignalCondition(SignalType.ML_ADJUSTED_SCORE, ComparisonOp.GREATER_EQUAL, 55)
            ])
        ],
        exit_conditions=ExitCondition(
            stop_loss_pct=7.0,
            take_profit_pct=20.0,
            max_holding_days=7,
            trailing_stop_pct=5.0
        ),
        tags=["sentiment", "momentum"]
    )
}
