"""
User Preferences API endpoints.

Manages user-specific scoring preferences, theme, filters, and customization.
"""

from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from enum import Enum

from api.dependencies import get_db
from api.utils.auth import get_current_user_with_plan
from api.utils.paywall import require_plan
from api.ratelimit import limiter, plan_limit
from scoring_customizer import ScoringCustomizer
from releaseradar.db.models import UserPreference


router = APIRouter(prefix="/preferences", tags=["preferences"])


class ThemeEnum(str, Enum):
    dark = "dark"
    light = "light"
    system = "system"


class ThemeRequest(BaseModel):
    """Request to update theme preference."""
    theme: ThemeEnum = Field(..., description="Theme preference: dark, light, or system")


class ThemeResponse(BaseModel):
    """Response for theme preference."""
    theme: str = Field(..., description="Current theme: dark, light, or system")


class SavedFiltersRequest(BaseModel):
    """Request to update saved filters."""
    event_types: List[str] = Field(default_factory=list, description="List of event types to filter")
    sectors: List[str] = Field(default_factory=list, description="List of sectors to filter")
    min_score: int = Field(default=0, ge=0, le=100, description="Minimum impact score filter")
    horizons: List[str] = Field(default_factory=list, description="List of time horizons")


class SavedFiltersResponse(BaseModel):
    """Response for saved filters."""
    event_types: List[str] = Field(default_factory=list)
    sectors: List[str] = Field(default_factory=list)
    min_score: int = Field(default=0)
    horizons: List[str] = Field(default_factory=list)


class NotificationSettings(BaseModel):
    """Notification settings configuration."""
    email: bool = Field(default=True, description="Enable email notifications")
    sms: bool = Field(default=False, description="Enable SMS notifications")
    in_app: bool = Field(default=True, description="Enable in-app notifications")


class UserSettingsRequest(BaseModel):
    """Request to update user settings."""
    theme: Optional[ThemeEnum] = Field(None, description="Theme preference")
    default_horizon: Optional[str] = Field(None, pattern="^(1d|7d|30d)$", description="Default time horizon")
    notification_settings: Optional[NotificationSettings] = Field(None, description="Notification preferences")
    timezone: Optional[str] = Field(None, description="User timezone (e.g., 'America/New_York')")


class UserSettingsResponse(BaseModel):
    """Response for user settings."""
    user_id: int
    theme: str
    default_horizon: str
    saved_filters: Optional[dict] = None
    dashboard_layout: Optional[dict] = None
    notification_settings: Optional[dict] = None
    timezone: Optional[str] = None


def get_or_create_user_preference(db: Session, user_id: int) -> UserPreference:
    """Get existing UserPreference or create a new one with defaults."""
    pref = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()
    if not pref:
        pref = UserPreference(
            user_id=user_id,
            theme="system",
            default_horizon="1d",
            saved_filters=None,
            dashboard_layout=None,
            notification_settings={"email": True, "sms": False, "in_app": True},
            timezone="UTC"
        )
        db.add(pref)
        db.commit()
        db.refresh(pref)
    return pref


@router.get("/theme", response_model=ThemeResponse)
@limiter.limit(plan_limit)
async def get_theme(
    request: Request,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Get current user's theme preference.
    
    Returns the theme setting: 'dark', 'light', or 'system'.
    """
    try:
        pref = get_or_create_user_preference(db, user_data["user_id"])
        return {"theme": pref.theme or "system"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load theme: {str(e)}")


@router.put("/theme", response_model=ThemeResponse)
@limiter.limit(plan_limit)
async def update_theme(
    request: Request,
    theme_request: ThemeRequest,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Update user's theme preference.
    
    Sets the theme to 'dark', 'light', or 'system'.
    """
    try:
        pref = get_or_create_user_preference(db, user_data["user_id"])
        pref.theme = theme_request.theme.value
        db.commit()
        return {"theme": pref.theme}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update theme: {str(e)}")


@router.get("/filters", response_model=SavedFiltersResponse)
@limiter.limit(plan_limit)
async def get_filters(
    request: Request,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Get user's saved filters.
    
    Returns the saved filter configuration for event types, sectors, min score, and horizons.
    """
    try:
        pref = get_or_create_user_preference(db, user_data["user_id"])
        filters = pref.saved_filters or {}
        return SavedFiltersResponse(
            event_types=filters.get("event_types", []),
            sectors=filters.get("sectors", []),
            min_score=filters.get("min_score", 0),
            horizons=filters.get("horizons", [])
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load filters: {str(e)}")


@router.put("/filters", response_model=SavedFiltersResponse)
@limiter.limit(plan_limit)
async def update_filters(
    request: Request,
    filters_request: SavedFiltersRequest,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Update user's saved filters.
    
    Saves the filter configuration for event types, sectors, min score, and horizons.
    """
    try:
        pref = get_or_create_user_preference(db, user_data["user_id"])
        pref.saved_filters = {
            "event_types": filters_request.event_types,
            "sectors": filters_request.sectors,
            "min_score": filters_request.min_score,
            "horizons": filters_request.horizons
        }
        db.commit()
        return SavedFiltersResponse(**pref.saved_filters)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update filters: {str(e)}")


@router.get("/settings", response_model=UserSettingsResponse)
@limiter.limit(plan_limit)
async def get_settings(
    request: Request,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Get all user settings.
    
    Returns the full UserPreference object including theme, default horizon,
    saved filters, dashboard layout, notification settings, and timezone.
    """
    try:
        pref = get_or_create_user_preference(db, user_data["user_id"])
        return UserSettingsResponse(
            user_id=pref.user_id,
            theme=pref.theme or "system",
            default_horizon=pref.default_horizon or "1d",
            saved_filters=pref.saved_filters,
            dashboard_layout=pref.dashboard_layout,
            notification_settings=pref.notification_settings,
            timezone=pref.timezone
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load settings: {str(e)}")


@router.put("/settings", response_model=UserSettingsResponse)
@limiter.limit(plan_limit)
async def update_settings(
    request: Request,
    settings_request: UserSettingsRequest,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Update user settings.
    
    Updates theme, default horizon, notification settings, and timezone.
    Only provided fields are updated; others remain unchanged.
    """
    try:
        pref = get_or_create_user_preference(db, user_data["user_id"])
        
        if settings_request.theme is not None:
            pref.theme = settings_request.theme.value
        
        if settings_request.default_horizon is not None:
            pref.default_horizon = settings_request.default_horizon
        
        if settings_request.notification_settings is not None:
            pref.notification_settings = settings_request.notification_settings.dict()
        
        if settings_request.timezone is not None:
            pref.timezone = settings_request.timezone
        
        db.commit()
        db.refresh(pref)
        
        return UserSettingsResponse(
            user_id=pref.user_id,
            theme=pref.theme or "system",
            default_horizon=pref.default_horizon or "1d",
            saved_filters=pref.saved_filters,
            dashboard_layout=pref.dashboard_layout,
            notification_settings=pref.notification_settings,
            timezone=pref.timezone
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update settings: {str(e)}")


class ScoringPreferences(BaseModel):
    """User scoring preferences model."""
    event_type_weights: Dict[str, float] = Field(default_factory=dict, description="Event type multipliers (0.5-2.0)")
    sector_weights: Dict[str, float] = Field(default_factory=dict, description="Sector multipliers (0.5-2.0)")
    confidence_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Minimum confidence (0.0-1.0)")
    min_impact_score: int = Field(default=0, ge=0, le=100, description="Minimum impact score (0-100)")


class ScoringPreferencesResponse(BaseModel):
    """Response for scoring preferences."""
    preferences: ScoringPreferences
    is_default: bool = Field(description="Whether using default preferences")


@router.get("/scoring", response_model=ScoringPreferencesResponse)
@limiter.limit(plan_limit)
async def get_scoring_preferences(
    request: Request,
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get current user's scoring preferences.
    
    Returns user's custom scoring weights or defaults if not set.
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Scoring preferences",
        user_data.get("trial_ends_at")
    )
    
    try:
        customizer = ScoringCustomizer()
        prefs = customizer.get_user_preferences(user_data["user_id"])
        
        # Check if using defaults (no custom weights set)
        is_default = (
            not prefs.get('event_type_weights') and
            not prefs.get('sector_weights') and
            prefs.get('confidence_threshold', 0.5) == 0.5 and
            prefs.get('min_impact_score', 0) == 0
        )
        
        return {
            "preferences": ScoringPreferences(**prefs),
            "is_default": is_default
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load preferences: {str(e)}")


@router.post("/scoring", response_model=ScoringPreferencesResponse)
@limiter.limit(plan_limit)
async def update_scoring_preferences(
    request: Request,
    preferences: ScoringPreferences,
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Update user's scoring preferences.
    
    Validates and saves custom scoring weights and filters.
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Scoring preferences",
        user_data.get("trial_ends_at")
    )
    
    try:
        # Validate weight ranges (0.5 to 2.0)
        for event_type, weight in preferences.event_type_weights.items():
            if not (0.5 <= weight <= 2.0):
                raise HTTPException(
                    status_code=400,
                    detail=f"Event type weight for '{event_type}' must be between 0.5 and 2.0"
                )
        
        for sector, weight in preferences.sector_weights.items():
            if not (0.5 <= weight <= 2.0):
                raise HTTPException(
                    status_code=400,
                    detail=f"Sector weight for '{sector}' must be between 0.5 and 2.0"
                )
        
        # Save preferences
        customizer = ScoringCustomizer()
        customizer.save_user_preferences(user_data["user_id"], preferences.dict())
        
        # Return updated preferences
        prefs = customizer.get_user_preferences(user_data["user_id"])
        is_default = (
            not prefs.get('event_type_weights') and
            not prefs.get('sector_weights') and
            prefs.get('confidence_threshold', 0.5) == 0.5 and
            prefs.get('min_impact_score', 0) == 0
        )
        
        return {
            "preferences": ScoringPreferences(**prefs),
            "is_default": is_default
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save preferences: {str(e)}")


@router.post("/scoring/reset")
@limiter.limit(plan_limit)
async def reset_scoring_preferences(
    request: Request,
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Reset user's scoring preferences to defaults.
    
    Removes all custom weights and filters.
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Scoring preferences",
        user_data.get("trial_ends_at")
    )
    
    try:
        customizer = ScoringCustomizer()
        customizer.reset_user_preferences(user_data["user_id"])
        
        return {
            "message": "Scoring preferences reset to defaults",
            "preferences": ScoringPreferences(),
            "is_default": True
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to reset preferences: {str(e)}")


class DashboardModeRequest(BaseModel):
    """Request to update dashboard mode."""
    mode: str = Field(..., pattern="^(watchlist|portfolio)$", description="Dashboard mode: watchlist or portfolio")


class DashboardModeResponse(BaseModel):
    """Response for dashboard mode."""
    mode: str = Field(..., description="Current dashboard mode: watchlist or portfolio")


@router.get("/dashboard-mode", response_model=DashboardModeResponse)
@limiter.limit(plan_limit)
async def get_dashboard_mode(
    request: Request,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Get current user's dashboard mode preference.
    
    Returns either 'watchlist' or 'portfolio' mode.
    """
    try:
        from releaseradar.db.models import User
        
        user = db.query(User).filter(User.id == user_data["user_id"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Default to watchlist if not set
        mode = getattr(user, 'dashboard_mode', 'watchlist') or 'watchlist'
        
        return {"mode": mode}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load dashboard mode: {str(e)}")


@router.put("/dashboard-mode", response_model=DashboardModeResponse)
@limiter.limit(plan_limit)
async def update_dashboard_mode(
    request: Request,
    mode_request: DashboardModeRequest,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Update user's dashboard mode preference.
    
    Sets the mode to either 'watchlist' or 'portfolio'.
    """
    try:
        from releaseradar.db.models import User
        
        user = db.query(User).filter(User.id == user_data["user_id"]).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Use setattr for safer SQLAlchemy attribute assignment
        setattr(user, 'dashboard_mode', mode_request.mode)
        db.commit()
        
        return {"mode": mode_request.mode}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Failed to update dashboard mode: {str(e)}")
