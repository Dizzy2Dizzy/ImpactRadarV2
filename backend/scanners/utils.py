"""
Scanner utility functions for Impact Radar.

Provides deduplication, normalization, and helper functions for scanners.
"""

import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Tuple, Optional


def classify_info_tier(event_type: str, source: str, title: str = "") -> Tuple[str, Optional[str]]:
    """
    Classify event into information tier and subtype.
    
    Wave J: Information Tiers
    - Primary: Direct corporate/financial events linked to price moves (SEC filings, FDA approvals, earnings, etc.)
    - Secondary: Contextual risk factors (environmental, infrastructure, geopolitical)
    
    Args:
        event_type: Event type (e.g., 'sec_8k', 'fda_approval', 'earnings')
        source: Event source (e.g., 'SEC EDGAR', 'FDA.gov', 'Press Release')
        title: Event title for additional context
        
    Returns:
        Tuple of (info_tier, info_subtype)
        - info_tier: "primary" or "secondary"
        - info_subtype: Granular classification (e.g., "ipo", "earnings", "regulatory_primary")
    """
    # All scanner-created events are primary by default
    # Secondary tier is reserved for future context signals (environmental, infrastructure, etc.)
    
    # SEC Filings - always primary, classify subtype
    if event_type.startswith('sec_'):
        if event_type == 'sec_s1':
            return ("primary", "ipo")
        elif event_type in ['sec_10k', 'sec_10q']:
            return ("primary", "earnings")
        elif event_type in ['sec_13d', 'sec_13g']:
            return ("primary", "ownership_change")
        elif event_type == 'sec_def14a':
            return ("primary", "proxy")
        elif event_type == 'sec_8k':
            # Classify 8-K by items in title
            title_lower = title.lower()
            if any(word in title_lower for word in ['acquisition', 'merger', 'agreement to acquire']):
                return ("primary", "ma")
            elif any(word in title_lower for word in ['earnings', 'results', 'financial']):
                return ("primary", "earnings")
            elif any(word in title_lower for word in ['officer', 'director', 'executive']):
                return ("primary", "executive_change")
            elif any(word in title_lower for word in ['debt', 'credit', 'financing']):
                return ("primary", "financing")
            else:
                return ("primary", "material_event")
        else:
            return ("primary", "filing")
    
    # FDA Events - always primary regulatory
    if event_type.startswith('fda_'):
        return ("primary", "regulatory_primary")
    
    # Earnings & Guidance - always primary
    if event_type in ['earnings', 'guidance_raise', 'guidance_lower', 'guidance_withdraw']:
        return ("primary", "earnings")
    
    # M&A and Corporate Actions - always primary
    if event_type in ['merger_acquisition', 'divestiture', 'restructuring']:
        return ("primary", "ma")
    
    # Product Events - always primary
    if event_type in ['product_launch', 'product_delay', 'product_recall', 'flagship_launch']:
        return ("primary", "product")
    
    # Legal/Regulatory - always primary
    if event_type in ['investigation', 'lawsuit']:
        return ("primary", "legal")
    
    # Press Releases - primary if major event
    if event_type == 'press_release':
        # Classify based on keywords in title
        title_lower = title.lower()
        if any(word in title_lower for word in ['acquisition', 'merger', 'acquire']):
            return ("primary", "ma")
        elif any(word in title_lower for word in ['approval', 'fda', 'regulatory']):
            return ("primary", "regulatory_primary")
        elif any(word in title_lower for word in ['launch', 'product', 'release']):
            return ("primary", "product")
        elif any(word in title_lower for word in ['earnings', 'results', 'revenue', 'profit']):
            return ("primary", "earnings")
        else:
            return ("primary", "announcement")
    
    # Default: primary with generic classification
    return ("primary", None)


def canonicalize_url(url: str) -> str:
    """
    Canonicalize a URL for deduplication by removing query params and normalizing.
    
    Args:
        url: Source URL to canonicalize
        
    Returns:
        Canonicalized URL (lowercase, no query params, no trailing slash)
    """
    from urllib.parse import urlparse, urlunparse
    
    if not url:
        return ""
    
    try:
        parsed = urlparse(url.strip())
        
        # Reconstruct URL without query params or fragment
        # Keep scheme, netloc, and path only
        canonical = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path.rstrip('/'),
            '', '', ''
        ))
        
        return canonical
    except Exception:
        # If URL parsing fails, return normalized string
        return url.strip().lower().rstrip('/')


def generate_raw_id(ticker: str, event_type: str, title: str, date: datetime, source_url: str = None) -> str:
    """
    Generate a unique raw_id for deduplication.
    
    Creates a hash from ticker, event_type, title, date, and source_url to prevent
    duplicate events from being inserted. Including source_url prevents duplicates
    when the same filing appears with different titles.
    
    Args:
        ticker: Company ticker symbol
        event_type: Event type (e.g., 'sec_8k', 'fda_approval')
        title: Event title
        date: Event date
        source_url: Optional source URL (canonicalized before hashing)
        
    Returns:
        Unique raw_id string (e.g., 'sec_8k_aapl_20251113_abc123')
    """
    # Normalize date to YYYYMMDD format
    date_str = date.strftime('%Y%m%d')
    
    # Create hash input from all fields
    hash_input = f"{ticker.upper()}|{event_type.lower()}|{title}|{date_str}"
    
    # Include canonicalized source_url if provided (prevents duplicate filings)
    if source_url:
        canonical_url = canonicalize_url(source_url)
        if canonical_url:
            hash_input += f"|{canonical_url}"
    
    # Generate short hash (first 8 characters of SHA-256)
    hash_digest = hashlib.sha256(hash_input.encode()).hexdigest()[:8]
    
    # Format: eventtype_ticker_date_hash
    raw_id = f"{event_type.lower()}_{ticker.lower()}_{date_str}_{hash_digest}"
    
    return raw_id


def normalize_event(
    ticker: str,
    company_name: str,
    event_type: str,
    title: str,
    date: datetime,
    source: str,
    source_url: str,
    description: str = None,
    source_scanner: str = None,
    sector: str = None,
    info_tier: str = None,
    info_subtype: str = None,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Normalize event data to standard schema.
    
    Args:
        ticker: Company ticker symbol
        company_name: Company name
        event_type: Event type (must match VALID_EVENT_TYPES)
        title: Event title
        date: Event date (should be timezone-aware UTC)
        source: Event source (e.g., 'SEC EDGAR', 'FDA.gov')
        source_url: URL to source document
        description: Optional event description
        source_scanner: Scanner that found this event
        sector: Company sector
        info_tier: Information tier ("primary" or "secondary"). Auto-classified if not provided.
        info_subtype: Optional granular classification (e.g., "ipo", "earnings", "regulatory_primary")
        metadata: Optional metadata dict (e.g., {"8k_items": ["2.02", "5.02"]} for 8-K filings)
        
    Returns:
        Normalized event dictionary ready for DataManager.add_event()
    """
    # Ensure date is timezone-aware UTC
    if date.tzinfo is None:
        date = date.replace(tzinfo=timezone.utc)
    
    # Generate deduplication key (includes source_url for better uniqueness)
    raw_id = generate_raw_id(ticker, event_type, title, date, source_url)
    
    # Auto-classify info tier if not provided
    if info_tier is None or info_subtype is None:
        classified_tier, classified_subtype = classify_info_tier(event_type, source, title)
        if info_tier is None:
            info_tier = classified_tier
        if info_subtype is None:
            info_subtype = classified_subtype
    
    return {
        'ticker': ticker.upper(),
        'company_name': company_name,
        'event_type': event_type.lower(),
        'title': title,
        'date': date,
        'source': source,
        'source_url': source_url,
        'description': description,
        'raw_id': raw_id,
        'source_scanner': source_scanner,
        'sector': sector,
        'info_tier': info_tier,
        'info_subtype': info_subtype,
        'metadata': metadata or {}
    }
