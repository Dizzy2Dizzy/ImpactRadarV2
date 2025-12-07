"""
Account management API endpoints.

Provides user account information, performance metrics, and activity tracking.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Dict
from fastapi import APIRouter, Depends, Request, HTTPException
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
import yfinance as yf
import bcrypt
import re

from api.dependencies import get_db

# Price cache for diagnostics endpoint - 5 minute TTL
PRICE_CACHE_TTL = 300  # seconds
price_cache: Dict[str, Tuple[float, datetime]] = {}

# 30-day price change cache - 15 minute TTL (less volatile)
PRICE_CHANGE_CACHE_TTL = 900  # seconds
price_change_cache: Dict[str, Tuple[float, datetime]] = {}


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


def get_cached_price_change(ticker: str) -> Optional[float]:
    """Get cached 30-day price change if available and not expired"""
    if ticker in price_change_cache:
        change, timestamp = price_change_cache[ticker]
        if (datetime.now() - timestamp).total_seconds() < PRICE_CHANGE_CACHE_TTL:
            return change
    return None


def cache_price_change(ticker: str, change: float):
    """Cache 30-day price change with current timestamp"""
    price_change_cache[ticker] = (change, datetime.now())


def fetch_current_price(ticker: str) -> Optional[float]:
    """Fetch current price from yfinance with caching"""
    cached = get_cached_price(ticker)
    if cached is not None:
        return cached
    
    try:
        ticker_data = yf.Ticker(ticker)
        hist = ticker_data.history(period="1d")
        if not hist.empty:
            price = float(hist['Close'].iloc[-1])
            cache_price(ticker, price)
            return price
    except Exception:
        pass
    return None


def fetch_30d_price_change(ticker: str) -> float:
    """Fetch 30-day price change percentage from yfinance with caching"""
    cached = get_cached_price_change(ticker)
    if cached is not None:
        return cached
    
    try:
        ticker_data = yf.Ticker(ticker)
        hist = ticker_data.history(period="35d")  # Get 35 days to ensure we have enough data
        if len(hist) >= 2:
            # Get the price from ~30 days ago and current price
            current_price = float(hist['Close'].iloc[-1])
            # Try to get price from 30 days ago (or closest available)
            old_price_idx = min(len(hist) - 1, 30)
            old_price = float(hist['Close'].iloc[-old_price_idx - 1]) if old_price_idx > 0 else float(hist['Close'].iloc[0])
            
            if old_price > 0:
                change_pct = ((current_price - old_price) / old_price) * 100
                cache_price_change(ticker, change_pct)
                return change_pct
    except Exception:
        pass
    
    # Return 0 if we can't calculate
    cache_price_change(ticker, 0.0)
    return 0.0


from api.utils.auth import get_current_user_id
from api.ratelimit import limiter, plan_limit
from releaseradar.db.models import (
    User,
    WatchlistItem,
    Alert,
    UserPortfolio,
    PortfolioPosition,
    AlertLog,
    Event,
    Company,
    EventGroupPrior
)

router = APIRouter(prefix="/account", tags=["account"])


class AccountSummary(BaseModel):
    """User account summary information."""
    user_id: int
    email: str
    plan: str
    username: Optional[str] = None
    avatar_url: Optional[str] = None
    trial_ends_at: Optional[datetime]
    account_created_at: Optional[datetime]
    last_login: Optional[datetime]
    total_watchlist_companies: int
    total_alerts_configured: int
    total_events_viewed: int


class PerformanceMetrics(BaseModel):
    """User performance and usage metrics."""
    total_portfolio_value: float
    total_positions: int
    events_this_month: int
    events_matched_to_portfolio: int


class ActivityItem(BaseModel):
    """Individual activity record."""
    type: str
    description: str
    timestamp: datetime
    details: Optional[dict] = None


class ActivityLog(BaseModel):
    """Recent account activity."""
    activities: List[ActivityItem]


class Holding(BaseModel):
    """Individual portfolio holding with P&L."""
    ticker: str
    quantity: float
    avg_cost: float
    current_price: float
    total_value: float
    profit_loss: float
    profit_loss_percent: float
    events_count: int


class PortfolioPerformance(BaseModel):
    """Portfolio performance metrics with P&L."""
    holdings: List[Holding]
    total_invested: float
    current_value: float
    total_profit_loss: float
    total_return_percent: float


class WatchlistInsight(BaseModel):
    """Watchlist ticker performance insight."""
    ticker: str
    company_name: str
    events_tracked: int
    high_impact_events: int
    avg_impact_score: float
    price_change_30d: float


class EventStats(BaseModel):
    """Event tracking statistics."""
    total_events_tracked: int
    high_impact_events: int
    portfolio_events: int
    watchlist_events: int


class DiagnosticsResponse(BaseModel):
    """Comprehensive account diagnostics."""
    portfolio_performance: PortfolioPerformance
    watchlist_performance: List[WatchlistInsight]
    event_stats: EventStats


class ModelHealthResponse(BaseModel):
    """Probabilistic impact scoring model health metrics."""
    total_groups: int
    avg_sample_size: float
    last_updated: Optional[datetime]
    coverage: dict


class ChangeEmailRequest(BaseModel):
    """Request to change user email."""
    new_email: str = Field(..., description="New email address")
    current_password: str = Field(..., description="Current password for verification")


class ChangePasswordRequest(BaseModel):
    """Request to change user password."""
    current_password: str = Field(..., description="Current password for verification")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")


class ChangePhoneRequest(BaseModel):
    """Request to change user phone number."""
    new_phone: str = Field(..., description="New phone number in E.164 format")
    
    @validator('new_phone')
    def validate_e164_format(cls, v):
        """Validate E.164 phone number format."""
        e164_pattern = r'^\+[1-9]\d{1,14}$'
        if not re.match(e164_pattern, v):
            raise ValueError('Phone number must be in E.164 format (e.g., +12025551234)')
        return v


class AccountUpdateResponse(BaseModel):
    """Response for account update operations."""
    success: bool
    message: str


@router.get("/summary", response_model=AccountSummary)
@limiter.limit(plan_limit)
async def get_account_summary(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get account summary information.
    
    Returns user account details, plan status, and usage statistics.
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        from api.utils.exceptions import ResourceNotFoundException
        raise ResourceNotFoundException("User", str(user_id))
    
    # Count watchlist items
    watchlist_count = db.query(func.count(WatchlistItem.id)).filter(
        WatchlistItem.user_id == user_id
    ).scalar() or 0
    
    # Count active alerts
    alerts_count = db.query(func.count(Alert.id)).filter(
        and_(Alert.user_id == user_id, Alert.active == True)
    ).scalar() or 0
    
    # Total events viewed (placeholder for now - could track this in future)
    events_viewed = 0
    
    return AccountSummary(
        user_id=user.id,
        email=user.email,
        plan=user.plan,
        username=getattr(user, 'username', None),
        avatar_url=getattr(user, 'avatar_url', None),
        trial_ends_at=user.trial_ends_at,
        account_created_at=user.created_at,
        last_login=user.last_login,
        total_watchlist_companies=watchlist_count,
        total_alerts_configured=alerts_count,
        total_events_viewed=events_viewed
    )


@router.get("/performance", response_model=PerformanceMetrics)
@limiter.limit(plan_limit)
async def get_account_performance(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get account performance metrics.
    
    Returns portfolio value, position counts, and event statistics.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"Getting account performance for user_id={user_id}")
    
    # Get portfolio value and position count
    portfolio = db.query(UserPortfolio).filter(
        UserPortfolio.user_id == user_id
    ).first()
    
    total_value = 0.0
    position_count = 0
    portfolio_tickers = []
    
    if portfolio:
        logger.info(f"Found portfolio id={portfolio.id} for user_id={user_id}")
        positions = db.query(PortfolioPosition).filter(
            PortfolioPosition.portfolio_id == portfolio.id
        ).all()
        
        position_count = len(positions)
        portfolio_tickers = [p.ticker for p in positions]
        logger.info(f"Found {position_count} positions for portfolio id={portfolio.id}")
        
        # Calculate total portfolio value (qty * avg_price as proxy for value)
        for position in positions:
            total_value += position.qty * (position.avg_price or 0)
    else:
        logger.warning(f"No portfolio found for user_id={user_id}")
    
    # Count events from current month
    now = datetime.utcnow()
    month_start = datetime(now.year, now.month, 1)
    
    events_this_month = db.query(func.count(Event.id)).filter(
        Event.date >= month_start
    ).scalar() or 0
    
    # Count events matching portfolio tickers
    events_matched = 0
    if portfolio_tickers:
        events_matched = db.query(func.count(Event.id)).filter(
            Event.ticker.in_(portfolio_tickers)
        ).scalar() or 0
    
    return PerformanceMetrics(
        total_portfolio_value=total_value,
        total_positions=position_count,
        events_this_month=events_this_month,
        events_matched_to_portfolio=events_matched
    )


@router.get("/activity", response_model=ActivityLog)
@limiter.limit(plan_limit)
async def get_account_activity(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get recent account activity.
    
    Returns recent alert triggers, portfolio uploads, and other activities.
    """
    activities: List[ActivityItem] = []
    
    # Get recent alert triggers (last 10)
    recent_alerts = db.query(AlertLog, Alert).join(
        Alert, AlertLog.alert_id == Alert.id
    ).filter(
        Alert.user_id == user_id
    ).order_by(
        AlertLog.sent_at.desc()
    ).limit(10).all()
    
    for alert_log, alert in recent_alerts:
        activities.append(ActivityItem(
            type="alert_triggered",
            description=f"Alert '{alert.name}' triggered",
            timestamp=alert_log.sent_at,
            details={
                "alert_name": alert.name,
                "event_id": alert_log.event_id,
                "channel": alert_log.channel,
                "status": alert_log.status
            }
        ))
    
    # Get recent portfolio uploads
    portfolio = db.query(UserPortfolio).filter(
        UserPortfolio.user_id == user_id
    ).first()
    
    if portfolio:
        # Calculate portfolio stats dynamically
        positions = db.query(PortfolioPosition).filter(
            PortfolioPosition.portfolio_id == portfolio.id
        ).all()
        
        total_positions = len(positions)
        total_value = sum(p.qty * (p.avg_price or 0) for p in positions)
        
        if total_positions > 0:
            activities.append(ActivityItem(
                type="portfolio_uploaded",
                description=f"Portfolio updated with {total_positions} positions",
                timestamp=portfolio.updated_at,
                details={
                    "total_positions": total_positions,
                    "total_value": float(total_value)
                }
            ))
    
    # Get recent watchlist additions (last 5)
    recent_watchlist = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user_id
    ).order_by(
        WatchlistItem.created_at.desc()
    ).limit(5).all()
    
    for item in recent_watchlist:
        activities.append(ActivityItem(
            type="watchlist_added",
            description=f"Added {item.ticker} to watchlist",
            timestamp=item.created_at,
            details={"ticker": item.ticker}
        ))
    
    # Sort all activities by timestamp (most recent first)
    activities.sort(key=lambda x: x.timestamp, reverse=True)
    
    # Return top 10 activities
    return ActivityLog(activities=activities[:10])


@router.get("/diagnostics", response_model=DiagnosticsResponse)
@limiter.limit(plan_limit)
async def get_account_diagnostics(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive account diagnostics.
    
    Returns portfolio performance with P&L, watchlist insights, and event statistics.
    """
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"[DIAGNOSTICS] Getting diagnostics for user_id={user_id}")
    
    # ===== PORTFOLIO PERFORMANCE =====
    portfolio = db.query(UserPortfolio).filter(
        UserPortfolio.user_id == user_id
    ).first()
    
    logger.info(f"[DIAGNOSTICS] Portfolio found: {portfolio is not None}, portfolio_id={portfolio.id if portfolio else None}")
    
    holdings: List[Holding] = []
    total_invested = 0.0
    current_value = 0.0
    total_profit_loss = 0.0
    portfolio_tickers: List[str] = []
    
    if portfolio:
        positions = db.query(PortfolioPosition).filter(
            PortfolioPosition.portfolio_id == portfolio.id
        ).all()
        
        logger.info(f"[DIAGNOSTICS] Found {len(positions)} positions for portfolio_id={portfolio.id}")
        
        # Get portfolio tickers for event counting
        portfolio_tickers = [p.ticker for p in positions]
        
        # Count events per ticker in a single query
        if portfolio_tickers:
            event_counts = db.query(
                Event.ticker,
                func.count(Event.id).label('count')
            ).filter(
                Event.ticker.in_(portfolio_tickers)
            ).group_by(Event.ticker).all()
            
            event_counts_dict = {ticker: count for ticker, count in event_counts}
        else:
            event_counts_dict = {}
        
        # Process each position - fetch real current prices with caching
        for position in positions:
            avg_cost = position.avg_price or 0
            quantity = position.qty
            invested = avg_cost * quantity
            
            # Fetch real current price from yfinance with caching
            current_price = fetch_current_price(position.ticker)
            if current_price is None:
                # Fallback to avg_price if price fetch fails
                current_price = avg_cost
                logger.warning(f"[DIAGNOSTICS] Could not fetch price for {position.ticker}, using avg_cost as fallback")
            
            # Calculate P&L with real current prices
            value = current_price * quantity
            profit_loss = value - invested
            profit_loss_percent = (profit_loss / invested * 100) if invested > 0 else 0
            
            # Get event count for this ticker
            events_count = event_counts_dict.get(position.ticker, 0)
            
            holdings.append(Holding(
                ticker=position.ticker,
                quantity=quantity,
                avg_cost=avg_cost,
                current_price=current_price,
                total_value=value,
                profit_loss=profit_loss,
                profit_loss_percent=profit_loss_percent,
                events_count=events_count
            ))
            
            total_invested += invested
            current_value += value
            total_profit_loss += profit_loss
    
    total_return_percent = (total_profit_loss / total_invested * 100) if total_invested > 0 else 0
    
    portfolio_performance = PortfolioPerformance(
        holdings=holdings,
        total_invested=total_invested,
        current_value=current_value,
        total_profit_loss=total_profit_loss,
        total_return_percent=total_return_percent
    )
    
    # ===== WATCHLIST PERFORMANCE =====
    watchlist_items = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user_id
    ).all()
    
    watchlist_performance: List[WatchlistInsight] = []
    watchlist_tickers = [item.ticker for item in watchlist_items]
    
    if watchlist_tickers:
        # Get company names in one query
        companies = db.query(Company).filter(
            Company.ticker.in_(watchlist_tickers)
        ).all()
        company_names = {c.ticker: c.name for c in companies}
        
        # Get event stats for watchlist tickers (high-impact = score >= 70)
        from sqlalchemy import case, literal
        event_stats = db.query(
            Event.ticker,
            func.count(Event.id).label('total_events'),
            func.sum(case((Event.impact_score >= 70, 1), else_=literal(0))).label('high_impact_events'),
            func.avg(Event.impact_score).label('avg_impact_score')
        ).filter(
            Event.ticker.in_(watchlist_tickers)
        ).group_by(Event.ticker).all()
        
        event_stats_dict = {
            ticker: {
                'total': total,
                'high_impact': high_impact or 0,
                'avg_score': float(avg_score) if avg_score else 0
            }
            for ticker, total, high_impact, avg_score in event_stats
        }
        
        # Build watchlist insights without slow price fetches
        for item in watchlist_items:
            ticker = item.ticker
            company_name = company_names.get(ticker, ticker)
            
            # Get event stats
            stats = event_stats_dict.get(ticker, {'total': 0, 'high_impact': 0, 'avg_score': 0})
            
            # Fetch 30-day price change with caching (15-min TTL)
            price_change_30d = fetch_30d_price_change(ticker)
            
            watchlist_performance.append(WatchlistInsight(
                ticker=ticker,
                company_name=company_name,
                events_tracked=stats['total'],
                high_impact_events=int(stats['high_impact']),
                avg_impact_score=stats['avg_score'],
                price_change_30d=price_change_30d
            ))
    
    # ===== EVENT STATS =====
    # Count total events
    total_events_tracked = db.query(func.count(Event.id)).scalar() or 0
    
    # Count high-impact events (score >= 70)
    high_impact_events = db.query(func.count(Event.id)).filter(
        Event.impact_score >= 70
    ).scalar() or 0
    
    # Count portfolio events
    portfolio_events = 0
    if portfolio_tickers:
        portfolio_events = db.query(func.count(Event.id)).filter(
            Event.ticker.in_(portfolio_tickers)
        ).scalar() or 0
    
    # Count watchlist events
    watchlist_events = 0
    if watchlist_tickers:
        watchlist_events = db.query(func.count(Event.id)).filter(
            Event.ticker.in_(watchlist_tickers)
        ).scalar() or 0
    
    event_stats = EventStats(
        total_events_tracked=total_events_tracked,
        high_impact_events=high_impact_events,
        portfolio_events=portfolio_events,
        watchlist_events=watchlist_events
    )
    
    logger.info(f"[DIAGNOSTICS] Returning diagnostics for user_id={user_id}: {len(holdings)} holdings, {len(watchlist_performance)} watchlist items")
    
    return DiagnosticsResponse(
        portfolio_performance=portfolio_performance,
        watchlist_performance=watchlist_performance,
        event_stats=event_stats
    )


@router.get("/model-health", response_model=ModelHealthResponse)
@limiter.limit(plan_limit)
async def get_model_health(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get probabilistic scoring model health metrics.
    
    Returns statistics about the trained event impact model including
    number of groups, sample sizes, and coverage.
    """
    # Get all event group priors
    priors = db.query(EventGroupPrior).all()
    
    # Calculate metrics
    total_groups = len(priors)
    avg_sample_size = sum(p.n for p in priors) / len(priors) if priors else 0
    last_updated = max(p.updated_at for p in priors) if priors else None
    
    # Calculate coverage
    event_types = len(set(p.event_type for p in priors))
    sectors = len(set(p.sector for p in priors))
    
    return ModelHealthResponse(
        total_groups=total_groups,
        avg_sample_size=avg_sample_size,
        last_updated=last_updated,
        coverage={
            "event_types": event_types,
            "sectors": sectors,
        }
    )


@router.post("/change-email", response_model=AccountUpdateResponse)
@limiter.limit(plan_limit)
async def change_email(
    request: Request,
    body: ChangeEmailRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Update user email with password verification.
    
    Requires current password for security verification before changing email.
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not bcrypt.checkpw(body.current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid current password")
    
    # Check if new email is already in use
    existing_user = db.query(User).filter(User.email == body.new_email).first()
    if existing_user and existing_user.id != user_id:
        raise HTTPException(status_code=400, detail="Email already in use")
    
    # Update email
    try:
        user.email = body.new_email
        db.commit()
        return AccountUpdateResponse(
            success=True,
            message="Email updated successfully"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update email: {str(e)}")


@router.post("/change-password", response_model=AccountUpdateResponse)
@limiter.limit(plan_limit)
async def change_password(
    request: Request,
    body: ChangePasswordRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Update user password with current password verification.
    
    Requires current password for security verification before changing password.
    New password must be at least 8 characters long.
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Verify current password
    if not bcrypt.checkpw(body.current_password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid current password")
    
    # Hash new password
    try:
        salt = bcrypt.gensalt()
        new_password_hash = bcrypt.hashpw(body.new_password.encode('utf-8'), salt).decode('utf-8')
        
        # Update password
        user.password_hash = new_password_hash
        db.commit()
        
        return AccountUpdateResponse(
            success=True,
            message="Password updated successfully"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update password: {str(e)}")


@router.post("/change-phone", response_model=AccountUpdateResponse)
@limiter.limit(plan_limit)
async def change_phone(
    request: Request,
    body: ChangePhoneRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Update user phone number with E.164 format validation.
    
    Phone number must be in E.164 format (e.g., +12025551234).
    Validation is performed automatically by the request model.
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if phone number is already in use
    existing_user = db.query(User).filter(User.phone == body.new_phone).first()
    if existing_user and existing_user.id != user_id:
        raise HTTPException(status_code=400, detail="Phone number already in use")
    
    # Update phone number
    try:
        user.phone = body.new_phone
        db.commit()
        return AccountUpdateResponse(
            success=True,
            message="Phone number updated successfully"
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update phone number: {str(e)}")


@router.post("/cancel-subscription", response_model=AccountUpdateResponse)
@limiter.limit(plan_limit)
async def cancel_subscription(
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Cancel user subscription.
    
    Sets user plan to 'free' (simplified implementation).
    In a production environment, this would also handle Stripe subscription cancellation.
    """
    # Get user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Check if user is already on free plan
    if user.plan == "free":
        return AccountUpdateResponse(
            success=True,
            message="User is already on the free plan"
        )
    
    # Cancel subscription by setting plan to free
    try:
        user.plan = "free"
        db.commit()
        return AccountUpdateResponse(
            success=True,
            message="Subscription cancelled successfully. Your plan has been downgraded to free."
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to cancel subscription: {str(e)}")
