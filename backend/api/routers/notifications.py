"""
API endpoints for user in-app notifications.

Provides endpoints for fetching notifications and marking them as read.
"""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import desc

from releaseradar.db.models import UserNotification
from api.dependencies import get_db
from api.utils.auth import get_current_user_id


router = APIRouter(prefix="/notifications", tags=["notifications"])


class NotificationResponse(BaseModel):
    """Response model for a notification."""
    id: int
    user_id: int
    title: str
    body: str
    url: Optional[str]
    created_at: datetime
    read_at: Optional[datetime]
    
    class Config:
        from_attributes = True


class MarkReadRequest(BaseModel):
    """Request model for marking notifications as read."""
    notification_ids: List[int]


@router.get("", response_model=List[NotificationResponse])
async def get_notifications(
    limit: int = 50,
    unread_only: bool = False,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get notifications for the authenticated user.
    
    Args:
        limit: Maximum number of notifications to return (default 50, max 100)
        unread_only: If True, only return unread notifications
        user_id: Authenticated user ID from token
        db: Database session
        
    Returns:
        List of notifications ordered by created_at descending
    """
    # Cap limit at 100
    limit = min(limit, 100)
    
    query = db.query(UserNotification).filter(
        UserNotification.user_id == user_id
    )
    
    if unread_only:
        query = query.filter(UserNotification.read_at.is_(None))
    
    notifications = query.order_by(desc(UserNotification.created_at)).limit(limit).all()
    
    return notifications


@router.get("/unread-count")
async def get_unread_count(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get count of unread notifications for the authenticated user."""
    count = db.query(UserNotification).filter(
        UserNotification.user_id == user_id,
        UserNotification.read_at.is_(None)
    ).count()
    
    return {"unread_count": count}


@router.post("/mark-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_notifications_read(
    request: MarkReadRequest,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Mark one or more notifications as read.
    
    Args:
        request: List of notification IDs to mark as read
        user_id: Authenticated user ID from token
        db: Database session
    """
    if not request.notification_ids:
        return None
    
    # Update notifications
    db.query(UserNotification).filter(
        UserNotification.id.in_(request.notification_ids),
        UserNotification.user_id == user_id
    ).update(
        {"read_at": datetime.utcnow()},
        synchronize_session=False
    )
    
    db.commit()
    
    return None


@router.post("/mark-all-read", status_code=status.HTTP_204_NO_CONTENT)
async def mark_all_notifications_read(
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read for the authenticated user."""
    db.query(UserNotification).filter(
        UserNotification.user_id == user_id,
        UserNotification.read_at.is_(None)
    ).update(
        {"read_at": datetime.utcnow()},
        synchronize_session=False
    )
    
    db.commit()
    
    return None
