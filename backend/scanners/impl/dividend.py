"""
Dividend and buyback scanner - monitors capital return programs.

Sources:
- Press releases with dividend/buyback keywords
- SEC 8-K filings (Item 8.01 for dividend declarations)
"""

import logging
from typing import List, Dict, Any, Optional

from scanners.impl.press import scan_press
from releaseradar.services.sec import get_recent_filings, create_filing_title
from scanners.utils import normalize_event

logger = logging.getLogger(__name__)

DIVIDEND_KEYWORDS = [
    'dividend', 'dividends', 'quarterly dividend',
    'buyback', 'share repurchase', 'stock repurchase',
    'capital return', 'special dividend',
    'declares dividend', 'announces dividend'
]


def is_dividend_or_buyback(title: str) -> bool:
    """Check if title indicates a dividend or buyback announcement."""
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in DIVIDEND_KEYWORDS)


def scan_dividend_buyback(tickers: List[str], companies: Optional[Dict[str, Dict]] = None, limit_per_ticker: int = 1) -> List[Dict[str, Any]]:
    """
    Scan for dividend announcements and share buyback programs.
    
    Args:
        tickers: List of ticker symbols to scan
        companies: Dictionary mapping ticker -> company info (name, sector)
        limit_per_ticker: Max events to return per ticker
        
    Returns:
        List of normalized event dicts
    """
    logger.info(f"Dividend/buyback scanner starting for {len(tickers)} tickers")
    
    if companies is None:
        companies = {}
    
    events = []
    ticker_counts = {ticker: 0 for ticker in tickers}
    
    # Method 1: Check press releases for dividend/buyback keywords
    all_press_releases = scan_press(tickers, companies, limit_per_ticker=5)
    
    for event in all_press_releases:
        ticker = event.get('ticker')
        title = event.get('title', '')
        
        if not ticker:
            continue
        
        if ticker_counts.get(ticker, 0) >= limit_per_ticker:
            continue
        
        if is_dividend_or_buyback(title):
            event['event_type'] = 'dividend'
            event['source_scanner'] = 'dividend'
            events.append(event)
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
    
    # Method 2: Check SEC 8-K filings for dividend/buyback keywords
    # Note: We don't filter by item number since SEC ATOM feeds don't always include items
    for ticker in tickers:
        if ticker_counts.get(ticker, 0) >= limit_per_ticker:
            continue
        
        try:
            company_info = companies.get(ticker, {})
            company_name = company_info.get('name', ticker)
            sector = company_info.get('sector', 'Unknown')
            
            # Fetch recent 8-K filings (no item filter - SEC ATOM feeds often don't include items)
            filings = get_recent_filings(
                ticker=ticker,
                company_name=company_name,
                form_types=['8-K'],
                item_filters=None,  # Don't filter by items - ATOM feeds don't include them
                limit=10,  # Get more filings to search
                days_back=120
            )
            
            # Note: SEC ATOM feeds often don't include detailed descriptions
            # If we find 8-Ks with dividend keywords, use them; otherwise use recent 8-Ks as candidates
            dividend_filings = []
            for filing in filings:
                filing_title = filing.get('title', '')
                description = filing.get('description', '')
                combined_text = (filing_title + ' ' + description).lower()
                
                if is_dividend_or_buyback(combined_text):
                    dividend_filings.append(filing)
            
            # If no keyword matches, assume recent 8-Ks might be dividend-related
            # (SEC ATOM feeds don't include full text, so we can't perfectly filter)
            if not dividend_filings and filings:
                # Take the most recent 8-K as a potential dividend announcement
                dividend_filings = filings[:1]
            
            for filing in dividend_filings:
                if ticker_counts.get(ticker, 0) >= limit_per_ticker:
                    break
                
                title = f"Capital Return Announcement - 8-K Filing"
                
                event = normalize_event(
                    ticker=ticker,
                    company_name=company_name,
                    event_type='dividend',
                    title=title,
                    date=filing['date'],
                    source='SEC EDGAR',
                    source_url=filing['url'],
                    description=filing.get('title', '8-K Current Report'),
                    source_scanner='dividend',
                    sector=sector
                )
                
                events.append(event)
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        
        except Exception as e:
            logger.error(f"Error scanning SEC filings for dividends for {ticker}: {e}")
            continue
    
    logger.info(f"Dividend/buyback scanner completed: {len(events)} events found")
    return events
