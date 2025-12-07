"""
Alert dispatcher job - matches events against user alerts and sends notifications.

Triggered on:
- New event creation
- Event score write/upgrade

Features:
- Rule matching (score, tickers, sectors, event_types, keywords)
- Deduplication via (alert_id, event_id, channel) 
- Rate limiting (10 notifications per 5 min per user, 1 per event per alert)
- Multi-channel delivery (in-app, email, sms, webhook, slack, discord)
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from releaseradar.db.models import (
    Alert,
    AlertLog,
    Event,
    EventScore,
    User,
    UserNotification
)
from backend.database import SessionLocal, close_db_session
from alerts.email_service import get_email_service
from sms_service import get_sms_service, SMSService
from webhook_service import WebhookService
from api.utils.metrics import increment_metric, increment_counter

logger = logging.getLogger(__name__)


def dispatch_alerts_for_event(event_id: int, db: Optional[Session] = None) -> int:
    """
    Evaluate all active alerts against a specific event and send notifications.
    
    Args:
        event_id: ID of the event to evaluate
        db: Optional database session (creates one if not provided)
        
    Returns:
        int: Number of notifications sent
    """
    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True
    
    try:
        # Get event with score
        event = db.query(Event).filter(Event.id == event_id).first()
        if not event:
            logger.warning(f"Event {event_id} not found")
            return 0
        
        # Get score (if available)
        score = db.query(EventScore).filter(EventScore.event_id == event_id).first()
        final_score = score.final_score if score else event.impact_score
        confidence = score.confidence if score else int(event.confidence * 100)
        
        # Get all active alerts
        active_alerts = db.query(Alert).filter(Alert.active == True).all()
        
        notifications_sent = 0
        
        for alert in active_alerts:
            increment_metric("alerts_evaluated_total")
            
            # Check if alert matches event
            if not _matches_alert(event, final_score, alert):
                continue
            
            # Process each channel
            for channel in alert.channels:
                # Check deduplication
                dedupe_key = f"{alert.id}:{event_id}:{channel}"
                existing_log = db.query(AlertLog).filter(
                    AlertLog.dedupe_key == dedupe_key
                ).first()
                
                if existing_log:
                    increment_metric("alerts_deduped_total")
                    logger.debug(f"Alert {alert.id} already sent for event {event_id} on {channel}")
                    continue
                
                # Check rate limits
                if not _check_rate_limits(alert, event_id, db):
                    increment_metric("alerts_rate_limited_total")
                    continue
                
                # Send notification
                success = _send_notification(
                    alert=alert,
                    event=event,
                    score=final_score,
                    confidence=confidence,
                    channel=channel,
                    db=db
                )
                
                # Log the alert
                alert_log = AlertLog(
                    alert_id=alert.id,
                    event_id=event_id,
                    channel=channel,
                    dedupe_key=dedupe_key,
                    status="sent" if success else "failed",
                    error=None if success else "Delivery failed"
                )
                db.add(alert_log)
                
                if success:
                    increment_counter("alerts_sent_total", labels={"channel": channel})
                    notifications_sent += 1
        
        db.commit()
        return notifications_sent
        
    except Exception as e:
        logger.error(f"Error dispatching alerts for event {event_id}: {e}")
        if db:
            db.rollback()
        return 0
        
    finally:
        if should_close and db:
            close_db_session(db)


def _matches_alert(event: Event, score: int, alert: Alert) -> bool:
    """
    Check if an event matches an alert's criteria.
    
    Matching logic:
    - score >= min_score (required)
    - At least one of: tickers OR sectors OR event_types (if specified)
    - Keywords match in headline (if specified)
    """
    # Score threshold
    if score < alert.min_score:
        return False
    
    # Check filters (OR logic: tickers OR sectors OR event_types)
    filters_specified = (
        (alert.tickers and len(alert.tickers) > 0) or
        (alert.sectors and len(alert.sectors) > 0) or
        (alert.event_types and len(alert.event_types) > 0)
    )
    
    if filters_specified:
        ticker_match = alert.tickers and event.ticker in alert.tickers
        sector_match = alert.sectors and event.sector in alert.sectors
        event_type_match = alert.event_types and event.event_type in alert.event_types
        
        if not (ticker_match or sector_match or event_type_match):
            return False
    
    # Keyword matching (case-insensitive, all keywords must match)
    if alert.keywords and len(alert.keywords) > 0:
        headline_lower = event.title.lower()
        for keyword in alert.keywords:
            if keyword.lower() not in headline_lower:
                return False
    
    return True


def _check_rate_limits(alert: Alert, event_id: int, db: Session) -> bool:
    """
    Check rate limits for alert delivery.
    
    Limits:
    - Max 10 notifications per user per 5 minutes
    - Max 1 notification per alert per event (across all channels)
    """
    # Check: 1 per alert per event
    existing_for_event = db.query(AlertLog).filter(
        AlertLog.alert_id == alert.id,
        AlertLog.event_id == event_id
    ).first()
    
    if existing_for_event:
        return False
    
    # Check: 10 per user per 5 minutes
    five_min_ago = datetime.utcnow() - timedelta(minutes=5)
    
    # Get all alerts for this user
    user_alert_ids = db.query(Alert.id).filter(Alert.user_id == alert.user_id).all()
    user_alert_ids = [a[0] for a in user_alert_ids]
    
    recent_count = db.query(AlertLog).filter(
        AlertLog.alert_id.in_(user_alert_ids),
        AlertLog.sent_at >= five_min_ago
    ).count()
    
    if recent_count >= 10:
        logger.warning(
            f"Rate limit exceeded for user {alert.user_id}: "
            f"{recent_count} notifications in last 5 minutes"
        )
        return False
    
    return True


def _send_notification(
    alert: Alert,
    event: Event,
    score: int,
    confidence: int,
    channel: str,
    db: Session
) -> bool:
    """
    Send a notification via the specified channel.
    
    Args:
        alert: Alert that matched
        event: Event that triggered the alert
        score: Final impact score
        confidence: Confidence percentage
        channel: Delivery channel ('in_app', 'email', 'sms', 'webhook', 'slack', 'discord')
        db: Database session
        
    Returns:
        bool: True if notification sent successfully
    """
    try:
        if channel == "in_app":
            return _send_in_app_notification(alert, event, score, confidence, db)
        elif channel == "email":
            return _send_email_notification(alert, event, score, confidence, db)
        elif channel == "sms":
            return _send_sms_notification(alert, event, score, confidence, db)
        elif channel == "webhook":
            return _send_webhook_notification(alert, event, score, confidence, db)
        elif channel == "slack":
            return _send_slack_notification(alert, event, score, confidence, db)
        elif channel == "discord":
            return _send_discord_notification(alert, event, score, confidence, db)
        else:
            logger.error(f"Unknown channel: {channel}")
            return False
    except Exception as e:
        logger.error(f"Failed to send notification via {channel}: {e}")
        return False


def _send_in_app_notification(
    alert: Alert,
    event: Event,
    score: int,
    confidence: int,
    db: Session
) -> bool:
    """Send an in-app notification."""
    notification = UserNotification(
        user_id=alert.user_id,
        title=f"{event.ticker}: {event.event_type}",
        body=f"{event.title} (Score: {score}, Confidence: {confidence}%)",
        url=event.source_url
    )
    
    db.add(notification)
    db.flush()  # Flush to get the ID but don't commit yet
    
    logger.info(
        f"In-app notification created for user {alert.user_id}, "
        f"event {event.id}, alert '{alert.name}'"
    )
    return True


def _send_email_notification(
    alert: Alert,
    event: Event,
    score: int,
    confidence: int,
    db: Session
) -> bool:
    """Send an email notification."""
    # Get user email
    user = db.query(User).filter(User.id == alert.user_id).first()
    if not user or not user.email:
        logger.warning(f"User {alert.user_id} has no email address")
        return False
    
    # Send email
    email_service = get_email_service()
    success = email_service.send_alert_email(
        to_email=user.email,
        event_headline=event.title,
        score=score,
        confidence=confidence,
        source_url=event.source_url,
        ticker=event.ticker,
        event_type=event.event_type
    )
    
    if success:
        logger.info(
            f"Email notification sent to {user.email} for "
            f"event {event.id}, alert '{alert.name}'"
        )
    
    return success


def _send_sms_notification(
    alert: Alert,
    event: Event,
    score: int,
    confidence: int,
    db: Session
) -> bool:
    """Send an SMS notification with rate limiting."""
    # Get user phone
    user = db.query(User).filter(User.id == alert.user_id).first()
    if not user or not user.phone:
        logger.warning(f"User {alert.user_id} has no phone number")
        return False
    
    # Check SMS rate limit (max 10 per user per day)
    sms_service = get_sms_service()
    can_send, remaining = SMSService.check_sms_rate_limit(alert.user_id, db, limit=10)
    
    if not can_send:
        logger.warning(
            f"SMS rate limit exceeded for user {alert.user_id}. "
            f"Cannot send alert for event {event.id}"
        )
        increment_metric("alerts_sms_rate_limited_total")
        return False
    
    # Send SMS
    result = sms_service.send_alert_sms(
        to_phone=user.phone,
        ticker=event.ticker,
        event_type=event.event_type,
        headline=event.title,
        score=score,
        confidence=confidence
    )
    
    if result.get("success"):
        logger.info(
            f"SMS notification sent to {user.phone} for "
            f"event {event.id}, alert '{alert.name}'. "
            f"Remaining SMS quota: {remaining - 1}"
        )
        return True
    else:
        error = result.get("error", "Unknown error")
        logger.error(
            f"Failed to send SMS to {user.phone} for event {event.id}: {error}"
        )
        return False


def _build_event_data(event: Event, score: int, confidence: int) -> dict:
    """Build event data dictionary for webhook payloads."""
    return {
        "id": event.id,
        "ticker": event.ticker,
        "company_name": getattr(event, 'company_name', event.ticker),
        "title": event.title,
        "event_type": event.event_type,
        "impact_score": score,
        "direction": event.direction,
        "confidence": confidence / 100.0,
        "date": event.date.isoformat() if event.date else None,
        "source_url": event.source_url,
        "sector": event.sector
    }


def _run_async_safely(coro):
    """Run an async coroutine safely from sync context."""
    try:
        loop = asyncio.get_running_loop()
        # We're in an async context, use nest_asyncio-style approach
        # Create a new thread to run the coroutine
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result(timeout=15)
    except RuntimeError:
        # No running event loop, safe to use asyncio.run
        return asyncio.run(coro)


def _send_webhook_notification(
    alert: Alert,
    event: Event,
    score: int,
    confidence: int,
    db: Session
) -> bool:
    """Send a custom webhook notification (Team plan only)."""
    if not alert.webhook_url:
        logger.warning(f"Alert {alert.id} has webhook channel but no webhook URL")
        return False
    
    event_data = _build_event_data(event, score, confidence)
    
    try:
        result = _run_async_safely(
            WebhookService.send_custom_webhook(
                webhook_url=alert.webhook_url,
                event_data=event_data,
                alert_name=alert.name
            )
        )
        
        if result.get("success"):
            logger.info(
                f"Custom webhook sent for alert '{alert.name}', "
                f"event {event.id}"
            )
            return True
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"Custom webhook failed for alert {alert.id}: {error}")
            return False
    except Exception as e:
        logger.error(f"Custom webhook exception for alert {alert.id}: {e}")
        return False


def _send_slack_notification(
    alert: Alert,
    event: Event,
    score: int,
    confidence: int,
    db: Session
) -> bool:
    """Send a Slack webhook notification (Team plan only)."""
    if not alert.slack_webhook_url:
        logger.warning(f"Alert {alert.id} has slack channel but no Slack webhook URL")
        return False
    
    event_data = _build_event_data(event, score, confidence)
    
    try:
        result = _run_async_safely(
            WebhookService.send_slack_notification(
                webhook_url=alert.slack_webhook_url,
                event_data=event_data,
                alert_name=alert.name
            )
        )
        
        if result.get("success"):
            logger.info(
                f"Slack notification sent for alert '{alert.name}', "
                f"event {event.id}"
            )
            return True
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"Slack notification failed for alert {alert.id}: {error}")
            return False
    except Exception as e:
        logger.error(f"Slack notification exception for alert {alert.id}: {e}")
        return False


def _send_discord_notification(
    alert: Alert,
    event: Event,
    score: int,
    confidence: int,
    db: Session
) -> bool:
    """Send a Discord webhook notification (Team plan only)."""
    if not alert.discord_webhook_url:
        logger.warning(f"Alert {alert.id} has discord channel but no Discord webhook URL")
        return False
    
    event_data = _build_event_data(event, score, confidence)
    
    try:
        result = _run_async_safely(
            WebhookService.send_discord_notification(
                webhook_url=alert.discord_webhook_url,
                event_data=event_data,
                alert_name=alert.name
            )
        )
        
        if result.get("success"):
            logger.info(
                f"Discord notification sent for alert '{alert.name}', "
                f"event {event.id}"
            )
            return True
        else:
            error = result.get("error", "Unknown error")
            logger.error(f"Discord notification failed for alert {alert.id}: {error}")
            return False
    except Exception as e:
        logger.error(f"Discord notification exception for alert {alert.id}: {e}")
        return False


if __name__ == "__main__":
    """Test dispatcher with a specific event ID."""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m alerts.dispatch <event_id>")
        sys.exit(1)
    
    event_id = int(sys.argv[1])
    count = dispatch_alerts_for_event(event_id)
    print(f"Sent {count} notifications for event {event_id}")
