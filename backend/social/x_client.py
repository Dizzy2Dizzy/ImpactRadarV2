"""
X.com (Twitter) API v2 Client for Impact Radar

Provides wrapper for X API v2 to fetch posts related to stock tickers.
Handles authentication, rate limiting, and ticker symbol extraction.
"""

import os
import re
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
import requests

logger = logging.getLogger(__name__)


@dataclass
class SocialPost:
    """Represents a social media post from X.com"""
    id: str
    created_at: datetime
    text: str
    author_handle: str
    author_followers: int
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    symbols: List[str]  # List of ticker symbols mentioned ($AAPL, $TSLA, etc.)
    url: str


def extract_cashtags(text: str) -> List[str]:
    """
    Extract ticker symbols from text using cashtag pattern ($TICKER).
    
    Args:
        text: Text to extract cashtags from
        
    Returns:
        List of unique ticker symbols (without $ prefix, uppercase)
    """
    # Match $TICKER pattern (1-5 letters, uppercase)
    pattern = r'\$([A-Z]{1,5})\b'
    matches = re.findall(pattern, text.upper())
    
    # Return unique tickers
    return list(set(matches))


def fetch_posts_for_tickers(
    tickers: List[str],
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    max_results: int = 100
) -> tuple[List[SocialPost], bool]:
    """
    Fetch posts from X.com that mention the given ticker symbols.
    
    Uses X API v2 search endpoint with proper authentication.
    Handles rate limits gracefully and extracts ticker symbols from post text.
    
    Args:
        tickers: List of ticker symbols to search for (e.g., ['AAPL', 'TSLA'])
        since: Start date for search (optional)
        until: End date for search (optional)
        max_results: Maximum number of posts to return (default 100, max 100 per request)
        
    Returns:
        Tuple of (list of SocialPost objects, source_available flag)
        - If credentials missing, returns ([], False)
        - If API error, returns ([], True) with logged error
        - On success, returns (posts, True)
    """
    # Check for required credentials
    bearer_token = os.getenv('X_BEARER_TOKEN')
    
    if not bearer_token:
        logger.warning(
            "X.com API credentials not configured. "
            "Set X_BEARER_TOKEN environment variable to enable social sentiment analysis."
        )
        return [], False
    
    # Build search query for cashtags
    # Example: ($AAPL OR $TSLA) -is:retweet
    cashtags = [f"${ticker.upper()}" for ticker in tickers]
    query = f"({' OR '.join(cashtags)}) -is:retweet lang:en"
    
    # Build API request
    url = "https://api.twitter.com/2/tweets/search/recent"
    
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "User-Agent": "Impact Radar/1.0"
    }
    
    params: Dict[str, Any] = {
        "query": query,
        "max_results": min(max_results, 100),  # API limit is 100
        "tweet.fields": "created_at,public_metrics,author_id",
        "expansions": "author_id",
        "user.fields": "username,public_metrics"
    }
    
    # Add date filters if provided
    if since:
        params["start_time"] = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    if until:
        params["end_time"] = until.strftime("%Y-%m-%dT%H:%M:%SZ")
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        
        # Handle rate limiting
        if response.status_code == 429:
            logger.error(
                f"X API rate limit exceeded. "
                f"Reset time: {response.headers.get('x-rate-limit-reset', 'unknown')}"
            )
            return [], True
        
        # Handle authentication errors
        if response.status_code == 401:
            logger.error("X API authentication failed. Check X_BEARER_TOKEN.")
            return [], False
        
        # Handle other errors
        if response.status_code != 200:
            logger.error(
                f"X API request failed: {response.status_code} - {response.text}"
            )
            return [], True
        
        data = response.json()
        
        # Extract posts from response
        posts: List[SocialPost] = []
        
        if not data.get('data'):
            logger.info(f"No posts found for tickers: {tickers}")
            return [], True
        
        # Build author lookup map
        authors_map = {}
        if data.get('includes', {}).get('users'):
            for user in data['includes']['users']:
                authors_map[user['id']] = {
                    'username': user['username'],
                    'followers': user.get('public_metrics', {}).get('followers_count', 0)
                }
        
        # Parse tweets
        for tweet in data['data']:
            tweet_id = tweet['id']
            text = tweet['text']
            created_at_str = tweet['created_at']
            author_id = tweet['author_id']
            
            # Get author info
            author_info = authors_map.get(author_id, {
                'username': 'unknown',
                'followers': 0
            })
            
            # Get engagement metrics
            metrics = tweet.get('public_metrics', {})
            
            # Extract ticker symbols from text
            symbols = extract_cashtags(text)
            
            # Only include posts that mention at least one of our target tickers
            target_tickers_upper = [t.upper() for t in tickers]
            if not any(symbol in target_tickers_upper for symbol in symbols):
                continue
            
            post = SocialPost(
                id=tweet_id,
                created_at=datetime.strptime(created_at_str, "%Y-%m-%dT%H:%M:%S.%fZ"),
                text=text,
                author_handle=author_info['username'],
                author_followers=author_info['followers'],
                like_count=metrics.get('like_count', 0),
                retweet_count=metrics.get('retweet_count', 0),
                reply_count=metrics.get('reply_count', 0),
                quote_count=metrics.get('quote_count', 0),
                symbols=symbols,
                url=f"https://twitter.com/{author_info['username']}/status/{tweet_id}"
            )
            
            posts.append(post)
        
        logger.info(f"Fetched {len(posts)} posts for tickers: {tickers}")
        return posts, True
        
    except requests.exceptions.Timeout:
        logger.error("X API request timed out")
        return [], True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"X API request failed: {e}")
        return [], True
        
    except Exception as e:
        logger.error(f"Unexpected error fetching X posts: {e}")
        return [], True
