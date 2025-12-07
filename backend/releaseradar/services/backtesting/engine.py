"""
BacktestEngine - Main orchestration service for the backtesting framework.

Wires together strategy evaluation, event simulation, and metrics calculation
to provide comprehensive backtesting capabilities for Market Echo Engine.
"""

from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from typing import List, Dict, Optional, Any, Tuple
import logging

from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import numpy as np

from releaseradar.db.models import (
    Event,
    PriceHistory,
    EventOutcome,
    UserStrategy,
    BacktestRun,
    BacktestResult as BacktestResultDB,
    SocialEventSignal,
)
from .strategy import StrategyDefinition, ConditionGroup, ExitCondition, PositionConfig
from .simulator import BacktestSimulator, EventData, Trade, PortfolioState
from .metrics import MetricsSuite, BacktestMetrics

logger = logging.getLogger(__name__)


@dataclass
class BacktestPeriod:
    """Defines the time period for backtesting."""
    start_date: date
    end_date: date
    
    @property
    def days(self) -> int:
        return (self.end_date - self.start_date).days
    
    @property
    def years(self) -> float:
        return self.days / 365.25
    
    def to_dict(self) -> Dict:
        return {
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "days": self.days,
            "years": round(self.years, 2)
        }


@dataclass
class TradeRecord:
    """Simplified trade record for result output."""
    trade_id: int
    ticker: str
    event_id: int
    event_type: str
    direction: str
    entry_date: datetime
    entry_price: float
    exit_date: Optional[datetime]
    exit_price: Optional[float]
    position_size: float
    pnl_dollars: float
    pnl_percent: float
    exit_reason: Optional[str]
    holding_days: int
    
    def to_dict(self) -> Dict:
        return {
            "trade_id": self.trade_id,
            "ticker": self.ticker,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "direction": self.direction,
            "entry_date": self.entry_date.isoformat() if self.entry_date else None,
            "entry_price": round(self.entry_price, 2),
            "exit_date": self.exit_date.isoformat() if self.exit_date else None,
            "exit_price": round(self.exit_price, 2) if self.exit_price else None,
            "position_size": round(self.position_size, 2),
            "pnl_dollars": round(self.pnl_dollars, 2),
            "pnl_percent": round(self.pnl_percent, 2),
            "exit_reason": self.exit_reason,
            "holding_days": self.holding_days
        }
    
    @classmethod
    def from_trade(cls, trade: Trade) -> "TradeRecord":
        """Create TradeRecord from simulator Trade."""
        holding_days = 0
        if trade.exit_date and trade.entry_date:
            holding_days = (trade.exit_date - trade.entry_date).days
        
        return cls(
            trade_id=trade.trade_id,
            ticker=trade.ticker,
            event_id=trade.event_id,
            event_type=trade.event_type,
            direction=trade.direction.value,
            entry_date=trade.entry_date,
            entry_price=trade.entry_price,
            exit_date=trade.exit_date,
            exit_price=trade.exit_price,
            position_size=trade.position_size,
            pnl_dollars=trade.pnl_dollars,
            pnl_percent=trade.pnl_percent,
            exit_reason=trade.exit_reason,
            holding_days=holding_days
        )


@dataclass
class EquityPoint:
    """Single point on the equity curve."""
    date: datetime
    equity: float
    
    def to_dict(self) -> Dict:
        return {
            "date": self.date.isoformat(),
            "equity": round(self.equity, 2)
        }


@dataclass
class BacktestEngineResult:
    """Complete result from backtest execution.
    
    Contains the strategy used, all computed metrics, trade history,
    equity curve, and period information.
    """
    strategy: StrategyDefinition
    metrics: BacktestMetrics
    trades: List[TradeRecord]
    equity_curve: List[EquityPoint]
    period: BacktestPeriod
    initial_capital: float
    final_equity: float
    events_processed: int
    events_matched: int
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for API response."""
        return {
            "strategy": {
                "name": self.strategy.name,
                "description": self.strategy.description,
                "version": self.strategy.version,
                "direction": self.strategy.direction
            },
            "metrics": self.metrics.to_dict(),
            "trades": [t.to_dict() for t in self.trades],
            "equity_curve": [e.to_dict() for e in self.equity_curve],
            "period": self.period.to_dict(),
            "summary": {
                "initial_capital": round(self.initial_capital, 2),
                "final_equity": round(self.final_equity, 2),
                "total_return_pct": round((self.final_equity / self.initial_capital - 1) * 100, 2),
                "events_processed": self.events_processed,
                "events_matched": self.events_matched,
                "total_trades": len(self.trades)
            }
        }


class BacktestEngine:
    """
    Main orchestration service for backtesting trading strategies.
    
    Wires together:
    - Database event loading with filtering
    - Strategy condition evaluation
    - BacktestSimulator for position tracking and P&L
    - MetricsSuite for performance metrics calculation
    
    Usage:
        engine = BacktestEngine(db_session, initial_capital=100000)
        result = engine.run_backtest(
            strategy=strategy_def,
            start_date=date(2023, 1, 1),
            end_date=date(2023, 12, 31)
        )
    """
    
    def __init__(
        self,
        db: Session,
        initial_capital: float = 100000.0
    ):
        """
        Initialize the backtest engine.
        
        Args:
            db: SQLAlchemy database session
            initial_capital: Starting capital for backtests
        """
        self.db = db
        self.initial_capital = initial_capital
    
    def run_backtest(
        self,
        strategy: StrategyDefinition,
        start_date: date,
        end_date: date,
        tickers: Optional[List[str]] = None,
        sectors: Optional[List[str]] = None,
        min_score: Optional[int] = None
    ) -> BacktestEngineResult:
        """
        Execute a backtest for a given strategy over a date range.
        
        Args:
            strategy: StrategyDefinition containing entry/exit conditions
            start_date: Start date for the backtest period
            end_date: End date for the backtest period
            tickers: Optional list of tickers to filter (overrides strategy filters)
            sectors: Optional list of sectors to filter (overrides strategy filters)
            min_score: Optional minimum impact score threshold
        
        Returns:
            BacktestEngineResult with complete metrics, trades, and equity curve
        
        Raises:
            ValueError: If strategy is invalid or date range is invalid
        """
        self._validate_inputs(strategy, start_date, end_date)
        
        logger.info(
            f"Starting backtest: strategy='{strategy.name}', "
            f"period={start_date} to {end_date}, capital=${self.initial_capital:,.0f}"
        )
        
        events = self._load_events(
            start_date=start_date,
            end_date=end_date,
            tickers=tickers or strategy.allowed_event_types,
            sectors=sectors or strategy.allowed_sectors,
            min_score=min_score
        )
        
        if not events:
            logger.warning(f"No events found for backtest period {start_date} to {end_date}")
            return self._create_empty_result(strategy, start_date, end_date)
        
        logger.info(f"Loaded {len(events)} events for backtest")
        
        event_data_list = self._convert_events_to_event_data(events)
        events_matched = len(event_data_list)
        
        simulator = BacktestSimulator(
            strategy=strategy,
            initial_capital=self.initial_capital
        )
        
        portfolio = simulator.run(event_data_list)
        
        metrics_suite = MetricsSuite(portfolio)
        metrics = metrics_suite.calculate_all()
        
        trades = [TradeRecord.from_trade(t) for t in portfolio.closed_trades]
        
        equity_curve = [
            EquityPoint(date=dt, equity=eq)
            for dt, eq in portfolio.equity_curve
        ]
        
        period = BacktestPeriod(start_date=start_date, end_date=end_date)
        
        result = BacktestEngineResult(
            strategy=strategy,
            metrics=metrics,
            trades=trades,
            equity_curve=equity_curve,
            period=period,
            initial_capital=self.initial_capital,
            final_equity=portfolio.current_equity,
            events_processed=len(events),
            events_matched=events_matched
        )
        
        logger.info(
            f"Backtest completed: {len(trades)} trades, "
            f"return={result.metrics.total_return_pct:.2f}%, "
            f"sharpe={result.metrics.sharpe_ratio:.2f if result.metrics.sharpe_ratio else 'N/A'}"
        )
        
        return result
    
    def run_backtest_from_db_strategy(
        self,
        strategy_id: int,
        start_date: date,
        end_date: date
    ) -> Tuple[BacktestEngineResult, BacktestRun]:
        """
        Run backtest using a UserStrategy from the database.
        
        Creates BacktestRun and BacktestResult records in the database.
        
        Args:
            strategy_id: ID of the UserStrategy to backtest
            start_date: Start date for backtest
            end_date: End date for backtest
        
        Returns:
            Tuple of (BacktestEngineResult, BacktestRun database record)
        """
        user_strategy = self.db.query(UserStrategy).filter(
            UserStrategy.id == strategy_id
        ).first()
        
        if not user_strategy:
            raise ValueError(f"Strategy {strategy_id} not found")
        
        strategy_def = self._convert_db_strategy(user_strategy)
        
        backtest_run = BacktestRun(
            strategy_id=strategy_id,
            user_id=user_strategy.user_id,
            start_date=start_date,
            end_date=end_date,
            initial_capital=self.initial_capital,
            status="running",
            started_at=datetime.utcnow()
        )
        self.db.add(backtest_run)
        self.db.commit()
        self.db.refresh(backtest_run)
        
        try:
            result = self.run_backtest(
                strategy=strategy_def,
                start_date=start_date,
                end_date=end_date,
                tickers=user_strategy.tickers,
                sectors=user_strategy.sectors,
                min_score=user_strategy.min_score_threshold
            )
            
            self._save_backtest_results(backtest_run.id, result)
            
            backtest_run.status = "completed"
            backtest_run.completed_at = datetime.utcnow()
            backtest_run.total_trades = len(result.trades)
            backtest_run.win_rate = result.metrics.win_rate * 100
            backtest_run.total_return_pct = result.metrics.total_return_pct
            backtest_run.sharpe_ratio = result.metrics.sharpe_ratio
            backtest_run.sortino_ratio = result.metrics.sortino_ratio
            backtest_run.max_drawdown_pct = result.metrics.max_drawdown_pct
            
            self.db.commit()
            self.db.refresh(backtest_run)
            
            return result, backtest_run
            
        except Exception as e:
            logger.error(f"Backtest failed: {str(e)}", exc_info=True)
            backtest_run.status = "failed"
            backtest_run.completed_at = datetime.utcnow()
            backtest_run.error_message = str(e)
            self.db.commit()
            raise
    
    def _validate_inputs(
        self,
        strategy: StrategyDefinition,
        start_date: date,
        end_date: date
    ):
        """Validate backtest inputs."""
        if not strategy:
            raise ValueError("Strategy definition is required")
        
        if not strategy.name:
            raise ValueError("Strategy must have a name")
        
        if start_date >= end_date:
            raise ValueError(
                f"Start date ({start_date}) must be before end date ({end_date})"
            )
        
        if (end_date - start_date).days > 365 * 10:
            raise ValueError("Backtest period cannot exceed 10 years")
        
        if end_date > date.today():
            raise ValueError("End date cannot be in the future")
    
    def _load_events(
        self,
        start_date: date,
        end_date: date,
        tickers: Optional[List[str]] = None,
        sectors: Optional[List[str]] = None,
        min_score: Optional[int] = None
    ) -> List[Event]:
        """Load events from database with filters."""
        query = self.db.query(Event).filter(
            and_(
                Event.date >= datetime.combine(start_date, datetime.min.time()),
                Event.date <= datetime.combine(end_date, datetime.max.time())
            )
        )
        
        if tickers:
            query = query.filter(Event.ticker.in_(tickers))
        
        if sectors:
            query = query.filter(Event.sector.in_(sectors))
        
        if min_score:
            query = query.filter(
                or_(
                    Event.ml_adjusted_score >= min_score,
                    and_(
                        Event.ml_adjusted_score.is_(None),
                        Event.impact_score >= min_score
                    )
                )
            )
        
        events = query.order_by(Event.date).all()
        return events
    
    def _convert_events_to_event_data(
        self,
        events: List[Event]
    ) -> List[EventData]:
        """Convert database Event models to EventData for simulator."""
        event_data_list = []
        
        price_cache: Dict[str, Dict[date, float]] = {}
        
        for event in events:
            try:
                event_date = event.date.date() if hasattr(event.date, 'date') else event.date
                
                price_at_event = self._get_price(
                    event.ticker, event_date, price_cache
                )
                
                if price_at_event is None or price_at_event <= 0:
                    logger.debug(
                        f"Skipping event {event.id}: no valid price for {event.ticker} on {event_date}"
                    )
                    continue
                
                price_1d = self._get_price(
                    event.ticker, event_date + timedelta(days=1), price_cache
                )
                price_5d = self._get_price(
                    event.ticker, event_date + timedelta(days=5), price_cache
                )
                price_20d = self._get_price(
                    event.ticker, event_date + timedelta(days=20), price_cache
                )
                
                social_signal = self._get_social_signal(event.id)
                
                event_data = EventData(
                    event_id=event.id,
                    ticker=event.ticker,
                    date=event.date if isinstance(event.date, datetime) else datetime.combine(event.date, datetime.min.time()),
                    event_type=event.event_type,
                    impact_score=event.impact_score or 50,
                    ml_adjusted_score=event.ml_adjusted_score,
                    direction=event.direction or "neutral",
                    confidence=event.confidence or 0.5,
                    ml_confidence=event.ml_confidence,
                    bearish_signal=event.bearish_signal or False,
                    bearish_score=event.bearish_score,
                    hidden_bearish_prob=event.hidden_bearish_prob,
                    sector=event.sector,
                    price_at_event=price_at_event,
                    price_1d=price_1d,
                    price_5d=price_5d,
                    price_20d=price_20d,
                    social_sentiment=social_signal.get("sentiment") if social_signal else None,
                    social_volume_zscore=social_signal.get("volume_zscore") if social_signal else None,
                    social_influencer_sentiment=social_signal.get("influencer_sentiment") if social_signal else None,
                    contrarian_rate=None
                )
                
                event_data_list.append(event_data)
                
            except Exception as e:
                logger.warning(
                    f"Error converting event {event.id} ({event.ticker}): {str(e)}"
                )
                continue
        
        return event_data_list
    
    def _get_price(
        self,
        ticker: str,
        target_date: date,
        cache: Dict[str, Dict[date, float]]
    ) -> Optional[float]:
        """Get price for a ticker on a specific date, with caching."""
        if ticker not in cache:
            cache[ticker] = {}
        
        if target_date in cache[ticker]:
            return cache[ticker][target_date]
        
        price_record = self.db.query(PriceHistory).filter(
            and_(
                PriceHistory.ticker == ticker,
                PriceHistory.date >= target_date
            )
        ).order_by(PriceHistory.date).first()
        
        if price_record and price_record.close:
            cache[ticker][target_date] = price_record.close
            return price_record.close
        
        return None
    
    def _get_social_signal(self, event_id: int) -> Optional[Dict]:
        """Get social sentiment signal for an event."""
        signal = self.db.query(SocialEventSignal).filter(
            SocialEventSignal.event_id == event_id
        ).first()
        
        if signal:
            return {
                "sentiment": signal.avg_sentiment,
                "volume_zscore": signal.volume_zscore,
                "influencer_sentiment": signal.influencer_sentiment
            }
        
        return None
    
    def _convert_db_strategy(self, user_strategy: UserStrategy) -> StrategyDefinition:
        """Convert database UserStrategy to StrategyDefinition."""
        entry_conditions = []
        if user_strategy.entry_conditions:
            try:
                conditions_data = user_strategy.entry_conditions
                if isinstance(conditions_data, list):
                    entry_conditions = [
                        ConditionGroup.from_dict(g) for g in conditions_data
                    ]
                elif isinstance(conditions_data, dict):
                    entry_conditions = [ConditionGroup.from_dict(conditions_data)]
            except Exception as e:
                logger.warning(f"Error parsing entry conditions: {e}")
        
        exit_conditions = ExitCondition()
        if user_strategy.exit_conditions:
            try:
                exit_data = user_strategy.exit_conditions
                if isinstance(exit_data, dict):
                    exit_type = exit_data.get("type", "fixed_horizon")
                    if exit_type == "fixed_horizon":
                        exit_conditions = ExitCondition(
                            max_holding_days=exit_data.get("days", 5)
                        )
                    else:
                        exit_conditions = ExitCondition.from_dict(exit_data)
            except Exception as e:
                logger.warning(f"Error parsing exit conditions: {e}")
        
        position_config = PositionConfig()
        if user_strategy.position_sizing:
            try:
                position_config = PositionConfig.from_dict(user_strategy.position_sizing)
            except Exception as e:
                logger.warning(f"Error parsing position sizing: {e}")
        
        return StrategyDefinition(
            name=user_strategy.name,
            description=user_strategy.description or "",
            entry_conditions=entry_conditions,
            exit_conditions=exit_conditions,
            position_config=position_config,
            allowed_event_types=user_strategy.tickers,
            allowed_sectors=user_strategy.sectors
        )
    
    def _save_backtest_results(
        self,
        run_id: int,
        result: BacktestEngineResult
    ):
        """Save individual trade results to database."""
        for trade in result.trades:
            db_result = BacktestResultDB(
                run_id=run_id,
                ticker=trade.ticker,
                event_id=trade.event_id,
                entry_date=trade.entry_date.date() if isinstance(trade.entry_date, datetime) else trade.entry_date,
                entry_price=trade.entry_price,
                exit_date=trade.exit_date.date() if trade.exit_date and isinstance(trade.exit_date, datetime) else trade.exit_date,
                exit_price=trade.exit_price,
                shares=trade.position_size / trade.entry_price if trade.entry_price > 0 else 0,
                position_value=trade.position_size,
                return_pct=trade.pnl_percent,
                profit_loss=trade.pnl_dollars,
                exit_reason=trade.exit_reason,
                holding_period_days=trade.holding_days
            )
            self.db.add(db_result)
        
        self.db.commit()
    
    def _create_empty_result(
        self,
        strategy: StrategyDefinition,
        start_date: date,
        end_date: date
    ) -> BacktestEngineResult:
        """Create an empty result when no events match."""
        empty_metrics = BacktestMetrics(
            total_return_pct=0.0,
            total_return_dollars=0.0,
            cagr=0.0,
            annual_volatility=0.0,
            max_drawdown_pct=0.0,
            max_drawdown_dollars=0.0,
            max_drawdown_duration_days=0,
            sharpe_ratio=None,
            sortino_ratio=None,
            calmar_ratio=None,
            var_95=0.0,
            cvar_95=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate=0.0,
            avg_win_pct=0.0,
            avg_loss_pct=0.0,
            profit_factor=0.0,
            expectancy=0.0,
            avg_holding_days=0.0,
            max_consecutive_wins=0,
            max_consecutive_losses=0,
            avg_trade_return=0.0,
            best_trade_pct=0.0,
            worst_trade_pct=0.0,
            long_trades=0,
            short_trades=0,
            long_win_rate=0.0,
            short_win_rate=0.0,
            trading_days=0,
            start_date=datetime.combine(start_date, datetime.min.time()),
            end_date=datetime.combine(end_date, datetime.max.time())
        )
        
        return BacktestEngineResult(
            strategy=strategy,
            metrics=empty_metrics,
            trades=[],
            equity_curve=[
                EquityPoint(
                    date=datetime.combine(start_date, datetime.min.time()),
                    equity=self.initial_capital
                )
            ],
            period=BacktestPeriod(start_date=start_date, end_date=end_date),
            initial_capital=self.initial_capital,
            final_equity=self.initial_capital,
            events_processed=0,
            events_matched=0
        )


def run_backtest_with_engine(
    strategy_id: int,
    start_date: date,
    end_date: date,
    initial_capital: float,
    db: Session
) -> BacktestRun:
    """
    Convenience function to run a backtest using BacktestEngine.
    
    Compatible with the existing run_backtest interface in backtesting_engine.py.
    
    Args:
        strategy_id: ID of the UserStrategy to backtest
        start_date: Start date for backtest
        end_date: End date for backtest
        initial_capital: Starting capital
        db: Database session
    
    Returns:
        BacktestRun database record with results
    """
    engine = BacktestEngine(db=db, initial_capital=initial_capital)
    _, backtest_run = engine.run_backtest_from_db_strategy(
        strategy_id=strategy_id,
        start_date=start_date,
        end_date=end_date
    )
    return backtest_run
