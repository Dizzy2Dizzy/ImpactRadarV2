"""
Sector Analysis API Router

Endpoints for sector-level analysis, rotation signals, and performance metrics.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, func, case
from sqlalchemy.orm import Session

from api.dependencies import get_db
from api.utils.auth import get_current_user_with_plan
from releaseradar.db.models import SectorMetrics, Event, EventOutcome, EventScore

router = APIRouter(prefix="/sectors", tags=["sectors"])


class SectorSummary(BaseModel):
    """Summary metrics for a sector"""
    sector: str
    win_rate: Optional[float] = None
    avg_impact: Optional[float] = None
    rotation_signal: Optional[str] = None
    momentum_score: Optional[float] = None
    total_events: int = 0
    snapshot_date: Optional[str] = None


class SectorDetailResponse(BaseModel):
    """Detailed metrics for a specific sector"""
    sector: str
    snapshot_date: Optional[str] = None
    total_events: int = 0
    win_rate: Optional[float] = None
    avg_impact: Optional[float] = None
    top_event_types: Optional[List[Dict[str, Any]]] = None
    bullish_ratio: Optional[float] = None
    bearish_ratio: Optional[float] = None
    rotation_signal: Optional[str] = None
    momentum_score: Optional[float] = None
    correlation_with_spy: Optional[float] = None


class SectorEventResponse(BaseModel):
    """Event response for sector events endpoint"""
    id: int
    ticker: str
    company_name: str
    event_type: str
    title: str
    date: str
    impact_score: int
    direction: Optional[str] = None
    sector: Optional[str] = None


class RotationSignalResponse(BaseModel):
    """Rotation signal for a sector"""
    sector: str
    rotation_signal: str
    momentum_score: Optional[float] = None
    win_rate: Optional[float] = None
    snapshot_date: Optional[str] = None


class SectorPerformancePoint(BaseModel):
    """Performance data point for time-series"""
    date: str
    win_rate: Optional[float] = None
    avg_impact: Optional[float] = None
    total_events: int = 0


class SectorPerformanceComparison(BaseModel):
    """Performance comparison for multiple sectors"""
    sector: str
    data: List[SectorPerformancePoint]


def _get_or_generate_sector_metrics(db: Session, sector: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Get sector metrics from database. If empty, generate initial metrics
    by aggregating from events, event_outcomes, and event_scores tables.
    """
    query = db.query(SectorMetrics)
    
    if sector:
        query = query.filter(SectorMetrics.sector == sector)
    
    latest_date_subq = db.query(func.max(SectorMetrics.snapshot_date)).scalar_subquery()
    metrics = query.filter(SectorMetrics.snapshot_date == latest_date_subq).all()
    
    if metrics:
        return [
            {
                "sector": m.sector,
                "snapshot_date": m.snapshot_date.isoformat() if m.snapshot_date else None,
                "total_events": m.total_events or 0,
                "win_rate": m.win_rate,
                "avg_impact": m.avg_impact,
                "top_event_types": m.top_event_types,
                "bullish_ratio": m.bullish_ratio,
                "bearish_ratio": m.bearish_ratio,
                "rotation_signal": m.rotation_signal,
                "momentum_score": m.momentum_score,
                "correlation_with_spy": m.correlation_with_spy,
            }
            for m in metrics
        ]
    
    return _generate_sector_metrics_from_events(db, sector)


def _generate_sector_metrics_from_events(db: Session, sector: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Generate sector metrics by aggregating data from events, event_outcomes, and event_scores tables.
    """
    cutoff = datetime.utcnow() - timedelta(days=90)
    
    event_query = db.query(
        Event.sector,
        func.count(Event.id).label("total_events"),
        func.sum(case((Event.direction == "positive", 1), else_=0)).label("bullish_count"),
        func.sum(case((Event.direction == "negative", 1), else_=0)).label("bearish_count"),
    ).filter(
        Event.sector.isnot(None),
        Event.sector != "",
        Event.date >= cutoff
    ).group_by(Event.sector)
    
    if sector:
        event_query = event_query.filter(Event.sector == sector)
    
    event_results = event_query.all()
    
    if not event_results:
        return []
    
    sector_data = {}
    for row in event_results:
        total = row.total_events or 0
        bullish = row.bullish_count or 0
        bearish = row.bearish_count or 0
        
        sector_data[row.sector] = {
            "sector": row.sector,
            "snapshot_date": date.today().isoformat(),
            "total_events": total,
            "bullish_ratio": round(bullish / total, 4) if total > 0 else None,
            "bearish_ratio": round(bearish / total, 4) if total > 0 else None,
            "win_rate": None,
            "avg_impact": None,
            "top_event_types": None,
            "rotation_signal": None,
            "momentum_score": None,
            "correlation_with_spy": None,
        }
    
    outcome_query = db.query(
        Event.sector,
        func.count(EventOutcome.id).label("outcome_count"),
        func.sum(case((EventOutcome.direction_correct == True, 1), else_=0)).label("correct_count"),
    ).join(Event, EventOutcome.event_id == Event.id).filter(
        Event.sector.isnot(None),
        Event.sector != "",
        EventOutcome.horizon == "1d"
    ).group_by(Event.sector)
    
    if sector:
        outcome_query = outcome_query.filter(Event.sector == sector)
    
    outcome_results = outcome_query.all()
    
    for row in outcome_results:
        if row.sector in sector_data:
            outcome_count = row.outcome_count or 0
            correct_count = row.correct_count or 0
            sector_data[row.sector]["win_rate"] = round(correct_count / outcome_count, 4) if outcome_count > 0 else None
    
    score_query = db.query(
        Event.sector,
        func.avg(EventScore.final_score).label("avg_score"),
    ).join(Event, EventScore.event_id == Event.id).filter(
        Event.sector.isnot(None),
        Event.sector != "",
    ).group_by(Event.sector)
    
    if sector:
        score_query = score_query.filter(Event.sector == sector)
    
    score_results = score_query.all()
    
    for row in score_results:
        if row.sector in sector_data:
            sector_data[row.sector]["avg_impact"] = round(float(row.avg_score), 2) if row.avg_score else None
    
    for s, data in sector_data.items():
        bullish = data.get("bullish_ratio") or 0
        bearish = data.get("bearish_ratio") or 0
        win_rate = data.get("win_rate")
        
        if bullish > bearish + 0.15 and (win_rate is None or win_rate > 0.55):
            data["rotation_signal"] = "inflow"
            data["momentum_score"] = round(0.5 + (bullish - bearish), 2)
        elif win_rate is not None and win_rate >= 0.65 and bullish >= bearish:
            data["rotation_signal"] = "inflow"
            data["momentum_score"] = round(0.5 + (win_rate - 0.5), 2)
        elif bearish > bullish + 0.15 and (win_rate is None or win_rate < 0.45):
            data["rotation_signal"] = "outflow"
            data["momentum_score"] = round(0.5 - (bearish - bullish), 2)
        else:
            data["rotation_signal"] = "neutral"
            data["momentum_score"] = 0.5
    
    return list(sector_data.values())


@router.get(
    "/rotation-signals",
    response_model=List[RotationSignalResponse],
    summary="Get current rotation signals for all sectors",
    description="Returns sectors marked as 'inflow' or 'outflow' with momentum scores."
)
async def get_rotation_signals(
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Get current rotation signals for all sectors."""
    try:
        metrics = _get_or_generate_sector_metrics(db)
        
        signals = [
            RotationSignalResponse(
                sector=m["sector"],
                rotation_signal=m.get("rotation_signal") or "neutral",
                momentum_score=m.get("momentum_score"),
                win_rate=m.get("win_rate"),
                snapshot_date=m.get("snapshot_date"),
            )
            for m in metrics
            if m.get("rotation_signal") in ("inflow", "outflow")
        ]
        
        signals.sort(key=lambda x: abs(x.momentum_score or 0), reverse=True)
        
        return signals
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch rotation signals: {str(e)}")


@router.get(
    "/performance-comparison",
    response_model=List[SectorPerformanceComparison],
    summary="Compare sector performance over time",
    description="Returns time-series data for comparing sector win rates over a specified period."
)
async def get_performance_comparison(
    sectors: Optional[List[str]] = Query(None, description="List of sectors to compare (defaults to all)"),
    days: int = Query(30, ge=7, le=365, description="Number of days to analyze"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Compare sector performance over time."""
    try:
        cutoff_date = date.today() - timedelta(days=days)
        
        query = db.query(SectorMetrics).filter(
            SectorMetrics.snapshot_date >= cutoff_date
        ).order_by(SectorMetrics.sector, SectorMetrics.snapshot_date)
        
        if sectors:
            query = query.filter(SectorMetrics.sector.in_(sectors))
        
        historical_data = query.all()
        
        if historical_data:
            sector_time_series: Dict[str, List[SectorPerformancePoint]] = {}
            
            for m in historical_data:
                if m.sector not in sector_time_series:
                    sector_time_series[m.sector] = []
                
                sector_time_series[m.sector].append(SectorPerformancePoint(
                    date=m.snapshot_date.isoformat() if m.snapshot_date else "",
                    win_rate=m.win_rate,
                    avg_impact=m.avg_impact,
                    total_events=m.total_events or 0,
                ))
            
            return [
                SectorPerformanceComparison(sector=sector, data=points)
                for sector, points in sector_time_series.items()
            ]
        
        event_query = db.query(
            Event.sector,
            func.date(Event.date).label("event_date"),
            func.count(Event.id).label("total_events"),
            func.avg(Event.impact_score).label("avg_impact"),
        ).filter(
            Event.sector.isnot(None),
            Event.sector != "",
            Event.date >= cutoff_date
        ).group_by(Event.sector, func.date(Event.date)).order_by(Event.sector, func.date(Event.date))
        
        if sectors:
            event_query = event_query.filter(Event.sector.in_(sectors))
        
        event_results = event_query.all()
        
        if not event_results:
            return []
        
        outcome_query = db.query(
            Event.sector,
            func.date(Event.date).label("event_date"),
            func.count(EventOutcome.id).label("outcome_count"),
            func.sum(case((EventOutcome.direction_correct == True, 1), else_=0)).label("correct_count"),
        ).join(Event, EventOutcome.event_id == Event.id).filter(
            Event.sector.isnot(None),
            Event.sector != "",
            Event.date >= cutoff_date,
            EventOutcome.horizon == "1d"
        ).group_by(Event.sector, func.date(Event.date))
        
        if sectors:
            outcome_query = outcome_query.filter(Event.sector.in_(sectors))
        
        outcome_results = outcome_query.all()
        
        win_rate_map: Dict[str, Dict[str, float]] = {}
        for row in outcome_results:
            sector_name = row.sector
            event_date_str = row.event_date.isoformat() if hasattr(row.event_date, 'isoformat') else str(row.event_date)
            outcome_count = row.outcome_count or 0
            correct_count = row.correct_count or 0
            if sector_name not in win_rate_map:
                win_rate_map[sector_name] = {}
            if outcome_count > 0:
                win_rate_map[sector_name][event_date_str] = round(correct_count / outcome_count, 4)
        
        sector_time_series: Dict[str, List[SectorPerformancePoint]] = {}
        for row in event_results:
            sector_name = row.sector
            event_date_str = row.event_date.isoformat() if hasattr(row.event_date, 'isoformat') else str(row.event_date)
            
            if sector_name not in sector_time_series:
                sector_time_series[sector_name] = []
            
            win_rate = win_rate_map.get(sector_name, {}).get(event_date_str)
            avg_impact = round(float(row.avg_impact), 2) if row.avg_impact else None
            
            sector_time_series[sector_name].append(SectorPerformancePoint(
                date=event_date_str,
                win_rate=win_rate,
                avg_impact=avg_impact,
                total_events=row.total_events or 0,
            ))
        
        return [
            SectorPerformanceComparison(sector=sector, data=points)
            for sector, points in sector_time_series.items()
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch performance comparison: {str(e)}")


@router.get(
    "",
    response_model=List[SectorSummary],
    summary="List all sectors with latest metrics",
    description="Returns list of all sectors with win_rate, avg_impact, rotation_signal, and momentum_score."
)
async def list_sectors(
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """List all sectors with their latest metrics."""
    try:
        metrics = _get_or_generate_sector_metrics(db)
        
        return [
            SectorSummary(
                sector=m["sector"],
                win_rate=m.get("win_rate"),
                avg_impact=m.get("avg_impact"),
                rotation_signal=m.get("rotation_signal"),
                momentum_score=m.get("momentum_score"),
                total_events=m.get("total_events", 0),
                snapshot_date=m.get("snapshot_date"),
            )
            for m in metrics
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sectors: {str(e)}")


@router.get(
    "/{sector}",
    response_model=SectorDetailResponse,
    summary="Get detailed metrics for a specific sector",
    description="Returns full sector metrics including top_event_types, bullish_ratio, bearish_ratio, and correlation_with_spy."
)
async def get_sector_details(
    sector: str,
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Get detailed metrics for a specific sector."""
    try:
        metrics = _get_or_generate_sector_metrics(db, sector=sector)
        
        if not metrics:
            raise HTTPException(status_code=404, detail=f"Sector '{sector}' not found")
        
        m = metrics[0]
        
        top_event_types = m.get("top_event_types")
        if not top_event_types:
            event_type_counts = db.query(
                Event.event_type,
                func.count(Event.id).label("count")
            ).filter(
                Event.sector == sector
            ).group_by(Event.event_type).order_by(desc("count")).limit(5).all()
            
            top_event_types = [{"event_type": et, "count": c} for et, c in event_type_counts]
        
        return SectorDetailResponse(
            sector=m["sector"],
            snapshot_date=m.get("snapshot_date"),
            total_events=m.get("total_events", 0),
            win_rate=m.get("win_rate"),
            avg_impact=m.get("avg_impact"),
            top_event_types=top_event_types,
            bullish_ratio=m.get("bullish_ratio"),
            bearish_ratio=m.get("bearish_ratio"),
            rotation_signal=m.get("rotation_signal"),
            momentum_score=m.get("momentum_score"),
            correlation_with_spy=m.get("correlation_with_spy"),
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sector details: {str(e)}")


@router.get(
    "/{sector}/events",
    response_model=List[SectorEventResponse],
    summary="Get recent events for a sector",
    description="Returns list of recent events filtered by sector."
)
async def get_sector_events(
    sector: str,
    limit: int = Query(50, ge=1, le=500, description="Maximum number of events to return"),
    days: int = Query(30, ge=1, le=365, description="Number of days to look back"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Get recent events for a specific sector."""
    try:
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        events = db.query(Event).filter(
            Event.sector == sector,
            Event.date >= cutoff
        ).order_by(desc(Event.date)).limit(limit).all()
        
        return [
            SectorEventResponse(
                id=e.id,
                ticker=e.ticker,
                company_name=e.company_name,
                event_type=e.event_type,
                title=e.title,
                date=e.date.isoformat() if e.date else "",
                impact_score=e.impact_score or 50,
                direction=e.direction,
                sector=e.sector,
            )
            for e in events
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch sector events: {str(e)}")
