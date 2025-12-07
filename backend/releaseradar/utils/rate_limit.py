"""
Rate limiting utilities for external API calls.

Provides per-domain and per-endpoint rate limiting with configurable limits.
"""

import time
from collections import defaultdict, deque
from typing import Optional
from urllib.parse import urlparse

from loguru import logger

from releaseradar.config import settings
from releaseradar.utils.errors import RateLimitError


class RateLimiter:
    """
    Token bucket rate limiter for controlling request rates.
    
    Tracks requests per domain/key and enforces configurable limits.
    """
    
    def __init__(self, requests: int = 10, period: int = 1):
        """
        Initialize rate limiter.
        
        Args:
            requests: Number of requests allowed per period
            period: Time period in seconds
        """
        self.requests = requests
        self.period = period
        self._buckets: dict[str, deque] = defaultdict(deque)
    
    def acquire(self, key: str) -> None:
        """
        Acquire a token for the given key, blocking if necessary.
        
        Args:
            key: Rate limit key (e.g., domain name, endpoint)
            
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        if not settings.rate_limit_enabled:
            return
        
        now = time.time()
        bucket = self._buckets[key]
        
        # Remove expired timestamps
        while bucket and bucket[0] <= now - self.period:
            bucket.popleft()
        
        # Check if we can make a request
        if len(bucket) >= self.requests:
            wait_time = self.period - (now - bucket[0])
            if wait_time > 0:
                logger.warning(
                    f"Rate limit reached for {key}: {len(bucket)}/{self.requests} requests in {self.period}s. "
                    f"Retry after {wait_time:.2f}s"
                )
                raise RateLimitError(
                    f"Rate limit exceeded for {key}",
                    retry_after=int(wait_time) + 1,
                )
        
        # Add current request
        bucket.append(now)
    
    def wait_if_needed(self, key: str, max_wait: float = 10.0) -> None:
        """
        Wait if rate limit is reached, up to max_wait seconds.
        
        Args:
            key: Rate limit key
            max_wait: Maximum seconds to wait
        """
        if not settings.rate_limit_enabled:
            return
        
        now = time.time()
        bucket = self._buckets[key]
        
        # Remove expired timestamps
        while bucket and bucket[0] <= now - self.period:
            bucket.popleft()
        
        # Check if we need to wait
        if len(bucket) >= self.requests:
            wait_time = min(self.period - (now - bucket[0]), max_wait)
            if wait_time > 0:
                logger.debug(f"Rate limit: waiting {wait_time:.2f}s for {key}")
                time.sleep(wait_time)
                # Recurse to check again after waiting
                self.wait_if_needed(key, max_wait - wait_time)
        
        # Add current request
        bucket.append(time.time())
    
    def reset(self, key: str) -> None:
        """Reset rate limit for a specific key."""
        if key in self._buckets:
            self._buckets[key].clear()
            logger.debug(f"Rate limit reset for {key}")
    
    def reset_all(self) -> None:
        """Reset all rate limits."""
        self._buckets.clear()
        logger.debug("All rate limits reset")


class DomainRateLimiter:
    """Rate limiter that tracks limits per domain."""
    
    def __init__(self):
        self._limiters: dict[str, RateLimiter] = {}
        self._default_limiter = RateLimiter(
            requests=settings.rate_limit_default_requests,
            period=settings.rate_limit_default_period,
        )
    
    def get_domain(self, url: str) -> str:
        """Extract domain from URL."""
        parsed = urlparse(url)
        return parsed.netloc or "default"
    
    def register_domain(self, domain: str, requests: int, period: int) -> None:
        """Register a rate limit for a specific domain."""
        self._limiters[domain] = RateLimiter(requests=requests, period=period)
        logger.debug(f"Registered rate limit for {domain}: {requests} req/{period}s")
    
    def acquire(self, url: str) -> None:
        """
        Acquire rate limit token for URL's domain.
        
        Args:
            url: Full URL or domain
            
        Raises:
            RateLimitError: If rate limit would be exceeded
        """
        domain = self.get_domain(url)
        limiter = self._limiters.get(domain, self._default_limiter)
        limiter.acquire(domain)
    
    def wait_if_needed(self, url: str, max_wait: float = 10.0) -> None:
        """Wait if rate limit is reached for URL's domain."""
        domain = self.get_domain(url)
        limiter = self._limiters.get(domain, self._default_limiter)
        limiter.wait_if_needed(domain, max_wait)


# Global rate limiter instance
domain_rate_limiter = DomainRateLimiter()

# Pre-register known domains
domain_rate_limiter.register_domain(
    "sec.gov",
    requests=settings.sec_edgar_rate_limit_requests,
    period=settings.sec_edgar_rate_limit_period,
)

domain_rate_limiter.register_domain(
    "fda.gov",
    requests=settings.fda_rate_limit_requests,
    period=settings.fda_rate_limit_period,
)
