"""
SEC 8-K scanner - monitors current report filings (material events).

Sources:
- SEC EDGAR RSS feeds via shared SEC service
- Real-time filing alerts
"""

import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional

from releaseradar.services.sec import get_recent_filings, create_filing_title, classify_8k_event_type
from scanners.utils import normalize_event

logger = logging.getLogger(__name__)


def _scan_8k_single_ticker(args: tuple) -> List[Dict[str, Any]]:
    """Process a single ticker for 8-K filings - helper for parallel execution."""
    import random
    
    ticker, company_info, limit_per_ticker = args
    company_name = company_info.get('name', ticker)
    sector = company_info.get('sector', 'Unknown')
    events = []
    
    delay = random.uniform(0.5, 2.0)
    time.sleep(delay)
    
    try:
        filings = get_recent_filings(
            ticker=ticker,
            company_name=company_name,
            form_types=['8-K'],
            limit=limit_per_ticker,
            days_back=30
        )
        
        if filings:
            logger.debug(f"Found {len(filings)} 8-K filings for {ticker}")
        
        for filing in filings:
            items = filing.get('items', [])
            title = create_filing_title('8-K', filing.get('title') or '', items)
            event_type = classify_8k_event_type(items)
            metadata = {'8k_items': items} if items else {}
            
            event = normalize_event(
                ticker=ticker,
                company_name=company_name,
                event_type=event_type,
                title=title,
                date=filing['date'],
                source='SEC EDGAR',
                source_url=filing['url'],
                description=filing.get('title', ''),
                source_scanner='sec_8k',
                sector=sector,
                metadata=metadata
            )
            events.append(event)
    
    except Exception as e:
        logger.debug(f"Error scanning 8-K for {ticker}: {e}")
    
    return events


def scan_sec_8k(
    tickers: List[str],
    companies: Optional[Dict[str, Dict]] = None,
    limit_per_ticker: int = 3,
    batch_size: int = 50,
    batch_delay: float = 10.0,
    short_circuit: bool = False,
    short_circuit_threshold: int = 50
) -> List[Dict[str, Any]]:
    """
    Scan for SEC 8-K filings across tracked companies using parallel processing.
    
    Uses ThreadPoolExecutor with controlled parallelism and batch delays to
    stay within SEC rate limits (10 requests/second max).
    
    Args:
        tickers: List of ticker symbols to scan
        companies: Dictionary mapping ticker -> company info (name, sector)
        limit_per_ticker: Max events to return per ticker
        batch_size: Number of tickers per batch (default 50)
        batch_delay: Delay between batches in seconds (default 10.0)
        short_circuit: Disabled by default - we want all events
        short_circuit_threshold: Unused
        
    Returns:
        List of normalized event dicts
    """
    import time
    from releaseradar.services.cik_mapping import _ensure_cache_loaded
    
    logger.info(f"SEC 8-K scanner starting for {len(tickers)} tickers (parallel mode)")
    
    _ensure_cache_loaded()
    logger.info("CIK cache pre-loaded for 8-K parallel processing")
    
    if companies is None:
        companies = {}
    
    all_events = []
    
    args_list = [
        (ticker, companies.get(ticker, {'name': ticker, 'sector': 'Unknown'}), limit_per_ticker)
        for ticker in tickers
    ]
    
    max_workers = min(3, len(tickers))
    
    for batch_start in range(0, len(args_list), batch_size):
        batch = args_list[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (len(args_list) + batch_size - 1) // batch_size
        
        logger.info(f"SEC 8-K batch {batch_num}/{total_batches}: processing {len(batch)} tickers")
        
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="sec-8k-") as executor:
            futures = {executor.submit(_scan_8k_single_ticker, args): args[0] for args in batch}
            
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    events = future.result(timeout=60)
                    if events:
                        all_events.extend(events)
                except Exception as e:
                    logger.debug(f"Error processing 8-K for {ticker}: {e}")
        
        if batch_start + batch_size < len(args_list):
            logger.info(f"SEC 8-K: pausing {batch_delay}s between batches to respect rate limits")
            time.sleep(batch_delay)
    
    logger.info(f"SEC 8-K scanner completed: {len(all_events)} events found from {len(tickers)} tickers")
    return all_events
