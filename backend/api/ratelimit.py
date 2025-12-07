"""Rate limiting configuration for API endpoints"""
from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from typing import Optional


def plan_limit(request: Optional[Request] = None) -> str:
    """
    Get rate limit string based on API key plan or user subscription.
    
    SlowAPI calls this with no arguments during decorator initialization,
    then with the actual Request during request handling.
    
    Note: Generous limits prevent dashboard loading issues when multiple
    API calls fire simultaneously. Burst limits are per-minute windows.
    """
    if request is None:
        # Called during decorator registration - return a conservative default
        return "120/minute"
    
    plan = getattr(request.state, "plan", "public")
    return {
        "public": "120/minute",  # Increased to support dashboard loading (6-8 simultaneous requests)
        "free": "180/minute",
        "pro": "600/minute",
        "team": "3000/minute",
    }.get(plan, "120/minute")


# Create slowAPI limiter
def get_rate_limit_key(request: Optional[Request] = None) -> str:
    """Get key for rate limiting (handles SlowAPI's no-arg calls during init)"""
    if request is None:
        return "default"
    return getattr(request.state, "api_key_hash", get_remote_address(request))

limiter = Limiter(key_func=get_rate_limit_key)
