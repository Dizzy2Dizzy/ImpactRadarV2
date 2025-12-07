"""Impact scoring router"""
from fastapi import APIRouter, Depends, Request, Header
from typing import Optional

from api.schemas.events import ImpactScoreRequest, ImpactScoreResponse
from api.utils.api_key import require_api_key
from impact_scoring import ImpactScorer

router = APIRouter(prefix="/impact", tags=["impact-scoring"])

# Import limiter and plan_limit from ratelimit module
from api.ratelimit import limiter, plan_limit


@router.post("/score", response_model=ImpactScoreResponse)
@limiter.limit(plan_limit)
async def score_event(
    request: ImpactScoreRequest,
    req: Request = None,
    x_api_key: Optional[str] = Header(None),
    _key = Depends(require_api_key)
):
    """Score an event's market impact (requires Pro or Team plan)"""
    score, direction, confidence, rationale = ImpactScorer.score_event(
        event_type=request.event_type,
        title=request.title,
        description=request.description,
        sector=request.sector,
        market_cap=request.market_cap,
        metadata=request.metadata or {}
    )
    
    return ImpactScoreResponse(
        impact_score=score,
        direction=direction,
        confidence=confidence,
        rationale=rationale
    )
