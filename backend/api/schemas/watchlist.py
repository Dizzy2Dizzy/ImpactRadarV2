"""Watchlist schemas"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class WatchlistAdd(BaseModel):
    company_id: int
    notes: Optional[str] = None


class WatchlistResponse(BaseModel):
    id: int
    user_id: int
    company_id: int
    ticker: str
    company_name: str
    sector: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    upcoming_events: list = []

    class Config:
        from_attributes = True
