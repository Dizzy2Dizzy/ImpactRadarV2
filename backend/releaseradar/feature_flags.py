"""
Feature flags for controlling V1 vs Beta/Labs features.

Centralizes feature toggle configuration to support gradual rollout and
A/B testing of new capabilities while maintaining stability for V1 users.
"""

import os
from typing import Dict
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class FeatureFlags:
    """Feature flags for controlling V1 vs Beta/Labs features."""
    
    # Real-time features
    ENABLE_LIVE_WS: bool = os.getenv("ENABLE_LIVE_WS", "false").lower() == "true"
    
    # Beta/Labs UI features
    ENABLE_LABS_UI: bool = os.getenv("ENABLE_LABS_UI", "false").lower() == "true"
    
    # X.com / Social sentiment
    ENABLE_X_SENTIMENT: bool = os.getenv("ENABLE_X_SENTIMENT", "false").lower() == "true"
    
    # Alerts system (if still flaky)
    ENABLE_ALERTS_BETA: bool = os.getenv("ENABLE_ALERTS_BETA", "false").lower() == "true"
    
    # Advanced analytics
    ENABLE_ADVANCED_ANALYTICS: bool = os.getenv("ENABLE_ADVANCED_ANALYTICS", "false").lower() == "true"
    
    @classmethod
    def to_dict(cls) -> Dict[str, bool]:
        """Return all flags as dictionary for API responses."""
        return {
            "enableLiveWs": cls.ENABLE_LIVE_WS,
            "enableLabsUi": cls.ENABLE_LABS_UI,
            "enableXSentiment": cls.ENABLE_X_SENTIMENT,
            "enableAlertsBeta": cls.ENABLE_ALERTS_BETA,
            "enableAdvancedAnalytics": cls.ENABLE_ADVANCED_ANALYTICS,
        }


# Global instance
feature_flags = FeatureFlags()
