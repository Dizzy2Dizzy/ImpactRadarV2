"""
Data Quality API router for monitoring and validation.

Provides endpoints for tracking data freshness, pipeline health, lineage, and audit logs.
Requires Pro plan minimum. Admin-only endpoints for audit logs.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from api.dependencies import get_db
from api.utils.auth import get_current_user_with_plan, require_admin
from api.utils.paywall import require_plan
from releaseradar.services.quality_metrics import QualityMetricsService
from sqlalchemy.orm import Session

router = APIRouter(prefix="/data-quality", tags=["data-quality"])


# Response Models
class FreshnessIndicator(BaseModel):
    """Freshness indicator for a data metric."""
    metric_key: str = Field(description="Metric identifier (e.g., 'events_total', 'prices_spy')")
    scope: str = Field(description="Scope: 'global', 'portfolio', or 'watchlist'")
    sample_count: int = Field(description="Number of records in this snapshot")
    freshness_ts: str = Field(description="ISO timestamp of most recent data point")
    source_job: str = Field(description="Job that generated this snapshot")
    quality_grade: str = Field(description="Quality grade: 'excellent', 'good', 'fair', or 'stale'")
    summary: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    recorded_at: str = Field(description="When this snapshot was recorded")


class PipelineHealthResponse(BaseModel):
    """Pipeline health status and metrics."""
    total_runs: int = Field(description="Total pipeline runs in time window")
    success_rate: float = Field(description="Success rate percentage")
    avg_runtime_seconds: float = Field(description="Average runtime in seconds")
    recent_failures: List[Dict[str, Any]] = Field(default_factory=list, description="Recent failed runs")
    jobs: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Per-job statistics")


class SourceEventResponse(BaseModel):
    """Source event information for lineage."""
    ticker: str
    event_type: str
    date: str
    source_url: str
    event_id: int
    title: str


class OutcomeDataResponse(BaseModel):
    """Outcome data for an event."""
    horizon: str
    return_pct: Optional[float]  # Abnormal return (stock - benchmark)
    return_pct_raw: Optional[float]  # Raw stock return
    abs_return_pct: Optional[float]  # Absolute return magnitude
    direction_correct: Optional[bool]
    has_benchmark_data: bool  # Whether SPY benchmark data was available


class PriceRecordResponse(BaseModel):
    """Price history record."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class LineageDetailResponse(BaseModel):
    """Detailed lineage data with aggregated source events, outcomes, and prices."""
    metric_key: str
    metric_name: str
    source_events: List[SourceEventResponse] = Field(default_factory=list)
    outcomes: List[OutcomeDataResponse] = Field(default_factory=list)
    price_history: List[PriceRecordResponse] = Field(default_factory=list)
    payload_hash: Optional[str] = None
    generated_at: str
    total_events: int


class LineageRecord(BaseModel):
    """Data lineage record."""
    metric_key: str
    entity_id: int
    entity_type: str
    source_url: Optional[str] = None
    payload_hash: Optional[str] = None
    observed_at: str


class AuditLogResponse(BaseModel):
    """Audit log response with pagination."""
    entries: List[Dict[str, Any]]
    total: int
    limit: int
    offset: int
    has_more: bool


class ValidationReportResponse(BaseModel):
    """Comprehensive validation report."""
    report_time: str
    overall_health: str = Field(description="'healthy', 'warning', or 'critical'")
    freshness_issues: List[Dict[str, Any]] = Field(default_factory=list)
    pipeline_issues: List[Dict[str, Any]] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


@router.get(
    "/freshness",
    response_model=List[FreshnessIndicator],
    summary="Get data freshness indicators",
    description="Returns freshness indicators for all tracked metrics. Shows last update times, sample sizes, and quality grades. Requires Pro plan.",
)
async def get_freshness_indicators(
    scope: Optional[str] = Query(None, description="Filter by scope: 'global', 'portfolio', or 'watchlist'"),
    metric_keys: Optional[str] = Query(None, description="Comma-separated list of metric keys to filter"),
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Get freshness indicators for all metrics or filtered by scope/keys.
    
    Shows when data was last updated, sample sizes, and quality grades.
    Useful for monitoring data pipeline health and detecting stale data.
    
    **Plan Requirement:** Pro or higher
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Data quality monitoring",
        user_data.get("trial_ends_at")
    )
    
    # Parse metric_keys if provided
    keys_list = None
    if metric_keys:
        keys_list = [k.strip() for k in metric_keys.split(",")]
    
    service = QualityMetricsService(db)
    indicators = service.get_freshness_indicators(scope=scope, metric_keys=keys_list)
    
    return [
        FreshnessIndicator(**indicator)
        for indicator in indicators
    ]


@router.get(
    "/pipeline-health",
    response_model=PipelineHealthResponse,
    summary="Get pipeline health status",
    description="Returns pipeline execution statistics including success rates and recent failures. Requires Pro plan.",
)
async def get_pipeline_health(
    job_name: Optional[str] = Query(None, description="Filter by specific job name"),
    hours_back: int = Query(24, ge=1, le=168, description="Look back this many hours (max 7 days)"),
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Get pipeline health status and success/failure rates.
    
    Returns aggregate statistics for all data pipeline jobs including:
    - Success rate
    - Average runtime
    - Recent failures
    - Per-job statistics
    
    **Plan Requirement:** Pro or higher
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Data quality monitoring",
        user_data.get("trial_ends_at")
    )
    
    service = QualityMetricsService(db)
    health = service.get_pipeline_health(job_name=job_name, hours_back=hours_back)
    
    return PipelineHealthResponse(**health)


@router.get(
    "/lineage/{metric_key}",
    response_model=LineageDetailResponse,
    summary="Get detailed data lineage for a metric",
    description="Returns detailed lineage data with aggregated source events, outcomes, and price history. Requires Pro plan.",
)
async def get_metric_lineage(
    metric_key: str,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Get detailed lineage data for a specific metric key.
    
    Returns a comprehensive view including:
    - Source events with full event details
    - Outcome data showing predicted vs actual returns
    - Price history for related tickers
    - Metadata (payload hash, timestamps, counts)
    
    Useful for debugging data issues, verifying data provenance,
    and understanding the full context of events and their outcomes.
    
    **Plan Requirement:** Pro or higher
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Data quality monitoring",
        user_data.get("trial_ends_at")
    )
    
    service = QualityMetricsService(db)
    lineage_data = service.get_metric_lineage_detail(metric_key=metric_key)
    
    # Service method returns minimal valid response even if no data found,
    # so we don't need to check for None
    return LineageDetailResponse(**lineage_data)


@router.get(
    "/audit-log",
    response_model=AuditLogResponse,
    summary="Get audit log entries (Admin only)",
    description="Returns audit log entries with filtering and pagination. Admin access only.",
)
async def get_audit_log(
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    entity_id: Optional[int] = Query(None, description="Filter by entity ID"),
    action: Optional[str] = Query(None, description="Filter by action: 'create', 'update', or 'delete'"),
    performed_by: Optional[int] = Query(None, description="Filter by user ID"),
    date_from: Optional[str] = Query(None, description="Filter from date (ISO format)"),
    date_to: Optional[str] = Query(None, description="Filter to date (ISO format)"),
    limit: int = Query(100, ge=1, le=500, description="Results per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Get audit log entries with filtering and pagination.
    
    Returns all data modification events including creates, updates, and deletes.
    Includes diffs for updates and user attribution.
    
    **Access:** Admin only
    """
    # Enforce admin access
    require_admin(user_data)
    
    # Parse dates if provided
    from_dt = None
    to_dt = None
    
    try:
        if date_from:
            from_dt = datetime.fromisoformat(date_from.replace('Z', '+00:00'))
        if date_to:
            to_dt = datetime.fromisoformat(date_to.replace('Z', '+00:00'))
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {str(e)}. Use ISO format (YYYY-MM-DDTHH:MM:SS)"
        )
    
    service = QualityMetricsService(db)
    result = service.get_audit_log(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        performed_by=performed_by,
        date_from=from_dt,
        date_to=to_dt,
        limit=limit,
        offset=offset
    )
    
    return AuditLogResponse(**result)


@router.get(
    "/validation-report",
    response_model=ValidationReportResponse,
    summary="Get comprehensive validation report",
    description="Returns a comprehensive data quality validation report with health status and recommendations. Requires Pro plan.",
)
async def get_validation_report(
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """
    Get comprehensive data quality validation report.
    
    Analyzes all quality metrics and returns:
    - Overall health status
    - Freshness issues (stale data)
    - Pipeline issues (failures)
    - Actionable recommendations
    
    **Plan Requirement:** Pro or higher
    """
    # Enforce Pro plan requirement
    require_plan(
        user_data["plan"],
        "pro",
        "Data quality monitoring",
        user_data.get("trial_ends_at")
    )
    
    service = QualityMetricsService(db)
    
    # Get freshness indicators
    freshness = service.get_freshness_indicators()
    
    # Get pipeline health
    pipeline_health = service.get_pipeline_health(hours_back=24)
    
    # Analyze for issues
    freshness_issues = []
    for indicator in freshness:
        if indicator["quality_grade"] in ["stale", "fair"]:
            freshness_issues.append({
                "metric_key": indicator["metric_key"],
                "grade": indicator["quality_grade"],
                "last_updated": indicator["freshness_ts"],
                "samples": indicator["sample_count"],
            })
    
    pipeline_issues = []
    if pipeline_health["success_rate"] < 90:
        pipeline_issues.append({
            "issue": "Low success rate",
            "success_rate": pipeline_health["success_rate"],
            "failures": len(pipeline_health["recent_failures"]),
        })
    
    # Generate recommendations
    recommendations = []
    
    if len(freshness_issues) > 0:
        recommendations.append(
            f"Found {len(freshness_issues)} metrics with stale/fair quality. "
            "Review data pipeline schedules."
        )
    
    if pipeline_health["success_rate"] < 90:
        recommendations.append(
            f"Pipeline success rate is {pipeline_health['success_rate']:.1f}%. "
            "Investigate recent failures in pipeline logs."
        )
    
    if len(pipeline_health["recent_failures"]) > 5:
        recommendations.append(
            f"High failure rate detected ({len(pipeline_health['recent_failures'])} recent failures). "
            "Check error logs and pipeline configuration."
        )
    
    # Determine overall health
    overall_health = "healthy"
    if len(freshness_issues) > 5 or pipeline_health["success_rate"] < 80:
        overall_health = "critical"
    elif len(freshness_issues) > 0 or pipeline_health["success_rate"] < 95:
        overall_health = "warning"
    
    return ValidationReportResponse(
        report_time=datetime.utcnow().isoformat(),
        overall_health=overall_health,
        freshness_issues=freshness_issues,
        pipeline_issues=pipeline_issues,
        recommendations=recommendations,
    )
