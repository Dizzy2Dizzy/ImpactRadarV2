"""
Centralized datetime and timezone utilities for Release Radar.

This module provides robust timezone conversion functions that handle
all edge cases including pre-normalized dates, ISO timestamps, and
SQLAlchemy datetime formats.
"""

from datetime import datetime, timezone
from typing import Any, Optional
import pytz
import re


def convert_to_est_date(date_value: Any) -> str:
    """
    Convert a UTC date/datetime to EST date string with robust edge case handling.
    
    This function handles all common date/datetime formats:
    - 'YYYY-MM-DD' (already normalized, no time component)
    - 'YYYY-MM-DDZ' (ISO with Z suffix, no time before Z)
    - 'YYYY-MM-DD+00:00' (SQLAlchemy format with timezone but no time)
    - 'YYYY-MM-DDTHH:MM:SSZ' (full ISO timestamp with Z)
    - 'YYYY-MM-DDTHH:MM:SS+00:00' (full ISO timestamp with timezone)
    - datetime objects (both timezone-aware and naive)
    - None values (returns empty string)
    
    The function detects pre-normalized dates by checking if characters 11+
    contain only timezone info (Z, +, -) and no actual time component.
    
    Args:
        date_value: Can be a string (ISO format), datetime object, or None
        
    Returns:
        Date string in EST timezone (YYYY-MM-DD format)
        
    Examples:
        >>> convert_to_est_date('2025-11-21')
        '2025-11-21'
        >>> convert_to_est_date('2025-11-21Z')
        '2025-11-21'
        >>> convert_to_est_date('2025-11-21+00:00')
        '2025-11-21'
        >>> convert_to_est_date('2025-11-21T21:00:00+00:00')
        '2025-11-21'  # Converted from UTC to EST
        >>> convert_to_est_date(None)
        ''
    """
    if date_value is None:
        return ""
    
    est_tz = pytz.timezone('America/New_York')
    
    # Handle string input (ISO format from database or API)
    if isinstance(date_value, str):
        # Extract base date (first 10 characters: YYYY-MM-DD)
        if len(date_value) < 10:
            # Invalid date string, return as-is
            return date_value
        
        base_date = date_value[:10]
        remaining = date_value[10:] if len(date_value) > 10 else ""
        
        # Check if remaining part contains actual time component
        # Pattern: remaining should match timezone-only patterns like:
        # - '' (empty - just date)
        # - 'Z' (UTC indicator)
        # - '+00:00', '-05:00', etc (timezone offset)
        # If there's a 'T' followed by digits, it's a full timestamp
        has_time_component = bool(re.search(r'T\d{2}:', remaining))
        
        if not has_time_component:
            # Pre-normalized date with no time component (or timezone-only suffix)
            # Examples: '2025-11-21', '2025-11-21Z', '2025-11-21+00:00'
            # These are already normalized to date-only format, return base date
            return base_date
        
        # Full ISO timestamp with time component
        # Examples: '2025-11-21T21:00:00Z', '2025-11-21T21:00:00+00:00'
        # Parse and convert to EST
        try:
            # Normalize 'Z' suffix to '+00:00' for consistent parsing
            normalized = date_value.replace('Z', '+00:00')
            dt = datetime.fromisoformat(normalized)
        except ValueError:
            # Fallback: try parsing without timezone info
            try:
                dt = datetime.fromisoformat(date_value.replace('Z', ''))
                # Assume UTC if no timezone
                dt = dt.replace(tzinfo=timezone.utc)
            except ValueError:
                # Cannot parse, return base date as fallback
                return base_date
    
    # Handle datetime object input
    elif isinstance(date_value, datetime):
        dt = date_value
        # If naive datetime, assume UTC
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
    
    # Handle other types
    else:
        return str(date_value)
    
    # Convert to EST timezone
    est_dt = dt.astimezone(est_tz)
    
    # Return date string in EST (YYYY-MM-DD format)
    return est_dt.strftime('%Y-%m-%d')


def convert_utc_to_est_date(date_value: Any) -> str:
    """
    Alias for convert_to_est_date() for backward compatibility.
    
    This function is deprecated and will be removed in a future version.
    Use convert_to_est_date() instead.
    
    Args:
        date_value: Can be a string (ISO format), datetime object, or None
        
    Returns:
        Date string in EST timezone (YYYY-MM-DD format)
    """
    return convert_to_est_date(date_value)
