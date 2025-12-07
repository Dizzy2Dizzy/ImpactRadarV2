"""
Backtesting Engine for Impact Radar Strategy Backtesting

Simulates trading strategies using historical event and price data.
"""

from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
import logging
import numpy as np

from releaseradar.db.models import (
    UserStrategy, 
    BacktestRun, 
    BacktestResult, 
    Event, 
    PriceHistory
)
from releaseradar.services.strategy_engine import (
    evaluate_conditions,
    calculate_position_size,
    check_exit_condition
)
from releaseradar.services.quantitative_metrics import (
    calculate_sortino_ratio,
    calculate_average_true_range,
    calculate_parkinson_volatility
)

logger = logging.getLogger(__name__)


def run_backtest(
    strategy_id: int,
    start_date: date,
    end_date: date,
    initial_capital: float,
    db: Session
) -> BacktestRun:
    """
    Run a backtest for a given strategy over a date range.
    
    Args:
        strategy_id: ID of the UserStrategy to backtest
        start_date: Start date for backtest period
        end_date: End date for backtest period
        initial_capital: Starting capital in dollars
        db: Database session
    
    Returns:
        BacktestRun: Completed backtest run with summary metrics
    
    Process:
        1. Create BacktestRun record with status="running"
        2. Query all events in date range matching strategy filters
        3. For each matching event:
           - Check if entry_conditions are met
           - Get entry price from price_history
           - Calculate position size
           - Simulate holding period and exit
           - Get exit price from price_history
           - Calculate P&L and create BacktestResult record
        4. Calculate summary metrics from all trades
        5. Update BacktestRun with status="completed" and metrics
    """
    # Get strategy
    strategy = db.query(UserStrategy).filter(UserStrategy.id == strategy_id).first()
    if not strategy:
        raise ValueError(f"Strategy {strategy_id} not found")
    
    # Create BacktestRun record
    backtest_run = BacktestRun(
        strategy_id=strategy_id,
        user_id=strategy.user_id,
        start_date=start_date,
        end_date=end_date,
        initial_capital=initial_capital,
        status="running",
        started_at=datetime.utcnow()
    )
    db.add(backtest_run)
    db.commit()
    db.refresh(backtest_run)
    
    try:
        # Query events in date range
        query = db.query(Event).filter(
            and_(
                Event.date >= start_date,
                Event.date <= end_date
            )
        )
        
        # Apply strategy filters
        if strategy.tickers:
            query = query.filter(Event.ticker.in_(strategy.tickers))
        
        if strategy.sectors:
            query = query.filter(Event.sector.in_(strategy.sectors))
        
        if strategy.min_score_threshold:
            # Use ML-adjusted score if available, otherwise use impact_score
            query = query.filter(
                or_(
                    Event.ml_adjusted_score >= strategy.min_score_threshold,
                    and_(
                        Event.ml_adjusted_score.is_(None),
                        Event.impact_score >= strategy.min_score_threshold
                    )
                )
            )
        
        # Order by date
        events = query.order_by(Event.date).all()
        
        logger.info(f"Backtesting {len(events)} events for strategy {strategy.name}")
        
        # Track active capital and positions
        current_capital = initial_capital
        trades: List[BacktestResult] = []
        skipped_trades = 0
        
        # Process each event
        for event in events:
            try:
                # Check if entry conditions are met
                if not evaluate_conditions(strategy.entry_conditions, event):
                    continue
                
                # Get entry price from price_history
                entry_price_record = db.query(PriceHistory).filter(
                    and_(
                        PriceHistory.ticker == event.ticker,
                        PriceHistory.date >= event.date.date()
                    )
                ).order_by(PriceHistory.date).first()
                
                if not entry_price_record:
                    logger.warning(f"No price data found for {event.ticker} on/after {event.date}")
                    continue
                
                entry_date = entry_price_record.date
                entry_price = entry_price_record.open  # Use open price for entry
                
                # Validate entry price
                if entry_price is None or entry_price <= 0:
                    logger.warning(f"Invalid entry price for {event.ticker} on {entry_date}: {entry_price}")
                    continue
                
                # Calculate position size
                position_size = calculate_position_size(strategy, current_capital, event)
                if position_size > current_capital:
                    position_size = current_capital  # Can't invest more than available capital
                
                if position_size <= 0:
                    continue  # Skip if no capital available
                
                shares = position_size / entry_price
                
                # Determine exit
                exit_date = None
                exit_price = None
                exit_reason = None
                
                # Get price history for holding period
                max_holding_days = 30  # Maximum holding period to check
                price_history = db.query(PriceHistory).filter(
                    and_(
                        PriceHistory.ticker == event.ticker,
                        PriceHistory.date > entry_date,
                        PriceHistory.date <= entry_date + timedelta(days=max_holding_days)
                    )
                ).order_by(PriceHistory.date).all()
                
                # Check exit conditions for each day
                for price_record in price_history:
                    if price_record.close is None:
                        continue
                    
                    should_exit, reason = check_exit_condition(
                        strategy.exit_conditions,
                        entry_date,
                        price_record.date,
                        entry_price,
                        price_record.close,
                        event
                    )
                    
                    if should_exit:
                        exit_date = price_record.date
                        exit_price = price_record.close
                        exit_reason = reason
                        break
                
                # If no exit condition met, exit at end of backtest period or max holding
                if exit_date is None or exit_price is None:
                    last_price = db.query(PriceHistory).filter(
                        and_(
                            PriceHistory.ticker == event.ticker,
                            PriceHistory.date <= end_date
                        )
                    ).order_by(PriceHistory.date.desc()).first()
                    
                    if last_price and last_price.close is not None:
                        exit_date = last_price.date
                        exit_price = last_price.close
                        exit_reason = "backtest_end"
                
                # Extended search for missing exit price
                if exit_price is None:
                    extended_price = db.query(PriceHistory).filter(
                        and_(
                            PriceHistory.ticker == event.ticker,
                            PriceHistory.date > entry_date,
                            PriceHistory.close.isnot(None)
                        )
                    ).order_by(PriceHistory.date).first()
                    
                    if extended_price and extended_price.close is not None:
                        exit_date = extended_price.date
                        exit_price = extended_price.close
                        exit_reason = "last_available_price"
                        logger.warning(
                            f"Using last available price for {event.ticker}: "
                            f"{exit_price} on {exit_date}"
                        )
                
                # Skip trade entirely if no valid exit price found
                if exit_price is None or exit_price <= 0:
                    logger.info(
                        f"Skipping trade for {event.ticker} (event {event.id}): "
                        f"no valid exit price available"
                    )
                    skipped_trades += 1
                    continue
                
                # Validate exit date
                if exit_date is None:
                    logger.info(
                        f"Skipping trade for {event.ticker} (event {event.id}): "
                        f"no valid exit date"
                    )
                    skipped_trades += 1
                    continue
                
                # Calculate P&L with null checks
                position_value = entry_price * shares
                profit_loss = (exit_price - entry_price) * shares
                return_pct = ((exit_price - entry_price) / entry_price) * 100
                holding_period_days = (exit_date - entry_date).days
                
                # Validate calculated values
                if np.isnan(return_pct) or np.isinf(return_pct):
                    logger.warning(
                        f"Invalid return_pct for {event.ticker}: {return_pct}, "
                        f"entry={entry_price}, exit={exit_price}"
                    )
                    continue
                
                # Create BacktestResult
                result = BacktestResult(
                    run_id=backtest_run.id,
                    ticker=event.ticker,
                    event_id=event.id,
                    entry_date=entry_date,
                    entry_price=entry_price,
                    exit_date=exit_date,
                    exit_price=exit_price,
                    shares=shares,
                    position_value=position_value,
                    return_pct=return_pct,
                    profit_loss=profit_loss,
                    exit_reason=exit_reason,
                    holding_period_days=holding_period_days
                )
                db.add(result)
                trades.append(result)
                
                # Update capital (simple model: full capital returned after exit)
                current_capital = current_capital - position_value + position_value + profit_loss
                
            except Exception as e:
                logger.error(
                    f"Error processing trade for {event.ticker} (event {event.id}): {str(e)}",
                    exc_info=True
                )
                # Continue processing remaining trades
                continue
        
        # Commit all trade results
        db.commit()
        
        # Calculate summary metrics
        if trades:
            total_trades = len(trades)
            winning_trades = sum(1 for t in trades if t.profit_loss > 0)
            win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0
            
            total_return = sum(t.profit_loss for t in trades)
            total_return_pct = (total_return / initial_capital) * 100 if initial_capital > 0 else 0
            
            # Calculate Sharpe ratio using actual holding periods
            try:
                returns = [t.return_pct for t in trades if t.return_pct is not None]
                holding_days = [t.holding_period_days for t in trades if t.holding_period_days is not None and t.holding_period_days > 0]
                
                # Filter out NaN and inf values
                returns = [r for r in returns if not (np.isnan(r) or np.isinf(r))]
                
                # Need at least 2 trades with valid returns for meaningful Sharpe ratio
                if len(returns) >= 2 and len(holding_days) >= 2:
                    avg_return = np.mean(returns)
                    std_return = np.std(returns)
                    avg_holding_days = np.mean(holding_days)
                    
                    # Guard against NaN results, zero/very small standard deviation, and zero holding period
                    if (not np.isnan(avg_return) and not np.isnan(std_return) and 
                        std_return > 1e-10 and avg_holding_days > 0):
                        # Annualize using actual holding periods: sharpe = mean/std * sqrt(252/avg_holding_days)
                        annualization_factor = np.sqrt(252.0 / avg_holding_days)
                        sharpe_ratio = (avg_return / std_return) * annualization_factor
                        
                        # Validate final sharpe ratio
                        if np.isnan(sharpe_ratio) or np.isinf(sharpe_ratio):
                            sharpe_ratio = 0.0
                    else:
                        sharpe_ratio = 0.0
                else:
                    sharpe_ratio = 0.0
            except Exception as e:
                logger.warning(f"Error calculating Sharpe ratio: {str(e)}")
                sharpe_ratio = 0.0
            
            # Calculate Sortino ratio using same returns array
            try:
                # Convert returns from percentages to decimals for Sortino calculation
                returns_decimal = [r / 100.0 for r in returns if not (np.isnan(r) or np.isinf(r))]
                sortino_ratio = calculate_sortino_ratio(returns_decimal, risk_free_rate=0.0)
                
                # Validate result
                if sortino_ratio is None or np.isnan(sortino_ratio) or np.isinf(sortino_ratio):
                    sortino_ratio = 0.0
            except Exception as e:
                logger.warning(f"Error calculating Sortino ratio: {str(e)}")
                sortino_ratio = 0.0
            
            # Calculate ATR and Parkinson volatility from PriceHistory data
            # Performance optimization: Query all price data in one batch instead of per-ticker
            try:
                # Gather all unique tickers from trades
                trade_tickers = list(set([t.ticker for t in trades if t.ticker]))
                
                all_high = []
                all_low = []
                all_close = []
                
                # Single optimized query for all tickers in the backtest period
                if trade_tickers:
                    price_data = db.query(PriceHistory).filter(
                        and_(
                            PriceHistory.ticker.in_(trade_tickers),
                            PriceHistory.date >= start_date,
                            PriceHistory.date <= end_date
                        )
                    ).order_by(PriceHistory.ticker, PriceHistory.date).all()
                    
                    for p in price_data:
                        if p.high is not None and p.low is not None and p.close is not None:
                            all_high.append(p.high)
                            all_low.append(p.low)
                            all_close.append(p.close)
                
                # Calculate ATR using all price data
                if len(all_high) >= 2 and len(all_low) >= 2 and len(all_close) >= 2:
                    avg_atr = calculate_average_true_range(all_high, all_low, all_close)
                    
                    # Validate result
                    if avg_atr is None or np.isnan(avg_atr) or np.isinf(avg_atr):
                        avg_atr = 0.0
                    
                    # Calculate Parkinson volatility using same high/low data
                    parkinson_volatility = calculate_parkinson_volatility(all_high, all_low, annualized=True)
                    
                    # Validate result
                    if parkinson_volatility is None or np.isnan(parkinson_volatility) or np.isinf(parkinson_volatility):
                        parkinson_volatility = 0.0
                else:
                    avg_atr = 0.0
                    parkinson_volatility = 0.0
            except Exception as e:
                logger.warning(f"Error calculating ATR/Parkinson volatility: {str(e)}")
                avg_atr = 0.0
                parkinson_volatility = 0.0
            
            # Calculate max drawdown with guards
            try:
                cumulative_returns = [initial_capital]
                for trade in trades:
                    if trade.profit_loss is not None and not np.isnan(trade.profit_loss):
                        cumulative_returns.append(cumulative_returns[-1] + trade.profit_loss)
                
                peak = cumulative_returns[0]
                max_drawdown = 0
                for value in cumulative_returns:
                    if value > peak:
                        peak = value
                    # Guard against division by zero
                    if peak > 0:
                        drawdown = ((peak - value) / peak) * 100
                        if drawdown > max_drawdown and not np.isnan(drawdown) and not np.isinf(drawdown):
                            max_drawdown = drawdown
                
                max_drawdown_pct = max_drawdown
            except Exception as e:
                logger.warning(f"Error calculating max drawdown: {str(e)}")
                max_drawdown_pct = 0.0
        else:
            total_trades = 0
            win_rate = 0.0
            total_return_pct = 0.0
            sharpe_ratio = 0.0
            sortino_ratio = 0.0
            avg_atr = 0.0
            parkinson_volatility = 0.0
            max_drawdown_pct = 0.0
        
        # Update BacktestRun with summary metrics
        backtest_run.status = "completed"
        backtest_run.completed_at = datetime.utcnow()
        backtest_run.total_trades = total_trades
        backtest_run.win_rate = win_rate
        backtest_run.total_return_pct = total_return_pct
        backtest_run.sharpe_ratio = sharpe_ratio
        backtest_run.sortino_ratio = sortino_ratio
        backtest_run.avg_atr = avg_atr
        backtest_run.parkinson_volatility = parkinson_volatility
        backtest_run.max_drawdown_pct = max_drawdown_pct
        
        db.commit()
        db.refresh(backtest_run)
        
        logger.info(
            f"Backtest completed: {total_trades} trades executed, "
            f"{skipped_trades} trades skipped (no exit price), "
            f"{win_rate:.1f}% win rate, "
            f"{total_return_pct:.2f}% total return"
        )
        
        return backtest_run
        
    except Exception as e:
        logger.error(f"Backtest failed: {str(e)}", exc_info=True)
        backtest_run.status = "failed"
        backtest_run.completed_at = datetime.utcnow()
        backtest_run.error_message = str(e)
        db.commit()
        raise
