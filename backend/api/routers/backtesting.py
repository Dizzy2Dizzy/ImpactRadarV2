"""
Strategy Backtesting API Router

Endpoints for creating trading strategies and running backtests.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from datetime import date, datetime
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc, select, func
from collections import defaultdict

from database import get_db, close_db_session
from releaseradar.db.models import UserStrategy, BacktestRun, BacktestResult, EventOutcome, Event, ModelRegistry
from releaseradar.services.backtesting_engine import run_backtest
from releaseradar.services.backtesting import BacktestEngine, BacktestEngineResult
from releaseradar.ml.event_type_families import get_event_family, get_family_display_name, EVENT_TYPE_FAMILIES
from api.utils.auth import get_current_user_with_plan
from api.utils.paywall import require_plan
from api.dependencies import get_data_manager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/backtesting", tags=["backtesting"])


# Request Models
class CreateStrategyRequest(BaseModel):
    """Request model for creating a new trading strategy"""
    name: str = Field(..., min_length=1, max_length=200, description="Strategy name")
    description: Optional[str] = Field(None, max_length=1000, description="Strategy description")
    entry_conditions: Dict[str, Any] = Field(..., description="JSON conditions for entering positions")
    exit_conditions: Optional[Dict[str, Any]] = Field(None, description="JSON conditions for exiting positions")
    position_sizing: Optional[Dict[str, Any]] = Field(None, description="Position sizing configuration")
    risk_management: Optional[Dict[str, Any]] = Field(None, description="Risk management rules")
    tickers: Optional[List[str]] = Field(None, description="Filter by specific tickers")
    sectors: Optional[List[str]] = Field(None, description="Filter by specific sectors")
    min_score_threshold: Optional[int] = Field(None, ge=0, le=100, description="Minimum impact score")
    active: bool = Field(True, description="Whether strategy is active")


class UpdateStrategyRequest(BaseModel):
    """Request model for updating an existing strategy"""
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    entry_conditions: Optional[Dict[str, Any]] = None
    exit_conditions: Optional[Dict[str, Any]] = None
    position_sizing: Optional[Dict[str, Any]] = None
    risk_management: Optional[Dict[str, Any]] = None
    tickers: Optional[List[str]] = None
    sectors: Optional[List[str]] = None
    min_score_threshold: Optional[int] = Field(None, ge=0, le=100)
    active: Optional[bool] = None


class RunBacktestRequest(BaseModel):
    """Request model for running a backtest"""
    strategy_id: int = Field(..., description="ID of strategy to backtest")
    start_date: date = Field(..., description="Backtest start date (YYYY-MM-DD)")
    end_date: date = Field(..., description="Backtest end date (YYYY-MM-DD)")
    initial_capital: float = Field(100000.0, gt=0, description="Starting capital in dollars")


# Response Models
class StrategyResponse(BaseModel):
    """Response model for strategy details"""
    id: int
    user_id: int
    name: str
    description: Optional[str]
    active: bool
    entry_conditions: Dict[str, Any]
    exit_conditions: Optional[Dict[str, Any]]
    position_sizing: Optional[Dict[str, Any]]
    risk_management: Optional[Dict[str, Any]]
    tickers: Optional[List[str]]
    sectors: Optional[List[str]]
    min_score_threshold: Optional[int]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class BacktestRunResponse(BaseModel):
    """Response model for backtest run summary"""
    id: int
    strategy_id: int
    user_id: int
    start_date: date
    end_date: date
    initial_capital: float
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    error_message: Optional[str]
    total_trades: Optional[int]
    win_rate: Optional[float]
    total_return_pct: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown_pct: Optional[float]
    
    class Config:
        from_attributes = True


class BacktestResultResponse(BaseModel):
    """Response model for individual trade result"""
    id: int
    run_id: int
    ticker: str
    event_id: Optional[int]
    entry_date: date
    entry_price: float
    exit_date: Optional[date]
    exit_price: Optional[float]
    shares: float
    position_value: float
    return_pct: Optional[float]
    profit_loss: Optional[float]
    exit_reason: Optional[str]
    holding_period_days: Optional[int]
    
    class Config:
        from_attributes = True


# Strategy CRUD Endpoints

@router.post(
    "/strategies",
    response_model=StrategyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new trading strategy",
    description="""
    Create a new trading strategy with custom entry/exit conditions.
    
    Example entry_conditions:
    ```json
    {
        "event_types": ["fda_approval", "earnings"],
        "min_score": 75,
        "directions": ["bullish"],
        "min_confidence": 0.7
    }
    ```
    
    Example exit_conditions:
    ```json
    {
        "type": "fixed_horizon",
        "days": 7
    }
    ```
    
    Example position_sizing:
    ```json
    {
        "type": "equal_weight",
        "max_positions": 10
    }
    ```
    """
)
async def create_strategy(
    request: CreateStrategyRequest,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Create a new trading strategy"""
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Strategy backtesting",
        user_data.get("trial_ends_at")
    )
    
    try:
        strategy = UserStrategy(
            user_id=user_data["user_id"],
            name=request.name,
            description=request.description,
            entry_conditions=request.entry_conditions,
            exit_conditions=request.exit_conditions,
            position_sizing=request.position_sizing,
            risk_management=request.risk_management,
            tickers=request.tickers,
            sectors=request.sectors,
            min_score_threshold=request.min_score_threshold,
            active=request.active
        )
        
        db.add(strategy)
        db.commit()
        db.refresh(strategy)
        
        logger.info(f"Created strategy {strategy.id} for user {user_data['user_id']}")
        
        return StrategyResponse.from_orm(strategy)
        
    finally:
        close_db_session(db)


@router.get(
    "/strategies",
    response_model=List[StrategyResponse],
    summary="List user strategies",
    description="Get all trading strategies for the authenticated user"
)
async def list_strategies(
    active_only: bool = False,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """List all strategies for the current user"""
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Strategy backtesting",
        user_data.get("trial_ends_at")
    )
    
    try:
        query = db.query(UserStrategy).filter(
            UserStrategy.user_id == user_data["user_id"]
        )
        
        if active_only:
            query = query.filter(UserStrategy.active == True)
        
        strategies = query.order_by(desc(UserStrategy.created_at)).all()
        
        return [StrategyResponse.from_orm(s) for s in strategies]
        
    finally:
        close_db_session(db)


@router.get(
    "/strategies/{strategy_id}",
    response_model=StrategyResponse,
    summary="Get strategy details",
    description="Get details of a specific trading strategy"
)
async def get_strategy(
    strategy_id: int,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Get a specific strategy by ID"""
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Strategy backtesting",
        user_data.get("trial_ends_at")
    )
    
    try:
        strategy = db.query(UserStrategy).filter(
            and_(
                UserStrategy.id == strategy_id,
                UserStrategy.user_id == user_data["user_id"]
            )
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found"
            )
        
        return StrategyResponse.from_orm(strategy)
        
    finally:
        close_db_session(db)


@router.put(
    "/strategies/{strategy_id}",
    response_model=StrategyResponse,
    summary="Update a trading strategy",
    description="Update an existing trading strategy's configuration"
)
async def update_strategy(
    strategy_id: int,
    request: UpdateStrategyRequest,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Update an existing strategy"""
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Strategy backtesting",
        user_data.get("trial_ends_at")
    )
    
    try:
        strategy = db.query(UserStrategy).filter(
            and_(
                UserStrategy.id == strategy_id,
                UserStrategy.user_id == user_data["user_id"]
            )
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found"
            )
        
        # Update fields if provided
        update_data = request.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(strategy, field, value)
        
        strategy.updated_at = datetime.utcnow()
        
        db.commit()
        db.refresh(strategy)
        
        logger.info(f"Updated strategy {strategy_id}")
        
        return StrategyResponse.from_orm(strategy)
        
    finally:
        close_db_session(db)


@router.delete(
    "/strategies/{strategy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a trading strategy",
    description="Delete a trading strategy and all associated backtest runs"
)
async def delete_strategy(
    strategy_id: int,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Delete a strategy"""
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Strategy backtesting",
        user_data.get("trial_ends_at")
    )
    
    try:
        strategy = db.query(UserStrategy).filter(
            and_(
                UserStrategy.id == strategy_id,
                UserStrategy.user_id == user_data["user_id"]
            )
        ).first()
        
        if not strategy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Strategy {strategy_id} not found"
            )
        
        db.delete(strategy)
        db.commit()
        
        logger.info(f"Deleted strategy {strategy_id}")
        
    finally:
        close_db_session(db)


# Backtest Execution Endpoints

@router.post(
    "/run",
    response_model=BacktestRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Run a backtest",
    description="""
    Execute a backtest for a trading strategy over a specified date range.
    
    The backtest will:
    1. Query all events in the date range matching strategy filters
    2. Simulate entries based on entry_conditions
    3. Simulate exits based on exit_conditions or fixed horizon
    4. Calculate P&L using actual price_history data
    5. Generate summary metrics (win rate, returns, Sharpe ratio, drawdown)
    
    Returns immediately with status="running". Poll the GET endpoint to check completion.
    """
)
async def run_backtest_endpoint(
    request: RunBacktestRequest,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Run a backtest for a strategy"""
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Strategy backtesting",
        user_data.get("trial_ends_at")
    )
    
    # Validate strategy exists and belongs to user
    strategy = db.query(UserStrategy).filter(
        and_(
            UserStrategy.id == request.strategy_id,
            UserStrategy.user_id == user_data["user_id"]
        )
    ).first()
    
    if not strategy:
        close_db_session(db)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Strategy {request.strategy_id} not found"
        )
    
    # Validate date range
    if request.end_date <= request.start_date:
        close_db_session(db)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="end_date must be after start_date"
        )
    
    try:
        # Run backtest (synchronous for now, could be made async with background tasks)
        backtest_run = run_backtest(
            strategy_id=request.strategy_id,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            db=db
        )
        
        logger.info(f"Completed backtest run {backtest_run.id} for strategy {request.strategy_id}")
        
        return BacktestRunResponse.from_orm(backtest_run)
        
    except Exception as e:
        logger.error(f"Backtest failed: {str(e)}", exc_info=True)
        close_db_session(db)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Backtest failed: {str(e)}"
        )
    finally:
        close_db_session(db)


@router.get(
    "/runs/{run_id}",
    response_model=BacktestRunResponse,
    summary="Get backtest run details",
    description="Get summary results and metrics for a completed backtest run"
)
async def get_backtest_run(
    run_id: int,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Get backtest run details"""
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Strategy backtesting",
        user_data.get("trial_ends_at")
    )
    
    try:
        run = db.query(BacktestRun).filter(
            and_(
                BacktestRun.id == run_id,
                BacktestRun.user_id == user_data["user_id"]
            )
        ).first()
        
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest run {run_id} not found"
            )
        
        return BacktestRunResponse.from_orm(run)
        
    finally:
        close_db_session(db)


@router.get(
    "/runs/{run_id}/trades",
    response_model=List[BacktestResultResponse],
    summary="Get individual trade details",
    description="Get all individual trades from a backtest run with entry/exit prices and P&L"
)
async def get_backtest_trades(
    run_id: int,
    limit: int = 100,
    offset: int = 0,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Get individual trades from a backtest run"""
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Strategy backtesting",
        user_data.get("trial_ends_at")
    )
    
    try:
        # Verify run belongs to user
        run = db.query(BacktestRun).filter(
            and_(
                BacktestRun.id == run_id,
                BacktestRun.user_id == user_data["user_id"]
            )
        ).first()
        
        if not run:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Backtest run {run_id} not found"
            )
        
        # Get trades
        trades = db.query(BacktestResult).filter(
            BacktestResult.run_id == run_id
        ).order_by(BacktestResult.entry_date).limit(limit).offset(offset).all()
        
        return [BacktestResultResponse.from_orm(t) for t in trades]
        
    finally:
        close_db_session(db)


@router.get(
    "/runs",
    response_model=List[BacktestRunResponse],
    summary="List backtest runs",
    description="Get all backtest runs for the authenticated user"
)
async def list_backtest_runs(
    strategy_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """List all backtest runs for the current user"""
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Strategy backtesting",
        user_data.get("trial_ends_at")
    )
    
    try:
        query = db.query(BacktestRun).filter(
            BacktestRun.user_id == user_data["user_id"]
        )
        
        if strategy_id:
            query = query.filter(BacktestRun.strategy_id == strategy_id)
        
        if status_filter:
            query = query.filter(BacktestRun.status == status_filter)
        
        runs = query.order_by(desc(BacktestRun.started_at)).limit(limit).offset(offset).all()
        
        return [BacktestRunResponse.from_orm(r) for r in runs]
        
    finally:
        close_db_session(db)


# Backtesting Summary Response Model
class BacktestingSummaryResponse(BaseModel):
    """Summary of all backtesting runs"""
    total_runs: int
    completed_runs: int
    total_strategies: int
    overall: Dict[str, Any]  # Overall performance metrics
    best_strategy: Optional[Dict[str, Any]] = None
    recent_runs: List[Dict[str, Any]] = []


@router.get(
    "/summary",
    response_model=BacktestingSummaryResponse,
    summary="Get backtesting summary",
    description="Returns overall summary of backtesting runs and strategies"
)
async def get_backtesting_summary(
    mode: Optional[str] = Query(None, description="Dashboard mode: watchlist or portfolio"),
    user_data: dict = Depends(get_current_user_with_plan),
    dm = Depends(get_data_manager),
    db: Session = Depends(get_db)
):
    """
    Get overall backtesting summary including total runs, strategies, and performance.
    
    Returns aggregated statistics for all backtesting activity.
    Supports filtering by dashboard mode (watchlist/portfolio).
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Strategy backtesting",
        user_data.get("trial_ends_at")
    )
    
    try:
        user_id = user_data["user_id"]
        
        # Get active tickers if mode is specified
        tickers_filter = None
        if mode and mode in ['watchlist', 'portfolio']:
            tickers_filter = dm.get_user_active_tickers(user_id, mode)
            
            # If empty watchlist/portfolio, return empty summary
            if tickers_filter is not None and len(tickers_filter) == 0:
                return BacktestingSummaryResponse(
                    total_runs=0,
                    completed_runs=0,
                    total_strategies=0,
                    overall={
                        "total_trades": 0,
                        "avg_win_rate": 0.0,
                        "avg_return": 0.0,
                        "avg_sharpe": 0.0,
                        "avg_max_drawdown": 0.0,
                    },
                    best_strategy=None,
                    recent_runs=[],
                )
        
        # Build base query for runs
        runs_query = db.query(BacktestRun).filter(BacktestRun.user_id == user_id)
        
        # Apply ticker filter if mode is active
        if tickers_filter is not None:
            # Filter strategies by tickers
            strategy_ids = db.query(UserStrategy.id).filter(
                and_(
                    UserStrategy.user_id == user_id,
                    UserStrategy.tickers.overlap(tickers_filter)
                )
            ).subquery()
            runs_query = runs_query.filter(BacktestRun.strategy_id.in_(strategy_ids))
        
        # Get total runs
        total_runs_count = runs_query.count()
        
        # Get completed runs count
        completed_runs_count = runs_query.filter(BacktestRun.status == "completed").count()
        
        # Get total strategies (with mode filter)
        strategies_query = db.query(UserStrategy).filter(UserStrategy.user_id == user_id)
        if tickers_filter is not None:
            strategies_query = strategies_query.filter(UserStrategy.tickers.overlap(tickers_filter))
        total_strategies_count = strategies_query.count()
        
        # Get completed runs for statistics
        completed_runs = runs_query.filter(
            and_(
                BacktestRun.status == "completed",
                BacktestRun.total_return_pct.isnot(None)
            )
        ).order_by(desc(BacktestRun.completed_at)).limit(50).all()
        
        # Calculate overall metrics (with proper rounding)
        overall_metrics = {
            "total_trades": 0,
            "avg_win_rate": 0.0,
            "avg_return": 0.0,
            "avg_sharpe": 0.0,
            "avg_max_drawdown": 0.0,
        }
        
        if completed_runs:
            overall_metrics["total_trades"] = sum(r.total_trades or 0 for r in completed_runs)
            # Note: win_rate from DB is already a percentage (0-100), no need to multiply by 100
            overall_metrics["avg_win_rate"] = round(
                sum(r.win_rate or 0.0 for r in completed_runs) / len(completed_runs), 
                2
            )
            overall_metrics["avg_return"] = round(
                sum(r.total_return_pct or 0.0 for r in completed_runs) / len(completed_runs), 
                2
            )
            sharpe_values = [r.sharpe_ratio for r in completed_runs if r.sharpe_ratio is not None]
            overall_metrics["avg_sharpe"] = round(
                sum(sharpe_values) / len(sharpe_values) if sharpe_values else 0.0, 
                2
            )
            overall_metrics["avg_max_drawdown"] = round(
                sum(r.max_drawdown_pct or 0.0 for r in completed_runs) / len(completed_runs), 
                2
            )
        
        # Find best strategy (highest Sharpe ratio)
        best_strategy = None
        if completed_runs:
            best_run = max(
                (r for r in completed_runs if r.sharpe_ratio is not None),
                key=lambda r: r.sharpe_ratio,
                default=None
            )
            
            if best_run:
                strategy = db.query(UserStrategy).filter(UserStrategy.id == best_run.strategy_id).first()
                best_strategy = {
                    "run_id": best_run.id,
                    "strategy_id": best_run.strategy_id,
                    "strategy_name": strategy.name if strategy else "Unknown",
                    "sharpe_ratio": round(best_run.sharpe_ratio, 2) if best_run.sharpe_ratio else None,
                    "total_return_pct": round(best_run.total_return_pct, 2) if best_run.total_return_pct else None,
                    "win_rate": round(best_run.win_rate, 2) if best_run.win_rate else None,
                }
        
        # Get recent runs with all required fields
        recent_runs_list = []
        for run in completed_runs[:5]:
            strategy = db.query(UserStrategy).filter(UserStrategy.id == run.strategy_id).first()
            recent_runs_list.append({
                "id": run.id,
                "strategy_id": run.strategy_id,
                "strategy_name": strategy.name if strategy else "Unknown",
                "status": run.status,
                "started_at": run.started_at.isoformat() if run.started_at else None,
                "completed_at": run.completed_at.isoformat() if run.completed_at else None,
                "total_return_pct": round(run.total_return_pct, 2) if run.total_return_pct else None,
                "sharpe_ratio": round(run.sharpe_ratio, 2) if run.sharpe_ratio else None,
                "win_rate": round(run.win_rate, 2) if run.win_rate else None,
                "max_drawdown_pct": round(run.max_drawdown_pct, 2) if run.max_drawdown_pct else None,
                "total_trades": run.total_trades,
            })
        
        return BacktestingSummaryResponse(
            total_runs=total_runs_count,
            completed_runs=completed_runs_count,
            total_strategies=total_strategies_count,
            overall=overall_metrics,
            best_strategy=best_strategy,
            recent_runs=recent_runs_list,
        )
    
    finally:
        close_db_session(db)


# Family Coverage Response Model
class FamilyCoverageResponse(BaseModel):
    """Model coverage by event family"""
    family: str
    family_display_name: str
    total_events: int
    labeled_count_1d: int
    labeled_count_5d: int
    labeled_count_20d: int
    model_status_1d: str
    model_status_5d: str
    model_status_20d: str
    model_source_1d: str
    model_source_5d: str
    model_source_20d: str
    model_version_1d: Optional[str]
    model_version_5d: Optional[str]
    model_version_20d: Optional[str]
    model_trained_at_1d: Optional[str]
    model_trained_at_5d: Optional[str]
    model_trained_at_20d: Optional[str]
    mae_1d: Optional[float]
    mae_5d: Optional[float]
    mae_20d: Optional[float]
    directional_accuracy_1d: Optional[float]
    directional_accuracy_5d: Optional[float]
    directional_accuracy_20d: Optional[float]


@router.get(
    "/coverage",
    response_model=List[FamilyCoverageResponse],
    summary="Get ML model coverage by event family",
    description="Returns labeled data coverage and model status for each event type family"
)
async def get_family_coverage(
    mode: Optional[str] = Query(None, description="Dashboard mode: watchlist or portfolio"),
    user_data: dict = Depends(get_current_user_with_plan),
    dm = Depends(get_data_manager),
    db: Session = Depends(get_db)
):
    """
    Get ML model coverage data by event family using efficient SQL aggregations.
    
    Returns information about:
    - Labeled training data counts by horizon
    - Model status (active/inactive) and source (family-specific/global/deterministic)
    - Model performance metrics (MAE, directional accuracy)
    
    Supports filtering by dashboard mode (watchlist/portfolio).
    """
    try:
        from sqlalchemy import func, case
        
        # Get active tickers if mode is specified
        tickers_filter = None
        if mode and mode in ['watchlist', 'portfolio']:
            tickers_filter = dm.get_user_active_tickers(user_data["user_id"], mode)
            
            # If empty watchlist/portfolio, return empty list
            if tickers_filter is not None and len(tickers_filter) == 0:
                return []
        
        # Use SQL aggregation instead of loading all rows into memory
        # Build aggregation query: COUNT(*) grouped by event_type and horizon
        agg_query = select(
            Event.event_type,
            EventOutcome.horizon,
            func.count().label('count')
        ).join(EventOutcome, Event.id == EventOutcome.event_id)
        
        # Filter by tickers if provided
        if tickers_filter is not None:
            agg_query = agg_query.where(Event.ticker.in_(tickers_filter))
        
        agg_query = agg_query.group_by(Event.event_type, EventOutcome.horizon)
        
        # Execute aggregation query
        agg_results = db.execute(agg_query).all()
        
        # Build family data from aggregated results
        family_data = defaultdict(lambda: {
            'total_events': 0,
            '1d': 0, '5d': 0, '20d': 0
        })
        
        for event_type, horizon, count in agg_results:
            family = get_event_family(event_type)
            family_data[family]['total_events'] += count
            family_data[family][horizon] += count
        
        # Pre-fetch ALL active models in a single query to avoid N+1
        all_models = db.execute(
            select(ModelRegistry)
            .where(ModelRegistry.status == "active")
            .order_by(ModelRegistry.promoted_at.desc())
        ).scalars().all()
        
        # Index models by (family, horizon) for O(1) lookup
        models_by_family_horizon = {}
        for model in all_models:
            key = (model.event_type_family, model.horizon)
            # Keep only the most recently promoted model per (family, horizon)
            if key not in models_by_family_horizon:
                models_by_family_horizon[key] = model
        
        # Build response for each family
        results = []
        
        for family, event_types in EVENT_TYPE_FAMILIES.items():
            data = family_data.get(family, {
                'total_events': 0,
                '1d': 0, '5d': 0, '20d': 0
            })
            
            # Get model info for each horizon using pre-fetched models
            model_info = {}
            for horizon in ["1d", "5d", "20d"]:
                # Check for family-specific model
                family_model = models_by_family_horizon.get((family, horizon))
                
                if family_model:
                    model_info[horizon] = {
                        'status': 'active',
                        'source': 'family-specific',
                        'version': family_model.version,
                        'trained_at': family_model.trained_at.isoformat() if family_model.trained_at else None,
                        'mae': family_model.metrics.get('mae'),
                        'directional_accuracy': family_model.metrics.get('directional_accuracy')
                    }
                else:
                    # Check for global model
                    global_model = models_by_family_horizon.get(("all", horizon))
                    
                    if global_model:
                        model_info[horizon] = {
                            'status': 'active',
                            'source': 'global',
                            'version': global_model.version,
                            'trained_at': global_model.trained_at.isoformat() if global_model.trained_at else None,
                            'mae': global_model.metrics.get('mae'),
                            'directional_accuracy': global_model.metrics.get('directional_accuracy')
                        }
                    else:
                        model_info[horizon] = {
                            'status': 'none',
                            'source': 'deterministic',
                            'version': None,
                            'trained_at': None,
                            'mae': None,
                            'directional_accuracy': None
                        }
            
            results.append(FamilyCoverageResponse(
                family=family,
                family_display_name=get_family_display_name(family),
                total_events=data['total_events'],
                labeled_count_1d=data.get('1d', 0),
                labeled_count_5d=data.get('5d', 0),
                labeled_count_20d=data.get('20d', 0),
                model_status_1d=model_info['1d']['status'],
                model_status_5d=model_info['5d']['status'],
                model_status_20d=model_info['20d']['status'],
                model_source_1d=model_info['1d']['source'],
                model_source_5d=model_info['5d']['source'],
                model_source_20d=model_info['20d']['source'],
                model_version_1d=model_info['1d']['version'],
                model_version_5d=model_info['5d']['version'],
                model_version_20d=model_info['20d']['version'],
                model_trained_at_1d=model_info['1d']['trained_at'],
                model_trained_at_5d=model_info['5d']['trained_at'],
                model_trained_at_20d=model_info['20d']['trained_at'],
                mae_1d=model_info['1d']['mae'],
                mae_5d=model_info['5d']['mae'],
                mae_20d=model_info['20d']['mae'],
                directional_accuracy_1d=model_info['1d']['directional_accuracy'],
                directional_accuracy_5d=model_info['5d']['directional_accuracy'],
                directional_accuracy_20d=model_info['20d']['directional_accuracy'],
            ))
        
        # Sort by total events (descending)
        results.sort(key=lambda x: x.total_events, reverse=True)
        
        return results
        
    except Exception as e:
        logger.error(f"Error getting family coverage: {e}", exc_info=True)
        # Return empty list instead of raising error (defensive)
        return []
    
    finally:
        close_db_session(db)
