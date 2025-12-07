"""Backtesting framework for Market Echo Engine trading strategies."""
from .strategy import StrategyDefinition, SignalCondition, ExitCondition, ConditionGroup, PositionConfig
from .simulator import BacktestSimulator, Trade, PortfolioState, EventData
from .metrics import BacktestMetrics, MetricsSuite
from .engine import BacktestEngine, BacktestEngineResult, BacktestPeriod, TradeRecord, run_backtest_with_engine

__all__ = [
    "StrategyDefinition",
    "SignalCondition",
    "ConditionGroup",
    "ExitCondition",
    "PositionConfig",
    "BacktestSimulator",
    "Trade",
    "PortfolioState",
    "EventData",
    "BacktestMetrics",
    "MetricsSuite",
    "BacktestEngine",
    "BacktestEngineResult",
    "BacktestPeriod",
    "TradeRecord",
    "run_backtest_with_engine"
]
