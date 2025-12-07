#!/usr/bin/env python3
"""
Initialize system-wide pattern definitions for Impact Radar.

Creates default patterns for common multi-event correlation scenarios:
- Bullish Convergence: FDA approval + insider buying
- Earnings Momentum: Strong earnings + guidance upgrade
- Regulatory Risk: Multiple negative regulatory events

Usage:
    python scripts/init_system_patterns.py
"""

import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from releaseradar.db.session import SessionLocal
from releaseradar.db.models import PatternDefinition
from sqlalchemy import and_
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# System pattern definitions
SYSTEM_PATTERNS = [
    {
        "name": "Bullish Convergence",
        "description": "Positive FDA approval combined with insider buying signals strong institutional confidence",
        "conditions": {
            "event_types": ["fda_approval", "insider_buy"],
            "min_score": 70,
            "direction": "positive",
            "min_events": 2
        },
        "time_window_days": 14,
        "min_correlation_score": 0.6,
        "alert_channels": ["in_app", "email"],
        "priority": "high"
    },
    {
        "name": "Earnings Momentum",
        "description": "Strong earnings results followed by positive guidance upgrade",
        "conditions": {
            "event_types": ["earnings", "guidance_upgrade"],
            "min_score": 75,
            "direction": "positive",
            "min_events": 2
        },
        "time_window_days": 7,
        "min_correlation_score": 0.7,
        "alert_channels": ["in_app", "email"],
        "priority": "high"
    },
    {
        "name": "Regulatory Risk",
        "description": "Multiple negative regulatory events indicating potential compliance or approval issues",
        "conditions": {
            "event_types": ["fda_rejection", "sec_investigation", "regulatory_warning"],
            "min_score": 60,
            "direction": "negative",
            "min_events": 2
        },
        "time_window_days": 30,
        "min_correlation_score": 0.5,
        "alert_channels": ["in_app", "email"],
        "priority": "high"
    },
    {
        "name": "Product Launch Catalyst",
        "description": "Product launch announcement combined with positive market reception or partnership",
        "conditions": {
            "event_types": ["product_launch", "partnership", "press_release"],
            "min_score": 65,
            "direction": "positive",
            "min_events": 2
        },
        "time_window_days": 14,
        "min_correlation_score": 0.6,
        "alert_channels": ["in_app"],
        "priority": "medium"
    },
    {
        "name": "M&A Activity Signal",
        "description": "Merger or acquisition rumors combined with unusual trading volume or insider activity",
        "conditions": {
            "event_types": ["ma_rumor", "ma_announcement", "insider_buy"],
            "min_score": 70,
            "min_events": 2
        },
        "time_window_days": 21,
        "min_correlation_score": 0.6,
        "alert_channels": ["in_app", "email"],
        "priority": "high"
    },
    {
        "name": "Clinical Trial Success",
        "description": "Positive clinical trial results combined with FDA fast track or breakthrough designation",
        "conditions": {
            "event_types": ["clinical_trial", "fda_breakthrough", "fda_approval"],
            "min_score": 75,
            "direction": "positive",
            "min_events": 2
        },
        "time_window_days": 30,
        "min_correlation_score": 0.7,
        "alert_channels": ["in_app", "email"],
        "priority": "high"
    }
]


def create_system_patterns():
    """
    Create or update system-wide pattern definitions.
    
    System patterns have created_by=null to distinguish them from user patterns.
    """
    session = SessionLocal()
    
    try:
        created_count = 0
        updated_count = 0
        
        for pattern_data in SYSTEM_PATTERNS:
            # Check if pattern already exists (by name, for system patterns)
            existing = session.query(PatternDefinition).filter(
                and_(
                    PatternDefinition.name == pattern_data["name"],
                    PatternDefinition.created_by == None  # System patterns only
                )
            ).first()
            
            if existing:
                # Update existing pattern
                existing.description = pattern_data["description"]
                existing.conditions = pattern_data["conditions"]
                existing.time_window_days = pattern_data["time_window_days"]
                existing.min_correlation_score = pattern_data["min_correlation_score"]
                existing.alert_channels = pattern_data["alert_channels"]
                existing.priority = pattern_data["priority"]
                existing.active = True
                
                logger.info(f"Updated system pattern: {pattern_data['name']}")
                updated_count += 1
            else:
                # Create new system pattern
                pattern = PatternDefinition(
                    name=pattern_data["name"],
                    description=pattern_data["description"],
                    created_by=None,  # System pattern (not user-created)
                    active=True,
                    conditions=pattern_data["conditions"],
                    time_window_days=pattern_data["time_window_days"],
                    min_correlation_score=pattern_data["min_correlation_score"],
                    alert_channels=pattern_data["alert_channels"],
                    priority=pattern_data["priority"]
                )
                
                session.add(pattern)
                logger.info(f"Created system pattern: {pattern_data['name']}")
                created_count += 1
        
        session.commit()
        
        logger.info(
            f"System patterns initialization complete. "
            f"Created: {created_count}, Updated: {updated_count}"
        )
        
        return created_count + updated_count
        
    except Exception as e:
        logger.exception(f"Error initializing system patterns: {e}")
        session.rollback()
        return 0
        
    finally:
        session.close()


def main():
    """Main entry point."""
    logger.info("Starting system patterns initialization...")
    
    count = create_system_patterns()
    
    if count > 0:
        logger.info(f"Successfully initialized {count} system patterns")
        sys.exit(0)
    else:
        logger.error("Failed to initialize system patterns")
        sys.exit(1)


if __name__ == "__main__":
    main()
