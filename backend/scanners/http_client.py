"""
Robust HTTP client for web scraping with proper headers and rate limiting.

This module provides browser-like request headers to avoid blocks from
SEC.gov, FDA.gov, and other government/corporate websites.
"""

import logging
import random
import time
from typing import Dict, Optional, Any
from functools import wraps

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

SEC_USER_AGENT = "ImpactRadar/1.0 (Financial Event Scanner; +https://impactradar.com; contact@impactradar.com)"

BROWSER_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]

def get_browser_headers(referer: Optional[str] = None) -> Dict[str, str]:
    """Get browser-like headers for general web scraping."""
    headers = {
        "User-Agent": random.choice(BROWSER_USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    if referer:
        headers["Referer"] = referer
    return headers


def get_sec_headers() -> Dict[str, str]:
    """
    Get SEC.gov compliant headers.
    
    SEC requires a User-Agent that identifies the application and provides contact info.
    Format: Company/Application Contact@email.com
    See: https://www.sec.gov/os/webmaster-faq#developers
    """
    return {
        "User-Agent": SEC_USER_AGENT,
        "Accept": "application/atom+xml,application/xml,text/html,application/xhtml+xml,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Host": "www.sec.gov",
    }


def get_fda_headers() -> Dict[str, str]:
    """Get FDA.gov compatible headers (browser-like)."""
    return {
        "User-Agent": random.choice(BROWSER_USER_AGENTS),
        "Accept": "application/rss+xml,application/xml,text/xml,text/html,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "DNT": "1",
    }


def create_session(max_retries: int = 3, backoff_factor: float = 0.5) -> requests.Session:
    """
    Create a requests session with retry logic and connection pooling.
    
    Args:
        max_retries: Maximum number of retries for failed requests
        backoff_factor: Backoff factor for retry delays
        
    Returns:
        Configured requests Session
    """
    session = requests.Session()
    
    retry_strategy = Retry(
        total=max_retries,
        backoff_factor=backoff_factor,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS"],
        raise_on_status=False,
    )
    
    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=10,
        pool_maxsize=10,
    )
    
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session


_sessions: Dict[str, requests.Session] = {}


def get_session(session_type: str = "default") -> requests.Session:
    """Get or create a shared session for the given type."""
    if session_type not in _sessions:
        _sessions[session_type] = create_session()
    return _sessions[session_type]


class RateLimiter:
    """Simple rate limiter to avoid overwhelming servers."""
    
    def __init__(self, min_delay: float = 0.5, max_delay: float = 2.0):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self._last_request_time: Dict[str, float] = {}
    
    def wait(self, domain: str):
        """Wait before making a request to the given domain."""
        now = time.time()
        last_time = self._last_request_time.get(domain, 0)
        
        elapsed = now - last_time
        delay = random.uniform(self.min_delay, self.max_delay)
        
        if elapsed < delay:
            sleep_time = delay - elapsed
            time.sleep(sleep_time)
        
        self._last_request_time[domain] = time.time()


_rate_limiters: Dict[str, RateLimiter] = {
    "sec.gov": RateLimiter(min_delay=0.2, max_delay=0.5),
    "fda.gov": RateLimiter(min_delay=0.5, max_delay=1.5),
    "default": RateLimiter(min_delay=0.3, max_delay=1.0),
}


def get_rate_limiter(domain: str) -> RateLimiter:
    """Get rate limiter for a domain."""
    for key in _rate_limiters:
        if key in domain:
            return _rate_limiters[key]
    return _rate_limiters["default"]


def fetch_url(
    url: str,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 20,
    session_type: str = "default",
    rate_limit: bool = True,
) -> requests.Response:
    """
    Fetch a URL with proper headers, rate limiting, and error handling.
    
    Args:
        url: URL to fetch
        headers: Optional custom headers (defaults to browser headers)
        timeout: Request timeout in seconds
        session_type: Session type for connection pooling
        rate_limit: Whether to apply rate limiting
        
    Returns:
        requests.Response object
        
    Raises:
        requests.exceptions.RequestException: On request failure
    """
    from urllib.parse import urlparse
    
    parsed = urlparse(url)
    domain = parsed.netloc
    
    if rate_limit:
        limiter = get_rate_limiter(domain)
        limiter.wait(domain)
    
    if headers is None:
        headers = get_browser_headers()
    
    session = get_session(session_type)
    
    logger.debug(f"Fetching URL: {url}")
    response = session.get(url, headers=headers, timeout=timeout)
    
    if response.status_code == 403:
        logger.warning(f"403 Forbidden for {url} - may need different headers or IP rotation")
    elif response.status_code == 429:
        logger.warning(f"429 Rate Limited for {url} - backing off")
        time.sleep(random.uniform(5, 10))
    
    return response


def fetch_sec_url(url: str, timeout: int = 20) -> requests.Response:
    """
    Fetch a SEC.gov URL with proper compliance headers.
    
    Args:
        url: SEC.gov URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        requests.Response object
    """
    headers = get_sec_headers()
    return fetch_url(url, headers=headers, timeout=timeout, session_type="sec", rate_limit=True)


def fetch_fda_url(url: str, timeout: int = 20) -> requests.Response:
    """
    Fetch a FDA.gov URL with browser-like headers.
    
    Args:
        url: FDA.gov URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        requests.Response object
    """
    headers = get_fda_headers()
    return fetch_url(url, headers=headers, timeout=timeout, session_type="fda", rate_limit=True)
