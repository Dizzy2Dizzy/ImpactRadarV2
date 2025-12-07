"""
Test script for production scanners.

Tests SEC EDGAR, FDA, and Press Release scanners with sample tickers.
"""

import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))

from scanners.impl.sec_edgar import scan_sec_edgar
from scanners.impl.fda import scan_fda
from scanners.impl.press import scan_press
from scanners.utils import generate_raw_id
from datetime import datetime, timezone

def test_sec_edgar():
    """Test SEC EDGAR scanner with AAPL."""
    print("\n" + "="*80)
    print("Testing SEC EDGAR Scanner")
    print("="*80)
    
    companies = {
        'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology'}
    }
    
    try:
        events = scan_sec_edgar(['AAPL'], companies=companies, limit_per_ticker=3)
        print(f"\nFound {len(events)} SEC EDGAR events for AAPL")
        
        for i, event in enumerate(events[:3], 1):
            print(f"\nEvent {i}:")
            print(f"  Ticker: {event['ticker']}")
            print(f"  Type: {event['event_type']}")
            print(f"  Title: {event['title']}")
            print(f"  Date: {event['date']}")
            print(f"  Source: {event['source']}")
            print(f"  URL: {event['source_url'][:80]}..." if len(event.get('source_url', '')) > 80 else f"  URL: {event.get('source_url', 'N/A')}")
            print(f"  Raw ID: {event['raw_id']}")
        
        return len(events) > 0
    
    except Exception as e:
        print(f"\nERROR in SEC EDGAR scanner: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_fda():
    """Test FDA scanner with MRNA."""
    print("\n" + "="*80)
    print("Testing FDA Scanner")
    print("="*80)
    
    companies = {
        'MRNA': {'name': 'Moderna Inc.', 'sector': 'Healthcare'}
    }
    
    try:
        events = scan_fda(['MRNA'], companies=companies, limit_per_ticker=3)
        print(f"\nFound {len(events)} FDA events for MRNA")
        
        for i, event in enumerate(events[:3], 1):
            print(f"\nEvent {i}:")
            print(f"  Ticker: {event['ticker']}")
            print(f"  Type: {event['event_type']}")
            print(f"  Title: {event['title']}")
            print(f"  Date: {event['date']}")
            print(f"  Source: {event['source']}")
            print(f"  URL: {event['source_url'][:80]}..." if len(event.get('source_url', '')) > 80 else f"  URL: {event.get('source_url', 'N/A')}")
            print(f"  Raw ID: {event['raw_id']}")
        
        return True  # FDA scanner might not always find events for MRNA
    
    except Exception as e:
        print(f"\nERROR in FDA scanner: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_press():
    """Test Press Release scanner with AAPL."""
    print("\n" + "="*80)
    print("Testing Press Release Scanner")
    print("="*80)
    
    companies = {
        'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology'}
    }
    
    try:
        events = scan_press(['AAPL'], companies=companies, limit_per_ticker=3)
        print(f"\nFound {len(events)} press releases for AAPL")
        
        for i, event in enumerate(events[:3], 1):
            print(f"\nEvent {i}:")
            print(f"  Ticker: {event['ticker']}")
            print(f"  Type: {event['event_type']}")
            print(f"  Title: {event['title']}")
            print(f"  Date: {event['date']}")
            print(f"  Source: {event['source']}")
            print(f"  URL: {event['source_url'][:80]}..." if len(event.get('source_url', '')) > 80 else f"  URL: {event.get('source_url', 'N/A')}")
            print(f"  Raw ID: {event['raw_id']}")
        
        return True  # Press scanner might not always find events
    
    except Exception as e:
        print(f"\nERROR in Press Release scanner: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_deduplication():
    """Test deduplication logic."""
    print("\n" + "="*80)
    print("Testing Deduplication Logic")
    print("="*80)
    
    # Generate raw_id for the same event twice
    date = datetime(2025, 11, 13, tzinfo=timezone.utc)
    
    raw_id_1 = generate_raw_id('AAPL', 'sec_8k', 'Test Event', date)
    raw_id_2 = generate_raw_id('AAPL', 'sec_8k', 'Test Event', date)
    
    print(f"\nRaw ID 1: {raw_id_1}")
    print(f"Raw ID 2: {raw_id_2}")
    
    if raw_id_1 == raw_id_2:
        print("\n✓ Deduplication works: Same event generates same raw_id")
        
        # Test with different event
        raw_id_3 = generate_raw_id('AAPL', 'sec_8k', 'Different Event', date)
        print(f"\nRaw ID 3 (different title): {raw_id_3}")
        
        if raw_id_1 != raw_id_3:
            print("✓ Different events generate different raw_ids")
            return True
        else:
            print("✗ Different events generated same raw_id")
            return False
    else:
        print("\n✗ Deduplication failed: Same event generated different raw_ids")
        return False


if __name__ == "__main__":
    print("\n" + "="*80)
    print("SCANNER TEST SUITE")
    print("="*80)
    
    results = {
        'SEC EDGAR': test_sec_edgar(),
        'FDA': test_fda(),
        'Press Release': test_press(),
        'Deduplication': test_deduplication()
    }
    
    print("\n" + "="*80)
    print("TEST RESULTS")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{test_name}: {status}")
    
    print("\n" + "="*80)
    
    all_passed = all(results.values())
    sys.exit(0 if all_passed else 1)
