"""
Correlation analysis router for event patterns and relationships.

Provides endpoints for:
- Ticker event timelines
- Event pattern discovery
- Related event identification
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from typing import List, Optional
from sqlalchemy.orm import Session

from correlation import get_correlation_engine, CorrelationEngine
from database import get_db
from api.schemas.events import EventDetail
from api.utils.auth import get_current_user_with_plan
from api.utils.paywall import require_plan

router = APIRouter(prefix="/correlation", tags=["correlation"])


@router.get(
    "/ticker/{ticker}",
    response_model=List[EventDetail],
    responses={
        200: {"description": "Timeline of all events for the ticker"},
        404: {"description": "Ticker not found"},
    },
    summary="Get ticker event timeline",
    description="Retrieve chronological timeline of all events for a specific ticker. Shows event patterns and relationships over time."
)
async def get_ticker_timeline(
    ticker: str,
    days: int = Query(90, description="Number of days to look back", ge=1, le=365),
    limit: int = Query(100, description="Maximum number of events", ge=1, le=500),
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get all events for a ticker in chronological order.
    
    Args:
        ticker: Stock ticker symbol (e.g., AAPL, TSLA)
        days: Number of days to look back (default: 90, max: 365)
        limit: Maximum events to return (default: 100, max: 500)
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Correlation analytics",
        user_data.get("trial_ends_at")
    )
    
    engine = get_correlation_engine(db)
    events = engine.get_ticker_timeline(ticker.upper(), days=days, limit=limit)
    
    if not events:
        raise HTTPException(
            status_code=404,
            detail=f"No events found for ticker {ticker.upper()} in the last {days} days"
        )
    
    return [EventDetail(**event) for event in events]


@router.get(
    "/patterns",
    responses={
        200: {"description": "List of common event patterns"},
    },
    summary="Find common event patterns",
    description="Discover frequent event sequences across all tickers. Helps identify patterns like 'earnings_miss → guidance_lower' to anticipate follow-on events."
)
async def get_event_patterns(
    event_type: Optional[str] = Query(None, description="Filter by specific event type"),
    days_window: int = Query(30, description="Time window for pattern detection (days)", ge=1, le=180),
    min_frequency: int = Query(3, description="Minimum pattern occurrences", ge=1, le=100),
    mode: Optional[str] = Query(None, description="Dashboard mode: watchlist or portfolio"),
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Find common event sequence patterns.
    
    Returns patterns like:
    - 'sec_8k → earnings' (frequency: 45, avg_days: 7.2)
    - 'fda_approval → product_launch' (frequency: 23, avg_days: 14.5)
    
    Args:
        event_type: Optional filter for specific event type
        days_window: Maximum days between events to consider a pattern (default: 30)
        min_frequency: Minimum times a pattern must occur (default: 3)
        mode: Optional dashboard mode to filter by watchlist or portfolio tickers
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Correlation analytics",
        user_data.get("trial_ends_at")
    )
    
    # Get active tickers if mode is specified
    active_tickers = None
    if mode and mode in ['watchlist', 'portfolio']:
        from api.dependencies import get_data_manager
        dm = get_data_manager()
        active_tickers = dm.get_user_active_tickers(user_data["user_id"], mode)
    
    # Convert empty list to None to show all results
    tickers_filter = active_tickers if active_tickers else None
    
    engine = get_correlation_engine(db)
    patterns = engine.find_event_patterns(
        event_type=event_type,
        days_window=days_window,
        min_frequency=min_frequency,
        tickers=tickers_filter  # None = all tickers, list = filtered
    )
    
    return {
        'patterns': patterns,
        'total_patterns': len(patterns),
        'filters': {
            'event_type': event_type,
            'days_window': days_window,
            'min_frequency': min_frequency,
            'mode': mode
        }
    }


@router.get(
    "/related/{event_id}",
    response_model=List[EventDetail],
    responses={
        200: {"description": "List of related events"},
        404: {"description": "Event not found"},
    },
    summary="Get related events",
    description="Find events on the same ticker within a time window of the specified event. Useful for understanding event context and sequences."
)
async def get_related_events(
    event_id: int,
    window_days: int = Query(30, description="Days before and after to search", ge=1, le=180),
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get events on the same ticker within a time window.
    
    Args:
        event_id: ID of the event to find related events for
        window_days: Number of days before and after to search (default: 30)
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Correlation analytics",
        user_data.get("trial_ends_at")
    )
    
    engine = get_correlation_engine(db)
    related_events = engine.get_related_events(event_id, window_days=window_days)
    
    if not related_events:
        # Check if the event itself exists
        from database import Event
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            raise HTTPException(
                status_code=404,
                detail=f"Event with ID {event_id} not found"
            )
        
        # Event exists but has no related events
        return []
    
    return [EventDetail(**event) for event in related_events]


@router.get(
    "/pattern-details",
    responses={
        200: {"description": "Detailed pattern statistics"},
    },
    summary="Get pattern details",
    description="Get detailed statistics and examples for a specific event pattern sequence."
)
async def get_pattern_details(
    event_type_1: str = Query(..., description="First event type in the pattern"),
    event_type_2: str = Query(..., description="Second event type in the pattern"),
    days_window: int = Query(30, description="Time window for pattern detection", ge=1, le=180),
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get detailed statistics for a specific event pattern.
    
    Args:
        event_type_1: First event type (e.g., 'earnings')
        event_type_2: Second event type (e.g., 'guidance')
        days_window: Time window for pattern detection (default: 30)
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Correlation analytics",
        user_data.get("trial_ends_at")
    )
    
    engine = get_correlation_engine(db)
    details = engine.get_pattern_details(
        event_type_1=event_type_1,
        event_type_2=event_type_2,
        days_window=days_window
    )
    
    return details
