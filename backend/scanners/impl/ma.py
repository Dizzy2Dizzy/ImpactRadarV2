"""
M&A scanner - monitors merger, acquisition, and strategic transactions.

Sources:
- SEC 8-K Item 2.01 (Completion of Acquisition or Disposition)
- SEC 8-K Item 8.01 (Other Events - often used for M&A announcements)
- SEC 8-K Item 1.01 (Entry into Material Agreement)
"""

import logging
from typing import List, Dict, Any, Optional

from releaseradar.services.sec import get_recent_filings, create_filing_title, get_8k_item_description
from scanners.utils import normalize_event

logger = logging.getLogger(__name__)


def scan_ma(tickers: List[str], companies: Optional[Dict[str, Dict]] = None, limit_per_ticker: int = 1) -> List[Dict[str, Any]]:
    """
    Scan for M&A and strategic transaction announcements.
    
    Args:
        tickers: List of ticker symbols to scan
        companies: Dictionary mapping ticker -> company info (name, sector)
        limit_per_ticker: Max events to return per ticker
        
    Returns:
        List of normalized event dicts
    """
    logger.info(f"M&A scanner starting for {len(tickers)} tickers")
    
    if companies is None:
        companies = {}
    
    events = []
    
    for ticker in tickers:
        try:
            company_info = companies.get(ticker, {})
            company_name = company_info.get('name', ticker)
            sector = company_info.get('sector', 'Unknown')
            
            # Fetch 8-K filings with M&A-related items from last 120 days
            filings = get_recent_filings(
                ticker=ticker,
                company_name=company_name,
                form_types=['8-K'],
                item_filters=['2.01', '8.01', '1.01'],
                limit=limit_per_ticker,
                days_back=120
            )
            
            logger.info(f"Found {len(filings)} M&A-related filings for {ticker}")
            
            for filing in filings:
                items = filing.get('items', [])
                
                # Create M&A-specific title
                if '2.01' in items:
                    title = f"M&A: {get_8k_item_description('2.01')}"
                elif '8.01' in items:
                    title = f"Strategic Event: {get_8k_item_description('8.01')}"
                elif '1.01' in items:
                    title = f"Material Agreement: {get_8k_item_description('1.01')}"
                else:
                    title = create_filing_title('8-K', filing.get('title') or '', items)
                
                event = normalize_event(
                    ticker=ticker,
                    company_name=company_name,
                    event_type='ma',
                    title=title,
                    date=filing['date'],
                    source='SEC EDGAR',
                    source_url=filing['url'],
                    description=filing.get('title', ''),
                    source_scanner='ma',
                    sector=sector
                )
                
                events.append(event)
        
        except Exception as e:
            logger.error(f"Error scanning M&A for {ticker}: {e}")
            continue
    
    logger.info(f"M&A scanner completed: {len(events)} events found")
    return events
