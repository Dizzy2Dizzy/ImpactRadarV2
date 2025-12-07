"""Portfolio schemas"""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import date, datetime


class Position(BaseModel):
    ticker: str
    quantity: int
    cost_basis: float


class PortfolioEstimateRequest(BaseModel):
    positions: list[Position]
    events_window: int = 30  # days


class PositionImpact(BaseModel):
    ticker: str
    quantity: int
    cost_basis: float
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    upcoming_events: int
    risk_score: int
    estimated_impact: str


class PortfolioEstimateResponse(BaseModel):
    positions: list[PositionImpact]
    total_value: float
    total_pnl: float
    risk_summary: dict


# Wave D: Portfolio Upload & Insights

class UploadPositionRow(BaseModel):
    """Single position row from CSV upload"""
    ticker: str
    qty: float
    avg_price: float
    as_of: date
    label: Optional[str] = None
    
    @field_validator('ticker')
    @classmethod
    def normalize_ticker(cls, v: str) -> str:
        """Normalize ticker to uppercase and strip whitespace"""
        return v.strip().upper()


class UploadError(BaseModel):
    """Error for a specific row in upload"""
    row: int
    field: str
    message: str


class UploadResponse(BaseModel):
    """Response from portfolio upload"""
    success: bool
    positions_count: int
    errors: List[UploadError] = []
    portfolio_id: Optional[int] = None


class CSVUploadResponse(BaseModel):
    """Response from CSV upload matching spec"""
    portfolio_id: int
    holdings_count: int
    tickers: List[str]


class InsightEvent(BaseModel):
    """Event details for portfolio insights"""
    event_id: int
    event_type: str
    title: str
    date: datetime
    days_until: int
    score: Optional[int] = None
    confidence: Optional[float] = None
    direction: Optional[str] = None
    typical_move_1d: Optional[float] = None
    typical_move_5d: Optional[float] = None
    typical_move_20d: Optional[float] = None
    source_url: Optional[str] = None


class PositionInsight(BaseModel):
    """Insight for a single portfolio position"""
    ticker: str
    qty: float
    avg_price: float
    current_price: Optional[float] = None
    position_value: Optional[float] = None
    upcoming_events: List[InsightEvent] = []
    total_exposure_1d: Optional[float] = None  # Sum of abs(expected_move * qty * price)


class InsightsResponse(BaseModel):
    """Response from portfolio insights endpoint"""
    portfolio_id: int
    portfolio_name: str
    window_days: int
    positions: List[PositionInsight]
    total_portfolio_value: float
    total_exposure_1d: float


class PortfolioResponse(BaseModel):
    """Response for portfolio details"""
    id: int
    name: str
    created_at: datetime
    positions_count: int


class HoldingResponse(BaseModel):
    """Individual holding response matching spec"""
    ticker: str
    company_name: Optional[str] = None
    shares: float
    cost_basis: Optional[float] = None
    current_price: Optional[float] = None
    market_value: Optional[float] = None
    gain_loss: Optional[float] = None
    sector: Optional[str] = None
    label: Optional[str] = None


class PortfolioInsightResponse(BaseModel):
    """Insight response for a single position matching spec"""
    ticker: str
    shares: float
    market_value: float
    upcoming_events_count: int
    total_risk_score: float
    exposure_1d: float
    exposure_5d: float
    exposure_20d: float
    events: List[dict]
