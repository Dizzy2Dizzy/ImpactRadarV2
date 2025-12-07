"""
Guidance updates scanner - monitors company financial guidance changes.

Sources:
- SEC 8-K Item 7.01 (Regulation FD Disclosure)
- SEC 8-K Item 2.02 (for guidance in earnings releases)
"""

import logging
from typing import List, Dict, Any, Optional

from releaseradar.services.sec import get_recent_filings, create_filing_title, get_8k_item_description
from scanners.utils import normalize_event

logger = logging.getLogger(__name__)


def scan_guidance(tickers: List[str], companies: Optional[Dict[str, Dict]] = None, limit_per_ticker: int = 2) -> List[Dict[str, Any]]:
    """
    Scan for company guidance updates and revisions.
    
    Args:
        tickers: List of ticker symbols to scan
        companies: Dictionary mapping ticker -> company info (name, sector)
        limit_per_ticker: Max events to return per ticker
        
    Returns:
        List of normalized event dicts
    """
    logger.info(f"Guidance scanner starting for {len(tickers)} tickers")
    
    if companies is None:
        companies = {}
    
    events = []
    
    for ticker in tickers:
        try:
            company_info = companies.get(ticker, {})
            company_name = company_info.get('name', ticker)
            sector = company_info.get('sector', 'Unknown')
            
            # Fetch 8-K filings with Item 7.01 (Regulation FD) - often used for guidance
            filings = get_recent_filings(
                ticker=ticker,
                company_name=company_name,
                form_types=['8-K'],
                item_filters=['7.01', '2.02'],
                limit=limit_per_ticker,
                days_back=120
            )
            
            logger.info(f"Found {len(filings)} guidance-related filings for {ticker}")
            
            for filing in filings:
                items = filing.get('items', [])
                
                # Create guidance-specific title
                if '7.01' in items:
                    title = f"Guidance Update: {get_8k_item_description('7.01')}"
                elif '2.02' in items:
                    title = f"Guidance in Earnings: {get_8k_item_description('2.02')}"
                else:
                    title = create_filing_title('8-K', filing.get('title') or '', items)
                
                event = normalize_event(
                    ticker=ticker,
                    company_name=company_name,
                    event_type='guidance',
                    title=title,
                    date=filing['date'],
                    source='SEC EDGAR',
                    source_url=filing['url'],
                    description=filing.get('title', ''),
                    source_scanner='guidance',
                    sector=sector
                )
                
                events.append(event)
        
        except Exception as e:
            logger.error(f"Error scanning guidance for {ticker}: {e}")
            continue
    
    logger.info(f"Guidance scanner completed: {len(events)} events found")
    return events
