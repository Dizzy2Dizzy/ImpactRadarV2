"""Portfolio router"""
from fastapi import APIRouter, Depends, Request, Header, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List
import yfinance as yf
from datetime import datetime, timedelta, date, timezone
import csv
import io
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from api.schemas.portfolio import (
    PortfolioEstimateRequest,
    PortfolioEstimateResponse,
    PositionImpact,
    UploadPositionRow,
    UploadResponse,
    UploadError,
    InsightsResponse,
    PositionInsight,
    InsightEvent,
    PortfolioResponse,
    CSVUploadResponse,
    HoldingResponse,
    PortfolioInsightResponse
)
from api.dependencies import get_data_manager
from api.utils.auth import get_current_user_id
from api.utils.api_key import require_api_key
from api.utils.metrics import increment_metric
from data_manager import DataManager
from releaseradar.db.models import UserPortfolio, PortfolioPosition, Company, Event, EventStats, EventScore, User
from api.dependencies import get_db
from api.utils.paywall import require_plan

router = APIRouter(prefix="/portfolio", tags=["portfolio"])

# Import limiter and plan_limit from ratelimit module
from api.ratelimit import limiter, plan_limit


@router.post("/estimate", response_model=PortfolioEstimateResponse)
@limiter.limit(plan_limit)
async def estimate_portfolio_impact(
    request: PortfolioEstimateRequest,
    req: Request = None,
    user_id: int = Depends(get_current_user_id),
    dm: DataManager = Depends(get_data_manager),
    x_api_key: Optional[str] = Header(None),
    _key = Depends(require_api_key)
):
    """Estimate portfolio impact based on upcoming events (requires Pro or Team plan)"""
    positions_impact = []
    total_value = 0.0
    total_pnl = 0.0
    
    # Get events window
    end_date = datetime.now() + timedelta(days=request.events_window)
    
    for position in request.positions:
        # Get current price using yfinance
        try:
            ticker_data = yf.Ticker(position.ticker)
            hist = ticker_data.history(period="1d")
            current_price = hist['Close'].iloc[-1] if not hist.empty else position.cost_basis
        except:
            current_price = position.cost_basis
        
        # Calculate P&L
        position_value = current_price * position.quantity
        unrealized_pnl = (current_price - position.cost_basis) * position.quantity
        
        # Get upcoming events
        events = dm.get_events(ticker=position.ticker, end_date=end_date)
        
        # Calculate risk score based on event impacts
        risk_score = 0
        if events:
            avg_score = sum(e.get('score', 50) for e in events) / len(events)
            risk_score = int(avg_score)
        
        # Determine estimated impact
        if len(events) == 0:
            estimated_impact = "Low - No upcoming events"
        elif risk_score > 75:
            estimated_impact = f"High - {len(events)} high-impact events"
        elif risk_score > 60:
            estimated_impact = f"Medium - {len(events)} moderate events"
        else:
            estimated_impact = f"Low - {len(events)} low-impact events"
        
        positions_impact.append(PositionImpact(
            ticker=position.ticker,
            quantity=position.quantity,
            cost_basis=position.cost_basis,
            current_price=current_price,
            unrealized_pnl=unrealized_pnl,
            upcoming_events=len(events),
            risk_score=risk_score,
            estimated_impact=estimated_impact
        ))
        
        total_value += position_value
        total_pnl += unrealized_pnl
    
    # Calculate risk summary
    high_risk_count = sum(1 for p in positions_impact if p.risk_score > 75)
    medium_risk_count = sum(1 for p in positions_impact if 60 < p.risk_score <= 75)
    
    # Calculate total cost basis for P&L percentage
    total_cost = sum(p.cost_basis * p.quantity for p in positions_impact)
    pnl_percentage = (total_pnl / total_cost * 100) if total_cost > 0 else 0
    
    # Determine portfolio risk level based on both P&L and event risk
    # Guard against empty portfolio
    if len(positions_impact) == 0:
        portfolio_risk_level = "Low"
    else:
        # P&L-based risk: High if >20% loss, Medium if 5-20% loss
        # Event-based risk: High if >1/3 high-risk events, Medium if any medium-risk events
        pnl_risk = "High" if pnl_percentage < -20 else ("Medium" if pnl_percentage < -5 else "Low")
        event_risk = "High" if high_risk_count > len(positions_impact) / 3 else ("Medium" if medium_risk_count > 0 else "Low")
        
        # Take the higher risk level of the two
        risk_levels = {"Low": 0, "Medium": 1, "High": 2}
        portfolio_risk_level = max(pnl_risk, event_risk, key=lambda x: risk_levels[x])
    
    risk_summary = {
        "high_risk_positions": high_risk_count,
        "medium_risk_positions": medium_risk_count,
        "total_upcoming_events": sum(p.upcoming_events for p in positions_impact),
        "portfolio_risk_level": portfolio_risk_level
    }
    
    return PortfolioEstimateResponse(
        positions=positions_impact,
        total_value=total_value,
        total_pnl=total_pnl,
        risk_summary=risk_summary
    )


@router.post(
    "/upload",
    response_model=CSVUploadResponse,
    responses={
        200: {"description": "Portfolio uploaded successfully"},
        400: {"description": "Invalid CSV format or data"},
        401: {"description": "Unauthorized - Invalid or missing API key"},
        402: {"description": "Payment Required - Plan limit exceeded"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Upload portfolio from CSV",
    description="Upload portfolio positions from CSV file. Requires columns: ticker, qty/shares, avg_price/cost_basis. Optional columns: label, as_of. Pro plan limited to 3 tickers, Team plan unlimited."
)
@limiter.limit(plan_limit)
async def upload_portfolio(
    file: UploadFile = File(...),
    request: Request = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Upload portfolio from CSV file (ticker, shares, cost_basis, label)"""
    
    # Debug logging
    print(f"[UPLOAD] File received: {file.filename}, content_type: {file.content_type}, size: {file.size}")
    
    # Get user to check plan
    user = db.execute(select(User).where(User.id == user_id)).scalar_one()
    
    # Read and parse CSV
    content = await file.read()
    print(f"[UPLOAD] Content length: {len(content)} bytes")
    csv_text = content.decode('utf-8')
    print(f"[UPLOAD] CSV text (first 200 chars): {csv_text[:200]}")
    csv_reader = csv.DictReader(io.StringIO(csv_text))
    
    errors: List[UploadError] = []
    valid_positions: List[UploadPositionRow] = []
    
    # Get all tracked companies for validation (warn but allow untracked)
    tracked_tickers = set(db.execute(
        select(Company.ticker).where(Company.tracked == True)
    ).scalars())
    
    # Detect CSV format by checking headers
    first_row = next(csv_reader, None)
    if first_row is None:
        raise HTTPException(status_code=400, detail="CSV file is empty")
    
    # Reset reader to read all rows
    csv_reader = csv.DictReader(io.StringIO(csv_text))
    
    # Check if this is brokerage transaction format (has Symbol, Quantity, Price columns)
    is_transaction_format = 'Symbol' in first_row and 'Quantity' in first_row and 'Price' in first_row
    
    print(f"[UPLOAD] Format detected: {'Transaction' if is_transaction_format else 'Simple'} format")
    
    for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is 1)
        try:
            if is_transaction_format:
                # Brokerage transaction format
                ticker = row.get('Symbol', '').strip().upper()
                shares_str = row.get('Quantity', '')
                price_str = row.get('Price', '').replace('$', '').replace(',', '')
                date_str = row.get('Date', '')
                action = row.get('Action', '').strip()
            else:
                # Simple format - support both "shares" and "qty" column names
                ticker = row.get('ticker', '').strip().upper()
                shares_str = row.get('shares', row.get('qty', ''))
                price_str = row.get('cost_basis', row.get('avg_price', ''))
                date_str = row.get('as_of', '')
                action = None
            
            cost_basis_str = price_str
            label = row.get('label', '').strip() or None if not is_transaction_format else action
            
            # Check ticker is required
            if not ticker:
                continue  # Skip rows without ticker (like header rows)
            
            # Warn if ticker not tracked (but allow)
            if ticker not in tracked_tickers:
                errors.append(UploadError(
                    row=row_num,
                    field='ticker',
                    message=f'Warning: Ticker {ticker} is not tracked in our system (will be added anyway)'
                ))
            
            # Parse shares
            try:
                shares = float(shares_str) if shares_str else 0.0
                # For transaction format, some actions may be negative (sells)
            except (ValueError, TypeError):
                errors.append(UploadError(row=row_num, field='shares', message=f'Shares must be a number, got: {shares_str}'))
                continue
            
            # Parse cost_basis (optional)
            cost_basis = 0.0
            if cost_basis_str:
                try:
                    cost_basis = float(cost_basis_str)
                except (ValueError, TypeError):
                    errors.append(UploadError(row=row_num, field='cost_basis', message=f'Cost basis must be a number, got: {cost_basis_str}'))
                    continue
            
            # Parse date (default to today if not provided)
            if date_str:
                try:
                    # Try MM/DD/YYYY format first (common in brokerage exports)
                    if '/' in date_str:
                        as_of = datetime.strptime(date_str, '%m/%d/%Y').date()
                    else:
                        as_of = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    as_of = date.today()
            else:
                as_of = date.today()
            
            # Add valid position
            valid_positions.append(UploadPositionRow(
                ticker=ticker,
                qty=shares,
                avg_price=cost_basis if cost_basis else 0.0,
                as_of=as_of,
                label=label
            ))
            
        except Exception as e:
            errors.append(UploadError(row=row_num, field='general', message=str(e)))
    
    # If no valid positions, return error
    if not valid_positions:
        raise HTTPException(status_code=400, detail={"errors": [e.dict() for e in errors]})
    
    # Aggregate duplicate tickers (sum shares, weighted avg cost_basis, keep latest label)
    from collections import defaultdict
    ticker_positions = defaultdict(lambda: {'total_qty': 0.0, 'weighted_sum': 0.0, 'as_of': None, 'label': None})
    
    for pos in valid_positions:
        ticker_positions[pos.ticker]['total_qty'] += pos.qty
        ticker_positions[pos.ticker]['weighted_sum'] += pos.qty * pos.avg_price
        # Keep the most recent as_of date
        if ticker_positions[pos.ticker]['as_of'] is None or pos.as_of > ticker_positions[pos.ticker]['as_of']:
            ticker_positions[pos.ticker]['as_of'] = pos.as_of
        # Keep the latest label (if any)
        if pos.label:
            ticker_positions[pos.ticker]['label'] = pos.label
    
    # Convert aggregated data back to positions (skip zero-quantity positions)
    aggregated_positions = []
    for ticker, data in ticker_positions.items():
        # Skip zero-quantity positions (offsetting trades)
        if data['total_qty'] == 0:
            continue
        
        # Calculate weighted average price (works for both long and short positions)
        avg_price = data['weighted_sum'] / data['total_qty'] if data['total_qty'] != 0 else 0
        aggregated_positions.append(UploadPositionRow(
            ticker=ticker,
            qty=data['total_qty'],
            avg_price=avg_price,
            as_of=data['as_of'],
            label=data['label']
        ))
    
    # Plan-based access control: Free plan limited to 3 tickers
    if user.plan == "free" and len(aggregated_positions) > 3:
        require_plan(user.plan, "pro", "portfolio_unlimited_tickers", user.trial_ends_at)
    
    # Get or create user's portfolio
    portfolio = db.execute(
        select(UserPortfolio).where(UserPortfolio.user_id == user_id)
    ).scalar_one_or_none()
    
    if portfolio:
        # Delete existing positions
        db.execute(delete(PortfolioPosition).where(PortfolioPosition.portfolio_id == portfolio.id))
        portfolio.name = "Default Portfolio"
        portfolio.updated_at = datetime.utcnow()
    else:
        # Create new portfolio
        portfolio = UserPortfolio(
            user_id=user_id,
            name="Default Portfolio"
        )
        db.add(portfolio)
        db.flush()  # Get portfolio ID
    
    # Add aggregated positions
    try:
        for pos in aggregated_positions:
            position = PortfolioPosition(
                portfolio_id=portfolio.id,
                ticker=pos.ticker,
                qty=pos.qty,
                avg_price=pos.avg_price,
                as_of=pos.as_of,
                label=pos.label
            )
            db.add(position)
        
        db.commit()
    except IntegrityError as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Database constraint error: {str(e)}")
    
    # Update metrics (count aggregated positions, not original valid positions)
    increment_metric('portfolio_positions_total', len(aggregated_positions))
    
    return CSVUploadResponse(
        portfolio_id=portfolio.id,
        holdings_count=len(aggregated_positions),
        tickers=[pos.ticker for pos in aggregated_positions]
    )


# Simple price cache to avoid rate limiting (5 minute TTL)
price_cache = {}
PRICE_CACHE_TTL = 300  # 5 minutes


def get_cached_price(ticker: str) -> Optional[float]:
    """Get cached price if available and not expired"""
    if ticker in price_cache:
        price, timestamp = price_cache[ticker]
        if (datetime.now() - timestamp).total_seconds() < PRICE_CACHE_TTL:
            return price
    return None


def cache_price(ticker: str, price: float):
    """Cache price with current timestamp"""
    price_cache[ticker] = (price, datetime.now())


@router.get("/holdings", response_model=List[HoldingResponse])
@limiter.limit(plan_limit)
async def get_portfolio_holdings(
    request: Request = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Fetch user's portfolio holdings with current prices and calculations"""
    
    # Get user's portfolio
    portfolio = db.execute(
        select(UserPortfolio).where(UserPortfolio.user_id == user_id)
    ).scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="No portfolio found. Please upload a portfolio first.")
    
    # Get positions
    positions = db.execute(
        select(PortfolioPosition).where(PortfolioPosition.portfolio_id == portfolio.id)
    ).scalars().all()
    
    if not positions:
        return []
    
    holdings: List[HoldingResponse] = []
    
    for pos in positions:
        # Get company info
        company = db.execute(
            select(Company).where(Company.ticker == pos.ticker)
        ).scalar_one_or_none()
        
        company_name = company.name if company else None
        sector = company.sector if company else None
        
        # Get current price with caching
        current_price = get_cached_price(pos.ticker)
        if current_price is None:
            try:
                ticker_data = yf.Ticker(pos.ticker)
                hist = ticker_data.history(period="1d")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    cache_price(pos.ticker, current_price)
                else:
                    current_price = None
            except Exception as e:
                current_price = None
        
        # Calculate market value and gain/loss
        market_value = None
        gain_loss = None
        if current_price is not None and pos.avg_price > 0:
            market_value = pos.qty * current_price
            gain_loss = (current_price - pos.avg_price) * pos.qty
        
        holdings.append(HoldingResponse(
            ticker=pos.ticker,
            company_name=company_name,
            shares=pos.qty,
            cost_basis=pos.avg_price if pos.avg_price > 0 else None,
            current_price=current_price,
            market_value=market_value,
            gain_loss=gain_loss,
            sector=sector,
            label=pos.label
        ))
    
    return holdings


@router.get(
    "/insights",
    response_model=List[PortfolioInsightResponse],
    responses={
        200: {"description": "Portfolio event exposure insights"},
        401: {"description": "Unauthorized - Invalid or missing API key"},
        404: {"description": "No portfolio found"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Get portfolio event exposure insights",
    description="Analyze portfolio exposure to upcoming events. Returns risk scores, expected dollar moves (1d, 5d, 20d), and upcoming events for each position. Requires uploaded portfolio."
)
@limiter.limit(plan_limit)
async def get_portfolio_insights(
    window_days: int = 30,
    request: Request = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get event exposure insights for portfolio positions (14-30 day window)"""
    
    # Increment metrics
    increment_metric('portfolio_insights_requests_total')
    
    # Get user's portfolio
    portfolio = db.execute(
        select(UserPortfolio).where(UserPortfolio.user_id == user_id)
    ).scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="No portfolio found. Please upload a portfolio first.")
    
    # Get positions
    positions = db.execute(
        select(PortfolioPosition).where(PortfolioPosition.portfolio_id == portfolio.id)
    ).scalars().all()
    
    if not positions:
        return []
    
    # Calculate date window (timezone-aware to match Event.date)
    start_date = datetime.now(tz=timezone.utc)
    end_date = start_date + timedelta(days=window_days)
    
    insights: List[PortfolioInsightResponse] = []
    
    for pos in positions:
        # Get current price with caching
        current_price = get_cached_price(pos.ticker)
        if current_price is None:
            try:
                ticker_data = yf.Ticker(pos.ticker)
                hist = ticker_data.history(period="1d")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    cache_price(pos.ticker, current_price)
                else:
                    current_price = pos.avg_price
            except:
                current_price = pos.avg_price
        
        market_value = current_price * pos.qty
        
        # Get upcoming events in window
        events = db.execute(
            select(Event).where(
                Event.ticker == pos.ticker,
                Event.date >= start_date,
                Event.date <= end_date
            ).order_by(Event.date)
        ).scalars().all()
        
        if not events:
            # Skip positions with no upcoming events
            continue
        
        # Calculate exposures and risk score
        exposure_1d = 0.0
        exposure_5d = 0.0
        exposure_20d = 0.0
        total_risk_score = 0.0
        event_list = []
        
        for event in events:
            # Get event score
            event_score = db.execute(
                select(EventScore).where(EventScore.event_id == event.id)
            ).scalar_one_or_none()
            
            score = event_score.final_score if event_score else event.impact_score
            confidence = event_score.confidence if event_score else (event.confidence * 100 if event.confidence else 70)
            
            # Accumulate risk score (weighted by confidence)
            total_risk_score += (score * confidence / 100.0)
            
            # Get historical stats
            stats = db.execute(
                select(EventStats).where(
                    EventStats.ticker == pos.ticker,
                    EventStats.event_type == event.event_type
                )
            ).scalar_one_or_none()
            
            # Calculate expected move percentages
            # If we have stats, use them; otherwise estimate from impact score
            if stats:
                move_1d_pct = stats.avg_abs_move_1d if stats.avg_abs_move_1d else (score / 20.0)  # score 80 → 4%
                move_5d_pct = stats.avg_abs_move_5d if stats.avg_abs_move_5d else (score / 15.0)  # score 80 → 5.3%
                move_20d_pct = stats.avg_abs_move_20d if stats.avg_abs_move_20d else (score / 10.0)  # score 80 → 8%
            else:
                # Fallback: map impact score to expected move percentage
                # score 80 → ~5% 1d move, ~7% 5d move, ~10% 20d move
                move_1d_pct = score / 16.0  # 80 → 5%
                move_5d_pct = score / 11.4  # 80 → 7%
                move_20d_pct = score / 8.0   # 80 → 10%
            
            # Calculate dollar exposure: shares * price * (move_pct / 100)
            exposure_1d += abs(pos.qty * current_price * move_1d_pct / 100.0)
            exposure_5d += abs(pos.qty * current_price * move_5d_pct / 100.0)
            exposure_20d += abs(pos.qty * current_price * move_20d_pct / 100.0)
            
            # Add event to list
            event_list.append({
                "title": event.title,
                "date": event.date.isoformat(),
                "score": score,
                "direction": event.direction
            })
        
        insights.append(PortfolioInsightResponse(
            ticker=pos.ticker,
            shares=pos.qty,
            market_value=market_value,
            upcoming_events_count=len(events),
            total_risk_score=total_risk_score / len(events) if events else 0.0,  # Average risk
            exposure_1d=exposure_1d,
            exposure_5d=exposure_5d,
            exposure_20d=exposure_20d,
            events=event_list
        ))
    
    return insights


@router.get("", response_model=PortfolioResponse)
async def get_portfolio(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get current portfolio details"""
    portfolio = db.execute(
        select(UserPortfolio).where(UserPortfolio.user_id == user_id)
    ).scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="No portfolio found")
    
    positions_count = db.execute(
        select(func.count(PortfolioPosition.id)).where(
            PortfolioPosition.portfolio_id == portfolio.id
        )
    ).scalar()
    
    return PortfolioResponse(
        id=portfolio.id,
        name=portfolio.name,
        created_at=portfolio.created_at,
        positions_count=positions_count
    )


@router.delete("")
async def delete_portfolio(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete current portfolio"""
    result = db.execute(delete(UserPortfolio).where(UserPortfolio.user_id == user_id))
    db.commit()
    
    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="No portfolio found")
    
    return {"success": True, "message": "Portfolio deleted"}


@router.get("/list", response_model=List[PortfolioResponse])
async def list_portfolios(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get all portfolios for the current user"""
    portfolios = db.execute(
        select(UserPortfolio).where(UserPortfolio.user_id == user_id).order_by(UserPortfolio.created_at.desc())
    ).scalars().all()
    
    result = []
    for portfolio in portfolios:
        positions_count = db.execute(
            select(func.count(PortfolioPosition.id)).where(
                PortfolioPosition.portfolio_id == portfolio.id
            )
        ).scalar()
        
        result.append(PortfolioResponse(
            id=portfolio.id,
            name=portfolio.name,
            created_at=portfolio.created_at,
            positions_count=positions_count
        ))
    
    return result


@router.delete("/{portfolio_id}")
async def delete_portfolio_by_id(
    portfolio_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete a specific portfolio by ID"""
    portfolio = db.execute(
        select(UserPortfolio).where(
            UserPortfolio.id == portfolio_id,
            UserPortfolio.user_id == user_id
        )
    ).scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="Portfolio not found")
    
    portfolio_name = portfolio.name
    
    db.delete(portfolio)
    db.commit()
    
    return {"success": True, "message": f"Portfolio '{portfolio_name}' deleted"}


@router.get(
    "/export",
    responses={
        200: {"description": "CSV file download", "content": {"text/csv": {}}},
        404: {"description": "No portfolio found"},
        429: {"description": "Rate limit exceeded"},
    },
    summary="Export portfolio analysis to CSV",
    description="Export portfolio holdings with event exposure analysis to CSV file. Includes position details, risk metrics, and upcoming events."
)
@limiter.limit(plan_limit)
async def export_portfolio_csv(
    window_days: int = 30,
    request: Request = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Export portfolio analysis to CSV with event exposure data"""
    
    # Get user's portfolio
    portfolio = db.execute(
        select(UserPortfolio).where(UserPortfolio.user_id == user_id)
    ).scalar_one_or_none()
    
    if not portfolio:
        raise HTTPException(status_code=404, detail="No portfolio found. Please upload a portfolio first.")
    
    # Get positions
    positions = db.execute(
        select(PortfolioPosition).where(PortfolioPosition.portfolio_id == portfolio.id)
    ).scalars().all()
    
    if not positions:
        raise HTTPException(status_code=404, detail="Portfolio has no positions")
    
    # Calculate date window
    start_date = datetime.now(tz=timezone.utc)
    end_date = start_date + timedelta(days=window_days)
    
    # Create CSV in memory
    output = io.StringIO()
    csv_writer = csv.writer(output)
    
    # Write header for portfolio summary
    csv_writer.writerow(['Portfolio Analysis Export'])
    csv_writer.writerow(['Export Date', datetime.now().strftime('%Y-%m-%d %H:%M:%S')])
    csv_writer.writerow(['Analysis Window', f'{window_days} days'])
    csv_writer.writerow([])
    
    # Write holdings header
    csv_writer.writerow([
        'ticker',
        'quantity',
        'avg_price',
        'current_price',
        'total_value',
        'events_count',
        'high_impact_events',
        'avg_impact_score',
        'risk_exposure',
        'exposure_1d',
        'exposure_5d',
        'exposure_20d'
    ])
    
    # Process each position
    total_portfolio_value = 0.0
    total_events_count = 0
    total_high_impact_events = 0
    all_position_events = []
    
    for pos in positions:
        # Get current price with caching
        current_price = get_cached_price(pos.ticker)
        if current_price is None:
            try:
                ticker_data = yf.Ticker(pos.ticker)
                hist = ticker_data.history(period="1d")
                if not hist.empty:
                    current_price = float(hist['Close'].iloc[-1])
                    cache_price(pos.ticker, current_price)
                else:
                    current_price = pos.avg_price
            except:
                current_price = pos.avg_price
        
        total_value = current_price * pos.qty
        total_portfolio_value += total_value
        
        # Get upcoming events
        events = db.execute(
            select(Event).where(
                Event.ticker == pos.ticker,
                Event.date >= start_date,
                Event.date <= end_date
            ).order_by(Event.date)
        ).scalars().all()
        
        total_events_count += len(events)
        
        # Calculate metrics
        exposure_1d = 0.0
        exposure_5d = 0.0
        exposure_20d = 0.0
        total_impact_score = 0.0
        high_impact_events = 0
        
        for event in events:
            # Get event score
            event_score = db.execute(
                select(EventScore).where(EventScore.event_id == event.id)
            ).scalar_one_or_none()
            
            score = event_score.final_score if event_score else event.impact_score
            total_impact_score += score
            
            if score >= 76:
                high_impact_events += 1
            
            # Get historical stats
            stats = db.execute(
                select(EventStats).where(
                    EventStats.ticker == pos.ticker,
                    EventStats.event_type == event.event_type
                )
            ).scalar_one_or_none()
            
            # Calculate expected move percentages
            if stats:
                move_1d_pct = stats.avg_abs_move_1d if stats.avg_abs_move_1d else (score / 20.0)
                move_5d_pct = stats.avg_abs_move_5d if stats.avg_abs_move_5d else (score / 15.0)
                move_20d_pct = stats.avg_abs_move_20d if stats.avg_abs_move_20d else (score / 10.0)
            else:
                move_1d_pct = score / 16.0
                move_5d_pct = score / 11.4
                move_20d_pct = score / 8.0
            
            # Calculate dollar exposure
            exposure_1d += abs(pos.qty * current_price * move_1d_pct / 100.0)
            exposure_5d += abs(pos.qty * current_price * move_5d_pct / 100.0)
            exposure_20d += abs(pos.qty * current_price * move_20d_pct / 100.0)
            
            # Store event details for later
            all_position_events.append({
                'ticker': pos.ticker,
                'event_title': event.title,
                'event_date': event.date,
                'event_type': event.event_type,
                'impact_score': score,
                'direction': event.direction
            })
        
        total_high_impact_events += high_impact_events
        avg_impact_score = total_impact_score / len(events) if events else 0.0
        
        # Determine risk exposure level
        risk_pct = (exposure_1d / total_value * 100) if total_value > 0 else 0
        if risk_pct >= 10:
            risk_exposure = "High"
        elif risk_pct >= 5:
            risk_exposure = "Medium"
        else:
            risk_exposure = "Low"
        
        # Write position row
        csv_writer.writerow([
            pos.ticker,
            pos.qty,
            f"{pos.avg_price:.2f}",
            f"{current_price:.2f}",
            f"{total_value:.2f}",
            len(events),
            high_impact_events,
            f"{avg_impact_score:.1f}",
            risk_exposure,
            f"{exposure_1d:.2f}",
            f"{exposure_5d:.2f}",
            f"{exposure_20d:.2f}"
        ])
    
    # Write summary section
    csv_writer.writerow([])
    csv_writer.writerow(['Portfolio Summary'])
    csv_writer.writerow(['Total Portfolio Value', f"${total_portfolio_value:.2f}"])
    csv_writer.writerow(['Total Upcoming Events', total_events_count])
    csv_writer.writerow(['High Impact Events', total_high_impact_events])
    csv_writer.writerow(['Positions Count', len(positions)])
    
    # Write detailed events section
    if all_position_events:
        csv_writer.writerow([])
        csv_writer.writerow(['Upcoming Events Detail'])
        csv_writer.writerow(['ticker', 'event_title', 'event_date', 'event_type', 'impact_score', 'direction'])
        
        for evt in all_position_events:
            csv_writer.writerow([
                evt['ticker'],
                evt['event_title'],
                evt['event_date'].strftime('%Y-%m-%d') if evt['event_date'] else '',
                evt['event_type'],
                f"{evt['impact_score']:.1f}",
                evt['direction']
            ])
    
    # Get CSV content
    csv_content = output.getvalue()
    output.close()
    
    # Generate filename with current date
    today = datetime.now().strftime('%Y-%m-%d')
    filename = f"impactradar_portfolio_{today}.csv"
    
    # Return as streaming response with proper headers
    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    )
