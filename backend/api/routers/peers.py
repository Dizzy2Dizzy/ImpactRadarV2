"""Peer Comparison router - Find and compare similar events on peer companies"""
from fastapi import APIRouter, Depends, Request, HTTPException
from typing import List, Dict, Optional
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from peers import PeerEngine
from api.utils.exceptions import ResourceNotFoundException
from api.utils.auth import get_current_user_with_plan
from api.utils.paywall import require_plan

router = APIRouter(prefix="/peers", tags=["peers"])

logger = logging.getLogger(__name__)


def get_peer_engine() -> PeerEngine:
    """Dependency for PeerEngine instance"""
    return PeerEngine()


@router.get(
    "/ticker/{ticker}",
    response_model=List[Dict],
    responses={
        200: {"description": "List of peer companies with details"},
        404: {"description": "Company not found or no peers available"},
    },
    summary="Get peer companies",
    description="Find peer companies based on sector matching. Returns companies in the same sector with active event data."
)
async def get_peer_companies(
    ticker: str,
    limit: int = 5,
    peer_engine: PeerEngine = Depends(get_peer_engine),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get peer companies for a given ticker.
    
    Args:
        ticker: Target company ticker symbol
        limit: Maximum number of peers to return (default: 5)
        
    Returns:
        List of peer companies with detailed information and event statistics
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Peer comparison analytics",
        user_data.get("trial_ends_at")
    )
    
    ticker = ticker.upper()
    
    try:
        # Get detailed peer information
        peers = peer_engine.get_peer_companies_detailed(ticker, limit=limit)
        
        if not peers:
            # Try to get the target company to see if it exists
            from database import get_db, close_db_session, Company
            db = get_db()
            try:
                target_company = db.query(Company).filter(Company.ticker == ticker).first()
                if not target_company:
                    raise ResourceNotFoundException("Company", ticker)
                
                # Company exists but no peers found
                logger.info(f"No peers found for {ticker} (sector: {target_company.sector})")
                return []
            finally:
                close_db_session(db)
        
        return peers
        
    except ResourceNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error getting peers for {ticker}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve peer companies")


@router.get(
    "/event/{event_id}/similar",
    response_model=List[Dict],
    responses={
        200: {"description": "List of similar events on peer companies"},
        404: {"description": "Event not found"},
    },
    summary="Find similar events on peers",
    description="Find events of the same type on peer companies within a specified lookback period. Useful for contextualizing how similar events performed historically."
)
async def get_similar_events(
    event_id: int,
    lookback_days: int = 365,
    peer_engine: PeerEngine = Depends(get_peer_engine),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Find similar events on peer companies.
    
    Args:
        event_id: Target event ID
        lookback_days: How far back to search for similar events (default: 365 days)
        
    Returns:
        List of similar events with comparison metrics
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Peer comparison analytics",
        user_data.get("trial_ends_at")
    )
    
    try:
        similar_events = peer_engine.find_similar_events(
            event_id=event_id,
            lookback_days=lookback_days
        )
        
        if similar_events is None:
            raise ResourceNotFoundException("Event", str(event_id))
        
        return similar_events
        
    except ResourceNotFoundException:
        raise
    except Exception as e:
        logger.error(f"Error finding similar events for event {event_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to find similar events")


@router.get(
    "/event/{event_id}/compare",
    response_model=Dict,
    responses={
        200: {"description": "Detailed comparison of target event vs peer events"},
        404: {"description": "Event not found"},
    },
    summary="Detailed peer comparison",
    description="Compare target event's impact score and outcomes against similar events on peer companies. Provides statistical analysis and insights."
)
async def compare_event_to_peers(
    event_id: int,
    peer_event_ids: Optional[str] = None,
    peer_engine: PeerEngine = Depends(get_peer_engine),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Compare event impact against peer events.
    
    Args:
        event_id: Target event ID
        peer_event_ids: Optional comma-separated list of specific peer event IDs
                       If not provided, automatically finds similar events
        
    Returns:
        Comparison analysis with:
        - target_event: Details of the target event
        - peer_events: List of peer events
        - comparison: Statistical comparison metrics
            - avg_peer_score: Average impact score of peer events
            - target_vs_peers: "higher", "similar", or "lower"
            - peer_count: Number of peer events found
            - score_diff: Difference between target and average peer score
            - direction_distribution: Distribution of directions in peer events
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Peer comparison analytics",
        user_data.get("trial_ends_at")
    )
    
    try:
        # Parse peer_event_ids if provided
        parsed_peer_ids = None
        if peer_event_ids:
            try:
                parsed_peer_ids = [int(id.strip()) for id in peer_event_ids.split(',')]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid peer_event_ids format. Must be comma-separated integers."
                )
        
        # Get comparison
        comparison = peer_engine.compare_impact(
            event_id=event_id,
            peer_event_ids=parsed_peer_ids
        )
        
        if comparison['target_event'] is None:
            raise ResourceNotFoundException("Event", str(event_id))
        
        return comparison
        
    except ResourceNotFoundException:
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error comparing event {event_id} to peers: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to compare events")


@router.get(
    "/health",
    responses={
        200: {"description": "Peer engine health check"},
    },
    summary="Health check",
    description="Check if the peer comparison engine is operational"
)
async def peer_engine_health():
    """Health check endpoint for peer comparison engine"""
    return {
        "status": "healthy",
        "service": "peer_comparison",
        "version": "1.0"
    }
