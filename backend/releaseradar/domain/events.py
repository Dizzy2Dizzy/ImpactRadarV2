"""
Domain models for events with Pydantic validation and deduplication logic.

This module contains pure data models without database or external dependencies.
"""

import hashlib
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator, ConfigDict


# Valid event types (must match scoring.py EVENT_TYPE_SCORES)
VALID_EVENT_TYPES = {
    # FDA Events
    "fda_approval",
    "fda_rejection",
    "fda_adcom",
    "fda_crl",
    "fda_safety_alert",
    "fda_announcement",
    # SEC Filings
    "sec_8k",
    "sec_10k",
    "sec_10q",
    "sec_s1",
    "sec_13d",
    "sec_13g",
    "sec_def14a",
    "sec_filing",
    # Earnings & Guidance
    "earnings",
    "guidance_raise",
    "guidance_lower",
    "guidance_withdraw",
    # Corporate Actions
    "merger_acquisition",
    "divestiture",
    "restructuring",
    "investigation",
    "lawsuit",
    "executive_change",
    # Product Events
    "product_launch",
    "product_delay",
    "product_recall",
    "flagship_launch",
    # Other
    "analyst_day",
    "conference_presentation",
    "press_release",
    "manual_entry",
}


class EventInput(BaseModel):
    """Input model for creating new events (from scanners or manual entry)."""
    
    model_config = ConfigDict(str_strip_whitespace=True)
    
    ticker: str = Field(..., min_length=1, max_length=10)
    company_name: str = Field(..., min_length=1, max_length=200)
    event_type: str = Field(...)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = Field(None, max_length=5000)
    date: datetime = Field(...)
    source: str = Field(..., min_length=1, max_length=100)
    source_url: Optional[str] = Field(None, max_length=1000)
    subsidiary_name: Optional[str] = Field(None, max_length=200)
    sector: Optional[str] = Field(None, max_length=100)
    
    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, v: str) -> str:
        """Validate event type is in allowed list."""
        v_lower = v.lower()
        if v_lower not in VALID_EVENT_TYPES:
            raise ValueError(
                f"Invalid event_type '{v}'. Must be one of: {sorted(VALID_EVENT_TYPES)}"
            )
        return v_lower
    
    @field_validator("ticker")
    @classmethod
    def validate_ticker(cls, v: str) -> str:
        """Normalize ticker to uppercase."""
        return v.upper()
    
    def dedupe_key(self) -> str:
        """
        Generate a deduplication key (hash) for this event.
        
        Events with the same ticker, event_type, title, and date are considered duplicates.
        
        Returns:
            SHA-256 hash of the event's unique characteristics
        """
        content = f"{self.ticker}|{self.event_type}|{self.title}|{self.date.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class EventRecord(BaseModel):
    """Complete event record including scoring and metadata (from database)."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    ticker: str
    company_name: str
    event_type: str
    title: str
    description: Optional[str] = None
    date: datetime
    source: str
    source_url: Optional[str] = None
    impact_score: int = Field(50, ge=0, le=100)
    direction: Optional[str] = Field(None, pattern="^(positive|negative|neutral|uncertain)$")
    confidence: float = Field(0.5, ge=0.0, le=1.0)
    rationale: Optional[str] = None
    subsidiary_name: Optional[str] = None
    sector: Optional[str] = None
    created_at: datetime
    
    @property
    def impact_color(self) -> str:
        """Get color code for impact score visualization."""
        if self.impact_score >= 80:
            return "red"
        elif self.impact_score >= 60:
            return "orange"
        elif self.impact_score >= 40:
            return "yellow"
        else:
            return "green"
    
    @property
    def direction_emoji(self) -> str:
        """Get emoji for event direction."""
        direction_map = {
            "positive": "📈",
            "negative": "📉",
            "neutral": "➡️",
            "uncertain": "❓",
        }
        return direction_map.get(self.direction, "➡️")


class ScoringResult(BaseModel):
    """Result of event impact scoring."""
    
    impact_score: int = Field(..., ge=0, le=100)
    direction: str = Field(..., pattern="^(positive|negative|neutral|uncertain)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    rationale: str


def merge_events(existing: EventRecord, new: EventInput, new_score: ScoringResult) -> dict:
    """
    Merge a new event with an existing duplicate, keeping the most recent data.
    
    Args:
        existing: Existing event record from database
        new: New event input
        new_score: Scoring result for new event
        
    Returns:
        Dictionary of fields to update in the existing event
    """
    updates = {}
    
    # Update if new event has more detail
    if new.description and len(new.description) > len(existing.description or ""):
        updates["description"] = new.description
    
    # Update source_url if missing
    if new.source_url and not existing.source_url:
        updates["source_url"] = new.source_url
    
    # Update scoring if new score is higher
    if new_score.impact_score > existing.impact_score:
        updates["impact_score"] = new_score.impact_score
        updates["direction"] = new_score.direction
        updates["confidence"] = new_score.confidence
        updates["rationale"] = new_score.rationale
    
    return updates
