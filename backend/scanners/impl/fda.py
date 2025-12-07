"""
FDA scanner - production implementation.

Fetches recent FDA announcements including approvals, rejections, safety alerts,
and PDUFA dates from FDA.gov RSS feeds and press announcements.
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from xml.etree import ElementTree as ET

from tenacity import retry, stop_after_attempt, wait_exponential
import trafilatura

from scanners.utils import normalize_event
from scanners.http_client import fetch_fda_url, get_fda_headers

logger = logging.getLogger(__name__)

FDA_RSS_FEEDS = {
    'press_releases': 'https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/press-releases/rss.xml',
    'recalls': 'https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/recalls/rss.xml',
    'drugs': 'https://www.fda.gov/about-fda/contact-fda/stay-informed/rss-feeds/drugs/rss.xml'
}


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def fetch_fda_rss_feed(feed_url: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch and parse FDA RSS feed."""
    try:
        response = fetch_fda_url(feed_url, timeout=20)
        response.raise_for_status()
        
        root = ET.fromstring(response.content)
        items = []
        
        for item in root.findall('.//item')[:limit]:
            title_elem = item.find('title')
            link_elem = item.find('link')
            pub_date_elem = item.find('pubDate')
            description_elem = item.find('description')
            
            if title_elem is None or title_elem.text is None:
                continue
            
            title = title_elem.text.strip()
            link = link_elem.text.strip() if link_elem is not None and link_elem.text else ''
            pub_date = pub_date_elem.text if pub_date_elem is not None and pub_date_elem.text else None
            description = description_elem.text if description_elem is not None and description_elem.text else ''
            
            announcement_date = None
            if pub_date:
                try:
                    from email.utils import parsedate_to_datetime
                    announcement_date = parsedate_to_datetime(pub_date)
                except:
                    announcement_date = datetime.now(timezone.utc)
            else:
                announcement_date = datetime.now(timezone.utc)
            
            if (datetime.now(timezone.utc) - announcement_date).days > 30:
                continue
            
            items.append({
                'title': title,
                'url': link,
                'date': announcement_date,
                'description': description
            })
        
        return items
    
    except Exception as e:
        logger.warning(f"Failed to fetch FDA RSS feed {feed_url}: {e}")
        return []


def extract_company_from_fda_announcement(title: str, description: str, tracked_tickers: List[str], companies: Dict[str, Dict]) -> Optional[tuple]:
    """
    Extract company ticker from FDA announcement.
    
    Returns: (ticker, company_name) or None
    """
    title_lower = title.lower()
    description_lower = description.lower() if description else ''
    combined_text = f"{title_lower} {description_lower}"
    
    for ticker in tracked_tickers:
        company_info = companies.get(ticker, {})
        company_name = company_info.get('name', ticker)
        
        company_name_lower = company_name.lower()
        ticker_lower = ticker.lower()
        
        if company_name_lower in combined_text or ticker_lower in combined_text:
            return (ticker, company_name)
        
        company_variations = [
            company_name.split()[0].lower(),
            company_name.replace(',', '').replace('.', '').lower()
        ]
        
        for variation in company_variations:
            if len(variation) > 3 and variation in combined_text:
                return (ticker, company_name)
    
    return None


def classify_fda_event(title: str, description: str) -> str:
    """Classify FDA announcement type."""
    title_lower = title.lower()
    description_lower = description.lower() if description else ''
    combined = f"{title_lower} {description_lower}"
    
    if any(word in combined for word in ['approval', 'approved', 'approves']):
        return 'fda_approval'
    elif any(word in combined for word in ['rejection', 'rejected', 'rejects', 'complete response letter', 'crl']):
        return 'fda_rejection'
    elif any(word in combined for word in ['advisory committee', 'adcom', 'panel']):
        return 'fda_adcom'
    elif any(word in combined for word in ['safety alert', 'warning', 'recall']):
        return 'fda_safety_alert'
    elif any(word in combined for word in ['pdufa', 'action date']):
        return 'fda_announcement'
    else:
        return 'fda_announcement'


def scan_fda(tickers: List[str], companies: Optional[Dict[str, Dict]] = None, limit_per_ticker: int = 3) -> List[Dict[str, Any]]:
    """
    Scan FDA for recent announcements.
    
    Args:
        tickers: List of ticker symbols to scan
        companies: Dictionary mapping ticker -> company info (name, sector)
        limit_per_ticker: Maximum events to return per ticker
        
    Returns:
        List of normalized event dictionaries
    """
    logger.info(f"FDA scanner starting for {len(tickers)} tickers")
    
    if companies is None:
        companies = {}
    
    events = []
    all_announcements = []
    
    for feed_name, feed_url in FDA_RSS_FEEDS.items():
        try:
            announcements = fetch_fda_rss_feed(feed_url, limit=30)
            all_announcements.extend(announcements)
            logger.info(f"Fetched {len(announcements)} items from FDA {feed_name} feed")
        except Exception as e:
            logger.error(f"Error fetching FDA {feed_name} feed: {e}")
            continue
    
    logger.info(f"Total FDA announcements fetched: {len(all_announcements)}")
    
    ticker_event_counts = {ticker: 0 for ticker in tickers}
    
    for announcement in all_announcements:
        try:
            match = extract_company_from_fda_announcement(
                announcement['title'],
                announcement.get('description', ''),
                tickers,
                companies
            )
            
            if not match:
                continue
            
            ticker, company_name = match
            
            if ticker_event_counts[ticker] >= limit_per_ticker:
                continue
            
            event_type = classify_fda_event(
                announcement['title'],
                announcement.get('description', '')
            )
            
            company_info = companies.get(ticker, {})
            sector = company_info.get('sector', 'Healthcare')
            
            event = normalize_event(
                ticker=ticker,
                company_name=company_name,
                event_type=event_type,
                title=announcement['title'],
                date=announcement['date'],
                source='FDA.gov',
                source_url=announcement['url'],
                description=announcement.get('description', ''),
                source_scanner='fda',
                sector=sector
            )
            
            events.append(event)
            ticker_event_counts[ticker] += 1
            
        except Exception as e:
            logger.error(f"Error processing FDA announcement: {e}")
            continue
    
    logger.info(f"FDA scanner completed: {len(events)} events found")
    return events
