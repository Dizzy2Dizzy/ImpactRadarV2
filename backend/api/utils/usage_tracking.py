"""
Usage tracking utilities for monthly quotas and metering.

Tracks API calls and alerts sent per user per month for billing and analytics.
"""

from datetime import datetime
from typing import Optional
from api.utils.metrics import increment_metric


def track_api_call(plan: str):
    """
    Track an API call for monthly usage metering.
    
    Args:
        plan: User's plan (free, pro, team)
    """
    metric_name = f"api_calls_monthly_{plan}"
    increment_metric(metric_name)


def track_alert_sent(plan: str):
    """
    Track an alert sent for monthly usage metering.
    
    Args:
        plan: User's plan (free, pro, team)
    """
    metric_name = f"alerts_sent_monthly_{plan}"
    increment_metric(metric_name)
