"""
Seed price history data for demonstration.

Creates sample price data for AAPL, ABBV, and AMD to enable backtesting demos.
"""

import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from jobs.fetch_prices import backfill_prices
from releaseradar.log_config import logger


def seed_demo_prices():
    """Seed price history for demo tickers."""
    demo_tickers = ["AAPL", "ABBV", "AMD"]
    
    logger.info(f"Seeding price history for {demo_tickers}")
    
    # Backfill 1 year of data for demo tickers
    stats = backfill_prices(tickers=demo_tickers, days_back=365, force=False)
    
    logger.info(f"Seed complete: {stats}")
    return stats


if __name__ == "__main__":
    seed_demo_prices()
