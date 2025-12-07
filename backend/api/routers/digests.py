"""
API endpoints for email digest subscription management.

Allows users to configure and manage email digests with configurable
frequency, delivery time, and content filters.
"""

import os
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import requests
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.utils.auth import get_current_user_id, get_current_user_with_plan
from releaseradar.db.models import (
    DigestSubscription,
    User,
    Event,
    EventScore,
    UserPortfolio,
    PortfolioPosition,
    Alert,
    AlertLog,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/digests", tags=["digests"])


class DigestSubscriptionRequest(BaseModel):
    """Request model for creating or updating a digest subscription."""
    frequency: str = Field(default="daily", pattern="^(daily|weekly|none)$")
    delivery_time: str = Field(default="08:00", pattern="^[0-2][0-9]:[0-5][0-9]$")
    delivery_day: Optional[int] = Field(default=None, ge=0, le=6)
    include_sections: Optional[dict] = Field(default=None)
    tickers_filter: Optional[List[str]] = Field(default=None)
    min_score_threshold: int = Field(default=0, ge=0, le=100)
    active: bool = Field(default=True)


class DigestSubscriptionResponse(BaseModel):
    """Response model for a digest subscription."""
    id: int
    user_id: int
    frequency: str
    delivery_time: str
    delivery_day: Optional[int]
    include_sections: Optional[dict]
    tickers_filter: Optional[List[str]]
    min_score_threshold: int
    last_sent_at: Optional[datetime]
    next_send_at: Optional[datetime]
    active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DigestEventItem(BaseModel):
    """Event item for digest preview."""
    id: int
    ticker: str
    title: str
    event_type: str
    impact_score: int
    direction: Optional[str]
    date: datetime


class PortfolioSummaryItem(BaseModel):
    """Portfolio summary item for digest."""
    ticker: str
    qty: float
    upcoming_events_count: int
    avg_impact_score: Optional[float]


class DigestPreviewResponse(BaseModel):
    """Response model for digest preview."""
    top_events: List[DigestEventItem]
    portfolio_summary: Optional[List[PortfolioSummaryItem]]
    alert_matches: int
    generated_at: datetime


class SendNowResponse(BaseModel):
    """Response model for send-now endpoint."""
    success: bool
    message: str
    sent_to: Optional[str]


def calculate_next_send_at(frequency: str, delivery_time: str, delivery_day: Optional[int] = None) -> Optional[datetime]:
    """Calculate the next send time based on frequency and delivery settings."""
    if frequency == "none":
        return None
    
    now = datetime.utcnow()
    hour, minute = map(int, delivery_time.split(":"))
    
    if frequency == "daily":
        next_send = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if next_send <= now:
            next_send += timedelta(days=1)
        return next_send
    
    elif frequency == "weekly":
        if delivery_day is None:
            delivery_day = 0  # Default to Monday
        
        next_send = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        days_ahead = delivery_day - now.weekday()
        if days_ahead < 0 or (days_ahead == 0 and next_send <= now):
            days_ahead += 7
        next_send += timedelta(days=days_ahead)
        return next_send
    
    return None


async def get_resend_credentials():
    """Get Resend API credentials from the connector."""
    hostname = os.getenv("REPLIT_CONNECTORS_HOSTNAME")
    token = os.getenv("REPL_IDENTITY") or os.getenv("WEB_REPL_RENEWAL")
    
    if not hostname or not token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Email service not configured"
        )
    
    token_prefix = "repl" if os.getenv("REPL_IDENTITY") else "depl"
    
    try:
        response = requests.get(
            f"https://{hostname}/api/v2/connection?include_secrets=true&connector_names=resend",
            headers={"X_REPLIT_TOKEN": f"{token_prefix} {token}"},
            timeout=10
        )
        response.raise_for_status()
        
        items = response.json().get("items", [])
        if not items:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Resend integration not connected"
            )
        
        connection = items[0]
        api_key = connection.get("settings", {}).get("api_key")
        from_email = connection.get("settings", {}).get("from_email", "noreply@impactradar.io")
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Resend API key not configured"
            )
        
        return api_key, from_email
    
    except requests.RequestException as e:
        logger.error(f"Failed to get Resend credentials: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to connect to email service"
        )


def format_digest_html(
    events: List[Event],
    portfolio_summary: Optional[List[dict]] = None,
    alert_matches: int = 0
) -> str:
    """Format digest content as HTML email."""
    html = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }
        h1 { color: #1a1a2e; border-bottom: 2px solid #4a90d9; padding-bottom: 10px; }
        h2 { color: #4a90d9; margin-top: 30px; }
        .event { background: #f8f9fa; border-radius: 8px; padding: 15px; margin-bottom: 15px; border-left: 4px solid #4a90d9; }
        .event-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
        .ticker { font-weight: bold; color: #1a1a2e; font-size: 16px; }
        .score { background: #4a90d9; color: white; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
        .score.high { background: #28a745; }
        .score.low { background: #dc3545; }
        .title { color: #555; font-size: 14px; }
        .direction { font-size: 12px; color: #888; margin-top: 5px; }
        .direction.positive { color: #28a745; }
        .direction.negative { color: #dc3545; }
        .portfolio-item { padding: 10px 0; border-bottom: 1px solid #eee; }
        .summary { background: #e8f4fd; padding: 15px; border-radius: 8px; margin-top: 20px; }
        .footer { margin-top: 30px; padding-top: 20px; border-top: 1px solid #eee; color: #888; font-size: 12px; }
    </style>
</head>
<body>
    <h1>🎯 Impact Radar Daily Digest</h1>
"""
    
    if events:
        html += "<h2>📊 Top Events</h2>"
        for event in events[:10]:
            score = event.impact_score or 50
            score_class = "high" if score >= 70 else ("low" if score <= 30 else "")
            direction_class = "positive" if event.direction == "positive" else ("negative" if event.direction == "negative" else "")
            direction_text = f"↑ {event.direction}" if event.direction == "positive" else (f"↓ {event.direction}" if event.direction == "negative" else "→ neutral")
            
            html += f"""
    <div class="event">
        <div class="event-header">
            <span class="ticker">{event.ticker}</span>
            <span class="score {score_class}">Score: {score}</span>
        </div>
        <div class="title">{event.title}</div>
        <div class="direction {direction_class}">{direction_text} • {event.event_type}</div>
    </div>
"""
    else:
        html += "<p>No significant events in this period.</p>"
    
    if portfolio_summary:
        html += "<h2>📈 Portfolio Summary</h2>"
        for item in portfolio_summary:
            html += f"""
    <div class="portfolio-item">
        <strong>{item['ticker']}</strong> - {item['qty']} shares • 
        {item['upcoming_events_count']} upcoming events
    </div>
"""
    
    if alert_matches > 0:
        html += f"""
    <div class="summary">
        <strong>🔔 {alert_matches} alerts triggered</strong> since your last digest.
    </div>
"""
    
    html += f"""
    <div class="footer">
        <p>This digest was sent by Impact Radar. To update your preferences, visit your account settings.</p>
        <p>© {datetime.now().year} Impact Radar</p>
    </div>
</body>
</html>
"""
    return html


async def send_digest_email(to_email: str, subject: str, html_content: str) -> bool:
    """Send digest email via Resend."""
    try:
        api_key, from_email = await get_resend_credentials()
        
        import resend
        resend.api_key = api_key
        
        resend.Emails.send({
            "from": from_email,
            "to": to_email,
            "subject": subject,
            "html": html_content
        })
        
        logger.info(f"Digest email sent to {to_email}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send digest email to {to_email}: {e}")
        raise


@router.get("", response_model=Optional[DigestSubscriptionResponse])
async def get_digest_subscription(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get user's digest subscription settings.
    
    Returns the DigestSubscription object if exists, else null.
    """
    subscription = db.query(DigestSubscription).filter(
        DigestSubscription.user_id == user_id
    ).first()
    
    if not subscription:
        return None
    
    return subscription


@router.post("", response_model=DigestSubscriptionResponse, status_code=status.HTTP_200_OK)
async def create_or_update_digest_subscription(
    request: DigestSubscriptionRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Create or update digest subscription.
    
    Calculates next_send_at based on frequency and delivery settings.
    """
    next_send_at = calculate_next_send_at(
        request.frequency,
        request.delivery_time,
        request.delivery_day
    )
    
    subscription = db.query(DigestSubscription).filter(
        DigestSubscription.user_id == user_id
    ).first()
    
    if subscription:
        subscription.frequency = request.frequency
        subscription.delivery_time = request.delivery_time
        subscription.delivery_day = request.delivery_day
        subscription.include_sections = request.include_sections
        subscription.tickers_filter = request.tickers_filter
        subscription.min_score_threshold = request.min_score_threshold
        subscription.active = request.active
        subscription.next_send_at = next_send_at
    else:
        subscription = DigestSubscription(
            user_id=user_id,
            frequency=request.frequency,
            delivery_time=request.delivery_time,
            delivery_day=request.delivery_day,
            include_sections=request.include_sections,
            tickers_filter=request.tickers_filter,
            min_score_threshold=request.min_score_threshold,
            active=request.active,
            next_send_at=next_send_at
        )
        db.add(subscription)
    
    db.commit()
    db.refresh(subscription)
    
    return subscription


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def disable_digest_subscription(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Disable digest subscription.
    
    Sets active=false instead of deleting the subscription.
    """
    subscription = db.query(DigestSubscription).filter(
        DigestSubscription.user_id == user_id
    ).first()
    
    if not subscription:
        return None
    
    subscription.active = False
    subscription.next_send_at = None
    db.commit()
    
    return None


@router.post("/preview", response_model=DigestPreviewResponse)
async def preview_digest(
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Preview what would be in the next digest.
    
    Returns sample digest content including top events, portfolio summary,
    and alert matches.
    """
    user_id = user_data["user_id"]
    
    subscription = db.query(DigestSubscription).filter(
        DigestSubscription.user_id == user_id
    ).first()
    
    min_score = subscription.min_score_threshold if subscription else 0
    tickers_filter = subscription.tickers_filter if subscription else None
    
    lookback_days = 1 if (subscription and subscription.frequency == "daily") else 7
    since_date = datetime.utcnow() - timedelta(days=lookback_days)
    
    query = db.query(Event).filter(
        Event.date >= since_date,
        Event.impact_score >= min_score
    )
    
    if tickers_filter:
        query = query.filter(Event.ticker.in_(tickers_filter))
    
    events = query.order_by(desc(Event.impact_score)).limit(20).all()
    
    top_events = [
        DigestEventItem(
            id=e.id,
            ticker=e.ticker,
            title=e.title,
            event_type=e.event_type,
            impact_score=e.impact_score or 50,
            direction=e.direction,
            date=e.date
        )
        for e in events
    ]
    
    portfolio_summary = None
    portfolio = db.query(UserPortfolio).filter(
        UserPortfolio.user_id == user_id
    ).first()
    
    if portfolio:
        positions = db.query(PortfolioPosition).filter(
            PortfolioPosition.portfolio_id == portfolio.id
        ).all()
        
        summary_items = []
        for pos in positions:
            upcoming = db.query(Event).filter(
                Event.ticker == pos.ticker,
                Event.date >= datetime.utcnow()
            ).count()
            
            avg_score_result = db.query(Event.impact_score).filter(
                Event.ticker == pos.ticker,
                Event.date >= since_date
            ).all()
            avg_score = sum(s[0] or 50 for s in avg_score_result) / len(avg_score_result) if avg_score_result else None
            
            summary_items.append(PortfolioSummaryItem(
                ticker=pos.ticker,
                qty=pos.qty,
                upcoming_events_count=upcoming,
                avg_impact_score=avg_score
            ))
        
        if summary_items:
            portfolio_summary = summary_items
    
    alert_count = db.query(AlertLog).join(Alert).filter(
        Alert.user_id == user_id,
        AlertLog.sent_at >= since_date
    ).count()
    
    return DigestPreviewResponse(
        top_events=top_events,
        portfolio_summary=portfolio_summary,
        alert_matches=alert_count,
        generated_at=datetime.utcnow()
    )


@router.post("/send-now", response_model=SendNowResponse)
async def send_digest_now(
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Send a digest immediately (for testing).
    
    Triggers email send using Resend integration.
    """
    user_id = user_data["user_id"]
    user_email = user_data.get("email")
    
    if not user_email:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No email address associated with your account"
            )
        user_email = user.email
    
    subscription = db.query(DigestSubscription).filter(
        DigestSubscription.user_id == user_id
    ).first()
    
    min_score = subscription.min_score_threshold if subscription else 0
    tickers_filter = subscription.tickers_filter if subscription else None
    
    lookback_days = 1 if (subscription and subscription.frequency == "daily") else 7
    since_date = datetime.utcnow() - timedelta(days=lookback_days)
    
    query = db.query(Event).filter(
        Event.date >= since_date,
        Event.impact_score >= min_score
    )
    
    if tickers_filter:
        query = query.filter(Event.ticker.in_(tickers_filter))
    
    events = query.order_by(desc(Event.impact_score)).limit(10).all()
    
    portfolio_summary = None
    portfolio = db.query(UserPortfolio).filter(
        UserPortfolio.user_id == user_id
    ).first()
    
    if portfolio:
        positions = db.query(PortfolioPosition).filter(
            PortfolioPosition.portfolio_id == portfolio.id
        ).all()
        
        summary_items = []
        for pos in positions:
            upcoming = db.query(Event).filter(
                Event.ticker == pos.ticker,
                Event.date >= datetime.utcnow()
            ).count()
            
            summary_items.append({
                "ticker": pos.ticker,
                "qty": pos.qty,
                "upcoming_events_count": upcoming
            })
        
        if summary_items:
            portfolio_summary = summary_items
    
    alert_count = db.query(AlertLog).join(Alert).filter(
        Alert.user_id == user_id,
        AlertLog.sent_at >= since_date
    ).count()
    
    html_content = format_digest_html(events, portfolio_summary, alert_count)
    
    try:
        await send_digest_email(
            to_email=user_email,
            subject="🎯 Your Impact Radar Digest",
            html_content=html_content
        )
        
        if subscription:
            subscription.last_sent_at = datetime.utcnow()
            subscription.next_send_at = calculate_next_send_at(
                subscription.frequency,
                subscription.delivery_time,
                subscription.delivery_day
            )
            db.commit()
        
        return SendNowResponse(
            success=True,
            message="Digest sent successfully",
            sent_to=user_email
        )
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to send digest: {e}")
        return SendNowResponse(
            success=False,
            message=f"Failed to send digest: {str(e)}",
            sent_to=None
        )
