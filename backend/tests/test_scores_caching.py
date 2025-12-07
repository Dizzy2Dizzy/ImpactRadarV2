"""
Test ETag-based HTTP caching for score endpoints.

Verifies cache hits return 304, misses return 200, and rescore invalidates cache.
"""

import os
import sys
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.main import app
from api.utils.auth import create_access_token
from releaseradar.db.models import Company, Event, EventScore
from releaseradar.db.session import SessionLocal


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    from releaseradar.db.models import User as RRUser
    
    session = SessionLocal()
    
    try:
        # Clean up test data
        session.execute(delete(EventScore))
        session.execute(delete(Event))
        session.execute(delete(Company).where(Company.ticker == "CACHE_TEST"))
        session.execute(delete(RRUser).where(RRUser.email.in_(["admin@cache.test", "pro@cache.test"])))
        session.commit()
    except Exception:
        session.rollback()
    
    yield session
    
    try:
        # Clean up after test
        session.execute(delete(EventScore))
        session.execute(delete(Event))
        session.execute(delete(Company).where(Company.ticker == "CACHE_TEST"))
        session.execute(delete(RRUser).where(RRUser.email.in_(["admin@cache.test", "pro@cache.test"])))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def pro_token():
    """Generate a valid PRO plan JWT token."""
    return create_access_token(
        data={
            "sub": "pro@cache.test",
            "user_id": 2000,
            "plan": "pro"
        },
        expires_delta=timedelta(hours=1)
    )


@pytest.fixture
def admin_token(db_session):
    """Generate a valid admin JWT token and create admin user in DB."""
    # Import User model from correct path
    from releaseradar.db.models import User as RRUser
    from api.utils.auth import hash_password
    
    # Create admin user
    admin_user = RRUser(
        email="admin@cache.test",
        password_hash=hash_password("admin123"),
        plan="team",
        is_admin=True
    )
    db_session.add(admin_user)
    db_session.commit()
    db_session.refresh(admin_user)
    
    # Create admin token
    return create_access_token(
        data={
            "sub": admin_user.email,
            "user_id": admin_user.id,
            "plan": "team"
        },
        expires_delta=timedelta(hours=1)
    )


@pytest.fixture
def test_event_with_score(db_session):
    """Create a test event with score for caching tests."""
    # Create company
    company = Company(
        ticker="CACHE_TEST",
        name="Cache Test Company",
        sector="Technology",
        tracked=True
    )
    db_session.add(company)
    db_session.commit()
    
    # Create event
    event = Event(
        ticker="CACHE_TEST",
        company_name="Cache Test Company",
        title="Cache Test Event",
        event_type="earnings",
        date=datetime(2024, 6, 15, 16, 0, 0),
        source="test",
        impact_score=80,
        direction="positive",
        confidence=0.90,
        rationale="Test event for caching"
    )
    db_session.add(event)
    db_session.commit()
    
    # Create score
    score = EventScore(
        event_id=event.id,
        ticker="CACHE_TEST",
        event_type="earnings",
        base_score=55,
        context_score=25,
        final_score=80,
        confidence=90,
        factor_sector=15,
        factor_volatility=10,
        factor_earnings_proximity=20,
        factor_market_mood=15,
        factor_after_hours=5,
        factor_duplicate_penalty=0,
        rationale="Cache test score"
    )
    db_session.add(score)
    db_session.commit()
    
    return event


class TestETagCaching:
    """Test ETag-based conditional GET caching."""
    
    def test_first_request_returns_etag(self, test_event_with_score, pro_token):
        """First request should return 200 with ETag header."""
        client = TestClient(app)
        
        response = client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={"Authorization": f"Bearer {pro_token}"}
        )
        
        assert response.status_code == 200, "First request should return 200"
        assert "ETag" in response.headers or "etag" in response.headers, "Response should include ETag header"
        
        # Get ETag value (case-insensitive)
        etag = response.headers.get("ETag") or response.headers.get("etag")
        assert etag is not None, "ETag should have a value"
        assert len(etag) > 0, "ETag should not be empty"
    
    def test_conditional_get_with_matching_etag_returns_304(self, test_event_with_score, pro_token):
        """Request with matching If-None-Match should return 304 Not Modified."""
        client = TestClient(app)
        
        # First request to get ETag
        response1 = client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={"Authorization": f"Bearer {pro_token}"}
        )
        
        assert response1.status_code == 200
        etag = response1.headers.get("ETag") or response1.headers.get("etag")
        assert etag is not None
        
        # Second request with If-None-Match
        response2 = client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={
                "Authorization": f"Bearer {pro_token}",
                "If-None-Match": etag
            }
        )
        
        assert response2.status_code == 304, "Matching ETag should return 304"
        # 304 responses should have no body or minimal body
        assert len(response2.content) == 0 or len(response2.content) < 10, "304 should have no/minimal body"
    
    def test_rescore_invalidates_cache(self, test_event_with_score, pro_token, admin_token):
        """POST /scores/rescore should invalidate cache and change ETag."""
        client = TestClient(app)
        
        # First GET to capture initial ETag
        response1 = client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={"Authorization": f"Bearer {pro_token}"}
        )
        
        assert response1.status_code == 200
        etag_before = response1.headers.get("ETag") or response1.headers.get("etag")
        assert etag_before is not None
        
        # Rescore the event (admin only)
        rescore_response = client.post(
            "/scores/rescore",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"event_ids": [test_event_with_score.id]}
        )
        
        # Rescore should succeed (200 or 202)
        assert rescore_response.status_code in [200, 202, 204], f"Rescore should succeed, got {rescore_response.status_code}"
        
        # GET again - should return 200 with different ETag
        response2 = client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={"Authorization": f"Bearer {pro_token}"}
        )
        
        assert response2.status_code == 200, "After rescore, should get fresh data"
        etag_after = response2.headers.get("ETag") or response2.headers.get("etag")
        assert etag_after is not None
        assert etag_before != etag_after, "ETag should change after rescore (cache invalidation)"
    
    def test_conditional_get_with_old_etag_after_rescore_returns_200(
        self, test_event_with_score, pro_token, admin_token
    ):
        """Using old ETag after rescore should return 200 with new data."""
        client = TestClient(app)
        
        # First GET
        response1 = client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={"Authorization": f"Bearer {pro_token}"}
        )
        etag_old = response1.headers.get("ETag") or response1.headers.get("etag")
        
        # Rescore
        client.post(
            "/scores/rescore",
            headers={"Authorization": f"Bearer {admin_token}"},
            json={"event_ids": [test_event_with_score.id]}
        )
        
        # GET with old ETag - should return 200 (cache miss)
        response2 = client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={
                "Authorization": f"Bearer {pro_token}",
                "If-None-Match": etag_old
            }
        )
        
        assert response2.status_code == 200, "Old ETag should be a cache miss after invalidation"
        assert len(response2.content) > 0, "Should return full body on cache miss"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
