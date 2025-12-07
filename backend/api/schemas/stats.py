"""
Stats API response schemas.

Provides historical event impact statistics for Pro+ users.
"""

from typing import Optional
from pydantic import BaseModel, Field


class HistoricalStatsResponse(BaseModel):
    """
    Historical event impact statistics.
    
    Shows win rate, average moves, and sample size for a specific
    ticker and event type combination based on backtesting data.
    """
    ticker: str = Field(description="Stock ticker symbol")
    event_type: str = Field(description="Event type (e.g., earnings, fda_approval)")
    sample_size: int = Field(description="Number of historical events in sample")
    win_rate: Optional[float] = Field(None, description="Percentage of positive moves (0-100)")
    
    # Absolute average moves (always positive)
    avg_abs_move_1d: Optional[float] = Field(None, description="Average absolute 1-day move (%)")
    avg_abs_move_5d: Optional[float] = Field(None, description="Average absolute 5-day move (%)")
    avg_abs_move_20d: Optional[float] = Field(None, description="Average absolute 20-day move (%)")
    
    # Mean moves (signed, can be negative)
    mean_move_1d: Optional[float] = Field(None, description="Mean 1-day move (%)")
    mean_move_5d: Optional[float] = Field(None, description="Mean 5-day move (%)")
    mean_move_20d: Optional[float] = Field(None, description="Mean 20-day move (%)")
    
    methodology: str = Field(
        default="Based on historical price movements following similar events",
        description="How stats were calculated"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "ticker": "AAPL",
                "event_type": "earnings",
                "sample_size": 12,
                "win_rate": 58.3,
                "avg_abs_move_1d": 2.4,
                "avg_abs_move_5d": 3.1,
                "avg_abs_move_20d": 4.2,
                "mean_move_1d": 1.2,
                "mean_move_5d": 1.8,
                "mean_move_20d": 2.1,
                "methodology": "Based on historical price movements following similar events"
            }
        }
