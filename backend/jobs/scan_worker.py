"""
Scan job worker - processes manual scan requests from the scan_jobs queue.

This worker polls the scan_jobs table for queued jobs and executes them
using the existing scanner infrastructure. It respects concurrency limits
and handles errors gracefully.
"""

import sys
import time
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from releaseradar.db.session import get_db as get_db_session
from releaseradar.db.models import ScanJob, Company
from database import close_db_session
from scanners.catalog import SCANNERS
from scanners.impl.sec_edgar import scan_sec_edgar
from scanners.impl.sec_8k import scan_sec_8k
from scanners.impl.sec_10q import scan_sec_10q
from scanners.impl.earnings import scan_earnings_calls
from scanners.impl.guidance import scan_guidance
from scanners.impl.ma import scan_ma
from scanners.impl.product_launch import scan_product_launch
from scanners.impl.dividend import scan_dividend_buyback
from scanners.impl.fda import scan_fda
from scanners.impl.press import scan_press
from releaseradar.scanners.form4_scanner import scan_form4_filings
from data_manager import DataManager
from sqlalchemy import select, and_
import logging

logger = logging.getLogger(__name__)

# Prometheus metrics - optional
try:
    from api.utils.metrics import increment_counter
except ImportError:
    def increment_counter(*args, **kwargs):
        pass

POLL_INTERVAL = 5
MAX_WORKERS = 4

# Scanner function mapping - all 11 scanners
SCANNER_FUNCTIONS = {
    'sec_edgar': scan_sec_edgar,
    'sec_8k': scan_sec_8k,
    'sec_10q': scan_sec_10q,
    'earnings_calls': scan_earnings_calls,
    'guidance_updates': scan_guidance,
    'ma_activity': scan_ma,
    'product_launch': scan_product_launch,
    'dividend_buyback': scan_dividend_buyback,
    'fda_announcements': scan_fda,
    'company_press': scan_press,
    'form4_insider': scan_form4_filings
}


def get_tracked_companies_data(db) -> tuple[List[str], dict]:
    """
    Get tracked companies from database.
    
    Returns: (tickers_list, companies_dict)
    """
    companies = db.query(Company).filter(Company.tracked == True).all()
    
    tickers = []
    companies_dict = {}
    
    for company in companies:
        tickers.append(company.ticker)
        companies_dict[company.ticker] = {
            'name': company.name,
            'sector': company.sector,
            'industry': company.industry
        }
    
    return tickers, companies_dict


def insert_events_with_deduplication(events: List[dict], data_manager: DataManager) -> int:
    """
    Insert events with deduplication.
    
    Returns: Number of events successfully inserted
    """
    inserted_count = 0
    
    for event_data in events:
        try:
            # Check if event already exists using event_exists
            if data_manager.event_exists(
                ticker=event_data['ticker'],
                event_type=event_data['event_type'],
                date=event_data['date'],
                title=event_data['title']
            ):
                logger.debug(f"Event already exists, skipping: {event_data['ticker']} {event_data['title']}")
                continue
            
            # Insert event
            data_manager.add_event(
                ticker=event_data['ticker'],
                company_name=event_data['company_name'],
                event_type=event_data['event_type'],
                title=event_data['title'],
                date=event_data['date'],
                source=event_data['source'],
                source_url=event_data['source_url'],
                description=event_data.get('description'),
                sector=event_data.get('sector'),
                auto_score=True,
                info_tier=event_data.get('info_tier', 'primary'),
                info_subtype=event_data.get('info_subtype'),
                metadata=event_data.get('metadata')
            )
            
            inserted_count += 1
            logger.info(f"Inserted event: {event_data['ticker']} - {event_data['title']}")
        
        except Exception as e:
            logger.error(f"Error inserting event {event_data.get('title', 'unknown')}: {e}")
            continue
    
    return inserted_count


def execute_company_scan(job_id: int, ticker: str) -> tuple[int, str | None]:
    """
    Run all scanners for a single company.
    
    Returns: (items_found, error_message)
    """
    db = get_db_session()
    
    try:
        # Get company data
        company = db.query(Company).filter(Company.ticker == ticker).first()
        if not company:
            return 0, f"Company {ticker} not found"
        
        # Build company info dict
        companies_dict = {
            ticker: {
                'name': company.name,
                'sector': company.sector,
                'industry': company.industry
            }
        }
        
        print(f"[Worker] Running all scanners for {ticker}")
        
        # Run all scanners for this company
        all_events = []
        
        for scanner_key, scanner_fn in SCANNER_FUNCTIONS.items():
            try:
                print(f"[Worker] Running {scanner_key} for {ticker}")
                events = scanner_fn([ticker], companies=companies_dict, limit_per_ticker=5)
                all_events.extend(events)
                print(f"[Worker] {scanner_key} found {len(events)} events for {ticker}")
            except Exception as e:
                print(f"[Worker] Error in {scanner_key} for {ticker}: {e}")
                logger.error(f"Error in {scanner_key} for {ticker}: {e}")
                continue
        
        # Insert events with deduplication
        data_manager = DataManager()
        items_found = insert_events_with_deduplication(all_events, data_manager)
        
        print(f"[Worker] Company scan {ticker} completed: {items_found}/{len(all_events)} events inserted")
        return items_found, None
        
    except Exception as e:
        return 0, str(e)
    finally:
        close_db_session(db)


def execute_scanner_scan(job_id: int, scanner_key: str) -> tuple[int, str | None]:
    """
    Run a specific scanner across all tracked companies.
    
    Returns: (items_found, error_message)
    """
    db = get_db_session()
    
    try:
        # Check if scanner exists
        if scanner_key not in SCANNER_FUNCTIONS:
            return 0, f"Scanner {scanner_key} not found"
        
        scanner_fn = SCANNER_FUNCTIONS[scanner_key]
        
        # Get tracked companies
        tickers, companies_dict = get_tracked_companies_data(db)
        
        if not tickers:
            return 0, "No tracked companies found"
        
        print(f"[Worker] Running {scanner_key} for {len(tickers)} companies")
        
        # Run scanner
        events = scanner_fn(tickers, companies=companies_dict, limit_per_ticker=3)
        
        print(f"[Worker] {scanner_key} found {len(events)} total events")
        
        # Insert events with deduplication
        data_manager = DataManager()
        items_found = insert_events_with_deduplication(events, data_manager)
        
        print(f"[Worker] Scanner {scanner_key} completed: {items_found}/{len(events)} events inserted")
        return items_found, None
        
    except Exception as e:
        logger.error(f"Error in scanner {scanner_key}: {e}")
        return 0, str(e)
    finally:
        close_db_session(db)


def process_job(job_id: int, scope: str, ticker: str | None, scanner_key: str | None):
    """Process a single scan job."""
    db = get_db_session()
    
    try:
        # Update status to running
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if not job:
            return
        
        job.status = "running"
        job.started_at = datetime.utcnow()
        db.commit()
        
        print(f"[Worker] Processing job {job_id}: scope={scope}, ticker={ticker}, scanner={scanner_key}")
        
        # Execute based on scope
        if scope == "company":
            items_found, error = execute_company_scan(job_id, ticker)
        elif scope == "scanner":
            items_found, error = execute_scanner_scan(job_id, scanner_key)
        else:
            error = f"Invalid scope: {scope}"
            items_found = 0
        
        # Update job with results
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        job.finished_at = datetime.utcnow()
        job.items_found = items_found
        
        if error:
            job.status = "error"
            job.error = error
            increment_counter("manual_scan_jobs_error_total", {"scope": scope})
        else:
            job.status = "success"
            increment_counter("manual_scan_jobs_total", {"scope": scope})
        
        db.commit()
        
        runtime = (job.finished_at - job.started_at).total_seconds()
        print(f"[Worker] Completed job {job_id}: status={job.status}, items={items_found}, runtime={runtime:.1f}s")
        
    except Exception as e:
        print(f"[Worker] Error processing job {job_id}: {e}")
        job = db.query(ScanJob).filter(ScanJob.id == job_id).first()
        if job:
            job.status = "error"
            job.error = str(e)
            job.finished_at = datetime.utcnow()
            db.commit()
            increment_counter("manual_scan_jobs_error_total", {"scope": scope})
    finally:
        close_db_session(db)


def run_worker():
    """Main worker loop - polls for queued jobs and processes them."""
    print("[Worker] Scan worker started")
    
    while True:
        try:
            db = get_db_session()
            
            # Get queued jobs
            queued_jobs = db.execute(
                select(ScanJob).where(ScanJob.status == "queued").order_by(ScanJob.created_at)
            ).scalars().all()
            
            if queued_jobs:
                print(f"[Worker] Found {len(queued_jobs)} queued job(s)")
                
                # Process jobs with bounded concurrency
                with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                    futures = []
                    for job in queued_jobs:
                        future = executor.submit(
                            process_job,
                            job.id,
                            job.scope,
                            job.ticker,
                            job.scanner_key
                        )
                        futures.append(future)
                    
                    # Wait for all jobs to complete
                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            print(f"[Worker] Job execution error: {e}")
            
            close_db_session(db)
            
        except Exception as e:
            print(f"[Worker] Error in main loop: {e}")
        
        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    run_worker()
