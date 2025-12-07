"""
Tests for Information Tier classification and filtering (Wave J)
"""
import pytest
from datetime import datetime
from scanners.utils import classify_info_tier, normalize_event


def test_classify_info_tier_sec_filings():
    """Test that SEC filings are correctly classified as primary tier"""
    # Test S-1 (IPO)
    tier, subtype = classify_info_tier("sec_s1", "SEC EDGAR")
    assert tier == "primary"
    assert subtype == "ipo"
    
    # Test 8-K (material event)
    tier, subtype = classify_info_tier("sec_8k", "SEC EDGAR")
    assert tier == "primary"
    assert subtype == "material_event"
    
    # Test 10-Q (earnings)
    tier, subtype = classify_info_tier("sec_10q", "SEC EDGAR")
    assert tier == "primary"
    assert subtype == "earnings"
    
    # Test 10-K (earnings)
    tier, subtype = classify_info_tier("sec_10k", "SEC EDGAR")
    assert tier == "primary"
    assert subtype == "earnings"


def test_classify_info_tier_fda():
    """Test that FDA events are correctly classified"""
    tier, subtype = classify_info_tier("fda_approval", "FDA")
    assert tier == "primary"
    assert subtype == "regulatory_primary"


def test_classify_info_tier_press_releases():
    """Test that press releases are classified correctly"""
    tier, subtype = classify_info_tier("product_launch", "Press Release", "New Product Launch")
    assert tier == "primary"
    assert subtype == "product"
    
    tier, subtype = classify_info_tier("merger_acquisition", "Press Release", "Company Acquires Competitor")
    assert tier == "primary"
    assert subtype == "ma"


def test_normalize_event_with_tier():
    """Test that normalize_event properly handles tier fields"""
    normalized = normalize_event(
        ticker="AAPL",
        company_name="Apple Inc.",
        event_type="sec_8k",
        title="Test Event",
        date=datetime(2024, 1, 15),
        source="SEC EDGAR",
        source_url="https://example.com",
        description="Test Description",
        info_tier="primary",
        info_subtype="material_event"
    )
    
    assert normalized["info_tier"] == "primary"
    assert normalized["info_subtype"] == "material_event"
    assert normalized["ticker"] == "AAPL"
    assert normalized["event_type"] == "sec_8k"


def test_normalize_event_auto_classification():
    """Test that normalize_event auto-classifies if tier not provided"""
    normalized = normalize_event(
        ticker="AAPL",
        company_name="Apple Inc.",
        event_type="fda_approval",
        title="FDA Approval",
        date=datetime(2024, 1, 15),
        source="FDA",
        source_url="https://example.com",
        description="Drug approved"
    )
    
    # Should auto-classify based on event_type
    assert normalized["info_tier"] == "primary"
    assert normalized["info_subtype"] == "regulatory_primary"


def test_default_tier_when_unknown():
    """Test that unknown event types get default primary tier"""
    tier, subtype = classify_info_tier("unknown_type", "Unknown Source")
    assert tier == "primary"
    assert subtype is None
