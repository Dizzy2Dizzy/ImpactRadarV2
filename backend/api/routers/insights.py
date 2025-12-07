"""
Insights API Router - Daily/weekly digest generation and delivery endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime

from api.utils.auth import get_current_user, get_user_plan, get_current_user_id
from database import get_db, close_db_session
from releaseradar.services.insight_digest_service import InsightDigestGenerator

router = APIRouter(prefix="/insights", tags=["insights"])


def check_plan_access(plan: str, required_plans: list[str]) -> bool:
    """Check if user plan has access."""
    return plan.lower() in [p.lower() for p in required_plans]


class GenerateDigestRequest(BaseModel):
    cadence: str = Field(..., pattern="^(daily|weekly)$")
    target_date: Optional[str] = Field(default=None, description="Target date in YYYY-MM-DD format")


class SendDigestRequest(BaseModel):
    digest_id: int
    test_email: Optional[str] = Field(default=None, description="Send to specific test email instead of subscribers")


@router.get("/latest")
async def get_latest_digest(
    cadence: str = Query(default="daily", pattern="^(daily|weekly)$"),
    user_id: int = Depends(get_current_user_id),
):
    """Get the most recent digest of the specified cadence."""
    session = get_db()
    try:
        service = InsightDigestGenerator(session)
        digest = service.get_latest_digest(cadence)
        if not digest:
            return {"message": f"No {cadence} digest found", "digest": None}
        return digest
    finally:
        close_db_session(session)


@router.get("")
async def list_digests(
    cadence: Optional[str] = Query(default=None, pattern="^(daily|weekly)$"),
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    user_id: int = Depends(get_current_user_id),
):
    """List all digests with optional filtering."""
    session = get_db()
    try:
        service = InsightDigestGenerator(session)
        digests = service.list_digests(cadence=cadence, limit=limit, offset=offset)
        return {"digests": digests, "count": len(digests)}
    finally:
        close_db_session(session)


@router.get("/{digest_id}")
async def get_digest(
    digest_id: int,
    user_id: int = Depends(get_current_user_id),
):
    """Get a specific digest by ID."""
    session = get_db()
    try:
        service = InsightDigestGenerator(session)
        digest = service.get_digest_by_id(digest_id)
        if not digest:
            raise HTTPException(status_code=404, detail="Digest not found")
        return digest
    finally:
        close_db_session(session)


@router.post("/generate")
async def generate_digest(
    data: GenerateDigestRequest,
    user_id: int = Depends(get_current_user_id),
    plan: str = Depends(get_user_plan),
):
    """Generate a new insight digest (Team/Admin only)."""
    if not check_plan_access(plan, ["team", "admin"]):
        raise HTTPException(status_code=403, detail="This feature requires Team or Admin plan")

    session = get_db()
    try:
        service = InsightDigestGenerator(session)

        target_date = None
        if data.target_date:
            try:
                target_date = date.fromisoformat(data.target_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        if data.cadence == "daily":
            digest = service.generate_daily_digest(target_date)
        else:
            digest = service.generate_weekly_digest(target_date)

        return digest
    finally:
        close_db_session(session)


@router.post("/send/{digest_id}")
async def send_digest(
    digest_id: int,
    background_tasks: BackgroundTasks,
    test_email: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
    plan: str = Depends(get_user_plan),
):
    """Send a digest to subscribers or test email (Team/Admin only)."""
    if not check_plan_access(plan, ["team", "admin"]):
        raise HTTPException(status_code=403, detail="This feature requires Team or Admin plan")

    session = get_db()
    try:
        service = InsightDigestGenerator(session)
        digest = service.get_digest_by_id(digest_id)

        if not digest:
            raise HTTPException(status_code=404, detail="Digest not found")

        if digest["status"] == "sent" and not test_email:
            raise HTTPException(status_code=400, detail="Digest has already been sent")

        background_tasks.add_task(
            _send_digest_emails,
            digest_id=digest_id,
            cadence=digest["cadence"],
            test_email=test_email,
        )

        return {
            "message": "Digest sending initiated",
            "digest_id": digest_id,
            "test_mode": test_email is not None,
        }
    finally:
        close_db_session(session)


@router.get("/subscribers/{cadence}")
async def get_subscribers(
    cadence: str,
    user_id: int = Depends(get_current_user_id),
    plan: str = Depends(get_user_plan),
):
    """Get all subscribers for a digest cadence (Admin only)."""
    if not check_plan_access(plan, ["admin"]):
        raise HTTPException(status_code=403, detail="This feature requires Admin access")

    if cadence not in ["daily", "weekly"]:
        raise HTTPException(status_code=400, detail="Invalid cadence. Use 'daily' or 'weekly'")

    session = get_db()
    try:
        service = InsightDigestGenerator(session)
        subscribers = service.get_subscribers(cadence)
        return {"cadence": cadence, "subscribers": subscribers, "count": len(subscribers)}
    finally:
        close_db_session(session)


@router.post("/generate-and-send")
async def generate_and_send(
    data: GenerateDigestRequest,
    background_tasks: BackgroundTasks,
    user_id: int = Depends(get_current_user_id),
    plan: str = Depends(get_user_plan),
):
    """Generate and immediately queue sending a digest (Admin only)."""
    if not check_plan_access(plan, ["admin"]):
        raise HTTPException(status_code=403, detail="This feature requires Admin access")

    session = get_db()
    try:
        service = InsightDigestGenerator(session)

        target_date = None
        if data.target_date:
            try:
                target_date = date.fromisoformat(data.target_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD")

        if data.cadence == "daily":
            digest = service.generate_daily_digest(target_date)
        else:
            digest = service.generate_weekly_digest(target_date)

        background_tasks.add_task(
            _send_digest_emails,
            digest_id=digest["id"],
            cadence=data.cadence,
            test_email=None,
        )

        return {
            "message": "Digest generated and sending initiated",
            "digest": digest,
        }
    finally:
        close_db_session(session)


@router.get("/preview/{cadence}")
async def preview_digest(
    cadence: str,
    target_date: Optional[str] = None,
    user_id: int = Depends(get_current_user_id),
):
    """Preview what a digest would look like without saving it."""
    if cadence not in ["daily", "weekly"]:
        raise HTTPException(status_code=400, detail="Invalid cadence")

    session = get_db()
    try:
        service = InsightDigestGenerator(session)

        date_obj = None
        if target_date:
            try:
                date_obj = date.fromisoformat(target_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format")

        if cadence == "daily":
            digest = service.generate_daily_digest(date_obj)
        else:
            digest = service.generate_weekly_digest(date_obj)

        return {
            "preview": True,
            "digest": digest,
        }
    finally:
        close_db_session(session)


async def _send_digest_emails(digest_id: int, cadence: str, test_email: Optional[str] = None):
    """Background task to send digest emails."""
    session = get_db()
    try:
        from releaseradar.services.insight_digest_service import InsightDigestGenerator

        service = InsightDigestGenerator(session)
        digest = service.get_digest_by_id(digest_id)

        if not digest:
            return

        if test_email:
            _send_single_email(
                to_email=test_email,
                subject=digest["subject"],
                html_body=digest["html_body"],
                text_body=digest["text_body"],
            )
            return

        subscribers = service.get_subscribers(cadence)
        sent_count = 0

        for sub in subscribers:
            if sub.get("email"):
                try:
                    _send_single_email(
                        to_email=sub["email"],
                        subject=digest["subject"],
                        html_body=digest["html_body"],
                        text_body=digest["text_body"],
                    )
                    sent_count += 1
                except Exception as e:
                    print(f"Failed to send digest to {sub['email']}: {e}")

        service.mark_digest_sent(digest_id, sent_count)

    finally:
        close_db_session(session)


def _send_single_email(to_email: str, subject: str, html_body: str, text_body: str):
    """Send a single email using Resend."""
    import os
    try:
        import resend

        resend.api_key = os.environ.get("RESEND_API_KEY")
        if not resend.api_key:
            print(f"RESEND_API_KEY not set, skipping email to {to_email}")
            return

        resend.Emails.send({
            "from": "Impact Radar <insights@impactradar.com>",
            "to": to_email,
            "subject": subject,
            "html": html_body,
            "text": text_body,
        })
    except Exception as e:
        print(f"Failed to send email: {e}")
        raise
