"""Event schemas"""
from pydantic import BaseModel
from typing import Optional, Union
from datetime import datetime


class EventBase(BaseModel):
    ticker: str
    title: str
    event_type: str
    description: Optional[str] = None
    date: Union[datetime, str]  # Accept both datetime and EST date string (YYYY-MM-DD)
    source_url: Optional[str] = None


class EventCreate(EventBase):
    pass


class EventResponse(EventBase):
    id: int
    impact_score: int
    direction: Optional[str] = None
    confidence: float
    rationale: Optional[str] = None
    company_name: str
    source: str
    bearish_signal: bool = False
    bearish_score: Optional[float] = None
    bearish_confidence: Optional[float] = None
    bearish_rationale: Optional[str] = None

    class Config:
        from_attributes = True


class EventDetail(EventResponse):
    sector: Optional[str] = None
    subsidiary_name: Optional[str] = None
    created_at: Optional[Union[datetime, str]] = None  # Accept both datetime and EST date string
    updated_at: Optional[Union[datetime, str]] = None  # Accept both datetime and EST date string
    beta: Optional[float] = None
    atr_percentile: Optional[float] = None
    market_regime: Optional[str] = None
    info_tier: str = "primary"
    info_subtype: Optional[str] = None
    context_risk_score: Optional[int] = None
    context_signals: Optional[list] = None
    impact_p_move: Optional[float] = None
    impact_p_up: Optional[float] = None
    impact_p_down: Optional[float] = None
    impact_score_version: Optional[int] = None
    ml_adjusted_score: Optional[int] = None
    model_source: Optional[str] = None
    ml_model_version: Optional[str] = None
    ml_confidence: Optional[float] = None
    delta_applied: Optional[float] = None


class ImpactScoreRequest(BaseModel):
    event_type: str
    title: str = ""
    description: str = ""
    sector: Optional[str] = None
    market_cap: Optional[str] = None
    metadata: Optional[dict] = None


class ImpactScoreResponse(BaseModel):
    impact_score: int
    direction: str
    confidence: float
    rationale: str
