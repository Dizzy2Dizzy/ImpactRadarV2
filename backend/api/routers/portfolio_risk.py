"""
Portfolio Risk API Router

Endpoints for portfolio risk analysis including:
- Risk calculation (event exposure, concentration, VaR, CVaR)
- Historical risk snapshots
- Event-level exposure tracking
- Hedging recommendations
"""

from fastapi import APIRouter, Depends, Request, HTTPException, Query
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from pydantic import BaseModel, Field
import logging

from api.dependencies import get_db
from api.utils.auth import get_current_user_id
from api.utils.paywall import require_plan
from api.ratelimit import limiter, plan_limit
from releaseradar.db.models import (
    UserPortfolio,
    PortfolioRiskSnapshot,
    PortfolioEventExposure,
    PortfolioPosition,
    Event,
    User
)
from releaseradar.services.portfolio_risk_calculator import (
    calculate_portfolio_risk,
    calculate_event_exposure
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# Response models
class RiskMetrics(BaseModel):
    """Risk metrics response model"""
    total_event_exposure: float = Field(..., description="% of portfolio exposed to upcoming events")
    concentration_risk_score: float = Field(..., description="Concentration risk (0-100, higher = more concentrated)")
    sector_diversification_score: float = Field(..., description="Sector diversification (0-100, higher = more diversified)")
    var_95: float = Field(..., description="Value at Risk at 95% confidence (%)")
    expected_shortfall: float = Field(..., description="Expected Shortfall/CVaR (%)")
    
    class Config:
        from_attributes = True


class TopEventRisk(BaseModel):
    """Top event risk model"""
    event_id: int
    ticker: str
    event_type: str
    title: str
    date: str
    impact_score: int
    direction: Optional[str]
    position_size_pct: float
    estimated_impact_pct: float
    dollar_exposure: float


class RiskSnapshotResponse(BaseModel):
    """Risk snapshot response model"""
    id: int
    portfolio_id: int
    snapshot_date: datetime
    metrics: RiskMetrics
    top_event_risks: List[TopEventRisk] = []
    
    class Config:
        from_attributes = True


class EventExposureResponse(BaseModel):
    """Event exposure response model"""
    id: int
    portfolio_id: int
    event_id: int
    ticker: str
    event_type: str
    event_title: str
    event_date: datetime
    position_size_pct: float
    estimated_impact_pct: float
    dollar_exposure: float
    hedge_recommendation: Optional[str]
    calculated_at: datetime
    
    class Config:
        from_attributes = True


class HedgingRecommendation(BaseModel):
    """Hedging recommendation model"""
    ticker: str
    event_id: int
    event_type: str
    event_date: datetime
    position_size_pct: float
    estimated_impact_pct: float
    dollar_exposure: float
    recommendation: str
    risk_level: str  # "high", "medium", "low"


class CalculateRiskRequest(BaseModel):
    """Request model for risk calculation"""
    lookforward_days: int = Field(30, description="Days to look ahead for event exposure", ge=1, le=90)


class CalculateRiskResponse(BaseModel):
    """Response for risk calculation trigger"""
    success: bool
    message: str
    snapshot_id: int
    snapshot_date: datetime


@router.post("/{portfolio_id}/risk/calculate", response_model=CalculateRiskResponse)
@limiter.limit(plan_limit)
async def trigger_risk_calculation(
    portfolio_id: int,
    body: CalculateRiskRequest = CalculateRiskRequest(),
    request: Request = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Trigger risk calculation for a portfolio.
    
    Calculates comprehensive risk metrics including:
    - Event exposure (% of portfolio with upcoming events)
    - Concentration risk (Herfindahl index)
    - Sector diversification (Shannon entropy)
    - Value at Risk (VaR) at 95% confidence
    - Expected Shortfall (CVaR)
    - Top 10 event risks
    
    Requires: Pro or Team plan
    """
    # Verify portfolio ownership
    portfolio = db.query(UserPortfolio).filter(
        and_(
            UserPortfolio.id == portfolio_id,
            UserPortfolio.user_id == user_id
        )
    ).first()
    
    if not portfolio:
        raise HTTPException(
            status_code=404,
            detail=f"Portfolio {portfolio_id} not found or access denied"
        )
    
    try:
        # Calculate risk metrics
        snapshot = calculate_portfolio_risk(
            portfolio_id=portfolio_id,
            db=db,
            lookforward_days=body.lookforward_days
        )
        
        return CalculateRiskResponse(
            success=True,
            message="Risk calculation completed successfully",
            snapshot_id=snapshot.id,
            snapshot_date=snapshot.snapshot_date
        )
    
    except ValueError as e:
        logger.error(f"Risk calculation failed for portfolio {portfolio_id}: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        logger.exception(f"Unexpected error during risk calculation for portfolio {portfolio_id}")
        raise HTTPException(
            status_code=500,
            detail="Risk calculation failed due to internal error"
        )


@router.get("/{portfolio_id}/risk/latest", response_model=RiskSnapshotResponse)
@limiter.limit(plan_limit)
async def get_latest_risk_snapshot(
    portfolio_id: int,
    request: Request = None,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get the latest risk snapshot for a portfolio.
    
    Returns the most recent risk calculation including all metrics and top event risks.
    
    Requires: Pro or Team plan
    """
    # Verify portfolio ownership
    portfolio = db.query(UserPortfolio).filter(
        and_(
            UserPortfolio.id == portfolio_id,
            UserPortfolio.user_id == user_id
        )
    ).first()
    
    if not portfolio:
        raise HTTPException(
            status_code=404,
            detail=f"Portfolio {portfolio_id} not found or access denied"
        )
    
    # Get latest snapshot
    snapshot = db.query(PortfolioRiskSnapshot).filter(
        PortfolioRiskSnapshot.portfolio_id == portfolio_id
    ).order_by(desc(PortfolioRiskSnapshot.snapshot_date)).first()
    
    if not snapshot:
        raise HTTPException(
            status_code=404,
            detail=f"No risk snapshots found for portfolio {portfolio_id}. "
                   "Please trigger a risk calculation first."
        )
    
    # Build response
    metrics = RiskMetrics(
        total_event_exposure=snapshot.total_event_exposure or 0.0,
        concentration_risk_score=snapshot.concentration_risk_score or 0.0,
        sector_diversification_score=snapshot.sector_diversification_score or 0.0,
        var_95=snapshot.var_95 or 0.0,
        expected_shortfall=snapshot.expected_shortfall or 0.0
    )
    
    top_event_risks = [
        TopEventRisk(**risk) 
        for risk in (snapshot.top_event_risks_json or [])
    ]
    
    return RiskSnapshotResponse(
        id=snapshot.id,
        portfolio_id=snapshot.portfolio_id,
        snapshot_date=snapshot.snapshot_date,
        metrics=metrics,
        top_event_risks=top_event_risks
    )


@router.get("/{portfolio_id}/risk/history", response_model=List[RiskSnapshotResponse])
@limiter.limit(plan_limit)
async def get_risk_history(
    portfolio_id: int,
    request: Request = None,
    limit: int = Query(30, ge=1, le=100, description="Number of snapshots to return"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get historical risk snapshots for a portfolio.
    
    Returns up to 100 most recent risk snapshots for trend analysis.
    
    Requires: Pro or Team plan
    """
    # Verify portfolio ownership
    portfolio = db.query(UserPortfolio).filter(
        and_(
            UserPortfolio.id == portfolio_id,
            UserPortfolio.user_id == user_id
        )
    ).first()
    
    if not portfolio:
        raise HTTPException(
            status_code=404,
            detail=f"Portfolio {portfolio_id} not found or access denied"
        )
    
    # Get historical snapshots
    snapshots = db.query(PortfolioRiskSnapshot).filter(
        PortfolioRiskSnapshot.portfolio_id == portfolio_id
    ).order_by(desc(PortfolioRiskSnapshot.snapshot_date)).limit(limit).all()
    
    # Build response
    results = []
    for snapshot in snapshots:
        metrics = RiskMetrics(
            total_event_exposure=snapshot.total_event_exposure or 0.0,
            concentration_risk_score=snapshot.concentration_risk_score or 0.0,
            sector_diversification_score=snapshot.sector_diversification_score or 0.0,
            var_95=snapshot.var_95 or 0.0,
            expected_shortfall=snapshot.expected_shortfall or 0.0
        )
        
        top_event_risks = [
            TopEventRisk(**risk) 
            for risk in (snapshot.top_event_risks_json or [])
        ]
        
        results.append(RiskSnapshotResponse(
            id=snapshot.id,
            portfolio_id=snapshot.portfolio_id,
            snapshot_date=snapshot.snapshot_date,
            metrics=metrics,
            top_event_risks=top_event_risks
        ))
    
    return results


@router.get("/{portfolio_id}/risk/events", response_model=List[EventExposureResponse])
@limiter.limit(plan_limit)
async def get_event_exposures(
    portfolio_id: int,
    request: Request = None,
    days_ahead: int = Query(30, ge=1, le=90, description="Days ahead to look for events"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get event-level exposures for a portfolio.
    
    Returns detailed exposure analysis for each upcoming event affecting portfolio positions.
    Automatically calculates exposures for events not yet analyzed.
    
    Requires: Pro or Team plan
    """
    # Verify portfolio ownership
    portfolio = db.query(UserPortfolio).filter(
        and_(
            UserPortfolio.id == portfolio_id,
            UserPortfolio.user_id == user_id
        )
    ).first()
    
    if not portfolio:
        raise HTTPException(
            status_code=404,
            detail=f"Portfolio {portfolio_id} not found or access denied"
        )
    
    # Get portfolio positions
    positions = db.query(PortfolioPosition).filter(
        PortfolioPosition.portfolio_id == portfolio_id
    ).all()
    
    if not positions:
        return []
    
    # Get upcoming events for portfolio tickers
    tickers = [pos.ticker for pos in positions]
    event_window_start = datetime.utcnow()
    event_window_end = datetime.utcnow() + timedelta(days=days_ahead)
    
    upcoming_events = db.query(Event).filter(
        and_(
            Event.ticker.in_(tickers),
            Event.date >= event_window_start,
            Event.date <= event_window_end
        )
    ).order_by(Event.date).all()
    
    # Calculate exposures for events not yet analyzed
    for event in upcoming_events:
        existing = db.query(PortfolioEventExposure).filter(
            and_(
                PortfolioEventExposure.portfolio_id == portfolio_id,
                PortfolioEventExposure.event_id == event.id
            )
        ).first()
        
        if not existing:
            try:
                calculate_event_exposure(
                    portfolio_id=portfolio_id,
                    event_id=event.id,
                    db=db
                )
            except ValueError as e:
                logger.warning(f"Could not calculate exposure for event {event.id}: {str(e)}")
                continue
    
    # Get all exposures
    exposures = db.query(PortfolioEventExposure).filter(
        PortfolioEventExposure.portfolio_id == portfolio_id
    ).join(Event, PortfolioEventExposure.event_id == Event.id).filter(
        and_(
            Event.date >= event_window_start,
            Event.date <= event_window_end
        )
    ).order_by(desc(PortfolioEventExposure.dollar_exposure)).all()
    
    # Build response
    results = []
    for exposure in exposures:
        event = exposure.event
        results.append(EventExposureResponse(
            id=exposure.id,
            portfolio_id=exposure.portfolio_id,
            event_id=exposure.event_id,
            ticker=event.ticker,
            event_type=event.event_type,
            event_title=event.title,
            event_date=event.date,
            position_size_pct=exposure.position_size_pct,
            estimated_impact_pct=exposure.estimated_impact_pct or 0.0,
            dollar_exposure=exposure.dollar_exposure or 0.0,
            hedge_recommendation=exposure.hedge_recommendation,
            calculated_at=exposure.calculated_at
        ))
    
    return results


@router.get("/{portfolio_id}/risk/hedging", response_model=List[HedgingRecommendation])
@limiter.limit(plan_limit)
async def get_hedging_recommendations(
    portfolio_id: int,
    request: Request = None,
    days_ahead: int = Query(30, ge=1, le=90, description="Days ahead to look for events"),
    min_risk_level: str = Query("medium", description="Minimum risk level to include (low, medium, high)"),
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Get hedging recommendations for high-risk event exposures.
    
    Returns actionable hedging strategies for positions with significant event exposure.
    Only includes exposures with hedge recommendations.
    
    Risk levels:
    - High: >5% position size AND >3% estimated impact
    - Medium: >10% position size AND >2% estimated impact
    - Low: All other exposures
    
    Requires: Pro or Team plan
    """
    # Verify portfolio ownership
    portfolio = db.query(UserPortfolio).filter(
        and_(
            UserPortfolio.id == portfolio_id,
            UserPortfolio.user_id == user_id
        )
    ).first()
    
    if not portfolio:
        raise HTTPException(
            status_code=404,
            detail=f"Portfolio {portfolio_id} not found or access denied"
        )
    
    # Get event exposures with hedge recommendations
    event_window_start = datetime.utcnow()
    event_window_end = datetime.utcnow() + timedelta(days=days_ahead)
    
    exposures = db.query(PortfolioEventExposure).filter(
        and_(
            PortfolioEventExposure.portfolio_id == portfolio_id,
            PortfolioEventExposure.hedge_recommendation.isnot(None)
        )
    ).join(Event, PortfolioEventExposure.event_id == Event.id).filter(
        and_(
            Event.date >= event_window_start,
            Event.date <= event_window_end
        )
    ).order_by(desc(PortfolioEventExposure.dollar_exposure)).all()
    
    # Build recommendations with risk levels
    recommendations = []
    for exposure in exposures:
        event = exposure.event
        
        # Determine risk level
        abs_impact = abs(exposure.estimated_impact_pct or 0.0)
        if exposure.position_size_pct > 5 and abs_impact > 3:
            risk_level = "high"
        elif exposure.position_size_pct > 10 and abs_impact > 2:
            risk_level = "medium"
        else:
            risk_level = "low"
        
        # Filter by minimum risk level
        risk_levels = {"low": 0, "medium": 1, "high": 2}
        if risk_levels[risk_level] < risk_levels[min_risk_level]:
            continue
        
        recommendations.append(HedgingRecommendation(
            ticker=event.ticker,
            event_id=event.id,
            event_type=event.event_type,
            event_date=event.date,
            position_size_pct=exposure.position_size_pct,
            estimated_impact_pct=exposure.estimated_impact_pct or 0.0,
            dollar_exposure=exposure.dollar_exposure or 0.0,
            recommendation=exposure.hedge_recommendation or "",
            risk_level=risk_level
        ))
    
    return recommendations
