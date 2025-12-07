#!/usr/bin/env python3
"""
Event Source Verification Tool

Validates that events have real, properly formatted source URLs from official sources.
Part of Impact Radar V1 quality gates.
"""

import os
import sys
from urllib.parse import urlparse
from collections import defaultdict

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Official domain whitelist
OFFICIAL_DOMAINS = {
    "SEC": ["sec.gov", "www.sec.gov"],
    "FDA": ["fda.gov", "www.fda.gov"],
    # Add more official domains as needed
}

# Company IR patterns (permissive for now - just check it's a valid company domain)
COMPANY_IR_PATTERNS = [
    "investor.",  # investor.apple.com
    "ir.",        # ir.google.com
    "/investor",  # company.com/investor-relations
    "/ir/",       # company.com/ir/
]

def verify_source_url(source_url: str, event_type: str) -> tuple[bool, str]:
    """
    Verify source URL is valid and from expected domain.
    Returns (is_valid, reason)
    """
    if not source_url:
        return False, "Missing source URL"
    
    try:
        parsed = urlparse(source_url)
        domain = parsed.netloc.lower()
        
        # Remove www. prefix for comparison
        domain_base = domain.replace("www.", "")
        
        # Check SEC events (using actual database event type names)
        if event_type in ["sec_8k", "sec_10k", "sec_10q", "sec_s1", "sec_def14a"]:
            if any(d in domain for d in OFFICIAL_DOMAINS["SEC"]):
                # Validate EDGAR URL pattern
                if "/Archives/edgar/" in source_url or "/edgar/browse-edgar/" in source_url:
                    return True, "Valid SEC EDGAR URL"
                return True, "Valid SEC URL (non-EDGAR)"
            return False, f"SEC event with non-SEC domain: {domain}"
        
        # Check FDA events (using actual database event type names)
        if event_type in ["fda_approval", "fda_announcement", "fda_decision", "clinical_trial"]:
            if any(d in domain for d in OFFICIAL_DOMAINS["FDA"]):
                return True, "Valid FDA URL"
            return False, f"FDA event with non-FDA domain: {domain}"
        
        # Check company IR events (using actual database event type names)
        if event_type in ["earnings", "guidance", "press_release", "product_launch", "ma", "dividend"]:
            # Permissive check - just verify it's HTTPS and has valid format
            if parsed.scheme in ["https", "http"] and domain:
                # Check for investor relations patterns
                url_lower = source_url.lower()
                if any(pattern in url_lower for pattern in COMPANY_IR_PATTERNS):
                    return True, "Valid company IR URL"
                # Accept any HTTPS company URL for now (can tighten later)
                return True, "Valid company URL (no IR pattern found)"
            return False, f"Company event with invalid URL: {source_url}"
        
        # Unknown event type - permissive
        return True, "Unknown event type - skipped validation"
        
    except Exception as e:
        return False, f"URL parse error: {str(e)}"

def main():
    # Get database URL from environment
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ ERROR: DATABASE_URL not set")
        sys.exit(1)
    
    print("=" * 70)
    print("Impact Radar Event Source Verification Tool")
    print("=" * 70)
    print()
    
    # Connect to database
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get total event count
        total_events = session.execute(text("SELECT COUNT(*) FROM events")).scalar()
        print(f"📊 Total events in database: {total_events}\n")
        
        # Sample events by type (using actual database event type names)
        event_types = [
            "sec_8k", "sec_10k", "sec_10q", "sec_def14a",  # SEC
            "fda_approval", "fda_announcement",  # FDA
            "earnings", "press_release", "product_launch"  # Company
        ]
        
        results = {
            "total_checked": 0,
            "valid": 0,
            "invalid": 0,
            "by_type": defaultdict(lambda: {"checked": 0, "valid": 0, "invalid": 0, "issues": []}),
        }
        
        for event_type in event_types:
            # Sample up to 50 events per type
            query = text("""
                SELECT id, ticker, title, event_type, source_url 
                FROM events 
                WHERE event_type = :event_type 
                LIMIT 50
            """)
            events = session.execute(query, {"event_type": event_type}).fetchall()
            
            if not events:
                continue
            
            print(f"🔍 Checking {event_type} events ({len(events)} samples)...")
            
            for event in events:
                event_id, ticker, title, evt_type, source_url = event
                results["total_checked"] += 1
                results["by_type"][evt_type]["checked"] += 1
                
                is_valid, reason = verify_source_url(source_url, evt_type)
                
                if is_valid:
                    results["valid"] += 1
                    results["by_type"][evt_type]["valid"] += 1
                else:
                    results["invalid"] += 1
                    results["by_type"][evt_type]["invalid"] += 1
                    results["by_type"][evt_type]["issues"].append({
                        "event_id": event_id,
                        "ticker": ticker,
                        "title": title[:60] if title else "N/A",
                        "source_url": source_url,
                        "reason": reason,
                    })
        
        # Print summary
        print()
        print("=" * 70)
        print("VERIFICATION SUMMARY")
        print("=" * 70)
        
        if results["total_checked"] == 0:
            print("⚠️  WARNING: No events found matching the specified event types")
            print("   Database may be empty or event types may not match.")
            sys.exit(0)
        
        print(f"✅ Valid events: {results['valid']}/{results['total_checked']} ({results['valid']/results['total_checked']*100:.1f}%)")
        print(f"❌ Invalid events: {results['invalid']}/{results['total_checked']} ({results['invalid']/results['total_checked']*100:.1f}%)")
        print()
        
        # Print details by type
        for event_type, stats in sorted(results["by_type"].items()):
            print(f"\n📋 {event_type}:")
            print(f"   Checked: {stats['checked']}")
            print(f"   Valid: {stats['valid']}")
            print(f"   Invalid: {stats['invalid']}")
            
            if stats["issues"]:
                print(f"   ⚠️  Issues found:")
                for issue in stats["issues"][:5]:  # Show first 5
                    print(f"      Event #{issue['event_id']} ({issue['ticker']}): {issue['reason']}")
                    print(f"         Title: {issue['title']}")
                    print(f"         URL: {issue['source_url']}")
                if len(stats["issues"]) > 5:
                    print(f"      ... and {len(stats['issues']) - 5} more")
        
        print()
        print("=" * 70)
        
        # Exit with error code if significant issues found
        if results["invalid"] > results["total_checked"] * 0.1:  # >10% invalid
            print("❌ CRITICAL: >10% of events have invalid source URLs")
            print("   This blocks V1 launch. Fix event ingestion pipelines.")
            sys.exit(1)
        elif results["invalid"] > 0:
            print("⚠️  WARNING: Some events have invalid source URLs")
            print("   Review and fix before V1 launch.")
            sys.exit(0)
        else:
            print("✅ All sampled events have valid source URLs")
            sys.exit(0)
        
    finally:
        session.close()

if __name__ == "__main__":
    main()
