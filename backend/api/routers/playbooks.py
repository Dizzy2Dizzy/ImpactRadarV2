"""
Playbooks API Router - CRUD and matching endpoints for trading playbooks.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from typing import Optional, Any
from datetime import datetime

from api.utils.auth import get_current_user, get_user_plan, get_current_user_id
from database import get_db, close_db_session
from releaseradar.services.playbook_service import PlaybookService, PlaybookMatchingService

router = APIRouter(prefix="/playbooks", tags=["playbooks"])


def check_plan_access(plan: str, required_plans: list[str]) -> bool:
    """Check if user plan has access."""
    return plan.lower() in [p.lower() for p in required_plans]


class PlaybookRuleCreate(BaseModel):
    rule_type: str = Field(..., description="Type of rule: event_type, keyword, score_range, sector, direction")
    operator: str = Field(default="eq", description="Comparison operator")
    value: Any = Field(..., description="Value to compare against")
    is_required: bool = Field(default=True)
    weight: float = Field(default=1.0)


class PlaybookScreenshotCreate(BaseModel):
    image_url: Optional[str] = None
    caption: Optional[str] = None
    event_ref: Optional[int] = None


class PlaybookCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=100)
    title: str = Field(..., min_length=2, max_length=200)
    category: str = Field(..., description="Category: earnings, fda, sec, corporate")
    description: Optional[str] = None
    setup_conditions: dict = Field(default_factory=dict)
    entry_logic: str = Field(..., min_length=10)
    stop_template: Optional[str] = None
    target_template: Optional[str] = None
    holding_period: Optional[str] = None
    win_rate: Optional[float] = Field(default=None, ge=0, le=1)
    avg_r: Optional[float] = None
    sample_size: Optional[int] = Field(default=0, ge=0)
    stats_metadata: Optional[dict] = None
    display_order: int = Field(default=0)
    is_active: bool = Field(default=True)
    is_featured: bool = Field(default=False)
    visibility: str = Field(default="public")
    rules: list[PlaybookRuleCreate] = Field(default_factory=list)
    screenshots: list[PlaybookScreenshotCreate] = Field(default_factory=list)


class PlaybookUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    description: Optional[str] = None
    setup_conditions: Optional[dict] = None
    entry_logic: Optional[str] = None
    stop_template: Optional[str] = None
    target_template: Optional[str] = None
    holding_period: Optional[str] = None
    win_rate: Optional[float] = None
    avg_r: Optional[float] = None
    sample_size: Optional[int] = None
    stats_metadata: Optional[dict] = None
    display_order: Optional[int] = None
    is_active: Optional[bool] = None
    is_featured: Optional[bool] = None
    visibility: Optional[str] = None


class ScreenshotAdd(BaseModel):
    slot_index: int = Field(..., ge=0, le=2)
    image_url: str
    caption: Optional[str] = None
    event_ref: Optional[int] = None


@router.get("")
async def list_playbooks(
    category: Optional[str] = None,
    is_active: bool = True,
    visibility: Optional[str] = None,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """List all playbooks with optional filters."""
    session = get_db()
    try:
        service = PlaybookService(session)
        playbooks = service.get_all_playbooks(
            category=category,
            is_active=is_active,
            visibility=visibility,
            limit=limit,
            offset=offset,
        )
        return playbooks
    finally:
        close_db_session(session)


@router.get("/categories")
async def get_categories():
    """Get all unique playbook categories."""
    session = get_db()
    try:
        service = PlaybookService(session)
        return {"categories": service.get_playbook_categories()}
    finally:
        close_db_session(session)


@router.get("/{playbook_id_or_slug}")
async def get_playbook(playbook_id_or_slug: str):
    """Get a single playbook by ID or slug."""
    session = get_db()
    try:
        service = PlaybookService(session)

        if playbook_id_or_slug.isdigit():
            playbook = service.get_playbook_by_id(int(playbook_id_or_slug))
        else:
            playbook = service.get_playbook_by_slug(playbook_id_or_slug)

        if not playbook:
            raise HTTPException(status_code=404, detail="Playbook not found")
        return playbook
    finally:
        close_db_session(session)


@router.get("/{playbook_id}/matches")
async def get_playbook_matches(
    playbook_id: int,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
):
    """Get events that match a specific playbook."""
    session = get_db()
    try:
        matching_service = PlaybookMatchingService(session)
        matches = matching_service.get_playbook_matched_events(
            playbook_id=playbook_id,
            limit=limit,
            offset=offset,
        )
        return matches
    finally:
        close_db_session(session)


@router.post("")
async def create_playbook(
    data: PlaybookCreate,
    user_id: int = Depends(get_current_user_id),
    plan: str = Depends(get_user_plan),
):
    """Create a new playbook (Team/Admin only)."""
    if not check_plan_access(plan, ["team", "admin"]):
        raise HTTPException(status_code=403, detail="This feature requires Team or Admin plan")

    session = get_db()
    try:
        service = PlaybookService(session)

        existing = service.get_playbook_by_slug(data.slug)
        if existing:
            raise HTTPException(status_code=400, detail="Playbook with this slug already exists")

        playbook_data = data.model_dump()
        playbook_data["author_id"] = user_id
        playbook_data["rules"] = [r.model_dump() for r in data.rules]
        playbook_data["screenshots"] = [s.model_dump() for s in data.screenshots]

        playbook = service.create_playbook(playbook_data)
        return playbook
    finally:
        close_db_session(session)


@router.patch("/{playbook_id}")
async def update_playbook(
    playbook_id: int,
    data: PlaybookUpdate,
    user_id: int = Depends(get_current_user_id),
    plan: str = Depends(get_user_plan),
):
    """Update a playbook (Team/Admin only)."""
    if not check_plan_access(plan, ["team", "admin"]):
        raise HTTPException(status_code=403, detail="This feature requires Team or Admin plan")

    session = get_db()
    try:
        service = PlaybookService(session)
        update_data = data.model_dump(exclude_unset=True)

        playbook = service.update_playbook(playbook_id, update_data)
        if not playbook:
            raise HTTPException(status_code=404, detail="Playbook not found")
        return playbook
    finally:
        close_db_session(session)


@router.delete("/{playbook_id}")
async def delete_playbook(
    playbook_id: int,
    user_id: int = Depends(get_current_user_id),
    plan: str = Depends(get_user_plan),
):
    """Delete a playbook (Admin only)."""
    if not check_plan_access(plan, ["admin"]):
        raise HTTPException(status_code=403, detail="This feature requires Admin access")

    session = get_db()
    try:
        service = PlaybookService(session)
        success = service.delete_playbook(playbook_id)
        if not success:
            raise HTTPException(status_code=404, detail="Playbook not found")
        return {"message": "Playbook deleted successfully"}
    finally:
        close_db_session(session)


@router.post("/{playbook_id}/screenshots")
async def add_screenshot(
    playbook_id: int,
    data: ScreenshotAdd,
    user_id: int = Depends(get_current_user_id),
    plan: str = Depends(get_user_plan),
):
    """Add or update a screenshot slot (Team/Admin only)."""
    if not check_plan_access(plan, ["team", "admin"]):
        raise HTTPException(status_code=403, detail="This feature requires Team or Admin plan")

    session = get_db()
    try:
        service = PlaybookService(session)
        playbook = service.add_screenshot(
            playbook_id=playbook_id,
            slot_index=data.slot_index,
            image_url=data.image_url,
            caption=data.caption,
            event_ref=data.event_ref,
        )
        if not playbook:
            raise HTTPException(status_code=404, detail="Playbook not found")
        return playbook
    finally:
        close_db_session(session)


@router.post("/match-event/{event_id}")
async def match_event_to_playbooks(
    event_id: int,
    min_confidence: float = Query(default=0.5, ge=0, le=1),
    save: bool = Query(default=True),
    user_id: int = Depends(get_current_user_id),
):
    """Match a specific event to all applicable playbooks."""
    from releaseradar.db.models import Event as EventModel

    session = get_db()
    try:
        event = session.query(EventModel).filter(EventModel.id == event_id).first()
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")

        matching_service = PlaybookMatchingService(session)
        matches = matching_service.match_event_to_playbooks(event, min_confidence)

        if save and matches:
            matching_service.save_event_matches(event_id, matches)

        return {"event_id": event_id, "matches": matches}
    finally:
        close_db_session(session)


@router.post("/batch-match")
async def batch_match_events(
    event_ids: list[int],
    min_confidence: float = Query(default=0.5, ge=0, le=1),
    user_id: int = Depends(get_current_user_id),
    plan: str = Depends(get_user_plan),
):
    """Batch match multiple events to playbooks (Team/Admin only)."""
    if not check_plan_access(plan, ["team", "admin"]):
        raise HTTPException(status_code=403, detail="This feature requires Team or Admin plan")

    session = get_db()
    try:
        matching_service = PlaybookMatchingService(session)
        results = matching_service.batch_match_events(event_ids, min_confidence)
        return results
    finally:
        close_db_session(session)


@router.get("/event/{event_id}/playbooks")
async def get_event_playbooks(event_id: int):
    """Get all playbooks that match a specific event."""
    session = get_db()
    try:
        matching_service = PlaybookMatchingService(session)
        matches = matching_service.get_event_playbook_matches(event_id)
        return matches
    finally:
        close_db_session(session)
