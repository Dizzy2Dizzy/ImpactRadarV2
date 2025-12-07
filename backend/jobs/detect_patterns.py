#!/usr/bin/env python3
"""
Pattern Detection Job - Hourly scheduled job for detecting multi-event patterns.

Runs pattern detection for all active pattern definitions and creates alerts
when correlation patterns are detected.

Usage:
    python jobs/detect_patterns.py           # Run once
    python jobs/detect_patterns.py --loop    # Run continuously (hourly)
"""

import sys
import time
import argparse
import logging
from pathlib import Path
from datetime import datetime

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from releaseradar.db.session import SessionLocal
from releaseradar.services.pattern_detector import detect_patterns

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def run_pattern_detection():
    """
    Run pattern detection for all active patterns.
    
    Creates PatternAlert records when multi-event correlations are detected.
    """
    logger.info("Starting pattern detection job...")
    start_time = time.time()
    
    session = SessionLocal()
    
    try:
        # Run detection for all active patterns and all tickers
        alerts = detect_patterns(db=session)
        
        elapsed = time.time() - start_time
        logger.info(
            f"Pattern detection complete. "
            f"Created {len(alerts)} alerts in {elapsed:.2f}s"
        )
        
        # Log individual alerts for monitoring
        for alert in alerts:
            logger.info(
                f"Pattern alert: {alert.ticker} - Pattern ID {alert.pattern_id} "
                f"(correlation={alert.correlation_score:.2f}, "
                f"impact={alert.aggregated_impact_score})"
            )
        
        return len(alerts)
        
    except Exception as e:
        logger.exception(f"Error during pattern detection: {e}")
        return 0
        
    finally:
        session.close()


def main():
    """Main entry point for pattern detection job."""
    parser = argparse.ArgumentParser(
        description="Pattern Detection Job - Detects multi-event correlation patterns"
    )
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously (hourly)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=3600,
        help="Loop interval in seconds (default: 3600 = 1 hour)"
    )
    
    args = parser.parse_args()
    
    if args.loop:
        logger.info(f"Starting continuous pattern detection (interval: {args.interval}s)...")
        
        while True:
            try:
                run_pattern_detection()
            except Exception as e:
                logger.exception(f"Unhandled error in pattern detection loop: {e}")
            
            # Sleep until next run
            logger.info(f"Sleeping for {args.interval}s until next run...")
            time.sleep(args.interval)
    else:
        # Run once
        alerts_created = run_pattern_detection()
        sys.exit(0 if alerts_created >= 0 else 1)


if __name__ == "__main__":
    main()
