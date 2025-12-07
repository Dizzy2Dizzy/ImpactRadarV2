"""
Admin dashboard API endpoints.
Protected by ADMIN_KEY for developer-only access.
"""
import os
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from threading import Lock
import time
import logging

from fastapi import APIRouter, Depends, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy import func, text, desc, select
from sqlalchemy.orm import Session

from api.dependencies import get_db
from database import Company, Event, User
from releaseradar.db.models import ForumMessage, ScanJob, ChangelogRelease, ChangelogItem

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

# ============================================================================
# ACTIVE USERS TRACKING
# ============================================================================

class ActiveUsersStore:
    """In-memory store for tracking active users with thread-safe operations."""
    
    def __init__(self, timeout_seconds: int = 300):
        self._active_users: Dict[int, Dict] = {}
        self._lock = Lock()
        self._timeout = timeout_seconds
    
    def heartbeat(self, user_id: int, email: str = None, plan: str = None):
        """Record user activity. Call this when user makes any request."""
        with self._lock:
            self._active_users[user_id] = {
                "last_seen": time.time(),
                "email": email,
                "plan": plan
            }
    
    def get_active_count(self) -> int:
        """Get count of users active within the timeout period."""
        self._cleanup_expired()
        with self._lock:
            return len(self._active_users)
    
    def get_active_users(self) -> List[Dict]:
        """Get list of active users with their info."""
        self._cleanup_expired()
        with self._lock:
            now = time.time()
            return [
                {
                    "user_id": user_id,
                    "email": data.get("email"),
                    "plan": data.get("plan"),
                    "seconds_ago": int(now - data["last_seen"])
                }
                for user_id, data in self._active_users.items()
            ]
    
    def remove_user(self, user_id: int):
        """Remove user from active list (e.g., on logout)."""
        with self._lock:
            self._active_users.pop(user_id, None)
    
    def _cleanup_expired(self):
        """Remove users who haven't been seen within timeout period."""
        with self._lock:
            now = time.time()
            expired = [
                user_id for user_id, data in self._active_users.items()
                if now - data["last_seen"] > self._timeout
            ]
            for user_id in expired:
                del self._active_users[user_id]


active_users_store = ActiveUsersStore(timeout_seconds=300)

ADMIN_KEY = os.environ.get("ADMIN_KEY", "")


def verify_admin_key(x_admin_key: str = Header(..., alias="X-Admin-Key")) -> bool:
    """Verify the admin key from request header."""
    if not ADMIN_KEY:
        raise HTTPException(status_code=500, detail="Admin key not configured")
    if x_admin_key != ADMIN_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin key")
    return True


class AdminVerifyResponse(BaseModel):
    valid: bool
    message: str


class UserStats(BaseModel):
    total_users: int
    free_users: int
    pro_users: int
    team_users: int
    verified_users: int
    unverified_users: int
    users_today: int
    users_this_week: int
    users_this_month: int


class WebsiteStats(BaseModel):
    total_events: int
    total_companies: int
    tracked_companies: int
    events_today: int
    events_this_week: int


class ContactMessage(BaseModel):
    id: int
    name: str
    email: str
    message: str
    status: str
    created_at: datetime


class ContactMessagesResponse(BaseModel):
    messages: list[ContactMessage]
    total: int
    unread: int


@router.get("/verify", response_model=AdminVerifyResponse)
async def verify_admin(
    _: bool = Depends(verify_admin_key)
):
    """Verify admin key is valid."""
    return AdminVerifyResponse(valid=True, message="Admin key verified")


@router.get("/stats/users", response_model=UserStats)
async def get_user_stats(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get user statistics for admin dashboard."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    week_start = week_start - timedelta(days=now.weekday())
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    total_users = db.query(func.count(User.id)).scalar() or 0
    free_users = db.query(func.count(User.id)).filter(User.plan == "free").scalar() or 0
    pro_users = db.query(func.count(User.id)).filter(User.plan == "pro").scalar() or 0
    team_users = db.query(func.count(User.id)).filter(User.plan == "team").scalar() or 0
    verified_users = db.query(func.count(User.id)).filter(User.is_verified == True).scalar() or 0
    unverified_users = db.query(func.count(User.id)).filter(User.is_verified == False).scalar() or 0
    
    users_today = db.query(func.count(User.id)).filter(User.created_at >= today_start).scalar() or 0
    users_this_week = db.query(func.count(User.id)).filter(User.created_at >= week_start).scalar() or 0
    users_this_month = db.query(func.count(User.id)).filter(User.created_at >= month_start).scalar() or 0
    
    return UserStats(
        total_users=total_users,
        free_users=free_users,
        pro_users=pro_users,
        team_users=team_users,
        verified_users=verified_users,
        unverified_users=unverified_users,
        users_today=users_today,
        users_this_week=users_this_week,
        users_this_month=users_this_month
    )


@router.get("/stats/website", response_model=WebsiteStats)
async def get_website_stats(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Get website statistics for admin dashboard."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    week_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = week_start - timedelta(days=now.weekday())
    
    total_events = db.query(func.count(Event.id)).scalar() or 0
    total_companies = db.query(func.count(Company.id)).scalar() or 0
    tracked_companies = db.query(func.count(Company.id)).filter(Company.tracked == True).scalar() or 0
    
    events_today = db.query(func.count(Event.id)).filter(Event.created_at >= today_start).scalar() or 0
    events_this_week = db.query(func.count(Event.id)).filter(Event.created_at >= week_start).scalar() or 0
    
    return WebsiteStats(
        total_events=total_events,
        total_companies=total_companies,
        tracked_companies=tracked_companies,
        events_today=events_today,
        events_this_week=events_this_week
    )


@router.get("/messages", response_model=ContactMessagesResponse)
async def get_contact_messages(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key),
    limit: int = 50,
    offset: int = 0,
    status: Optional[str] = None
):
    """Get contact form messages for admin dashboard."""
    query = "SELECT id, name, email, message, status, created_at FROM contact_messages"
    count_query = "SELECT COUNT(*) FROM contact_messages"
    unread_query = "SELECT COUNT(*) FROM contact_messages WHERE status = 'unread'"
    
    params = {}
    
    if status:
        query += " WHERE status = :status"
        count_query += " WHERE status = :status"
        params["status"] = status
    
    query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    params["limit"] = limit
    params["offset"] = offset
    
    result = db.execute(text(query), params)
    rows = result.fetchall()
    
    messages = [
        ContactMessage(
            id=row[0],
            name=row[1],
            email=row[2],
            message=row[3],
            status=row[4],
            created_at=row[5]
        )
        for row in rows
    ]
    
    total = db.execute(text(count_query.replace(" LIMIT :limit OFFSET :offset", "")), 
                       {"status": status} if status else {}).scalar() or 0
    unread = db.execute(text(unread_query)).scalar() or 0
    
    return ContactMessagesResponse(
        messages=messages,
        total=total,
        unread=unread
    )


@router.patch("/messages/{message_id}")
async def update_message_status(
    message_id: int,
    status: str,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """Update contact message status (mark as read/unread)."""
    if status not in ["read", "unread", "archived"]:
        raise HTTPException(status_code=400, detail="Invalid status. Must be 'read', 'unread', or 'archived'")
    
    result = db.execute(
        text("UPDATE contact_messages SET status = :status WHERE id = :id RETURNING id"),
        {"status": status, "id": message_id}
    )
    updated_row = result.fetchone()
    if not updated_row:
        raise HTTPException(status_code=404, detail="Message not found")
    
    db.commit()
    return {"success": True, "message_id": message_id, "status": status}


@router.get("/users/list")
async def get_users_list(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key),
    limit: int = 100,
    offset: int = 0
):
    """Get list of users with their details (no passwords)."""
    users = db.query(User).order_by(User.created_at.desc()).limit(limit).offset(offset).all()
    
    return {
        "users": [
            {
                "id": user.id,
                "email": user.email,
                "phone": user.phone,
                "plan": user.plan,
                "is_verified": user.is_verified,
                "is_admin": user.is_admin,
                "created_at": user.created_at.isoformat() if user.created_at is not None else None,
                "last_login": user.last_login.isoformat() if user.last_login is not None else None,
            }
            for user in users
        ],
        "total": db.query(func.count(User.id)).scalar() or 0
    }


@router.get("/errors")
async def get_sentry_errors(
    _: bool = Depends(verify_admin_key)
):
    """
    Get recent Sentry errors.
    Note: This would require Sentry API integration.
    For now, returns a placeholder indicating Sentry errors should be viewed in the Sentry dashboard.
    """
    return {
        "message": "Sentry errors should be viewed directly in the Sentry dashboard",
        "sentry_url": "https://sentry.io",
        "note": "To integrate Sentry API, you would need to add SENTRY_AUTH_TOKEN and SENTRY_ORG/PROJECT settings"
    }


# ============================================================================
# ACTIVE USERS ENDPOINTS
# ============================================================================

class ActiveUserInfo(BaseModel):
    user_id: int
    email: Optional[str]
    plan: Optional[str]
    seconds_ago: int


class ActiveUsersResponse(BaseModel):
    count: int
    users: List[ActiveUserInfo]
    timeout_seconds: int


@router.get("/active-users", response_model=ActiveUsersResponse)
async def get_active_users(
    _: bool = Depends(verify_admin_key)
):
    """
    Get count and list of currently active users.
    Users are considered active if they made a request within the last 5 minutes.
    """
    users = active_users_store.get_active_users()
    return ActiveUsersResponse(
        count=len(users),
        users=[ActiveUserInfo(**u) for u in users],
        timeout_seconds=300
    )


# ============================================================================
# FORUM MESSAGES ADMIN ENDPOINTS
# ============================================================================

class ForumUserInfo(BaseModel):
    id: int
    email: Optional[str]
    username: str
    plan: str


class ForumMessageAdmin(BaseModel):
    id: int
    user_id: int
    content: str
    image_url: Optional[str]
    is_ai_response: bool
    ai_prompt: Optional[str]
    parent_message_id: Optional[int]
    created_at: datetime
    edited_at: Optional[datetime]
    deleted_at: Optional[datetime]
    user: ForumUserInfo

    class Config:
        from_attributes = True


class ForumMessagesAdminResponse(BaseModel):
    messages: List[ForumMessageAdmin]
    total: int
    has_more: bool


@router.get("/forum/messages", response_model=ForumMessagesAdminResponse)
async def get_forum_messages_admin(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key),
    limit: int = 50,
    offset: int = 0,
    include_deleted: bool = False
):
    """
    Get forum messages for admin dashboard.
    Includes user information and supports pagination.
    Can include soft-deleted messages if include_deleted is True.
    """
    query = db.query(ForumMessage).join(User, ForumMessage.user_id == User.id)
    
    if not include_deleted:
        query = query.filter(ForumMessage.deleted_at.is_(None))
    
    total = query.count()
    
    messages = query.order_by(desc(ForumMessage.created_at)).offset(offset).limit(limit).all()
    
    result = []
    for msg in messages:
        user = db.query(User).filter(User.id == msg.user_id).first()
        email = user.email if user else None
        username = email.split('@')[0] if email else f"user_{msg.user_id}"
        
        result.append(ForumMessageAdmin(
            id=msg.id,
            user_id=msg.user_id,
            content=msg.content,
            image_url=msg.image_url,
            is_ai_response=msg.is_ai_response,
            ai_prompt=msg.ai_prompt,
            parent_message_id=msg.parent_message_id,
            created_at=msg.created_at,
            edited_at=msg.edited_at,
            deleted_at=msg.deleted_at,
            user=ForumUserInfo(
                id=user.id if user else msg.user_id,
                email=email,
                username=username,
                plan=user.plan if user else "unknown"
            )
        ))
    
    return ForumMessagesAdminResponse(
        messages=result,
        total=total,
        has_more=offset + limit < total
    )


@router.delete("/forum/messages/{message_id}")
async def delete_forum_message_admin(
    message_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key),
    hard_delete: bool = False
):
    """
    Delete a forum message.
    By default, performs a soft delete (sets deleted_at timestamp).
    Set hard_delete=True to permanently remove the message.
    """
    message = db.query(ForumMessage).filter(ForumMessage.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if hard_delete:
        db.delete(message)
        db.commit()
        return {"success": True, "message_id": message_id, "action": "hard_deleted"}
    else:
        message.deleted_at = datetime.utcnow()
        db.commit()
        return {"success": True, "message_id": message_id, "action": "soft_deleted"}


@router.patch("/forum/messages/{message_id}/restore")
async def restore_forum_message_admin(
    message_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Restore a soft-deleted forum message.
    """
    message = db.query(ForumMessage).filter(ForumMessage.id == message_id).first()
    
    if not message:
        raise HTTPException(status_code=404, detail="Message not found")
    
    if message.deleted_at is None:
        raise HTTPException(status_code=400, detail="Message is not deleted")
    
    message.deleted_at = None
    db.commit()
    return {"success": True, "message_id": message_id, "action": "restored"}


# ============================================================================
# SCANNER CONTROL & NOTIFICATIONS
# ============================================================================

class GlobalNotificationStore:
    """Store for global notifications that all users should see."""
    
    def __init__(self):
        self._notifications: List[Dict] = []
        self._lock = Lock()
        self._notification_id = 0
    
    def add_notification(self, message: str, notification_type: str = "success", duration_seconds: int = 60):
        """Add a global notification."""
        with self._lock:
            self._notification_id += 1
            notification = {
                "id": self._notification_id,
                "message": message,
                "type": notification_type,
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": (datetime.utcnow() + timedelta(seconds=duration_seconds)).isoformat()
            }
            self._notifications.append(notification)
            # Clean up old notifications (keep last 10)
            if len(self._notifications) > 10:
                self._notifications = self._notifications[-10:]
            return notification
    
    def get_active_notifications(self) -> List[Dict]:
        """Get notifications that haven't expired."""
        with self._lock:
            now = datetime.utcnow()
            active = []
            for n in self._notifications:
                expires = datetime.fromisoformat(n["expires_at"])
                if expires > now:
                    active.append(n)
            return active
    
    def clear_notification(self, notification_id: int):
        """Clear a specific notification."""
        with self._lock:
            self._notifications = [n for n in self._notifications if n["id"] != notification_id]


class ScanOperationStore:
    """Store for tracking scan operations with automatic timeout."""
    
    OPERATION_TIMEOUT_SECONDS = 1800  # 30 minutes max for all scanners
    
    def __init__(self):
        self._current_operation: Optional[Dict] = None
        self._lock = Lock()
    
    def _check_timeout(self) -> bool:
        """Check if current operation has timed out and auto-clear if so."""
        if not self._current_operation:
            return False
        
        if self._current_operation["status"] != "running":
            return False
        
        started_at = datetime.fromisoformat(self._current_operation["started_at"])
        elapsed = (datetime.utcnow() - started_at).total_seconds()
        
        if elapsed > self.OPERATION_TIMEOUT_SECONDS:
            self._current_operation["status"] = "timeout"
            self._current_operation["error"] = f"Operation timed out after {int(elapsed)} seconds"
            self._current_operation["completed_at"] = datetime.utcnow().isoformat()
            logger.warning(f"Scan operation auto-timed out after {int(elapsed)}s")
            return True
        
        return False
    
    def start_operation(self, total_scanners: int, scanner_labels: List[str]) -> Dict:
        """Start a new scan operation."""
        with self._lock:
            # Check for timeout first
            self._check_timeout()
            
            if self._current_operation and self._current_operation["status"] == "running":
                raise ValueError("A scan operation is already in progress")
            
            self._current_operation = {
                "id": int(time.time() * 1000),
                "status": "running",
                "started_at": datetime.utcnow().isoformat(),
                "total_scanners": total_scanners,
                "completed_scanners": 0,
                "scanner_results": {label: {"status": "pending", "events_found": 0} for label in scanner_labels},
                "estimated_duration_seconds": total_scanners * 30,  # ~30s per scanner average
                "error": None
            }
            return self._current_operation.copy()
    
    def update_scanner_result(self, scanner_label: str, status: str, events_found: int = 0, error: str = None):
        """Update result for a specific scanner."""
        with self._lock:
            if not self._current_operation:
                return
            
            if scanner_label in self._current_operation["scanner_results"]:
                self._current_operation["scanner_results"][scanner_label] = {
                    "status": status,
                    "events_found": events_found,
                    "error": error,
                    "completed_at": datetime.utcnow().isoformat()
                }
                
                if status in ["success", "error"]:
                    self._current_operation["completed_scanners"] += 1
    
    def complete_operation(self, total_events: int):
        """Mark the operation as complete."""
        with self._lock:
            if self._current_operation:
                self._current_operation["status"] = "completed"
                self._current_operation["completed_at"] = datetime.utcnow().isoformat()
                self._current_operation["total_events_found"] = total_events
    
    def fail_operation(self, error: str):
        """Mark the operation as failed."""
        with self._lock:
            if self._current_operation:
                self._current_operation["status"] = "error"
                self._current_operation["error"] = error
                self._current_operation["completed_at"] = datetime.utcnow().isoformat()
    
    def get_current_operation(self) -> Optional[Dict]:
        """Get the current operation status."""
        with self._lock:
            # Check for timeout on every status check
            self._check_timeout()
            return self._current_operation.copy() if self._current_operation else None
    
    def clear_operation(self):
        """Clear the current operation (for manual reset)."""
        with self._lock:
            self._current_operation = None


# Global stores
global_notifications = GlobalNotificationStore()
scan_operations = ScanOperationStore()


class TriggerAllScannersResponse(BaseModel):
    operation_id: int
    status: str
    total_scanners: int
    estimated_duration_seconds: int
    message: str


class ScannerResult(BaseModel):
    status: str
    events_found: int
    error: Optional[str] = None
    completed_at: Optional[str] = None


class ScanOperationStatus(BaseModel):
    id: int
    status: str
    started_at: str
    completed_at: Optional[str] = None
    total_scanners: int
    completed_scanners: int
    scanner_results: Dict[str, ScannerResult]
    estimated_duration_seconds: int
    total_events_found: Optional[int] = None
    error: Optional[str] = None


class GlobalNotification(BaseModel):
    id: int
    message: str
    type: str
    created_at: str
    expires_at: str


@router.get("/notifications/global", response_model=List[GlobalNotification])
async def get_global_notifications():
    """
    Get active global notifications.
    This endpoint is public so all users can see notifications.
    """
    return global_notifications.get_active_notifications()


@router.delete("/notifications/global/{notification_id}")
async def clear_global_notification(
    notification_id: int,
    _: bool = Depends(verify_admin_key)
):
    """Clear a global notification (admin only)."""
    global_notifications.clear_notification(notification_id)
    return {"success": True}


SCAN_JOB_TIMEOUT_SECONDS = 1800  # 30 minutes max per scanner


def cleanup_stale_scan_jobs(db: Session) -> int:
    """Mark stale running scan jobs as timed out."""
    cutoff = datetime.utcnow() - timedelta(seconds=SCAN_JOB_TIMEOUT_SECONDS)
    from sqlalchemy import or_
    stale_jobs = db.query(ScanJob).filter(
        ScanJob.status == "running",
        or_(
            ScanJob.started_at < cutoff,
            ScanJob.created_at < cutoff  # Fallback for NULL started_at
        )
    ).all()
    
    count = 0
    for job in stale_jobs:
        job.status = "error"
        job.error = f"Timed out after {SCAN_JOB_TIMEOUT_SECONDS} seconds"
        job.finished_at = datetime.utcnow()
        count += 1
        logger.warning(f"Marked stale scan job {job.id} as timed out")
    
    if count > 0:
        db.commit()
    
    return count


@router.get("/scanners/operation-status")
async def get_scan_operation_status(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Get the current scan operation status from database.
    
    Aggregates status from ScanJob table for accurate real-time progress.
    Only considers scanner-scoped jobs (not company rescans).
    Automatically cleans up stale jobs that have been running too long.
    
    Batch grouping: All scanner jobs created after the first running/queued job
    are considered part of the same batch, until the batch is fully complete.
    """
    cleanup_stale_scan_jobs(db)
    
    now = datetime.utcnow()
    
    running_or_queued = db.query(ScanJob).filter(
        ScanJob.scope == "scanner",
        ScanJob.status.in_(["running", "queued"])
    ).order_by(ScanJob.created_at.asc()).all()
    
    if not running_or_queued:
        recent_cutoff = now - timedelta(minutes=10)
        last_completed = db.query(ScanJob).filter(
            ScanJob.scope == "scanner",
            ScanJob.status.in_(["success", "error"]),
            ScanJob.finished_at >= recent_cutoff
        ).order_by(ScanJob.finished_at.desc()).first()
        
        if last_completed:
            return {
                "status": "idle",
                "message": "Last scan completed",
                "last_completed_at": last_completed.finished_at.isoformat(),
                "last_status": last_completed.status
            }
        return {"status": "idle", "message": "No scan operation in progress"}
    
    first_active_job = running_or_queued[0]
    batch_start = first_active_job.created_at
    
    batch_jobs = db.query(ScanJob).filter(
        ScanJob.scope == "scanner",
        ScanJob.created_at >= batch_start - timedelta(seconds=5)
    ).order_by(ScanJob.created_at.asc()).all()
    
    total_scanners = len(batch_jobs)
    completed_scanners = len([j for j in batch_jobs if j.status in ("success", "error")])
    running_count = len([j for j in batch_jobs if j.status == "running"])
    queued_count = len([j for j in batch_jobs if j.status == "queued"])
    
    scanner_results = {}
    for job in batch_jobs:
        label = job.scanner_key or f"scanner_{job.id}"
        scanner_results[label] = {
            "status": "running" if job.status == "running" else ("success" if job.status == "success" else ("pending" if job.status == "queued" else "error")),
            "events_found": job.items_found or 0,
            "error": job.error,
            "completed_at": job.finished_at.isoformat() if job.finished_at else None
        }
    
    started_at = min(j.started_at or j.created_at for j in batch_jobs)
    elapsed_seconds = (now - started_at).total_seconds()
    estimated_per_scanner = 30 if not completed_scanners else elapsed_seconds / max(completed_scanners, 1)
    remaining_scanners = total_scanners - completed_scanners
    estimated_remaining = int(remaining_scanners * estimated_per_scanner)
    
    return {
        "id": batch_jobs[0].id if batch_jobs else 0,
        "status": "running" if running_count > 0 or queued_count > 0 else "completed",
        "started_at": started_at.isoformat(),
        "completed_at": None if running_count > 0 or queued_count > 0 else (max(j.finished_at for j in batch_jobs if j.finished_at) if any(j.finished_at for j in batch_jobs) else now).isoformat(),
        "total_scanners": total_scanners,
        "completed_scanners": completed_scanners,
        "scanner_results": scanner_results,
        "estimated_duration_seconds": estimated_remaining,
        "total_events_found": sum(j.items_found or 0 for j in batch_jobs if j.status == "success"),
        "error": None
    }


@router.post("/scanners/clear-operation")
async def clear_scan_operation(
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Manually clear stuck scan operations.
    
    Marks all running/queued scanner jobs as cancelled.
    Use this endpoint when scans are stuck and preventing new scans.
    Admin only endpoint.
    """
    running_jobs = db.query(ScanJob).filter(
        ScanJob.scope == "scanner",
        ScanJob.status.in_(["running", "queued"])
    ).all()
    
    if not running_jobs:
        scan_operations.clear_operation()
        return {"success": True, "message": "No operation to clear"}
    
    cleared_count = 0
    for job in running_jobs:
        job.status = "error"
        job.error = "Manually cancelled by admin"
        job.finished_at = datetime.utcnow()
        cleared_count += 1
    
    db.commit()
    
    scan_operations.clear_operation()
    
    logger.info(
        f"Manually cleared {cleared_count} scan jobs",
        extra={
            "event": "clear_scan_operation",
            "cleared_count": cleared_count,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return {
        "success": True,
        "message": f"Cleared {cleared_count} running/queued scan job(s)",
        "cleared_count": cleared_count
    }


@router.post("/scanners/trigger-all", response_model=TriggerAllScannersResponse)
async def trigger_all_scanners(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Trigger all 11 event family scanners at once.
    
    This endpoint:
    - Starts all scanners in the background
    - Provides estimated duration based on scanner count
    - Tracks progress of each scanner
    - Sends a global notification when complete
    
    Admin only endpoint.
    """
    # Import scanner catalog
    try:
        from scanners.catalog import SCANNERS
    except ImportError:
        raise HTTPException(status_code=500, detail="Scanner catalog not available")
    
    # Get enabled scanners
    enabled_scanners = [s for s in SCANNERS if s.enabled]
    scanner_labels = [s.label for s in enabled_scanners]
    
    # Check if operation already in progress
    current_op = scan_operations.get_current_operation()
    if current_op and current_op["status"] == "running":
        raise HTTPException(
            status_code=409,
            detail="A scan operation is already in progress. Please wait for it to complete."
        )
    
    # Start the operation
    try:
        operation = scan_operations.start_operation(len(enabled_scanners), scanner_labels)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    
    # Queue background task to run all scanners
    background_tasks.add_task(run_all_scanners_task, enabled_scanners)
    
    logger.info(
        f"Triggered all {len(enabled_scanners)} scanners",
        extra={
            "event": "trigger_all_scanners",
            "operation_id": operation["id"],
            "scanner_count": len(enabled_scanners),
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    return TriggerAllScannersResponse(
        operation_id=operation["id"],
        status="running",
        total_scanners=len(enabled_scanners),
        estimated_duration_seconds=operation["estimated_duration_seconds"],
        message=f"Started scanning with all {len(enabled_scanners)} event family scanners. Estimated time: {operation['estimated_duration_seconds'] // 60} minutes."
    )


async def run_all_scanners_task(scanners):
    """Background task to run all scanners and track progress."""
    from database import SessionLocal
    from api.scheduler import run_scanner, SCANNER_FUNCTIONS
    
    total_events = 0
    
    for scanner in scanners:
        db = None
        try:
            # Update status to running
            scan_operations.update_scanner_result(scanner.label, "running")
            logger.info(f"Starting scanner: {scanner.label} (key={scanner.key}, fn={scanner.fn_name})")
            
            # Create a scan job for this scanner
            db = SessionLocal()
            job = ScanJob(
                created_by=None,  # System-triggered
                scope="scanner",
                scanner_key=scanner.key,
                status="running"
            )
            db.add(job)
            db.commit()
            db.refresh(job)
            job_id = job.id
            
            # Get the scanner function
            scanner_fn = SCANNER_FUNCTIONS.get(scanner.fn_name)
            if not scanner_fn:
                error_msg = f"Scanner function '{scanner.fn_name}' not found in SCANNER_FUNCTIONS"
                logger.error(error_msg)
                scan_operations.update_scanner_result(scanner.label, "error", 0, error_msg)
                job.status = "error"
                job.error = error_msg
                job.finished_at = datetime.utcnow()
                db.commit()
                continue
            
            # Run the scanner
            try:
                await run_scanner(
                    scanner_key=scanner.key,
                    scanner_fn=scanner_fn,
                    scanner_label=scanner.label,
                    scanner_interval=scanner.interval_minutes,
                    use_slow_pool=scanner.use_slow_pool
                )
                
                # Update job status
                job.status = "success"
                job.finished_at = datetime.utcnow()
                db.commit()
                
                # Get events found in last hour for this scanner
                cutoff = datetime.utcnow() - timedelta(hours=1)
                events_found = db.query(func.count(Event.id)).filter(
                    Event.source_scanner == scanner.key,
                    Event.created_at >= cutoff
                ).scalar() or 0
                
                total_events += events_found
                scan_operations.update_scanner_result(scanner.label, "success", events_found)
                logger.info(f"Scanner {scanner.label} completed: {events_found} events found")
                
            except asyncio.TimeoutError:
                error_msg = f"Scanner timed out after configured timeout"
                logger.error(f"Scanner {scanner.label} timed out")
                scan_operations.update_scanner_result(scanner.label, "error", 0, error_msg)
                job.status = "error"
                job.error = error_msg
                job.finished_at = datetime.utcnow()
                db.commit()
                
            except Exception as e:
                error_msg = str(e)[:500]
                logger.error(f"Scanner {scanner.label} failed: {e}", exc_info=True)
                scan_operations.update_scanner_result(scanner.label, "error", 0, error_msg)
                job.status = "error"
                job.error = error_msg
                job.finished_at = datetime.utcnow()
                db.commit()
                
        except Exception as e:
            logger.error(f"Failed to process scanner {scanner.label}: {e}", exc_info=True)
            scan_operations.update_scanner_result(scanner.label, "error", 0, str(e)[:200])
        finally:
            if db:
                db.close()
    
    # Complete the operation
    scan_operations.complete_operation(total_events)
    
    # Send global notification
    global_notifications.add_notification(
        message=f"Scanning complete! Found {total_events} new events. Reload to see updates.",
        notification_type="success",
        duration_seconds=300  # 5 minutes
    )
    
    logger.info(f"All {len(scanners)} scanners completed: {total_events} total events found")


@router.get("/scanners/list")
async def list_scanners(
    _: bool = Depends(verify_admin_key)
):
    """
    Get list of all available scanners with their configuration.
    """
    try:
        from scanners.catalog import SCANNERS
    except ImportError:
        raise HTTPException(status_code=500, detail="Scanner catalog not available")
    
    return {
        "scanners": [
            {
                "key": s.key,
                "label": s.label,
                "interval_minutes": s.interval_minutes,
                "enabled": s.enabled,
                "use_slow_pool": s.use_slow_pool,
                "estimated_duration_seconds": 30 if not s.use_slow_pool else 120
            }
            for s in SCANNERS
        ],
        "total": len(SCANNERS),
        "enabled_count": len([s for s in SCANNERS if s.enabled])
    }


# ============================================================================
# CHANGELOG MANAGEMENT
# ============================================================================

class ChangelogItemCreate(BaseModel):
    category: str
    description: str
    icon: Optional[str] = "CheckCircle2"
    sort_order: Optional[int] = 0


class ChangelogItemResponse(BaseModel):
    id: int
    category: str
    description: str
    icon: str
    sort_order: int
    
    class Config:
        from_attributes = True


class ChangelogReleaseCreate(BaseModel):
    version: str
    title: str
    release_date: str
    is_published: Optional[bool] = True
    items: Optional[List[ChangelogItemCreate]] = []


class ChangelogReleaseUpdate(BaseModel):
    version: Optional[str] = None
    title: Optional[str] = None
    release_date: Optional[str] = None
    is_published: Optional[bool] = None


class ChangelogReleaseResponse(BaseModel):
    id: int
    version: str
    title: str
    release_date: str
    is_published: bool
    items: List[ChangelogItemResponse]
    
    class Config:
        from_attributes = True


@router.get("/changelog")
async def list_changelog_releases(
    include_unpublished: bool = True,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Get all changelog releases for admin management.
    """
    query = db.query(ChangelogRelease).order_by(desc(ChangelogRelease.release_date))
    
    if not include_unpublished:
        query = query.filter(ChangelogRelease.is_published == True)
    
    releases = query.all()
    
    return {
        "releases": [
            {
                "id": r.id,
                "version": r.version,
                "title": r.title,
                "release_date": r.release_date.isoformat() if r.release_date else None,
                "is_published": r.is_published,
                "items": [
                    {
                        "id": item.id,
                        "category": item.category,
                        "description": item.description,
                        "icon": item.icon or "CheckCircle2",
                        "sort_order": item.sort_order or 0
                    }
                    for item in sorted(r.items, key=lambda x: x.sort_order or 0)
                ]
            }
            for r in releases
        ],
        "total": len(releases)
    }


@router.post("/changelog")
async def create_changelog_release(
    release: ChangelogReleaseCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Create a new changelog release with items.
    """
    from datetime import date
    
    existing = db.query(ChangelogRelease).filter(ChangelogRelease.version == release.version).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Version {release.version} already exists")
    
    release_date = date.fromisoformat(release.release_date)
    
    db_release = ChangelogRelease(
        version=release.version,
        title=release.title,
        release_date=release_date,
        is_published=release.is_published
    )
    db.add(db_release)
    db.flush()
    
    for idx, item in enumerate(release.items or []):
        db_item = ChangelogItem(
            release_id=db_release.id,
            category=item.category,
            description=item.description,
            icon=item.icon or "CheckCircle2",
            sort_order=item.sort_order if item.sort_order else idx
        )
        db.add(db_item)
    
    db.commit()
    db.refresh(db_release)
    
    return {
        "id": db_release.id,
        "version": db_release.version,
        "title": db_release.title,
        "release_date": db_release.release_date.isoformat(),
        "is_published": db_release.is_published,
        "items": [
            {
                "id": item.id,
                "category": item.category,
                "description": item.description,
                "icon": item.icon or "CheckCircle2",
                "sort_order": item.sort_order or 0
            }
            for item in db_release.items
        ]
    }


@router.put("/changelog/{release_id}")
async def update_changelog_release(
    release_id: int,
    release: ChangelogReleaseUpdate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Update an existing changelog release.
    """
    from datetime import date
    
    db_release = db.query(ChangelogRelease).filter(ChangelogRelease.id == release_id).first()
    if not db_release:
        raise HTTPException(status_code=404, detail="Release not found")
    
    if release.version is not None:
        existing = db.query(ChangelogRelease).filter(
            ChangelogRelease.version == release.version,
            ChangelogRelease.id != release_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Version {release.version} already exists")
        db_release.version = release.version
    
    if release.title is not None:
        db_release.title = release.title
    
    if release.release_date is not None:
        db_release.release_date = date.fromisoformat(release.release_date)
    
    if release.is_published is not None:
        db_release.is_published = release.is_published
    
    db.commit()
    db.refresh(db_release)
    
    return {
        "id": db_release.id,
        "version": db_release.version,
        "title": db_release.title,
        "release_date": db_release.release_date.isoformat(),
        "is_published": db_release.is_published
    }


@router.delete("/changelog/{release_id}")
async def delete_changelog_release(
    release_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Delete a changelog release and all its items.
    """
    db_release = db.query(ChangelogRelease).filter(ChangelogRelease.id == release_id).first()
    if not db_release:
        raise HTTPException(status_code=404, detail="Release not found")
    
    db.delete(db_release)
    db.commit()
    
    return {"success": True, "message": f"Release {db_release.version} deleted"}


@router.post("/changelog/{release_id}/items")
async def add_changelog_item(
    release_id: int,
    item: ChangelogItemCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Add an item to an existing changelog release.
    """
    db_release = db.query(ChangelogRelease).filter(ChangelogRelease.id == release_id).first()
    if not db_release:
        raise HTTPException(status_code=404, detail="Release not found")
    
    max_sort = db.query(func.max(ChangelogItem.sort_order)).filter(
        ChangelogItem.release_id == release_id
    ).scalar() or 0
    
    db_item = ChangelogItem(
        release_id=release_id,
        category=item.category,
        description=item.description,
        icon=item.icon or "CheckCircle2",
        sort_order=item.sort_order if item.sort_order else max_sort + 1
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    
    return {
        "id": db_item.id,
        "category": db_item.category,
        "description": db_item.description,
        "icon": db_item.icon,
        "sort_order": db_item.sort_order
    }


@router.put("/changelog/items/{item_id}")
async def update_changelog_item(
    item_id: int,
    item: ChangelogItemCreate,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Update an existing changelog item.
    """
    db_item = db.query(ChangelogItem).filter(ChangelogItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db_item.category = item.category
    db_item.description = item.description
    db_item.icon = item.icon or "CheckCircle2"
    if item.sort_order is not None:
        db_item.sort_order = item.sort_order
    
    db.commit()
    db.refresh(db_item)
    
    return {
        "id": db_item.id,
        "category": db_item.category,
        "description": db_item.description,
        "icon": db_item.icon,
        "sort_order": db_item.sort_order
    }


@router.delete("/changelog/items/{item_id}")
async def delete_changelog_item(
    item_id: int,
    db: Session = Depends(get_db),
    _: bool = Depends(verify_admin_key)
):
    """
    Delete a changelog item.
    """
    db_item = db.query(ChangelogItem).filter(ChangelogItem.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    db.delete(db_item)
    db.commit()
    
    return {"success": True, "message": "Item deleted"}
