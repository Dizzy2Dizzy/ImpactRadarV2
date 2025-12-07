"""
X.com Event Linker for Impact Radar

Links social media posts to Impact Radar events based on timing,
ticker symbols, and event type hints. Computes aggregated sentiment.
"""

import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class XEventCluster:
    """
    Cluster of social media posts linked to an event (or orphaned posts by ticker).
    """
    event: Optional[Any]  # Event object or None if no matching event
    ticker: str
    posts: List[Any]  # List of SocialPost objects
    sentiment_summary: Dict[str, Any]  # Aggregated sentiment metrics


def link_posts_to_events(
    posts: List[Any],
    analyses: Dict[str, Any],
    events: List[Any],
    window_days: int = 3
) -> List[XEventCluster]:
    """
    Link social media posts to Impact Radar events and compute aggregated sentiment.
    
    Matching logic:
    1. For each post's ticker symbols, find events within time window
    2. Match event_type to post's event_hint when possible
    3. Group posts by (event, ticker) or (None, ticker) if no event
    4. Compute weighted sentiment for each cluster
    
    Args:
        posts: List of SocialPost objects
        analyses: Dict mapping post_id to PostAnalysis
        events: List of Event objects from database
        window_days: Time window for matching posts to events (default 3)
        
    Returns:
        List of XEventCluster objects with aggregated sentiment
    """
    from backend.social.x_client import SocialPost
    from backend.social.x_sentiment import PostAnalysis
    
    if not posts:
        return []
    
    # Build event index by (ticker, date_range)
    # For faster lookup: events_by_ticker[ticker] = list of events
    events_by_ticker: Dict[str, List[Any]] = defaultdict(list)
    for event in events:
        events_by_ticker[event.ticker].append(event)
    
    # Map event hints to event types for matching
    hint_to_type = {
        'earnings': ['earnings', 'guidance_raise', 'guidance_lower', 'guidance_withdraw'],
        'fda': ['fda_approval', 'fda_rejection', 'fda_adcom', 'fda_crl', 'fda_safety_alert', 'fda_announcement'],
        'guidance': ['guidance_raise', 'guidance_lower', 'guidance_withdraw'],
        'product': ['product_launch', 'product_delay', 'product_recall', 'flagship_launch'],
        'macro': [],  # Macro events don't match specific company events
        'other': []
    }
    
    # Cluster posts by (event_id, ticker) or (None, ticker)
    clusters: Dict[tuple, List[SocialPost]] = defaultdict(list)
    
    for post in posts:
        analysis = analyses.get(post.id)
        if not analysis:
            continue
        
        # Try to match post to events for each ticker mentioned
        matched = False
        
        for ticker in post.symbols:
            ticker_events = events_by_ticker.get(ticker, [])
            
            # Find events within time window
            for event in ticker_events:
                time_diff = abs((post.created_at - event.date).total_seconds()) / 86400  # days
                
                if time_diff <= window_days:
                    # Check if event_hint matches event_type
                    matching_types = hint_to_type.get(analysis.event_hint, [])
                    
                    if not matching_types or event.event_type in matching_types:
                        # Match found
                        cluster_key = (event.id, ticker)
                        clusters[cluster_key].append(post)
                        matched = True
                        break
            
            if matched:
                break
        
        # If no event match, create orphan cluster by ticker
        if not matched:
            for ticker in post.symbols:
                cluster_key = (None, ticker)
                clusters[cluster_key].append(post)
    
    # Build XEventCluster objects with aggregated sentiment
    result = []
    
    for (event_id, ticker), cluster_posts in clusters.items():
        # Find the event object (if exists)
        event_obj = None
        if event_id:
            for e in events:
                if e.id == event_id:
                    event_obj = e
                    break
        
        # Compute aggregated sentiment
        sentiment_summary = compute_aggregated_sentiment(cluster_posts, analyses)
        
        cluster = XEventCluster(
            event=event_obj,
            ticker=ticker,
            posts=cluster_posts,
            sentiment_summary=sentiment_summary
        )
        
        result.append(cluster)
    
    logger.info(f"Created {len(result)} event clusters from {len(posts)} posts")
    return result


def compute_aggregated_sentiment(
    posts: List[Any],
    analyses: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Compute aggregated sentiment for a cluster of posts.
    
    Weighting factors:
    - Author followers: log(1 + followers)
    - Engagement: likes + retweets + replies + quotes
    - Sentiment strength: from PostAnalysis
    
    Args:
        posts: List of SocialPost objects
        analyses: Dict mapping post_id to PostAnalysis
        
    Returns:
        Dict with:
        - sentiment_score: float in [-1, +1] (bullish=+1, bearish=-1)
        - sentiment_label: 'bullish', 'bearish', 'mixed', or 'neutral'
        - confidence: float in [0, 1]
        - support_count: number of posts
    """
    from backend.social.x_client import SocialPost
    from backend.social.x_sentiment import PostAnalysis
    
    if not posts:
        return {
            'sentiment_score': 0.0,
            'sentiment_label': 'neutral',
            'confidence': 0.0,
            'support_count': 0
        }
    
    # Calculate weighted sentiment scores
    total_weight = 0.0
    weighted_sentiment = 0.0
    
    sentiment_counts = {'bullish': 0, 'bearish': 0, 'neutral': 0}
    author_handles = set()
    
    for post in posts:
        analysis = analyses.get(post.id)
        if not analysis:
            continue
        
        # Track sentiment distribution
        sentiment_counts[analysis.sentiment] += 1
        author_handles.add(post.author_handle)
        
        # Calculate weight for this post
        follower_weight = math.log(1 + post.author_followers)
        engagement = post.like_count + post.retweet_count + post.reply_count + post.quote_count
        engagement_weight = math.log(1 + engagement)
        
        weight = follower_weight * engagement_weight * analysis.confidence
        
        # Convert sentiment to numeric score
        if analysis.sentiment == 'bullish':
            score = analysis.strength
        elif analysis.sentiment == 'bearish':
            score = -analysis.strength
        else:
            score = 0.0
        
        weighted_sentiment += score * weight
        total_weight += weight
    
    # Calculate final sentiment score
    if total_weight > 0:
        sentiment_score = weighted_sentiment / total_weight
    else:
        sentiment_score = 0.0
    
    # Determine sentiment label
    if sentiment_score > 0.3:
        sentiment_label = 'bullish'
    elif sentiment_score < -0.3:
        sentiment_label = 'bearish'
    elif abs(sentiment_score) > 0.1:
        sentiment_label = 'mixed'
    else:
        sentiment_label = 'neutral'
    
    # Calculate confidence based on:
    # 1. Number of posts (more posts = higher confidence)
    # 2. Author diversity (more unique authors = higher confidence)
    # 3. Sentiment agreement (more agreement = higher confidence)
    
    post_count_factor = min(len(posts) / 10.0, 1.0)  # 10+ posts = max
    author_diversity_factor = min(len(author_handles) / 5.0, 1.0)  # 5+ authors = max
    
    # Agreement: What % of posts agree with the final label?
    if sentiment_label in sentiment_counts:
        agreement_factor = sentiment_counts[sentiment_label] / len(posts)
    else:
        agreement_factor = 0.5
    
    confidence = (post_count_factor + author_diversity_factor + agreement_factor) / 3.0
    
    return {
        'sentiment_score': round(sentiment_score, 3),
        'sentiment_label': sentiment_label,
        'confidence': round(confidence, 3),
        'support_count': len(posts)
    }
