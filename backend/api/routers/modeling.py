"""
Modeling API Router

Endpoints for topological stock analysis, visualization, and strategy backtesting
using persistent homology and Takens delay embeddings.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from datetime import date, datetime, timedelta
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
import numpy as np
import logging

from database import get_db
from releaseradar.services.persistent_topology import (
    PersistentTopologyService, 
    PersistenceFeatures,
    TakensEmbedding
)
from api.utils.auth import get_current_user_with_plan
from api.utils.paywall import require_plan

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/modeling", tags=["modeling"])


class TopologyPreviewRequest(BaseModel):
    """Request for computing topology preview of a stock."""
    ticker: str = Field(..., min_length=1, max_length=10, description="Stock ticker symbol")
    end_date: date = Field(..., description="End date for analysis")
    lookback_days: int = Field(30, ge=10, le=365, description="Days of price history")
    embedding_dim: int = Field(3, ge=2, le=10, description="Takens embedding dimension (m)")
    delay: int = Field(2, ge=1, le=10, description="Time delay for embedding (τ)")


class TopologyPreviewResponse(BaseModel):
    """Response containing topology analysis results."""
    ticker: str
    analysis_date: date
    lookback_days: int
    embedding_dim: int
    delay: int
    
    embedding_points: List[List[float]]
    prices: List[float]
    dates: List[str]
    returns: List[float]
    
    persistence_diagram_h0: List[List[float]]
    persistence_diagram_h1: List[List[float]]
    
    betti_curve_scales: List[float]
    betti_curve_h0: List[int]
    betti_curve_h1: List[int]
    
    features: Dict[str, float]
    
    has_data: bool
    error_message: Optional[str] = None


class ModelingBacktestRequest(BaseModel):
    """Request for running a topology-based backtest."""
    ticker: str = Field(..., min_length=1, max_length=10)
    start_date: date = Field(...)
    end_date: date = Field(...)
    
    embedding_dim: int = Field(3, ge=2, le=10)
    delay: int = Field(2, ge=1, le=10)
    lookback_days: int = Field(30, ge=10, le=90)
    
    entry_conditions: Dict[str, Any] = Field(..., description="Topology-based entry rules")
    exit_conditions: Dict[str, Any] = Field(default_factory=dict, description="Exit rules")
    
    initial_capital: float = Field(10000.0, gt=0)
    position_size_pct: float = Field(100.0, gt=0, le=100)
    max_holding_days: int = Field(10, ge=1, le=60)


class TradeResult(BaseModel):
    """Individual trade result."""
    entry_date: str
    exit_date: str
    entry_price: float
    exit_price: float
    return_pct: float
    profit_loss: float
    holding_days: int
    entry_reason: str
    exit_reason: str
    topology_features_at_entry: Dict[str, float]


class ModelingBacktestResponse(BaseModel):
    """Response from topology-based backtest."""
    ticker: str
    start_date: str
    end_date: str
    
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    
    total_return_pct: float
    sharpe_ratio: Optional[float]
    max_drawdown_pct: float
    avg_holding_days: float
    
    trades: List[TradeResult]
    equity_curve: List[Dict[str, Any]]
    
    initial_capital: float
    final_capital: float


class EventMarkersRequest(BaseModel):
    """Request for event markers overlay."""
    ticker: str
    start_date: date
    end_date: date


class EventMarker(BaseModel):
    """Event marker for overlay on charts."""
    date: str
    event_type: str
    title: str
    impact_score: float
    direction: str


@router.post("/topology/preview", response_model=TopologyPreviewResponse)
async def get_topology_preview(
    request: TopologyPreviewRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_with_plan)
):
    """
    Compute topology preview for a stock.
    
    Returns Takens embedding points, persistence diagrams, Betti curves,
    and extracted topological features for visualization.
    """
    require_plan(current_user.get("plan", "free"), "pro", "Modeling Workspace")
    
    try:
        service = PersistentTopologyService(db)
        
        n_required = (request.embedding_dim - 1) * request.delay + 1
        min_lookback = max(request.lookback_days, n_required + 15)
        min_data_points = 15
        
        prices, dates, returns = _fetch_price_data(request.ticker, request.end_date, min_lookback)
        
        if returns is None or len(returns) < min_data_points:
            return TopologyPreviewResponse(
                ticker=request.ticker,
                analysis_date=request.end_date,
                lookback_days=request.lookback_days,
                embedding_dim=request.embedding_dim,
                delay=request.delay,
                embedding_points=[],
                prices=[],
                dates=[],
                returns=[],
                persistence_diagram_h0=[],
                persistence_diagram_h1=[],
                betti_curve_scales=[],
                betti_curve_h0=[],
                betti_curve_h1=[],
                features={},
                has_data=False,
                error_message=f"Unable to fetch sufficient price data for {request.ticker}. Please check the ticker symbol and try a different date range."
            )
        
        returns_std = (returns - np.mean(returns)) / (np.std(returns) + 1e-8)
        embedding = service._create_takens_embedding(returns_std, request.embedding_dim, request.delay)
        embedding_points = embedding.points.tolist() if embedding.points.shape[0] > 0 else []
        
        if len(embedding_points) < 5:
            return TopologyPreviewResponse(
                ticker=request.ticker,
                analysis_date=request.end_date,
                lookback_days=request.lookback_days,
                embedding_dim=request.embedding_dim,
                delay=request.delay,
                embedding_points=[],
                prices=prices if prices else [],
                dates=dates if dates else [],
                returns=returns.tolist() if returns is not None else [],
                persistence_diagram_h0=[],
                persistence_diagram_h1=[],
                betti_curve_scales=[],
                betti_curve_h0=[],
                betti_curve_h1=[],
                features={},
                has_data=False,
                error_message="Not enough data points for topological analysis. Try increasing the lookback period."
            )
        
        persistence_result = None
        try:
            persistence_result = service._compute_persistence(np.array(embedding_points))
        except Exception as e:
            logger.warning(f"Persistence computation failed: {e}")
        
        h0_diagram = []
        h1_diagram = []
        if persistence_result and 'dgms' in persistence_result:
            dgms = persistence_result['dgms']
            if len(dgms) > 0:
                for birth, death in dgms[0]:
                    if not np.isinf(death):
                        h0_diagram.append([float(birth), float(death)])
            if len(dgms) > 1:
                for birth, death in dgms[1]:
                    if not np.isinf(death):
                        h1_diagram.append([float(birth), float(death)])
        
        betti_scales, betti_h0, betti_h1 = _compute_betti_curves(h0_diagram, h1_diagram)
        
        features = service._extract_features(persistence_result) if persistence_result else PersistenceFeatures()
        
        feature_dict = {
            'betti0_count': features.betti0_count,
            'betti1_count': features.betti1_count,
            'max_lifetime_h0': features.max_lifetime_h0,
            'max_lifetime_h1': features.max_lifetime_h1,
            'mean_lifetime_h0': features.mean_lifetime_h0,
            'mean_lifetime_h1': features.mean_lifetime_h1,
            'total_persistence_h0': features.total_persistence_h0,
            'total_persistence_h1': features.total_persistence_h1,
            'persistence_entropy': features.persistence_entropy,
            'betti_curve_h0_mean': features.betti_curve_h0_mean,
            'betti_curve_h1_mean': features.betti_curve_h1_mean,
            'topological_complexity': features.topological_complexity
        }
        
        return TopologyPreviewResponse(
            ticker=request.ticker,
            analysis_date=request.end_date,
            lookback_days=request.lookback_days,
            embedding_dim=request.embedding_dim,
            delay=request.delay,
            embedding_points=embedding_points,
            prices=prices if prices else [],
            dates=dates if dates else [],
            returns=returns.tolist() if returns is not None else [],
            persistence_diagram_h0=h0_diagram,
            persistence_diagram_h1=h1_diagram,
            betti_curve_scales=betti_scales,
            betti_curve_h0=betti_h0,
            betti_curve_h1=betti_h1,
            features=feature_dict,
            has_data=True
        )
        
    except Exception as e:
        logger.exception(f"Error in topology preview: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to compute topology: {str(e)}"
        )


@router.get("/events", response_model=List[EventMarker])
async def get_event_markers(
    ticker: str = Query(..., min_length=1, max_length=10),
    start_date: date = Query(...),
    end_date: date = Query(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_with_plan)
):
    """
    Get event markers for overlay on modeling charts.
    """
    require_plan(current_user.get("plan", "free"), "pro", "Modeling Events")
    
    try:
        from releaseradar.db.models import Event
        
        events = db.query(Event).filter(
            Event.ticker == ticker.upper(),
            Event.date >= start_date,
            Event.date <= end_date
        ).order_by(Event.date).all()
        
        markers = []
        for event in events:
            markers.append(EventMarker(
                date=event.date.strftime('%Y-%m-%d'),
                event_type=event.event_type or 'unknown',
                title=event.title[:100] if event.title else '',
                impact_score=float(event.impact_score) if event.impact_score else 0.0,
                direction=event.direction or 'neutral'
            ))
        
        return markers
        
    except Exception as e:
        logger.exception(f"Error fetching event markers: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch events: {str(e)}"
        )


@router.post("/backtest", response_model=ModelingBacktestResponse)
async def run_topology_backtest(
    request: ModelingBacktestRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_with_plan)
):
    """
    Run a topology-based backtesting strategy.
    
    Entry conditions can include:
    - betti1_count: {"operator": ">", "value": 5}
    - persistence_entropy: {"operator": ">", "value": 0.7}
    - topological_complexity: {"operator": ">", "value": 50}
    
    Exit conditions:
    - holding_days: Maximum days to hold
    - stop_loss_pct: Stop loss percentage
    - take_profit_pct: Take profit percentage
    """
    require_plan(current_user.get("plan", "free"), "pro", "Strategy Lab Backtest")
    
    try:
        service = PersistentTopologyService(db)
        
        prices, dates, returns = _fetch_price_data_range(
            request.ticker, 
            request.start_date, 
            request.end_date
        )
        
        if prices is None or len(prices) < request.lookback_days + 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient price data for {request.ticker}"
            )
        
        trades = []
        equity_curve = []
        capital = request.initial_capital
        position = None
        
        for i in range(request.lookback_days, len(prices)):
            current_date = dates[i]
            current_price = prices[i]
            
            equity_curve.append({
                'date': current_date,
                'equity': capital + (position['shares'] * current_price if position else 0),
                'in_position': position is not None
            })
            
            if position:
                days_held = (datetime.strptime(current_date, '%Y-%m-%d') - 
                           datetime.strptime(position['entry_date'], '%Y-%m-%d')).days
                
                pnl_pct = (current_price - position['entry_price']) / position['entry_price'] * 100
                
                exit_reason = None
                
                if days_held >= request.max_holding_days:
                    exit_reason = 'max_holding_days'
                elif 'stop_loss_pct' in request.exit_conditions and pnl_pct <= -request.exit_conditions['stop_loss_pct']:
                    exit_reason = 'stop_loss'
                elif 'take_profit_pct' in request.exit_conditions and pnl_pct >= request.exit_conditions['take_profit_pct']:
                    exit_reason = 'take_profit'
                
                if exit_reason:
                    profit_loss = position['shares'] * (current_price - position['entry_price'])
                    capital += position['shares'] * current_price
                    
                    trades.append(TradeResult(
                        entry_date=position['entry_date'],
                        exit_date=current_date,
                        entry_price=position['entry_price'],
                        exit_price=current_price,
                        return_pct=pnl_pct,
                        profit_loss=profit_loss,
                        holding_days=days_held,
                        entry_reason=position['entry_reason'],
                        exit_reason=exit_reason,
                        topology_features_at_entry=position['features']
                    ))
                    position = None
            
            else:
                lookback_returns = returns[i - request.lookback_days:i]
                if len(lookback_returns) >= request.lookback_days:
                    returns_std = (lookback_returns - np.mean(lookback_returns)) / (np.std(lookback_returns) + 1e-8)
                    
                    embedding = service._create_takens_embedding(
                        returns_std, 
                        request.embedding_dim, 
                        request.delay
                    )
                    
                    if embedding.points.shape[0] >= 5:
                        persistence_result = service._compute_persistence(embedding.points)
                        features = service._extract_features(persistence_result)
                        
                        should_enter, reason = _check_entry_conditions(
                            features, 
                            request.entry_conditions
                        )
                        
                        if should_enter:
                            position_value = capital * (request.position_size_pct / 100)
                            shares = position_value / current_price
                            capital -= position_value
                            
                            position = {
                                'entry_date': current_date,
                                'entry_price': current_price,
                                'shares': shares,
                                'entry_reason': reason,
                                'features': {
                                    'betti0_count': features.betti0_count,
                                    'betti1_count': features.betti1_count,
                                    'persistence_entropy': features.persistence_entropy,
                                    'topological_complexity': features.topological_complexity
                                }
                            }
        
        if position:
            final_price = prices[-1]
            pnl_pct = (final_price - position['entry_price']) / position['entry_price'] * 100
            days_held = (datetime.strptime(dates[-1], '%Y-%m-%d') - 
                        datetime.strptime(position['entry_date'], '%Y-%m-%d')).days
            profit_loss = position['shares'] * (final_price - position['entry_price'])
            capital += position['shares'] * final_price
            
            trades.append(TradeResult(
                entry_date=position['entry_date'],
                exit_date=dates[-1],
                entry_price=position['entry_price'],
                exit_price=final_price,
                return_pct=pnl_pct,
                profit_loss=profit_loss,
                holding_days=days_held,
                entry_reason=position['entry_reason'],
                exit_reason='end_of_period',
                topology_features_at_entry=position['features']
            ))
        
        winning_trades = [t for t in trades if t.return_pct > 0]
        losing_trades = [t for t in trades if t.return_pct <= 0]
        
        total_return_pct = (capital - request.initial_capital) / request.initial_capital * 100
        
        max_drawdown = _calculate_max_drawdown(equity_curve)
        sharpe = _calculate_sharpe_ratio(trades) if trades else None
        avg_holding = sum(t.holding_days for t in trades) / len(trades) if trades else 0
        
        return ModelingBacktestResponse(
            ticker=request.ticker,
            start_date=str(request.start_date),
            end_date=str(request.end_date),
            total_trades=len(trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            win_rate=len(winning_trades) / len(trades) * 100 if trades else 0,
            total_return_pct=total_return_pct,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_drawdown,
            avg_holding_days=avg_holding,
            trades=trades,
            equity_curve=equity_curve,
            initial_capital=request.initial_capital,
            final_capital=capital
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error in topology backtest: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtest failed: {str(e)}"
        )


def _fetch_price_data(ticker: str, end_date: date, lookback_days: int):
    """Fetch price data for a ticker."""
    try:
        import yfinance as yf
        
        start = end_date - timedelta(days=lookback_days + 30)
        data = yf.download(ticker, start=start.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
        
        if data.empty:
            return None, None, None
        
        if 'Adj Close' in data.columns:
            prices = data['Adj Close'].values
        elif 'Close' in data.columns:
            prices = data['Close'].values
        else:
            prices = data.iloc[:, 0].values
        
        if hasattr(prices, 'flatten'):
            prices = prices.flatten()
        
        dates = [d.strftime('%Y-%m-%d') for d in data.index]
        
        log_prices = np.log(prices)
        returns = np.diff(log_prices)
        
        return prices[-lookback_days:].tolist(), dates[-lookback_days:], returns[-lookback_days+1:]
        
    except Exception as e:
        logger.warning(f"Error fetching price data for {ticker}: {e}")
        return None, None, None


def _fetch_price_data_range(ticker: str, start_date: date, end_date: date):
    """Fetch price data for a date range."""
    try:
        import yfinance as yf
        
        buffer_start = start_date - timedelta(days=60)
        data = yf.download(ticker, start=buffer_start.strftime('%Y-%m-%d'), end=end_date.strftime('%Y-%m-%d'), progress=False)
        
        if data.empty:
            return None, None, None
        
        if 'Adj Close' in data.columns:
            prices = data['Adj Close'].values
        elif 'Close' in data.columns:
            prices = data['Close'].values
        else:
            prices = data.iloc[:, 0].values
        
        if hasattr(prices, 'flatten'):
            prices = prices.flatten()
        
        dates = [d.strftime('%Y-%m-%d') for d in data.index]
        
        log_prices = np.log(prices)
        returns = np.diff(log_prices)
        
        return prices.tolist(), dates, returns
        
    except Exception as e:
        logger.warning(f"Error fetching price data for {ticker}: {e}")
        return None, None, None


def _compute_betti_curves(h0_diagram: List[List[float]], h1_diagram: List[List[float]], n_samples: int = 50):
    """Compute Betti curves from persistence diagrams."""
    all_points = h0_diagram + h1_diagram
    if not all_points:
        return [], [], []
    
    min_birth = min(p[0] for p in all_points)
    max_death = max(p[1] for p in all_points)
    
    if max_death <= min_birth:
        return [], [], []
    
    scales = np.linspace(min_birth, max_death, n_samples).tolist()
    betti_h0 = []
    betti_h1 = []
    
    for scale in scales:
        count_h0 = sum(1 for p in h0_diagram if p[0] <= scale < p[1])
        count_h1 = sum(1 for p in h1_diagram if p[0] <= scale < p[1])
        betti_h0.append(count_h0)
        betti_h1.append(count_h1)
    
    return scales, betti_h0, betti_h1


def _check_entry_conditions(features: PersistenceFeatures, conditions: Dict[str, Any]) -> tuple:
    """Check if entry conditions are met based on topology features."""
    for feature_name, condition in conditions.items():
        if not hasattr(features, feature_name):
            continue
        
        feature_value = getattr(features, feature_name)
        operator = condition.get('operator', '>')
        threshold = condition.get('value', 0)
        
        if operator == '>' and feature_value <= threshold:
            return False, None
        elif operator == '>=' and feature_value < threshold:
            return False, None
        elif operator == '<' and feature_value >= threshold:
            return False, None
        elif operator == '<=' and feature_value > threshold:
            return False, None
        elif operator == '==' and feature_value != threshold:
            return False, None
    
    triggered = list(conditions.keys())
    return True, f"topology_signal: {', '.join(triggered)}"


def _calculate_max_drawdown(equity_curve: List[Dict]) -> float:
    """Calculate maximum drawdown from equity curve."""
    if not equity_curve:
        return 0.0
    
    equities = [e['equity'] for e in equity_curve]
    peak = equities[0]
    max_dd = 0.0
    
    for equity in equities:
        if equity > peak:
            peak = equity
        dd = (peak - equity) / peak * 100 if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    return max_dd


def _calculate_sharpe_ratio(trades: List[TradeResult], risk_free_rate: float = 0.02) -> Optional[float]:
    """Calculate Sharpe ratio from trades."""
    if len(trades) < 2:
        return None
    
    returns = [t.return_pct / 100 for t in trades]
    avg_return = np.mean(returns)
    std_return = np.std(returns)
    
    if std_return < 0.0001:
        return None
    
    annual_factor = 252 / np.mean([t.holding_days for t in trades]) if trades else 252
    sharpe = (avg_return * annual_factor - risk_free_rate) / (std_return * np.sqrt(annual_factor))
    
    return round(sharpe, 2)
