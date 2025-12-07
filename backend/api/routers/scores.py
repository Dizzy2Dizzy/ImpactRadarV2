"""
API endpoints for event scoring (Wave B).

Provides access to computed event scores with caching for performance.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response, Request
from pydantic import BaseModel
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from releaseradar.db.models import Event, EventScore
from api.dependencies import get_db
from jobs.compute_event_scores import compute_scores_for_event, recompute_all_scores, get_market_data_service
from api.utils.metrics import increment_metric, set_cache_size_getter
from api.utils.auth import require_admin, get_user_plan
from api.ratelimit import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scores", tags=["scores"])

# Simple in-memory cache (60s TTL)
_CACHE = {}
_CACHE_TTL = 60  # seconds

# Register cache size getter for metrics
set_cache_size_getter(lambda: len(_CACHE))


class FactorsBreakdown(BaseModel):
    """Individual factor contributions to the score."""
    sector: int = 0
    volatility: int = 0
    earnings_proximity: int = 0
    market_mood: int = 0
    after_hours: int = 0
    duplicate_penalty: int = 0


class EventScoreResponse(BaseModel):
    """Event score response model."""
    event_id: int
    ticker: str
    event_type: str
    base_score: int
    context_score: int
    final_score: int
    confidence: int
    factors: FactorsBreakdown
    rationale: List[str]
    computed_at: datetime
    beta: Optional[float] = None
    atr_percentile: Optional[float] = None
    market_regime: Optional[str] = None
    
    class Config:
        from_attributes = True


def _get_from_cache(key: str) -> Optional[dict]:
    """Get item from cache if not expired."""
    if key in _CACHE:
        entry = _CACHE[key]
        if datetime.utcnow() < entry["expires_at"]:
            return entry["data"]
        else:
            del _CACHE[key]
    return None


def _set_cache(key: str, data, ttl: int = _CACHE_TTL):
    """Set item in cache with TTL."""
    _CACHE[key] = {
        "data": data,
        "expires_at": datetime.utcnow() + timedelta(seconds=ttl)
    }


def _generate_etag(data) -> str:
    """Generate ETag hash from response data."""
    content = json.dumps(data, sort_keys=True, default=str)
    return hashlib.md5(content.encode()).hexdigest()


def _score_to_factors(score: EventScore) -> FactorsBreakdown:
    """Convert EventScore model to FactorsBreakdown."""
    return FactorsBreakdown(
        sector=score.factor_sector,
        volatility=score.factor_volatility,
        earnings_proximity=score.factor_earnings_proximity,
        market_mood=score.factor_market_mood,
        after_hours=score.factor_after_hours,
        duplicate_penalty=score.factor_duplicate_penalty
    )


@router.get("/events/{event_id}", response_model=EventScoreResponse)
async def get_event_score(
    event_id: int,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    plan: str = Depends(get_user_plan)
):
    """
    Get score for a specific event by ID.
    
    Cached for 60 seconds to optimize performance.
    Target: <200ms warm response.
    """
    # Check plan access - Free users get 402
    if plan == "free":
        increment_metric("scores_denied_free_total")
        raise HTTPException(
            status_code=402,
            detail={"error": "UPGRADE_REQUIRED", "feature": "scores"}
        )
    
    increment_metric("scores_served_total")
    cache_key = f"event_score_{event_id}"
    
    # Check cache
    cached = _get_from_cache(cache_key)
    if cached:
        # Set ETag headers even on cache hits
        etag = _generate_etag(cached)
        response.headers["ETag"] = f'"{etag}"'
        response.headers["Cache-Control"] = f"max-age={_CACHE_TTL}"
        
        # Check if client has valid ETag (conditional GET)
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match.strip('"') == etag:
            increment_metric("score_cache_hits_total")
            # Return proper 304 Response with headers
            return Response(status_code=304, headers=response.headers)
        
        # Cache hit but different ETag - return cached data
        increment_metric("score_cache_hits_total")
        return cached
    
    increment_metric("score_cache_misses_total")
    
    # Fetch from database
    score = db.execute(
        select(EventScore).where(EventScore.event_id == event_id)
    ).scalar_one_or_none()
    
    if not score:
        # Score not computed yet - compute on demand
        event = db.execute(
            select(Event).where(Event.id == event_id)
        ).scalar_one_or_none()
        
        if not event:
            raise HTTPException(status_code=404, detail="Event not found")
        
        score = compute_scores_for_event(db, event)
        if not score:
            raise HTTPException(status_code=500, detail="Failed to compute score")
        
        db.commit()
    
    # Fetch current market data for context (cached 24h)
    market_service = get_market_data_service()
    beta = market_service.get_beta(score.ticker)
    atr_percentile = market_service.get_atr_percentile(score.ticker)
    spy_returns = market_service.get_spy_returns()
    market_regime = market_service.get_market_regime(spy_returns) if spy_returns else None
    
    # Convert to response
    rationale_list = score.rationale.split("\n") if score.rationale else []
    factors = _score_to_factors(score)
    response_data = {
        "event_id": score.event_id,
        "ticker": score.ticker,
        "event_type": score.event_type,
        "base_score": score.base_score,
        "context_score": score.context_score,
        "final_score": score.final_score,
        "confidence": score.confidence,
        "factors": factors.model_dump(),
        "rationale": rationale_list,
        "computed_at": score.computed_at,
        "beta": beta,
        "atr_percentile": atr_percentile,
        "market_regime": market_regime
    }
    
    # Cache response
    _set_cache(cache_key, response_data)
    
    # Generate and set ETag
    etag = _generate_etag(response_data)
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Cache-Control"] = f"max-age={_CACHE_TTL}"
    
    # Check if client has valid ETag
    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match.strip('"') == etag:
        response.status_code = 304
        return None
    
    return response_data


@router.get("/", response_model=List[EventScoreResponse])
async def get_event_scores(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    ticker: Optional[str] = Query(None, description="Filter by ticker"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of scores to return"),
    plan: str = Depends(get_user_plan)
):
    """
    Get recent event scores with optional ticker filter.
    
    Cached for 60 seconds per query combination.
    """
    # Check plan access - Free users get 402
    if plan == "free":
        increment_metric("scores_denied_free_total")
        raise HTTPException(
            status_code=402,
            detail={"error": "UPGRADE_REQUIRED", "feature": "scores"}
        )
    
    increment_metric("scores_served_total")
    cache_key = f"event_scores_{ticker}_{limit}"
    
    # Check cache
    cached = _get_from_cache(cache_key)
    if cached:
        increment_metric("score_cache_hits_total")
        # Set ETag headers even on cache hits
        etag = _generate_etag({"items": cached})
        response.headers["ETag"] = f'"{etag}"'
        response.headers["Cache-Control"] = f"max-age={_CACHE_TTL}"
        
        # Check if client has valid ETag
        if_none_match = request.headers.get("if-none-match")
        if if_none_match and if_none_match.strip('"') == etag:
            response.status_code = 304
            return None
        
        return cached
    
    increment_metric("score_cache_misses_total")
    
    # Build query
    query = select(EventScore).order_by(desc(EventScore.computed_at)).limit(limit)
    
    if ticker:
        query = query.where(EventScore.ticker == ticker)
    
    scores = db.execute(query).scalars().all()
    
    # Fetch market data (reused for all tickers due to caching)
    market_service = get_market_data_service()
    spy_returns = market_service.get_spy_returns()
    market_regime = market_service.get_market_regime(spy_returns) if spy_returns else None
    
    # Convert to response
    response_data = []
    for score in scores:
        # Fetch ticker-specific market data (cached 24h)
        beta = market_service.get_beta(score.ticker)
        atr_percentile = market_service.get_atr_percentile(score.ticker)
        
        rationale_list = score.rationale.split("\n") if score.rationale else []
        factors = _score_to_factors(score)
        response_data.append({
            "event_id": score.event_id,
            "ticker": score.ticker,
            "event_type": score.event_type,
            "base_score": score.base_score,
            "context_score": score.context_score,
            "final_score": score.final_score,
            "confidence": score.confidence,
            "factors": factors.model_dump(),
            "rationale": rationale_list,
            "computed_at": score.computed_at,
            "beta": beta,
            "atr_percentile": atr_percentile,
            "market_regime": market_regime
        })
    
    # Cache and generate ETag for list response (60s TTL per Wave B spec)
    _set_cache(cache_key, response_data, ttl=_CACHE_TTL)
    
    # Generate ETag from list data
    etag = _generate_etag({"items": response_data})
    response.headers["ETag"] = f'"{etag}"'
    response.headers["Cache-Control"] = f"max-age={_CACHE_TTL}"
    
    # Check if client has valid ETag (even on cache miss)
    if_none_match = request.headers.get("if-none-match")
    if if_none_match and if_none_match.strip('"') == etag:
        response.status_code = 304
        return None
    
    return response_data


class RescoreResponse(BaseModel):
    """Response model for rescore endpoint."""
    message: str
    events_processed: int
    

@router.post("/rescore", response_model=RescoreResponse)
@limiter.limit("30/minute")
async def rescore_events(
    request: Request,
    ticker: Optional[str] = Query(None, description="Filter by ticker (optional)"),
    limit: Optional[int] = Query(None, ge=1, le=10000, description="Maximum events to process"),
    force: bool = Query(False, description="Force recompute even if score exists"),
    db: Session = Depends(get_db),
    admin_user = Depends(require_admin)
):
    """
    Recompute event scores for all events (or filtered subset).
    
    Admin-only endpoint for batch recomputation. Processes in batches for efficiency.
    Rate limited to 30 requests per minute to prevent abuse.
    
    Note: This is a long-running operation. Consider using async task queue in production.
    """
    # Log requester
    logger.info(
        f"Rescore requested by admin user_id={admin_user.user_id} email={admin_user.email} "
        f"ticker={ticker} limit={limit} force={force}"
    )
    
    increment_metric("rescore_requests_total")
    
    try:
        count = recompute_all_scores(
            db=db,
            ticker=ticker,
            limit=limit,
            force=force
        )
        
        # Track scored events
        increment_metric("scored_events_total", count)
        
        # Clear cache after rescore
        _CACHE.clear()
        
        return {
            "message": f"Successfully recomputed scores",
            "events_processed": count
        }
        
    except Exception as e:
        increment_metric("rescore_errors_total")
        logger.error(f"Rescore failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Rescore failed: {str(e)}")
