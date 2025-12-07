"""
Integration tests for event statistics pipeline.

Tests the complete flow: Event creation → Price backfill → Stats recomputation
Validates pipeline invariants and action-based contract.
"""

import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select, delete, func
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from releaseradar.db.models import Event, PriceHistory, EventStats, Company
from releaseradar.db.session import SessionLocal
from jobs.recompute_event_stats import compute_stats_for_ticker_event_type, recompute_all_stats

# Fixed reference date for deterministic tests (avoid datetime.now() flakiness)
REFERENCE_DATE = datetime(2024, 6, 1, 10, 0, 0)  # June 1, 2024 at 10 AM


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    session = SessionLocal()
    
    try:
        # Clean up test data before each test
        session.execute(delete(EventStats))
        session.execute(delete(PriceHistory))
        session.execute(delete(Event))
        session.execute(delete(Company).where(Company.ticker.in_(["TEST", "PARTIAL", "RECENT", "EMPTY"])))
        session.commit()
    except Exception:
        session.rollback()
    
    yield session
    
    try:
        # Clean up after test
        session.execute(delete(EventStats))
        session.execute(delete(PriceHistory))
        session.execute(delete(Event))
        session.execute(delete(Company).where(Company.ticker.in_(["TEST", "PARTIAL", "RECENT", "EMPTY"])))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


def create_test_company(session, ticker: str, name: str):
    """Helper to create a test company."""
    company = Company(
        ticker=ticker,
        name=name,
        sector="Technology",
        tracked=True
    )
    session.add(company)
    session.commit()
    return company


def create_test_event(session, ticker: str, event_type: str, date: datetime, title: str = None):
    """Helper to create a test event."""
    event = Event(
        ticker=ticker,
        company_name=f"{ticker} Company",  # Required field
        title=title or f"{ticker} {event_type}",
        event_type=event_type,
        date=date,
        source="test",  # Required field
        impact_score=50,
        direction="positive",
        confidence=0.8,
        rationale="Test event"
    )
    session.add(event)
    session.commit()
    return event


def create_test_price_history(session, ticker: str, start_date: datetime, days: int, base_price: float = 100.0):
    """Helper to create price history for testing."""
    for i in range(days):
        date = start_date + timedelta(days=i)
        # Skip weekends (simplified - doesn't account for holidays)
        if date.weekday() >= 5:
            continue
        
        # Simulate some price movement
        price = base_price * (1 + (i * 0.01))
        
        price_record = PriceHistory(
            ticker=ticker,
            date=date.date(),
            open=Decimal(str(price)),
            high=Decimal(str(price * 1.02)),
            low=Decimal(str(price * 0.98)),
            close=Decimal(str(price)),
            volume=1000000
        )
        session.add(price_record)
    
    session.commit()


class TestEventStatsInvariant:
    """Test pipeline invariant enforcement."""
    
    def test_full_price_data_creates_stats(self, db_session):
        """
        Scenario: Full price data available for all events
        Expected: EventStats row created with correct metrics
        """
        # Setup
        create_test_company(db_session, "TEST", "Test Company")
        
        # Create event 30 days before reference date (plenty of time for 20d window)
        event_date = REFERENCE_DATE - timedelta(days=30)
        create_test_event(db_session, "TEST", "earnings", event_date)
        
        # Create price history: 10 days before event + 35 days after (50 total days ensures >20 trading days)
        create_test_price_history(db_session, "TEST", event_date - timedelta(days=10), 50)
        
        # Execute
        result = compute_stats_for_ticker_event_type(db_session, "TEST", "earnings")
        
        # Assert
        assert result["action"] == "update", "Should create stats when full data available"
        payload = result["payload"]
        assert payload["ticker"] == "TEST"
        assert payload["event_type"] == "earnings"
        assert payload["sample_size"] == 1
        assert payload["win_rate"] is not None
        assert payload["mean_move_1d"] is not None
        assert payload["mean_move_5d"] is not None
        assert payload["mean_move_20d"] is not None
    
    def test_missing_price_data_deletes_stats(self, db_session):
        """
        Scenario: No price data available
        Expected: EventStats row deleted (action='delete'), database row removed
        """
        # Setup
        create_test_company(db_session, "EMPTY", "Empty Company")
        create_test_event(db_session, "EMPTY", "earnings", REFERENCE_DATE - timedelta(days=30))
        
        # Pre-create stale EventStats row
        stale_stats = EventStats(
            ticker="EMPTY",
            event_type="earnings",
            sample_size=5,
            win_rate=0.6,
            mean_move_1d=0.02,
            updated_at=REFERENCE_DATE - timedelta(days=60)
        )
        db_session.add(stale_stats)
        db_session.commit()
        
        # Verify stale row exists
        count_before = db_session.execute(
            select(func.count()).select_from(EventStats).where(
                EventStats.ticker == "EMPTY",
                EventStats.event_type == "earnings"
            )
        ).scalar()
        assert count_before == 1, "Stale EventStats should exist before recompute"
        
        # No price history created
        
        # Execute
        result = compute_stats_for_ticker_event_type(db_session, "EMPTY", "earnings")
        
        # Assert action
        assert result["action"] == "delete", "Should delete when no price data"
        
        # Execute deletion (simulate recompute job behavior)
        db_session.execute(
            delete(EventStats).where(
                EventStats.ticker == "EMPTY",
                EventStats.event_type == "earnings"
            )
        )
        db_session.commit()
        
        # Assert database row removed
        count_after = db_session.execute(
            select(func.count()).select_from(EventStats).where(
                EventStats.ticker == "EMPTY",
                EventStats.event_type == "earnings"
            )
        ).scalar()
        assert count_after == 0, "EventStats row should be deleted from database"
    
    def test_partial_price_history_deletes_stats(self, db_session):
        """
        Scenario: Price history partially present (not enough for 20d window)
        Expected: EventStats deleted if NO events have complete coverage, database row removed
        """
        # Setup
        create_test_company(db_session, "RECENT", "Recent Event Company")
        
        # Create recent event (only 10 days before reference - insufficient for 20d window)
        event_date = REFERENCE_DATE - timedelta(days=10)
        create_test_event(db_session, "RECENT", "earnings", event_date)
        
        # Pre-create stale EventStats row
        stale_stats = EventStats(
            ticker="RECENT",
            event_type="earnings",
            sample_size=3,
            win_rate=0.7,
            mean_move_20d=0.05,
            updated_at=REFERENCE_DATE - timedelta(days=60)
        )
        db_session.add(stale_stats)
        db_session.commit()
        
        # Create price history: before event + only 10 days after (missing 20d window)
        create_test_price_history(db_session, "RECENT", event_date - timedelta(days=10), 20)
        
        # Execute
        result = compute_stats_for_ticker_event_type(db_session, "RECENT", "earnings")
        
        # Assert action
        assert result["action"] == "delete", "Should delete when insufficient future price data"
        
        # Execute deletion
        db_session.execute(
            delete(EventStats).where(
                EventStats.ticker == "RECENT",
                EventStats.event_type == "earnings"
            )
        )
        db_session.commit()
        
        # Assert database row removed
        count_after = db_session.execute(
            select(func.count()).select_from(EventStats).where(
                EventStats.ticker == "RECENT",
                EventStats.event_type == "earnings"
            )
        ).scalar()
        assert count_after == 0, "Stale EventStats row should be deleted"
    
    def test_multiple_events_mixed_completeness(self, db_session):
        """
        Scenario: Multiple events, some with complete data, some without
        Expected: Stats computed using only events with complete coverage (Option B: Lenient)
        """
        # Setup
        create_test_company(db_session, "PARTIAL", "Partial Data Company")
        
        # Old event with full coverage (60 days before reference - plenty of time for 20d)
        old_event_date = REFERENCE_DATE - timedelta(days=60)
        create_test_event(db_session, "PARTIAL", "earnings", old_event_date, "Q1 Earnings")
        
        # Recent event without 20d coverage (5 days before reference - definitely insufficient)
        recent_event_date = REFERENCE_DATE - timedelta(days=5)
        create_test_event(db_session, "PARTIAL", "earnings", recent_event_date, "Q2 Earnings")
        
        # Create price history: 10 days before old event, ending 30 days after old event
        # This gives old event full coverage but recent event lacks 20d window
        create_test_price_history(db_session, "PARTIAL", old_event_date - timedelta(days=10), 40)
        
        # Execute
        result = compute_stats_for_ticker_event_type(db_session, "PARTIAL", "earnings")
        
        # Assert (Option B: Use available data from old event)
        assert result["action"] == "update", "Should use old event with complete coverage"
        payload = result["payload"]
        assert payload["sample_size"] == 1, "Should only include event with complete coverage (recent excluded)"
        assert payload["mean_move_1d"] is not None
        assert payload["mean_move_5d"] is not None
        assert payload["mean_move_20d"] is not None
    
    def test_weekend_timezone_alignment(self, db_session):
        """
        Scenario: Event on weekend, price data on nearest trading day
        Expected: Returns computed using nearest trading day
        """
        # Setup
        create_test_company(db_session, "TEST", "Test Company")
        
        # Create event on a Saturday (2024-01-06 was a Saturday)
        event_date = datetime(2024, 1, 6, 16, 0, 0)  # Saturday 4PM
        create_test_event(db_session, "TEST", "fda_approval", event_date)
        
        # Create weekday price data around the event
        create_test_price_history(db_session, "TEST", datetime(2024, 1, 1), 40)
        
        # Execute
        result = compute_stats_for_ticker_event_type(db_session, "TEST", "fda_approval")
        
        # Assert
        assert result["action"] == "update", "Should handle weekend events gracefully"
        assert result["payload"]["sample_size"] >= 1


class TestRecomputeJobIdempotence:
    """Test that recompute job is idempotent (multiple runs produce identical results)."""
    
    def test_recompute_idempotence(self, db_session):
        """
        Scenario: Run recompute_all_stats() multiple times
        Expected: Identical results each time, single row maintained
        """
        # Setup
        create_test_company(db_session, "TEST", "Test Company")
        event_date = REFERENCE_DATE - timedelta(days=30)
        create_test_event(db_session, "TEST", "earnings", event_date)
        create_test_price_history(db_session, "TEST", event_date - timedelta(days=10), 50)
        
        # First run
        stats1 = recompute_all_stats(tickers=["TEST"], event_types=["earnings"])
        
        # Query fresh after first run to get values
        db_session.expire_all()  # Expire cached objects
        result1 = db_session.execute(
            select(EventStats).where(
                EventStats.ticker == "TEST",
                EventStats.event_type == "earnings"
            )
        ).first()
        
        assert result1 is not None, "First run should create EventStats"
        
        # Extract values immediately
        stats_row1 = result1[0]
        sample_size_1 = stats_row1.sample_size
        win_rate_1 = stats_row1.win_rate
        mean_1d_1 = stats_row1.mean_move_1d
        mean_5d_1 = stats_row1.mean_move_5d
        mean_20d_1 = stats_row1.mean_move_20d
        
        # Count rows after first run
        count_after_first = db_session.execute(
            select(func.count()).select_from(EventStats).where(
                EventStats.ticker == "TEST",
                EventStats.event_type == "earnings"
            )
        ).scalar()
        assert count_after_first == 1, "First run should create exactly one EventStats row"
        
        # Second run (should be idempotent)
        stats2 = recompute_all_stats(tickers=["TEST"], event_types=["earnings"])
        
        # Query fresh after second run
        db_session.expire_all()  # Expire cached objects
        result2 = db_session.execute(
            select(EventStats).where(
                EventStats.ticker == "TEST",
                EventStats.event_type == "earnings"
            )
        ).first()
        
        assert result2 is not None, "Second run should preserve EventStats"
        
        # Extract values immediately
        stats_row2 = result2[0]
        sample_size_2 = stats_row2.sample_size
        win_rate_2 = stats_row2.win_rate
        mean_1d_2 = stats_row2.mean_move_1d
        mean_5d_2 = stats_row2.mean_move_5d
        mean_20d_2 = stats_row2.mean_move_20d
        
        # Count rows after second run
        count_after_second = db_session.execute(
            select(func.count()).select_from(EventStats).where(
                EventStats.ticker == "TEST",
                EventStats.event_type == "earnings"
            )
        ).scalar()
        assert count_after_second == 1, "Second run should maintain exactly one EventStats row (no duplicates)"
        
        # Compare the extracted values (proves idempotence)
        assert sample_size_1 == sample_size_2, f"Sample size changed: {sample_size_1} != {sample_size_2}"
        assert win_rate_1 == win_rate_2, f"Win rate changed: {win_rate_1} != {win_rate_2}"
        assert mean_1d_1 == mean_1d_2, f"Mean 1d changed: {mean_1d_1} != {mean_1d_2}"
        assert mean_5d_1 == mean_5d_2, f"Mean 5d changed: {mean_5d_1} != {mean_5d_2}"
        assert mean_20d_1 == mean_20d_2, f"Mean 20d changed: {mean_20d_1} != {mean_20d_2}"


class TestActionBasedContract:
    """Test the structured action-based contract."""
    
    def test_delete_action_structure(self, db_session):
        """Verify delete action returns correct structure."""
        create_test_company(db_session, "EMPTY", "Empty Company")
        create_test_event(db_session, "EMPTY", "earnings", datetime.now() - timedelta(days=30))
        
        result = compute_stats_for_ticker_event_type(db_session, "EMPTY", "earnings")
        
        assert "action" in result
        assert result["action"] == "delete"
        assert "payload" not in result, "Delete action should not have payload"
    
    def test_update_action_structure(self, db_session):
        """Verify update action returns correct structure with payload."""
        create_test_company(db_session, "TEST", "Test Company")
        event_date = REFERENCE_DATE - timedelta(days=30)
        create_test_event(db_session, "TEST", "earnings", event_date)
        create_test_price_history(db_session, "TEST", event_date - timedelta(days=10), 50)
        
        result = compute_stats_for_ticker_event_type(db_session, "TEST", "earnings")
        
        assert "action" in result
        assert result["action"] == "update"
        assert "payload" in result
        
        payload = result["payload"]
        assert "ticker" in payload
        assert "event_type" in payload
        assert "sample_size" in payload
        assert "win_rate" in payload
        assert "mean_move_1d" in payload
        assert "mean_move_5d" in payload
        assert "mean_move_20d" in payload
        assert "avg_abs_move_1d" in payload
        assert "avg_abs_move_5d" in payload
        assert "avg_abs_move_20d" in payload
        assert "updated_at" in payload


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
