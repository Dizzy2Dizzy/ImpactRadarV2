"""
Scanner catalog registry for Impact Radar.

Defines all active scanners with metadata and function references.
"""

from typing import Dict, List, Callable
from dataclasses import dataclass


@dataclass
class ScannerDefinition:
    """Scanner configuration and metadata."""
    key: str
    label: str
    fn_name: str
    interval_minutes: int = 30
    enabled: bool = True
    use_slow_pool: bool = False  # Force slow pool for heavy scanners regardless of interval


# Central scanner registry
SCANNERS: List[ScannerDefinition] = [
    # Existing scanners
    ScannerDefinition(
        key="sec_edgar",
        label="SEC EDGAR",
        fn_name="scan_sec_edgar",
        interval_minutes=240  # 4 hours
    ),
    ScannerDefinition(
        key="fda_announcements",
        label="FDA Announcements",
        fn_name="scan_fda",
        interval_minutes=360  # 6 hours
    ),
    ScannerDefinition(
        key="company_press",
        label="Company Press Releases",
        fn_name="scan_press",
        interval_minutes=480  # 8 hours
    ),
    
    # New scanners
    ScannerDefinition(
        key="earnings_calls",
        label="Earnings Calls",
        fn_name="scan_earnings_calls",
        interval_minutes=60  # 1 hour
    ),
    ScannerDefinition(
        key="sec_8k",
        label="SEC 8-K",
        fn_name="scan_sec_8k",
        interval_minutes=15,  # 15 minutes
        use_slow_pool=True   # Heavy scanner - needs more time for 1000+ companies
    ),
    ScannerDefinition(
        key="sec_10q",
        label="SEC 10-Q",
        fn_name="scan_sec_10q",
        interval_minutes=360  # 6 hours
    ),
    ScannerDefinition(
        key="guidance_updates",
        label="Guidance Updates",
        fn_name="scan_guidance",
        interval_minutes=120  # 2 hours
    ),
    ScannerDefinition(
        key="product_launch",
        label="Product Launches",
        fn_name="scan_product_launch",
        interval_minutes=180  # 3 hours
    ),
    ScannerDefinition(
        key="ma_activity",
        label="M&A / Strategic",
        fn_name="scan_ma",
        interval_minutes=60  # 1 hour
    ),
    ScannerDefinition(
        key="dividend_buyback",
        label="Dividends / Buybacks",
        fn_name="scan_dividend_buyback",
        interval_minutes=240  # 4 hours
    ),
    ScannerDefinition(
        key="form4_insider",
        label="Form 4 Insider Trading",
        fn_name="scan_form4_filings",
        interval_minutes=360  # 6 hours
    ),
]


def get_scanner_count() -> int:
    """Return count of active scanners."""
    return len([s for s in SCANNERS if s.enabled])


def get_scanner_by_key(key: str) -> ScannerDefinition:
    """Get scanner definition by key."""
    for scanner in SCANNERS:
        if scanner.key == key:
            return scanner
    raise ValueError(f"Scanner not found: {key}")
