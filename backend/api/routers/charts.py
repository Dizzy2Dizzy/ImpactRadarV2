"""Charts router for price data with event annotations"""
from fastapi import APIRouter, Depends, HTTPException, Query
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel
import yfinance as yf
from sqlalchemy import and_

from api.dependencies import get_data_manager
from api.utils.auth import get_current_user_with_plan
from api.utils.paywall import require_plan
from data_manager import DataManager
from database import Event, get_db
from releaseradar.utils.datetime import convert_utc_to_est_date
from services.projection_calculator import calculate_projection_for_event

router = APIRouter(prefix="/charts", tags=["charts"])


class PriceDataPoint(BaseModel):
    """Single OHLC price data point"""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class EventMarker(BaseModel):
    """Event marker for chart annotation with ML fields for accurate projections"""
    date: str
    event_id: int
    title: str
    impact_score: int
    direction: str
    event_type: str
    confidence: Optional[float] = None
    # ML fields for accurate projected impact calculations
    ml_adjusted_score: Optional[int] = None
    ml_confidence: Optional[float] = None
    impact_p_move: Optional[float] = None  # Predicted % move magnitude
    impact_p_up: Optional[float] = None    # Probability of upward move
    impact_p_down: Optional[float] = None  # Probability of downward move
    model_source: Optional[str] = None     # 'family-specific' | 'global' | 'deterministic'


class PriceRange(BaseModel):
    """Price range for chart scaling"""
    min: float
    max: float


class ChartData(BaseModel):
    """Complete chart data response"""
    ticker: str
    data: List[PriceDataPoint]
    events: List[EventMarker]
    price_range: PriceRange


@router.get(
    "/ticker/{ticker}",
    response_model=ChartData,
    responses={
        200: {"description": "Price chart data with event markers"},
        404: {"description": "Ticker not found or no price data available"},
        422: {"description": "Invalid parameters"},
    },
    summary="Get price chart with event annotations",
    description="Fetch historical OHLC price data for a ticker with event markers for visual analysis"
)
async def get_chart_data(
    ticker: str,
    days: int = Query(default=90, ge=1, le=365, description="Number of days to look back (1-365)"),
    show_events: bool = Query(default=True, description="Include event markers on the chart"),
    dm: DataManager = Depends(get_data_manager),
    user_data: dict = Depends(get_current_user_with_plan)
) -> ChartData:
    """
    Get price chart data with event annotations for a specific ticker.
    
    - **ticker**: Stock ticker symbol (e.g., AAPL, MSFT)
    - **days**: Lookback period in days (default 90, max 365)
    - **show_events**: Whether to include event markers (default true)
    
    Returns OHLC price data and optionally event markers for visual analysis.
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Chart analytics",
        user_data.get("trial_ends_at")
    )
    
    ticker = ticker.upper()
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Fetch price data using yfinance
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(start=start_date, end=end_date)
        
        if hist.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No price data found for ticker {ticker}. Verify the ticker symbol is correct."
            )
        
        # Convert to list of PriceDataPoint
        price_data = []
        for date, row in hist.iterrows():
            price_data.append(PriceDataPoint(
                date=date.strftime('%Y-%m-%d'),
                open=round(float(row['Open']), 2),
                high=round(float(row['High']), 2),
                low=round(float(row['Low']), 2),
                close=round(float(row['Close']), 2),
                volume=int(row['Volume'])
            ))
        
        # Calculate price range
        all_highs = [p.high for p in price_data]
        all_lows = [p.low for p in price_data]
        price_range = PriceRange(
            min=round(min(all_lows) * 0.98, 2) if all_lows else 0,
            max=round(max(all_highs) * 1.02, 2) if all_highs else 0
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Failed to fetch price data for {ticker}: {str(e)}"
        )
    
    # Fetch events if requested
    events = []
    if show_events:
        try:
            # Get events for this ticker within the date range
            event_data = dm.get_events(
                ticker=ticker,
                start_date=start_date,
                end_date=end_date
            )
            
            # Convert to EventMarker format with ML fields for accurate projections
            for event in event_data:
                # Calculate authentic projection for unique, data-driven values
                projection = calculate_projection_for_event(event)
                
                # Use authentic projections instead of stored NULL values
                # Use abs() to ensure magnitude is always positive (valid probability)
                impact_p_move = abs(projection.projected_move_pct) / 100 if projection.projected_move_pct else 0
                impact_p_up = projection.probability_up
                impact_p_down = projection.probability_down
                
                events.append(EventMarker(
                    date=convert_utc_to_est_date(event['date']),
                    event_id=event['id'],
                    title=event['title'],
                    impact_score=event.get('impact_score', 50),
                    direction=event.get('direction', 'neutral'),
                    event_type=event.get('event_type', 'unknown'),
                    confidence=event.get('confidence'),
                    ml_adjusted_score=event.get('ml_adjusted_score'),
                    ml_confidence=event.get('ml_confidence'),
                    impact_p_move=impact_p_move,
                    impact_p_up=impact_p_up,
                    impact_p_down=impact_p_down,
                    model_source=projection.data_source,
                ))
                
        except Exception as e:
            # Log error but don't fail the entire request
            print(f"Warning: Failed to fetch events for {ticker}: {str(e)}")
            events = []
    
    return ChartData(
        ticker=ticker,
        data=price_data,
        events=events,
        price_range=price_range
    )
