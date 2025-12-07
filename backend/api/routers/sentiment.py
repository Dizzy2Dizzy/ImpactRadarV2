"""
Social Sentiment API Router

Endpoints for Twitter/X sentiment analysis and social signals.
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_

from database import get_db, close_db_session
from releaseradar.db.models import SocialEventSignal as SocialEventSignalModel, Event
from releaseradar.social import TwitterSentimentIngestor, SentimentAnalyzer, TwitterConfig
from api.utils.auth import get_current_user_with_plan
from api.utils.paywall import require_plan
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sentiment", tags=["sentiment"])


class SocialSignalResponse(BaseModel):
    """Response model for social event signals"""
    id: int
    event_id: int
    ticker: str
    event_type: Optional[str]
    tweet_count: int
    unique_authors: int
    avg_sentiment: float
    sentiment_std: Optional[float]
    positive_ratio: Optional[float]
    negative_ratio: Optional[float]
    neutral_ratio: Optional[float]
    total_engagement: Optional[float]
    influencer_count: Optional[int]
    influencer_sentiment: Optional[float]
    volume_zscore: Optional[float]
    peak_hour: Optional[int]
    tweet_velocity: Optional[float]
    sample_tweets: Optional[List[Dict[str, Any]]]
    created_at: datetime
    
    class Config:
        from_attributes = True


class SentimentSummaryResponse(BaseModel):
    """Summary of sentiment analysis across events"""
    total_signals: int
    avg_sentiment: float
    positive_events: int
    negative_events: int
    neutral_events: int
    top_positive: List[Dict[str, Any]]
    top_negative: List[Dict[str, Any]]
    high_volume_events: List[Dict[str, Any]]


class TwitterStatusResponse(BaseModel):
    """Status of Twitter API integration"""
    configured: bool
    available: bool
    message: str


class AnalyzeTweetsRequest(BaseModel):
    """Request to analyze tweets for an event"""
    event_id: int = Field(..., description="Event ID to analyze")
    max_tweets: int = Field(100, ge=10, le=500, description="Maximum tweets to fetch")


class SentimentFeaturesResponse(BaseModel):
    """Sentiment features for ML integration"""
    event_id: int
    ticker: str
    features: Dict[str, float]


@router.get(
    "/status",
    response_model=TwitterStatusResponse,
    summary="Check Twitter API status",
    description="Check if Twitter API is configured and available"
)
async def get_twitter_status(
    user_data: dict = Depends(get_current_user_with_plan)
):
    """Check Twitter API integration status"""
    config = TwitterConfig.from_env()
    ingestor = TwitterSentimentIngestor(config)
    
    if not config.is_configured():
        return TwitterStatusResponse(
            configured=False,
            available=False,
            message="Twitter API credentials not configured. Add TWITTER_BEARER_TOKEN to secrets."
        )
    
    if ingestor.is_available():
        return TwitterStatusResponse(
            configured=True,
            available=True,
            message="Twitter API is configured and ready"
        )
    else:
        return TwitterStatusResponse(
            configured=True,
            available=False,
            message="Twitter API credentials configured but connection failed"
        )


@router.get(
    "/event/{event_id}",
    response_model=SocialSignalResponse,
    summary="Get sentiment for an event",
    description="Get aggregated social sentiment signal for a specific event"
)
async def get_event_sentiment(
    event_id: int,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Get social sentiment for a specific event"""
    require_plan(
        user_data["plan"],
        "pro",
        "Social sentiment",
        user_data.get("trial_ends_at")
    )
    
    try:
        signal = db.query(SocialEventSignalModel).filter(
            SocialEventSignalModel.event_id == event_id
        ).first()
        
        if not signal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No sentiment data for event {event_id}"
            )
        
        return SocialSignalResponse.from_orm(signal)
        
    finally:
        close_db_session(db)


@router.get(
    "/ticker/{ticker}",
    response_model=List[SocialSignalResponse],
    summary="Get sentiment history for a ticker",
    description="Get social sentiment signals for all events of a ticker"
)
async def get_ticker_sentiment(
    ticker: str,
    limit: int = Query(50, ge=1, le=200),
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Get sentiment history for a ticker"""
    require_plan(
        user_data["plan"],
        "pro",
        "Social sentiment",
        user_data.get("trial_ends_at")
    )
    
    try:
        signals = db.query(SocialEventSignalModel).filter(
            SocialEventSignalModel.ticker == ticker.upper()
        ).order_by(desc(SocialEventSignalModel.created_at)).limit(limit).all()
        
        return [SocialSignalResponse.from_orm(s) for s in signals]
        
    finally:
        close_db_session(db)


@router.get(
    "/summary",
    response_model=SentimentSummaryResponse,
    summary="Get sentiment summary",
    description="Get summary of sentiment analysis across all events"
)
async def get_sentiment_summary(
    days: int = Query(7, ge=1, le=90, description="Number of days to analyze"),
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Get overall sentiment summary"""
    require_plan(
        user_data["plan"],
        "pro",
        "Social sentiment",
        user_data.get("trial_ends_at")
    )
    
    try:
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        signals = db.query(SocialEventSignalModel).filter(
            SocialEventSignalModel.created_at >= cutoff
        ).all()
        
        if not signals:
            return SentimentSummaryResponse(
                total_signals=0,
                avg_sentiment=0.0,
                positive_events=0,
                negative_events=0,
                neutral_events=0,
                top_positive=[],
                top_negative=[],
                high_volume_events=[]
            )
        
        positive = [s for s in signals if s.avg_sentiment > 0.15]
        negative = [s for s in signals if s.avg_sentiment < -0.15]
        neutral = [s for s in signals if -0.15 <= s.avg_sentiment <= 0.15]
        
        sorted_by_sentiment = sorted(signals, key=lambda s: s.avg_sentiment, reverse=True)
        sorted_by_volume = sorted(signals, key=lambda s: s.volume_zscore or 0, reverse=True)
        
        def signal_to_dict(s):
            return {
                "event_id": s.event_id,
                "ticker": s.ticker,
                "sentiment": s.avg_sentiment,
                "tweet_count": s.tweet_count,
                "volume_zscore": s.volume_zscore
            }
        
        return SentimentSummaryResponse(
            total_signals=len(signals),
            avg_sentiment=sum(s.avg_sentiment for s in signals) / len(signals),
            positive_events=len(positive),
            negative_events=len(negative),
            neutral_events=len(neutral),
            top_positive=[signal_to_dict(s) for s in sorted_by_sentiment[:5]],
            top_negative=[signal_to_dict(s) for s in sorted_by_sentiment[-5:]],
            high_volume_events=[signal_to_dict(s) for s in sorted_by_volume[:5]]
        )
        
    finally:
        close_db_session(db)


@router.post(
    "/analyze",
    response_model=SocialSignalResponse,
    summary="Analyze tweets for an event",
    description="Fetch and analyze tweets for a specific event (requires Twitter API)"
)
async def analyze_event_tweets(
    request: AnalyzeTweetsRequest,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Analyze tweets for an event"""
    require_plan(
        user_data["plan"],
        "pro",
        "Social sentiment analysis",
        user_data.get("trial_ends_at")
    )
    
    try:
        event = db.query(Event).filter(Event.id == request.event_id).first()
        if not event:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Event {request.event_id} not found"
            )
        
        config = TwitterConfig.from_env()
        ingestor = TwitterSentimentIngestor(config)
        analyzer = SentimentAnalyzer()
        
        if ingestor.is_available():
            tweets = ingestor.search_event_tweets(
                ticker=event.ticker,
                event_type=event.event_type,
                max_results=request.max_tweets
            )
        else:
            tweets = ingestor.get_demo_tweets(
                ticker=event.ticker,
                event_type=event.event_type,
                count=min(request.max_tweets, 20)
            )
        
        volume_baseline = ingestor.calculate_volume_baseline(event.ticker) if ingestor.is_available() else (0, 1)
        
        signal_data = analyzer.aggregate_sentiment(
            tweets=tweets,
            event_id=event.id,
            ticker=event.ticker,
            event_type=event.event_type,
            volume_baseline=volume_baseline
        )
        
        existing = db.query(SocialEventSignalModel).filter(
            SocialEventSignalModel.event_id == event.id
        ).first()
        
        if existing:
            existing.tweet_count = signal_data.tweet_count
            existing.unique_authors = signal_data.unique_authors
            existing.avg_sentiment = signal_data.avg_sentiment
            existing.sentiment_std = signal_data.sentiment_std
            existing.positive_ratio = signal_data.positive_ratio
            existing.negative_ratio = signal_data.negative_ratio
            existing.neutral_ratio = signal_data.neutral_ratio
            existing.total_engagement = signal_data.total_engagement
            existing.influencer_count = signal_data.influencer_count
            existing.influencer_sentiment = signal_data.influencer_sentiment
            existing.volume_zscore = signal_data.volume_zscore
            existing.peak_hour = signal_data.peak_hour
            existing.tweet_velocity = signal_data.tweet_velocity
            existing.sample_tweets = signal_data.sample_tweets
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return SocialSignalResponse.from_orm(existing)
        else:
            new_signal = SocialEventSignalModel(
                event_id=event.id,
                ticker=event.ticker,
                event_type=event.event_type,
                tweet_count=signal_data.tweet_count,
                unique_authors=signal_data.unique_authors,
                avg_sentiment=signal_data.avg_sentiment,
                sentiment_std=signal_data.sentiment_std,
                positive_ratio=signal_data.positive_ratio,
                negative_ratio=signal_data.negative_ratio,
                neutral_ratio=signal_data.neutral_ratio,
                total_engagement=signal_data.total_engagement,
                influencer_count=signal_data.influencer_count,
                influencer_sentiment=signal_data.influencer_sentiment,
                volume_zscore=signal_data.volume_zscore,
                peak_hour=signal_data.peak_hour,
                tweet_velocity=signal_data.tweet_velocity,
                sample_tweets=signal_data.sample_tweets
            )
            db.add(new_signal)
            db.commit()
            db.refresh(new_signal)
            return SocialSignalResponse.from_orm(new_signal)
        
    finally:
        close_db_session(db)


@router.get(
    "/features/{event_id}",
    response_model=SentimentFeaturesResponse,
    summary="Get sentiment features for ML",
    description="Get sentiment features formatted for ML model input"
)
async def get_sentiment_features(
    event_id: int,
    user_data: dict = Depends(get_current_user_with_plan),
    db: Session = Depends(get_db)
):
    """Get sentiment features for ML integration"""
    require_plan(
        user_data["plan"],
        "pro",
        "Sentiment features",
        user_data.get("trial_ends_at")
    )
    
    try:
        signal = db.query(SocialEventSignalModel).filter(
            SocialEventSignalModel.event_id == event_id
        ).first()
        
        if not signal:
            return SentimentFeaturesResponse(
                event_id=event_id,
                ticker="",
                features={
                    "social_tweet_count": 0,
                    "social_unique_authors": 0,
                    "social_avg_sentiment": 0.0,
                    "social_sentiment_std": 0.0,
                    "social_positive_ratio": 0.0,
                    "social_negative_ratio": 0.0,
                    "social_engagement": 0.0,
                    "social_influencer_count": 0,
                    "social_influencer_sentiment": 0.0,
                    "social_volume_zscore": 0.0,
                    "social_velocity": 0.0
                }
            )
        
        import numpy as np
        
        features = {
            "social_tweet_count": signal.tweet_count,
            "social_unique_authors": signal.unique_authors,
            "social_avg_sentiment": signal.avg_sentiment,
            "social_sentiment_std": signal.sentiment_std or 0.0,
            "social_positive_ratio": signal.positive_ratio or 0.0,
            "social_negative_ratio": signal.negative_ratio or 0.0,
            "social_engagement": min(signal.total_engagement or 0, 10000) / 10000,
            "social_influencer_count": signal.influencer_count or 0,
            "social_influencer_sentiment": signal.influencer_sentiment or 0.0,
            "social_volume_zscore": np.clip(signal.volume_zscore or 0, -5, 5),
            "social_velocity": min(signal.tweet_velocity or 0, 100) / 100
        }
        
        return SentimentFeaturesResponse(
            event_id=event_id,
            ticker=signal.ticker,
            features=features
        )
        
    finally:
        close_db_session(db)
