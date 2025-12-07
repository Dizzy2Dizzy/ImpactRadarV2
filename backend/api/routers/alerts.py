"""
CRUD API endpoints for user alerts management.

Allows users to create, read, update, and delete alerts with filters for 
tickers, sectors, event types, keywords, and score thresholds.
"""

from datetime import datetime
from typing import List, Optional
import re

from fastapi import APIRouter, Depends, status, HTTPException
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session

from releaseradar.db.models import Alert, User
from api.dependencies import get_db
from api.utils.auth import get_current_user_id
from api.utils.exceptions import ResourceNotFoundException, UpgradeRequiredException


router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertCreate(BaseModel):
    """Request model for creating an alert."""
    name: str = Field(..., min_length=1, max_length=200)
    min_score: int = Field(default=0, ge=0, le=100)
    tickers: Optional[List[str]] = Field(default=None)
    sectors: Optional[List[str]] = Field(default=None)
    event_types: Optional[List[str]] = Field(default=None)
    keywords: Optional[List[str]] = Field(default=None)
    channels: List[str] = Field(default=["in_app"])
    active: bool = Field(default=True)
    
    # Webhook integration fields (Team plan only)
    webhook_url: Optional[str] = Field(default=None)
    slack_webhook_url: Optional[str] = Field(default=None)
    discord_webhook_url: Optional[str] = Field(default=None)
    
    @validator("channels")
    def validate_channels(cls, v):
        """Validate that channels are valid."""
        valid_channels = {"in_app", "email", "sms", "webhook", "slack", "discord"}
        for channel in v:
            if channel not in valid_channels:
                raise ValueError(f"Invalid channel: {channel}. Must be one of {valid_channels}")
        return v
    
    @validator("tickers", "sectors", "event_types", "keywords")
    def validate_arrays(cls, v):
        """Ensure arrays are not empty if provided."""
        if v is not None and len(v) == 0:
            return None
        return v
    
    @validator("webhook_url", "slack_webhook_url", "discord_webhook_url")
    def validate_webhook_url(cls, v):
        """Validate webhook URLs are valid HTTP/HTTPS URLs."""
        if v is not None and v.strip():
            if not v.startswith(("http://", "https://")):
                raise ValueError("Webhook URL must start with http:// or https://")
        return v


class AlertUpdate(BaseModel):
    """Request model for updating an alert."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    min_score: Optional[int] = Field(default=None, ge=0, le=100)
    tickers: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    event_types: Optional[List[str]] = None
    keywords: Optional[List[str]] = None
    channels: Optional[List[str]] = None
    active: Optional[bool] = None
    
    # Webhook integration fields (Team plan only)
    webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    
    @validator("channels")
    def validate_channels(cls, v):
        """Validate that channels are valid."""
        if v is None:
            return v
        valid_channels = {"in_app", "email", "sms", "webhook", "slack", "discord"}
        for channel in v:
            if channel not in valid_channels:
                raise ValueError(f"Invalid channel: {channel}. Must be one of {valid_channels}")
        return v
    
    @validator("webhook_url", "slack_webhook_url", "discord_webhook_url")
    def validate_webhook_url(cls, v):
        """Validate webhook URLs are valid HTTP/HTTPS URLs."""
        if v is not None and v.strip():
            if not v.startswith(("http://", "https://")):
                raise ValueError("Webhook URL must start with http:// or https://")
        return v


class AlertResponse(BaseModel):
    """Response model for an alert."""
    id: int
    user_id: int
    name: str
    min_score: int
    tickers: Optional[List[str]]
    sectors: Optional[List[str]]
    event_types: Optional[List[str]]
    keywords: Optional[List[str]]
    channels: List[str]
    active: bool
    created_at: datetime
    
    # Webhook integration fields
    webhook_url: Optional[str] = None
    slack_webhook_url: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    
    class Config:
        from_attributes = True


@router.post("", response_model=AlertResponse, status_code=status.HTTP_201_CREATED)
async def create_alert(
    alert_data: AlertCreate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Create a new alert for the authenticated user."""
    # Check user plan - only Pro and Team users can create alerts
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ResourceNotFoundException("User", str(user_id))
    
    if user.plan == "free":
        raise UpgradeRequiredException("Alerts", "Pro")
    
    # Webhook channels require Team plan
    team_only_channels = {"webhook", "slack", "discord"}
    requested_team_channels = set(alert_data.channels) & team_only_channels
    
    if requested_team_channels and user.plan != "team":
        raise HTTPException(
            status_code=403,
            detail=f"Webhook integrations ({', '.join(requested_team_channels)}) require a Team plan. Please upgrade to use Slack, Discord, or custom webhook notifications."
        )
    
    # Validate phone number if SMS channel is selected
    if "sms" in alert_data.channels:
        if not user.phone:
            raise HTTPException(
                status_code=400,
                detail="Phone number required for SMS notifications. Please add a phone number to your profile."
            )
        # Validate E.164 format (+ followed by 1-15 digits)
        if not re.match(r'^\+[1-9]\d{1,14}$', user.phone):
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number format. Phone must be in E.164 format (e.g., +14155551234)"
            )
    
    # Validate webhook URLs are provided for corresponding channels
    if "webhook" in alert_data.channels and not alert_data.webhook_url:
        raise HTTPException(
            status_code=400,
            detail="Webhook URL is required when using the 'webhook' channel."
        )
    
    if "slack" in alert_data.channels and not alert_data.slack_webhook_url:
        raise HTTPException(
            status_code=400,
            detail="Slack webhook URL is required when using the 'slack' channel."
        )
    
    if "discord" in alert_data.channels and not alert_data.discord_webhook_url:
        raise HTTPException(
            status_code=400,
            detail="Discord webhook URL is required when using the 'discord' channel."
        )
    
    # Create alert
    alert = Alert(
        user_id=user_id,
        name=alert_data.name,
        min_score=alert_data.min_score,
        tickers=alert_data.tickers,
        sectors=alert_data.sectors,
        event_types=alert_data.event_types,
        keywords=alert_data.keywords,
        channels=alert_data.channels,
        active=alert_data.active,
        webhook_url=alert_data.webhook_url,
        slack_webhook_url=alert_data.slack_webhook_url,
        discord_webhook_url=alert_data.discord_webhook_url
    )
    
    db.add(alert)
    db.commit()
    db.refresh(alert)
    
    return alert


@router.get("", response_model=List[AlertResponse])
async def list_alerts(
    active_only: bool = False,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """List all alerts for the authenticated user."""
    query = db.query(Alert).filter(Alert.user_id == user_id)
    
    if active_only:
        query = query.filter(Alert.active == True)
    
    alerts = query.order_by(Alert.created_at.desc()).all()
    return alerts


@router.get("/{alert_id}", response_model=AlertResponse)
async def get_alert(
    alert_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get a specific alert by ID."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == user_id
    ).first()
    
    if not alert:
        raise ResourceNotFoundException("Alert", str(alert_id))
    
    return alert


@router.patch("/{alert_id}", response_model=AlertResponse)
async def update_alert(
    alert_id: int,
    alert_data: AlertUpdate,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Update an existing alert."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == user_id
    ).first()
    
    if not alert:
        raise ResourceNotFoundException("Alert", str(alert_id))
    
    user = db.query(User).filter(User.id == user_id).first()
    
    # Webhook channels require Team plan
    if alert_data.channels:
        team_only_channels = {"webhook", "slack", "discord"}
        requested_team_channels = set(alert_data.channels) & team_only_channels
        
        if requested_team_channels and user.plan != "team":
            raise HTTPException(
                status_code=403,
                detail=f"Webhook integrations ({', '.join(requested_team_channels)}) require a Team plan. Please upgrade to use Slack, Discord, or custom webhook notifications."
            )
    
    # Validate phone number if SMS channel is being added
    if alert_data.channels and "sms" in alert_data.channels:
        if not user.phone:
            raise HTTPException(
                status_code=400,
                detail="Phone number required for SMS notifications. Please add a phone number to your profile."
            )
        # Validate E.164 format
        if not re.match(r'^\+[1-9]\d{1,14}$', user.phone):
            raise HTTPException(
                status_code=400,
                detail="Invalid phone number format. Phone must be in E.164 format (e.g., +14155551234)"
            )
    
    # Determine final channels (from update or existing)
    final_channels = alert_data.channels if alert_data.channels is not None else alert.channels
    
    # Determine final webhook URLs (from update or existing)
    final_webhook_url = alert_data.webhook_url if alert_data.webhook_url is not None else alert.webhook_url
    final_slack_url = alert_data.slack_webhook_url if alert_data.slack_webhook_url is not None else alert.slack_webhook_url
    final_discord_url = alert_data.discord_webhook_url if alert_data.discord_webhook_url is not None else alert.discord_webhook_url
    
    # Validate webhook URLs are provided for corresponding channels
    if "webhook" in final_channels and not final_webhook_url:
        raise HTTPException(
            status_code=400,
            detail="Webhook URL is required when using the 'webhook' channel."
        )
    
    if "slack" in final_channels and not final_slack_url:
        raise HTTPException(
            status_code=400,
            detail="Slack webhook URL is required when using the 'slack' channel."
        )
    
    if "discord" in final_channels and not final_discord_url:
        raise HTTPException(
            status_code=400,
            detail="Discord webhook URL is required when using the 'discord' channel."
        )
    
    # Update only provided fields
    update_data = alert_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(alert, field, value)
    
    db.commit()
    db.refresh(alert)
    
    return alert


@router.delete("/{alert_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert(
    alert_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Delete an alert (CASCADE deletes associated logs)."""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.user_id == user_id
    ).first()
    
    if not alert:
        raise ResourceNotFoundException("Alert", str(alert_id))
    
    db.delete(alert)
    db.commit()
    
    return None
