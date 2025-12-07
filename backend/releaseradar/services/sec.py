"""
Shared SEC EDGAR service for Impact Radar.

Provides centralized SEC filing fetching, filtering, and parsing utilities
for use across multiple scanners (sec_8k, sec_10q, earnings, ma, guidance).
"""

import logging
import re
import time
import threading
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional, Set
from xml.etree import ElementTree as ET

import requests
from bs4 import BeautifulSoup
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from releaseradar.services.cik_mapping import get_cik_for_ticker

logger = logging.getLogger(__name__)


class SECRateLimiter:
    """
    Rate limiter for SEC EDGAR API requests.
    
    SEC EDGAR enforces a limit of 10 requests per second.
    This class ensures we never exceed that limit.
    """
    
    def __init__(self, requests_per_second: float = 10.0):
        self.requests_per_second = requests_per_second
        self.min_interval = 1.0 / requests_per_second
        self.last_request_time = 0
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if necessary to respect rate limit."""
        with self.lock:
            current_time = time.time()
            time_since_last_request = current_time - self.last_request_time
            
            if time_since_last_request < self.min_interval:
                sleep_time = self.min_interval - time_since_last_request
                logger.debug(f"Rate limiting: sleeping for {sleep_time:.3f}s")
                time.sleep(sleep_time)
            
            self.last_request_time = time.time()


sec_rate_limiter = SECRateLimiter(requests_per_second=10.0)


class SEC403Error(Exception):
    """Raised when SEC returns 403 (rate limit exceeded)."""
    pass

SEC_HEADERS = {
    'User-Agent': 'Impact Radar Scanner contact@impactradar.com',
    'Accept-Encoding': 'gzip, deflate',
    'Host': 'www.sec.gov'
}

# 8-K Item descriptions for enhanced classification
ITEM_8K_DESCRIPTIONS = {
    '1.01': 'Entry into Material Agreement',
    '1.02': 'Termination of Material Agreement',
    '1.03': 'Bankruptcy or Receivership',
    '2.01': 'Completion of Acquisition or Disposition',
    '2.02': 'Results of Operations and Financial Condition',
    '2.03': 'Creation of Direct Financial Obligation',
    '2.04': 'Triggering Events That Accelerate or Increase a Direct Financial Obligation',
    '2.05': 'Costs Associated with Exit or Disposal Activities',
    '2.06': 'Material Impairments',
    '3.01': 'Notice of Delisting or Failure to Satisfy a Continued Listing Rule',
    '3.02': 'Unregistered Sales of Equity Securities',
    '3.03': 'Material Modification to Rights of Security Holders',
    '4.01': 'Changes in Registrant\'s Certifying Accountant',
    '4.02': 'Non-Reliance on Previously Issued Financial Statements',
    '5.01': 'Changes in Control of Registrant',
    '5.02': 'Departure/Election of Directors or Officers',
    '5.03': 'Amendments to Articles of Incorporation or Bylaws',
    '5.04': 'Temporary Suspension of Trading Under Registrant\'s Employee Benefit Plans',
    '5.05': 'Amendment to Registrant\'s Code of Ethics',
    '5.07': 'Submission of Matters to a Vote of Security Holders',
    '7.01': 'Regulation FD Disclosure',
    '8.01': 'Other Events',
    '9.01': 'Financial Statements and Exhibits'
}


@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    retry=retry_if_exception_type(SEC403Error)
)
def fetch_company_filings(
    ticker: str,
    company_name: str = None,
    filing_types: Optional[List[str]] = None,
    limit: int = 20,
    days_back: int = 30
) -> List[Dict[str, Any]]:
    """
    Fetch recent SEC filings for a company.
    
    Args:
        ticker: Company ticker symbol
        company_name: Company name (optional)
        filing_types: List of filing types to filter (e.g., ['8-K', '10-Q'])
        limit: Maximum number of filings to fetch
        days_back: Only return filings from last N days
        
    Returns:
        List of filing dictionaries with keys:
            - filing_type: Filing form type (e.g., '8-K')
            - title: Filing title
            - date: Filing date (datetime)
            - url: URL to filing
            - items: List of 8-K items (for 8-K filings)
    """
    # Convert ticker to CIK (SEC EDGAR requires CIK, not ticker symbols)
    cik = get_cik_for_ticker(ticker)
    if not cik:
        logger.warning(f"No CIK found for ticker {ticker}, skipping SEC filing fetch")
        return []
    
    logger.debug(f"Fetching SEC filings for {ticker} (CIK: {cik})")
    
    try:
        # Apply rate limiting before making request
        sec_rate_limiter.wait_if_needed()
        
        search_url = "https://www.sec.gov/cgi-bin/browse-edgar"
        params = {
            'action': 'getcompany',
            'CIK': cik,
            'type': '',
            'dateb': '',
            'owner': 'exclude',
            'count': limit,
            'output': 'atom'
        }
        
        response = requests.get(search_url, params=params, headers=SEC_HEADERS, timeout=15)
        
        # Handle 403 errors specifically (rate limiting)
        if response.status_code == 403:
            logger.warning(f"SEC 403 error for {ticker}, rate limit exceeded - will retry with backoff")
            raise SEC403Error(f"SEC rate limit exceeded for {ticker}")
        
        response.raise_for_status()
        
        filings = []
        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom'}
        
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        
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
            
            # Filter by filing type if specified
            if filing_types and filing_type not in filing_types:
                continue
            
            # Parse filing date
            filing_date = None
            if updated:
                try:
                    filing_date = datetime.fromisoformat(updated.replace('Z', '+00:00'))
                except:
                    filing_date = datetime.now(timezone.utc)
            else:
                filing_date = datetime.now(timezone.utc)
            
            # Filter by date
            if filing_date < cutoff_date:
                continue
            
            # Extract 8-K items if applicable
            items = []
            if filing_type == '8-K':
                # Try to extract items from title first (fast)
                items = extract_8k_items(title)
                
                # If no items found in title, fetch from the full document (slower but accurate)
                if not items and link:
                    logger.debug(f"No items in title for {ticker} 8-K, fetching full document...")
                    items = fetch_8k_items_from_document(link)
            
            filings.append({
                'filing_type': filing_type,
                'title': title,
                'date': filing_date,
                'url': link,
                'items': items
            })
        
        return filings[:limit]
    
    except ET.ParseError as e:
        logger.warning(f"Failed to parse SEC EDGAR XML for {ticker}: {e}")
        return []
    except requests.exceptions.RequestException as e:
        logger.warning(f"Failed to fetch SEC filings for {ticker}: {e}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching SEC filings for {ticker}: {e}")
        return []


def extract_8k_items(title: str) -> List[str]:
    """
    Extract 8-K item numbers from filing title.
    
    Args:
        title: Filing title (e.g., "8-K - Item 2.02, Item 5.02")
        
    Returns:
        List of item numbers (e.g., ['2.02', '5.02'])
    """
    items = []
    
    # Pattern: "Item X.XX" or "Items X.XX, Y.YY"
    item_matches = re.findall(r'Item\s+(\d+\.\d+)', title, re.IGNORECASE)
    items.extend(item_matches)
    
    return list(set(items))  # Remove duplicates


def fetch_8k_items_from_document(filing_url: str) -> List[str]:
    """
    Fetch 8-K filing and extract Item numbers from the content.
    
    This function:
    1. Fetches the filing index page (which usually contains Item info)
    2. Extracts Item numbers from the index page text
    3. If no items found, tries fetching the primary document
    
    Args:
        filing_url: URL to the 8-K filing (index page)
        
    Returns:
        List of item numbers found (e.g., ['2.02', '5.02'])
    """
    items = []
    
    try:
        # Apply rate limiting before making request
        sec_rate_limiter.wait_if_needed()
        
        # Fetch the filing index page
        response = requests.get(filing_url, headers=SEC_HEADERS, timeout=10)
        
        if response.status_code == 403:
            logger.warning(f"SEC 403 error fetching document items, skipping")
            return []
        
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract Item numbers from the index page text
        # Most modern SEC filings include Items in the index page itself
        index_text = soup.get_text()
        item_matches = re.findall(r'Item\s+(\d+\.\d+)', index_text, re.IGNORECASE)
        
        if item_matches:
            items = sorted(list(set(item_matches)))
            logger.debug(f"Extracted {len(items)} items from index page: {items}")
            return items
        
        # If no items found on index page, try fetching the primary document
        # This is slower but may be necessary for older filings
        doc_url = None
        
        # Look for the primary 8-K document link
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 4:
                doc_type = cells[3].get_text(strip=True)
                if '8-K' in doc_type:
                    link = cells[2].find('a')
                    if link and link.get('href'):
                        doc_url = 'https://www.sec.gov' + link['href']
                        break
        
        if not doc_url:
            # Try alternative method - look for .htm files
            for link in soup.find_all('a', href=True):
                href = link['href']
                if href.endswith('.htm') and not 'index.htm' in href.lower():
                    doc_url = 'https://www.sec.gov' + href if not href.startswith('http') else href
                    break
        
        if not doc_url:
            logger.debug(f"Could not find primary document URL for {filing_url}")
            return []
        
        # Fetch the actual 8-K document
        logger.debug(f"No items on index page, fetching primary document...")
        sec_rate_limiter.wait_if_needed()
        doc_response = requests.get(doc_url, headers=SEC_HEADERS, timeout=10)
        
        if doc_response.status_code == 403:
            logger.warning(f"SEC 403 error fetching primary document, skipping")
            return []
        
        doc_response.raise_for_status()
        
        doc_soup = BeautifulSoup(doc_response.content, 'html.parser')
        doc_text = doc_soup.get_text()
        
        # Extract Item numbers from document text
        item_matches = re.findall(r'Item\s+(\d+\.\d+)', doc_text, re.IGNORECASE)
        items = sorted(list(set(item_matches)))
        
        if items:
            logger.debug(f"Extracted {len(items)} items from primary document: {items}")
        else:
            logger.debug(f"No items found in primary document at {doc_url}")
        
        return items
    
    except requests.exceptions.RequestException as e:
        logger.debug(f"Failed to fetch 8-K document from {filing_url}: {e}")
        return []
    except Exception as e:
        logger.debug(f"Error parsing 8-K document from {filing_url}: {e}")
        return []


def get_recent_filings(
    ticker: str,
    company_name: str = None,
    form_types: Optional[List[str]] = None,
    item_filters: Optional[List[str]] = None,
    limit: int = 10,
    days_back: int = 30
) -> List[Dict[str, Any]]:
    """
    Get recent SEC filings with optional filtering.
    
    Args:
        ticker: Company ticker symbol
        company_name: Company name (optional)
        form_types: Filter by filing types (e.g., ['8-K', '10-Q'])
        item_filters: Filter 8-K filings by item numbers (e.g., ['2.02', '7.01'])
                      NOTE: Item filtering is best-effort since SEC ATOM feeds don't
                      always include item details. If no items found, returns all filings.
        limit: Maximum number of filings to return
        days_back: Only return filings from last N days
        
    Returns:
        List of filing dictionaries
    """
    filings = fetch_company_filings(
        ticker=ticker,
        company_name=company_name,
        filing_types=form_types,
        limit=limit * 2,  # Fetch more to account for filtering
        days_back=days_back
    )
    
    # Apply item filters for 8-K filings (best effort)
    # Note: SEC ATOM feeds often don't include item numbers, so we return
    # all filings if no items are found
    if item_filters:
        filtered_filings = []
        has_any_items = False
        
        for filing in filings:
            if filing['filing_type'] == '8-K':
                items = filing.get('items', [])
                if items:
                    has_any_items = True
                    # Check if any of the filing's items match our filters
                    if any(item in item_filters for item in items):
                        filtered_filings.append(filing)
                else:
                    # No items extracted, add to filtered list (we can't filter)
                    filtered_filings.append(filing)
            else:
                # Non-8K filings pass through
                filtered_filings.append(filing)
        
        # If we found no items in any filing, return all filings (filtering not possible)
        if not has_any_items and form_types == ['8-K']:
            logger.debug(f"No 8-K items found for {ticker}, returning all 8-K filings")
            return filings[:limit]
        
        return filtered_filings[:limit]
    
    return filings[:limit]


def get_8k_item_description(item_number: str) -> str:
    """
    Get human-readable description for 8-K item number.
    
    Args:
        item_number: Item number (e.g., '2.02')
        
    Returns:
        Description string
    """
    return ITEM_8K_DESCRIPTIONS.get(item_number, f'Item {item_number}')


def create_filing_title(filing_type: str, raw_title: str = None, items: List[str] = None) -> str:
    """
    Create a human-readable title for a SEC filing.
    
    Args:
        filing_type: Filing form type (e.g., '8-K', '10-Q')
        raw_title: Raw filing title
        items: List of 8-K item numbers
        
    Returns:
        Formatted title
    """
    base_titles = {
        '8-K': 'Material Event Disclosure',
        '10-K': 'Annual Report',
        '10-Q': 'Quarterly Report',
        'S-1': 'IPO Registration Statement',
        '13D': 'Beneficial Ownership Report',
        '13G': 'Beneficial Ownership Report',
        'DEF 14A': 'Proxy Statement'
    }
    
    base_title = base_titles.get(filing_type, filing_type)
    
    # For 8-K filings, add item descriptions
    if filing_type == '8-K' and items:
        # Use the most significant item
        primary_item = items[0] if items else None
        if primary_item:
            item_desc = get_8k_item_description(primary_item)
            return f"{item_desc} (8-K)"
    
    return f"{base_title} ({filing_type})"


def classify_8k_event_type(items: List[str]) -> str:
    """
    Classify 8-K filing into specific event type based on items.
    
    Args:
        items: List of 8-K item numbers
        
    Returns:
        Event type string (e.g., 'earnings', 'ma', 'guidance')
    """
    if not items:
        return 'sec_8k'
    
    # Earnings-related items
    if '2.02' in items:
        return 'earnings'
    
    # M&A-related items
    if '2.01' in items or '8.01' in items:
        return 'ma'
    
    # Guidance-related items
    if '7.01' in items:
        return 'guidance'
    
    # Leadership changes
    if '5.02' in items:
        return 'sec_8k'
    
    # Default to generic 8-K
    return 'sec_8k'
