"""Company schemas"""
from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class CompanyBase(BaseModel):
    ticker: str
    name: str
    sector: Optional[str] = None
    industry: Optional[str] = None
    parent_id: Optional[int] = None
    tracked: bool = True


class CompanyCreate(CompanyBase):
    pass


class CompanyResponse(CompanyBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    event_count: Optional[int] = None

    class Config:
        from_attributes = True


class CompanyDetail(CompanyResponse):
    upcoming_events: list = []
    price_data: Optional[dict] = None
