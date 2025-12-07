"""
CIK Mapping Service for SEC EDGAR API integration.

Provides ticker-to-CIK (Central Index Key) mapping for SEC EDGAR API calls.
SEC EDGAR requires CIK numbers, not ticker symbols.

Example:
    - Ticker: "TSLA" -> CIK: "0001318605"
    - Ticker: "AAPL" -> CIK: "0000320193"
    - Ticker: "MSFT" -> CIK: "0000789019"
"""

import json
import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional, Dict
from tenacity import retry, stop_after_attempt, wait_exponential

from scanners.http_client import fetch_sec_url

logger = logging.getLogger(__name__)

_CIK_CACHE: Optional[Dict[str, str]] = None
_CIK_CACHE_LOCK = threading.Lock()

SEC_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

LOCAL_CACHE_PATH = Path(__file__).parent.parent.parent / "data" / "cik_cache.json"
CACHE_MAX_AGE_HOURS = 24


def _load_local_cache() -> Optional[Dict[str, str]]:
    """Load CIK mappings from local file cache if available and fresh."""
    try:
        if not LOCAL_CACHE_PATH.exists():
            return None
        
        stat = LOCAL_CACHE_PATH.stat()
        age_hours = (time.time() - stat.st_mtime) / 3600
        
        if age_hours > CACHE_MAX_AGE_HOURS:
            logger.info(f"Local CIK cache is stale ({age_hours:.1f}h old)")
            return None
        
        with open(LOCAL_CACHE_PATH, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and len(data) > 1000:
            logger.info(f"Loaded {len(data)} CIK mappings from local cache ({age_hours:.1f}h old)")
            return data
        
        return None
    except Exception as e:
        logger.warning(f"Failed to load local CIK cache: {e}")
        return None


def _save_local_cache(mappings: Dict[str, str]) -> None:
    """Save CIK mappings to local file cache."""
    try:
        LOCAL_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        with open(LOCAL_CACHE_PATH, 'w') as f:
            json.dump(mappings, f)
        
        logger.info(f"Saved {len(mappings)} CIK mappings to local cache")
    except Exception as e:
        logger.warning(f"Failed to save local CIK cache: {e}")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=4, max=10))
def _fetch_company_tickers() -> Dict[str, str]:
    """
    Fetch company tickers from SEC and build ticker-to-CIK mapping.
    
    Returns:
        Dictionary mapping uppercase ticker -> zero-padded CIK string
        
    Raises:
        Exception: If fetching fails after retries
    """
    logger.info("Fetching SEC company tickers mapping from SEC.gov")
    
    try:
        response = fetch_sec_url(SEC_COMPANY_TICKERS_URL, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        ticker_to_cik = {}
        
        for entry in data.values():
            ticker = entry.get('ticker', '').upper()
            cik_num = entry.get('cik_str')
            
            if ticker and cik_num is not None:
                cik_padded = str(cik_num).zfill(10)
                ticker_to_cik[ticker] = cik_padded
        
        logger.info(f"Successfully loaded {len(ticker_to_cik)} ticker-to-CIK mappings from SEC")
        
        _save_local_cache(ticker_to_cik)
        
        return ticker_to_cik
    
    except Exception as e:
        logger.error(f"Failed to fetch SEC company tickers: {e}")
        raise


def _ensure_cache_loaded() -> None:
    """Load CIK cache if not already loaded (thread-safe). Uses local file cache as fallback."""
    global _CIK_CACHE
    
    if _CIK_CACHE is not None:
        return
    
    with _CIK_CACHE_LOCK:
        if _CIK_CACHE is not None:
            return
        
        local_cache = _load_local_cache()
        if local_cache:
            _CIK_CACHE = local_cache
            return
        
        try:
            _CIK_CACHE = _fetch_company_tickers()
        except Exception as e:
            logger.error(f"Failed to load CIK cache from SEC: {e}")
            
            stale_cache = _load_stale_local_cache()
            if stale_cache:
                logger.warning(f"Using stale local cache with {len(stale_cache)} mappings")
                _CIK_CACHE = stale_cache
            else:
                _CIK_CACHE = {}


def _load_stale_local_cache() -> Optional[Dict[str, str]]:
    """Load CIK mappings from local cache even if stale (for fallback)."""
    try:
        if not LOCAL_CACHE_PATH.exists():
            return None
        
        with open(LOCAL_CACHE_PATH, 'r') as f:
            data = json.load(f)
        
        if isinstance(data, dict) and len(data) > 1000:
            return data
        
        return None
    except Exception:
        return None


def get_cik_for_ticker(ticker: str) -> Optional[str]:
    """
    Get CIK (Central Index Key) for a given ticker symbol.
    
    Args:
        ticker: Stock ticker symbol (e.g., "TSLA", "AAPL")
        
    Returns:
        Zero-padded 10-digit CIK string (e.g., "0001318605") or None if not found
        
    Examples:
        >>> get_cik_for_ticker("TSLA")
        "0001318605"
        
        >>> get_cik_for_ticker("AAPL")
        "0000320193"
        
        >>> get_cik_for_ticker("MSFT")
        "0000789019"
        
        >>> get_cik_for_ticker("INVALID")
        None
    """
    if not ticker:
        return None
    
    # Ensure cache is loaded
    _ensure_cache_loaded()
    
    # Lookup ticker (case-insensitive)
    ticker_upper = ticker.upper().strip()
    cik = _CIK_CACHE.get(ticker_upper) if _CIK_CACHE else None
    
    if cik:
        logger.debug(f"Mapped ticker {ticker} -> CIK {cik}")
    else:
        logger.warning(f"No CIK found for ticker: {ticker}")
    
    return cik


def reload_cache() -> None:
    """
    Force reload of the CIK cache.
    
    Useful for testing or if the cache becomes stale.
    """
    global _CIK_CACHE
    logger.info("Reloading CIK cache")
    _CIK_CACHE = None
    _ensure_cache_loaded()


def get_cache_size() -> int:
    """
    Get the number of ticker-to-CIK mappings in cache.
    
    Returns:
        Number of mappings loaded, or 0 if cache not loaded
    """
    if _CIK_CACHE is None:
        return 0
    return len(_CIK_CACHE)
