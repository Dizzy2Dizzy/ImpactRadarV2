"""
Backtest Simulator for Market Echo Engine.

Executes trading strategies against historical event data with realistic
position tracking, P&L calculation, and trade logging.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum
import numpy as np

from releaseradar.log_config import logger
from .strategy import StrategyDefinition


class TradeDirection(str, Enum):
    LONG = "long"
    SHORT = "short"


class TradeStatus(str, Enum):
    OPEN = "open"
    CLOSED = "closed"


@dataclass
class Trade:
    """Represents a single trade in the backtest."""
    trade_id: int
    ticker: str
    event_id: int
    event_type: str
    direction: TradeDirection
    
    entry_date: datetime
    entry_price: float
    position_size: float
    
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    
    status: TradeStatus = TradeStatus.OPEN
    
    pnl_dollars: float = 0.0
    pnl_percent: float = 0.0
    max_drawdown_pct: float = 0.0
    max_profit_pct: float = 0.0
    
    entry_signals: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_pnl(self, current_price: float) -> Tuple[float, float]:
        """Calculate P&L at given price."""
        if self.direction == TradeDirection.LONG:
            pct_change = (current_price - self.entry_price) / self.entry_price * 100
        else:
            pct_change = (self.entry_price - current_price) / self.entry_price * 100
        
        pnl_dollars = self.position_size * (pct_change / 100)
        return pnl_dollars, pct_change
    
    def close(self, exit_price: float, exit_date: datetime, exit_reason: str):
        """Close the trade."""
        self.exit_price = exit_price
        self.exit_date = exit_date
        self.exit_reason = exit_reason
        self.status = TradeStatus.CLOSED
        
        self.pnl_dollars, self.pnl_percent = self.calculate_pnl(exit_price)
    
    def update_extremes(self, current_price: float):
        """Update max drawdown and max profit tracking."""
        _, pct = self.calculate_pnl(current_price)
        self.max_profit_pct = max(self.max_profit_pct, pct)
        self.max_drawdown_pct = min(self.max_drawdown_pct, pct)
    
    def to_dict(self) -> Dict:
        return {
            "trade_id": self.trade_id,
            "ticker": self.ticker,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "direction": self.direction.value,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "entry_price": self.entry_price,
            "position_size": self.position_size,
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "exit_price": self.exit_price,
            "exit_reason": self.exit_reason,
            "status": self.status.value,
            "pnl_dollars": self.pnl_dollars,
            "pnl_percent": self.pnl_percent,
            "max_drawdown_pct": self.max_drawdown_pct,
            "max_profit_pct": self.max_profit_pct,
            "entry_signals": self.entry_signals
        }


@dataclass
class PortfolioState:
    """Current state of the backtest portfolio."""
    initial_capital: float
    cash: float
    positions: Dict[str, Trade] = field(default_factory=dict)
    closed_trades: List[Trade] = field(default_factory=list)
    
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    
    last_trade_date: Dict[str, datetime] = field(default_factory=dict)
    
    @property
    def current_equity(self) -> float:
        """Calculate current portfolio equity."""
        position_value = sum(t.position_size + t.pnl_dollars for t in self.positions.values())
        return self.cash + position_value
    
    @property
    def open_position_count(self) -> int:
        return len(self.positions)
    
    @property
    def total_return_pct(self) -> float:
        return (self.current_equity / self.initial_capital - 1) * 100
    
    @property
    def win_rate(self) -> float:
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades
    
    def record_equity(self, date: datetime):
        """Record current equity for equity curve."""
        self.equity_curve.append((date, self.current_equity))
    
    def to_dict(self) -> Dict:
        return {
            "initial_capital": self.initial_capital,
            "current_equity": self.current_equity,
            "cash": self.cash,
            "total_return_pct": self.total_return_pct,
            "open_positions": self.open_position_count,
            "total_trades": self.total_trades,
            "winning_trades": self.winning_trades,
            "losing_trades": self.losing_trades,
            "win_rate": self.win_rate
        }


@dataclass
class EventData:
    """Event data for backtest simulation."""
    event_id: int
    ticker: str
    date: datetime
    event_type: str
    
    impact_score: int
    ml_adjusted_score: Optional[int]
    direction: str
    confidence: float
    ml_confidence: Optional[float]
    
    bearish_signal: bool
    bearish_score: Optional[float]
    hidden_bearish_prob: Optional[float]
    
    sector: Optional[str]
    
    price_at_event: float
    price_1d: Optional[float]
    price_5d: Optional[float]
    price_20d: Optional[float]
    
    social_sentiment: Optional[float] = None
    social_volume_zscore: Optional[float] = None
    social_influencer_sentiment: Optional[float] = None
    contrarian_rate: Optional[float] = None
    
    def to_signal_dict(self) -> Dict:
        """Convert to dictionary for signal evaluation."""
        return {
            "event_id": self.event_id,
            "ticker": self.ticker,
            "event_type": self.event_type,
            "impact_score": self.impact_score,
            "ml_adjusted_score": self.ml_adjusted_score,
            "direction": self.direction,
            "confidence": self.confidence,
            "ml_confidence": self.ml_confidence,
            "bearish_signal": self.bearish_signal,
            "bearish_score": self.bearish_score,
            "hidden_bearish_prob": self.hidden_bearish_prob,
            "sector": self.sector,
            "social_sentiment": self.social_sentiment,
            "social_volume_zscore": self.social_volume_zscore,
            "social_influencer_sentiment": self.social_influencer_sentiment,
            "contrarian_rate": self.contrarian_rate
        }


class BacktestSimulator:
    """
    Executes trading strategies against historical event data.
    
    Features:
    - Event-driven execution
    - Position tracking with P&L
    - Multiple exit conditions
    - Equity curve generation
    - Trade logging
    """
    
    def __init__(
        self,
        strategy: StrategyDefinition,
        initial_capital: float = 100000.0
    ):
        self.strategy = strategy
        self.initial_capital = initial_capital
        self.portfolio = None
        self.trade_counter = 0
    
    def reset(self):
        """Reset simulator state for new backtest."""
        self.portfolio = PortfolioState(
            initial_capital=self.initial_capital,
            cash=self.initial_capital
        )
        self.trade_counter = 0
    
    def run(self, events: List[EventData]) -> PortfolioState:
        """
        Run backtest on list of events.
        
        Args:
            events: List of EventData sorted by date
            
        Returns:
            Final PortfolioState with all trades and metrics
        """
        self.reset()
        
        events_sorted = sorted(events, key=lambda e: e.date)
        
        for i, event in enumerate(events_sorted):
            self._process_open_positions(event)
            
            if self._should_enter(event):
                self._open_position(event)
            
            self.portfolio.record_equity(event.date)
        
        self._close_all_positions(events_sorted[-1].date if events_sorted else datetime.utcnow())
        
        return self.portfolio
    
    def _should_enter(self, event: EventData) -> bool:
        """Check if strategy entry conditions are met."""
        if self.portfolio.open_position_count >= self.strategy.position_config.max_positions:
            return False
        
        if not self.strategy.allow_pyramiding:
            if event.ticker in self.portfolio.positions:
                return False
        
        if self.strategy.min_days_between_trades > 0:
            last_trade = self.portfolio.last_trade_date.get(event.ticker)
            if last_trade:
                days_since = (event.date - last_trade).days
                if days_since < self.strategy.min_days_between_trades:
                    return False
        
        return self.strategy.check_entry(event.to_signal_dict())
    
    def _open_position(self, event: EventData):
        """Open a new position based on event."""
        confidence = event.ml_confidence or event.confidence
        position_size = self.strategy.position_config.calculate_size(
            portfolio_value=self.portfolio.current_equity,
            confidence=confidence
        )
        
        if position_size <= 0:
            return
        
        if position_size > self.portfolio.cash:
            position_size = self.portfolio.cash
        
        if position_size < self.strategy.position_config.min_position_size:
            return
        
        direction = TradeDirection.LONG
        if self.strategy.direction == "short":
            direction = TradeDirection.SHORT
        elif self.strategy.direction == "both":
            if event.bearish_signal or (event.direction == "negative"):
                direction = TradeDirection.SHORT
        
        self.trade_counter += 1
        trade = Trade(
            trade_id=self.trade_counter,
            ticker=event.ticker,
            event_id=event.event_id,
            event_type=event.event_type,
            direction=direction,
            entry_date=event.date,
            entry_price=event.price_at_event,
            position_size=position_size,
            entry_signals={
                "impact_score": event.impact_score,
                "ml_adjusted_score": event.ml_adjusted_score,
                "direction": event.direction,
                "bearish_signal": event.bearish_signal,
                "confidence": confidence
            }
        )
        
        self.portfolio.positions[event.ticker] = trade
        self.portfolio.cash -= position_size
        self.portfolio.last_trade_date[event.ticker] = event.date
        
        logger.debug(f"Opened {direction.value} position: {event.ticker} @ {event.price_at_event}")
    
    def _process_open_positions(self, event: EventData):
        """Update and check exits for all open positions."""
        positions_to_close = []
        
        for ticker, trade in list(self.portfolio.positions.items()):
            if ticker == event.ticker:
                current_price = event.price_at_event
            elif trade.entry_date < event.date:
                days_held = (event.date - trade.entry_date).days
                if days_held <= 1 and event.price_1d:
                    current_price = event.price_1d
                elif days_held <= 5 and event.price_5d:
                    current_price = event.price_5d
                else:
                    current_price = trade.entry_price * (1 + np.random.normal(0, 0.02))
            else:
                continue
            
            trade.update_extremes(current_price)
            
            current_pnl_pct = trade.calculate_pnl(current_price)[1]
            days_held = (event.date - trade.entry_date).days
            
            should_exit, exit_reason = self.strategy.exit_conditions.check_exit(
                current_return_pct=current_pnl_pct,
                days_held=days_held,
                max_return_pct=trade.max_profit_pct,
                has_bearish_signal=event.bearish_signal if ticker == event.ticker else False,
                new_event_type=event.event_type if ticker == event.ticker else None
            )
            
            if should_exit:
                positions_to_close.append((trade, current_price, event.date, exit_reason))
        
        for trade, exit_price, exit_date, exit_reason in positions_to_close:
            self._close_position(trade, exit_price, exit_date, exit_reason)
    
    def _close_position(
        self,
        trade: Trade,
        exit_price: float,
        exit_date: datetime,
        exit_reason: str
    ):
        """Close a position and record the trade."""
        trade.close(exit_price, exit_date, exit_reason)
        
        self.portfolio.cash += trade.position_size + trade.pnl_dollars
        
        if trade.ticker in self.portfolio.positions:
            del self.portfolio.positions[trade.ticker]
        
        self.portfolio.closed_trades.append(trade)
        self.portfolio.total_trades += 1
        
        if trade.pnl_dollars >= 0:
            self.portfolio.winning_trades += 1
        else:
            self.portfolio.losing_trades += 1
        
        logger.debug(
            f"Closed {trade.ticker}: {trade.pnl_percent:.2f}% ({exit_reason})"
        )
    
    def _close_all_positions(self, final_date: datetime):
        """Close all remaining positions at end of backtest."""
        for ticker, trade in list(self.portfolio.positions.items()):
            estimated_price = trade.entry_price * (1 + trade.max_profit_pct / 100 * 0.5)
            self._close_position(trade, estimated_price, final_date, "end_of_backtest")
