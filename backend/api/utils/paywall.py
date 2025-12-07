"""
Paywall utilities for enforcing plan-based access control.

Provides standardized 402 Payment Required responses for feature gating.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel
from api.utils.exceptions import UpgradeRequiredException


class PaywallResponse(BaseModel):
    """Standard paywall response structure"""
    error: str = "UPGRADE_REQUIRED"
    feature: str
    plan_required: str  # "pro" or "team"
    message: str
    trial_available: Optional[bool] = None


def require_plan(
    current_plan: str,
    required_plan: str,
    feature: str,
    trial_ends_at: Optional[datetime] = None
):
    """
    Enforce plan requirement for a feature.
    
    Args:
        current_plan: User's current plan (free, pro, team)
        required_plan: Minimum required plan (pro or team)
        feature: Feature name for error message
        trial_ends_at: User's trial expiration (if any)
    
    Raises:
        HTTPException: 402 Payment Required if access denied
    """
    # Check if trial has expired
    if trial_ends_at and trial_ends_at < datetime.utcnow():
        # Trial expired, downgrade effectively to free
        current_plan = "free"
    
    # Plan hierarchy: free < pro < team
    plan_hierarchy = {"free": 0, "pro": 1, "team": 2}
    
    current_level = plan_hierarchy.get(current_plan, 0)
    required_level = plan_hierarchy.get(required_plan, 1)
    
    if current_level < required_level:
        raise UpgradeRequiredException(feature, required_plan.capitalize())


def is_trial_active(trial_ends_at: Optional[datetime]) -> bool:
    """Check if a trial is currently active"""
    if not trial_ends_at:
        return False
    return trial_ends_at > datetime.utcnow()


def get_effective_plan(plan: str, trial_ends_at: Optional[datetime]) -> str:
    """
    Get effective plan accounting for expired trials.
    
    Args:
        plan: User's plan from database
        trial_ends_at: User's trial expiration
    
    Returns:
        Effective plan (free if trial expired)
    """
    if plan in ("pro", "team") and trial_ends_at:
        # User has pro/team but no paid subscription (trial)
        if trial_ends_at < datetime.utcnow():
            return "free"  # Trial expired
    return plan
