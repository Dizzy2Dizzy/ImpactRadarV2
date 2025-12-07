"""Scanner schemas"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ScannerStatus(BaseModel):
    scanner: str
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    message: Optional[str] = None
    level: str
    discoveries: int = 0


class ScannerRun(BaseModel):
    source: str


class Discovery(BaseModel):
    id: int
    ticker: str
    title: str
    event_type: str
    event_time: datetime
    score: int
    direction: str
    source: str
    created_at: datetime

    class Config:
        from_attributes = True
