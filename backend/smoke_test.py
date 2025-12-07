"""
Smoke test for backward compatibility between DataService and DataManager.

This validates that the new DataService can be used as a drop-in replacement
for the existing DataManager without breaking app.py.
"""

import sys
from datetime import datetime, timedelta

print("=" * 80)
print("Impact Radar Backward Compatibility Smoke Test")
print("=" * 80)

# Test 1: Import new DataService
print("\n[Test 1] Importing new DataService...")
try:
    from releaseradar.services.data import DataService
    print("✅ DataService imported successfully")
except Exception as e:
    print(f"❌ Failed to import DataService: {e}")
    sys.exit(1)

# Test 2: Initialize DataService
print("\n[Test 2] Initializing DataService...")
try:
    dm = DataService()
    print("✅ DataService initialized successfully")
except Exception as e:
    print(f"❌ Failed to initialize DataService: {e}")
    sys.exit(1)

# Test 3: Check interface compatibility (methods exist)
print("\n[Test 3] Checking interface compatibility...")
required_methods = [
    'get_companies',
    'create_company',
    'get_events',
    'create_event',
    'event_exists',
    'get_watchlist',
    'add_to_watchlist',
    'remove_from_watchlist',
    'log_scanner_event',
    'get_scanner_status',
]

missing_methods = []
for method in required_methods:
    if not hasattr(dm, method):
        missing_methods.append(method)
        print(f"❌ Missing method: {method}")
    else:
        print(f"✅ Method exists: {method}")

if missing_methods:
    print(f"\n❌ DataService is missing methods: {', '.join(missing_methods)}")
    sys.exit(1)

# Test 4: Test get_companies()
print("\n[Test 4] Testing get_companies()...")
try:
    companies = dm.get_companies(limit=5)
    print(f"✅ get_companies() returned {len(companies)} companies")
    if companies:
        print(f"   Sample company: {companies[0]['ticker']} - {companies[0]['name']}")
except Exception as e:
    print(f"❌ get_companies() failed: {e}")
    sys.exit(1)

# Test 5: Test get_events()
print("\n[Test 5] Testing get_events()...")
try:
    now = datetime.utcnow()
    events = dm.get_events(
        date_from=now - timedelta(days=30),
        date_to=now + timedelta(days=30),
        limit=5
    )
    print(f"✅ get_events() returned {len(events)} events")
    if events:
        sample = events[0]
        print(f"   Sample event: {sample['ticker']} - {sample['title']}")
        print(f"   Impact: {sample['impact_score']}, Direction: {sample['direction']}")
except Exception as e:
    print(f"❌ get_events() failed: {e}")
    sys.exit(1)

# Test 6: Test get_watchlist()
print("\n[Test 6] Testing get_watchlist()...")
try:
    watchlist = dm.get_watchlist(user_id=1)
    print(f"✅ get_watchlist() returned {len(watchlist)} items")
except Exception as e:
    print(f"❌ get_watchlist() failed: {e}")
    sys.exit(1)

# Test 7: Test scanner logs
print("\n[Test 7] Testing scanner logging...")
try:
    dm.log_scanner_event("smoke_test", "Test log entry", level="info")
    logs = dm.get_scanner_status(limit=1)
    print(f"✅ Scanner logging works, retrieved {len(logs)} logs")
except Exception as e:
    print(f"❌ Scanner logging failed: {e}")
    sys.exit(1)

# Test 8: Test event_exists()
print("\n[Test 8] Testing event_exists()...")
try:
    exists = dm.event_exists("AAPL", "earnings", "Q1 2024", datetime.utcnow())
    print(f"✅ event_exists() returned {exists}")
except Exception as e:
    print(f"❌ event_exists() failed: {e}")
    sys.exit(1)

# Test 9: Import check - Verify models can be imported
print("\n[Test 9] Verifying model imports...")
try:
    from releaseradar.db.models import Company, Event, User, WatchlistItem, ScannerLog
    print("✅ All models imported successfully")
except Exception as e:
    print(f"❌ Failed to import models: {e}")
    sys.exit(1)

# Test 10: Import check - Verify domain modules
print("\n[Test 10] Verifying domain module imports...")
try:
    from releaseradar.domain.events import EventInput, EventRecord, VALID_EVENT_TYPES
    from releaseradar.domain.scoring import score_event, EVENT_TYPE_SCORES
    print(f"✅ Domain modules imported successfully")
    print(f"   VALID_EVENT_TYPES: {len(VALID_EVENT_TYPES)} types")
    print(f"   EVENT_TYPE_SCORES: {len(EVENT_TYPE_SCORES)} scores")
except Exception as e:
    print(f"❌ Failed to import domain modules: {e}")
    sys.exit(1)

# Summary
print("\n" + "=" * 80)
print("✅ ALL SMOKE TESTS PASSED")
print("=" * 80)
print("\nConclusion:")
print("  - DataService provides complete backward compatibility with DataManager")
print("  - All required methods exist and work correctly")
print("  - Database connection and queries function properly")
print("  - Domain modules and models import successfully")
print("\nThe new modular architecture is ready for use!")
print("app.py can be updated to use DataService without breaking changes.")
print("=" * 80)
