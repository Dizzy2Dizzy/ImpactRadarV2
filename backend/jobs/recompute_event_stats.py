"""
Recompute event statistics job.

Calculates historical impact statistics for each (ticker, event_type) pair by analyzing
price movements after event dates. Computes win_rate, average moves, and mean moves for
1-day, 5-day, and 20-day windows.
"""

import os
import sys
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

import pandas as pd
from sqlalchemy import select, and_, delete
from sqlalchemy.dialects.postgresql import insert

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from releaseradar.db.models import Event, PriceHistory, EventStats
from releaseradar.db.session import SessionLocal
from database import close_db_session
from releaseradar.log_config import logger


def calculate_returns(
    ticker: str,
    event_date: datetime,
    price_data: pd.DataFrame,
    windows: List[int] = [1, 5, 20]
) -> Dict[str, float]:
    """
    Calculate returns for specified windows after an event.
    
    Args:
        ticker: Stock ticker
        event_date: Date of the event
        price_data: DataFrame with columns [date, close]
        windows: List of window sizes in trading days
        
    Returns:
        Dictionary with keys like 'return_1d', 'return_5d', 'return_20d'
    """
    returns = {}
    
    # Get price before event (t-1)
    event_date_obj = event_date.date() if isinstance(event_date, datetime) else event_date
    pre_event = price_data[price_data['date'] < event_date_obj]
    
    if pre_event.empty:
        return returns
    
    base_price = pre_event.iloc[-1]['close']
    
    # Calculate returns for each window
    for window in windows:
        try:
            # Get prices after event (strictly after, not including event date)
            post_event = price_data[price_data['date'] > event_date_obj]
            
            # Need at least 'window' trading days of data
            if len(post_event) < window:
                continue
            
            # Price at t+N trading days (iloc[window-1] because 0-indexed)
            # For window=1, iloc[0] is the first trading day AFTER the event
            future_price = post_event.iloc[window - 1]['close']
            
            # Calculate return
            pct_return = (future_price / base_price) - 1
            returns[f'return_{window}d'] = pct_return
            
        except Exception as e:
            logger.debug(f"Could not calculate {window}d return for {ticker}: {e}")
            continue
    
    return returns


def compute_stats_for_ticker_event_type(
    db,
    ticker: str,
    event_type: str
) -> Dict:
    """
    Compute statistics for a specific ticker and event type combination.
    
    Returns a structured action contract specifying whether to update or delete
    the EventStats row for this ticker/event_type pair.
    
    Invariants (see INVARIANTS.md Wave A):
        1. Complete Price Coverage: EventStats exists iff at least one event has complete 1d/5d/20d coverage
        2. Sample Size Accuracy: sample_size reflects ONLY events with complete coverage
        3. Deletion Behavior: DELETE action if no events have complete coverage
        4. Idempotence: Calling twice produces identical results
        5. Action Contract: Always returns {"action": "update"|"delete", ...}
    
    Args:
        db: Database session
        ticker: Stock ticker
        event_type: Type of event (e.g., 'earnings', 'fda_approval')
        
    Returns:
        {
            "action": "update" | "delete",
            "payload": {
                "ticker": str,
                "event_type": str,
                "sample_size": int,
                "win_rate": float | None,
                ...
            }  # Only present if action == "update"
        }
    """
    # Fetch all events of this type for this ticker
    result = db.execute(
        select(Event.id, Event.date)
        .where(and_(Event.ticker == ticker, Event.event_type == event_type))
        .order_by(Event.date)
    )
    events = list(result)
    
    if not events:
        return {"action": "delete"}
    
    # Fetch price history for this ticker
    price_result = db.execute(
        select(PriceHistory.date, PriceHistory.close)
        .where(PriceHistory.ticker == ticker)
        .order_by(PriceHistory.date)
    )
    price_data = pd.DataFrame(price_result, columns=['date', 'close'])
    
    if price_data.empty:
        logger.warning(f"No price data for {ticker}, will delete EventStats row")
        return {"action": "delete"}
    
    # Calculate returns for each event
    # Pipeline Invariant (Dataset-Level): Compute stats using events with complete coverage
    # Only return action="delete" if NO events have all three windows (1d, 5d, 20d)
    all_returns_1d = []
    all_returns_5d = []
    all_returns_20d = []
    events_with_complete_coverage = 0
    
    for event_id, event_date in events:
        returns = calculate_returns(ticker, event_date, price_data)
        
        # Check if this event has all required windows
        has_all_windows = (
            'return_1d' in returns and 
            'return_5d' in returns and 
            'return_20d' in returns
        )
        
        if has_all_windows:
            # Event has complete data across all windows - include it
            events_with_complete_coverage += 1
            all_returns_1d.append(returns['return_1d'])
            all_returns_5d.append(returns['return_5d'])
            all_returns_20d.append(returns['return_20d'])
        else:
            # Event missing some windows (likely recent) - skip it
            logger.debug(
                f"Event {event_id} for {ticker}/{event_type} missing windows: "
                f"1d={'return_1d' in returns}, 5d={'return_5d' in returns}, "
                f"20d={'return_20d' in returns} - excluding from stats"
            )
    
    # Enforce invariant: must have at least one event with complete window coverage
    if events_with_complete_coverage == 0:
        logger.info(
            f"No events with complete window coverage for {ticker}/{event_type} "
            f"({len(events)} total events), will delete EventStats row"
        )
        return {"action": "delete"}
    
    # Use events with complete coverage as sample size
    sample_size = events_with_complete_coverage
    
    # Build payload with all statistics
    payload = {
        "ticker": ticker,
        "event_type": event_type,
        "sample_size": sample_size,
        "win_rate": None,
        "avg_abs_move_1d": None,
        "avg_abs_move_5d": None,
        "avg_abs_move_20d": None,
        "mean_move_1d": None,
        "mean_move_5d": None,
        "mean_move_20d": None,
        "updated_at": datetime.now(),
    }
    
    # 1-day stats (only set if we have data)
    if all_returns_1d:
        payload["mean_move_1d"] = float(pd.Series(all_returns_1d).mean())
        payload["avg_abs_move_1d"] = float(pd.Series(all_returns_1d).abs().mean())
        payload["win_rate"] = float((pd.Series(all_returns_1d) > 0).sum() / len(all_returns_1d))
    
    # 5-day stats (only set if we have data)
    if all_returns_5d:
        payload["mean_move_5d"] = float(pd.Series(all_returns_5d).mean())
        payload["avg_abs_move_5d"] = float(pd.Series(all_returns_5d).abs().mean())
    
    # 20-day stats (only set if we have data)
    if all_returns_20d:
        payload["mean_move_20d"] = float(pd.Series(all_returns_20d).mean())
        payload["avg_abs_move_20d"] = float(pd.Series(all_returns_20d).abs().mean())
    
    return {"action": "update", "payload": payload}


def recompute_all_stats(tickers: List[str] = None, event_types: List[str] = None) -> Dict:
    """
    Recompute statistics for all ticker/event_type combinations.
    
    Args:
        tickers: Optional list of tickers to process (None = all)
        event_types: Optional list of event types to process (None = all)
        
    Returns:
        Statistics about the recomputation
    """
    db = SessionLocal()
    stats = {
        "combinations_processed": 0,
        "combinations_updated": 0,
        "errors": 0,
    }
    
    try:
        # Get all unique ticker/event_type combinations
        query = select(Event.ticker, Event.event_type).distinct()
        
        if tickers:
            query = query.where(Event.ticker.in_(tickers))
        if event_types:
            query = query.where(Event.event_type.in_(event_types))
        
        result = db.execute(query)
        combinations = list(result)
        
        logger.info(f"Recomputing stats for {len(combinations)} combinations")
        
        for ticker, event_type in combinations:
            try:
                result = compute_stats_for_ticker_event_type(db, ticker, event_type)
                action = result["action"]
                
                if action == "delete":
                    # Remove EventStats row to prevent stale data
                    db.execute(
                        delete(EventStats).where(
                            EventStats.ticker == ticker,
                            EventStats.event_type == event_type
                        )
                    )
                    db.commit()
                    logger.info(f"✗ {ticker}/{event_type}: deleted (insufficient data)")
                    stats["combinations_updated"] += 1
                    
                elif action == "update":
                    # Upsert stats
                    payload = result["payload"]
                    stmt = insert(EventStats).values(payload)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["ticker", "event_type"],
                        set_={
                            "sample_size": stmt.excluded.sample_size,
                            "win_rate": stmt.excluded.win_rate,
                            "avg_abs_move_1d": stmt.excluded.avg_abs_move_1d,
                            "avg_abs_move_5d": stmt.excluded.avg_abs_move_5d,
                            "avg_abs_move_20d": stmt.excluded.avg_abs_move_20d,
                            "mean_move_1d": stmt.excluded.mean_move_1d,
                            "mean_move_5d": stmt.excluded.mean_move_5d,
                            "mean_move_20d": stmt.excluded.mean_move_20d,
                            "updated_at": stmt.excluded.updated_at,
                        }
                    )
                    db.execute(stmt)
                    db.commit()
                    
                    stats["combinations_updated"] += 1
                    logger.info(
                        f"✓ {ticker}/{event_type}: "
                        f"samples={payload['sample_size']}, "
                        f"win_rate={payload.get('win_rate', 0):.2%}"
                    )
                
            except Exception as e:
                logger.error(f"Error computing stats for {ticker}/{event_type}: {e}")
                db.rollback()
                stats["errors"] += 1
                continue
            
            stats["combinations_processed"] += 1
        
        logger.info(f"Recomputation complete: {stats}")
        return stats
        
    finally:
        close_db_session(db)


def main():
    """Entry point for scheduled job."""
    logger.info("Starting event statistics recomputation job")
    
    stats = recompute_all_stats()
    
    if stats["errors"] > 0:
        logger.warning(f"Completed with {stats['errors']} errors")
        sys.exit(1)
    else:
        logger.info("Event statistics recomputation completed successfully")
        sys.exit(0)


if __name__ == "__main__":
    main()
