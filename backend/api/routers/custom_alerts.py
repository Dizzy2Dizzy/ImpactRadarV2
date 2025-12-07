"""
Custom Alert Rules API endpoints.

Allows users to create, read, update, and delete custom alert rules with
user-defined thresholds for confidence, impact, directions, and filtering criteria.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_

from releaseradar.db.models import CustomAlertRule, Event, User
from api.dependencies import get_db
from api.utils.auth import get_current_user_id
from api.utils.exceptions import ResourceNotFoundException, UpgradeRequiredException


router = APIRouter(prefix="/custom-alerts", tags=["custom-alerts"])


class AlertConditions(BaseModel):
    """Conditions for triggering a custom alert rule."""
    min_confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    min_impact: Optional[int] = Field(default=None, ge=0, le=100)
    directions: Optional[List[str]] = Field(default=None)
    
    @validator("directions")
    def validate_directions(cls, v):
        """Validate that directions are valid values."""
        if v is not None:
            valid_directions = {"positive", "negative", "neutral"}
            for direction in v:
                if direction.lower() not in valid_directions:
                    raise ValueError(f"Invalid direction: {direction}. Must be one of {valid_directions}")
            return [d.lower() for d in v]
        return v


class CustomAlertRuleCreate(BaseModel):
    """Request model for creating a custom alert rule."""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    conditions: AlertConditions = Field(default_factory=AlertConditions)
    tickers: Optional[List[str]] = Field(default=None)
    sectors: Optional[List[str]] = Field(default=None)
    event_types: Optional[List[str]] = Field(default=None)
    notification_channels: List[str] = Field(default=["in_app"])
    cooldown_minutes: int = Field(default=60, ge=1, le=1440)
    active: bool = Field(default=True)
    
    @validator("notification_channels")
    def validate_channels(cls, v):
        """Validate that notification channels are valid."""
        valid_channels = {"in_app", "email", "sms"}
        for channel in v:
            if channel not in valid_channels:
                raise ValueError(f"Invalid channel: {channel}. Must be one of {valid_channels}")
        return v
    
    @validator("tickers", "sectors", "event_types")
    def validate_arrays(cls, v):
        """Ensure arrays are not empty if provided."""
        if v is not None and len(v) == 0:
            return None
        return v


class CustomAlertRuleUpdate(BaseModel):
    """Request model for updating a custom alert rule."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    conditions: Optional[AlertConditions] = None
    tickers: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    event_types: Optional[List[str]] = None
    notification_channels: Optional[List[str]] = None
    cooldown_minutes: Optional[int] = Field(default=None, ge=1, le=1440)
    active: Optional[bool] = None
    
    @validator("notification_channels")
    def validate_channels(cls, v):
        """Validate that notification channels are valid."""
        if v is None:
            return v
        valid_channels = {"in_app", "email", "sms"}
        for channel in v:
            if channel not in valid_channels:
                raise ValueError(f"Invalid channel: {channel}. Must be one of {valid_channels}")
        return v


class CustomAlertRuleResponse(BaseModel):
    """Response model for a custom alert rule."""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    conditions: Dict[str, Any]
    tickers: Optional[List[str]]
    sectors: Optional[List[str]]
    event_types: Optional[List[str]]
    notification_channels: List[str]
    cooldown_minutes: int
    active: bool
    last_triggered_at: Optional[datetime]
    times_triggered: int
    created_at: datetime
    updated_at: datetime
    is_in_cooldown: bool = Field(description="Whether the rule is currently in cooldown")
    
    class Config:
        from_attributes = True


class MatchingEventResponse(BaseModel):
    """Response model for an event that matches a custom alert rule."""
    id: int
    ticker: str
    company_name: str
    event_type: str
    title: str
    date: datetime
    impact_score: int
    direction: Optional[str]
    confidence: float
    sector: Optional[str]
    
    class Config:
        from_attributes = True


class TestRuleResponse(BaseModel):
    """Response model for testing a custom alert rule."""
    rule_id: int
    rule_name: str
    matching_events_count: int
    matching_events: List[MatchingEventResponse]
    would_trigger: bool = Field(description="Whether the rule would trigger (not in cooldown)")


def _check_cooldown(rule: CustomAlertRule) -> bool:
    """Check if a rule is currently in cooldown period."""
    if rule.last_triggered_at is None:
        return False
    cooldown_end = rule.last_triggered_at + timedelta(minutes=rule.cooldown_minutes)
    return datetime.utcnow() < cooldown_end


def _rule_to_response(rule: CustomAlertRule) -> dict:
    """Convert a CustomAlertRule to a response dict with computed fields."""
    return {
        "id": rule.id,
        "user_id": rule.user_id,
        "name": rule.name,
        "description": rule.description,
        "conditions": rule.conditions or {},
        "tickers": rule.tickers,
        "sectors": rule.sectors,
        "event_types": rule.event_types,
        "notification_channels": rule.notification_channels or ["in_app"],
        "cooldown_minutes": rule.cooldown_minutes,
        "active": rule.active,
        "last_triggered_at": rule.last_triggered_at,
        "times_triggered": rule.times_triggered,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
        "is_in_cooldown": _check_cooldown(rule),
    }


def _find_matching_events(rule: CustomAlertRule, db: Session, limit: int = 50) -> List[Event]:
    """Find events that match a custom alert rule's criteria."""
    query = db.query(Event)
    
    conditions = rule.conditions or {}
    
    if conditions.get("min_confidence") is not None:
        query = query.filter(Event.confidence >= conditions["min_confidence"])
    
    if conditions.get("min_impact") is not None:
        query = query.filter(Event.impact_score >= conditions["min_impact"])
    
    if conditions.get("directions"):
        query = query.filter(Event.direction.in_(conditions["directions"]))
    
    if rule.tickers:
        query = query.filter(Event.ticker.in_(rule.tickers))
    
    if rule.sectors:
        query = query.filter(Event.sector.in_(rule.sectors))
    
    if rule.event_types:
        query = query.filter(Event.event_type.in_(rule.event_types))
    
    events = query.order_by(Event.date.desc()).limit(limit).all()
    return events


@router.post("", response_model=CustomAlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_custom_alert_rule(
    rule_data: CustomAlertRuleCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new custom alert rule for the authenticated user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ResourceNotFoundException("User", str(user_id))
    
    if user.plan == "free":
        raise UpgradeRequiredException("Custom Alert Rules", "Pro")
    
    if "sms" in rule_data.notification_channels:
        if not user.phone:
            raise HTTPException(
                status_code=400,
                detail="Phone number required for SMS notifications. Please add a phone number to your profile."
            )
    
    rule = CustomAlertRule(
        user_id=user_id,
        name=rule_data.name,
        description=rule_data.description,
        conditions=rule_data.conditions.dict(exclude_none=True),
        tickers=rule_data.tickers,
        sectors=rule_data.sectors,
        event_types=rule_data.event_types,
        notification_channels=rule_data.notification_channels,
        cooldown_minutes=rule_data.cooldown_minutes,
        active=rule_data.active,
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return _rule_to_response(rule)


@router.get("", response_model=List[CustomAlertRuleResponse])
async def list_custom_alert_rules(
    active_only: bool = False,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """List all custom alert rules for the authenticated user."""
    query = db.query(CustomAlertRule).filter(CustomAlertRule.user_id == user_id)
    
    if active_only:
        query = query.filter(CustomAlertRule.active == True)
    
    rules = query.order_by(CustomAlertRule.created_at.desc()).all()
    return [_rule_to_response(rule) for rule in rules]


@router.get("/{rule_id}", response_model=CustomAlertRuleResponse)
async def get_custom_alert_rule(
    rule_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get a specific custom alert rule by ID."""
    rule = db.query(CustomAlertRule).filter(
        CustomAlertRule.id == rule_id,
        CustomAlertRule.user_id == user_id
    ).first()
    
    if not rule:
        raise ResourceNotFoundException("CustomAlertRule", str(rule_id))
    
    return _rule_to_response(rule)


@router.patch("/{rule_id}", response_model=CustomAlertRuleResponse)
async def update_custom_alert_rule(
    rule_id: int,
    rule_data: CustomAlertRuleUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update an existing custom alert rule."""
    rule = db.query(CustomAlertRule).filter(
        CustomAlertRule.id == rule_id,
        CustomAlertRule.user_id == user_id
    ).first()
    
    if not rule:
        raise ResourceNotFoundException("CustomAlertRule", str(rule_id))
    
    if rule_data.notification_channels and "sms" in rule_data.notification_channels:
        user = db.query(User).filter(User.id == user_id).first()
        if not user or not user.phone:
            raise HTTPException(
                status_code=400,
                detail="Phone number required for SMS notifications. Please add a phone number to your profile."
            )
    
    update_data = rule_data.dict(exclude_unset=True)
    
    if "conditions" in update_data and update_data["conditions"] is not None:
        update_data["conditions"] = rule_data.conditions.dict(exclude_none=True)
    
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    rule.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rule)
    
    return _rule_to_response(rule)


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_custom_alert_rule(
    rule_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete a custom alert rule."""
    rule = db.query(CustomAlertRule).filter(
        CustomAlertRule.id == rule_id,
        CustomAlertRule.user_id == user_id
    ).first()
    
    if not rule:
        raise ResourceNotFoundException("CustomAlertRule", str(rule_id))
    
    db.delete(rule)
    db.commit()
    
    return None


@router.post("/{rule_id}/test", response_model=TestRuleResponse)
async def test_custom_alert_rule(
    rule_id: int,
    limit: int = 50,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Test a custom alert rule against recent events.
    
    Returns a list of events that would match the rule criteria.
    Also indicates whether the rule would trigger (not in cooldown).
    """
    rule = db.query(CustomAlertRule).filter(
        CustomAlertRule.id == rule_id,
        CustomAlertRule.user_id == user_id
    ).first()
    
    if not rule:
        raise ResourceNotFoundException("CustomAlertRule", str(rule_id))
    
    matching_events = _find_matching_events(rule, db, limit=min(limit, 100))
    is_in_cooldown = _check_cooldown(rule)
    
    return {
        "rule_id": rule.id,
        "rule_name": rule.name,
        "matching_events_count": len(matching_events),
        "matching_events": [
            {
                "id": event.id,
                "ticker": event.ticker,
                "company_name": event.company_name,
                "event_type": event.event_type,
                "title": event.title,
                "date": event.date,
                "impact_score": event.impact_score,
                "direction": event.direction,
                "confidence": event.confidence,
                "sector": event.sector,
            }
            for event in matching_events
        ],
        "would_trigger": rule.active and not is_in_cooldown and len(matching_events) > 0,
    }
