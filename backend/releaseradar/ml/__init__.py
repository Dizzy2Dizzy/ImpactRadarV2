"""
ML package for self-learning impact scoring system.

This package implements continuous learning from realized event outcomes
to improve impact predictions over time using gradient boosted models.
"""

from releaseradar.ml.label_filter import (
    OverlapDetector,
    OverlapResult,
    filter_overlapping_events,
    get_overlap_statistics,
    OVERLAP_WINDOW_CALENDAR_DAYS,
    HIGH_IMPACT_THRESHOLD,
)

__version__ = "1.0.0"

__all__ = [
    "OverlapDetector",
    "OverlapResult",
    "filter_overlapping_events",
    "get_overlap_statistics",
    "OVERLAP_WINDOW_CALENDAR_DAYS",
    "HIGH_IMPACT_THRESHOLD",
]
