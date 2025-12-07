"""Events router"""
from fastapi import APIRouter, Depends, Request, Header, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List, Any, Union
from datetime import datetime, timedelta, timezone
import csv
import io
import json
import time
from sqlalchemy import and_, or_, func

from api.schemas.events import EventResponse, EventDetail
from api.dependencies import get_data_manager
from api.utils.api_key import require_api_key
from api.utils.auth import get_current_user_optional
from api.utils.exceptions import ResourceNotFoundException, InvalidInputException
from data_manager import DataManager
from database import Event, WatchlistItem, get_db, close_db_session
from releaseradar.utils.datetime import convert_utc_to_est_date
from services.projection_calculator import calculate_projection_for_event

router = APIRouter(prefix="/events", tags=["events"])

# Import limiter and plan_limit from ratelimit module
from api.ratelimit import limiter, plan_limit

# Simple in-memory cache for featured events (TTL: 5 minutes)
_featured_events_cache = {"data": None, "timestamp": 0}
FEATURED_CACHE_TTL = 300  # 5 minutes in seconds


@router.get(
    "/public",
    response_model=list[EventDetail],
    responses={
        200: {"description": "List of public events with optional filters"},
        422: {"description": "Validation error - Invalid query parameters"},
    },
    summary="Get public events",
    description="Retrieve public event feed with optional filters. No authentication required. Returns events from the last 30 days. Use mode parameter to filter by watchlist or portfolio when authenticated."
)
async def get_public_events(
    ticker: Optional[str] = None,
    sector: Optional[str] = None,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    min_impact: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    info_tier: Optional[str] = "both",
    mode: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    dm: DataManager = Depends(get_data_manager),
    user_id: Optional[int] = Depends(get_current_user_optional)
):
    """Get public event feed with optional filters (for dashboard and public access)"""
    # Parse dates if provided (handle ISO format with 'Z' suffix)
    start_date = None
    end_date = None
    
    try:
        if from_date:
            # Replace 'Z' with '+00:00' for ISO 8601 compatibility
            from_date_normalized = from_date.replace('Z', '+00:00')
            start_date = datetime.fromisoformat(from_date_normalized)
        if to_date:
            to_date_normalized = to_date.replace('Z', '+00:00')
            end_date = datetime.fromisoformat(to_date_normalized)
    except ValueError as e:
        raise InvalidInputException(f"Invalid date format: {str(e)}")
    
    # Filter by active tickers if mode is specified and user is authenticated
    active_tickers = None
    use_empty_means_all = False
    if mode and user_id and mode in ['watchlist', 'portfolio']:
        active_tickers = dm.get_user_active_tickers(user_id, mode)
        use_empty_means_all = True  # For user mode, empty watchlist/portfolio should show all events
    
    # Determine ticker parameter for query
    # If mode is specified and we have active tickers, use them; otherwise use the ticker param
    ticker_filter = active_tickers if active_tickers is not None else ticker
    
    # Get events with filters using single query (no N+1 problem)
    events = dm.get_events(
        ticker=ticker_filter,
        start_date=start_date,
        end_date=end_date,
        event_type=category,
        min_impact=min_impact,
        direction=direction,
        sector=sector,
        info_tier=info_tier,
        empty_means_all=use_empty_means_all
    )
    
    # Apply pagination
    events = events[offset:offset + limit]
    
    # Return events (already enriched by DataManager)
    return [EventDetail(**event) for event in events]


@router.get(
    "/search",
    response_model=list[EventDetail],
    responses={
        200: {"description": "List of events matching search criteria"},
        401: {"description": "Unauthorized - Invalid or missing API key"},
        402: {"description": "Payment Required - API quota exceeded"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Search events with filters",
    description="Search and filter events by ticker, sector, category, date range, and score. Requires Pro or Team plan API key."
)
@limiter.limit(plan_limit)
async def search_events(
    request: Request,
    ticker: Optional[str] = None,
    sector: Optional[str] = None,
    category: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    min_impact: Optional[int] = None,
    direction: Optional[str] = None,
    info_tier: Optional[str] = "both",
    limit: int = 100,
    offset: int = 0,
    dm: DataManager = Depends(get_data_manager),
    x_api_key: Optional[str] = Header(None),
    _key = Depends(require_api_key)
):
    """Search events with filters (requires Pro or Team plan)"""
    # Parse dates if provided
    start_date = datetime.fromisoformat(from_date) if from_date else None
    end_date = datetime.fromisoformat(to_date) if to_date else None
    
    # Get events with filters
    events = dm.get_events(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        event_type=category,
        min_impact=min_impact,
        direction=direction,
        sector=sector,
        info_tier=info_tier
    )
    
    # Apply pagination
    events = events[offset:offset + limit]
    
    # Return events (already enriched by DataManager)
    return [EventDetail(**event) for event in events]


@router.get(
    "/calendar",
    responses={
        200: {"description": "Calendar view of events grouped by date"},
        422: {"description": "Validation error - Invalid query parameters"},
    },
    summary="Get events in calendar format",
    description="Retrieve events for a specific month grouped by date. Supports watchlist filtering for authenticated users."
)
async def get_events_calendar(
    year: Optional[int] = None,
    month: Optional[int] = None,
    watchlist_only: Union[bool, str] = False,
    user_data: Optional[dict] = Depends(get_current_user_optional),
    dm: DataManager = Depends(get_data_manager)
):
    """
    Get events grouped by date for calendar display.
    
    Supports optional authentication for personalized watchlist filtering.
    
    Args:
        year: Year for calendar (default: current year)
        month: Month for calendar (default: current month)
        watchlist_only: Only show events for watchlist tickers (requires auth)
        user_data: Optional authenticated user data (injected by dependency)
    
    Returns:
        Calendar data with events grouped by date and summary statistics
    
    Example:
        /events/calendar?year=2025&month=11&watchlist_only=true
    """
    from collections import defaultdict
    import calendar as cal
    
    # Normalize watchlist_only to boolean
    if isinstance(watchlist_only, str):
        watchlist_only = watchlist_only.lower() in ('true', '1', 'yes')
    
    # Default to current year/month if not provided
    now = datetime.now(timezone.utc)
    year = year or now.year
    month = month or now.month
    
    # Validate month
    if month < 1 or month > 12:
        raise InvalidInputException(f"Invalid month: {month}. Must be between 1 and 12.")
    
    # Get first and last day of the month
    _, last_day = cal.monthrange(year, month)
    start_date = datetime(year, month, 1, 0, 0, 0)
    end_date = datetime(year, month, last_day, 23, 59, 59)
    
    # Get watchlist tickers if filtering and user is authenticated
    watchlist_tickers = []
    if watchlist_only:
        if not user_data:
            raise HTTPException(
                status_code=401,
                detail="Authentication required for watchlist filtering"
            )
        
        user_id = user_data["user_id"]
        db = get_db()
        try:
            watchlist_items = db.query(WatchlistItem).filter(
                WatchlistItem.user_id == user_id
            ).all()
            watchlist_tickers = [item.ticker for item in watchlist_items]
        finally:
            close_db_session(db)
        
        # If watchlist is empty, return empty calendar
        if not watchlist_tickers:
            return {
                "year": year,
                "month": month,
                "events_by_date": {},
                "summary": {
                    "total_events": 0,
                    "high_impact_days": []
                }
            }
    
    # Optimize: Query database directly with only needed fields
    db = get_db()
    try:
        # Build optimized query - only select fields needed for calendar display
        query = db.query(
            Event.id,
            Event.ticker,
            Event.company_name,
            Event.event_type,
            Event.title,
            Event.description,
            Event.date,
            Event.source,
            Event.source_url,
            Event.impact_score,
            Event.direction,
            Event.confidence,
            Event.rationale,
            Event.sector,
            Event.info_tier,
            Event.info_subtype,
            Event.impact_p_move,
            Event.impact_p_up,
            Event.impact_p_down
        ).filter(
            Event.date >= start_date,
            Event.date <= end_date
        )
        
        # Add watchlist filter if needed
        if watchlist_only and watchlist_tickers:
            query = query.filter(Event.ticker.in_(watchlist_tickers))
        
        # Execute query - database handles filtering
        event_rows = query.all()
        
        # Group events by date
        events_by_date = defaultdict(list)
        high_impact_threshold = 75
        day_impact_totals = defaultdict(int)
        
        for row in event_rows:
            # Extract date key in EST timezone
            date_key = convert_utc_to_est_date(row.date)
            
            # Convert row to dict with EST date conversion
            event_dict = {
                'id': row.id,
                'ticker': row.ticker,
                'company_name': row.company_name,
                'event_type': row.event_type,
                'title': row.title,
                'description': row.description,
                'date': convert_utc_to_est_date(row.date),
                'source': row.source,
                'source_url': row.source_url,
                'impact_score': row.impact_score,
                'direction': row.direction,
                'confidence': row.confidence,
                'rationale': row.rationale,
                'sector': row.sector,
                'info_tier': row.info_tier,
                'info_subtype': row.info_subtype,
                'impact_p_move': row.impact_p_move,
                'impact_p_up': row.impact_p_up,
                'impact_p_down': row.impact_p_down
            }
            
            # Add to date bucket
            events_by_date[date_key].append(event_dict)
            day_impact_totals[date_key] += row.impact_score
    finally:
        close_db_session(db)
    
    # Sort events within each date by impact score (descending)
    for date_key in events_by_date:
        events_by_date[date_key].sort(
            key=lambda e: e.get('impact_score', 0),
            reverse=True
        )
    
    # Identify high impact days (days with any event >= 75 impact or total impact >= 150)
    high_impact_days = []
    for date_key, day_events in events_by_date.items():
        max_impact = max((e.get('impact_score', 0) for e in day_events), default=0)
        total_impact = day_impact_totals[date_key]
        
        if max_impact >= high_impact_threshold or total_impact >= 150:
            high_impact_days.append(date_key)
    
    # Sort high impact days chronologically
    high_impact_days.sort()
    
    return {
        "year": year,
        "month": month,
        "events_by_date": dict(events_by_date),
        "summary": {
            "total_events": len(event_rows),
            "high_impact_days": high_impact_days
        }
    }


@router.get(
    "/featured",
    response_model=list[EventDetail],
    responses={
        200: {"description": "5 curated high-impact events showcasing diverse event types"},
        422: {"description": "Validation error"},
    },
    summary="Get featured events for landing page",
    description="Returns 5 curated high-impact events of diverse types (2 FDA approvals, SEC filing, M&A, earnings) for the landing page. No authentication required. Results are cached for 5 minutes for optimal performance."
)
async def get_featured_events(
    dm: DataManager = Depends(get_data_manager)
):
    """
    Get 5 featured events with diverse types and high impact scores from the last 90 days.
    
    This endpoint is optimized for the landing page and returns a diverse mix of event types
    including 2 FDA approvals, SEC filings, M&A, and earnings to showcase the platform's
    comprehensive coverage. Results are cached for 5 minutes to reduce database load.
    
    Returns:
        List of 5 EventDetail objects ordered by impact_score DESC
    """
    global _featured_events_cache
    
    # Check cache validity (5 minute TTL)
    current_time = time.time()
    if _featured_events_cache["data"] and (current_time - _featured_events_cache["timestamp"]) < FEATURED_CACHE_TTL:
        return _featured_events_cache["data"]
    
    # Cache miss or expired - fetch fresh data
    db = get_db()
    try:
        # Calculate 90 days ago
        ninety_days_ago = datetime.now(timezone.utc) - timedelta(days=90)
        
        # Get diverse events by fetching high-impact events per type
        # 1 & 2. FDA approvals (get top 2 for biotech showcase)
        fda_events = db.query(Event).filter(
            Event.event_type == 'fda_approval',
            Event.direction != 'neutral',
            Event.date >= ninety_days_ago,
            Event.source_url.isnot(None)
        ).order_by(Event.impact_score.desc()).limit(2).all()
        
        # 3. SEC 8-K filing
        sec_8k = db.query(Event).filter(
            Event.event_type == 'sec_8k',
            Event.direction != 'neutral',
            Event.date >= ninety_days_ago,
            Event.source_url.isnot(None)
        ).order_by(Event.impact_score.desc()).first()
        
        # 4. M&A or other high-impact event
        ma = db.query(Event).filter(
            Event.event_type == 'ma',
            Event.direction != 'neutral',
            Event.date >= ninety_days_ago,
            Event.source_url.isnot(None)
        ).order_by(Event.impact_score.desc()).first()
        
        # 6. Earnings report
        earnings = db.query(Event).filter(
            Event.event_type == 'earnings',
            Event.direction != 'neutral',
            Event.date >= ninety_days_ago,
            Event.source_url.isnot(None)
        ).order_by(Event.impact_score.desc()).first()
        
        # Compile events list ensuring we have 5 diverse events
        events = []
        for fda in fda_events:
            events.append(fda)
        if sec_8k: events.append(sec_8k)
        if ma: events.append(ma)
        if earnings: events.append(earnings)
        
        # Convert to EventDetail format with EST date conversion
        result = []
        for event in events:
            result.append(EventDetail(
                id=event.id,
                ticker=event.ticker,
                company_name=event.company_name,
                event_type=event.event_type,
                title=event.title,
                description=event.description,
                date=convert_utc_to_est_date(event.date),
                source=event.source,
                source_url=event.source_url,
                impact_score=event.impact_score,
                direction=event.direction,
                confidence=event.confidence,
                rationale=event.rationale,
                sector=event.sector,
                subsidiary_name=event.subsidiary_name,
                created_at=convert_utc_to_est_date(event.created_at),
                updated_at=convert_utc_to_est_date(event.updated_at),
                info_tier=event.info_tier,
                info_subtype=event.info_subtype,
                impact_p_move=event.impact_p_move,
                impact_p_up=event.impact_p_up,
                impact_p_down=event.impact_p_down,
                impact_score_version=event.impact_score_version,
                ml_adjusted_score=event.ml_adjusted_score,
                model_source=event.model_source,
                ml_model_version=event.ml_model_version,
                ml_confidence=event.ml_confidence,
                delta_applied=event.delta_applied
            ))
        
        # Update cache
        _featured_events_cache["data"] = result
        _featured_events_cache["timestamp"] = current_time
        
        return result
        
    finally:
        close_db_session(db)


@router.get(
    "/export",
    responses={
        200: {"description": "CSV file download", "content": {"text/csv": {}}},
        422: {"description": "Validation error - Invalid query parameters"},
    },
    summary="Export events to CSV",
    description="Export events to CSV file with optional filters. Same query parameters as /events/public. Returns CSV with all event details for external analysis."
)
async def export_events_csv(
    ticker: Optional[str] = None,
    sector: Optional[str] = None,
    category: Optional[str] = None,
    direction: Optional[str] = None,
    min_impact: Optional[int] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    info_tier: Optional[str] = "both",
    limit: int = 1000,
    dm: DataManager = Depends(get_data_manager)
):
    """Export events to CSV with optional filters (for dashboard users)"""
    # Parse dates if provided (handle ISO format with 'Z' suffix)
    start_date = None
    end_date = None
    
    try:
        if from_date:
            from_date_normalized = from_date.replace('Z', '+00:00')
            start_date = datetime.fromisoformat(from_date_normalized)
        if to_date:
            to_date_normalized = to_date.replace('Z', '+00:00')
            end_date = datetime.fromisoformat(to_date_normalized)
    except ValueError as e:
        raise InvalidInputException(f"Invalid date format: {str(e)}")
    
    # Get events with filters
    events = dm.get_events(
        ticker=ticker,
        start_date=start_date,
        end_date=end_date,
        event_type=category,
        min_impact=min_impact,
        direction=direction,
        sector=sector,
        info_tier=info_tier
    )
    
    # Apply limit
    events = events[:limit]
    
    # Create CSV in memory
    output = io.StringIO()
    csv_writer = csv.writer(output)
    
    # Write header with all requested columns
    csv_writer.writerow([
        'id',
        'ticker',
        'company_name',
        'event_type',
        'title',
        'description',
        'date',
        'source',
        'source_url',
        'impact_score',
        'direction',
        'confidence',
        'rationale',
        'impact_p_move',
        'impact_p_up',
        'impact_p_down',
        'sector',
        'info_tier',
        'info_subtype'
    ])
    
    # Write data rows
    for event in events:
        csv_writer.writerow([
            event.get('id', ''),
            event.get('ticker', ''),
            event.get('company_name', ''),
            event.get('event_type', ''),
            event.get('title', ''),
            event.get('description', ''),
            event.get('date', ''),
            event.get('source', ''),
            event.get('source_url', ''),
            event.get('impact_score', event.get('score', '')),
            event.get('direction', ''),
            event.get('confidence', ''),
            event.get('rationale', ''),
            event.get('impact_p_move', ''),
            event.get('impact_p_up', ''),
            event.get('impact_p_down', ''),
            event.get('sector', ''),
            event.get('info_tier', ''),
            event.get('info_subtype', '')
        ])
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    # Generate filename with current date
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    filename = f"impactradar_events_{today}.csv"
    
    # Return as streaming response with proper headers
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )


def _build_filter_condition(field: str, operator: str, value: Any):
    """
    Build SQLAlchemy filter condition based on field, operator, and value.
    
    Supported operators:
    - equals, not_equals
    - gt, gte, lt, lte (for numeric fields)
    - contains, not_contains (for text fields)
    - in, not_in (for list values)
    """
    # Map field names to Event model attributes
    field_map = {
        'ticker': Event.ticker,
        'company_name': Event.company_name,
        'event_type': Event.event_type,
        'title': Event.title,
        'description': Event.description,
        'direction': Event.direction,
        'sector': Event.sector,
        'source': Event.source,
        'info_tier': Event.info_tier,
        'info_subtype': Event.info_subtype,
        'impact_score': Event.impact_score,
        'confidence': Event.confidence,
        'date': Event.date,
        'impact_p_move': Event.impact_p_move,
        'impact_p_up': Event.impact_p_up,
        'impact_p_down': Event.impact_p_down,
    }
    
    if field not in field_map:
        raise InvalidInputException(f"Invalid filter field: {field}")
    
    column = field_map[field]
    
    # Build condition based on operator
    if operator == 'equals':
        return column == value
    elif operator == 'not_equals':
        return column != value
    elif operator == 'gt':
        return column > value
    elif operator == 'gte':
        return column >= value
    elif operator == 'lt':
        return column < value
    elif operator == 'lte':
        return column <= value
    elif operator == 'contains':
        return column.ilike(f'%{value}%')
    elif operator == 'not_contains':
        return ~column.ilike(f'%{value}%')
    elif operator == 'in':
        if not isinstance(value, list):
            raise InvalidInputException(f"'in' operator requires a list value")
        return column.in_(value)
    elif operator == 'not_in':
        if not isinstance(value, list):
            raise InvalidInputException(f"'not_in' operator requires a list value")
        return ~column.in_(value)
    else:
        raise InvalidInputException(f"Invalid operator: {operator}")


@router.get(
    "/advanced-search",
    response_model=list[EventDetail],
    responses={
        200: {"description": "List of events matching advanced search criteria"},
        422: {"description": "Validation error - Invalid query parameters"},
    },
    summary="Advanced multi-criteria event search",
    description="Search events with complex multi-criteria filters, AND/OR logic, and keyword search across multiple fields. No authentication required for dashboard users."
)
async def advanced_search_events(
    filters: Optional[str] = None,
    logic: str = "AND",
    keyword: Optional[str] = None,
    keyword_fields: Optional[str] = None,
    limit: int = 100,
    offset: int = 0,
    dm: DataManager = Depends(get_data_manager)
):
    """
    Advanced search with multi-criteria filtering and keyword search.
    
    Args:
        filters: JSON string of filter array, e.g., '[{"field": "event_type", "operator": "equals", "value": "fda_approval"}]'
        logic: "AND" or "OR" - how to combine filters (default: AND)
        keyword: Keyword to search across text fields
        keyword_fields: Comma-separated list of fields to search (default: title,description,company_name)
        limit: Maximum number of results
        offset: Pagination offset
    
    Example:
        /events/advanced-search?filters=[{"field":"impact_score","operator":"gte","value":75},{"field":"direction","operator":"equals","value":"positive"}]&logic=AND&keyword=approval
    """
    db = get_db()
    try:
        query = db.query(Event)
        
        # Parse and apply filters if provided
        if filters:
            try:
                filter_list = json.loads(filters)
                if not isinstance(filter_list, list):
                    raise InvalidInputException("filters must be a JSON array")
                
                # Build filter conditions
                conditions = []
                for filter_item in filter_list:
                    if not isinstance(filter_item, dict):
                        raise InvalidInputException("Each filter must be an object with field, operator, and value")
                    
                    field = filter_item.get('field')
                    operator = filter_item.get('operator')
                    value = filter_item.get('value')
                    
                    if not field or not operator or value is None:
                        raise InvalidInputException("Each filter must have field, operator, and value")
                    
                    # Handle date parsing for date fields
                    if field == 'date' and isinstance(value, str):
                        try:
                            value_normalized = value.replace('Z', '+00:00')
                            value = datetime.fromisoformat(value_normalized)
                        except ValueError as e:
                            raise InvalidInputException(f"Invalid date format in filter: {str(e)}")
                    
                    condition = _build_filter_condition(field, operator, value)
                    conditions.append(condition)
                
                # Combine conditions with AND or OR logic
                if conditions:
                    if logic.upper() == 'OR':
                        query = query.filter(or_(*conditions))
                    else:  # Default to AND
                        query = query.filter(and_(*conditions))
                        
            except json.JSONDecodeError as e:
                raise InvalidInputException(f"Invalid JSON in filters parameter: {str(e)}")
        
        # Apply keyword search if provided
        if keyword:
            # Determine which fields to search
            if keyword_fields:
                search_fields = [f.strip() for f in keyword_fields.split(',')]
            else:
                # Default to all text fields
                search_fields = ['title', 'description', 'company_name']
            
            # Build keyword search conditions
            keyword_conditions = []
            for field in search_fields:
                if field == 'title':
                    keyword_conditions.append(Event.title.ilike(f'%{keyword}%'))
                elif field == 'description':
                    keyword_conditions.append(Event.description.ilike(f'%{keyword}%'))
                elif field == 'company_name':
                    keyword_conditions.append(Event.company_name.ilike(f'%{keyword}%'))
                elif field == 'ticker':
                    keyword_conditions.append(Event.ticker.ilike(f'%{keyword}%'))
                elif field == 'event_type':
                    keyword_conditions.append(Event.event_type.ilike(f'%{keyword}%'))
                elif field == 'sector':
                    keyword_conditions.append(Event.sector.ilike(f'%{keyword}%'))
            
            # Combine keyword conditions with OR (keyword should match any of the fields)
            if keyword_conditions:
                query = query.filter(or_(*keyword_conditions))
        
        # Order by date descending
        query = query.order_by(Event.date.desc())
        
        # Get total count before pagination
        total = query.count()
        
        # Apply pagination
        query = query.offset(offset).limit(limit)
        
        # Execute query
        events = query.all()
        
        # Convert to dictionaries
        result = []
        for event in events:
            result.append(dm._event_to_dict(event))
        
        return [EventDetail(**event) for event in result]
        
    finally:
        close_db_session(db)


@router.get(
    "/marketing/weekly",
    response_model=dict,
    responses={
        200: {"description": "Weekly event highlights for email campaigns"},
    },
    summary="Get weekly event highlights (public)",
    description="Get high-impact events from the past week for 'What You Missed' email campaigns. Completely public - no authentication required."
)
async def get_marketing_weekly_highlights(
    dm: DataManager = Depends(get_data_manager)
):
    """
    Public endpoint for weekly highlights in email campaigns (Tip #11: What You Missed)
    Returns top events from the past 7 days for marketing emails.
    Completely public - no authentication or API key required.
    """
    # Get events from last 7 days (timezone-aware)
    end_date = datetime.now(timezone.utc)
    start_date = end_date - timedelta(days=7)
    
    # Get high-impact events (score >= 70)
    events = dm.get_events(
        start_date=start_date,
        end_date=end_date,
        min_impact=70
    )
    
    # Group by direction
    positive_events = [e for e in events if e.get('direction') == 'positive']
    negative_events = [e for e in events if e.get('direction') == 'negative']
    
    # Get top 5 positive and top 5 negative by impact score
    top_positive = sorted(positive_events, key=lambda x: x.get('impact_score', 0), reverse=True)[:5]
    top_negative = sorted(negative_events, key=lambda x: x.get('impact_score', 0), reverse=True)[:5]
    
    # Calculate summary stats
    total_events = len(events)
    avg_impact = sum(e.get('impact_score', 0) for e in events) / len(events) if events else 0
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
            "days": 7
        },
        "summary": {
            "total_events": total_events,
            "average_impact": round(avg_impact, 1),
            "positive_events": len(positive_events),
            "negative_events": len(negative_events)
        },
        "top_positive": [EventDetail(**e) for e in top_positive],
        "top_negative": [EventDetail(**e) for e in top_negative],
        "message": f"You missed {total_events} market-moving events this week. Upgrade to catch the next one in real-time."
    }


@router.get(
    "/{event_id}",
    response_model=EventDetail,
    responses={
        200: {"description": "Event details"},
        401: {"description": "Unauthorized - Invalid or missing API key"},
        404: {"description": "Event not found"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Get event by ID",
    description="Retrieve detailed information about a specific event by ID. Requires Pro or Team plan API key."
)
@limiter.limit(plan_limit)
async def get_event(
    request: Request,
    event_id: int,
    dm: DataManager = Depends(get_data_manager),
    x_api_key: Optional[str] = Header(None),
    _key = Depends(require_api_key)
):
    """Get single event by ID (requires Pro or Team plan)"""
    event = dm.get_event(event_id)
    
    if not event:
        raise ResourceNotFoundException("Event", str(event_id))
    
    # Return event (already enriched by DataManager)
    return EventDetail(**event)


@router.get(
    "/{event_id}/summary",
    responses={
        200: {"description": "AI-generated summary of the event"},
        404: {"description": "Event not found"},
        429: {"description": "Rate limit exceeded"},
        503: {"description": "AI service unavailable"},
    },
    summary="Generate AI summary for an event",
    description="Generate a 3-6 sentence AI summary describing the event, its impact on shareholders, and projected earnings/losses. Uses Market Echo V2.0 engine with actual filing content analysis."
)
@limiter.limit("10/minute")
async def get_event_summary(
    request: Request,
    event_id: int,
    dm: DataManager = Depends(get_data_manager),
    user_data: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Generate AI-powered summary for a specific event.
    
    The summary includes:
    - Description of what the event is (now with actual filing content)
    - Impact on stock and shareholders
    - Projected earnings/losses with percentage changes
    
    For high-value filings (8-K items 1.01, 2.01, 2.02, 7.01; FDA approvals),
    fetches and analyzes actual source document content.
    
    Returns:
        Summary text with Market Echo V2.0 branding
    """
    import os
    import httpx
    from releaseradar.services.filing_content_service import get_filing_content_service
    
    event = dm.get_event(event_id)
    if not event:
        raise ResourceNotFoundException(f"Event with id {event_id} not found")
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503, 
            detail="AI service not configured. Please contact support."
        )
    
    direction_text = {
        "positive": "bullish/positive",
        "negative": "bearish/negative",
        "neutral": "neutral",
        "uncertain": "uncertain"
    }.get(event.get("direction", "uncertain"), "uncertain")
    
    ml_adjusted_score = event.get("ml_adjusted_score") or event.get("impact_score", 50)
    
    projection = calculate_projection_for_event(event)
    
    projected_move_pct = abs(projection.projected_move_pct)
    projected_direction = projection.projected_direction
    if projection.projected_move_pct >= 0:
        projected_move_display = f"+{projected_move_pct:.1f}%"
    else:
        projected_move_display = f"-{projected_move_pct:.1f}%"
    
    impact_p_move = projection.probability_move
    impact_p_up = projection.probability_up
    impact_p_down = projection.probability_down
    prob_source = projection.data_source
    
    filing_content_section = ""
    filing_fetch_attempted = False
    source_url = event.get("source_url") or event.get("url")
    event_type = event.get("event_type", "")
    
    if source_url:
        filing_service = get_filing_content_service()
        event_metadata = {
            "8k_items": event.get("8k_items", []),
        }
        
        if filing_service.should_fetch_full_content(event_type, event_metadata):
            filing_fetch_attempted = True
            try:
                filing_summary = filing_service.get_filing_summary_for_ai(
                    source_url, event_type, max_length=3000
                )
                if filing_summary and not filing_summary.startswith("[Unable"):
                    filing_content_section = f"""

ACTUAL FILING CONTENT (from source document):
{filing_summary}
"""
            except Exception as e:
                import logging
                logging.getLogger("events").warning(
                    f"Failed to fetch filing content for event {event_id}: {e}"
                )
    
    prompt = f"""Analyze this market event and provide a concise summary for investors.

EVENT DETAILS:
- Company: {event.get("company_name", "Unknown")} ({event.get("ticker", "N/A")})
- Event Type: {event_type.replace("_", " ").title()}
- Title: {event.get("title", "N/A")}
- Description: {event.get("description", "No description available")}
- Date: {event.get("date", "N/A")}
- Direction: {direction_text}
- Impact Score: {ml_adjusted_score}/100
{filing_content_section}
PROJECTED PRICE IMPACT (based on {prob_source}):
- Projected price move: {projected_move_display} ({projected_direction})
- Probability of significant move (>3%): {(impact_p_move * 100):.1f}%
- Probability of upside move: {(impact_p_up * 100):.1f}%  
- Probability of downside move: {(impact_p_down * 100):.1f}%

TASK: Write a summary of 3-6 sentences that:
1. Explains what this event is in plain language{' - use specific details from the actual filing content if provided' if filing_content_section else ''}
2. Describes what this means for the stock and shareholders
3. States the projected percentage change and whether it's likely to be positive or negative
4. Mentions any relevant context about the company or market implications

RULES:
- Be factual and professional
- Use specific numbers from the data provided{' and from the actual filing content' if filing_content_section else ''}
- Always mention this is a projection based on historical patterns, not a guarantee
- Do NOT provide investment advice or recommendations
- Keep it concise (3-6 sentences maximum)"""

    try:
        system_instructions = "You are a financial analyst assistant that provides clear, factual summaries of market events. You always cite specific data and probabilities. You never provide investment advice."
        
        async with httpx.AsyncClient(timeout=45.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-5.1",
                    "instructions": system_instructions,
                    "input": prompt,
                    "reasoning": {"effort": "low"},
                    "text": {"format": {"type": "text"}}
                }
            )
            response.raise_for_status()
            data = response.json()
            
            # Extract text from Responses API format
            summary_text = ""
            if "output" in data:
                for item in data["output"]:
                    if item.get("type") == "message":
                        content = item.get("content", [])
                        for c in content:
                            if c.get("type") == "output_text":
                                summary_text = c.get("text", "")
                                break
            if not summary_text and "output_text" in data:
                summary_text = data["output_text"]
            
            return {
                "event_id": event_id,
                "summary": summary_text,
                "model_version": "V2.0 (Market Echo)",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "event_ticker": event.get("ticker"),
                "event_title": event.get("title"),
                "projected_move": projected_move_display,
                "projected_direction": projected_direction
            }
            
    except httpx.HTTPStatusError as e:
        raise HTTPException(
            status_code=503,
            detail="AI service temporarily unavailable. Please try again later."
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail="Failed to generate summary. Please try again later."
        )


@router.get(
    "/{event_id}/similar",
    responses={
        200: {"description": "Similar historical events with their outcomes"},
        404: {"description": "Event not found"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Get similar historical events",
    description="Find similar past events for a given event and show their 1d/5d/20d price outcomes. Provides concrete precedent data for investors."
)
@limiter.limit("30/minute")
async def get_similar_events(
    request: Request,
    event_id: int,
    max_results: int = 10,
    dm: DataManager = Depends(get_data_manager),
    user_data: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Find similar historical events and their outcomes.
    
    Matching strategies:
    1. Same ticker + same event type (highest relevance)
    2. Same sector + same event type (good for sector-wide patterns)
    3. Keyword matching in title (for specific themes like "iPhone launch")
    4. Same event type + similar score range (fallback)
    
    Returns:
        Similar events with their actual 1d/5d/20d price changes,
        aggregate statistics, and confidence level.
    """
    from releaseradar.services.historical_event_matcher import get_historical_matcher
    from releaseradar.db.session import get_db as get_db_session
    from database import close_db_session
    
    event = dm.get_event(event_id)
    if not event:
        raise ResourceNotFoundException(f"Event with id {event_id} not found")
    
    db = get_db_session()
    try:
        matcher = get_historical_matcher(db)
        result = matcher.find_similar_events(
            event=event,
            max_results=max_results,
            min_days_ago=7,
            max_days_ago=730
        )
        
        return {
            "event_id": event_id,
            "event_ticker": event.get("ticker"),
            "event_type": event.get("event_type"),
            "similar_events": result.to_dict()["similar_events"],
            "statistics": {
                "total_matches": result.total_matches,
                "avg_1d_change": result.avg_1d_change,
                "avg_5d_change": result.avg_5d_change,
                "avg_20d_change": result.avg_20d_change,
                "positive_outcome_pct": result.positive_outcome_pct,
                "sample_size": result.sample_size,
                "confidence_level": result.confidence_level
            },
            "pattern_description": result.pattern_description
        }
    finally:
        close_db_session(db)
