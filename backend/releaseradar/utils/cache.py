"""
Caching utilities for HTTP responses, yfinance data, and other expensive operations.

Supports both in-memory and on-disk caching with TTL.
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Optional, Callable
from datetime import datetime, timedelta
from functools import wraps

from loguru import logger

from releaseradar.config import settings


class Cache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self):
        self._cache: dict[str, tuple[Any, datetime]] = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key in self._cache:
            value, expires_at = self._cache[key]
            if datetime.utcnow() < expires_at:
                logger.debug(f"Cache hit: {key}")
                return value
            else:
                logger.debug(f"Cache expired: {key}")
                del self._cache[key]
        return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """Set value in cache with TTL."""
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        self._cache[key] = (value, expires_at)
        logger.debug(f"Cache set: {key} (TTL: {ttl_seconds}s)")
    
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache deleted: {key}")
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._cache.clear()
        logger.debug("Cache cleared")
    
    def cleanup_expired(self) -> None:
        """Remove all expired entries."""
        now = datetime.utcnow()
        expired_keys = [k for k, (_, exp) in self._cache.items() if now >= exp]
        for key in expired_keys:
            del self._cache[key]
        if expired_keys:
            logger.debug(f"Cleaned up {len(expired_keys)} expired cache entries")


class DiskCache:
    """On-disk cache for persistent caching across restarts."""
    
    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path(settings.cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_cache_path(self, key: str) -> Path:
        """Get cache file path for a key."""
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from disk cache if not expired."""
        cache_path = self._get_cache_path(key)
        
        if not cache_path.exists():
            return None
        
        try:
            with open(cache_path, "r") as f:
                data = json.load(f)
            
            expires_at = datetime.fromisoformat(data["expires_at"])
            if datetime.utcnow() < expires_at:
                logger.debug(f"Disk cache hit: {key}")
                return data["value"]
            else:
                logger.debug(f"Disk cache expired: {key}")
                cache_path.unlink()
                return None
        except Exception as e:
            logger.warning(f"Disk cache read error: {e}")
            return None
    
    def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Set value in disk cache with TTL."""
        cache_path = self._get_cache_path(key)
        expires_at = datetime.utcnow() + timedelta(seconds=ttl_seconds)
        
        try:
            data = {
                "key": key,
                "value": value,
                "expires_at": expires_at.isoformat(),
            }
            with open(cache_path, "w") as f:
                json.dump(data, f)
            logger.debug(f"Disk cache set: {key} (TTL: {ttl_seconds}s)")
        except Exception as e:
            logger.warning(f"Disk cache write error: {e}")
    
    def delete(self, key: str) -> None:
        """Delete value from disk cache."""
        cache_path = self._get_cache_path(key)
        if cache_path.exists():
            cache_path.unlink()
            logger.debug(f"Disk cache deleted: {key}")
    
    def clear(self) -> None:
        """Clear all disk cache entries."""
        for cache_file in self.cache_dir.glob("*.json"):
            cache_file.unlink()
        logger.debug("Disk cache cleared")


# Global cache instances
memory_cache = Cache()
disk_cache = DiskCache()


def cached(ttl_seconds: int = 300, use_disk: bool = False):
    """
    Decorator for caching function results.
    
    Args:
        ttl_seconds: Time to live for cached value in seconds
        use_disk: If True, use disk cache instead of memory cache
        
    Usage:
        @cached(ttl_seconds=600)
        def expensive_function(arg1, arg2):
            # ... expensive computation
            return result
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not settings.cache_enabled:
                return func(*args, **kwargs)
            
            # Create cache key from function name and arguments
            cache_key = f"{func.__module__}.{func.__name__}:{args}:{kwargs}"
            
            # Try to get from cache
            cache_instance = disk_cache if use_disk else memory_cache
            cached_value = cache_instance.get(cache_key)
            
            if cached_value is not None:
                return cached_value
            
            # Compute and cache result
            result = func(*args, **kwargs)
            cache_instance.set(cache_key, result, ttl_seconds)
            
            return result
        
        return wrapper
    return decorator


def cache_yfinance_quote(ticker: str, price: float) -> None:
    """Cache a yfinance stock quote."""
    key = f"yfinance:quote:{ticker}"
    memory_cache.set(key, price, ttl_seconds=settings.yfinance_cache_ttl)


def get_cached_yfinance_quote(ticker: str) -> Optional[float]:
    """Get cached yfinance stock quote."""
    key = f"yfinance:quote:{ticker}"
    return memory_cache.get(key)


def cache_http_response(url: str, content: str, ttl_seconds: Optional[int] = None) -> None:
    """Cache HTTP response content."""
    if ttl_seconds is None:
        ttl_seconds = settings.http_cache_ttl
    key = f"http:{url}"
    disk_cache.set(key, content, ttl_seconds)


def get_cached_http_response(url: str) -> Optional[str]:
    """Get cached HTTP response content."""
    key = f"http:{url}"
    return disk_cache.get(key)
