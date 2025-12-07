"""
Company press releases scanner - production implementation.

Fetches recent press releases from company investor relations pages,
newsrooms, and PR distribution services.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

from tenacity import retry, stop_after_attempt, wait_exponential
import trafilatura
from bs4 import BeautifulSoup

from scanners.utils import normalize_event
from scanners.http_client import fetch_url, get_browser_headers

logger = logging.getLogger(__name__)

IR_URL_PATTERNS = {
    'generic': [
        'https://investor.{domain}/press-releases',
        'https://{domain}/newsroom',
        'https://{domain}/news',
        'https://{domain}/investors/press-releases',
        'https://ir.{domain}/news-releases'
    ]
}

COMMON_DOMAINS = {
    'AAPL': 'apple.com',
    'MRNA': 'modernatx.com',
    'TSLA': 'tesla.com',
    'MSFT': 'microsoft.com',
    'GOOGL': 'abc.xyz',
    'AMZN': 'amazon.com',
    'META': 'meta.com',
    'NVDA': 'nvidia.com'
}

# Direct newsroom URLs for known companies
# Note: We only scan companies with verified, accessible newsroom URLs
# Many company newsrooms use JavaScript rendering or authentication, so we limit to verified sources
DIRECT_NEWSROOM_URLS = {
    'AAPL': 'https://www.apple.com/newsroom/',
    'MRNA': 'https://investors.modernatx.com/news-releases',
    # Note: MSFT, TSLA and many others have newsrooms that require JavaScript or block scraping
    # For these, we rely on SEC filings instead
}


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=2, max=8))
def fetch_press_releases_from_url(url: str, company_name: str) -> List[Dict[str, Any]]:
    """Fetch press releases from a company IR/newsroom page."""
    try:
        response = fetch_url(url, headers=get_browser_headers(referer=url), timeout=20)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        press_releases = []
        
        # Try multiple selectors to find articles
        articles = soup.find_all(['article', 'div'], class_=re.compile(r'(press|news|release|article|tile)', re.I), limit=30)
        
        # If no articles found with class matching, try broader search
        if not articles:
            articles = soup.find_all(['article', 'div'], limit=30)
        
        for article in articles:
            # Try to find title in multiple ways
            title_elem = (
                article.find(['h2', 'h3', 'h4'], class_=re.compile(r'title|headline', re.I)) or
                article.find(['h2', 'h3', 'h4']) or
                article.find('a', class_=re.compile(r'title|headline', re.I)) or
                article.find('a')
            )
            
            if not title_elem:
                continue
            
            title = title_elem.get_text(strip=True)
            if not title or len(title) < 10:
                continue
            
            # Find link
            link = ''
            if title_elem.name == 'a':
                link = str(title_elem.get('href', ''))
            else:
                a_tag = article.find('a')
                if a_tag:
                    link = str(a_tag.get('href', ''))
            
            if link and not link.startswith('http'):
                link = urljoin(url, link)
            
            # Find date
            date_elem = article.find(['time', 'span'], class_=re.compile(r'date|time', re.I))
            date_str = None
            
            if date_elem:
                date_str = date_elem.get('datetime') or date_elem.get_text(strip=True)
            
            release_date = None
            if date_str and isinstance(date_str, str):
                try:
                    from dateutil import parser
                    release_date = parser.parse(str(date_str))
                    if release_date.tzinfo is None:
                        release_date = release_date.replace(tzinfo=timezone.utc)
                except:
                    pass
            
            # If no date found, use recent date (assume within last 7 days)
            if not release_date:
                release_date = datetime.now(timezone.utc) - timedelta(days=3)
            
            # Filter by date (30 days)
            if (datetime.now(timezone.utc) - release_date).days > 30:
                continue
            
            press_releases.append({
                'title': title,
                'url': link if link else url,
                'date': release_date
            })
        
        return press_releases[:5]
    
    except Exception as e:
        logger.warning(f"Failed to fetch press releases from {url}: {e}")
        return []


def get_company_domain(ticker: str, company_name: str) -> Optional[str]:
    """Get company domain from ticker or company name."""
    if ticker in COMMON_DOMAINS:
        return COMMON_DOMAINS[ticker]
    
    company_lower = company_name.lower()
    
    if 'inc' in company_lower or 'corp' in company_lower:
        base_name = company_lower.split()[0]
        return f"{base_name}.com"
    
    return None


def classify_press_release(title: str) -> str:
    """Classify press release type based on title."""
    title_lower = title.lower()
    
    if any(word in title_lower for word in ['launch', 'introduces', 'unveils', 'announces new product']):
        return 'product_launch'
    elif any(word in title_lower for word in ['partnership', 'collaboration', 'agreement']):
        return 'press_release'
    elif any(word in title_lower for word in ['acquisition', 'acquires', 'merger']):
        return 'merger_acquisition'
    elif any(word in title_lower for word in ['executive', 'ceo', 'cfo', 'appoints', 'promotes']):
        return 'executive_change'
    else:
        return 'press_release'


def scan_press(tickers: List[str], companies: Optional[Dict[str, Dict]] = None, limit_per_ticker: int = 3) -> List[Dict[str, Any]]:
    """
    Scan company press releases and newsrooms.
    
    Args:
        tickers: List of ticker symbols to scan
        companies: Dictionary mapping ticker -> company info (name, sector)
        limit_per_ticker: Maximum releases to fetch per ticker
        
    Returns:
        List of normalized event dictionaries
    """
    logger.info(f"Press releases scanner starting for {len(tickers)} tickers")
    
    if companies is None:
        companies = {}
    
    events = []
    
    for ticker in tickers:
        company_info = companies.get(ticker, {})
        company_name = company_info.get('name', ticker)
        sector = company_info.get('sector')
        
        try:
            press_releases = []
            
            # Only try direct newsroom URLs if we have them
            if ticker in DIRECT_NEWSROOM_URLS:
                url = DIRECT_NEWSROOM_URLS[ticker]
                
                try:
                    releases = fetch_press_releases_from_url(url, company_name)
                    if releases:
                        press_releases.extend(releases)
                        logger.info(f"Found {len(releases)} press releases for {ticker} at {url}")
                except Exception as url_error:
                    logger.debug(f"Failed to fetch from {url}: {url_error}")
            
            # If we didn't find any press releases, that's OK - not all companies have accessible newsrooms
            if not press_releases:
                logger.debug(f"No press releases found for {ticker} (no verified newsroom URL)")
                continue
            
            for release in press_releases[:limit_per_ticker]:
                event_type = classify_press_release(release['title'])
                
                event = normalize_event(
                    ticker=ticker,
                    company_name=company_name,
                    event_type=event_type,
                    title=release['title'],
                    date=release['date'],
                    source='Company Press Release',
                    source_url=release['url'],
                    description='',
                    source_scanner='press',
                    sector=sector if sector else 'Unknown'
                )
                
                events.append(event)
        
        except Exception as e:
            logger.error(f"Error scanning press releases for {ticker}: {e}")
            continue
    
    logger.info(f"Press releases scanner completed: {len(events)} events found")
    return events
