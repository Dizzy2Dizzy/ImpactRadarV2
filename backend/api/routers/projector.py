"""
Projector chart endpoints - Advanced trading charts with OHLCV, indicators, and overlays
"""
from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List
from datetime import datetime, timedelta
from pydantic import BaseModel
from concurrent.futures import ThreadPoolExecutor
import asyncio

from api.utils.auth import get_current_user_with_plan
from api.utils.paywall import require_plan
from market_data_service import get_market_data_service
from database import Event, get_db, close_db_session
from services.projection_calculator import calculate_authentic_projection

router = APIRouter(prefix="/projector", tags=["projector"])

# ThreadPoolExecutor for non-blocking yfinance calls
executor = ThreadPoolExecutor(max_workers=8)

class OHLCVDataPoint(BaseModel):
    time: int  # Unix timestamp
    open: float
    high: float
    low: float
    close: float
    volume: int

class EventMarker(BaseModel):
    time: int
    position: str  # 'aboveBar' or 'belowBar'
    color: str
    shape: str  # 'circle', 'square', 'arrowUp', 'arrowDown'
    text: str
    event_id: int
    # Full event details for accurate projections
    title: Optional[str] = None
    event_type: Optional[str] = None
    impact_score: Optional[int] = None
    direction: Optional[str] = None
    confidence: Optional[float] = None
    # ML fields for accurate projected impact calculations
    ml_adjusted_score: Optional[int] = None
    ml_confidence: Optional[float] = None
    impact_p_move: Optional[float] = None  # Predicted % move magnitude
    impact_p_up: Optional[float] = None    # Probability of upward move
    impact_p_down: Optional[float] = None  # Probability of downward move
    model_source: Optional[str] = None     # 'family-specific' | 'global' | 'deterministic'
    # Bearish signal fields
    bearish_signal: bool = False
    bearish_score: Optional[float] = None
    bearish_confidence: Optional[float] = None
    bearish_rationale: Optional[str] = None

class IndicatorData(BaseModel):
    time: int
    value: Optional[float]

class ProjectorResponse(BaseModel):
    ticker: str
    interval: str
    ohlcv: List[OHLCVDataPoint]
    events: List[EventMarker]
    indicators: dict  # {'sma_20': List[IndicatorData], ...}

class FullProjectorResponse(BaseModel):
    """Aggregated response with all indicators in one call"""
    ticker: str
    interval: str
    ohlcv: List[OHLCVDataPoint]
    events: List[EventMarker]
    indicators: dict  # SMA, EMA indicators
    rsi: List[IndicatorData]
    macd: dict  # {'macd': [], 'signal': [], 'histogram': []}
    
@router.get("/ohlcv", response_model=ProjectorResponse)
async def get_projector_ohlcv(
    ticker: str = Query(..., description="Stock ticker symbol"),
    interval: str = Query('1d', description="Time interval: 1m, 5m, 15m, 30m, 1h, 1d, 1w"),
    period: str = Query('3mo', description="Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y"),
    include_events: bool = Query(True, description="Include Impact Radar event markers"),
    include_indicators: bool = Query(True, description="Include technical indicators"),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get comprehensive OHLCV data for Projector chart with events and indicators.
    Pro/Enterprise feature.
    """
    # Require Pro plan
    require_plan(user_data["plan"], "pro", "Projector Chart", user_data.get("trial_ends_at"))
    
    # Fetch OHLCV data using singleton and async executor with timeout
    market_service = get_market_data_service()
    loop = asyncio.get_event_loop()
    try:
        ohlcv_data = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                lambda: market_service.get_ohlcv(ticker, interval, period)
            ),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Market data service timed out while fetching {ticker} data. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market data: {str(e)}"
        )
    
    if not ohlcv_data:
        raise HTTPException(
            status_code=404,
            detail=f"No market data available for {ticker}"
        )
    
    # Fetch events for this ticker
    event_markers = []
    if include_events:
        db = get_db()
        try:
            # Get events from last 6 months
            start_time = datetime.now() - timedelta(days=180)
            events = db.query(Event).filter(
                Event.ticker == ticker.upper(),
                Event.date >= start_time
            ).order_by(Event.date.asc()).all()
            
            for event in events:
                # Determine marker properties based on event direction
                if event.direction == 'positive':
                    color = '#10b981'  # Green
                    shape = 'arrowUp'
                    position = 'belowBar'
                elif event.direction == 'negative':
                    color = '#ef4444'  # Red
                    shape = 'arrowDown'
                    position = 'aboveBar'
                else:
                    color = '#6b7280'  # Gray
                    shape = 'circle'
                    position = 'aboveBar'
                
                # Calculate authentic projection for this event
                projection = calculate_authentic_projection(
                    event_id=event.id,
                    ticker=event.ticker,
                    event_type=event.event_type,
                    title=event.title or "",
                    direction=event.direction or "neutral",
                    impact_score=event.impact_score or 50,
                    ml_adjusted_score=event.ml_adjusted_score,
                    sector=getattr(event, 'sector', None),
                    confidence=event.confidence or 0.5,
                )
                
                # Use authentic projections instead of stored NULL values
                # Use abs() to ensure magnitude is always positive (valid probability)
                impact_p_move = abs(projection.projected_move_pct) / 100 if projection.projected_move_pct else 0
                impact_p_up = projection.probability_up
                impact_p_down = projection.probability_down
                
                event_markers.append(EventMarker(
                    time=int(event.date.timestamp()),
                    position=position,
                    color=color,
                    shape=shape,
                    text=f"{event.event_type}: {event.impact_score}",
                    event_id=event.id,
                    title=event.title,
                    event_type=event.event_type,
                    impact_score=event.impact_score,
                    direction=event.direction,
                    confidence=event.confidence,
                    ml_adjusted_score=event.ml_adjusted_score,
                    ml_confidence=event.ml_confidence,
                    impact_p_move=impact_p_move,
                    impact_p_up=impact_p_up,
                    impact_p_down=impact_p_down,
                    model_source=projection.data_source,
                    bearish_signal=getattr(event, 'bearish_signal', False) or False,
                    bearish_score=getattr(event, 'bearish_score', None),
                    bearish_confidence=getattr(event, 'bearish_confidence', None),
                    bearish_rationale=getattr(event, 'bearish_rationale', None),
                ))
        finally:
            close_db_session(db)
    
    # Calculate indicators
    indicators = {}
    if include_indicators and ohlcv_data:
        closes = [d['close'] for d in ohlcv_data]
        times = [d['time'] for d in ohlcv_data]
        
        # SMA 20, 50, 200
        sma_20 = market_service.calculate_sma(closes, 20)
        sma_50 = market_service.calculate_sma(closes, 50)
        sma_200 = market_service.calculate_sma(closes, 200)
        
        # EMA 20, 50
        ema_20 = market_service.calculate_ema(closes, 20)
        ema_50 = market_service.calculate_ema(closes, 50)
        
        indicators['sma_20'] = [
            IndicatorData(time=times[i], value=sma_20[i])
            for i in range(len(times))
        ]
        indicators['sma_50'] = [
            IndicatorData(time=times[i], value=sma_50[i])
            for i in range(len(times))
        ]
        indicators['sma_200'] = [
            IndicatorData(time=times[i], value=sma_200[i])
            for i in range(len(times))
        ]
        indicators['ema_20'] = [
            IndicatorData(time=times[i], value=ema_20[i])
            for i in range(len(times))
        ]
        indicators['ema_50'] = [
            IndicatorData(time=times[i], value=ema_50[i])
            for i in range(len(times))
        ]
    
    return ProjectorResponse(
        ticker=ticker,
        interval=interval,
        ohlcv=[OHLCVDataPoint(**d) for d in ohlcv_data],
        events=event_markers,
        indicators=indicators
    )

@router.get("/full", response_model=FullProjectorResponse)
async def get_full_projector_data(
    ticker: str = Query(..., description="Stock ticker symbol"),
    interval: str = Query('1d', description="Time interval: 1m, 5m, 15m, 30m, 1h, 1d, 1w"),
    period: str = Query('3mo', description="Time period: 1d, 5d, 1mo, 3mo, 6mo, 1y"),
    rsi_period: int = Query(14, description="RSI period"),
    fast_period: int = Query(12, description="MACD fast period"),
    slow_period: int = Query(26, description="MACD slow period"),
    signal_period: int = Query(9, description="MACD signal period"),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """
    Get complete Projector data with all indicators in ONE call.
    This endpoint fetches OHLCV once and calculates all indicators,
    significantly faster than multiple separate calls.
    Pro/Enterprise feature.
    """
    # Require Pro plan
    require_plan(user_data["plan"], "pro", "Projector Chart", user_data.get("trial_ends_at"))
    
    # Fetch OHLCV data ONCE using singleton and async executor
    market_service = get_market_data_service()
    loop = asyncio.get_event_loop()
    try:
        ohlcv_data = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                lambda: market_service.get_ohlcv(ticker, interval, period)
            ),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Market data service timed out while fetching {ticker} data. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch market data: {str(e)}"
        )
    
    if not ohlcv_data:
        raise HTTPException(
            status_code=404,
            detail=f"No market data available for {ticker}"
        )
    
    # Fetch events for this ticker
    event_markers = []
    db = get_db()
    try:
        start_time = datetime.now() - timedelta(days=180)
        events = db.query(Event).filter(
            Event.ticker == ticker.upper(),
            Event.date >= start_time
        ).order_by(Event.date.asc()).all()
        
        for event in events:
            if event.direction == 'positive':
                color, shape, position = '#10b981', 'arrowUp', 'belowBar'
            elif event.direction == 'negative':
                color, shape, position = '#ef4444', 'arrowDown', 'aboveBar'
            else:
                color, shape, position = '#6b7280', 'circle', 'aboveBar'
            
            # Calculate authentic projection for this event
            projection = calculate_authentic_projection(
                event_id=event.id,
                ticker=event.ticker,
                event_type=event.event_type,
                title=event.title or "",
                direction=event.direction or "neutral",
                impact_score=event.impact_score or 50,
                ml_adjusted_score=event.ml_adjusted_score,
                sector=getattr(event, 'sector', None),
                confidence=event.confidence or 0.5,
            )
            
            # Use authentic projections
            # Use abs() to ensure magnitude is always positive (valid probability)
            impact_p_move = abs(projection.projected_move_pct) / 100 if projection.projected_move_pct else 0
            impact_p_up = projection.probability_up
            impact_p_down = projection.probability_down
            
            event_markers.append(EventMarker(
                time=int(event.date.timestamp()),
                position=position,
                color=color,
                shape=shape,
                text=f"{event.event_type}: {event.impact_score}",
                event_id=event.id,
                title=event.title,
                event_type=event.event_type,
                impact_score=event.impact_score,
                direction=event.direction,
                confidence=event.confidence,
                ml_adjusted_score=event.ml_adjusted_score,
                ml_confidence=event.ml_confidence,
                impact_p_move=impact_p_move,
                impact_p_up=impact_p_up,
                impact_p_down=impact_p_down,
                model_source=projection.data_source,
                bearish_signal=getattr(event, 'bearish_signal', False) or False,
                bearish_score=getattr(event, 'bearish_score', None),
                bearish_confidence=getattr(event, 'bearish_confidence', None),
                bearish_rationale=getattr(event, 'bearish_rationale', None),
            ))
    finally:
        close_db_session(db)
    
    # Extract closes and times ONCE
    closes = [d['close'] for d in ohlcv_data]
    times = [d['time'] for d in ohlcv_data]
    
    # Calculate ALL indicators from the single OHLCV dataset
    # SMA indicators
    sma_20 = market_service.calculate_sma(closes, 20)
    sma_50 = market_service.calculate_sma(closes, 50)
    sma_200 = market_service.calculate_sma(closes, 200)
    
    # EMA indicators
    ema_20 = market_service.calculate_ema(closes, 20)
    ema_50 = market_service.calculate_ema(closes, 50)
    
    # RSI indicator
    rsi_values = market_service.calculate_rsi(closes, rsi_period)
    
    # MACD indicator
    macd, signal, histogram = market_service.calculate_macd(closes, fast_period, slow_period, signal_period)
    
    # Format indicators
    indicators = {
        'sma_20': [IndicatorData(time=times[i], value=sma_20[i]) for i in range(len(times))],
        'sma_50': [IndicatorData(time=times[i], value=sma_50[i]) for i in range(len(times))],
        'sma_200': [IndicatorData(time=times[i], value=sma_200[i]) for i in range(len(times))],
        'ema_20': [IndicatorData(time=times[i], value=ema_20[i]) for i in range(len(times))],
        'ema_50': [IndicatorData(time=times[i], value=ema_50[i]) for i in range(len(times))],
    }
    
    # Format RSI
    rsi_data = [IndicatorData(time=times[i], value=rsi_values[i]) for i in range(len(times))]
    
    # Format MACD
    macd_data = {
        'macd': [{'time': times[i], 'value': macd[i]} for i in range(len(times))],
        'signal': [{'time': times[i], 'value': signal[i]} for i in range(len(times))],
        'histogram': [{'time': times[i], 'value': histogram[i]} for i in range(len(times))]
    }
    
    return FullProjectorResponse(
        ticker=ticker,
        interval=interval,
        ohlcv=[OHLCVDataPoint(**d) for d in ohlcv_data],
        events=event_markers,
        indicators=indicators,
        rsi=rsi_data,
        macd=macd_data
    )

@router.get("/indicators/rsi")
async def get_rsi_indicator(
    ticker: str = Query(..., description="Stock ticker symbol"),
    interval: str = Query('1d', description="Time interval"),
    period: str = Query('3mo', description="Time period"),
    rsi_period: int = Query(14, description="RSI period"),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """Get RSI indicator data. Pro/Enterprise feature."""
    require_plan(user_data["plan"], "pro", "RSI Indicator", user_data.get("trial_ends_at"))
    
    market_service = get_market_data_service()
    loop = asyncio.get_event_loop()
    try:
        ohlcv_data = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                lambda: market_service.get_ohlcv(ticker, interval, period)
            ),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Market data service timed out while fetching RSI data for {ticker}. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch RSI data: {str(e)}"
        )
    
    if not ohlcv_data:
        raise HTTPException(
            status_code=404,
            detail=f"No market data available for {ticker}"
        )
    
    closes = [d['close'] for d in ohlcv_data]
    times = [d['time'] for d in ohlcv_data]
    rsi_values = market_service.calculate_rsi(closes, rsi_period)
    
    return {
        "rsi": [
            {"time": times[i], "value": rsi_values[i]}
            for i in range(len(times))
        ]
    }

@router.get("/indicators/ema")
async def get_ema_indicator(
    ticker: str = Query(..., description="Stock ticker symbol"),
    interval: str = Query('1d', description="Time interval"),
    period: str = Query('3mo', description="Time period"),
    ema_period: int = Query(20, description="EMA period"),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """Get EMA indicator data. Pro/Enterprise feature."""
    require_plan(user_data["plan"], "pro", "EMA Indicator", user_data.get("trial_ends_at"))
    
    market_service = get_market_data_service()
    loop = asyncio.get_event_loop()
    try:
        ohlcv_data = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                lambda: market_service.get_ohlcv(ticker, interval, period)
            ),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Market data service timed out while fetching EMA data for {ticker}. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch EMA data: {str(e)}"
        )
    
    if not ohlcv_data:
        raise HTTPException(
            status_code=404,
            detail=f"No market data available for {ticker}"
        )
    
    closes = [d['close'] for d in ohlcv_data]
    times = [d['time'] for d in ohlcv_data]
    ema_values = market_service.calculate_ema(closes, ema_period)
    
    return {
        "ema": [
            {"time": times[i], "value": ema_values[i]}
            for i in range(len(times))
        ]
    }

@router.get("/indicators/macd")
async def get_macd_indicator(
    ticker: str = Query(..., description="Stock ticker symbol"),
    interval: str = Query('1d', description="Time interval"),
    period: str = Query('3mo', description="Time period"),
    fast_period: int = Query(12, description="MACD fast period"),
    slow_period: int = Query(26, description="MACD slow period"),
    signal_period: int = Query(9, description="MACD signal period"),
    user_data: dict = Depends(get_current_user_with_plan)
):
    """Get MACD indicator data. Pro/Enterprise feature."""
    require_plan(user_data["plan"], "pro", "MACD Indicator", user_data.get("trial_ends_at"))
    
    market_service = get_market_data_service()
    loop = asyncio.get_event_loop()
    try:
        ohlcv_data = await asyncio.wait_for(
            loop.run_in_executor(
                executor,
                lambda: market_service.get_ohlcv(ticker, interval, period)
            ),
            timeout=30.0
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=504,
            detail=f"Market data service timed out while fetching MACD data for {ticker}. Please try again."
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch MACD data: {str(e)}"
        )
    
    if not ohlcv_data:
        raise HTTPException(
            status_code=404,
            detail=f"No market data available for {ticker}"
        )
    
    closes = [d['close'] for d in ohlcv_data]
    times = [d['time'] for d in ohlcv_data]
    macd, signal, histogram = market_service.calculate_macd(closes, fast_period, slow_period, signal_period)
    
    return {
        "macd": [{"time": times[i], "value": macd[i]} for i in range(len(times))],
        "signal": [{"time": times[i], "value": signal[i]} for i in range(len(times))],
        "histogram": [{"time": times[i], "value": histogram[i]} for i in range(len(times))]
    }
