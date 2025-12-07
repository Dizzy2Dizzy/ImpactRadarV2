"""
Event Type Family Configuration for Market Echo Engine

This module defines logical groupings of event types for ML training purposes.
Each family groups similar event types that should be trained together.

Sample size thresholds for training:
- >= 150: Production models (reliable predictions)
- 50-149: Experimental models (limited data, use with caution)
- < 50: Deterministic only (insufficient data for ML)
"""

from typing import Dict, List, Optional

# Event type family definitions
EVENT_TYPE_FAMILIES: Dict[str, List[str]] = {
    # SEC 8-K: Material corporate events
    "sec_8k": ["sec_8k"],
    
    # SEC Quarterly Reports
    "sec_10q": ["sec_10q"],
    
    # SEC Annual Reports
    "sec_10k": ["sec_10k"],
    
    # Earnings-related events
    "earnings": [
        "earnings",
        "earnings_call",
        "earnings_release",
        "earnings_guidance"
    ],
    
    # FDA regulatory events
    "fda": [
        "fda_approval",
        "fda_complete_response",
        "fda_rejection",
        "fda_clinical_hold",
        "fda_breakthrough_designation",
        "fda_priority_review"
    ],
    
    # M&A and strategic transactions
    "mna": [
        "ma",
        "acquisition",
        "merger",
        "divestiture",
        "spin_off"
    ],
    
    # Capital allocation events
    "capital_allocation": [
        "dividend",
        "buyback",
        "stock_split",
        "rights_offering"
    ],
    
    # Product and business events
    "product_business": [
        "product_launch",
        "product_recall",
        "partnership",
        "contract_win",
        "contract_loss"
    ],
    
    # Guidance updates
    "guidance": [
        "guidance_raise",
        "guidance_lower",
        "guidance_update"
    ],
    
    # Other SEC filings
    "sec_other": [
        "sec_def14a",
        "sec_s1",
        "sec_s3",
        "sec_424b"
    ]
}

# Reverse mapping: event_type -> family
_EVENT_TYPE_TO_FAMILY: Optional[Dict[str, str]] = None


def get_event_family(event_type: str) -> str:
    """
    Get the family name for a given event type.
    
    Args:
        event_type: The event type string
        
    Returns:
        The family name, or 'unknown' if not found
    """
    global _EVENT_TYPE_TO_FAMILY
    
    # Build reverse mapping on first call
    if _EVENT_TYPE_TO_FAMILY is None:
        _EVENT_TYPE_TO_FAMILY = {}
        for family, types in EVENT_TYPE_FAMILIES.items():
            for event_type_name in types:
                _EVENT_TYPE_TO_FAMILY[event_type_name] = family
    
    return _EVENT_TYPE_TO_FAMILY.get(event_type, "unknown")


def get_family_display_name(family: str) -> str:
    """
    Get a human-readable display name for an event family.
    
    Args:
        family: The family key
        
    Returns:
        Display name for the family
    """
    display_names = {
        "sec_8k": "SEC 8-K Filings",
        "sec_10q": "SEC 10-Q (Quarterly Reports)",
        "sec_10k": "SEC 10-K (Annual Reports)",
        "earnings": "Earnings Events",
        "fda": "FDA Regulatory Events",
        "mna": "M&A / Strategic Transactions",
        "capital_allocation": "Capital Allocation",
        "product_business": "Product & Business Events",
        "guidance": "Guidance Updates",
        "sec_other": "Other SEC Filings",
        "unknown": "Uncategorized Events"
    }
    return display_names.get(family, family.replace("_", " ").title())


# Family ID mapping for global models (used as numeric features in XGBoost)
FAMILY_TO_ID = {
    "sec_8k": 0,
    "sec_10q": 1,
    "sec_10k": 2,
    "earnings": 3,
    "fda": 4,
    "mna": 5,
    "capital_allocation": 6,
    "product_business": 7,
    "guidance": 8,
    "sec_other": 9,
    "unknown": 10
}


def get_family_id(family: str) -> int:
    """
    Get numeric ID for an event family (for use as ML feature).
    
    Args:
        family: The family name
        
    Returns:
        Integer ID for the family
    """
    return FAMILY_TO_ID.get(family, 10)  # 10 = unknown


# Training thresholds
MIN_SAMPLES_PRODUCTION = 150  # Minimum for production models
MIN_SAMPLES_EXPERIMENTAL = 50  # Minimum for experimental models
MIN_SAMPLES_TRAINING = 30  # Absolute minimum to attempt training


def should_train_model(sample_count: int) -> tuple[bool, str]:
    """
    Determine if a model should be trained based on sample count.
    
    Args:
        sample_count: Number of labeled samples available
        
    Returns:
        (should_train, status) where status is one of:
        - 'production': >= 150 samples
        - 'experimental': 50-149 samples
        - 'insufficient': < 50 samples
    """
    if sample_count >= MIN_SAMPLES_PRODUCTION:
        return True, "production"
    elif sample_count >= MIN_SAMPLES_EXPERIMENTAL:
        return True, "experimental"
    else:
        return False, "insufficient"
