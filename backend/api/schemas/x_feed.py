"""X.com Feed API Schemas"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class XPostSchema(BaseModel):
    """Schema for a single social media post from X.com"""
    id: str
    created_at: datetime
    text: str
    author_handle: str
    author_followers: int
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    symbols: List[str]
    url: str


class XPostAnalysisSchema(BaseModel):
    """Schema for post sentiment analysis"""
    sentiment: str
    strength: float
    event_hint: str
    confidence: float


class XEventClusterSchema(BaseModel):
    """Schema for a cluster of posts linked to an event"""
    event: Optional[dict] = None
    ticker: str
    sentiment_label: str
    sentiment_score: float
    confidence: float
    support_count: int
    posts: List[dict]


class XFeedResponse(BaseModel):
    """Response schema for X.com feed endpoint"""
    source_available: bool
    clusters: List[XEventClusterSchema]
