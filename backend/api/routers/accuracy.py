"""
Accuracy Dashboard API Router

Endpoints for retrieving prediction accuracy metrics and performance trends.
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, date, timedelta
from pydantic import BaseModel, Field, field_serializer
from sqlalchemy import and_, desc, func, case, asc
from sqlalchemy.orm import Session

from database import get_db, close_db_session
from releaseradar.db.models import PredictionMetrics, PredictionSnapshot, Event, EventOutcome
from api.utils.auth import get_current_user_with_plan

router = APIRouter(prefix="/accuracy", tags=["accuracy"])


# Response Models
class MetricsResponse(BaseModel):
    """Response model for prediction accuracy metrics"""
    model_version: str
    event_type: str
    horizon: str
    date: str = Field(description="Date of the metric snapshot (ISO format)")
    total_predictions: int
    correct_direction: int
    win_rate: Optional[float] = Field(description="Percentage of correct direction predictions")
    mae: Optional[float] = Field(description="Mean absolute error")
    rmse: Optional[float] = Field(description="Root mean squared error")
    sharpe_ratio: Optional[float] = Field(description="Risk-adjusted returns")
    avg_confidence: Optional[float]
    high_conf_win_rate: Optional[float] = Field(description="Win rate for confidence > 0.7")
    med_conf_win_rate: Optional[float] = Field(description="Win rate for 0.4 < confidence <= 0.7")
    low_conf_win_rate: Optional[float] = Field(description="Win rate for confidence <= 0.4")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SnapshotResponse(BaseModel):
    """Response model for prediction snapshots"""
    snapshot_date: str = Field(description="ISO format date of the snapshot")
    overall_win_rate: float
    mae: float
    rmse: float
    total_predictions: int


class ModelVersionPerformance(BaseModel):
    """Performance metrics for a specific model version"""
    model_version: str
    win_rate: float
    total_predictions: int


class SummaryResponse(BaseModel):
    """Response model for overall performance summary"""
    overall_win_rate: float
    total_events_scored: int
    avg_mae: float
    avg_rmse: float
    model_versions: List[ModelVersionPerformance] = Field(description="Performance by model version")
    trend_direction: str = Field(description="Trend direction: 'up', 'down', or 'stable'")
    trend_percentage: float = Field(description="Percentage change in win rate")


class ConfidenceBreakdownResponse(BaseModel):
    """Response model for win rates by confidence level"""
    confidence_level: str = Field(description="Confidence level: High, Medium, or Low")
    win_rate: float = Field(description="Win rate percentage for this confidence level")
    count: int = Field(description="Number of predictions at this confidence level")


@router.get(
    "/metrics",
    response_model=List[MetricsResponse],
    summary="Get prediction accuracy metrics",
    description="""
    Retrieve prediction accuracy metrics with optional filters.
    
    Metrics include win rates, MAE, RMSE, Sharpe ratio, and confidence-based breakdowns.
    Results can be filtered by model version, event type, horizon, and date range.
    """,
)
async def get_accuracy_metrics(
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    event_type: Optional[str] = Query(None, description="Filter by event type (e.g., 'earnings', 'fda_approval')"),
    horizon: Optional[str] = Query(None, description="Filter by time horizon (e.g., '1d', '5d', '30d')"),
    from_date: Optional[date] = Query(None, description="Start date for filtering (ISO format)"),
    to_date: Optional[date] = Query(None, description="End date for filtering (ISO format)"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """
    Get prediction accuracy metrics with filters.
    
    Returns the most recent accuracy snapshot for each model/event type/horizon combination.
    """
    try:
        # Subquery to get the latest date for each model_version/event_type/horizon group
        subq = (
            db.query(
                PredictionMetrics.model_version,
                PredictionMetrics.event_type,
                PredictionMetrics.horizon,
                func.max(PredictionMetrics.date).label('max_date')
            )
            .group_by(
                PredictionMetrics.model_version,
                PredictionMetrics.event_type,
                PredictionMetrics.horizon
            )
        )
        
        # Apply user filters to the subquery
        if model_version:
            subq = subq.filter(PredictionMetrics.model_version == model_version)
        if event_type:
            subq = subq.filter(PredictionMetrics.event_type == event_type)
        if horizon:
            subq = subq.filter(PredictionMetrics.horizon == horizon)
        if from_date:
            subq = subq.filter(PredictionMetrics.date >= from_date)
        if to_date:
            subq = subq.filter(PredictionMetrics.date <= to_date)
        
        subq = subq.subquery()
        
        # Main query: join with subquery to get only the latest snapshot for each group
        query = db.query(PredictionMetrics).join(
            subq,
            and_(
                PredictionMetrics.model_version == subq.c.model_version,
                PredictionMetrics.event_type == subq.c.event_type,
                PredictionMetrics.horizon == subq.c.horizon,
                PredictionMetrics.date == subq.c.max_date
            )
        )
        
        # Order by model version, event type, horizon for consistent display
        query = query.order_by(
            PredictionMetrics.model_version,
            PredictionMetrics.event_type,
            PredictionMetrics.horizon
        )
        
        # Limit results
        query = query.limit(limit)
        
        # Execute query
        metrics = query.all()
        if not metrics:
            return []
        
        # Convert ORM objects to Pydantic models, converting date objects to ISO strings
        result = []
        for m in metrics:
            # Convert the date field to ISO string if it's a date object
            metric_dict = {
                "model_version": m.model_version,
                "event_type": m.event_type,
                "horizon": m.horizon,
                "date": m.date.isoformat() if m.date else "",
                "total_predictions": m.total_predictions,
                "correct_direction": m.correct_direction,
                "win_rate": m.win_rate,
                "mae": m.mae,
                "rmse": m.rmse,
                "sharpe_ratio": m.sharpe_ratio,
                "avg_confidence": m.avg_confidence,
                "high_conf_win_rate": m.high_conf_win_rate,
                "med_conf_win_rate": m.med_conf_win_rate,
                "low_conf_win_rate": m.low_conf_win_rate,
                "created_at": m.created_at,
                "updated_at": m.updated_at,
            }
            result.append(MetricsResponse(**metric_dict))
        
        return result
    
    except Exception as e:
        # Log the error and re-raise to surface issues
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error fetching accuracy metrics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")


@router.get(
    "/snapshots",
    response_model=List[SnapshotResponse],
    summary="Get historical prediction snapshots",
    description="""
    Retrieve point-in-time snapshots of prediction accuracy for trend charting.
    
    Snapshots capture overall model performance at specific timestamps,
    useful for visualizing performance trends over time.
    """,
)
async def get_accuracy_snapshots(
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    days: Optional[int] = Query(None, description="Number of days of history to retrieve"),
    from_time: Optional[datetime] = Query(None, description="Start timestamp for filtering"),
    to_time: Optional[datetime] = Query(None, description="End timestamp for filtering"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of snapshots"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """
    Get historical snapshots for trend charts.
    
    Returns time-series data showing how model accuracy has evolved over time.
    """
    # Build query
    query = db.query(PredictionSnapshot)
    
    # Apply filters
    if model_version:
        query = query.filter(PredictionSnapshot.model_version == model_version)
    
    # Use days parameter to filter by recent history
    if days:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = query.filter(PredictionSnapshot.timestamp >= cutoff_date)
    elif from_time:
        query = query.filter(PredictionSnapshot.timestamp >= from_time)
    
    if to_time:
        query = query.filter(PredictionSnapshot.timestamp <= to_time)
    
    # Order by timestamp ascending (oldest first for charts)
    query = query.order_by(PredictionSnapshot.timestamp)
    
    # Limit results
    query = query.limit(limit)
    
    # Execute query
    snapshots = query.all()
    
    # Transform to match frontend expectations
    result = []
    for snapshot in snapshots:
        # Get MAE from snapshot and average RMSE from metrics for this model version and date
        snapshot_date = snapshot.timestamp.date()
        
        # Use overall_mae from snapshot
        mae = float(snapshot.overall_mae) if snapshot.overall_mae is not None else 0.0
        
        # Get average RMSE from metrics for this model version and date
        avg_rmse_result = db.query(func.avg(PredictionMetrics.rmse)).filter(
            and_(
                PredictionMetrics.model_version == snapshot.model_version,
                PredictionMetrics.date == snapshot_date
            )
        ).scalar()
        
        rmse = float(avg_rmse_result) if avg_rmse_result is not None else mae * 1.2  # Estimate RMSE if not available
        
        result.append(SnapshotResponse(
            snapshot_date=snapshot.timestamp.isoformat(),
            overall_win_rate=snapshot.overall_win_rate or 0.0,
            mae=mae,
            rmse=rmse,
            total_predictions=snapshot.total_events_scored or 0,
        ))
    
    return result


@router.get(
    "/summary",
    response_model=SummaryResponse,
    summary="Get overall performance summary",
    description="""
    Get current overall prediction accuracy summary across all model versions.
    
    Returns aggregated metrics including win rate, total events scored, MAE, RMSE,
    performance by model version, and trend analysis.
    """,
)
async def get_accuracy_summary(
    model_version: Optional[str] = Query(None, description="Model version to summarize (defaults to all versions)"),
    days: Optional[int] = Query(30, description="Days of history to include for trend analysis"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """
    Get overall performance summary with trend analysis.
    
    Provides a high-level view of current model accuracy across all versions.
    """
    # Get all unique model versions from recent snapshots
    model_versions_query = db.query(PredictionSnapshot.model_version).distinct()
    all_model_versions = [row[0] for row in model_versions_query.all()]
    
    if not all_model_versions:
        # Return empty summary if no data exists at all
        return SummaryResponse(
            overall_win_rate=0.0,
            total_events_scored=0,
            avg_mae=0.0,
            avg_rmse=0.0,
            model_versions=[],
            trend_direction="stable",
            trend_percentage=0.0,
        )
    
    # Get performance for each model version
    model_version_performance = []
    total_win_rate_sum = 0.0
    total_mae_sum = 0.0
    total_rmse_sum = 0.0
    total_events_all_versions = 0
    rmse_count = 0
    
    for mv in all_model_versions:
        # Get latest snapshot for this version
        snapshot = db.query(PredictionSnapshot).filter(
            PredictionSnapshot.model_version == mv
        ).order_by(desc(PredictionSnapshot.timestamp)).first()
        
        if snapshot:
            model_version_performance.append(
                ModelVersionPerformance(
                    model_version=mv,
                    win_rate=snapshot.overall_win_rate or 0.0,
                    total_predictions=snapshot.total_events_scored or 0,
                )
            )
            total_win_rate_sum += (snapshot.overall_win_rate or 0.0)
            total_events_all_versions += (snapshot.total_events_scored or 0)
            
            # Use overall_mae from snapshot if available
            if snapshot.overall_mae is not None:
                total_mae_sum += float(snapshot.overall_mae)
            
            # Get average RMSE from all metrics for this version
            avg_rmse_result = db.query(func.avg(PredictionMetrics.rmse)).filter(
                PredictionMetrics.model_version == mv
            ).scalar()
            
            if avg_rmse_result is not None:
                total_rmse_sum += float(avg_rmse_result)
                rmse_count += 1
    
    # Calculate averages
    num_versions = len(model_version_performance)
    overall_win_rate = total_win_rate_sum / num_versions if num_versions > 0 else 0.0
    avg_mae = total_mae_sum / num_versions if num_versions > 0 else 0.0
    avg_rmse = total_rmse_sum / rmse_count if rmse_count > 0 else 0.0
    
    # Calculate trend (compare to previous period)
    trend_direction = "stable"
    trend_percentage = 0.0
    
    if days:
        # Get snapshots from the previous period
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        previous_cutoff = cutoff_date - timedelta(days=days)
        
        # Current period
        current_snapshots = db.query(PredictionSnapshot).filter(
            PredictionSnapshot.timestamp >= cutoff_date
        ).all()
        
        # Previous period
        previous_snapshots = db.query(PredictionSnapshot).filter(
            and_(
                PredictionSnapshot.timestamp >= previous_cutoff,
                PredictionSnapshot.timestamp < cutoff_date
            )
        ).all()
        
        if current_snapshots and previous_snapshots:
            current_avg = sum(s.overall_win_rate or 0.0 for s in current_snapshots) / len(current_snapshots)
            previous_avg = sum(s.overall_win_rate or 0.0 for s in previous_snapshots) / len(previous_snapshots)
            
            if previous_avg > 0:
                trend_percentage = ((current_avg - previous_avg) / previous_avg) * 100
                
                if trend_percentage > 2.0:
                    trend_direction = "up"
                elif trend_percentage < -2.0:
                    trend_direction = "down"
                else:
                    trend_direction = "stable"
    
    return SummaryResponse(
        overall_win_rate=overall_win_rate,
        total_events_scored=total_events_all_versions,
        avg_mae=avg_mae,
        avg_rmse=avg_rmse,
        model_versions=model_version_performance,
        trend_direction=trend_direction,
        trend_percentage=trend_percentage,
    )


@router.get(
    "/by-confidence",
    response_model=List[ConfidenceBreakdownResponse],
    summary="Get win rates by confidence level",
    description="""
    Get win rates broken down by model confidence levels.
    
    Shows how prediction accuracy varies with model confidence:
    - High (> 0.7)
    - Medium (0.4 - 0.7)
    - Low (< 0.4)
    
    Helps assess whether the model's confidence scores are well-calibrated.
    """,
)
async def get_accuracy_by_confidence(
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    horizon: Optional[str] = Query("7d", description="Time horizon"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """
    Get win rates broken down by confidence level.
    
    Shows whether high-confidence predictions are actually more accurate.
    Returns aggregated data across all matching metrics.
    """
    # Build query to get latest metrics
    query = db.query(PredictionMetrics)
    
    # Apply filters
    if model_version:
        query = query.filter(PredictionMetrics.model_version == model_version)
    if event_type:
        query = query.filter(PredictionMetrics.event_type == event_type)
    if horizon:
        query = query.filter(PredictionMetrics.horizon == horizon)
    
    # Order by date descending and get latest
    query = query.order_by(desc(PredictionMetrics.date))
    
    # Execute query - get recent metrics to aggregate
    metrics = query.limit(10).all()
    
    if not metrics:
        return []
    
    # Aggregate confidence level data
    high_conf_total = 0.0
    high_conf_count = 0
    med_conf_total = 0.0
    med_conf_count = 0
    low_conf_total = 0.0
    low_conf_count = 0
    
    for metric in metrics:
        if metric.high_conf_win_rate is not None:
            high_conf_total += metric.high_conf_win_rate
            high_conf_count += 1
        
        if metric.med_conf_win_rate is not None:
            med_conf_total += metric.med_conf_win_rate
            med_conf_count += 1
        
        if metric.low_conf_win_rate is not None:
            low_conf_total += metric.low_conf_win_rate
            low_conf_count += 1
    
    # Build response with aggregated data
    results = []
    
    if high_conf_count > 0:
        results.append(ConfidenceBreakdownResponse(
            confidence_level="High (> 0.7)",
            win_rate=high_conf_total / high_conf_count,
            count=high_conf_count,
        ))
    
    if med_conf_count > 0:
        results.append(ConfidenceBreakdownResponse(
            confidence_level="Medium (0.4 - 0.7)",
            win_rate=med_conf_total / med_conf_count,
            count=med_conf_count,
        ))
    
    if low_conf_count > 0:
        results.append(ConfidenceBreakdownResponse(
            confidence_level="Low (< 0.4)",
            win_rate=low_conf_total / low_conf_count,
            count=low_conf_count,
        ))
    
    return results


# ============================================================================
# NEW ENDPOINTS: 6 Enhanced Dashboard Features
# ============================================================================

# Response Models for New Features
class TrendDataPoint(BaseModel):
    """Single data point for accuracy trend charts"""
    date: str
    win_rate: float
    mae: float
    total_predictions: int
    period_label: str = Field(description="Friendly label for the period (e.g., 'Nov 25')")


class TrendResponse(BaseModel):
    """Response for accuracy trends over time"""
    granularity: str = Field(description="'daily' or 'weekly'")
    data_points: List[TrendDataPoint]
    trend_direction: str = Field(description="'up', 'down', or 'stable'")
    trend_percentage: float


class EventTypePerformanceItem(BaseModel):
    """Performance metrics for a single event type"""
    event_type: str
    display_name: str = Field(description="Human-readable event type name")
    win_rate: float
    mae: float
    total_predictions: int
    trend_vs_previous: float = Field(description="Win rate change vs previous period")
    horizons: Dict[str, float] = Field(description="Win rate by horizon")


class EventTypePerformanceResponse(BaseModel):
    """Response for event type performance breakdown"""
    event_types: List[EventTypePerformanceItem]
    best_performing: str
    worst_performing: str


class RecentPrediction(BaseModel):
    """A single prediction with its outcome"""
    event_id: int
    ticker: str
    event_type: str
    title: str
    event_date: str
    predicted_direction: str
    predicted_impact: int
    confidence: float
    actual_return: Optional[float]
    direction_correct: Optional[bool]
    horizon: str
    outcome_status: str = Field(description="'pending', 'correct', or 'incorrect'")


class ScorecardResponse(BaseModel):
    """Response for prediction scorecard"""
    predictions: List[RecentPrediction]
    total_shown: int
    wins: int
    losses: int
    pending: int
    streak: int = Field(description="Current win/loss streak, positive for wins")


class AccuracyAlert(BaseModel):
    """Alert for accuracy changes"""
    alert_id: str
    alert_type: str = Field(description="'accuracy_drop', 'accuracy_improvement', 'mae_spike'")
    severity: str = Field(description="'warning', 'critical', 'info'")
    message: str
    metric_name: str
    current_value: float
    previous_value: float
    change_percentage: float
    detected_at: str
    dismissed: bool = False


class AlertsResponse(BaseModel):
    """Response for performance alerts"""
    alerts: List[AccuracyAlert]
    has_critical: bool
    total_alerts: int


class HorizonComparisonItem(BaseModel):
    """Comparison data for a single horizon"""
    horizon: str
    display_name: str = Field(description="Friendly name like '1 Day', '7 Days'")
    win_rate: float
    mae: float
    total_predictions: int
    confidence_avg: float


class HorizonComparisonResponse(BaseModel):
    """Response for time horizon comparison"""
    horizons: List[HorizonComparisonItem]
    best_horizon: str
    recommendation: str = Field(description="Actionable insight about horizon performance")


# Helper function to get display name for event types
def get_event_type_display_name(event_type: str) -> str:
    """Convert event type code to human-readable name"""
    display_names = {
        "earnings": "Earnings",
        "sec_8k": "SEC 8-K Filings",
        "sec_def14a": "Proxy Statements",
        "fda_approval": "FDA Approvals",
        "fda_rejection": "FDA Rejections",
        "insider_buy": "Insider Buying",
        "insider_sell": "Insider Selling",
        "ma": "M&A Activity",
        "ipo": "IPO",
        "dividend": "Dividend",
        "guidance": "Guidance",
        "analyst": "Analyst Rating",
    }
    return display_names.get(event_type, event_type.replace("_", " ").title())


def get_horizon_display_name(horizon: str) -> str:
    """Convert horizon code to human-readable name"""
    display_names = {
        "1d": "1 Day",
        "5d": "5 Days",
        "7d": "7 Days",
        "20d": "20 Days",
        "30d": "30 Days",
    }
    return display_names.get(horizon, horizon)


@router.get(
    "/trends",
    response_model=TrendResponse,
    summary="Get accuracy trends over time",
    description="Get daily or weekly accuracy trends for charting historical performance.",
)
async def get_accuracy_trends(
    granularity: str = Query("daily", description="'daily' or 'weekly'"),
    days: int = Query(30, ge=7, le=365, description="Number of days of history"),
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Get accuracy trends with daily or weekly aggregation for trend charts."""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        # Query snapshots for the time period
        query = db.query(PredictionSnapshot).filter(
            PredictionSnapshot.timestamp >= cutoff_date
        )
        
        if model_version:
            query = query.filter(PredictionSnapshot.model_version == model_version)
        
        query = query.order_by(asc(PredictionSnapshot.timestamp))
        snapshots = query.all()
        
        if not snapshots:
            return TrendResponse(
                granularity=granularity,
                data_points=[],
                trend_direction="stable",
                trend_percentage=0.0,
            )
        
        # Aggregate by granularity
        data_points = []
        
        if granularity == "weekly":
            # Group by week
            weekly_data = {}
            for s in snapshots:
                week_start = s.timestamp - timedelta(days=s.timestamp.weekday())
                week_key = week_start.strftime("%Y-%m-%d")
                if week_key not in weekly_data:
                    weekly_data[week_key] = {"win_rates": [], "maes": [], "totals": []}
                weekly_data[week_key]["win_rates"].append(s.overall_win_rate or 0)
                weekly_data[week_key]["maes"].append(float(s.overall_mae) if s.overall_mae else 0)
                weekly_data[week_key]["totals"].append(s.total_events_scored or 0)
            
            for week_key in sorted(weekly_data.keys()):
                data = weekly_data[week_key]
                avg_win_rate = sum(data["win_rates"]) / len(data["win_rates"]) if data["win_rates"] else 0
                avg_mae = sum(data["maes"]) / len(data["maes"]) if data["maes"] else 0
                total_preds = sum(data["totals"])
                
                week_date = datetime.strptime(week_key, "%Y-%m-%d")
                data_points.append(TrendDataPoint(
                    date=week_key,
                    win_rate=avg_win_rate,
                    mae=avg_mae,
                    total_predictions=total_preds,
                    period_label=week_date.strftime("%b %d"),
                ))
        else:
            # Daily aggregation
            daily_data = {}
            for s in snapshots:
                day_key = s.timestamp.strftime("%Y-%m-%d")
                if day_key not in daily_data:
                    daily_data[day_key] = {"win_rates": [], "maes": [], "totals": []}
                daily_data[day_key]["win_rates"].append(s.overall_win_rate or 0)
                daily_data[day_key]["maes"].append(float(s.overall_mae) if s.overall_mae else 0)
                daily_data[day_key]["totals"].append(s.total_events_scored or 0)
            
            for day_key in sorted(daily_data.keys()):
                data = daily_data[day_key]
                avg_win_rate = sum(data["win_rates"]) / len(data["win_rates"]) if data["win_rates"] else 0
                avg_mae = sum(data["maes"]) / len(data["maes"]) if data["maes"] else 0
                total_preds = sum(data["totals"])
                
                day_date = datetime.strptime(day_key, "%Y-%m-%d")
                data_points.append(TrendDataPoint(
                    date=day_key,
                    win_rate=avg_win_rate,
                    mae=avg_mae,
                    total_predictions=total_preds,
                    period_label=day_date.strftime("%b %d"),
                ))
        
        # Calculate trend
        trend_direction = "stable"
        trend_percentage = 0.0
        if len(data_points) >= 2:
            first_half = data_points[:len(data_points)//2]
            second_half = data_points[len(data_points)//2:]
            
            first_avg = sum(p.win_rate for p in first_half) / len(first_half) if first_half else 0
            second_avg = sum(p.win_rate for p in second_half) / len(second_half) if second_half else 0
            
            if first_avg > 0:
                trend_percentage = ((second_avg - first_avg) / first_avg) * 100
                if trend_percentage > 2:
                    trend_direction = "up"
                elif trend_percentage < -2:
                    trend_direction = "down"
        
        return TrendResponse(
            granularity=granularity,
            data_points=data_points,
            trend_direction=trend_direction,
            trend_percentage=trend_percentage,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch trends: {str(e)}")


@router.get(
    "/by-event-type",
    response_model=EventTypePerformanceResponse,
    summary="Get accuracy breakdown by event type",
    description="Get win rates and error metrics grouped by event type.",
)
async def get_accuracy_by_event_type(
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    horizon: str = Query("1d", description="Time horizon to analyze"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Get accuracy performance breakdown by event type."""
    try:
        # Query latest metrics grouped by event type
        query = db.query(PredictionMetrics)
        
        if model_version:
            query = query.filter(PredictionMetrics.model_version == model_version)
        if horizon:
            query = query.filter(PredictionMetrics.horizon == horizon)
        
        # Get the latest date for each event type
        subq = db.query(
            PredictionMetrics.event_type,
            func.max(PredictionMetrics.date).label('max_date')
        ).group_by(PredictionMetrics.event_type)
        
        if model_version:
            subq = subq.filter(PredictionMetrics.model_version == model_version)
        if horizon:
            subq = subq.filter(PredictionMetrics.horizon == horizon)
        
        subq = subq.subquery()
        
        metrics = db.query(PredictionMetrics).join(
            subq,
            and_(
                PredictionMetrics.event_type == subq.c.event_type,
                PredictionMetrics.date == subq.c.max_date
            )
        ).all()
        
        if not metrics:
            return EventTypePerformanceResponse(
                event_types=[],
                best_performing="N/A",
                worst_performing="N/A",
            )
        
        # Build response
        event_types = []
        best_win_rate = -1
        worst_win_rate = 101
        best_event = "N/A"
        worst_event = "N/A"
        
        for m in metrics:
            win_rate = m.win_rate or 0
            
            # Get horizons data for this event type
            horizons_data = {}
            horizon_metrics = db.query(PredictionMetrics).filter(
                PredictionMetrics.event_type == m.event_type,
                PredictionMetrics.date == m.date
            ).all()
            for hm in horizon_metrics:
                horizons_data[hm.horizon] = hm.win_rate or 0
            
            event_types.append(EventTypePerformanceItem(
                event_type=m.event_type,
                display_name=get_event_type_display_name(m.event_type),
                win_rate=win_rate,
                mae=m.mae or 0,
                total_predictions=m.total_predictions or 0,
                trend_vs_previous=0,  # Would need historical data
                horizons=horizons_data,
            ))
            
            if win_rate > best_win_rate and m.total_predictions >= 10:
                best_win_rate = win_rate
                best_event = m.event_type
            
            if win_rate < worst_win_rate and m.total_predictions >= 10:
                worst_win_rate = win_rate
                worst_event = m.event_type
        
        # Sort by win rate descending
        event_types.sort(key=lambda x: x.win_rate, reverse=True)
        
        return EventTypePerformanceResponse(
            event_types=event_types,
            best_performing=get_event_type_display_name(best_event),
            worst_performing=get_event_type_display_name(worst_event),
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch event type breakdown: {str(e)}")


@router.get(
    "/recent-predictions",
    response_model=ScorecardResponse,
    summary="Get recent predictions with outcomes",
    description="Get a scorecard of recent predictions showing their outcomes.",
)
async def get_recent_predictions(
    limit: int = Query(50, ge=10, le=200, description="Number of predictions to return"),
    horizon: str = Query("1d", description="Filter by time horizon"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Get recent predictions with their actual outcomes for a scorecard view."""
    try:
        # Query events with their outcomes
        query = db.query(Event, EventOutcome).outerjoin(
            EventOutcome,
            and_(
                Event.id == EventOutcome.event_id,
                EventOutcome.horizon == horizon
            )
        ).order_by(desc(Event.date))
        
        if event_type:
            query = query.filter(Event.event_type == event_type)
        
        # Only get events with ML predictions
        query = query.filter(Event.ml_model_version.isnot(None))
        
        results = query.limit(limit).all()
        
        predictions = []
        wins = 0
        losses = 0
        pending = 0
        streak = 0
        last_result = None
        
        for event, outcome in results:
            if outcome:
                direction_correct = outcome.direction_correct
                actual_return = outcome.return_pct
                if direction_correct is True:
                    outcome_status = "correct"
                    wins += 1
                    if last_result == "correct" or last_result is None:
                        streak += 1
                    last_result = "correct"
                elif direction_correct is False:
                    outcome_status = "incorrect"
                    losses += 1
                    if last_result == "incorrect":
                        streak -= 1
                    elif last_result is None:
                        streak = -1
                    else:
                        streak = -1
                    last_result = "incorrect"
                else:
                    outcome_status = "pending"
                    pending += 1
            else:
                outcome_status = "pending"
                pending += 1
                actual_return = None
                direction_correct = None
            
            predictions.append(RecentPrediction(
                event_id=event.id,
                ticker=event.ticker,
                event_type=event.event_type,
                title=event.title[:100] if event.title else "",
                event_date=event.date.isoformat() if event.date else "",
                predicted_direction=event.direction or "neutral",
                predicted_impact=event.impact_score or 50,
                confidence=event.ml_confidence or event.confidence or 0.5,
                actual_return=actual_return,
                direction_correct=direction_correct,
                horizon=horizon,
                outcome_status=outcome_status,
            ))
        
        return ScorecardResponse(
            predictions=predictions,
            total_shown=len(predictions),
            wins=wins,
            losses=losses,
            pending=pending,
            streak=streak,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch predictions: {str(e)}")


@router.get(
    "/alerts",
    response_model=AlertsResponse,
    summary="Get performance alerts",
    description="Get alerts for significant accuracy changes or anomalies.",
)
async def get_accuracy_alerts(
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Get alerts for accuracy drops, spikes, or other notable changes."""
    try:
        alerts = []
        has_critical = False
        
        # Get recent snapshots to detect changes
        recent_snapshots = db.query(PredictionSnapshot).order_by(
            desc(PredictionSnapshot.timestamp)
        ).limit(10).all()
        
        if len(recent_snapshots) >= 2:
            current = recent_snapshots[0]
            previous = recent_snapshots[1]
            
            current_wr = current.overall_win_rate or 0
            previous_wr = previous.overall_win_rate or 0
            
            # Check for accuracy drop
            if previous_wr > 0:
                change_pct = ((current_wr - previous_wr) / previous_wr) * 100
                
                if change_pct < -10:
                    severity = "critical"
                    has_critical = True
                elif change_pct < -5:
                    severity = "warning"
                else:
                    severity = None
                
                if severity:
                    alerts.append(AccuracyAlert(
                        alert_id=f"wr_drop_{current.timestamp.strftime('%Y%m%d')}",
                        alert_type="accuracy_drop",
                        severity=severity,
                        message=f"Win rate dropped by {abs(change_pct):.1f}% compared to previous period",
                        metric_name="Win Rate",
                        current_value=current_wr * 100,
                        previous_value=previous_wr * 100,
                        change_percentage=change_pct,
                        detected_at=current.timestamp.isoformat(),
                        dismissed=False,
                    ))
                
                # Check for accuracy improvement
                if change_pct > 5:
                    alerts.append(AccuracyAlert(
                        alert_id=f"wr_improve_{current.timestamp.strftime('%Y%m%d')}",
                        alert_type="accuracy_improvement",
                        severity="info",
                        message=f"Win rate improved by {change_pct:.1f}% compared to previous period",
                        metric_name="Win Rate",
                        current_value=current_wr * 100,
                        previous_value=previous_wr * 100,
                        change_percentage=change_pct,
                        detected_at=current.timestamp.isoformat(),
                        dismissed=False,
                    ))
            
            # Check for MAE spike
            current_mae = float(current.overall_mae) if current.overall_mae else 0
            previous_mae = float(previous.overall_mae) if previous.overall_mae else 0
            
            if previous_mae > 0:
                mae_change_pct = ((current_mae - previous_mae) / previous_mae) * 100
                
                if mae_change_pct > 20:
                    severity = "critical" if mae_change_pct > 50 else "warning"
                    if severity == "critical":
                        has_critical = True
                    
                    alerts.append(AccuracyAlert(
                        alert_id=f"mae_spike_{current.timestamp.strftime('%Y%m%d')}",
                        alert_type="mae_spike",
                        severity=severity,
                        message=f"Prediction error (MAE) increased by {mae_change_pct:.1f}%",
                        metric_name="MAE",
                        current_value=current_mae,
                        previous_value=previous_mae,
                        change_percentage=mae_change_pct,
                        detected_at=current.timestamp.isoformat(),
                        dismissed=False,
                    ))
        
        # If no alerts, add info message
        if not alerts:
            # Get overall stats for context
            latest = db.query(PredictionSnapshot).order_by(
                desc(PredictionSnapshot.timestamp)
            ).first()
            
            if latest:
                alerts.append(AccuracyAlert(
                    alert_id="status_ok",
                    alert_type="accuracy_improvement",
                    severity="info",
                    message=f"Model performing normally at {(latest.overall_win_rate or 0) * 100:.1f}% accuracy",
                    metric_name="Win Rate",
                    current_value=(latest.overall_win_rate or 0) * 100,
                    previous_value=(latest.overall_win_rate or 0) * 100,
                    change_percentage=0,
                    detected_at=latest.timestamp.isoformat(),
                    dismissed=False,
                ))
        
        return AlertsResponse(
            alerts=alerts,
            has_critical=has_critical,
            total_alerts=len(alerts),
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch alerts: {str(e)}")


@router.get(
    "/horizon-comparison",
    response_model=HorizonComparisonResponse,
    summary="Compare accuracy across time horizons",
    description="Compare prediction accuracy between 1-day, 7-day, and 30-day horizons.",
)
async def get_horizon_comparison(
    model_version: Optional[str] = Query(None, description="Filter by model version"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    db: Session = Depends(get_db),
    user=Depends(get_current_user_with_plan),
):
    """Compare prediction accuracy across different time horizons."""
    try:
        # Get latest metrics for each horizon
        horizons_to_check = ["1d", "7d", "30d"]
        horizon_data = []
        
        for h in horizons_to_check:
            query = db.query(
                func.avg(PredictionMetrics.win_rate).label('avg_win_rate'),
                func.avg(PredictionMetrics.mae).label('avg_mae'),
                func.sum(PredictionMetrics.total_predictions).label('total_predictions'),
                func.avg(PredictionMetrics.avg_confidence).label('avg_confidence'),
            ).filter(PredictionMetrics.horizon == h)
            
            if model_version:
                query = query.filter(PredictionMetrics.model_version == model_version)
            if event_type:
                query = query.filter(PredictionMetrics.event_type == event_type)
            
            result = query.first()
            
            if result and result.avg_win_rate is not None:
                horizon_data.append(HorizonComparisonItem(
                    horizon=h,
                    display_name=get_horizon_display_name(h),
                    win_rate=float(result.avg_win_rate),
                    mae=float(result.avg_mae) if result.avg_mae else 0,
                    total_predictions=int(result.total_predictions) if result.total_predictions else 0,
                    confidence_avg=float(result.avg_confidence) if result.avg_confidence else 0.5,
                ))
        
        if not horizon_data:
            return HorizonComparisonResponse(
                horizons=[],
                best_horizon="N/A",
                recommendation="Insufficient data to compare horizons.",
            )
        
        # Find best horizon
        best_horizon = max(horizon_data, key=lambda x: x.win_rate)
        
        # Generate recommendation
        if best_horizon.win_rate > 0.6:
            recommendation = f"The {best_horizon.display_name} horizon shows the strongest performance at {best_horizon.win_rate*100:.1f}% accuracy. Consider prioritizing signals at this timeframe."
        elif best_horizon.win_rate > 0.5:
            recommendation = f"The {best_horizon.display_name} horizon has the best accuracy at {best_horizon.win_rate*100:.1f}%, though all horizons show room for improvement."
        else:
            recommendation = "All time horizons are showing mixed results. Consider using higher confidence signals only."
        
        return HorizonComparisonResponse(
            horizons=horizon_data,
            best_horizon=best_horizon.horizon,
            recommendation=recommendation,
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch horizon comparison: {str(e)}")
