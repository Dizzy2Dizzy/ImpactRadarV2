"""
Historical Pattern Matching API Router

Endpoints for historical pattern analysis, similar event discovery, and outcome statistics.
"""

import math
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, desc
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.utils.auth import get_current_user_with_plan
from releaseradar.db.models import HistoricalPattern, Event, EventOutcome


router = APIRouter(prefix="/history", tags=["history"])


class HistoricalPatternResponse(BaseModel):
    """Response model for historical pattern."""
    id: int
    event_type: str
    ticker: Optional[str] = None
    sector: Optional[str] = None
    pattern_name: str
    pattern_description: Optional[str] = None
    sample_events: Optional[List[int]] = None
    avg_return_1d: Optional[float] = None
    avg_return_7d: Optional[float] = None
    avg_return_30d: Optional[float] = None
    win_rate: Optional[float] = None
    sample_size: int
    confidence_interval_low: Optional[float] = None
    confidence_interval_high: Optional[float] = None
    pattern_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PatternCreateRequest(BaseModel):
    """Request model for creating a historical pattern."""
    event_type: str = Field(..., min_length=1, description="Event type for this pattern")
    ticker: Optional[str] = Field(default=None, description="Optional ticker for ticker-specific patterns")
    sector: Optional[str] = Field(default=None, description="Optional sector for sector-specific patterns")
    pattern_name: str = Field(..., min_length=1, max_length=200, description="Name of the pattern")
    pattern_description: Optional[str] = Field(default=None, description="Description of the pattern")


class SimilarEventResponse(BaseModel):
    """Response model for similar historical events."""
    event_id: int
    ticker: str
    company_name: str
    event_type: str
    title: str
    sector: Optional[str] = None
    date: datetime
    impact_score: Optional[int] = None
    direction: Optional[str] = None
    return_1d: Optional[float] = None
    return_5d: Optional[float] = None
    return_20d: Optional[float] = None
    direction_correct_1d: Optional[bool] = None


class SimilarEventsAggregatedResponse(BaseModel):
    """Aggregated response for similar events with statistics."""
    similar_events: List[SimilarEventResponse]
    total_count: int
    win_rate: Optional[float] = None
    avg_return_1d: Optional[float] = None
    avg_return_7d: Optional[float] = None
    avg_return_30d: Optional[float] = None


class EventOutcomeStats(BaseModel):
    """Statistics for event outcomes."""
    sample_size: int
    avg_return_1d: Optional[float] = None
    avg_return_5d: Optional[float] = None
    avg_return_20d: Optional[float] = None
    win_rate_1d: Optional[float] = None
    win_rate_5d: Optional[float] = None
    win_rate_20d: Optional[float] = None
    std_return_1d: Optional[float] = None
    std_return_5d: Optional[float] = None
    std_return_20d: Optional[float] = None
    ci_low_1d: Optional[float] = None
    ci_high_1d: Optional[float] = None
    ci_low_5d: Optional[float] = None
    ci_high_5d: Optional[float] = None
    ci_low_20d: Optional[float] = None
    ci_high_20d: Optional[float] = None


class EventOutcomeStatsResponse(BaseModel):
    """Response model for event outcome statistics."""
    event_id: int
    event_type: str
    sector: Optional[str] = None
    ticker: str
    similar_events_count: int
    stats: EventOutcomeStats


@router.get(
    "/patterns",
    response_model=List[HistoricalPatternResponse],
    summary="List historical patterns",
    description="""
    List all historical patterns with optional filters.
    
    Filters available:
    - event_type: Filter by specific event type
    - sector: Filter by sector
    - min_sample_size: Only return patterns with at least this many samples
    """,
)
async def list_patterns(
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    min_sample_size: Optional[int] = Query(None, ge=1, description="Minimum sample size"),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of results"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """List all historical patterns with optional filters."""
    query = db.query(HistoricalPattern)
    
    if event_type:
        query = query.filter(HistoricalPattern.event_type == event_type)
    
    if sector:
        query = query.filter(HistoricalPattern.sector == sector)
    
    if min_sample_size:
        query = query.filter(HistoricalPattern.sample_size >= min_sample_size)
    
    patterns = query.order_by(desc(HistoricalPattern.sample_size)).limit(limit).all()
    return patterns


@router.get(
    "/patterns/{pattern_id}",
    response_model=HistoricalPatternResponse,
    summary="Get a specific pattern",
    description="Retrieve a specific historical pattern by ID with all details.",
)
async def get_pattern(
    pattern_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Get a specific historical pattern by ID."""
    pattern = db.query(HistoricalPattern).filter(HistoricalPattern.id == pattern_id).first()
    
    if not pattern:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pattern with ID {pattern_id} not found"
        )
    
    return pattern


@router.get(
    "/similar-events/{event_id}",
    response_model=SimilarEventsAggregatedResponse,
    summary="Find similar historical events",
    description="""
    Find historical events with similar characteristics (same event_type, sector) 
    and their outcomes. Includes aggregated statistics like win_rate and average returns.
    """,
)
async def get_similar_events(
    event_id: int,
    limit: int = Query(50, ge=1, le=200, description="Maximum number of similar events to return"),
    min_similarity: Optional[float] = Query(None, ge=0, le=1, description="Minimum similarity score (not used, reserved for future)"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Find similar historical events based on event_type and sector."""
    target_event = db.query(Event).filter(Event.id == event_id).first()
    
    if not target_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found"
        )
    
    similar_query = db.query(Event).filter(
        Event.id != event_id,
        Event.event_type == target_event.event_type,
    )
    
    if target_event.sector:
        similar_query = similar_query.filter(Event.sector == target_event.sector)
    
    similar_events = similar_query.order_by(desc(Event.date)).limit(limit).all()
    
    event_ids = [e.id for e in similar_events]
    outcomes = {}
    if event_ids:
        outcome_records = db.query(EventOutcome).filter(
            EventOutcome.event_id.in_(event_ids)
        ).all()
        
        for outcome in outcome_records:
            if outcome.event_id not in outcomes:
                outcomes[outcome.event_id] = {}
            outcomes[outcome.event_id][outcome.horizon] = outcome
    
    result_events = []
    returns_1d = []
    returns_5d = []
    returns_20d = []
    direction_correct_count = 0
    direction_total = 0
    
    for event in similar_events:
        event_outcomes = outcomes.get(event.id, {})
        outcome_1d = event_outcomes.get("1d")
        outcome_5d = event_outcomes.get("5d")
        outcome_20d = event_outcomes.get("20d")
        
        return_1d = outcome_1d.return_pct if outcome_1d else None
        return_5d = outcome_5d.return_pct if outcome_5d else None
        return_20d = outcome_20d.return_pct if outcome_20d else None
        direction_correct_1d = outcome_1d.direction_correct if outcome_1d else None
        
        if return_1d is not None:
            returns_1d.append(return_1d)
        if return_5d is not None:
            returns_5d.append(return_5d)
        if return_20d is not None:
            returns_20d.append(return_20d)
        if direction_correct_1d is not None:
            direction_total += 1
            if direction_correct_1d:
                direction_correct_count += 1
        
        result_events.append(SimilarEventResponse(
            event_id=event.id,
            ticker=event.ticker,
            company_name=event.company_name,
            event_type=event.event_type,
            title=event.title,
            sector=event.sector,
            date=event.date,
            impact_score=event.impact_score,
            direction=event.direction,
            return_1d=return_1d,
            return_5d=return_5d,
            return_20d=return_20d,
            direction_correct_1d=direction_correct_1d,
        ))
    
    win_rate = (direction_correct_count / direction_total * 100) if direction_total > 0 else None
    avg_return_1d = (sum(returns_1d) / len(returns_1d)) if returns_1d else None
    avg_return_7d = (sum(returns_5d) / len(returns_5d)) if returns_5d else None
    avg_return_30d = (sum(returns_20d) / len(returns_20d)) if returns_20d else None
    
    return SimilarEventsAggregatedResponse(
        similar_events=result_events,
        total_count=len(result_events),
        win_rate=win_rate,
        avg_return_1d=avg_return_1d,
        avg_return_7d=avg_return_7d,
        avg_return_30d=avg_return_30d,
    )


@router.post(
    "/patterns",
    response_model=HistoricalPatternResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new pattern definition",
    description="""
    Create a new historical pattern definition.
    
    The pattern will be initialized with sample_size=0 and can be populated
    by running pattern detection jobs.
    """,
)
async def create_pattern(
    pattern_data: PatternCreateRequest,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Create a new historical pattern definition."""
    existing = db.query(HistoricalPattern).filter(
        HistoricalPattern.event_type == pattern_data.event_type,
        HistoricalPattern.pattern_name == pattern_data.pattern_name,
        HistoricalPattern.ticker == pattern_data.ticker,
        HistoricalPattern.sector == pattern_data.sector,
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A pattern with the same event_type, pattern_name, ticker, and sector already exists"
        )
    
    new_pattern = HistoricalPattern(
        event_type=pattern_data.event_type,
        ticker=pattern_data.ticker,
        sector=pattern_data.sector,
        pattern_name=pattern_data.pattern_name,
        pattern_description=pattern_data.pattern_description,
        sample_size=0,
    )
    
    db.add(new_pattern)
    db.commit()
    db.refresh(new_pattern)
    
    return new_pattern


@router.get(
    "/event-outcomes/{event_id}",
    response_model=EventOutcomeStatsResponse,
    summary="Get historical outcomes for similar events",
    description="""
    Get aggregated statistics for events similar to the specified event.
    
    Returns average returns, win rates, and confidence intervals for multiple
    time horizons (1d, 5d, 20d).
    
    Confidence intervals are computed as: mean +/- 1.96 * std / sqrt(n)
    """,
)
async def get_event_outcomes(
    event_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Get historical outcome statistics for similar events."""
    target_event = db.query(Event).filter(Event.id == event_id).first()
    
    if not target_event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event with ID {event_id} not found"
        )
    
    similar_query = db.query(Event.id).filter(
        Event.event_type == target_event.event_type,
    )
    
    if target_event.sector:
        similar_query = similar_query.filter(Event.sector == target_event.sector)
    
    similar_event_ids = [row[0] for row in similar_query.all()]
    
    if not similar_event_ids:
        return EventOutcomeStatsResponse(
            event_id=event_id,
            event_type=target_event.event_type,
            sector=target_event.sector,
            ticker=target_event.ticker,
            similar_events_count=0,
            stats=EventOutcomeStats(sample_size=0),
        )
    
    outcomes = db.query(EventOutcome).filter(
        EventOutcome.event_id.in_(similar_event_ids)
    ).all()
    
    returns_by_horizon: Dict[str, List[float]] = {"1d": [], "5d": [], "20d": []}
    direction_correct_by_horizon: Dict[str, List[bool]] = {"1d": [], "5d": [], "20d": []}
    
    for outcome in outcomes:
        if outcome.horizon in returns_by_horizon:
            returns_by_horizon[outcome.horizon].append(outcome.return_pct)
            if outcome.direction_correct is not None:
                direction_correct_by_horizon[outcome.horizon].append(outcome.direction_correct)
    
    def compute_stats(returns: List[float]) -> tuple:
        """Compute mean, std, and confidence interval."""
        if not returns:
            return None, None, None, None
        
        n = len(returns)
        mean = sum(returns) / n
        
        if n > 1:
            variance = sum((x - mean) ** 2 for x in returns) / (n - 1)
            std = math.sqrt(variance)
            margin = 1.96 * std / math.sqrt(n)
            ci_low = mean - margin
            ci_high = mean + margin
        else:
            std = 0
            ci_low = mean
            ci_high = mean
        
        return mean, std, ci_low, ci_high
    
    def compute_win_rate(correct_list: List[bool]) -> Optional[float]:
        """Compute win rate from direction_correct list."""
        if not correct_list:
            return None
        return sum(1 for c in correct_list if c) / len(correct_list) * 100
    
    avg_1d, std_1d, ci_low_1d, ci_high_1d = compute_stats(returns_by_horizon["1d"])
    avg_5d, std_5d, ci_low_5d, ci_high_5d = compute_stats(returns_by_horizon["5d"])
    avg_20d, std_20d, ci_low_20d, ci_high_20d = compute_stats(returns_by_horizon["20d"])
    
    win_rate_1d = compute_win_rate(direction_correct_by_horizon["1d"])
    win_rate_5d = compute_win_rate(direction_correct_by_horizon["5d"])
    win_rate_20d = compute_win_rate(direction_correct_by_horizon["20d"])
    
    sample_size = max(
        len(returns_by_horizon["1d"]),
        len(returns_by_horizon["5d"]),
        len(returns_by_horizon["20d"]),
    )
    
    stats = EventOutcomeStats(
        sample_size=sample_size,
        avg_return_1d=avg_1d,
        avg_return_5d=avg_5d,
        avg_return_20d=avg_20d,
        win_rate_1d=win_rate_1d,
        win_rate_5d=win_rate_5d,
        win_rate_20d=win_rate_20d,
        std_return_1d=std_1d,
        std_return_5d=std_5d,
        std_return_20d=std_20d,
        ci_low_1d=ci_low_1d,
        ci_high_1d=ci_high_1d,
        ci_low_5d=ci_low_5d,
        ci_high_5d=ci_high_5d,
        ci_low_20d=ci_low_20d,
        ci_high_20d=ci_high_20d,
    )
    
    return EventOutcomeStatsResponse(
        event_id=event_id,
        event_type=target_event.event_type,
        sector=target_event.sector,
        ticker=target_event.ticker,
        similar_events_count=len(similar_event_ids),
        stats=stats,
    )
