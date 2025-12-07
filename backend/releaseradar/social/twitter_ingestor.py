"""
Twitter/X API Integration for Market Echo Engine.

This module provides real-time and historical tweet ingestion for
event sentiment analysis, ready for Twitter API credentials to be added later.
"""

import os
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
import re

from releaseradar.log_config import logger

try:
    import tweepy
    TWEEPY_AVAILABLE = True
except ImportError:
    TWEEPY_AVAILABLE = False
    logger.warning("Tweepy not installed - Twitter integration will be unavailable")


class TwitterAPIError(Exception):
    """Base exception for Twitter API errors."""
    pass


class TwitterRateLimitError(TwitterAPIError):
    """Raised when Twitter API rate limit is exceeded."""
    def __init__(self, message: str, reset_time: Optional[int] = None):
        super().__init__(message)
        self.reset_time = reset_time


class TwitterAuthError(TwitterAPIError):
    """Raised when Twitter API authentication fails."""
    pass


class TwitterNetworkError(TwitterAPIError):
    """Raised when network issues occur."""
    pass


@dataclass
class TwitterConfig:
    """Configuration for Twitter API access."""
    bearer_token: Optional[str] = None
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    access_token: Optional[str] = None
    access_token_secret: Optional[str] = None
    max_results_per_request: int = 100
    lookback_hours: int = 24
    rate_limit_wait_seconds: int = 60
    max_retries: int = 3
    retry_delay_seconds: int = 5
    
    @classmethod
    def from_env(cls) -> "TwitterConfig":
        """Load configuration from environment variables."""
        return cls(
            bearer_token=os.getenv("TWITTER_BEARER_TOKEN"),
            api_key=os.getenv("TWITTER_API_KEY"),
            api_secret=os.getenv("TWITTER_API_SECRET"),
            access_token=os.getenv("TWITTER_ACCESS_TOKEN"),
            access_token_secret=os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
        )
    
    def is_configured(self) -> bool:
        """Check if minimum required credentials are set."""
        return self.bearer_token is not None


@dataclass
class TweetData:
    """Processed tweet data for sentiment analysis."""
    tweet_id: str
    text: str
    author_id: str
    author_username: Optional[str]
    author_followers: int
    created_at: datetime
    retweet_count: int
    like_count: int
    reply_count: int
    quote_count: int
    ticker: str
    event_keywords: List[str]
    
    @property
    def engagement_score(self) -> float:
        """Calculate normalized engagement score."""
        raw_score = (
            self.like_count * 1.0 +
            self.retweet_count * 2.0 +
            self.reply_count * 1.5 +
            self.quote_count * 2.5
        )
        follower_weight = min(1.0, self.author_followers / 100000)
        return raw_score * (0.5 + 0.5 * follower_weight)
    
    @property
    def is_influencer(self) -> bool:
        """Check if author is considered an influencer."""
        return self.author_followers >= 10000


@dataclass
class SocialEventSignal:
    """Aggregated social signals for an event."""
    event_id: int
    ticker: str
    event_type: str
    
    tweet_count: int
    unique_authors: int
    
    avg_sentiment: float
    sentiment_std: float
    positive_ratio: float
    negative_ratio: float
    neutral_ratio: float
    
    total_engagement: float
    influencer_count: int
    influencer_sentiment: Optional[float]
    
    volume_zscore: float
    
    peak_hour: Optional[int]
    tweet_velocity: float
    
    sample_tweets: List[Dict] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)


class TwitterSentimentIngestor:
    """
    Ingests tweets related to market events for sentiment analysis.
    
    Features:
    - Search tweets by ticker ($SYMBOL) and event keywords
    - Calculate engagement metrics and influencer signals
    - Aggregate sentiment for correlation with event outcomes
    """
    
    EVENT_KEYWORD_MAP = {
        "earnings": ["earnings", "EPS", "revenue", "beat", "miss", "quarterly"],
        "earnings_beat": ["beat", "exceeded", "earnings", "EPS", "surprise"],
        "earnings_miss": ["miss", "missed", "disappointed", "earnings", "below"],
        "fda_approval": ["FDA", "approval", "approved", "drug", "clearance"],
        "fda_rejection": ["FDA", "rejection", "rejected", "CRL", "denied"],
        "sec_8k": ["SEC", "filing", "8-K", "material", "disclosure"],
        "sec_10k": ["SEC", "annual", "10-K", "report"],
        "sec_10q": ["SEC", "quarterly", "10-Q", "report"],
        "guidance_raise": ["guidance", "raised", "increased", "outlook", "upgrade"],
        "guidance_lower": ["guidance", "lowered", "cut", "outlook", "downgrade"],
        "merger_acquisition": ["acquisition", "merger", "buyout", "deal", "acquire"],
        "stock_split": ["split", "stock split", "shares"],
        "dividend": ["dividend", "payout", "distribution", "yield"],
        "insider_buying": ["insider", "buying", "purchased", "CEO", "CFO"],
        "insider_selling": ["insider", "selling", "sold", "CEO", "CFO"],
        "analyst_upgrade": ["upgrade", "analyst", "rating", "buy", "outperform"],
        "analyst_downgrade": ["downgrade", "analyst", "rating", "sell", "underperform"],
        "product_launch": ["launch", "product", "release", "new", "announced"],
        "layoffs": ["layoff", "layoffs", "job cuts", "restructuring", "workforce"],
        "partnership": ["partnership", "collaboration", "agreement", "deal"]
    }
    
    def __init__(self, config: Optional[TwitterConfig] = None):
        self.config = config or TwitterConfig.from_env()
        self.client = None
        
        if self.config.is_configured() and TWEEPY_AVAILABLE:
            self._init_client()
    
    def _init_client(self):
        """Initialize Twitter API client with bearer token only for API v2."""
        if not self.config.bearer_token:
            logger.warning("No bearer token provided - Twitter client not initialized")
            return
            
        try:
            self.client = tweepy.Client(
                bearer_token=self.config.bearer_token,
                wait_on_rate_limit=True
            )
            logger.info("Twitter API client initialized successfully with bearer token")
        except tweepy.TweepyException as e:
            logger.error(f"Failed to initialize Twitter client: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"Unexpected error initializing Twitter client: {e}")
            self.client = None
    
    def is_available(self) -> bool:
        """Check if Twitter integration is available and configured."""
        return self.client is not None
    
    def _build_search_query(
        self,
        ticker: str,
        event_type: str,
        event_keywords: Optional[List[str]] = None
    ) -> str:
        """
        Build Twitter API v2 search query.
        
        Args:
            ticker: Stock ticker symbol
            event_type: Type of event
            event_keywords: Optional custom keywords
            
        Returns:
            Formatted search query string
        """
        query_parts = [f"${ticker}"]
        
        keywords = event_keywords or self.EVENT_KEYWORD_MAP.get(event_type, [])
        if keywords:
            keyword_query = " OR ".join(keywords[:3])
            query_parts.append(f"({keyword_query})")
        
        query_parts.append("-is:retweet")
        query_parts.append("lang:en")
        
        query = " ".join(query_parts)
        
        if len(query) > 512:
            logger.warning(f"Query too long ({len(query)} chars), truncating keywords")
            query_parts = [f"${ticker}", "-is:retweet", "lang:en"]
            query = " ".join(query_parts)
        
        return query
    
    def _parse_tweet_response(
        self,
        tweets,
        ticker: str,
        keywords: List[str]
    ) -> List[TweetData]:
        """
        Parse Twitter API response into TweetData objects.
        
        Args:
            tweets: Tweepy Response object
            ticker: Stock ticker
            keywords: Event keywords used in search
            
        Returns:
            List of TweetData objects
        """
        if not tweets.data:
            return []
        
        users_map = {}
        if tweets.includes and "users" in tweets.includes:
            for user in tweets.includes["users"]:
                users_map[user.id] = user
        
        results = []
        for tweet in tweets.data:
            try:
                author = users_map.get(tweet.author_id)
                
                public_metrics = tweet.public_metrics or {}
                author_followers = 0
                if author and hasattr(author, 'public_metrics'):
                    author_followers = author.public_metrics.get("followers_count", 0)
                
                tweet_data = TweetData(
                    tweet_id=str(tweet.id),
                    text=tweet.text,
                    author_id=str(tweet.author_id),
                    author_username=author.username if author else None,
                    author_followers=author_followers,
                    created_at=tweet.created_at,
                    retweet_count=public_metrics.get("retweet_count", 0),
                    like_count=public_metrics.get("like_count", 0),
                    reply_count=public_metrics.get("reply_count", 0),
                    quote_count=public_metrics.get("quote_count", 0),
                    ticker=ticker,
                    event_keywords=keywords
                )
                results.append(tweet_data)
            except Exception as e:
                logger.warning(f"Error parsing tweet {tweet.id}: {e}")
                continue
        
        return results
    
    def search_event_tweets(
        self,
        ticker: str,
        event_type: str,
        event_keywords: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results: int = 100
    ) -> List[TweetData]:
        """
        Search for tweets related to a specific event using Twitter API v2.
        
        Uses tweepy.Client.search_recent_tweets() with pagination support.
        
        Args:
            ticker: Stock ticker symbol (without $)
            event_type: Type of event (e.g., "earnings", "fda_approval")
            event_keywords: Additional keywords to search
            start_time: Start of search window (default: 24 hours ago)
            end_time: End of search window (default: now)
            max_results: Maximum tweets to retrieve (handles pagination)
            
        Returns:
            List of TweetData objects
            
        Raises:
            TwitterRateLimitError: When rate limit is exceeded
            TwitterAuthError: When authentication fails
            TwitterNetworkError: When network issues occur
        """
        if not self.is_available():
            logger.warning("Twitter API not available - returning empty results")
            return []
        
        query = self._build_search_query(ticker, event_type, event_keywords)
        keywords = event_keywords or self.EVENT_KEYWORD_MAP.get(event_type, [])
        
        if end_time is None:
            end_time = datetime.utcnow()
        if start_time is None:
            start_time = end_time - timedelta(hours=self.config.lookback_hours)
        
        start_time = start_time.replace(tzinfo=None)
        end_time = end_time.replace(tzinfo=None)
        
        if start_time < datetime.utcnow() - timedelta(days=7):
            logger.warning("Twitter API v2 only supports searching last 7 days, adjusting start_time")
            start_time = datetime.utcnow() - timedelta(days=6, hours=23)
        
        all_tweets: List[TweetData] = []
        next_token: Optional[str] = None
        remaining = max_results
        
        for retry in range(self.config.max_retries):
            try:
                while remaining > 0:
                    batch_size = min(remaining, self.config.max_results_per_request)
                    
                    response = self.client.search_recent_tweets(
                        query=query,
                        start_time=start_time,
                        end_time=end_time,
                        max_results=max(10, batch_size),
                        tweet_fields=["created_at", "public_metrics", "author_id"],
                        user_fields=["username", "public_metrics"],
                        expansions=["author_id"],
                        next_token=next_token
                    )
                    
                    if not response.data:
                        logger.info(f"No more tweets found for {ticker} / {event_type}")
                        break
                    
                    parsed_tweets = self._parse_tweet_response(response, ticker, keywords)
                    all_tweets.extend(parsed_tweets)
                    remaining -= len(parsed_tweets)
                    
                    if hasattr(response, 'meta') and response.meta:
                        next_token = response.meta.get('next_token')
                        if not next_token:
                            break
                    else:
                        break
                
                logger.info(f"Retrieved {len(all_tweets)} tweets for {ticker} / {event_type}")
                return all_tweets
                
            except tweepy.TooManyRequests as e:
                reset_time = getattr(e, 'response', {})
                if hasattr(reset_time, 'headers'):
                    reset_time = reset_time.headers.get('x-rate-limit-reset')
                logger.warning(f"Twitter rate limit exceeded. Reset time: {reset_time}")
                if retry < self.config.max_retries - 1:
                    wait_time = self.config.rate_limit_wait_seconds
                    logger.info(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                else:
                    raise TwitterRateLimitError(
                        f"Rate limit exceeded after {self.config.max_retries} retries",
                        reset_time=reset_time
                    )
                    
            except tweepy.Unauthorized as e:
                logger.error(f"Twitter authentication failed: {e}")
                raise TwitterAuthError(f"Authentication failed: {e}")
                
            except tweepy.TwitterServerError as e:
                logger.error(f"Twitter server error: {e}")
                if retry < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay_seconds * (retry + 1))
                else:
                    raise TwitterNetworkError(f"Twitter server error after retries: {e}")
                    
            except tweepy.TweepyException as e:
                logger.error(f"Tweepy error: {e}")
                if retry < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    raise TwitterAPIError(f"Twitter API error: {e}")
                    
            except ConnectionError as e:
                logger.error(f"Network connection error: {e}")
                if retry < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay_seconds * (retry + 1))
                else:
                    raise TwitterNetworkError(f"Network error: {e}")
                    
            except Exception as e:
                logger.error(f"Unexpected error searching tweets: {e}")
                if retry < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    return all_tweets
        
        return all_tweets
    
    def stream_mentions(
        self,
        tickers: List[str],
        callback=None
    ) -> None:
        """
        Stream real-time mentions for given tickers.
        
        Note: Real-time streaming requires elevated Twitter API access
        and OAuth 1.0a authentication. This is a placeholder for future
        implementation when streaming access is available.
        
        Args:
            tickers: List of stock ticker symbols to monitor
            callback: Function to call for each new tweet
            
        Raises:
            NotImplementedError: Streaming is not yet implemented
        """
        raise NotImplementedError(
            "Real-time streaming requires Twitter API elevated access with OAuth 1.0a. "
            "Use search_event_tweets() for batch retrieval instead. "
            "To implement streaming, you need to:\n"
            "1. Apply for elevated Twitter API access\n"
            "2. Set up OAuth 1.0a credentials (api_key, api_secret, access_token, access_token_secret)\n"
            "3. Implement tweepy.StreamingClient with filtered stream rules"
        )
    
    def calculate_volume_baseline(
        self,
        ticker: str,
        lookback_days: int = 7
    ) -> Tuple[float, float]:
        """
        Calculate baseline tweet volume for a ticker using tweet counts API.
        
        Queries historical daily tweet counts to compute mean and standard
        deviation for z-score calculation.
        
        Args:
            ticker: Stock ticker symbol
            lookback_days: Number of days to look back (max 7 for basic API)
            
        Returns:
            Tuple of (mean_volume, std_volume) for z-score calculation
            Returns (0.0, 1.0) if API unavailable or error occurs
        """
        if not self.is_available():
            return (0.0, 1.0)
        
        lookback_days = min(lookback_days, 7)
        
        daily_counts = []
        end_time = datetime.utcnow()
        
        query = f"${ticker} -is:retweet lang:en"
        
        for retry in range(self.config.max_retries):
            try:
                start_time = end_time - timedelta(days=lookback_days)
                
                count_response = self.client.get_recent_tweets_count(
                    query=query,
                    start_time=start_time,
                    end_time=end_time,
                    granularity="day"
                )
                
                if count_response.data:
                    for day_data in count_response.data:
                        daily_counts.append(day_data.get("tweet_count", 0))
                
                break
                    
            except tweepy.TooManyRequests:
                logger.warning(f"Rate limit hit while getting tweet counts for {ticker}")
                if retry < self.config.max_retries - 1:
                    time.sleep(self.config.rate_limit_wait_seconds)
                else:
                    return (0.0, 1.0)
                    
            except tweepy.Unauthorized as e:
                logger.error(f"Auth error getting tweet counts: {e}")
                return (0.0, 1.0)
                
            except Exception as e:
                logger.warning(f"Error getting tweet count for {ticker}: {e}")
                if retry < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay_seconds)
                else:
                    return (0.0, 1.0)
        
        if not daily_counts:
            return (0.0, 1.0)
        
        try:
            import numpy as np
            mean_vol = float(np.mean(daily_counts))
            std_vol = float(np.std(daily_counts)) if len(daily_counts) > 1 else 1.0
            std_vol = std_vol if std_vol > 0 else 1.0
            
            logger.debug(f"Volume baseline for {ticker}: mean={mean_vol:.2f}, std={std_vol:.2f}")
            return (mean_vol, std_vol)
            
        except Exception as e:
            logger.error(f"Error calculating volume baseline: {e}")
            return (0.0, 1.0)
    
    def get_demo_tweets(
        self,
        ticker: str,
        event_type: str,
        count: int = 10
    ) -> List[TweetData]:
        """
        Generate demo tweet data when Twitter API is not configured.
        
        Generates realistic financial tweet patterns for testing the
        sentiment pipeline without real API access.
        
        Args:
            ticker: Stock ticker symbol
            event_type: Type of event
            count: Number of demo tweets to generate
            
        Returns:
            List of TweetData with realistic financial content
        """
        import random
        import hashlib
        
        base_sentiment_templates = [
            ("🚀 ${ticker} just crushed {event_type}! This is EXACTLY what we expected. Adding more.", 0.9, "bullish"),
            ("${ticker} {event_type} results look solid. Holding my position. 📈", 0.6, "bullish"),
            ("Interesting {event_type} from ${ticker}. Need to dig into the details before making a move.", 0.1, "neutral"),
            ("Not impressed with ${ticker} {event_type}. Numbers were weak. Trimming position. 📉", -0.5, "bearish"),
            ("${ticker} {event_type} was a complete disaster. Selling everything. 💀", -0.9, "bearish"),
            ("${ticker} looking strong heading into {event_type}. The technicals are lining up.", 0.5, "bullish"),
            ("Mixed feelings about ${ticker} {event_type}. Guidance was soft but numbers beat.", 0.2, "neutral"),
            ("${ticker} management crushed it on the call. {event_type} exceeded expectations!", 0.85, "bullish"),
            ("Bearish on ${ticker} after this {event_type}. Market is overreacting to the upside.", -0.4, "bearish"),
            ("${ticker} {event_type} in line with expectations. Nothing exciting here. Hold.", 0.0, "neutral"),
        ]
        
        event_specific_templates = {
            "earnings": [
                ("${ticker} Q3 earnings: EPS $2.45 vs $2.20 est. Revenue up 15% YoY. 🔥", 0.8, "bullish"),
                ("${ticker} missed EPS by $0.10. Revenue light too. Not good. 📉", -0.7, "bearish"),
                ("${ticker} earnings call starting in 30 min. Let's see what they say about guidance.", 0.1, "neutral"),
            ],
            "fda_approval": [
                ("BREAKING: ${ticker} receives FDA approval! This is huge for their pipeline. 🚀🚀", 0.95, "bullish"),
                ("${ticker} FDA approval finally came through. Years of waiting paid off! 💎", 0.85, "bullish"),
                ("${ticker} drug approved! PT raised to $150. Strong buy.", 0.9, "bullish"),
            ],
            "fda_rejection": [
                ("${ticker} receives CRL from FDA. Major setback for the company. 💀", -0.9, "bearish"),
                ("FDA rejected ${ticker}'s application. Stock down 40% AH. Brutal.", -0.95, "bearish"),
                ("${ticker} FDA rejection was unexpected. Need to reassess the thesis.", -0.6, "bearish"),
            ],
            "guidance_raise": [
                ("${ticker} raises full year guidance! Management is confident. 📈", 0.8, "bullish"),
                ("Love seeing ${ticker} raise guidance. They're executing.", 0.7, "bullish"),
            ],
            "guidance_lower": [
                ("${ticker} cuts guidance. Management blames macro. Classic. 📉", -0.7, "bearish"),
                ("Not surprised ${ticker} lowered guidance. The writing was on the wall.", -0.5, "bearish"),
            ],
            "merger_acquisition": [
                ("${ticker} acquisition announced at $45/share. Premium seems fair.", 0.5, "bullish"),
                ("${ticker} being acquired! This came out of nowhere. 🎯", 0.6, "bullish"),
            ],
            "analyst_upgrade": [
                ("Morgan Stanley upgrades ${ticker} to Overweight. PT $200. 📈", 0.7, "bullish"),
                ("${ticker} getting upgraded left and right. Wall Street finally catching on.", 0.6, "bullish"),
            ],
            "analyst_downgrade": [
                ("Goldman downgrades ${ticker} to Sell. PT cut to $50. 📉", -0.7, "bearish"),
                ("Another downgrade for ${ticker}. The analysts are piling on.", -0.5, "bearish"),
            ]
        }
        
        templates = base_sentiment_templates.copy()
        if event_type in event_specific_templates:
            templates.extend(event_specific_templates[event_type])
        
        username_prefixes = [
            "trader", "investor", "stock", "wall", "market", "quant",
            "alpha", "bull", "bear", "capital", "fin", "options"
        ]
        
        demo_tweets = []
        base_time = datetime.utcnow()
        
        seed = hashlib.md5(f"{ticker}{event_type}".encode()).hexdigest()
        random.seed(int(seed[:8], 16))
        
        for i in range(count):
            template, base_sentiment, category = random.choice(templates)
            text = template.replace("${ticker}", f"${ticker}").replace("{event_type}", event_type.replace("_", " "))
            
            sentiment_noise = random.gauss(0, 0.1)
            adjusted_sentiment = max(-1.0, min(1.0, base_sentiment + sentiment_noise))
            
            is_influencer = random.random() < 0.2
            if is_influencer:
                followers = random.randint(10000, 500000)
            else:
                followers = random.randint(50, 9999)
            
            time_offset = random.randint(0, 1440)
            created_at = base_time - timedelta(minutes=time_offset)
            
            engagement_base = 1 + (followers / 10000)
            likes = int(random.expovariate(1 / (50 * engagement_base)))
            retweets = int(random.expovariate(1 / (20 * engagement_base)))
            replies = int(random.expovariate(1 / (10 * engagement_base)))
            quotes = int(random.expovariate(1 / (5 * engagement_base)))
            
            username_prefix = random.choice(username_prefixes)
            username = f"{username_prefix}_{random.randint(100, 9999)}"
            
            tweet = TweetData(
                tweet_id=f"demo_{i}_{ticker}_{int(created_at.timestamp())}",
                text=text,
                author_id=f"demo_user_{i}_{random.randint(1000, 9999)}",
                author_username=username,
                author_followers=followers,
                created_at=created_at,
                retweet_count=retweets,
                like_count=likes,
                reply_count=replies,
                quote_count=quotes,
                ticker=ticker,
                event_keywords=[event_type]
            )
            demo_tweets.append(tweet)
        
        random.seed()
        
        demo_tweets.sort(key=lambda t: t.created_at, reverse=True)
        
        return demo_tweets
    
    def get_tweets_for_event(
        self,
        ticker: str,
        event_type: str,
        event_keywords: Optional[List[str]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        max_results: int = 100,
        use_demo: bool = False
    ) -> List[TweetData]:
        """
        High-level method to get tweets for an event, with automatic fallback.
        
        If Twitter API is not available or configured, automatically falls back
        to demo mode.
        
        Args:
            ticker: Stock ticker symbol
            event_type: Type of event
            event_keywords: Optional custom keywords
            start_time: Start of search window
            end_time: End of search window
            max_results: Maximum tweets to retrieve
            use_demo: Force demo mode even if API is available
            
        Returns:
            List of TweetData objects
        """
        if use_demo or not self.is_available():
            if not self.is_available():
                logger.info(f"Twitter API not available, using demo tweets for {ticker}/{event_type}")
            return self.get_demo_tweets(ticker, event_type, min(max_results, 50))
        
        try:
            tweets = self.search_event_tweets(
                ticker=ticker,
                event_type=event_type,
                event_keywords=event_keywords,
                start_time=start_time,
                end_time=end_time,
                max_results=max_results
            )
            
            if not tweets:
                logger.info(f"No tweets found via API for {ticker}/{event_type}, using demo fallback")
                return self.get_demo_tweets(ticker, event_type, min(max_results, 20))
            
            return tweets
            
        except TwitterAPIError as e:
            logger.warning(f"Twitter API error for {ticker}/{event_type}: {e}, falling back to demo")
            return self.get_demo_tweets(ticker, event_type, min(max_results, 20))
        except Exception as e:
            logger.error(f"Unexpected error getting tweets for {ticker}/{event_type}: {e}")
            return self.get_demo_tweets(ticker, event_type, min(max_results, 20))
