"""Watchlist router"""
from fastapi import APIRouter, Depends, status

from api.schemas.watchlist import WatchlistAdd, WatchlistResponse
from api.dependencies import get_data_manager
from api.utils.auth import get_current_user_id
from api.utils.exceptions import ResourceNotFoundException
from data_manager import DataManager

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=list[WatchlistResponse])
async def get_watchlist(
    user_id: int = Depends(get_current_user_id),
    dm: DataManager = Depends(get_data_manager)
):
    """Get user's watchlist"""
    watchlist_items = dm.get_watchlist(user_id)
    
    if not watchlist_items:
        return []
    
    # Batch fetch all companies in one query
    tickers = [item['ticker'] for item in watchlist_items]
    from database import get_db, close_db_session, Company, Event
    from datetime import datetime, timedelta
    
    db = get_db()
    try:
        # Single query for all companies
        companies = db.query(Company).filter(Company.ticker.in_(tickers)).all()
        companies_by_ticker = {c.ticker: c for c in companies}
        
        # Single query for all upcoming events (next 7 days)
        end_date = datetime.now() + timedelta(days=7)
        events = db.query(Event).filter(
            Event.ticker.in_(tickers),
            Event.date <= end_date
        ).order_by(Event.date.asc()).all()
        
        # Group events by ticker
        events_by_ticker = {}
        for event in events:
            if event.ticker not in events_by_ticker:
                events_by_ticker[event.ticker] = []
            events_by_ticker[event.ticker].append(event)
        
        # Build enriched response
        enriched = []
        for item in watchlist_items:
            company = companies_by_ticker.get(item['ticker'])
            if company:
                ticker_events = events_by_ticker.get(item['ticker'], [])
                
                # Convert events to serializable dictionaries (limit to 3)
                upcoming_events_serialized = []
                for event in ticker_events[:3]:
                    event_dict = {
                        'id': event.id,
                        'ticker': event.ticker,
                        'company_name': event.company_name,
                        'title': event.title,
                        'event_type': event.event_type,
                        'date': event.date,
                        'impact_score': event.impact_score,
                        'direction': event.direction,
                        'confidence': float(event.confidence) if event.confidence is not None else None,
                        'source_url': event.source_url,
                    }
                    upcoming_events_serialized.append(event_dict)
                
                enriched.append(WatchlistResponse(
                    **item,
                    company_id=company.id,
                    company_name=company.name,
                    sector=company.sector,
                    upcoming_events=upcoming_events_serialized
                ))
        
        return enriched
    finally:
        close_db_session(db)


@router.post("", status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    data: WatchlistAdd,
    user_id: int = Depends(get_current_user_id),
    dm: DataManager = Depends(get_data_manager)
):
    """Add company to watchlist"""
    # Get company to verify it exists
    from database import get_db, close_db_session, Company
    db = get_db()
    try:
        company = db.query(Company).filter(Company.id == data.company_id).first()
        if not company:
            raise ResourceNotFoundException("Company", str(data.company_id))
        
        # Add to watchlist (fixed argument order: ticker first, then user_id)
        dm.add_to_watchlist(company.ticker, user_id, notes=data.notes)
        return {"message": "Company added to watchlist"}
    finally:
        close_db_session(db)


@router.delete("/{company_id}")
async def remove_from_watchlist(
    company_id: int,
    user_id: int = Depends(get_current_user_id),
    dm: DataManager = Depends(get_data_manager)
):
    """Remove company from watchlist"""
    # Get company ticker
    from database import get_db, close_db_session, Company
    db = get_db()
    try:
        company = db.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise ResourceNotFoundException("Company", str(company_id))
        
        # Fixed argument order: ticker first, then user_id
        dm.remove_from_watchlist(company.ticker, user_id)
        return {"message": "Company removed from watchlist"}
    finally:
        close_db_session(db)
