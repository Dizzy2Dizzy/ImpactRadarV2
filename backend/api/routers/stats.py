"""
Stats API router for historical event statistics.

Provides backtesting data showing historical win rates and average moves
for ticker/event_type combinations. Requires Pro plan or higher.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from api.utils.auth import get_current_user_with_plan
from api.utils.paywall import require_plan
from api.schemas.stats import HistoricalStatsResponse
from data_manager import DataManager

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get(
    "/{ticker}/{event_type}",
    response_model=HistoricalStatsResponse,
    summary="Get historical event statistics",
    description="Returns historical win rate, average moves, and sample size for a ticker/event_type combination. Requires Pro plan or higher."
)
async def get_event_stats(
    ticker: str,
    event_type: str,
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get historical statistics for events of this type for this ticker.
    
    Shows win rate, average moves, and sample size based on backtesting data.
    Helps users understand typical price impact magnitude for similar events.
    
    **Plan Requirement:** Pro or higher
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Historical event statistics",
        user_data.get("trial_ends_at")
    )
    
    dm = DataManager()
    
    # Query EventStats table
    stats = dm.get_event_stats(ticker=ticker.upper(), event_type=event_type)
    
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No historical data found for {ticker.upper()} {event_type}"
        )
    
    return HistoricalStatsResponse(
        ticker=stats.ticker,
        event_type=stats.event_type,
        sample_size=stats.sample_size,
        win_rate=stats.win_rate,
        avg_abs_move_1d=stats.avg_abs_move_1d,
        avg_abs_move_5d=stats.avg_abs_move_5d,
        avg_abs_move_20d=stats.avg_abs_move_20d,
        mean_move_1d=stats.mean_move_1d,
        mean_move_5d=stats.mean_move_5d,
        mean_move_20d=stats.mean_move_20d
    )


@router.get(
    "/{ticker}",
    response_model=List[HistoricalStatsResponse],
    summary="Get all event type stats for a ticker",
    description="Returns stats for all event types available for this ticker. Requires Pro plan or higher."
)
async def get_ticker_stats(
    ticker: str,
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get stats for all event types for this ticker.
    
    Returns a list of historical statistics for every event type
    that has backtesting data for this ticker.
    
    **Plan Requirement:** Pro or higher
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Historical event statistics",
        user_data.get("trial_ends_at")
    )
    
    dm = DataManager()
    all_stats = dm.get_ticker_all_event_stats(ticker=ticker.upper())
    
    if not all_stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No historical data found for {ticker.upper()}"
        )
    
    return [
        HistoricalStatsResponse(
            ticker=stats.ticker,
            event_type=stats.event_type,
            sample_size=stats.sample_size,
            win_rate=stats.win_rate,
            avg_abs_move_1d=stats.avg_abs_move_1d,
            avg_abs_move_5d=stats.avg_abs_move_5d,
            avg_abs_move_20d=stats.avg_abs_move_20d,
            mean_move_1d=stats.mean_move_1d,
            mean_move_5d=stats.mean_move_5d,
            mean_move_20d=stats.mean_move_20d
        )
        for stats in all_stats
    ]
