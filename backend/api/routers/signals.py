"""Signals router for bearish and bullish signal detection"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, timezone
from pydantic import BaseModel

from api.dependencies import get_data_manager
from api.utils.auth import get_current_user_optional
from api.ratelimit import limiter, plan_limit
from data_manager import DataManager
from database import get_db, close_db_session
from releaseradar.db.models import Event
from sqlalchemy import select, func, and_, desc
from releaseradar.services.bearish_pattern_detector import BearishPatternDetector, BearishPatternConfig


router = APIRouter(prefix="/signals", tags=["signals"])


class BearishEventResponse(BaseModel):
    """Response model for bearish events"""
    id: int
    ticker: str
    company_name: Optional[str]
    event_type: str
    title: str
    date: Optional[str]
    bearish_signal: bool
    bearish_score: Optional[float]
    bearish_confidence: Optional[float]
    bearish_rationale: Optional[str]
    direction: Optional[str]
    impact_score: Optional[int]
    ml_adjusted_score: Optional[int]
    source_url: Optional[str]


class BearishPatternResponse(BaseModel):
    """Response model for detected bearish patterns"""
    pattern_type: str
    ticker: str
    sector: Optional[str]
    window_days: int
    event_count: int
    avg_bearish_score: float
    max_bearish_score: float
    total_bearish_score: float
    confidence: float
    detected_at: str
    description: str
    event_ids: List[int]


class BearishSummaryResponse(BaseModel):
    """Response model for bearish summary"""
    ticker: str
    window_days: int
    bearish_event_count: int
    total_bearish_score: float
    avg_bearish_score: float
    max_bearish_score: float
    risk_level: str
    patterns: List[Dict[str, Any]]
    recent_events: List[Dict[str, Any]]


class BearishStatsResponse(BaseModel):
    """Response model for overall bearish statistics"""
    total_bearish_events: int
    total_events: int
    bearish_percentage: float
    top_bearish_tickers: List[Dict[str, Any]]
    top_bearish_sectors: List[Dict[str, Any]]
    recent_bearish_count: int
    window_days: int


@router.get(
    "/bearish",
    response_model=List[BearishEventResponse],
    summary="Get bearish events",
    description="Retrieve events flagged with bearish signals. These are events that indicate potential negative stock movements based on event type, keywords, and ML predictions."
)
async def get_bearish_events(
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    min_score: Optional[float] = Query(0.4, description="Minimum bearish score (0-1)"),
    window_days: Optional[int] = Query(30, description="Look back window in days"),
    limit: int = Query(50, description="Maximum number of results"),
    offset: int = Query(0, description="Pagination offset"),
    dm: DataManager = Depends(get_data_manager),
    user_id: Optional[int] = Depends(get_current_user_optional)
):
    """Get events with bearish signals"""
    db = get_db()
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=window_days)
        
        query = (
            select(Event)
            .where(Event.bearish_signal == True)
            .where(Event.date >= cutoff_date)
        )
        
        if min_score:
            query = query.where(Event.bearish_score >= min_score)
        
        if ticker:
            query = query.where(Event.ticker == ticker.upper())
        
        if sector:
            query = query.where(Event.sector == sector)
        
        query = query.order_by(desc(Event.bearish_score), desc(Event.date))
        query = query.offset(offset).limit(limit)
        
        events = db.execute(query).scalars().all()
        
        return [
            BearishEventResponse(
                id=e.id,
                ticker=e.ticker,
                company_name=e.company_name,
                event_type=e.event_type,
                title=e.title,
                date=e.date.isoformat() if e.date else None,
                bearish_signal=e.bearish_signal or False,
                bearish_score=e.bearish_score,
                bearish_confidence=e.bearish_confidence,
                bearish_rationale=e.bearish_rationale,
                direction=e.direction,
                impact_score=e.impact_score,
                ml_adjusted_score=e.ml_adjusted_score,
                source_url=e.source_url
            )
            for e in events
        ]
    finally:
        close_db_session(db)


@router.get(
    "/bearish/patterns",
    response_model=Dict[str, List[BearishPatternResponse]],
    summary="Detect bearish patterns",
    description="Detect bearish patterns including event clusters, escalations, and sector contagion."
)
async def get_bearish_patterns(
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    sector: Optional[str] = Query(None, description="Filter by sector"),
    dm: DataManager = Depends(get_data_manager),
    user_id: Optional[int] = Depends(get_current_user_optional)
):
    """Detect bearish patterns across events"""
    db = get_db()
    try:
        detector = BearishPatternDetector()
        patterns = detector.detect_all_patterns(
            db=db,
            ticker=ticker.upper() if ticker else None,
            sector=sector
        )
        
        result = {
            'clusters': [],
            'escalations': [],
            'sector_contagions': []
        }
        
        for p in patterns.get('clusters', []):
            result['clusters'].append(BearishPatternResponse(
                pattern_type=p.pattern_type,
                ticker=p.ticker,
                sector=p.sector,
                window_days=p.window_days,
                event_count=p.event_count,
                avg_bearish_score=p.avg_bearish_score,
                max_bearish_score=p.max_bearish_score,
                total_bearish_score=p.total_bearish_score,
                confidence=p.confidence,
                detected_at=p.detected_at.isoformat(),
                description=p.description,
                event_ids=p.event_ids
            ))
        
        for p in patterns.get('escalations', []):
            result['escalations'].append(BearishPatternResponse(
                pattern_type=p.pattern_type,
                ticker=p.ticker,
                sector=p.sector,
                window_days=p.window_days,
                event_count=p.event_count,
                avg_bearish_score=p.avg_bearish_score,
                max_bearish_score=p.max_bearish_score,
                total_bearish_score=p.total_bearish_score,
                confidence=p.confidence,
                detected_at=p.detected_at.isoformat(),
                description=p.description,
                event_ids=p.event_ids
            ))
        
        for p in patterns.get('sector_contagions', []):
            result['sector_contagions'].append(BearishPatternResponse(
                pattern_type=p.pattern_type,
                ticker=p.ticker,
                sector=p.sector,
                window_days=p.window_days,
                event_count=p.event_count,
                avg_bearish_score=p.avg_bearish_score,
                max_bearish_score=p.max_bearish_score,
                total_bearish_score=p.total_bearish_score,
                confidence=p.confidence,
                detected_at=p.detected_at.isoformat(),
                description=p.description,
                event_ids=p.event_ids
            ))
        
        return result
    finally:
        close_db_session(db)


@router.get(
    "/bearish/summary/{ticker}",
    response_model=BearishSummaryResponse,
    summary="Get bearish summary for ticker",
    description="Get comprehensive bearish analysis for a specific ticker including risk level and patterns."
)
async def get_bearish_summary(
    ticker: str,
    window_days: int = Query(30, description="Analysis window in days"),
    dm: DataManager = Depends(get_data_manager),
    user_id: Optional[int] = Depends(get_current_user_optional)
):
    """Get comprehensive bearish summary for a ticker"""
    db = get_db()
    try:
        detector = BearishPatternDetector()
        summary = detector.get_ticker_bearish_summary(
            db=db,
            ticker=ticker.upper(),
            window_days=window_days
        )
        
        return BearishSummaryResponse(**summary)
    finally:
        close_db_session(db)


@router.get(
    "/bearish/stats",
    response_model=BearishStatsResponse,
    summary="Get overall bearish statistics",
    description="Get aggregate statistics on bearish signals across all events."
)
async def get_bearish_stats(
    window_days: int = Query(30, description="Analysis window in days"),
    dm: DataManager = Depends(get_data_manager),
    user_id: Optional[int] = Depends(get_current_user_optional)
):
    """Get overall bearish signal statistics"""
    db = get_db()
    try:
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=window_days)
        
        total_events = db.execute(
            select(func.count(Event.id))
            .where(Event.date >= cutoff_date)
        ).scalar()
        
        bearish_events = db.execute(
            select(func.count(Event.id))
            .where(Event.bearish_signal == True)
            .where(Event.date >= cutoff_date)
        ).scalar()
        
        recent_cutoff = datetime.now(timezone.utc) - timedelta(days=7)
        recent_bearish = db.execute(
            select(func.count(Event.id))
            .where(Event.bearish_signal == True)
            .where(Event.date >= recent_cutoff)
        ).scalar()
        
        top_tickers = db.execute(
            select(
                Event.ticker,
                func.count(Event.id).label('count'),
                func.avg(Event.bearish_score).label('avg_score')
            )
            .where(Event.bearish_signal == True)
            .where(Event.date >= cutoff_date)
            .group_by(Event.ticker)
            .order_by(func.count(Event.id).desc())
            .limit(10)
        ).all()
        
        top_sectors = db.execute(
            select(
                Event.sector,
                func.count(Event.id).label('count'),
                func.avg(Event.bearish_score).label('avg_score')
            )
            .where(Event.bearish_signal == True)
            .where(Event.date >= cutoff_date)
            .where(Event.sector.isnot(None))
            .group_by(Event.sector)
            .order_by(func.count(Event.id).desc())
            .limit(5)
        ).all()
        
        return BearishStatsResponse(
            total_bearish_events=bearish_events or 0,
            total_events=total_events or 0,
            bearish_percentage=round((bearish_events / total_events * 100) if total_events else 0, 2),
            top_bearish_tickers=[
                {'ticker': t[0], 'count': t[1], 'avg_score': round(float(t[2]) if t[2] else 0, 3)}
                for t in top_tickers
            ],
            top_bearish_sectors=[
                {'sector': s[0], 'count': s[1], 'avg_score': round(float(s[2]) if s[2] else 0, 3)}
                for s in top_sectors
            ],
            recent_bearish_count=recent_bearish or 0,
            window_days=window_days
        )
    finally:
        close_db_session(db)


class ContrarianEventResponse(BaseModel):
    """Response model for contrarian events"""
    event_id: int
    ticker: str
    event_type: str
    title: str
    predicted_direction: str
    realized_return_1d: float
    hidden_bearish_prob: Optional[float]
    hidden_bearish_signal: bool
    divergence_severity: Optional[float]


class ContrarianPatternResponse(BaseModel):
    """Response model for contrarian patterns"""
    ticker: str
    event_type: str
    contrarian_rate: float
    total_events: int
    contrarian_events: int
    avg_decline: float
    hidden_bearish_prob: float
    confidence: float


class ContrarianSummaryResponse(BaseModel):
    """Response model for contrarian analysis summary"""
    lookback_days: int
    total_positive_neutral_events: int
    contrarian_events: int
    contrarian_rate: float
    severe_contrarian_events: int
    patterns_detected: int
    top_contrarian_patterns: List[Dict[str, Any]]
    thresholds: Dict[str, float]


@router.get(
    "/contrarian/events",
    response_model=List[ContrarianEventResponse],
    summary="Get contrarian events",
    description="Retrieve events where the prediction was positive/neutral but the stock declined (hidden bearish signals)."
)
async def get_contrarian_events(
    ticker: Optional[str] = Query(None, description="Filter by ticker symbol"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    min_decline: Optional[float] = Query(-1.0, description="Minimum decline threshold (e.g., -1.0 for 1% drop)"),
    lookback_days: int = Query(90, description="Look back window in days"),
    limit: int = Query(50, description="Maximum number of results"),
    dm: DataManager = Depends(get_data_manager),
    user_id: Optional[int] = Depends(get_current_user_optional)
):
    """Get events where predictions diverged from actual outcomes"""
    db = get_db()
    try:
        from releaseradar.services.contrariance_analyzer import ContrarianAnalyzer
        
        analyzer = ContrarianAnalyzer(db)
        events = analyzer.find_contrarian_events(
            ticker=ticker,
            event_type=event_type,
            lookback_days=lookback_days,
            min_decline=min_decline
        )
        
        return [
            ContrarianEventResponse(
                event_id=e.event_id,
                ticker=e.ticker,
                event_type=e.event_type,
                title=e.title,
                predicted_direction=e.predicted_direction,
                realized_return_1d=round(e.realized_return_1d, 2),
                hidden_bearish_prob=round(e.hidden_bearish_prob, 3) if e.hidden_bearish_prob else None,
                hidden_bearish_signal=e.is_hidden_bearish,
                divergence_severity=round(e.divergence_severity, 3) if e.divergence_severity else None
            )
            for e in events[:limit]
        ]
    finally:
        close_db_session(db)


@router.get(
    "/contrarian/patterns",
    response_model=List[ContrarianPatternResponse],
    summary="Get contrarian patterns",
    description="Retrieve patterns where ticker/event_type combinations historically led to declines despite positive/neutral predictions."
)
async def get_contrarian_patterns(
    min_sample_size: int = Query(3, description="Minimum events required for pattern"),
    min_contrarian_rate: float = Query(0.3, description="Minimum contrarian rate (0-1)"),
    lookback_days: int = Query(180, description="Look back window in days"),
    limit: int = Query(20, description="Maximum number of patterns"),
    dm: DataManager = Depends(get_data_manager),
    user_id: Optional[int] = Depends(get_current_user_optional)
):
    """Get patterns of contrarian outcomes for ML learning"""
    db = get_db()
    try:
        from releaseradar.services.contrariance_analyzer import ContrarianAnalyzer
        
        analyzer = ContrarianAnalyzer(db)
        patterns = analyzer.compute_contrarian_patterns(
            lookback_days=lookback_days,
            min_sample_size=min_sample_size
        )
        
        # Filter by minimum contrarian rate
        patterns = [p for p in patterns if p.contrarian_rate >= min_contrarian_rate]
        
        return [
            ContrarianPatternResponse(
                ticker=p.ticker,
                event_type=p.event_type,
                contrarian_rate=round(p.contrarian_rate, 3),
                total_events=p.total_events,
                contrarian_events=p.contrarian_events,
                avg_decline=round(p.avg_negative_divergence, 2),
                hidden_bearish_prob=round(p.hidden_bearish_probability, 3),
                confidence=round(p.confidence, 3)
            )
            for p in patterns[:limit]
        ]
    finally:
        close_db_session(db)


@router.get(
    "/contrarian/summary",
    response_model=ContrarianSummaryResponse,
    summary="Get contrarian analysis summary",
    description="Get overall summary of contrarian patterns and hidden bearish signals in the dataset."
)
async def get_contrarian_summary(
    lookback_days: int = Query(90, description="Analysis window in days"),
    dm: DataManager = Depends(get_data_manager),
    user_id: Optional[int] = Depends(get_current_user_optional)
):
    """Get summary of contrarian analysis"""
    db = get_db()
    try:
        from releaseradar.services.contrariance_analyzer import ContrarianAnalyzer
        
        analyzer = ContrarianAnalyzer(db)
        summary = analyzer.get_contrarian_summary(lookback_days=lookback_days)
        
        return ContrarianSummaryResponse(**summary)
    finally:
        close_db_session(db)


@router.get(
    "/contrarian/hidden-bearish/{ticker}",
    summary="Get hidden bearish probability for ticker",
    description="Get the probability that a new positive/neutral event for this ticker/event_type will result in a decline."
)
async def get_hidden_bearish_probability(
    ticker: str,
    event_type: str = Query(..., description="Event type to check"),
    dm: DataManager = Depends(get_data_manager),
    user_id: Optional[int] = Depends(get_current_user_optional)
):
    """Get hidden bearish probability for a specific ticker and event type"""
    db = get_db()
    try:
        from releaseradar.services.contrariance_analyzer import ContrarianAnalyzer
        
        analyzer = ContrarianAnalyzer(db)
        prob, confidence, pattern = analyzer.get_hidden_bearish_probability(
            ticker=ticker,
            event_type=event_type
        )
        
        return {
            "ticker": ticker,
            "event_type": event_type,
            "hidden_bearish_probability": round(prob * 100, 1),
            "confidence": round(confidence * 100, 1),
            "pattern_detected": pattern is not None,
            "sample_size": pattern.total_events if pattern else 0,
            "contrarian_events": pattern.contrarian_events if pattern else 0,
            "avg_decline": round(pattern.avg_negative_divergence, 2) if pattern else None,
            "risk_level": (
                "high" if prob >= 0.6 else
                "medium" if prob >= 0.4 else
                "low"
            )
        }
    finally:
        close_db_session(db)
