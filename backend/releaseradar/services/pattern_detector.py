"""
Pattern Detection Engine for Impact Radar.

Detects multi-event correlation patterns (e.g., FDA approval + insider buying)
and generates pattern alerts when conditions are met.
"""

from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session
from loguru import logger

from releaseradar.db.models import (
    PatternDefinition,
    PatternAlert,
    Event,
    User,
    WatchlistItem,
)


def detect_patterns(
    db: Session,
    ticker: Optional[str] = None,
    pattern_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> List[PatternAlert]:
    """
    Detect pattern matches and create pattern alerts.
    
    Args:
        db: Database session
        ticker: Optional ticker to limit detection (default: all tickers)
        pattern_id: Optional specific pattern to check (default: all active patterns)
        user_id: Optional user ID to scope detection to user's patterns + system patterns
    
    Returns:
        List of created PatternAlert objects
    """
    # Query active pattern definitions
    # Only include patterns owned by user OR system patterns (created_by=NULL)
    query = db.query(PatternDefinition).filter(PatternDefinition.active == True)
    
    if user_id is not None:
        query = query.filter(
            or_(
                PatternDefinition.created_by == user_id,
                PatternDefinition.created_by == None
            )
        )
    
    if pattern_id:
        query = query.filter(PatternDefinition.id == pattern_id)
    
    patterns = query.all()
    
    if not patterns:
        logger.info("No active patterns found")
        return []
    
    # Get user's watchlist tickers if user_id is provided
    watchlist_tickers = set()
    if user_id is not None:
        watchlist_tickers = _get_user_watchlist_tickers(db, user_id)
    
    alerts_created = []
    
    for pattern in patterns:
        logger.info(f"Checking pattern: {pattern.name} (id={pattern.id})")
        
        # Get tickers to check
        if ticker:
            tickers_to_check = [ticker]
        else:
            # For system patterns with user context, only check watchlist tickers
            if pattern.created_by is None and user_id is not None:
                tickers_to_check = list(watchlist_tickers)
            else:
                tickers_to_check = _get_all_tickers(db)
        
        for check_ticker in tickers_to_check:
            # Skip if this is a system pattern and ticker not in user's watchlist
            if pattern.created_by is None and user_id is not None:
                if check_ticker not in watchlist_tickers:
                    logger.debug(
                        f"Skipping {check_ticker} for system pattern {pattern.name} - "
                        f"not in user's watchlist"
                    )
                    continue
            
            # Determine target user_id for this alert
            # - User patterns: always use pattern.created_by
            # - System patterns in user context: use provided user_id
            # - System patterns in background job: use None
            if pattern.created_by is not None:
                # User-owned pattern
                target_user_id = pattern.created_by
            else:
                # System pattern
                target_user_id = user_id  # None for background jobs, user_id for user context
            
            # SCOPED DEDUPLICATION: Check if alert exists for same pattern + ticker + user + today
            # This allows both system alerts (user_id=NULL) and user alerts (user_id=305) to coexist
            today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
            existing_alert = db.query(PatternAlert).filter(
                and_(
                    PatternAlert.pattern_id == pattern.id,
                    PatternAlert.ticker == check_ticker,
                    PatternAlert.user_id == target_user_id,  # Include user_id in duplicate check
                    PatternAlert.detected_at >= today_start
                )
            ).first()
            
            if existing_alert:
                logger.debug(
                    f"Pattern {pattern.name} already detected for {check_ticker} today "
                    f"(user_id={target_user_id}), skipping"
                )
                continue
            
            # Find matching events
            matching_events = _find_matching_events(db, pattern, check_ticker)
            
            if matching_events:
                # Calculate correlation score
                correlation_score = calculate_correlation_score(matching_events, pattern)
                
                # Check if correlation meets minimum threshold
                if correlation_score >= pattern.min_correlation_score:
                    # Create pattern alert
                    alert = _create_pattern_alert(
                        db, pattern, check_ticker, matching_events, correlation_score, target_user_id
                    )
                    alerts_created.append(alert)
                    logger.info(
                        f"Created pattern alert: {pattern.name} for {check_ticker} "
                        f"(user_id={target_user_id}, correlation={correlation_score:.2f})"
                    )
    
    return alerts_created


def _get_all_tickers(db: Session) -> List[str]:
    """Get all unique tickers from recent events."""
    # Get tickers from events in the last 30 days
    cutoff = datetime.utcnow() - timedelta(days=30)
    tickers = db.query(Event.ticker).filter(
        Event.date >= cutoff
    ).distinct().all()
    
    return [t[0] for t in tickers]


def _get_user_watchlist_tickers(db: Session, user_id: int) -> set:
    """Get all tickers in user's watchlist."""
    watchlist_items = db.query(WatchlistItem).filter(
        WatchlistItem.user_id == user_id
    ).all()
    
    return {item.ticker for item in watchlist_items}


def _find_matching_events(
    db: Session,
    pattern: PatternDefinition,
    ticker: str
) -> List[Event]:
    """
    Find events matching pattern conditions for a specific ticker.
    
    Args:
        db: Database session
        pattern: PatternDefinition to match
        ticker: Ticker symbol to check
    
    Returns:
        List of matching Event objects
    """
    # Get time window
    cutoff = datetime.utcnow() - timedelta(days=pattern.time_window_days)
    
    # Extract pattern conditions
    conditions = pattern.conditions or {}
    required_event_types = conditions.get("event_types", [])
    min_score = conditions.get("min_score", 0)
    required_direction = conditions.get("direction")  # Optional: "positive", "negative"
    min_events = conditions.get("min_events", len(required_event_types))
    
    # Query events for this ticker within time window
    query = db.query(Event).filter(
        and_(
            Event.ticker == ticker,
            Event.date >= cutoff
        )
    )
    
    # Filter by event types if specified
    if required_event_types:
        query = query.filter(Event.event_type.in_(required_event_types))
    
    # Filter by minimum score
    if min_score > 0:
        query = query.filter(Event.impact_score >= min_score)
    
    # Filter by direction if specified
    if required_direction:
        query = query.filter(Event.direction == required_direction)
    
    # Order by date (most recent first)
    query = query.order_by(Event.date.desc())
    
    events = query.all()
    
    # Check if we have enough events
    if len(events) < min_events:
        return []
    
    # Check if we have at least one of each required event type
    if required_event_types:
        event_types_found = set(e.event_type for e in events)
        required_set = set(required_event_types)
        
        if not required_set.issubset(event_types_found):
            return []
    
    return events


def calculate_correlation_score(
    events: List[Event],
    pattern: PatternDefinition
) -> float:
    """
    Calculate correlation score based on time proximity, directional alignment, and magnitude.
    
    Args:
        events: List of matching events
        pattern: PatternDefinition being evaluated
    
    Returns:
        Correlation score between 0.0 and 1.0
    """
    if not events:
        return 0.0
    
    # Sort events by date
    sorted_events = sorted(events, key=lambda e: e.date)
    
    # Component scores
    time_score = _calculate_time_proximity_score(sorted_events, pattern.time_window_days)
    direction_score = _calculate_directional_alignment_score(events)
    magnitude_score = _calculate_magnitude_score(events)
    
    # Weighted average (time proximity is most important)
    correlation_score = (
        0.5 * time_score +
        0.3 * direction_score +
        0.2 * magnitude_score
    )
    
    return min(1.0, max(0.0, correlation_score))


def _calculate_time_proximity_score(events: List[Event], time_window_days: int) -> float:
    """
    Score based on how close together events occurred.
    Events closer together get higher scores.
    """
    if len(events) < 2:
        return 1.0
    
    # Calculate time span between first and last event
    time_span = (events[-1].date - events[0].date).total_seconds() / 86400  # days
    
    # Normalize to time window (closer = better)
    # If all events happen on same day: 1.0
    # If events span full window: 0.5
    # If events exceed window (shouldn't happen): 0.0
    proximity_score = 1.0 - (time_span / (time_window_days * 2))
    
    return max(0.0, min(1.0, proximity_score))


def _calculate_directional_alignment_score(events: List[Event]) -> float:
    """
    Score based on directional consistency.
    All events pointing same direction = 1.0
    Mixed directions = lower score
    """
    if not events:
        return 0.0
    
    # Count directions
    directions = [e.direction for e in events if e.direction]
    
    if not directions:
        return 0.5  # No direction info = neutral
    
    # Count each direction
    positive_count = sum(1 for d in directions if d == "positive")
    negative_count = sum(1 for d in directions if d == "negative")
    neutral_count = sum(1 for d in directions if d == "neutral")
    
    total = len(directions)
    
    # Alignment score = proportion of majority direction
    max_count = max(positive_count, negative_count, neutral_count)
    alignment_score = max_count / total
    
    return alignment_score


def _calculate_magnitude_score(events: List[Event]) -> float:
    """
    Score based on average impact magnitude.
    Higher impact scores = higher correlation score.
    """
    if not events:
        return 0.0
    
    # Calculate weighted average of impact scores
    total_score = 0.0
    total_weight = 0.0
    
    for event in events:
        # Weight by confidence
        weight = event.confidence if event.confidence else 0.5
        total_score += event.impact_score * weight
        total_weight += weight
    
    if total_weight == 0:
        return 0.0
    
    avg_score = total_score / total_weight
    
    # Normalize to 0-1 (assuming impact_score is 0-100)
    return min(1.0, avg_score / 100.0)


def aggregate_impact(events: List[Event]) -> Dict[str, Any]:
    """
    Combine individual event scores into aggregated impact metrics.
    
    Args:
        events: List of events to aggregate
    
    Returns:
        Dictionary with:
        - aggregated_impact_score: Weighted average impact score (0-100)
        - aggregated_direction: Majority vote direction
        - rationale: Explanation of the aggregated impact
    """
    if not events:
        return {
            "aggregated_impact_score": 50,
            "aggregated_direction": "neutral",
            "rationale": "No events to aggregate"
        }
    
    # Calculate weighted average impact score (weight by confidence and recency)
    now = datetime.utcnow()
    total_score = 0.0
    total_weight = 0.0
    
    for event in events:
        # Recency weight: events from last 24h = 1.0, older events decay
        days_ago = (now - event.date).total_seconds() / 86400
        recency_weight = max(0.3, 1.0 - (days_ago / 30.0))  # Min weight 0.3
        
        # Confidence weight
        confidence_weight = event.confidence if event.confidence else 0.5
        
        # Combined weight
        weight = recency_weight * confidence_weight
        
        total_score += event.impact_score * weight
        total_weight += weight
    
    aggregated_score = int(total_score / total_weight) if total_weight > 0 else 50
    
    # Determine majority direction
    directions = [e.direction for e in events if e.direction]
    positive_count = sum(1 for d in directions if d == "positive")
    negative_count = sum(1 for d in directions if d == "negative")
    
    if positive_count > negative_count:
        aggregated_direction = "positive"
    elif negative_count > positive_count:
        aggregated_direction = "negative"
    else:
        aggregated_direction = "neutral"
    
    # Generate rationale
    event_types = [e.event_type for e in events]
    event_summaries = [f"{e.event_type} (score: {e.impact_score})" for e in events]
    
    rationale = (
        f"Pattern detected with {len(events)} events: {', '.join(event_types)}. "
        f"Aggregated impact score: {aggregated_score}/100. "
        f"Overall direction: {aggregated_direction}. "
        f"Events: {'; '.join(event_summaries)}."
    )
    
    return {
        "aggregated_impact_score": aggregated_score,
        "aggregated_direction": aggregated_direction,
        "rationale": rationale
    }


def _create_pattern_alert(
    db: Session,
    pattern: PatternDefinition,
    ticker: str,
    events: List[Event],
    correlation_score: float,
    target_user_id: Optional[int]
) -> PatternAlert:
    """
    Create a PatternAlert record for detected pattern.
    
    Args:
        db: Database session
        pattern: PatternDefinition that matched
        ticker: Ticker symbol
        events: Matching events
        correlation_score: Calculated correlation score
        target_user_id: User ID for the alert (None for system alerts in background jobs,
                        user_id for user-specific alerts, pattern.created_by for user patterns)
    
    Returns:
        Created PatternAlert object
    """
    # Get company name from first event
    company_name = events[0].company_name if events else ticker
    
    # Aggregate impact
    impact_data = aggregate_impact(events)
    
    # Create alert with scoped user_id
    alert = PatternAlert(
        pattern_id=pattern.id,
        user_id=target_user_id,  # Scoped: user-specific or system (NULL)
        ticker=ticker,
        company_name=company_name,
        event_ids=[e.id for e in events],
        correlation_score=correlation_score,
        aggregated_impact_score=impact_data["aggregated_impact_score"],
        aggregated_direction=impact_data["aggregated_direction"],
        rationale=impact_data["rationale"],
        status="active",
        detected_at=datetime.utcnow()
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    return alert
