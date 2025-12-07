"""
Label filtering utilities for ML training data preparation.

Implements overlap detection to filter out events with confounding nearby events
for the same ticker, which would result in noisy training labels where price
movements could be attributed to multiple catalysts.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, cast

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from releaseradar.db.models import Event
from releaseradar.log_config import logger


OVERLAP_WINDOW_CALENDAR_DAYS = 3
HIGH_IMPACT_THRESHOLD = 60


class OverlapResult:
    """Result of overlap detection for a single event."""
    
    def __init__(
        self,
        has_overlap: bool,
        overlap_count: int,
        nearby_event_ids: List[int],
        overlap_window_days: int,
        high_impact_overlap_count: int = 0,
        high_impact_event_ids: Optional[List[int]] = None
    ):
        self.has_overlap = has_overlap
        self.overlap_count = overlap_count
        self.nearby_event_ids = nearby_event_ids
        self.overlap_window_days = overlap_window_days
        self.high_impact_overlap_count = high_impact_overlap_count
        self.high_impact_event_ids = high_impact_event_ids or []
    
    def to_dict(self) -> Dict:
        """Convert to dictionary representation."""
        return {
            "has_overlap": self.has_overlap,
            "overlap_count": self.overlap_count,
            "nearby_event_ids": self.nearby_event_ids,
            "overlap_window_days": self.overlap_window_days,
            "high_impact_overlap_count": self.high_impact_overlap_count,
            "high_impact_event_ids": self.high_impact_event_ids
        }


class OverlapDetector:
    """
    Detects overlapping events for the same ticker within a time window.
    
    Used during training data preparation to filter out events with confounding
    overlaps, where price movements could be attributed to multiple catalysts.
    
    Attributes:
        window_days: Number of calendar days on each side to check (default: 3 for ~2 trading days)
        high_impact_threshold: Impact score threshold for high-impact overlaps (default: 60)
    """
    
    def __init__(
        self,
        window_days: int = OVERLAP_WINDOW_CALENDAR_DAYS,
        high_impact_threshold: int = HIGH_IMPACT_THRESHOLD
    ):
        """
        Initialize the overlap detector.
        
        Args:
            window_days: Calendar days to check on each side (±window_days).
                        Default is 3 calendar days which approximates ±2 trading days.
            high_impact_threshold: Minimum impact_score to consider an event high-impact.
        """
        self.window_days = window_days
        self.high_impact_threshold = high_impact_threshold
    
    def detect_overlaps(self, event_id: int, db: Session) -> Dict:
        """
        Check if an event has nearby events for the same ticker within the overlap window.
        
        Args:
            event_id: ID of the event to check
            db: SQLAlchemy database session
            
        Returns:
            Dict containing:
                - has_overlap: bool - True if overlapping events exist
                - overlap_count: int - Number of overlapping events (excluding current)
                - nearby_event_ids: List[int] - IDs of overlapping events
                - overlap_window_days: int - Window used for detection
                - high_impact_overlap_count: int - Count of high-impact overlapping events
                - high_impact_event_ids: List[int] - IDs of high-impact overlapping events
        """
        event = db.execute(
            select(Event).where(Event.id == event_id)
        ).scalar_one_or_none()
        
        if not event:
            logger.warning(f"Event {event_id} not found for overlap detection")
            return OverlapResult(
                has_overlap=False,
                overlap_count=0,
                nearby_event_ids=[],
                overlap_window_days=self.window_days
            ).to_dict()
        
        event_date = event.date
        ticker = event.ticker
        
        window_start = event_date - timedelta(days=self.window_days)
        window_end = event_date + timedelta(days=self.window_days)
        
        nearby_events = db.execute(
            select(Event)
            .where(
                and_(
                    Event.ticker == ticker,
                    Event.id != event_id,
                    Event.date >= window_start,
                    Event.date <= window_end
                )
            )
            .order_by(Event.date)
        ).scalars().all()
        
        nearby_event_ids: List[int] = [int(e.id) for e in nearby_events]
        high_impact_events = [
            e for e in nearby_events 
            if (int(e.impact_score or 0)) >= self.high_impact_threshold
        ]
        high_impact_event_ids: List[int] = [int(e.id) for e in high_impact_events]
        
        result = OverlapResult(
            has_overlap=len(nearby_events) > 0,
            overlap_count=len(nearby_events),
            nearby_event_ids=nearby_event_ids,
            overlap_window_days=self.window_days,
            high_impact_overlap_count=len(high_impact_events),
            high_impact_event_ids=high_impact_event_ids
        )
        
        if result.has_overlap:
            event_types = [e.event_type for e in nearby_events]
            logger.debug(
                f"Event {event_id} ({ticker}) has {result.overlap_count} overlapping events "
                f"within ±{self.window_days} days: types={event_types}, "
                f"high_impact={result.high_impact_overlap_count}"
            )
        
        return result.to_dict()
    
    def get_overlap_result(self, event_id: int, db: Session) -> OverlapResult:
        """
        Get overlap result as an OverlapResult object (for internal use).
        
        Args:
            event_id: ID of the event to check
            db: SQLAlchemy database session
            
        Returns:
            OverlapResult object with overlap detection results
        """
        result_dict = self.detect_overlaps(event_id, db)
        return OverlapResult(**result_dict)
    
    def batch_detect_overlaps(
        self,
        event_ids: List[int],
        db: Session
    ) -> Dict[int, Dict]:
        """
        Detect overlaps for multiple events efficiently.
        
        Args:
            event_ids: List of event IDs to check
            db: SQLAlchemy database session
            
        Returns:
            Dict mapping event_id -> overlap result dict
        """
        if not event_ids:
            return {}
        
        events = db.execute(
            select(Event).where(Event.id.in_(event_ids))
        ).scalars().all()
        
        events_by_id: Dict[int, Event] = {int(e.id): e for e in events}
        
        events_by_ticker: Dict[str, List[Event]] = {}
        for event in events:
            ticker_str = str(event.ticker)
            if ticker_str not in events_by_ticker:
                events_by_ticker[ticker_str] = []
            events_by_ticker[ticker_str].append(event)
        
        tickers = list(events_by_ticker.keys())
        event_dates: List[datetime] = [cast(datetime, e.date) for e in events]
        min_date = min(event_dates)
        max_date = max(event_dates)
        
        window_start = min_date - timedelta(days=self.window_days)
        window_end = max_date + timedelta(days=self.window_days)
        
        all_candidate_events = db.execute(
            select(Event)
            .where(
                and_(
                    Event.ticker.in_(tickers),
                    Event.date >= window_start,
                    Event.date <= window_end
                )
            )
        ).scalars().all()
        
        candidates_by_ticker: Dict[str, List[Event]] = {}
        for e in all_candidate_events:
            ticker_str = str(e.ticker)
            if ticker_str not in candidates_by_ticker:
                candidates_by_ticker[ticker_str] = []
            candidates_by_ticker[ticker_str].append(e)
        
        results: Dict[int, Dict[str, Any]] = {}
        for event_id in event_ids:
            event = events_by_id.get(event_id)
            if not event:
                results[event_id] = OverlapResult(
                    has_overlap=False,
                    overlap_count=0,
                    nearby_event_ids=[],
                    overlap_window_days=self.window_days
                ).to_dict()
                continue
            
            event_date = event.date
            event_window_start = event_date - timedelta(days=self.window_days)
            event_window_end = event_date + timedelta(days=self.window_days)
            
            candidates = candidates_by_ticker.get(str(event.ticker), [])
            nearby_events = [
                e for e in candidates
                if int(e.id) != event_id
                and event_window_start <= e.date <= event_window_end
            ]
            
            nearby_event_ids_list: List[int] = [int(e.id) for e in nearby_events]
            high_impact_events = [
                e for e in nearby_events
                if (int(e.impact_score or 0)) >= self.high_impact_threshold
            ]
            high_impact_event_ids_list: List[int] = [int(e.id) for e in high_impact_events]
            
            results[event_id] = OverlapResult(
                has_overlap=len(nearby_events) > 0,
                overlap_count=len(nearby_events),
                nearby_event_ids=nearby_event_ids_list,
                overlap_window_days=self.window_days,
                high_impact_overlap_count=len(high_impact_events),
                high_impact_event_ids=high_impact_event_ids_list
            ).to_dict()
        
        return results


def filter_overlapping_events(
    event_ids: List[int],
    db: Session,
    window_days: int = OVERLAP_WINDOW_CALENDAR_DAYS,
    exclude_high_impact_only: bool = False,
    high_impact_threshold: int = HIGH_IMPACT_THRESHOLD
) -> List[int]:
    """
    Filter out events that have overlapping events for the same ticker.
    
    Returns a list of event IDs that do NOT have overlapping events within the
    specified window. These "clean" events have unambiguous labels suitable
    for ML training.
    
    Args:
        event_ids: List of event IDs to filter
        db: SQLAlchemy database session
        window_days: Calendar days to check on each side (default: 3 for ~2 trading days)
        exclude_high_impact_only: If True, only exclude events with high-impact overlaps.
                                  If False (default), exclude all events with any overlaps.
        high_impact_threshold: Minimum impact_score to consider high-impact (default: 60)
        
    Returns:
        List of event IDs without overlapping events (clean labels)
    """
    if not event_ids:
        return []
    
    detector = OverlapDetector(
        window_days=window_days,
        high_impact_threshold=high_impact_threshold
    )
    
    overlap_results = detector.batch_detect_overlaps(event_ids, db)
    
    clean_event_ids = []
    excluded_count = 0
    high_impact_excluded_count = 0
    
    for event_id in event_ids:
        result = overlap_results.get(event_id, {})
        has_overlap = result.get("has_overlap", False)
        has_high_impact_overlap = result.get("high_impact_overlap_count", 0) > 0
        
        if exclude_high_impact_only:
            if not has_high_impact_overlap:
                clean_event_ids.append(event_id)
            else:
                excluded_count += 1
                high_impact_excluded_count += 1
        else:
            if not has_overlap:
                clean_event_ids.append(event_id)
            else:
                excluded_count += 1
                if has_high_impact_overlap:
                    high_impact_excluded_count += 1
    
    logger.info(
        f"Overlap filtering: {len(event_ids)} events -> {len(clean_event_ids)} clean events "
        f"(excluded {excluded_count}, {high_impact_excluded_count} with high-impact overlaps)"
    )
    
    return clean_event_ids


def get_overlap_statistics(
    event_ids: List[int],
    db: Session,
    window_days: int = OVERLAP_WINDOW_CALENDAR_DAYS
) -> Dict:
    """
    Compute statistics about overlaps in a set of events.
    
    Useful for understanding the extent of label noise in training data.
    
    Args:
        event_ids: List of event IDs to analyze
        db: SQLAlchemy database session
        window_days: Calendar days to check on each side
        
    Returns:
        Dict with overlap statistics:
            - total_events: Total number of events analyzed
            - events_with_overlaps: Number of events with at least one overlap
            - events_without_overlaps: Number of clean events
            - overlap_rate: Percentage of events with overlaps
            - avg_overlap_count: Average number of overlapping events (when overlap exists)
            - high_impact_overlap_rate: Percentage with high-impact overlaps
    """
    if not event_ids:
        return {
            "total_events": 0,
            "events_with_overlaps": 0,
            "events_without_overlaps": 0,
            "overlap_rate": 0.0,
            "avg_overlap_count": 0.0,
            "high_impact_overlap_rate": 0.0
        }
    
    detector = OverlapDetector(window_days=window_days)
    overlap_results = detector.batch_detect_overlaps(event_ids, db)
    
    events_with_overlaps = 0
    events_with_high_impact_overlaps = 0
    total_overlap_count = 0
    
    for event_id, result in overlap_results.items():
        if result.get("has_overlap", False):
            events_with_overlaps += 1
            total_overlap_count += result.get("overlap_count", 0)
        if result.get("high_impact_overlap_count", 0) > 0:
            events_with_high_impact_overlaps += 1
    
    total_events = len(event_ids)
    events_without_overlaps = total_events - events_with_overlaps
    overlap_rate = (events_with_overlaps / total_events * 100) if total_events > 0 else 0.0
    avg_overlap_count = (total_overlap_count / events_with_overlaps) if events_with_overlaps > 0 else 0.0
    high_impact_rate = (events_with_high_impact_overlaps / total_events * 100) if total_events > 0 else 0.0
    
    return {
        "total_events": total_events,
        "events_with_overlaps": events_with_overlaps,
        "events_without_overlaps": events_without_overlaps,
        "overlap_rate": round(overlap_rate, 2),
        "avg_overlap_count": round(avg_overlap_count, 2),
        "high_impact_overlap_rate": round(high_impact_rate, 2)
    }
