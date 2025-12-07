"""
API endpoints for Event Pattern Detection.

Allows users to create, manage, and monitor multi-event correlation patterns.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, status, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from releaseradar.db.models import PatternDefinition, PatternAlert, User, WatchlistItem
from sqlalchemy import and_, or_
from releaseradar.services.pattern_detector import detect_patterns
from api.dependencies import get_db
from api.utils.auth import get_current_user_id
from api.utils.exceptions import ResourceNotFoundException, UpgradeRequiredException


router = APIRouter(prefix="/patterns", tags=["patterns"])


# ==================== REQUEST/RESPONSE MODELS ====================

class PatternConditions(BaseModel):
    """Pattern matching conditions."""
    event_types: List[str] = Field(..., min_items=1, description="Required event types")
    min_score: int = Field(default=0, ge=0, le=100, description="Minimum impact score")
    direction: Optional[str] = Field(default=None, description="Required direction: positive, negative, or null for any")
    min_events: Optional[int] = Field(default=None, ge=1, description="Minimum number of events required")
    
    @validator("direction")
    def validate_direction(cls, v):
        if v is not None and v not in ["positive", "negative", "neutral"]:
            raise ValueError("Direction must be 'positive', 'negative', or 'neutral'")
        return v


class PatternCreate(BaseModel):
    """Request model for creating a pattern definition."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None)
    conditions: PatternConditions
    time_window_days: int = Field(default=7, ge=1, le=90)
    min_correlation_score: float = Field(default=0.6, ge=0.0, le=1.0)
    alert_channels: Optional[List[str]] = Field(default=["in_app"])
    priority: str = Field(default="medium")
    active: bool = Field(default=True)
    
    @validator("alert_channels")
    def validate_channels(cls, v):
        if v:
            valid_channels = {"in_app", "email", "sms"}
            for channel in v:
                if channel not in valid_channels:
                    raise ValueError(f"Invalid channel: {channel}")
        return v
    
    @validator("priority")
    def validate_priority(cls, v):
        if v not in ["low", "medium", "high"]:
            raise ValueError("Priority must be 'low', 'medium', or 'high'")
        return v


class PatternUpdate(BaseModel):
    """Request model for updating a pattern definition."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = None
    conditions: Optional[PatternConditions] = None
    time_window_days: Optional[int] = Field(default=None, ge=1, le=90)
    min_correlation_score: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    alert_channels: Optional[List[str]] = None
    priority: Optional[str] = None
    active: Optional[bool] = None
    
    @validator("alert_channels")
    def validate_channels(cls, v):
        if v:
            valid_channels = {"in_app", "email", "sms"}
            for channel in v:
                if channel not in valid_channels:
                    raise ValueError(f"Invalid channel: {channel}")
        return v
    
    @validator("priority")
    def validate_priority(cls, v):
        if v is not None and v not in ["low", "medium", "high"]:
            raise ValueError("Priority must be 'low', 'medium', or 'high'")
        return v


class PatternResponse(BaseModel):
    """Response model for a pattern definition."""
    id: int
    name: str
    description: Optional[str]
    created_by: Optional[int]
    active: bool
    conditions: dict
    time_window_days: int
    min_correlation_score: float
    alert_channels: Optional[List[str]]
    priority: str
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class PatternAlertResponse(BaseModel):
    """Response model for a pattern alert."""
    id: int
    pattern_id: int
    pattern_name: Optional[str] = None  # Populated from join
    user_id: Optional[int]
    ticker: str
    company_name: str
    event_ids: List[int]
    correlation_score: float
    aggregated_impact_score: int
    aggregated_direction: str
    rationale: Optional[str]
    status: str
    detected_at: datetime
    acknowledged_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class DetectPatternsRequest(BaseModel):
    """Request model for manual pattern detection."""
    ticker: Optional[str] = Field(default=None, description="Optional ticker to limit detection")
    pattern_id: Optional[int] = Field(default=None, description="Optional specific pattern to check")


class DetectPatternsResponse(BaseModel):
    """Response model for pattern detection."""
    alerts_created: int
    message: str


# ==================== ENDPOINTS ====================

@router.post("", response_model=PatternResponse, status_code=status.HTTP_201_CREATED)
async def create_pattern(
    pattern_data: PatternCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Create a new pattern definition.
    
    Requires Pro or Team plan.
    """
    # Check user plan
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ResourceNotFoundException("User", str(user_id))
    
    if user.plan == "free":
        raise UpgradeRequiredException("Pattern Detection", "Pro")
    
    # Create pattern
    pattern = PatternDefinition(
        name=pattern_data.name,
        description=pattern_data.description,
        created_by=user_id,
        active=pattern_data.active,
        conditions=pattern_data.conditions.dict(),
        time_window_days=pattern_data.time_window_days,
        min_correlation_score=pattern_data.min_correlation_score,
        alert_channels=pattern_data.alert_channels,
        priority=pattern_data.priority
    )
    
    db.add(pattern)
    db.commit()
    db.refresh(pattern)
    
    return pattern


@router.get("", response_model=List[PatternResponse])
async def list_patterns(
    active_only: bool = False,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    List all pattern definitions for the authenticated user.
    
    Also includes system patterns (created_by=null).
    """
    # Query user patterns and system patterns
    query = db.query(PatternDefinition).filter(
        (PatternDefinition.created_by == user_id) |
        (PatternDefinition.created_by == None)
    )
    
    if active_only:
        query = query.filter(PatternDefinition.active == True)
    
    patterns = query.order_by(PatternDefinition.created_at.desc()).all()
    return patterns


@router.get("/{pattern_id}", response_model=PatternResponse)
async def get_pattern(
    pattern_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get a specific pattern definition by ID."""
    pattern = db.query(PatternDefinition).filter(
        PatternDefinition.id == pattern_id
    ).first()
    
    if not pattern:
        raise ResourceNotFoundException("Pattern", str(pattern_id))
    
    # Check access: user can access their own patterns or system patterns
    if pattern.created_by is not None and pattern.created_by != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this pattern"
        )
    
    return pattern


@router.put("/{pattern_id}", response_model=PatternResponse)
async def update_pattern(
    pattern_id: int,
    pattern_data: PatternUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update an existing pattern definition. Only the creator can update."""
    pattern = db.query(PatternDefinition).filter(
        PatternDefinition.id == pattern_id,
        PatternDefinition.created_by == user_id
    ).first()
    
    if not pattern:
        raise ResourceNotFoundException("Pattern", str(pattern_id))
    
    # Update only provided fields
    update_data = pattern_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        if field == "conditions" and value is not None:
            # Convert Pydantic model to dict
            setattr(pattern, field, value.dict())
        else:
            setattr(pattern, field, value)
    
    pattern.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(pattern)
    
    return pattern


@router.delete("/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_pattern(
    pattern_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete a pattern definition. Only the creator can delete."""
    pattern = db.query(PatternDefinition).filter(
        PatternDefinition.id == pattern_id,
        PatternDefinition.created_by == user_id
    ).first()
    
    if not pattern:
        raise ResourceNotFoundException("Pattern", str(pattern_id))
    
    db.delete(pattern)
    db.commit()


@router.get("/alerts", response_model=List[PatternAlertResponse])
async def get_pattern_alerts(
    ticker: Optional[str] = None,
    status_filter: Optional[str] = None,
    limit: int = Query(default=100, ge=1, le=500),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get triggered pattern alerts.
    
    Returns alerts owned by the user (from their patterns) and alerts from system patterns
    that apply to tickers in their watchlist.
    """
    # Get user's watchlist tickers
    watchlist_tickers = {
        item.ticker 
        for item in db.query(WatchlistItem).filter(WatchlistItem.user_id == user_id).all()
    }
    
    # Query alerts that belong to this user OR are system pattern alerts for watchlist tickers
    query = db.query(PatternAlert).join(
        PatternDefinition,
        PatternAlert.pattern_id == PatternDefinition.id
    ).filter(
        or_(
            # User's own pattern alerts
            PatternAlert.user_id == user_id,
            # System pattern alerts for tickers in user's watchlist
            and_(
                PatternDefinition.created_by == None,
                PatternAlert.ticker.in_(watchlist_tickers) if watchlist_tickers else False
            )
        )
    )
    
    if ticker:
        query = query.filter(PatternAlert.ticker == ticker)
    
    if status_filter:
        query = query.filter(PatternAlert.status == status_filter)
    
    alerts = query.order_by(
        PatternAlert.detected_at.desc()
    ).limit(limit).all()
    
    # Enrich with pattern name
    result = []
    for alert in alerts:
        alert_dict = {
            "id": alert.id,
            "pattern_id": alert.pattern_id,
            "pattern_name": alert.pattern.name if alert.pattern else None,
            "user_id": alert.user_id,
            "ticker": alert.ticker,
            "company_name": alert.company_name,
            "event_ids": alert.event_ids,
            "correlation_score": alert.correlation_score,
            "aggregated_impact_score": alert.aggregated_impact_score,
            "aggregated_direction": alert.aggregated_direction,
            "rationale": alert.rationale,
            "status": alert.status,
            "detected_at": alert.detected_at,
            "acknowledged_at": alert.acknowledged_at
        }
        result.append(PatternAlertResponse(**alert_dict))
    
    return result


@router.post("/alerts/{alert_id}/acknowledge", status_code=status.HTTP_200_OK)
async def acknowledge_pattern_alert(
    alert_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Acknowledge a pattern alert.
    
    User can only acknowledge alerts they own (from their patterns) or system pattern alerts
    for tickers in their watchlist.
    """
    # Get user's watchlist tickers
    watchlist_tickers = {
        item.ticker 
        for item in db.query(WatchlistItem).filter(WatchlistItem.user_id == user_id).all()
    }
    
    # Query the alert with ownership verification
    alert = db.query(PatternAlert).join(
        PatternDefinition,
        PatternAlert.pattern_id == PatternDefinition.id
    ).filter(
        PatternAlert.id == alert_id,
        or_(
            # User's own pattern alert
            PatternAlert.user_id == user_id,
            # System pattern alert for ticker in user's watchlist
            and_(
                PatternDefinition.created_by == None,
                PatternAlert.ticker.in_(watchlist_tickers) if watchlist_tickers else False
            )
        )
    ).first()
    
    if not alert:
        # Check if alert exists at all
        alert_exists = db.query(PatternAlert).filter(PatternAlert.id == alert_id).first()
        if alert_exists:
            # Alert exists but user doesn't have permission
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to acknowledge this alert"
            )
        else:
            # Alert doesn't exist
            raise ResourceNotFoundException("PatternAlert", str(alert_id))
    
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.utcnow()
    
    db.commit()
    db.refresh(alert)
    
    return {"message": "Pattern alert acknowledged", "alert_id": alert_id}


@router.post("/detect", response_model=DetectPatternsResponse)
async def trigger_pattern_detection(
    request: DetectPatternsRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Manually trigger pattern detection.
    
    Runs pattern detection in the background and returns immediately.
    Requires Pro or Team plan.
    """
    # Check user plan
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ResourceNotFoundException("User", str(user_id))
    
    if user.plan == "free":
        raise UpgradeRequiredException("Manual Pattern Detection", "Pro")
    
    # Run detection synchronously for immediate feedback
    alerts = detect_patterns(
        db=db,
        ticker=request.ticker,
        pattern_id=request.pattern_id,
        user_id=user_id
    )
    
    return DetectPatternsResponse(
        alerts_created=len(alerts),
        message=f"Pattern detection complete. {len(alerts)} alerts created."
    )
