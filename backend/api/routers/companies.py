"""Companies router"""
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from typing import Optional
import yfinance as yf
from datetime import datetime
import time
from starlette.concurrency import run_in_threadpool
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from api.schemas.companies import CompanyResponse, CompanyDetail
from api.schemas.events import EventDetail
from api.dependencies import get_data_manager, get_db
from api.utils.api_key import require_api_key
from data_manager import DataManager
from releaseradar.db.models import Company

router = APIRouter(prefix="/companies", tags=["companies"])

# Import limiter and plan_limit from ratelimit module
from api.ratelimit import limiter, plan_limit

# Cache for companies list (60 second TTL) - keyed by query params
_companies_cache: dict = {}
COMPANIES_CACHE_TTL = 60


def calculate_projected_move(impact_score: int, direction: str, confidence: float) -> dict:
    """Calculate projected percentage move from impact score, direction, and confidence.
    
    Formula: magnitude = 12% * (impact_score/100) * (0.5 + 0.5*confidence)
    
    Returns:
        dict with 'display' (formatted string), 'magnitude' (float), and 'is_uncertain' (bool)
    """
    MAX_MOVE = 12.0  # Maximum projected move percentage
    
    # Calculate magnitude
    magnitude = MAX_MOVE * (impact_score / 100.0) * (0.5 + 0.5 * confidence)
    magnitude = round(magnitude, 1)
    
    if direction == 'positive':
        return {
            'display': f'+{magnitude}%',
            'magnitude': magnitude,
            'is_uncertain': False
        }
    elif direction == 'negative':
        return {
            'display': f'-{magnitude}%',
            'magnitude': -magnitude,
            'is_uncertain': False
        }
    elif direction == 'neutral':
        return {
            'display': f'±{magnitude}%',
            'magnitude': magnitude,  # Return positive magnitude for UI range display
            'is_uncertain': False
        }
    else:  # uncertain
        return {
            'display': 'uncertain',
            'magnitude': magnitude,  # Still return magnitude for potential UI use
            'is_uncertain': True
        }


@router.get("/universe", response_model=dict)
async def get_universe(
    request: Request,
    count_only: bool = False,
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get tracked company universe directly from database (S&P 500)."""
    # Count total tracked companies
    count_stmt = select(func.count()).select_from(Company).where(Company.tracked == True)
    total_count = db.execute(count_stmt).scalar()
    
    if count_only:
        return {"count": total_count}
    
    # Query companies with pagination
    stmt = select(Company).where(Company.tracked == True).offset(offset).limit(limit)
    companies = db.execute(stmt).scalars().all()
    
    # Convert to response format with all required fields
    company_list = [
        {
            "id": c.id,
            "ticker": c.ticker,
            "name": c.name,
            "sector": c.sector or "Unknown",
            "industry": c.industry or "",
            "tracked": c.tracked,
            "created_at": c.created_at.isoformat(),
            "event_count": 0  # Would need join with events table for accurate count
        }
        for c in companies
    ]
    
    return {
        "count": total_count,
        "offset": offset,
        "limit": limit,
        "companies": [CompanyResponse(**c) for c in company_list]
    }


@router.get(
    "",
    response_model=list[CompanyResponse],
    responses={
        200: {"description": "List of companies with event counts"},
    },
    summary="Get list of companies",
    description="Retrieve list of tracked companies with event counts. Optional filters by sector or search query. Public endpoint, no authentication required."
)
async def get_companies(
    request: Request,
    query: Optional[str] = None,
    sector: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
    dm: DataManager = Depends(get_data_manager)
):
    """Get list of companies with optional filters (public access for basic metadata)"""
    current_time = time.time()
    
    # Create cache key based on parameters (excluding query for text search)
    cache_key = f"sector:{sector or 'all'}"
    
    # Check cache
    cached = _companies_cache.get(cache_key)
    if cached and (current_time - cached["timestamp"]) < COMPANIES_CACHE_TTL:
        companies = cached["data"]
    else:
        # Fetch from database
        companies = dm.get_companies(sector=sector, with_event_counts=True)
        # Store in cache
        _companies_cache[cache_key] = {
            "data": companies,
            "timestamp": current_time
        }
        # Limit cache size to prevent memory bloat
        if len(_companies_cache) > 10:
            oldest_key = min(_companies_cache.keys(), key=lambda k: _companies_cache[k]["timestamp"])
            del _companies_cache[oldest_key]
    
    # Apply query filter if provided (not cached since text search varies)
    if query:
        query_lower = query.lower()
        companies = [
            c for c in companies 
            if query_lower in c['name'].lower() or query_lower in c['ticker'].lower()
        ]
    
    # Apply pagination
    companies = companies[offset:offset + limit]
    
    return [CompanyResponse(**c) for c in companies]


@router.get("/{ticker}/events/public")
async def get_company_events_public(
    request: Request,
    ticker: str,
    limit: int = 10,
    dm: DataManager = Depends(get_data_manager)
):
    """Get recent events for a company (public access, limited to 10 events)
    
    Returns events with projected percentage moves calculated from impact_score, direction, and confidence.
    Shows all events (past and upcoming) sorted by date descending (most recent first).
    """
    from datetime import datetime
    
    # Get all events for this ticker
    events = dm.get_events(ticker=ticker.upper())
    
    if not events:
        return []
    
    # Sort by date descending (most recent first) and limit to 10
    events = sorted(events, key=lambda e: e.get('date', datetime.min), reverse=True)[:min(limit, 10)]
    
    # Enrich each event with projected move
    enriched_events = []
    for event in events:
        projection = calculate_projected_move(
            event.get('impact_score', 50),
            event.get('direction', 'uncertain'),
            event.get('confidence', 0.5)
        )
        
        enriched_events.append({
            **event,
            'projected_move': projection['display'],
            'projected_magnitude': projection['magnitude'],
            'is_uncertain': projection['is_uncertain']
        })
    
    return enriched_events


@router.get("/{ticker}", response_model=CompanyDetail)
@limiter.limit(plan_limit)
async def get_company(
    request: Request,
    ticker: str,
    dm: DataManager = Depends(get_data_manager),
    x_api_key: Optional[str] = Header(None),
    _key = Depends(require_api_key)
):
    """Get detailed company information (requires Pro or Team plan)"""
    company = dm.get_company(ticker)
    
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    # Get upcoming events for this company
    from datetime import datetime, timedelta
    end_date = datetime.now() + timedelta(days=30)
    events = dm.get_events(ticker=ticker, end_date=end_date)
    
    return CompanyDetail(
        **company,
        upcoming_events=events[:5]  # Limit to 5 upcoming events
    )


def _fetch_stock_price(ticker: str):
    """Synchronous helper to fetch stock price"""
    ticker_data = yf.Ticker(ticker.upper())
    
    # Try to get real-time price from fast_info first
    try:
        price = ticker_data.fast_info.get('last_price')
        if price and price > 0:
            return float(price)
    except:
        pass
    
    # Fallback to latest 1-minute interval price
    try:
        hist = ticker_data.history(period="1d", interval="1m")
        if not hist.empty:
            return float(hist['Close'].iloc[-1])
    except:
        pass
    
    # Final fallback to daily close
    hist = ticker_data.history(period="1d")
    if hist.empty:
        raise ValueError("No price data available")
    
    return float(hist['Close'].iloc[-1])


@router.get("/{ticker}/price")
@limiter.limit(plan_limit)
async def get_stock_price(
    request: Request,
    ticker: str,
    x_api_key: Optional[str] = Header(None),
    _key = Depends(require_api_key)
):
    """Get current stock price for a ticker (requires Pro or Team plan)"""
    try:
        # Run in threadpool to avoid blocking async event loop
        current_price = await run_in_threadpool(_fetch_stock_price, ticker.upper())
        
        return {
            "ticker": ticker.upper(),
            "price": round(current_price, 2),
            "currency": "USD",
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch price: {str(e)}")
