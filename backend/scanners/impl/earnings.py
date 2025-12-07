"""
Earnings calls scanner - monitors company earnings announcements and calls.

Sources:
- SEC 8-K Item 2.02 (Results of Operations and Financial Condition)
- EDGAR RSS feeds via shared SEC service
"""

import logging
from typing import List, Dict, Any, Optional

from releaseradar.services.sec import get_recent_filings, create_filing_title, get_8k_item_description
from scanners.utils import normalize_event

logger = logging.getLogger(__name__)


def scan_earnings_calls(tickers: List[str], companies: Optional[Dict[str, Dict]] = None, limit_per_ticker: int = 5) -> List[Dict[str, Any]]:
    """
    Scan for earnings calls and financial result announcements.
    
    Args:
        tickers: List of ticker symbols to scan
        companies: Dictionary mapping ticker -> company info (name, sector)
        limit_per_ticker: Max events to return per ticker
        
    Returns:
        List of normalized event dicts
    """
    logger.info(f"Earnings scanner starting for {len(tickers)} tickers")
    
    if companies is None:
        companies = {}
    
    events = []
    
    for ticker in tickers:
        try:
            company_info = companies.get(ticker, {})
            company_name = company_info.get('name', ticker)
            sector = company_info.get('sector', 'Unknown')
            
            # Fetch 8-K filings with Item 2.02 (earnings announcements) from last 120 days
            filings = get_recent_filings(
                ticker=ticker,
                company_name=company_name,
                form_types=['8-K'],
                item_filters=['2.02'],
                limit=limit_per_ticker,
                days_back=120
            )
            
            logger.info(f"Found {len(filings)} earnings filings for {ticker}")
            
            for filing in filings:
                items = filing.get('items', [])
                
                # Create earnings-specific title
                if '2.02' in items:
                    title = f"Earnings Release: {get_8k_item_description('2.02')}"
                else:
                    title = create_filing_title('8-K', filing.get('title') or '', items)
                
                event = normalize_event(
                    ticker=ticker,
                    company_name=company_name,
                    event_type='earnings',
                    title=title,
                    date=filing['date'],
                    source='SEC EDGAR',
                    source_url=filing['url'],
                    description=filing.get('title', ''),
                    source_scanner='earnings',
                    sector=sector
                )
                
                events.append(event)
        
        except Exception as e:
            logger.error(f"Error scanning earnings for {ticker}: {e}")
            continue
    
    logger.info(f"Earnings scanner completed: {len(events)} events found")
    return events
