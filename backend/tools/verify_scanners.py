#!/usr/bin/env python3
"""
Scanner Verification Tool for Impact Radar

Tests all 10 data scanners to verify:
1. They can be imported and called successfully
2. They return data in the correct format
3. URLs are valid and point to real sources
4. Dates are realistic (not fake future dates)
5. They're fetching real data vs returning stubs

Usage:
    python backend/tools/verify_scanners.py
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Tuple
import re
from urllib.parse import urlparse

# Add backend to path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

# Import scanner functions
try:
    from scanners.impl.sec_edgar import scan_sec_edgar
    from scanners.impl.fda import scan_fda
    from scanners.impl.press import scan_press
    from scanners.impl.sec_8k import scan_sec_8k
    from scanners.impl.earnings import scan_earnings_calls
    from scanners.impl.sec_10q import scan_sec_10q
    from scanners.impl.guidance import scan_guidance
    from scanners.impl.product_launch import scan_product_launch
    from scanners.impl.ma import scan_ma
    from scanners.impl.dividend import scan_dividend_buyback
except ImportError as e:
    print(f"ERROR: Failed to import scanner modules: {e}")
    sys.exit(1)


# Test configuration
TEST_TICKERS = ['AAPL', 'TSLA', 'MSFT']
TEST_COMPANIES = {
    'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology'},
    'TSLA': {'name': 'Tesla Inc.', 'sector': 'Automotive'},
    'MSFT': {'name': 'Microsoft Corporation', 'sector': 'Technology'}
}

# Scanner definitions
SCANNERS = [
    {
        'id': 'sec_edgar',
        'name': 'SEC EDGAR',
        'function': scan_sec_edgar,
        'description': 'SEC EDGAR filings (8-K, 10-K, 10-Q, etc.)'
    },
    {
        'id': 'fda',
        'name': 'FDA Announcements',
        'function': scan_fda,
        'description': 'FDA approvals, rejections, safety alerts'
    },
    {
        'id': 'press',
        'name': 'Company Press Releases',
        'function': scan_press,
        'description': 'Company newsrooms and press releases'
    },
    {
        'id': 'sec_8k',
        'name': 'SEC 8-K',
        'function': scan_sec_8k,
        'description': 'SEC 8-K material event filings'
    },
    {
        'id': 'earnings',
        'name': 'Earnings Calls',
        'function': scan_earnings_calls,
        'description': 'Earnings announcements and calls'
    },
    {
        'id': 'sec_10q',
        'name': 'SEC 10-Q',
        'function': scan_sec_10q,
        'description': 'SEC 10-Q quarterly reports'
    },
    {
        'id': 'guidance',
        'name': 'Guidance Updates',
        'function': scan_guidance,
        'description': 'Company financial guidance updates'
    },
    {
        'id': 'product_launch',
        'name': 'Product Launches',
        'function': scan_product_launch,
        'description': 'New product announcements'
    },
    {
        'id': 'ma',
        'name': 'M&A Activity',
        'function': scan_ma,
        'description': 'Mergers, acquisitions, strategic transactions'
    },
    {
        'id': 'dividend',
        'name': 'Dividends/Buybacks',
        'function': scan_dividend_buyback,
        'description': 'Dividend announcements and share buybacks'
    }
]


class ScannerStatus:
    """Scanner verification status."""
    PRODUCTION = "PRODUCTION"  # Fully working with real data
    STUB = "STUB"              # Returns fake/placeholder data
    BROKEN = "BROKEN"          # Errors or no data
    UNKNOWN = "UNKNOWN"        # Could not determine


def check_url_is_real(url: str) -> Tuple[bool, str]:
    """
    Check if URL looks like real data vs placeholder.
    
    Returns:
        (is_real, reason)
    """
    if not url:
        return False, "Empty URL"
    
    # Parse URL
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        path = parsed.path.lower()
    except:
        return False, "Invalid URL format"
    
    # Check for placeholder patterns
    placeholder_patterns = [
        r'investors\.\{ticker\}\.com',  # Template variables
        r'www\.\{ticker\}\.com',
        r'\{domain\}',
        r'newsroom$',  # Generic paths with no specifics
        r'/news$',
        r'/press-releases$',
    ]
    
    for pattern in placeholder_patterns:
        if re.search(pattern, url, re.IGNORECASE):
            return False, f"Contains placeholder pattern: {pattern}"
    
    # Check if URL has ticker but no real path (likely stub)
    if 'CIK={ticker}' in url or 'CIK=AAPL' in url or 'CIK=TSLA' in url:
        # SEC URLs with just ticker and no filing number are suspicious
        if 'accession' not in url and not re.search(r'\d{10}-\d{2}-\d{6}', url):
            return False, "Generic SEC URL without specific filing"
    
    # Check for specific document indicators (signs of real data)
    real_indicators = [
        r'/\d{10}-\d{2}-\d{6}/',  # SEC accession numbers
        r'\.htm$',                 # HTML documents
        r'\.pdf$',                 # PDF documents
        r'/newsroom/\d{4}/',       # Dated newsroom paths
        r'/news-releases/\d{4}/',  # Dated press release paths
        r'id=\d+',                 # Specific item IDs
    ]
    
    for indicator in real_indicators:
        if re.search(indicator, url, re.IGNORECASE):
            return True, f"Has specific document indicator: {indicator}"
    
    # Check for authoritative domains
    authoritative_domains = [
        'sec.gov',
        'fda.gov',
        'apple.com',
        'tesla.com',
        'microsoft.com',
        'nasdaq.com',
        'nyse.com'
    ]
    
    is_authoritative = any(auth in domain for auth in authoritative_domains)
    
    if is_authoritative and (path and path != '/' and path != '/news' and path != '/newsroom'):
        return True, "Authoritative domain with specific path"
    
    return False, "Generic URL structure"


def check_date_is_realistic(date: datetime, event_title: str) -> Tuple[bool, str]:
    """
    Check if date is realistic vs fake.
    
    Returns:
        (is_realistic, reason)
    """
    if not date:
        return False, "No date provided"
    
    now = datetime.now(timezone.utc)
    
    # Check if date is in the future
    if date > now:
        days_future = (date - now).days
        if days_future > 1:
            return False, f"Date is {days_future} days in the future"
    
    # Check if date is suspiciously recent (< 1 hour ago - likely utcnow())
    time_diff = abs((now - date).total_seconds())
    if time_diff < 3600:  # Less than 1 hour
        return False, "Date is suspiciously recent (likely datetime.utcnow())"
    
    # Check if date is too old
    days_old = (now - date).days
    if days_old > 365:
        return False, f"Date is {days_old} days old (> 1 year)"
    
    return True, f"{days_old} days old (reasonable)"


def check_title_is_real(title: str, ticker: str) -> Tuple[bool, str]:
    """
    Check if title looks like real data vs template.
    
    Returns:
        (is_real, reason)
    """
    if not title:
        return False, "Empty title"
    
    # Check for template variables
    if '{ticker}' in title or '{company}' in title:
        return False, "Contains template variables"
    
    # Check for overly generic patterns
    generic_patterns = [
        rf'^{ticker} filed \w+-\w+:',  # "AAPL filed 8-K:"
        rf'^{ticker} Announces',        # "AAPL Announces"
        rf'^{ticker} Updated',          # "AAPL Updated"
        rf'^{ticker} Earnings Call',    # "AAPL Earnings Call"
    ]
    
    for pattern in generic_patterns:
        if re.match(pattern, title):
            # Check if there's more specific content
            if len(title) < 50 and title.count(' ') < 5:
                return False, f"Generic pattern: {pattern}"
    
    # Real titles usually have more detail
    if len(title) > 60 or title.count(' ') > 5:
        return True, "Detailed title with specifics"
    
    return True, "Title format looks acceptable"


def analyze_scanner_data(events: List[Dict[str, Any]], scanner_id: str) -> Dict[str, Any]:
    """
    Analyze scanner output to determine if it's real data or stub.
    
    Returns:
        Analysis dictionary with status and details
    """
    if not events:
        return {
            'status': ScannerStatus.BROKEN,
            'event_count': 0,
            'issues': ['No events returned'],
            'warnings': [],
            'details': []
        }
    
    issues = []
    warnings = []
    details = []
    real_indicators = 0
    stub_indicators = 0
    
    # Check required fields
    required_fields = ['ticker', 'event_type', 'title', 'date', 'source_url']
    missing_fields = []
    
    for event in events[:5]:  # Check first 5 events
        for field in required_fields:
            if field not in event:
                missing_fields.append(field)
        
        # Check URL
        if 'source_url' in event:
            url_is_real, url_reason = check_url_is_real(event['source_url'])
            if url_is_real:
                real_indicators += 1
                details.append(f"✓ Real URL: {url_reason}")
            else:
                stub_indicators += 1
                warnings.append(f"Placeholder URL in '{event.get('title', 'Unknown')}': {url_reason}")
        
        # Check date
        if 'date' in event:
            date = event['date']
            if isinstance(date, str):
                try:
                    date = datetime.fromisoformat(date.replace('Z', '+00:00'))
                except:
                    warnings.append(f"Invalid date format: {date}")
                    continue
            
            date_is_real, date_reason = check_date_is_realistic(date, event.get('title', ''))
            if date_is_real:
                real_indicators += 1
                details.append(f"✓ Realistic date: {date_reason}")
            else:
                stub_indicators += 1
                warnings.append(f"Suspicious date in '{event.get('title', 'Unknown')}': {date_reason}")
        
        # Check title
        if 'title' in event and 'ticker' in event:
            title_is_real, title_reason = check_title_is_real(event['title'], event['ticker'])
            if title_is_real:
                real_indicators += 1
            else:
                stub_indicators += 1
                warnings.append(f"Generic title: {title_reason}")
    
    if missing_fields:
        issues.append(f"Missing fields in some events: {set(missing_fields)}")
    
    # Determine status based on indicators
    total_indicators = real_indicators + stub_indicators
    if total_indicators > 0:
        real_ratio = real_indicators / total_indicators
        
        if real_ratio >= 0.7:
            status = ScannerStatus.PRODUCTION
        elif stub_indicators > real_indicators:
            status = ScannerStatus.STUB
            issues.append(f"Stub indicators ({stub_indicators}) > Real indicators ({real_indicators})")
        else:
            status = ScannerStatus.UNKNOWN
    else:
        status = ScannerStatus.UNKNOWN
    
    # Add sample event for review
    if events:
        sample = events[0]
        details.append(f"\nSample event:")
        details.append(f"  Title: {sample.get('title', 'N/A')}")
        details.append(f"  Ticker: {sample.get('ticker', 'N/A')}")
        details.append(f"  Type: {sample.get('event_type', 'N/A')}")
        details.append(f"  Date: {sample.get('date', 'N/A')}")
        details.append(f"  URL: {sample.get('source_url', 'N/A')[:80]}...")
    
    return {
        'status': status,
        'event_count': len(events),
        'real_indicators': real_indicators,
        'stub_indicators': stub_indicators,
        'issues': issues,
        'warnings': warnings,
        'details': details
    }


def test_scanner(scanner_def: Dict[str, Any]) -> Dict[str, Any]:
    """
    Test a single scanner and return results.
    
    Returns:
        Test results dictionary
    """
    scanner_id = scanner_def['id']
    scanner_name = scanner_def['name']
    scanner_fn = scanner_def['function']
    
    print(f"\nTesting {scanner_name} ({scanner_id})...")
    print("-" * 60)
    
    result = {
        'id': scanner_id,
        'name': scanner_name,
        'description': scanner_def['description'],
        'status': ScannerStatus.UNKNOWN,
        'event_count': 0,
        'error': None,
        'analysis': {}
    }
    
    # Try to call the scanner
    try:
        # Different scanners have different signatures
        # Try with companies parameter first
        try:
            events = scanner_fn(TEST_TICKERS, companies=TEST_COMPANIES, limit_per_ticker=3)
        except TypeError:
            # Fall back to just tickers
            try:
                events = scanner_fn(TEST_TICKERS, limit_per_ticker=3)
            except TypeError:
                # Try with no kwargs
                events = scanner_fn(TEST_TICKERS)
        
        # Analyze the results
        analysis = analyze_scanner_data(events, scanner_id)
        result['status'] = analysis['status']
        result['event_count'] = analysis['event_count']
        result['analysis'] = analysis
        
        # Print immediate feedback
        status_emoji = {
            ScannerStatus.PRODUCTION: "✅",
            ScannerStatus.STUB: "⚠️",
            ScannerStatus.BROKEN: "❌",
            ScannerStatus.UNKNOWN: "❓"
        }
        
        print(f"Status: {status_emoji.get(result['status'], '?')} {result['status']}")
        print(f"Events found: {result['event_count']}")
        
        if analysis.get('real_indicators'):
            print(f"Real data indicators: {analysis['real_indicators']}")
        if analysis.get('stub_indicators'):
            print(f"Stub data indicators: {analysis['stub_indicators']}")
        
        if analysis.get('issues'):
            print(f"\nIssues:")
            for issue in analysis['issues']:
                print(f"  ❌ {issue}")
        
        if analysis.get('warnings'):
            print(f"\nWarnings:")
            for warning in analysis['warnings'][:3]:  # Show first 3
                print(f"  ⚠️  {warning}")
            if len(analysis['warnings']) > 3:
                print(f"  ... and {len(analysis['warnings']) - 3} more warnings")
        
    except Exception as e:
        result['status'] = ScannerStatus.BROKEN
        result['error'] = str(e)
        print(f"Status: ❌ BROKEN")
        print(f"Error: {e}")
    
    return result


def print_summary_report(results: List[Dict[str, Any]]):
    """Print comprehensive summary report."""
    print("\n" + "=" * 80)
    print(" SCANNER VERIFICATION SUMMARY REPORT")
    print("=" * 80)
    
    # Count by status
    status_counts = {
        ScannerStatus.PRODUCTION: 0,
        ScannerStatus.STUB: 0,
        ScannerStatus.BROKEN: 0,
        ScannerStatus.UNKNOWN: 0
    }
    
    for result in results:
        status_counts[result['status']] += 1
    
    print(f"\n📊 Overall Status:")
    print(f"   ✅ Production-ready:  {status_counts[ScannerStatus.PRODUCTION]}/10")
    print(f"   ⚠️  Stub/Placeholder:  {status_counts[ScannerStatus.STUB]}/10")
    print(f"   ❌ Broken:            {status_counts[ScannerStatus.BROKEN]}/10")
    print(f"   ❓ Unknown:           {status_counts[ScannerStatus.UNKNOWN]}/10")
    
    # Production scanners
    prod_scanners = [r for r in results if r['status'] == ScannerStatus.PRODUCTION]
    if prod_scanners:
        print(f"\n✅ PRODUCTION-READY SCANNERS ({len(prod_scanners)}):")
        for result in prod_scanners:
            print(f"   • {result['name']}: {result['event_count']} events")
            print(f"     {result['description']}")
    
    # Stub scanners
    stub_scanners = [r for r in results if r['status'] == ScannerStatus.STUB]
    if stub_scanners:
        print(f"\n⚠️  STUB/PLACEHOLDER SCANNERS ({len(stub_scanners)}):")
        print("   These scanners return fake data and need development:")
        for result in stub_scanners:
            print(f"   • {result['name']}")
            print(f"     {result['description']}")
            if result['analysis'].get('issues'):
                for issue in result['analysis']['issues'][:2]:
                    print(f"     - {issue}")
    
    # Broken scanners
    broken_scanners = [r for r in results if r['status'] == ScannerStatus.BROKEN]
    if broken_scanners:
        print(f"\n❌ BROKEN SCANNERS ({len(broken_scanners)}):")
        for result in broken_scanners:
            print(f"   • {result['name']}: {result['error']}")
    
    # Recommendations
    print(f"\n📋 RECOMMENDATIONS:")
    
    if status_counts[ScannerStatus.PRODUCTION] == 10:
        print("   🎉 All scanners are production-ready! Great work!")
    else:
        if stub_scanners:
            print(f"   1. Priority: Replace {len(stub_scanners)} stub scanners with real implementations")
            print(f"      Stub scanners are returning fake data, making the platform unreliable")
        
        if broken_scanners:
            print(f"   2. Fix {len(broken_scanners)} broken scanners that are throwing errors")
        
        if status_counts[ScannerStatus.PRODUCTION] > 0:
            print(f"   3. Good news: {status_counts[ScannerStatus.PRODUCTION]} scanners are working!")
            print(f"      Use these as templates for fixing the stub scanners:")
            for result in prod_scanners[:3]:
                print(f"      - {result['name']}")
    
    print(f"\n💡 CRITICAL INSIGHT:")
    if status_counts[ScannerStatus.STUB] > 0:
        print(f"   The fake data from stub scanners is likely what caused the")
        print(f"   issues you saw (FDA events from 2021, wrong dates, etc.)")
        print(f"   Priority: Replace stub implementations with real API calls")
    
    print("\n" + "=" * 80)
    print(f" Test completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print("=" * 80 + "\n")


def main():
    """Run scanner verification tests."""
    print("=" * 80)
    print(" Impact Radar Scanner Verification Tool")
    print("=" * 80)
    print(f"\nTesting {len(SCANNERS)} scanners with test tickers: {', '.join(TEST_TICKERS)}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
    
    results = []
    
    # Test each scanner
    for scanner_def in SCANNERS:
        result = test_scanner(scanner_def)
        results.append(result)
    
    # Print summary report
    print_summary_report(results)
    
    # Exit code based on results
    production_count = sum(1 for r in results if r['status'] == ScannerStatus.PRODUCTION)
    if production_count == len(SCANNERS):
        sys.exit(0)  # All good
    elif production_count > 0:
        sys.exit(1)  # Some working, some not
    else:
        sys.exit(2)  # None working


if __name__ == '__main__':
    main()
