"""
Alerts module for Impact Radar.

Handles alert matching, notification delivery, and email services.
"""

from alerts.email_service import get_email_service

__all__ = ["get_email_service"]
