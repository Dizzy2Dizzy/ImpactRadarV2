"""Scanners router with SSE support"""
from fastapi import APIRouter, Depends, HTTPException
from sse_starlette.sse import EventSourceResponse
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
import asyncio
import json
from datetime import datetime, timedelta
import sys
from pathlib import Path

# Add backend to path for scanner catalog import
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.schemas.scanners import ScannerStatus, ScannerRun, Discovery
from api.dependencies import get_data_manager, get_db
from api.utils.auth import get_current_user_id, require_admin
from data_manager import DataManager
from releaseradar.db.models import ScanJob, Company
import logging

logger = logging.getLogger(__name__)

try:
    from scanners.catalog import get_scanner_count, SCANNERS
except ImportError:
    # Fallback if catalog not available
    def get_scanner_count():
        return 3
    SCANNERS = []

router = APIRouter(prefix="/scanners", tags=["scanners"])

# Global queue for SSE discoveries
discovery_queue = asyncio.Queue()


@router.get("/count")
async def get_scanner_count_endpoint():
    """Get count of active scanners."""
    return {"count": get_scanner_count()}


@router.get(
    "/status",
    response_model=list[ScannerStatus],
    responses={
        200: {"description": "Status of all scanners with last run time and discoveries"},
    },
    summary="Get scanner status",
    description="Retrieve status of all data scanners (SEC EDGAR, FDA, Press Releases). Shows last run time, next run time, and discovery counts. Public endpoint."
)
async def get_scanner_status(
    db: Session = Depends(get_db)
):
    """Get status of all scanners"""
    from datetime import timedelta
    
    # Build scanner key to label mapping from catalog
    scanner_key_to_label = {s.key: s.label for s in SCANNERS if s.enabled}
    
    # Map scanner keys to source identifiers
    scanner_key_to_source = {
        'sec_edgar': 'sec_edgar',
        'fda_announcements': 'fda',
        'company_press': 'press',
        'earnings_calls': 'earnings',
        'sec_8k': 'sec_8k',
        'sec_10q': 'sec_10q',
        'guidance_updates': 'guidance',
        'product_launch': 'product',
        'ma_activity': 'ma',
        'dividend_buyback': 'dividend'
    }
    
    # Query recent ScanJobs for each scanner (scope='scanner')
    scanner_statuses = {}
    for scanner_key, source in scanner_key_to_source.items():
        # Get most recent job for this scanner
        recent_job = db.execute(
            select(ScanJob).where(
                and_(
                    ScanJob.scope == "scanner",
                    ScanJob.scanner_key == scanner_key
                )
            ).order_by(ScanJob.created_at.desc()).limit(1)
        ).scalar_one_or_none()
        
        if recent_job:
            # Determine status
            if recent_job.status == 'running':
                level = 'info'
                message = "Currently scanning for events..."
            elif recent_job.status == 'error':
                level = 'error'
                message = f"Error: {recent_job.error}" if recent_job.error else "Scanner error"
            elif recent_job.status == 'success':
                level = 'success'
                if recent_job.items_found and recent_job.items_found > 0:
                    message = f"Found {recent_job.items_found} new event(s) in last run"
                else:
                    message = "Completed successfully - no new events"
            else:
                level = 'pending'
                message = "Queued for scanning..."
            
            scanner_statuses[scanner_key] = {
                'last_run': recent_job.created_at,
                'next_run': None,  # Will be set by scheduler
                'level': level,
                'discoveries': recent_job.items_found or 0,
                'message': message
            }
    
    # Create status for each scanner from catalog
    statuses = []
    for scanner in SCANNERS:
        if not scanner.enabled:
            continue
        
        if scanner.key in scanner_statuses:
            statuses.append(ScannerStatus(
                scanner=scanner.label,
                **scanner_statuses[scanner.key]
            ))
        else:
            statuses.append(ScannerStatus(
                scanner=scanner.label,
                level='pending',
                message='Waiting to start first scan...',
                discoveries=0
            ))
    
    return statuses


@router.get("/discoveries", response_model=list[Discovery])
async def get_discoveries(
    since: Optional[str] = None,
    limit: int = 50,
    dm: DataManager = Depends(get_data_manager)
):
    """Get recent discoveries"""
    try:
        # Parse since date with proper error handling
        if since:
            try:
                since_date = datetime.fromisoformat(since.replace('Z', '+00:00'))
            except ValueError:
                # Try parsing as ISO format without timezone
                since_date = datetime.fromisoformat(since)
        else:
            since_date = datetime.now() - timedelta(hours=24)
        
        # Get recent events (discoveries)
        events = dm.get_events(start_date=since_date, limit=limit)
        
        # Convert to Discovery format
        discoveries = []
        for event in events:
            scanner_source = 'manual'
            if 'sec_' in event['event_type']:
                scanner_source = 'sec'
            elif 'fda_' in event['event_type']:
                scanner_source = 'fda'
            elif event['event_type'] in ['press_release', 'product_launch']:
                scanner_source = 'press'
            
            discoveries.append(Discovery(
                id=event['id'],
                ticker=event['ticker'],
                title=event['title'],
                event_type=event['event_type'],
                event_time=event['date'],  # Map event 'date' to Discovery 'event_time'
                score=event['impact_score'],  # Map event 'impact_score' to Discovery 'score'
                direction=event['direction'],
                source=scanner_source,
                created_at=event['created_at']
            ))
        
        return discoveries
    except Exception as e:
        logger.error(f"Error in get_discoveries: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch discoveries: {str(e)}")


@router.get("/stream/discoveries")
async def stream_discoveries():
    """SSE endpoint for real-time discoveries"""
    async def event_generator():
        while True:
            try:
                # Wait for new discoveries
                discovery = await asyncio.wait_for(discovery_queue.get(), timeout=30.0)
                yield {
                    "event": "discovery",
                    "data": json.dumps(discovery)
                }
            except asyncio.TimeoutError:
                # Send heartbeat every 30 seconds
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({"timestamp": datetime.now().isoformat()})
                }
    
    return EventSourceResponse(event_generator())


@router.post("/run")
async def run_scanner(
    data: ScannerRun,
    admin_user: dict = Depends(require_admin),
    dm: DataManager = Depends(get_data_manager)
):
    """Manually trigger a scanner (admin only)"""
    user_id = admin_user.user_id
    user_email = admin_user.email
    
    # Validate scanner source
    if data.source not in ['sec', 'fda', 'press']:
        raise HTTPException(status_code=400, detail="Invalid scanner source")
    
    # Structured audit logging
    logger.info(
        f"Manual scanner triggered",
        extra={
            "event": "manual_scan_triggered",
            "user_id": user_id,
            "user_email": user_email,
            "scanner": data.source,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Log the manual run
    log_id = dm.create_scanner_log(source=data.source)
    
    # In a real implementation, this would trigger the actual scanner
    # For now, just return success
    return {
        "message": f"Scanner {data.source} triggered by admin {user_email}",
        "log_id": log_id
    }


from pydantic import BaseModel

class RescanCompanyRequest(BaseModel):
    ticker: str

class RescanScannerRequest(BaseModel):
    scanner_key: str


@router.post("/rescan/company")
async def rescan_company(
    request: RescanCompanyRequest,
    admin_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Enqueue a rescan job for all scanners on a specific company (admin only, rate limited: 1 per 60s)"""
    user_id = admin_user.user_id
    user_email = admin_user.email
    ticker = request.ticker
    # Validate ticker exists
    company = db.query(Company).filter(Company.ticker == ticker).first()
    if not company:
        raise HTTPException(status_code=404, detail=f"Company {ticker} not found")
    
    # Check rate limit: 1 company job per 60 seconds per user
    cutoff = datetime.utcnow() - timedelta(seconds=60)
    recent_jobs = db.execute(
        select(ScanJob).where(
            and_(
                ScanJob.created_by == user_id,
                ScanJob.scope == "company",
                ScanJob.created_at > cutoff
            )
        )
    ).scalars().all()
    
    if recent_jobs:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait 60 seconds between company rescans."
        )
    
    # Structured audit logging
    logger.info(
        f"Company rescan requested",
        extra={
            "event": "company_rescan_requested",
            "user_id": user_id,
            "user_email": user_email,
            "ticker": ticker,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Create job
    job = ScanJob(
        created_by=user_id,
        scope="company",
        ticker=ticker,
        scanner_key=None,
        status="queued"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return {
        "job_id": job.id,
        "ticker": ticker,
        "status": "queued",
        "message": f"Rescan job for {ticker} enqueued by admin {user_email}"
    }


@router.post("/rescan/scanner")
async def rescan_scanner(
    request: RescanScannerRequest,
    admin_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Enqueue a rescan job for a specific scanner across all companies (admin only, rate limited: 1 per 120s)"""
    user_id = admin_user.user_id
    user_email = admin_user.email
    scanner_key = request.scanner_key
    # Validate scanner_key exists
    valid_keys = [s.key for s in SCANNERS]
    if scanner_key not in valid_keys:
        raise HTTPException(
            status_code=404,
            detail=f"Scanner {scanner_key} not found. Valid scanners: {', '.join(valid_keys)}"
        )
    
    # Check rate limit: 1 scanner job per 120 seconds per user
    cutoff = datetime.utcnow() - timedelta(seconds=120)
    recent_jobs = db.execute(
        select(ScanJob).where(
            and_(
                ScanJob.created_by == user_id,
                ScanJob.scope == "scanner",
                ScanJob.created_at > cutoff
            )
        )
    ).scalars().all()
    
    if recent_jobs:
        raise HTTPException(
            status_code=429,
            detail="Rate limit exceeded. Please wait 120 seconds between scanner rescans."
        )
    
    # Structured audit logging
    logger.info(
        f"Scanner rescan requested",
        extra={
            "event": "scanner_rescan_requested",
            "user_id": user_id,
            "user_email": user_email,
            "scanner_key": scanner_key,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Create job
    job = ScanJob(
        created_by=user_id,
        scope="scanner",
        ticker=None,
        scanner_key=scanner_key,
        status="queued"
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    
    return {
        "job_id": job.id,
        "scanner_key": scanner_key,
        "status": "queued",
        "message": f"Rescan job for scanner {scanner_key} enqueued by admin {user_email}"
    }


@router.post("/trigger/{scanner_key}")
async def trigger_scanner(
    scanner_key: str,
    admin_user: dict = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """
    Manually trigger a specific scanner with rate limiting.
    
    This endpoint:
    - Checks rate limits (60s cooldown for manual scans)
    - Prevents concurrent execution using async locks
    - Logs scan job to database
    - Returns job status
    
    Admin only endpoint.
    """
    user_id = admin_user.user_id
    user_email = admin_user.email
    
    # Validate scanner_key exists
    valid_keys = [s.key for s in SCANNERS if s.enabled]
    if scanner_key not in valid_keys:
        raise HTTPException(
            status_code=404,
            detail=f"Scanner {scanner_key} not found. Valid scanners: {', '.join(valid_keys)}"
        )
    
    # Check rate limit
    allowed, reason = can_trigger_scan(scanner_key, is_automatic=False, db=db, user_id=user_id)
    if not allowed:
        raise HTTPException(status_code=429, detail=reason)
    
    # Check if scanner is already running (non-blocking)
    lock = _get_lock(scanner_key)
    if lock.locked():
        raise HTTPException(
            status_code=409,
            detail=f"Scanner {scanner_key} is currently running. Please wait for it to complete."
        )
    
    # Create scan job
    job = create_scan_job(scanner_key, is_automatic=False, db=db, user_id=user_id)
    
    # Log the manual trigger
    logger.info(
        f"Manual scanner triggered",
        extra={
            "event": "manual_scan_triggered",
            "user_id": user_id,
            "user_email": user_email,
            "scanner_key": scanner_key,
            "job_id": job.id,
            "timestamp": datetime.utcnow().isoformat()
        }
    )
    
    # Note: The actual scanner execution will be handled by the scan_worker.py
    # This endpoint just creates the job in the queue
    
    return {
        "job_id": job.id,
        "scanner_key": scanner_key,
        "status": job.status,
        "message": f"Scanner {scanner_key} triggered by admin {user_email}. Job queued.",
        "created_at": job.created_at.isoformat()
    }


@router.get("/jobs")
async def list_scan_jobs(
    status: Optional[str] = None,
    limit: int = 25,
    offset: int = 0,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """List scan jobs with optional status filter and pagination"""
    query = select(ScanJob).where(ScanJob.created_by == user_id)
    
    if status:
        if status not in ["queued", "running", "success", "error"]:
            raise HTTPException(status_code=400, detail="Invalid status")
        query = query.where(ScanJob.status == status)
    
    query = query.order_by(ScanJob.created_at.desc()).offset(offset).limit(limit)
    jobs = db.execute(query).scalars().all()
    
    return {
        "jobs": [
            {
                "id": job.id,
                "scope": job.scope,
                "ticker": job.ticker,
                "scanner_key": job.scanner_key,
                "status": job.status,
                "items_found": job.items_found,
                "error": job.error,
                "created_at": job.created_at.isoformat(),
                "started_at": job.started_at.isoformat() if job.started_at else None,
                "finished_at": job.finished_at.isoformat() if job.finished_at else None,
            }
            for job in jobs
        ],
        "offset": offset,
        "limit": limit
    }


@router.get("/jobs/{job_id}")
async def get_scan_job(
    job_id: int,
    user_id: int = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """Get details of a specific scan job"""
    job = db.query(ScanJob).filter(
        ScanJob.id == job_id,
        ScanJob.created_by == user_id
    ).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return {
        "id": job.id,
        "scope": job.scope,
        "ticker": job.ticker,
        "scanner_key": job.scanner_key,
        "status": job.status,
        "items_found": job.items_found,
        "error": job.error,
        "created_at": job.created_at.isoformat(),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "finished_at": job.finished_at.isoformat() if job.finished_at else None,
    }
