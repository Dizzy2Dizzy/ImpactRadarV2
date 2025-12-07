"""
Test plan-based authorization for score endpoints.

Verifies FREE users get 402 Payment Required, PRO/Team users get full access.
"""

import os
import sys
from datetime import datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.main import app
from api.utils.auth import create_access_token
from releaseradar.db.models import Company, Event, EventScore
from releaseradar.db.session import SessionLocal


@pytest.fixture(scope="function")
def db_session():
    """Create a fresh database session for each test."""
    session = SessionLocal()
    
    try:
        # Clean up test data
        session.execute(delete(EventScore))
        session.execute(delete(Event))
        session.execute(delete(Company).where(Company.ticker == "AUTH_TEST"))
        session.commit()
    except Exception:
        session.rollback()
    
    yield session
    
    try:
        # Clean up after test
        session.execute(delete(EventScore))
        session.execute(delete(Event))
        session.execute(delete(Company).where(Company.ticker == "AUTH_TEST"))
        session.commit()
    except Exception:
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def free_token():
    """Generate a valid FREE plan JWT token."""
    return create_access_token(
        data={
            "sub": "free@example.com",
            "user_id": 999,
            "plan": "free"
        },
        expires_delta=timedelta(hours=1)
    )


@pytest.fixture
def pro_token():
    """Generate a valid PRO plan JWT token."""
    return create_access_token(
        data={
            "sub": "pro@example.com",
            "user_id": 1000,
            "plan": "pro"
        },
        expires_delta=timedelta(hours=1)
    )


@pytest.fixture
def team_token():
    """Generate a valid TEAM plan JWT token."""
    return create_access_token(
        data={
            "sub": "team@example.com",
            "user_id": 1001,
            "plan": "team"
        },
        expires_delta=timedelta(hours=1)
    )


@pytest.fixture
def test_event_with_score(db_session):
    """Create a test event with score for testing."""
    # Create company
    company = Company(
        ticker="AUTH_TEST",
        name="Auth Test Company",
        sector="Technology",
        tracked=True
    )
    db_session.add(company)
    db_session.commit()
    
    # Create event
    event = Event(
        ticker="AUTH_TEST",
        company_name="Auth Test Company",
        title="Test Event",
        event_type="earnings",
        date=datetime(2024, 6, 15, 16, 0, 0),
        source="test",
        impact_score=75,
        direction="positive",
        confidence=0.85,
        rationale="Test event for authorization"
    )
    db_session.add(event)
    db_session.commit()
    
    # Create score
    score = EventScore(
        event_id=event.id,
        ticker="AUTH_TEST",
        event_type="earnings",
        base_score=50,
        context_score=25,
        final_score=75,
        confidence=85,
        factor_sector=10,
        factor_volatility=5,
        factor_earnings_proximity=15,
        factor_market_mood=20,
        factor_after_hours=10,
        factor_duplicate_penalty=0,
        rationale="Test score rationale"
    )
    db_session.add(score)
    db_session.commit()
    
    return event


class TestScorePlanGates:
    """Test plan-based access control for score endpoints."""
    
    def test_get_event_score_free_denied(self, test_event_with_score, free_token):
        """FREE users should receive 402 Payment Required on event score endpoint."""
        client = TestClient(app)
        
        response = client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={"Authorization": f"Bearer {free_token}"}
        )
        
        assert response.status_code == 402, "FREE users should be denied with 402"
        data = response.json()
        assert "detail" in data
        # Detail is a dict with structure: {"error": "UPGRADE_REQUIRED", "feature": "scores"}
        if isinstance(data["detail"], dict):
            assert data["detail"].get("error") == "UPGRADE_REQUIRED"
            assert data["detail"].get("feature") == "scores"
        else:
            # Fallback for string detail
            assert "upgrade" in data["detail"].lower() or "payment" in data["detail"].lower()
    
    def test_get_event_score_pro_allowed(self, test_event_with_score, pro_token):
        """PRO users should receive 200 with full score data."""
        client = TestClient(app)
        
        response = client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={"Authorization": f"Bearer {pro_token}"}
        )
        
        assert response.status_code == 200, "PRO users should get full access"
        data = response.json()
        
        # Verify required keys
        assert "score" in data or "final_score" in data, "Response should include score"
        assert "confidence" in data, "Response should include confidence"
        assert "factors" in data, "Response should include factors breakdown"
        
        # Verify all factor fields present
        factors = data["factors"]
        assert "sector" in factors, "Factors should include sector"
        assert "volatility" in factors, "Factors should include volatility"
        assert "earnings_proximity" in factors, "Factors should include earnings_proximity"
        assert "market_mood" in factors, "Factors should include market_mood"
        assert "after_hours" in factors, "Factors should include after_hours"
        assert "duplicate_penalty" in factors, "Factors should include duplicate_penalty"
    
    def test_get_event_score_team_allowed(self, test_event_with_score, team_token):
        """TEAM users should receive 200 with full score data."""
        client = TestClient(app)
        
        response = client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={"Authorization": f"Bearer {team_token}"}
        )
        
        assert response.status_code == 200, "TEAM users should get full access"
        data = response.json()
        
        # Verify structure
        assert "confidence" in data
        assert "factors" in data
    
    def test_get_scores_query_free_denied(self, test_event_with_score, free_token):
        """FREE users should receive 402 on scores query endpoint."""
        client = TestClient(app)
        
        response = client.get(
            "/scores/?ticker=AUTH_TEST&limit=10",
            headers={"Authorization": f"Bearer {free_token}"}
        )
        
        assert response.status_code == 402, "FREE users should be denied with 402"
        data = response.json()
        assert "detail" in data
        # Verify upgrade required response
        if isinstance(data["detail"], dict):
            assert data["detail"].get("error") == "UPGRADE_REQUIRED"
    
    def test_get_scores_query_pro_allowed(self, test_event_with_score, pro_token):
        """PRO users should receive 200 with scores list."""
        client = TestClient(app)
        
        response = client.get(
            "/scores/?ticker=AUTH_TEST&limit=10",
            headers={"Authorization": f"Bearer {pro_token}"}
        )
        
        assert response.status_code == 200, "PRO users should get full access"
        data = response.json()
        
        # Should be a list
        assert isinstance(data, list), "Response should be a list of scores"
        
        # If there are scores, verify structure
        if len(data) > 0:
            score_item = data[0]
            assert "confidence" in score_item or "event_id" in score_item
    
    def test_get_scores_query_team_allowed(self, test_event_with_score, team_token):
        """TEAM users should receive 200 with scores list."""
        client = TestClient(app)
        
        response = client.get(
            "/scores/?ticker=AUTH_TEST&limit=10",
            headers={"Authorization": f"Bearer {team_token}"}
        )
        
        assert response.status_code == 200, "TEAM users should get full access"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
