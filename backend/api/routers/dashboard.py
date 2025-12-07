"""Consolidated dashboard router for optimized page loading"""
from fastapi import APIRouter, Depends, Request
from typing import Optional, List, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
import time
import logging

from api.dependencies import get_data_manager, get_db
from api.utils.auth import get_current_user_optional
from data_manager import DataManager
from releaseradar.db.models import ScanJob, Company, Event

try:
    from scanners.catalog import get_scanner_count, SCANNERS
except ImportError:
    def get_scanner_count():
        return 3
    SCANNERS = []

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

_dashboard_cache = {"data": None, "timestamp": 0, "user_id": None}
DASHBOARD_CACHE_TTL = 30


def _get_scanner_statuses(db: Session) -> List[dict]:
    """Get scanner status data efficiently"""
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
    
    scanner_statuses = {}
    for scanner_key, source in scanner_key_to_source.items():
        recent_job = db.execute(
            select(ScanJob).where(
                and_(
                    ScanJob.scope == "scanner",
                    ScanJob.scanner_key == scanner_key
                )
            ).order_by(ScanJob.created_at.desc()).limit(1)
        ).scalar_one_or_none()
        
        if recent_job:
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
                'last_run': recent_job.created_at.isoformat() if recent_job.created_at else None,
                'next_run': None,
                'level': level,
                'discoveries': recent_job.items_found or 0,
                'message': message
            }
    
    statuses = []
    for scanner in SCANNERS:
        if not scanner.enabled:
            continue
        
        if scanner.key in scanner_statuses:
            statuses.append({
                'scanner': scanner.label,
                **scanner_statuses[scanner.key]
            })
        else:
            statuses.append({
                'scanner': scanner.label,
                'last_run': None,
                'next_run': None,
                'level': 'pending',
                'discoveries': 0,
                'message': 'No runs recorded'
            })
    
    return statuses


def _get_recent_discoveries(db: Session, limit: int = 10) -> tuple:
    """Get recent discoveries and last scan metadata"""
    recent_job = db.execute(
        select(ScanJob).where(
            ScanJob.status == 'success'
        ).order_by(ScanJob.created_at.desc()).limit(1)
    ).scalar_one_or_none()
    
    last_scan = None
    if recent_job:
        last_scan = {
            'started_at': recent_job.created_at.isoformat() if recent_job.created_at else None,
            'is_automatic': recent_job.is_automatic if hasattr(recent_job, 'is_automatic') else True
        }
    
    cutoff = datetime.utcnow() - timedelta(hours=24)
    discoveries = db.execute(
        select(Event).where(
            Event.created_at >= cutoff
        ).order_by(Event.created_at.desc()).limit(limit)
    ).scalars().all()
    
    discovery_list = []
    for event in discoveries:
        discovery_list.append({
            'id': event.id,
            'ticker': event.ticker,
            'title': event.title,
            'event_type': event.event_type,
            'impact_score': event.impact_score,
            'direction': event.direction,
            'timestamp': event.created_at.isoformat() if event.created_at else None,
            'source_url': event.source_url
        })
    
    return discovery_list, last_scan


@router.get("/init")
async def get_dashboard_init(
    request: Request,
    mode: Optional[str] = "watchlist",
    db: Session = Depends(get_db),
    dm: DataManager = Depends(get_data_manager),
    current_user: Optional[dict] = Depends(get_current_user_optional)
):
    """
    Consolidated dashboard initialization endpoint.
    Returns all data needed to render the dashboard in a single request.
    
    Combines: events, companies, scanner status, scanner count, company count, discoveries
    
    Cache: 30 seconds TTL to reduce database load
    """
    current_time = time.time()
    user_id = current_user.get("user_id") if current_user else None
    cache_key = f"{user_id}_{mode}"
    
    if (
        _dashboard_cache["data"] 
        and _dashboard_cache.get("cache_key") == cache_key
        and (current_time - _dashboard_cache["timestamp"]) < DASHBOARD_CACHE_TTL
    ):
        return _dashboard_cache["data"]
    
    try:
        active_tickers = None
        if mode and user_id and mode in ['watchlist', 'portfolio']:
            active_tickers = dm.get_user_active_tickers(user_id, mode)
        
        events = dm.get_events(
            ticker=active_tickers,
            empty_means_all=True
        )[:10]
        
        event_list = []
        for event in events:
            event_list.append({
                'id': event.get('id'),
                'ticker': event.get('ticker'),
                'title': event.get('title'),
                'event_type': event.get('event_type'),
                'date': event.get('date'),
                'impact_score': event.get('impact_score'),
                'direction': event.get('direction'),
                'confidence': event.get('confidence'),
                'rationale': event.get('rationale'),
                'source_url': event.get('source_url'),
                'info_tier': event.get('info_tier'),
                'company_name': event.get('company_name'),
                'sector': event.get('sector'),
            })
        
        scanner_statuses = _get_scanner_statuses(db)
        scanner_count = get_scanner_count()
        
        company_count = db.execute(
            select(func.count()).select_from(Company).where(Company.tracked == True)
        ).scalar() or 0
        
        discoveries, last_scan = _get_recent_discoveries(db, limit=10)
        
        response_data = {
            "events": event_list,
            "scanners": scanner_statuses,
            "scanner_count": scanner_count,
            "company_count": company_count,
            "discoveries": discoveries,
            "last_scan": last_scan,
            "cached_at": datetime.utcnow().isoformat(),
        }
        
        _dashboard_cache["data"] = response_data
        _dashboard_cache["timestamp"] = current_time
        _dashboard_cache["cache_key"] = cache_key
        
        return response_data
        
    except Exception as e:
        logger.error(f"Dashboard init error: {e}")
        raise


@router.get("/stats")
async def get_dashboard_stats(
    db: Session = Depends(get_db),
):
    """
    Quick stats endpoint for dashboard cards.
    Cached for 60 seconds.
    """
    scanner_count = get_scanner_count()
    
    company_count = db.execute(
        select(func.count()).select_from(Company).where(Company.tracked == True)
    ).scalar() or 0
    
    cutoff = datetime.utcnow() - timedelta(hours=24)
    event_count_24h = db.execute(
        select(func.count()).select_from(Event).where(Event.created_at >= cutoff)
    ).scalar() or 0
    
    return {
        "scanner_count": scanner_count,
        "company_count": company_count,
        "events_24h": event_count_24h,
    }
