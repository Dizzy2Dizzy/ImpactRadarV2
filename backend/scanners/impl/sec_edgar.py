"""
SEC EDGAR scanner - production implementation.

Fetches recent SEC filings (8-K, 10-K, 10-Q, S-1, 13D/G) from SEC EDGAR
RSS feeds and company-specific filings.
"""

import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential

from scanners.utils import normalize_event
from scanners.http_client import fetch_sec_url, get_sec_headers
from releaseradar.services.cik_mapping import get_cik_for_ticker

logger = logging.getLogger(__name__)

FILING_TYPES = {
    '8-K': 'sec_8k',
    '10-K': 'sec_10k',
    '10-Q': 'sec_10q',
    'S-1': 'sec_s1',
    '13D': 'sec_13d',
    '13G': 'sec_13g',
    'DEF 14A': 'sec_def14a'
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_company_filings(ticker: str, company_name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """Fetch recent filings for a company from SEC EDGAR."""
    cik = get_cik_for_ticker(ticker)
    if not cik:
        logger.warning(f"No CIK found for ticker {ticker}, skipping SEC EDGAR fetch")
        return []
    
    logger.debug(f"Fetching SEC EDGAR filings for {ticker} (CIK: {cik})")
    
    try:
        search_url = f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={cik}&type=&dateb=&owner=exclude&count={limit}&output=atom"
        
        response = fetch_sec_url(search_url, timeout=20)
        response.raise_for_status()
        
        filings = []
        try:
            root = ET.fromstring(response.content)
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            
            for entry in root.findall('.//atom:entry', ns):
                filing_type_elem = entry.find('.//atom:category', ns)
                title_elem = entry.find('.//atom:title', ns)
                updated_elem = entry.find('.//atom:updated', ns)
                link_elem = entry.find('.//atom:link[@rel="alternate"]', ns)
                
                if filing_type_elem is None or title_elem is None:
                    continue
                
                filing_type = filing_type_elem.get('term', '').strip()
                title = title_elem.text.strip() if title_elem.text else ''
                updated = updated_elem.text if updated_elem is not None and updated_elem.text else None
                link = link_elem.get('href', '') if link_elem is not None else ''
                
                if filing_type not in FILING_TYPES and filing_type.replace('-', ' ').strip() not in FILING_TYPES:
                    continue
                
                filing_date = None
                if updated:
                    try:
                        filing_date = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                    except:
                        filing_date = datetime.now(timezone.utc)
                else:
                    filing_date = datetime.now(timezone.utc)
                
                if (datetime.now(timezone.utc) - filing_date).days > 30:
                    continue
                
                filings.append({
                    'filing_type': filing_type,
                    'title': title,
                    'date': filing_date,
                    'url': link
                })
        
        except ET.ParseError as e:
            logger.warning(f"Failed to parse SEC EDGAR XML for {ticker}: {e}")
            return []
        
        return filings[:limit]
    
    except Exception as e:
        logger.warning(f"Failed to fetch SEC filings for {ticker}: {e}")
        return []


def extract_8k_items(raw_title: str) -> List[str]:
    """Extract 8-K item numbers from filing title.
    
    Args:
        raw_title: Raw filing title from SEC EDGAR
        
    Returns:
        List of item numbers (e.g., ['2.02', '5.02'])
    """
    if not raw_title:
        return []
    
    item_pattern = re.compile(r'Item\s+(\d+\.\d+)', re.IGNORECASE)
    matches = item_pattern.findall(raw_title)
    return list(set(matches))


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=6))
def fetch_8k_items_from_document(filing_url: str) -> List[str]:
    """Fetch full 8-K filing document and extract Item numbers.
    
    Since SEC EDGAR RSS feeds don't include Item numbers in titles,
    we need to fetch the actual filing document and parse it.
    
    Args:
        filing_url: URL to the 8-K filing index page
        
    Returns:
        List of item numbers found in the filing (e.g., ['2.02', '5.02'])
    """
    if not filing_url:
        return []
    
    try:
        response = fetch_sec_url(filing_url, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Find the primary document link (usually .htm or .html file)
        # Look for the table that lists documents
        doc_table = soup.find('table', class_='tableFile')
        if not doc_table:
            logger.debug(f"No document table found in {filing_url}")
            return []
        
        # Find the first .htm or .html document (usually the primary 8-K filing)
        primary_doc_link = None
        for row in doc_table.find_all('tr')[1:]:  # Skip header row
            cols = row.find_all('td')
            if len(cols) >= 3:
                doc_type = cols[3].get_text(strip=True) if len(cols) > 3 else ''
                # Look for 8-K document (not exhibits)
                if '8-K' in doc_type or cols[0].get_text(strip=True) == '1':
                    link = cols[2].find('a')
                    if link and link.get('href'):
                        href = link.get('href')
                        if isinstance(href, str):
                            # Handle both direct links and inline XBRL viewer links (/ix?doc=...)
                            if href.startswith('/ix?doc='):
                                # Extract the actual document path from XBRL viewer
                                doc_path = href.replace('/ix?doc=', '')
                                primary_doc_link = f"https://www.sec.gov{doc_path}"
                                break
                            elif href.endswith('.htm') or href.endswith('.html'):
                                primary_doc_link = f"https://www.sec.gov{href}"
                                break
        
        if not primary_doc_link:
            logger.debug(f"No primary document link found in {filing_url}")
            return []
        
        logger.debug(f"Fetching 8-K document: {primary_doc_link}")
        doc_response = fetch_sec_url(primary_doc_link, timeout=15)
        doc_response.raise_for_status()
        
        # Parse the document content to extract Item numbers
        doc_soup = BeautifulSoup(doc_response.content, 'html.parser')
        doc_text = doc_soup.get_text()
        
        # Extract all Item numbers using regex
        # Pattern matches "Item 1.01", "Item 2.02", "Item  1.01" (with spaces), etc.
        item_pattern = re.compile(r'Item\s+(\d+\.\d{2})', re.IGNORECASE)
        matches = item_pattern.findall(doc_text)
        
        # Remove duplicates and sort
        unique_items = sorted(list(set(matches)), key=lambda x: float(x))
        
        if unique_items:
            logger.info(f"Extracted 8-K items from document: {unique_items}")
        else:
            logger.debug(f"No Item numbers found in {primary_doc_link}")
        
        return unique_items
        
    except Exception as e:
        logger.warning(f"Failed to fetch/parse 8-K document from {filing_url}: {e}")
        return []


def extract_filing_title(filing_type: str, raw_title: str, items: Optional[List[str]] = None) -> str:
    """Extract meaningful title from SEC filing.
    
    Args:
        filing_type: Type of SEC filing (8-K, 10-K, etc.)
        raw_title: Raw filing title from SEC EDGAR
        items: Optional list of 8-K item numbers (e.g., ['2.02', '5.02'])
        
    Returns:
        Human-readable title for the filing
    """
    title_map = {
        '8-K': 'Material Event Disclosure',
        '10-K': 'Annual Report',
        '10-Q': 'Quarterly Report',
        'S-1': 'IPO Registration Statement',
        '13D': 'Beneficial Ownership Report (13D)',
        '13G': 'Beneficial Ownership Report (13G)',
        'DEF 14A': 'Proxy Statement'
    }
    
    base_title = title_map.get(filing_type, filing_type)
    
    # For 8-K filings, use item-specific descriptions
    if filing_type == '8-K':
        # Use provided items list, or try extracting from title
        if not items:
            items = extract_8k_items(raw_title)
        
        if items:
            item_num = items[0]  # Use the first/primary item
            item_descriptions = {
                '1.01': 'Entry into Material Agreement',
                '1.02': 'Termination of Material Agreement',
                '2.01': 'Completion of Acquisition or Disposition',
                '2.02': 'Results of Operations and Financial Condition',
                '2.03': 'Creation of Direct Financial Obligation',
                '2.06': 'Material Impairment',
                '3.01': 'Notice of Delisting',
                '4.02': 'Non-Reliance on Previous Financial Statements',
                '5.01': 'Changes in Control',
                '5.02': 'Departure/Election of Directors or Officers',
                '5.03': 'Amendments to Articles or Bylaws',
                '5.07': 'Submission of Matters to a Vote',
                '7.01': 'Regulation FD Disclosure',
                '8.01': 'Other Events'
            }
            if item_num in item_descriptions:
                return f"{item_descriptions[item_num]} (8-K)"
    
    return f"{base_title} ({filing_type})"


def _scan_single_ticker(args: tuple) -> List[Dict[str, Any]]:
    """Process a single ticker - helper for parallel execution."""
    import random
    
    ticker, company_info, limit_per_ticker = args
    company_name = company_info.get('name', ticker)
    sector = company_info.get('sector')
    events = []
    
    delay = random.uniform(0.5, 2.0)
    time.sleep(delay)
    
    try:
        filings = fetch_company_filings(ticker, company_name, limit=limit_per_ticker)
        if filings:
            logger.info(f"Found {len(filings)} SEC filings for {ticker}")
        
        for filing in filings:
            filing_type = filing['filing_type']
            event_type = FILING_TYPES.get(filing_type, 'sec_filing')
            raw_title = filing.get('title', '')
            filing_url = filing.get('url', '')
            
            metadata = {}
            items = []
            
            if filing_type == '8-K' and filing_url:
                items = extract_8k_items(raw_title)
                if not items:
                    items = fetch_8k_items_from_document(filing_url)
                if items:
                    metadata['8k_items'] = items
                    logger.info(f"8-K items for {ticker}: {items}")
            
            title = extract_filing_title(filing_type, raw_title, items)
            
            event = normalize_event(
                ticker=ticker,
                company_name=company_name,
                event_type=event_type,
                title=title,
                date=filing['date'],
                source='SEC EDGAR',
                source_url=filing_url,
                description=raw_title,
                source_scanner='sec_edgar',
                sector=sector if sector else 'Unknown',
                metadata=metadata
            )
            events.append(event)
    
    except Exception as e:
        logger.debug(f"Error scanning SEC filings for {ticker}: {e}")
    
    return events


def scan_sec_edgar(tickers: List[str], companies: Optional[Dict[str, Dict]] = None, limit_per_ticker: int = 5) -> List[Dict[str, Any]]:
    """
    Scan SEC EDGAR for recent filings using parallel processing with rate limiting.
    
    Uses ThreadPoolExecutor with controlled parallelism and batch delays to
    stay within SEC rate limits (10 requests/second max).
    
    Args:
        tickers: List of ticker symbols to scan
        companies: Dictionary mapping ticker -> company info (name, sector)
        limit_per_ticker: Maximum filings to fetch per ticker
        
    Returns:
        List of normalized event dictionaries
    """
    import time
    from concurrent.futures import ThreadPoolExecutor, as_completed
    from releaseradar.services.cik_mapping import _ensure_cache_loaded
    
    logger.info(f"SEC EDGAR scanner starting for {len(tickers)} tickers (parallel mode)")
    
    _ensure_cache_loaded()
    logger.info("CIK cache pre-loaded for parallel processing")
    
    if companies is None:
        companies = {}
    
    all_events = []
    
    args_list = [
        (ticker, companies.get(ticker, {'name': ticker}), limit_per_ticker)
        for ticker in tickers
    ]
    
    max_workers = min(3, len(tickers))
    batch_size = 50
    batch_delay = 10.0
    
    for batch_start in range(0, len(args_list), batch_size):
        batch = args_list[batch_start:batch_start + batch_size]
        batch_num = batch_start // batch_size + 1
        total_batches = (len(args_list) + batch_size - 1) // batch_size
        
        logger.info(f"SEC EDGAR batch {batch_num}/{total_batches}: processing {len(batch)} tickers")
        
        with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="sec-edgar-") as executor:
            futures = {executor.submit(_scan_single_ticker, args): args[0] for args in batch}
            
            for future in as_completed(futures):
                ticker = futures[future]
                try:
                    events = future.result(timeout=60)
                    if events:
                        all_events.extend(events)
                except Exception as e:
                    logger.debug(f"Error processing {ticker}: {e}")
        
        if batch_start + batch_size < len(args_list):
            logger.info(f"SEC EDGAR: pausing {batch_delay}s between batches to respect rate limits")
            time.sleep(batch_delay)
    
    logger.info(f"SEC EDGAR scanner completed: {len(all_events)} events found from {len(tickers)} tickers")
    return all_events
