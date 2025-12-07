"""
Public changelog API endpoint.
"""
from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from api.dependencies import get_db
from releaseradar.db.models import ChangelogRelease

router = APIRouter(prefix="/changelog", tags=["changelog"])


@router.get("")
async def get_public_changelog(
    db: Session = Depends(get_db)
):
    """
    Get all published changelog releases for public display.
    """
    releases = db.query(ChangelogRelease).filter(
        ChangelogRelease.is_published == True
    ).order_by(desc(ChangelogRelease.release_date)).all()
    
    return {
        "releases": [
            {
                "id": r.id,
                "version": r.version,
                "title": r.title,
                "release_date": r.release_date.isoformat() if r.release_date is not None else None,
                "items": [
                    {
                        "id": item.id,
                        "category": item.category,
                        "description": item.description,
                        "icon": item.icon or "CheckCircle2"
                    }
                    for item in sorted(r.items, key=lambda x: x.sort_order or 0)
                ]
            }
            for r in releases
        ]
    }
