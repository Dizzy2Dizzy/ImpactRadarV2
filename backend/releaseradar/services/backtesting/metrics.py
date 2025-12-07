"""
Backtest Metrics Calculation for Market Echo Engine.

Provides comprehensive performance metrics including:
- Returns (total, CAGR, risk-adjusted)
- Risk measures (volatility, VaR, max drawdown)
- Trade statistics (win rate, expectancy, profit factor)
- Benchmark comparison
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

from .simulator import PortfolioState, Trade


@dataclass
class BacktestMetrics:
    """Complete backtest performance metrics."""
    
    total_return_pct: float
    total_return_dollars: float
    cagr: float
    
    annual_volatility: float
    max_drawdown_pct: float
    max_drawdown_dollars: float
    max_drawdown_duration_days: int
    
    sharpe_ratio: Optional[float]
    sortino_ratio: Optional[float]
    calmar_ratio: Optional[float]
    
    var_95: float
    cvar_95: float
    
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    expectancy: float
    
    avg_holding_days: float
    max_consecutive_wins: int
    max_consecutive_losses: int
    
    avg_trade_return: float
    best_trade_pct: float
    worst_trade_pct: float
    
    long_trades: int
    short_trades: int
    long_win_rate: float
    short_win_rate: float
    
    trading_days: int
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    monthly_returns: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "returns": {
                "total_return_pct": round(self.total_return_pct, 2),
                "total_return_dollars": round(self.total_return_dollars, 2),
                "cagr": round(self.cagr, 2) if self.cagr else None,
            },
            "risk": {
                "annual_volatility": round(self.annual_volatility, 2),
                "max_drawdown_pct": round(self.max_drawdown_pct, 2),
                "max_drawdown_dollars": round(self.max_drawdown_dollars, 2),
                "max_drawdown_duration_days": self.max_drawdown_duration_days,
                "var_95": round(self.var_95, 2),
                "cvar_95": round(self.cvar_95, 2),
            },
            "risk_adjusted": {
                "sharpe_ratio": round(self.sharpe_ratio, 3) if self.sharpe_ratio else None,
                "sortino_ratio": round(self.sortino_ratio, 3) if self.sortino_ratio else None,
                "calmar_ratio": round(self.calmar_ratio, 3) if self.calmar_ratio else None,
            },
            "trades": {
                "total_trades": self.total_trades,
                "winning_trades": self.winning_trades,
                "losing_trades": self.losing_trades,
                "win_rate": round(self.win_rate * 100, 1),
                "avg_win_pct": round(self.avg_win_pct, 2),
                "avg_loss_pct": round(self.avg_loss_pct, 2),
                "profit_factor": round(self.profit_factor, 2) if self.profit_factor else None,
                "expectancy": round(self.expectancy, 2),
            },
            "trade_details": {
                "avg_holding_days": round(self.avg_holding_days, 1),
                "max_consecutive_wins": self.max_consecutive_wins,
                "max_consecutive_losses": self.max_consecutive_losses,
                "best_trade_pct": round(self.best_trade_pct, 2),
                "worst_trade_pct": round(self.worst_trade_pct, 2),
            },
            "direction_breakdown": {
                "long_trades": self.long_trades,
                "short_trades": self.short_trades,
                "long_win_rate": round(self.long_win_rate * 100, 1),
                "short_win_rate": round(self.short_win_rate * 100, 1),
            },
            "period": {
                "trading_days": self.trading_days,
                "start_date": self.start_date.isoformat() if self.start_date else None,
                "end_date": self.end_date.isoformat() if self.end_date else None,
            },
            "monthly_returns": self.monthly_returns,
        }


class MetricsSuite:
    """Calculates comprehensive backtest metrics from portfolio state."""
    
    RISK_FREE_RATE = 0.05
    TRADING_DAYS_PER_YEAR = 252
    
    def __init__(self, portfolio: PortfolioState):
        self.portfolio = portfolio
        self.trades = portfolio.closed_trades
        self.equity_curve = portfolio.equity_curve
    
    def calculate_all(self) -> BacktestMetrics:
        """Calculate all metrics."""
        return_metrics = self._calculate_returns()
        risk_metrics = self._calculate_risk()
        risk_adjusted = self._calculate_risk_adjusted(return_metrics, risk_metrics)
        trade_stats = self._calculate_trade_statistics()
        direction_stats = self._calculate_direction_breakdown()
        
        return BacktestMetrics(
            total_return_pct=return_metrics["total_return_pct"],
            total_return_dollars=return_metrics["total_return_dollars"],
            cagr=return_metrics["cagr"],
            annual_volatility=risk_metrics["annual_volatility"],
            max_drawdown_pct=risk_metrics["max_drawdown_pct"],
            max_drawdown_dollars=risk_metrics["max_drawdown_dollars"],
            max_drawdown_duration_days=risk_metrics["max_drawdown_duration_days"],
            sharpe_ratio=risk_adjusted["sharpe_ratio"],
            sortino_ratio=risk_adjusted["sortino_ratio"],
            calmar_ratio=risk_adjusted["calmar_ratio"],
            var_95=risk_metrics["var_95"],
            cvar_95=risk_metrics["cvar_95"],
            total_trades=trade_stats["total_trades"],
            winning_trades=trade_stats["winning_trades"],
            losing_trades=trade_stats["losing_trades"],
            win_rate=trade_stats["win_rate"],
            avg_win_pct=trade_stats["avg_win_pct"],
            avg_loss_pct=trade_stats["avg_loss_pct"],
            profit_factor=trade_stats["profit_factor"],
            expectancy=trade_stats["expectancy"],
            avg_holding_days=trade_stats["avg_holding_days"],
            max_consecutive_wins=trade_stats["max_consecutive_wins"],
            max_consecutive_losses=trade_stats["max_consecutive_losses"],
            avg_trade_return=trade_stats["avg_trade_return"],
            best_trade_pct=trade_stats["best_trade_pct"],
            worst_trade_pct=trade_stats["worst_trade_pct"],
            long_trades=direction_stats["long_trades"],
            short_trades=direction_stats["short_trades"],
            long_win_rate=direction_stats["long_win_rate"],
            short_win_rate=direction_stats["short_win_rate"],
            trading_days=return_metrics["trading_days"],
            start_date=return_metrics["start_date"],
            end_date=return_metrics["end_date"],
            equity_curve=self.equity_curve,
            monthly_returns=self._calculate_monthly_returns()
        )
    
    def _calculate_returns(self) -> Dict:
        """Calculate return metrics."""
        initial = self.portfolio.initial_capital
        final = self.portfolio.current_equity
        
        total_return_pct = (final / initial - 1) * 100
        total_return_dollars = final - initial
        
        if self.equity_curve and len(self.equity_curve) >= 2:
            start_date = self.equity_curve[0][0]
            end_date = self.equity_curve[-1][0]
            years = max((end_date - start_date).days / 365.25, 0.01)
            cagr = ((final / initial) ** (1 / years) - 1) * 100
            trading_days = len(self.equity_curve)
        else:
            start_date = None
            end_date = None
            cagr = 0.0
            trading_days = 0
        
        return {
            "total_return_pct": total_return_pct,
            "total_return_dollars": total_return_dollars,
            "cagr": cagr,
            "start_date": start_date,
            "end_date": end_date,
            "trading_days": trading_days
        }
    
    def _calculate_risk(self) -> Dict:
        """Calculate risk metrics."""
        if len(self.equity_curve) < 2:
            return {
                "annual_volatility": 0.0,
                "max_drawdown_pct": 0.0,
                "max_drawdown_dollars": 0.0,
                "max_drawdown_duration_days": 0,
                "var_95": 0.0,
                "cvar_95": 0.0
            }
        
        equities = np.array([e[1] for e in self.equity_curve])
        returns = np.diff(equities) / equities[:-1]
        
        daily_vol = np.std(returns) if len(returns) > 1 else 0.0
        annual_volatility = daily_vol * np.sqrt(self.TRADING_DAYS_PER_YEAR) * 100
        
        peak = equities[0]
        max_dd_pct = 0.0
        max_dd_dollars = 0.0
        dd_start_idx = 0
        max_dd_duration = 0
        current_dd_start = 0
        
        for i, equity in enumerate(equities):
            if equity > peak:
                peak = equity
                if current_dd_start > 0:
                    duration = i - current_dd_start
                    max_dd_duration = max(max_dd_duration, duration)
                current_dd_start = i
            else:
                dd_pct = (peak - equity) / peak * 100
                dd_dollars = peak - equity
                if dd_pct > max_dd_pct:
                    max_dd_pct = dd_pct
                    max_dd_dollars = dd_dollars
                    dd_start_idx = current_dd_start
        
        if len(returns) > 0:
            var_95 = np.percentile(returns, 5) * 100
            tail_returns = returns[returns <= np.percentile(returns, 5)]
            cvar_95 = np.mean(tail_returns) * 100 if len(tail_returns) > 0 else var_95
        else:
            var_95 = 0.0
            cvar_95 = 0.0
        
        return {
            "annual_volatility": annual_volatility,
            "max_drawdown_pct": max_dd_pct,
            "max_drawdown_dollars": max_dd_dollars,
            "max_drawdown_duration_days": max_dd_duration,
            "var_95": var_95,
            "cvar_95": cvar_95
        }
    
    def _calculate_risk_adjusted(self, returns: Dict, risk: Dict) -> Dict:
        """Calculate risk-adjusted return metrics."""
        if len(self.equity_curve) < 2:
            return {"sharpe_ratio": None, "sortino_ratio": None, "calmar_ratio": None}
        
        equities = np.array([e[1] for e in self.equity_curve])
        daily_returns = np.diff(equities) / equities[:-1]
        
        if len(daily_returns) == 0 or np.std(daily_returns) == 0:
            return {"sharpe_ratio": None, "sortino_ratio": None, "calmar_ratio": None}
        
        excess_return = np.mean(daily_returns) * self.TRADING_DAYS_PER_YEAR - self.RISK_FREE_RATE
        sharpe = excess_return / (np.std(daily_returns) * np.sqrt(self.TRADING_DAYS_PER_YEAR))
        
        downside_returns = daily_returns[daily_returns < 0]
        if len(downside_returns) > 0 and np.std(downside_returns) > 0:
            sortino = excess_return / (np.std(downside_returns) * np.sqrt(self.TRADING_DAYS_PER_YEAR))
        else:
            sortino = None
        
        if risk["max_drawdown_pct"] > 0:
            calmar = returns["cagr"] / risk["max_drawdown_pct"]
        else:
            calmar = None
        
        return {
            "sharpe_ratio": sharpe,
            "sortino_ratio": sortino,
            "calmar_ratio": calmar
        }
    
    def _calculate_trade_statistics(self) -> Dict:
        """Calculate trade-level statistics."""
        if not self.trades:
            return {
                "total_trades": 0, "winning_trades": 0, "losing_trades": 0,
                "win_rate": 0.0, "avg_win_pct": 0.0, "avg_loss_pct": 0.0,
                "profit_factor": 0.0, "expectancy": 0.0,
                "avg_holding_days": 0.0, "max_consecutive_wins": 0,
                "max_consecutive_losses": 0, "avg_trade_return": 0.0,
                "best_trade_pct": 0.0, "worst_trade_pct": 0.0
            }
        
        returns = [t.pnl_percent for t in self.trades]
        winning = [r for r in returns if r > 0]
        losing = [r for r in returns if r <= 0]
        
        holding_days = []
        for t in self.trades:
            if t.exit_date and t.entry_date:
                holding_days.append((t.exit_date - t.entry_date).days)
        
        max_consec_wins = 0
        max_consec_losses = 0
        current_wins = 0
        current_losses = 0
        
        for r in returns:
            if r > 0:
                current_wins += 1
                current_losses = 0
                max_consec_wins = max(max_consec_wins, current_wins)
            else:
                current_losses += 1
                current_wins = 0
                max_consec_losses = max(max_consec_losses, current_losses)
        
        total_profit = sum(winning) if winning else 0
        total_loss = abs(sum(losing)) if losing else 0
        profit_factor = total_profit / total_loss if total_loss > 0 else float('inf')
        
        win_rate = len(winning) / len(returns) if returns else 0
        avg_win = np.mean(winning) if winning else 0
        avg_loss = np.mean(losing) if losing else 0
        expectancy = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        
        return {
            "total_trades": len(returns),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": win_rate,
            "avg_win_pct": avg_win,
            "avg_loss_pct": avg_loss,
            "profit_factor": profit_factor if profit_factor != float('inf') else 99.99,
            "expectancy": expectancy,
            "avg_holding_days": np.mean(holding_days) if holding_days else 0,
            "max_consecutive_wins": max_consec_wins,
            "max_consecutive_losses": max_consec_losses,
            "avg_trade_return": np.mean(returns),
            "best_trade_pct": max(returns) if returns else 0,
            "worst_trade_pct": min(returns) if returns else 0
        }
    
    def _calculate_direction_breakdown(self) -> Dict:
        """Calculate statistics by trade direction."""
        long_trades = [t for t in self.trades if t.direction.value == "long"]
        short_trades = [t for t in self.trades if t.direction.value == "short"]
        
        long_wins = sum(1 for t in long_trades if t.pnl_percent > 0)
        short_wins = sum(1 for t in short_trades if t.pnl_percent > 0)
        
        return {
            "long_trades": len(long_trades),
            "short_trades": len(short_trades),
            "long_win_rate": long_wins / len(long_trades) if long_trades else 0,
            "short_win_rate": short_wins / len(short_trades) if short_trades else 0
        }
    
    def _calculate_monthly_returns(self) -> Dict[str, float]:
        """Calculate returns by month."""
        if len(self.equity_curve) < 2:
            return {}
        
        monthly = {}
        current_month = None
        month_start_equity = None
        
        for date, equity in self.equity_curve:
            month_key = date.strftime("%Y-%m")
            
            if month_key != current_month:
                if current_month and month_start_equity:
                    monthly[current_month] = (prev_equity / month_start_equity - 1) * 100
                current_month = month_key
                month_start_equity = equity
            
            prev_equity = equity
        
        if current_month and month_start_equity:
            monthly[current_month] = (prev_equity / month_start_equity - 1) * 100
        
        return monthly
