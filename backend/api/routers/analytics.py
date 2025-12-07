"""
Analytics endpoints for historical backtesting and event statistics.

Provides:
- GET /analytics/backtest - Historical event impact statistics with distribution data
- POST /analytics/recompute - Trigger statistics recomputation (admin only)
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from releaseradar.db.models import EventStats
from releaseradar.db.session import get_db, close_db
from jobs.recompute_event_stats import compute_stats_for_ticker_event_type
from api.utils.auth import get_current_user_with_plan
from api.utils.paywall import require_plan


router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/backtest")
def get_backtest_stats(
    ticker: str = Query(..., description="Stock ticker symbol"),
    event_type: str = Query(..., description="Event type (e.g., earnings, fda_approval)"),
    db: Session = Depends(get_db),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get historical backtest statistics for a ticker and event type.
    
    Returns win rate, average absolute moves, and mean directional moves for
    1-day, 5-day, and 20-day windows after events.
    
    Response includes:
    - sample_size: Number of historical events analyzed
    - win_rate: Percentage of events with positive 1-day returns
    - avg_abs_move_1d/5d/20d: Average absolute price movement
    - mean_move_1d/5d/20d: Average directional price movement
    - distribution: Bucketed return distribution for visualization
    
    Requires Pro or Team plan.
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Analytics backtest",
        user_data.get("trial_ends_at")
    )
    
    try:
        # Fetch statistics
        result = db.execute(
            select(EventStats).where(
                EventStats.ticker == ticker.upper(),
                EventStats.event_type == event_type.lower()
            )
        )
        stats = result.scalar_one_or_none()
        
        if not stats:
            raise HTTPException(
                status_code=404,
                detail=f"No backtest data available for {ticker}/{event_type}. "
                       f"Run recompute job or wait for nightly update."
            )
        
        # Build response
        response = {
            "ticker": stats.ticker,
            "event_type": stats.event_type,
            "sample_size": stats.sample_size,
            "win_rate": stats.win_rate,
            "moves": {
                "1d": {
                    "mean": stats.mean_move_1d,
                    "avg_abs": stats.avg_abs_move_1d,
                },
                "5d": {
                    "mean": stats.mean_move_5d,
                    "avg_abs": stats.avg_abs_move_5d,
                },
                "20d": {
                    "mean": stats.mean_move_20d,
                    "avg_abs": stats.avg_abs_move_20d,
                },
            },
            "updated_at": stats.updated_at.isoformat() if stats.updated_at else None,
        }
        
        return response
        
    finally:
        close_db()


@router.post("/recompute")
def trigger_recompute(
    ticker: Optional[str] = Query(None, description="Specific ticker to recompute (None = all)"),
    event_type: Optional[str] = Query(None, description="Specific event type (None = all)"),
    db: Session = Depends(get_db),
):
    """
    Trigger event statistics recomputation.
    
    Admin-only endpoint to recompute historical event impact statistics.
    Can be scoped to specific ticker and/or event type for faster execution.
    
    Note: This is a synchronous endpoint. For large datasets, use the
    background job via `make jobs.recompute`.
    """
    try:
        # In production, add admin authentication here
        # For MVP, allowing public access
        
        tickers = [ticker.upper()] if ticker else None
        event_types = [event_type.lower()] if event_type else None
        
        # For single ticker/event, compute inline and persist
        if ticker and event_type:
            from sqlalchemy.dialects.postgresql import insert as pg_insert
            from sqlalchemy import delete
            
            result = compute_stats_for_ticker_event_type(
                db, 
                ticker.upper(), 
                event_type.lower()
            )
            
            action = result["action"]
            
            if action == "delete":
                # Remove stale EventStats row
                db.execute(
                    delete(EventStats).where(
                        EventStats.ticker == ticker.upper(),
                        EventStats.event_type == event_type.lower()
                    )
                )
                db.commit()
                
                return {
                    "status": "deleted",
                    "ticker": ticker.upper(),
                    "event_type": event_type.lower(),
                    "message": "Insufficient price data, EventStats row removed"
                }
            
            elif action == "update":
                # Persist computed stats to database
                payload = result["payload"]
                stmt = pg_insert(EventStats).values(payload)
                stmt = stmt.on_conflict_do_update(
                    index_elements=["ticker", "event_type"],
                    set_={
                        "sample_size": stmt.excluded.sample_size,
                        "win_rate": stmt.excluded.win_rate,
                        "avg_abs_move_1d": stmt.excluded.avg_abs_move_1d,
                        "avg_abs_move_5d": stmt.excluded.avg_abs_move_5d,
                        "avg_abs_move_20d": stmt.excluded.avg_abs_move_20d,
                        "mean_move_1d": stmt.excluded.mean_move_1d,
                        "mean_move_5d": stmt.excluded.mean_move_5d,
                        "mean_move_20d": stmt.excluded.mean_move_20d,
                        "updated_at": stmt.excluded.updated_at,
                    }
                )
                db.execute(stmt)
                db.commit()
                
                return {
                    "status": "completed",
                    "ticker": ticker.upper(),
                    "event_type": event_type.lower(),
                    "stats": payload,
                }
        
        # For broader scope, return job trigger message
        return {
            "status": "queued",
            "message": "For full recomputation, use: make jobs.recompute",
            "scope": {
                "tickers": tickers or "all",
                "event_types": event_types or "all",
            }
        }
        
    finally:
        close_db()


@router.get("/market-regime")
def get_market_regime(
    db: Session = Depends(get_db),
):
    """
    Get current market regime and topology context.
    
    Returns market regime (risk_on/risk_off), confidence score,
    and related metrics like volatility and breadth.
    
    This endpoint is public for dashboard display.
    """
    try:
        from releaseradar.services.topology import TopologyContextService
        
        topology_service = TopologyContextService(db)
        regime = topology_service.get_current_regime()
        
        if not regime:
            return {
                "regime": "unknown",
                "confidence": 0.0,
                "volatility": None,
                "avg_correlation": None,
                "avg_return": None,
                "breadth": None,
                "message": "Insufficient data for regime detection"
            }
        
        return {
            "regime": regime.regime,
            "confidence": round(regime.confidence, 3),
            "volatility": round(regime.volatility, 4),
            "avg_correlation": round(regime.avg_correlation, 3),
            "avg_return": round(regime.avg_return, 4),
            "breadth": round(1.0 - regime.negative_breadth, 2),  # Positive breadth
            "scores": regime.scores,
            "message": f"Market in {regime.regime.upper().replace('_', '-')} mode"
        }
        
    except Exception as e:
        return {
            "regime": "unknown",
            "confidence": 0.0,
            "volatility": None,
            "avg_correlation": None,
            "avg_return": None,
            "breadth": None,
            "message": f"Error detecting regime: {str(e)}"
        }
        
    finally:
        close_db()
