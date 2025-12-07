"""
Product launch scanner - monitors new product announcements.

Sources:
- Press releases with product launch keywords
- SEC 8-K filings with product-related announcements
"""

import logging
from typing import List, Dict, Any, Optional

from scanners.impl.press import scan_press, classify_press_release
from releaseradar.services.sec import get_recent_filings, create_filing_title
from scanners.utils import normalize_event

logger = logging.getLogger(__name__)

PRODUCT_KEYWORDS = [
    'launch', 'launches', 'launching',
    'introduces', 'introducing', 'introduced',
    'unveils', 'unveiling', 'unveiled',
    'announces new product', 'new product',
    'releases new', 'releasing',
    'debuts', 'debuting',
    'new version', 'product update'
]


def is_product_launch(title: str) -> bool:
    """Check if title indicates a product launch."""
    title_lower = title.lower()
    return any(keyword in title_lower for keyword in PRODUCT_KEYWORDS)


def scan_product_launch(tickers: List[str], companies: Optional[Dict[str, Dict]] = None, limit_per_ticker: int = 2) -> List[Dict[str, Any]]:
    """
    Scan for product launch announcements.
    
    Args:
        tickers: List of ticker symbols to scan
        companies: Dictionary mapping ticker -> company info (name, sector)
        limit_per_ticker: Max events to return per ticker
        
    Returns:
        List of normalized event dicts
    """
    logger.info(f"Product launch scanner starting for {len(tickers)} tickers")
    
    if companies is None:
        companies = {}
    
    product_launches = []
    ticker_counts = {ticker: 0 for ticker in tickers}
    
    # Method 1: Use press scanner to get press releases
    all_press_releases = scan_press(tickers, companies, limit_per_ticker=5)
    
    for event in all_press_releases:
        ticker = event.get('ticker')
        title = event.get('title', '')
        
        if not ticker:
            continue
        
        if ticker_counts.get(ticker, 0) >= limit_per_ticker:
            continue
        
        # Check if this is a product launch
        if is_product_launch(title):
            # Update event type to product_launch
            event['event_type'] = 'product_launch'
            event['source_scanner'] = 'product_launch'
            
            product_launches.append(event)
            ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
    
    # Method 2: Check SEC 8-K filings for product-related keywords (fallback)
    for ticker in tickers:
        if ticker_counts.get(ticker, 0) >= limit_per_ticker:
            continue
        
        try:
            company_info = companies.get(ticker, {})
            company_name = company_info.get('name', ticker)
            sector = company_info.get('sector', 'Unknown')
            
            # Fetch recent 8-K filings (no item filter)
            filings = get_recent_filings(
                ticker=ticker,
                company_name=company_name,
                form_types=['8-K'],
                item_filters=None,
                limit=10,
                days_back=60
            )
            
            # Note: SEC ATOM feeds often don't include detailed descriptions
            # If we find 8-Ks with product keywords, use them; otherwise use recent 8-Ks as candidates
            product_filings = []
            for filing in filings:
                filing_title = filing.get('title', '')
                description = filing.get('description', '')
                combined_text = (filing_title + ' ' + description).lower()
                
                if is_product_launch(combined_text):
                    product_filings.append(filing)
            
            # If no keyword matches, assume recent 8-Ks might be product-related
            # (SEC ATOM feeds don't include full text, so we can't perfectly filter)
            if not product_filings and filings:
                # Take the most recent 8-K as a potential product announcement
                product_filings = filings[:1]
            
            for filing in product_filings:
                if ticker_counts.get(ticker, 0) >= limit_per_ticker:
                    break
                
                title = f"Product/Service Announcement - 8-K Filing"
                
                event = normalize_event(
                    ticker=ticker,
                    company_name=company_name,
                    event_type='product_launch',
                    title=title,
                    date=filing['date'],
                    source='SEC EDGAR',
                    source_url=filing['url'],
                    description=filing.get('title', '8-K Current Report'),
                    source_scanner='product_launch',
                    sector=sector
                )
                
                product_launches.append(event)
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        
        except Exception as e:
            logger.error(f"Error scanning SEC filings for product launches for {ticker}: {e}")
            continue
    
    logger.info(f"Product launch scanner completed: {len(product_launches)} events found")
    return product_launches
