"""
SEC 10-Q scanner - monitors quarterly financial report filings.

Sources:
- SEC EDGAR filing feeds via shared SEC service
"""

import logging
from typing import List, Dict, Any, Optional

from releaseradar.services.sec import get_recent_filings, create_filing_title
from scanners.utils import normalize_event

logger = logging.getLogger(__name__)


def scan_sec_10q(tickers: List[str], companies: Optional[Dict[str, Dict]] = None, limit_per_ticker: int = 1) -> List[Dict[str, Any]]:
    """
    Scan for SEC 10-Q filings (quarterly reports).
    
    Args:
        tickers: List of ticker symbols to scan
        companies: Dictionary mapping ticker -> company info (name, sector)
        limit_per_ticker: Max events to return per ticker
        
    Returns:
        List of normalized event dicts
    """
    logger.info(f"SEC 10-Q scanner starting for {len(tickers)} tickers")
    
    if companies is None:
        companies = {}
    
    events = []
    
    # 10-Q filings are less frequent, scan all tickers
    for ticker in tickers:
        try:
            company_info = companies.get(ticker, {})
            company_name = company_info.get('name', ticker)
            sector = company_info.get('sector', 'Unknown')
            
            # Fetch 10-Q filings from last 120 days (quarterly filings)
            filings = get_recent_filings(
                ticker=ticker,
                company_name=company_name,
                form_types=['10-Q'],
                limit=limit_per_ticker,
                days_back=120
            )
            
            logger.info(f"Found {len(filings)} 10-Q filings for {ticker}")
            
            for filing in filings:
                title = create_filing_title('10-Q', filing.get('title') or '')
                
                event = normalize_event(
                    ticker=ticker,
                    company_name=company_name,
                    event_type='sec_10q',
                    title=title,
                    date=filing['date'],
                    source='SEC EDGAR',
                    source_url=filing['url'],
                    description=filing.get('title', ''),
                    source_scanner='sec_10q',
                    sector=sector
                )
                
                events.append(event)
        
        except Exception as e:
            logger.error(f"Error scanning 10-Q for {ticker}: {e}")
            continue
    
    logger.info(f"SEC 10-Q scanner completed: {len(events)} events found")
    return events
