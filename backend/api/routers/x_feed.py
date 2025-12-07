"""X.com Feed Router"""
from fastapi import APIRouter, Depends, Request, HTTPException, status
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from api.schemas.x_feed import XFeedResponse, XEventClusterSchema
from api.utils.auth import get_current_user
from api.schemas.auth import TokenData
from api.ratelimit import limiter, plan_limit
from database import WatchlistItem, Event, get_db, close_db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["x_feed"])


@router.get(
    "/x-feed",
    response_model=XFeedResponse,
    responses={
        200: {"description": "X.com feed data with sentiment analysis"},
        401: {"description": "Unauthorized - Invalid or missing JWT token"},
        429: {"description": "Rate limit exceeded"},
        500: {"description": "Internal server error"},
    },
    summary="Get X.com social sentiment feed",
    description="Retrieve social media posts from X.com (Twitter) for specified tickers with sentiment analysis and event linking. Requires JWT authentication."
)
@limiter.limit(plan_limit)
async def get_x_feed(
    request: Request,
    tickers: Optional[str] = None,
    days: int = 7,
    sentiment_filter: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get X.com social sentiment feed with event linking.
    
    Args:
        tickers: Comma-separated list of ticker symbols (e.g., "AAPL,TSLA"). If not provided, uses user's watchlist.
        days: Number of days to look back (default: 7, max: 30)
        sentiment_filter: Optional filter by sentiment: "bullish", "bearish", or "neutral"
        current_user: Authenticated user data (JWT required)
    
    Returns:
        XFeedResponse with source_available flag and event clusters with sentiment
    """
    from backend.social.x_client import fetch_posts_for_tickers
    from backend.social.x_sentiment import analyze_posts
    from backend.social.x_event_linker import link_posts_to_events
    
    logger.info(f"X feed request from user_id={current_user.user_id}, tickers={tickers}, days={days}")
    
    # Validate days parameter
    if days < 1 or days > 30:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="days parameter must be between 1 and 30"
        )
    
    # Parse tickers or fetch from watchlist
    ticker_list: List[str] = []
    
    if tickers:
        ticker_list = [t.strip().upper() for t in tickers.split(",")]
    else:
        db = get_db()
        try:
            watchlist_items = db.query(WatchlistItem).filter(
                WatchlistItem.user_id == current_user.user_id
            ).all()
            
            ticker_list = [str(item.ticker) for item in watchlist_items]
            
            if not ticker_list:
                logger.warning(f"User {current_user.user_id} has empty watchlist")
                return XFeedResponse(
                    source_available=True,
                    clusters=[]
                )
        finally:
            close_db_session(db)
    
    if not ticker_list:
        logger.warning("No tickers provided and watchlist is empty")
        return XFeedResponse(
            source_available=True,
            clusters=[]
        )
    
    logger.info(f"Fetching X posts for tickers: {ticker_list}")
    
    # Calculate date range
    until = datetime.utcnow()
    since = until - timedelta(days=days)
    
    try:
        posts, source_available = fetch_posts_for_tickers(
            tickers=ticker_list,
            since=since,
            until=until,
            max_results=100
        )
        
        if not source_available:
            logger.warning("X.com API credentials not configured")
            return XFeedResponse(
                source_available=False,
                clusters=[]
            )
        
        if not posts:
            logger.info("No posts found for the given tickers and timeframe")
            return XFeedResponse(
                source_available=True,
                clusters=[]
            )
        
        logger.info(f"Fetched {len(posts)} posts from X.com")
        
        analyses = analyze_posts(posts)
        logger.info(f"Analyzed {len(analyses)} posts for sentiment")
        
        db = get_db()
        try:
            events = db.query(Event).filter(
                Event.ticker.in_(ticker_list),
                Event.date >= since,
                Event.date <= until
            ).all()
            
            logger.info(f"Found {len(events)} events for linking")
        finally:
            close_db_session(db)
        
        clusters = link_posts_to_events(
            posts=posts,
            analyses=analyses,
            events=events,
            window_days=3
        )
        
        logger.info(f"Created {len(clusters)} event clusters")
        
        cluster_schemas = []
        for cluster in clusters:
            event_dict = None
            if cluster.event:
                event_dict = {
                    "id": cluster.event.id,
                    "ticker": cluster.event.ticker,
                    "event_type": cluster.event.event_type,
                    "title": cluster.event.title,
                    "date": cluster.event.date.isoformat(),
                    "impact_score": cluster.event.impact_score,
                    "direction": cluster.event.direction
                }
            
            post_dicts = []
            for post in cluster.posts:
                post_dict = {
                    "id": post.id,
                    "created_at": post.created_at.isoformat(),
                    "text": post.text,
                    "author_handle": post.author_handle,
                    "author_followers": post.author_followers,
                    "like_count": post.like_count,
                    "retweet_count": post.retweet_count,
                    "reply_count": post.reply_count,
                    "quote_count": post.quote_count,
                    "symbols": post.symbols,
                    "url": post.url
                }
                
                analysis = analyses.get(post.id)
                if analysis:
                    post_dict["analysis"] = {
                        "sentiment": analysis.sentiment,
                        "strength": analysis.strength,
                        "event_hint": analysis.event_hint,
                        "confidence": analysis.confidence
                    }
                
                post_dicts.append(post_dict)
            
            if sentiment_filter:
                if cluster.sentiment_summary['sentiment_label'] != sentiment_filter.lower():
                    continue
            
            cluster_schema = XEventClusterSchema(
                event=event_dict,
                ticker=cluster.ticker,
                sentiment_label=cluster.sentiment_summary['sentiment_label'],
                sentiment_score=cluster.sentiment_summary['sentiment_score'],
                confidence=cluster.sentiment_summary['confidence'],
                support_count=cluster.sentiment_summary['support_count'],
                posts=post_dicts
            )
            cluster_schemas.append(cluster_schema)
        
        return XFeedResponse(
            source_available=True,
            clusters=cluster_schemas
        )
        
    except HTTPException:
        raise
        
    except Exception as e:
        logger.exception(f"Error processing X feed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the X.com feed"
        )
