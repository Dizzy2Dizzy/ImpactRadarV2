"""
Test /metrics endpoint for Prometheus-compatible metrics exposure.

Verifies all counters are present and increment correctly.
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
from api.utils.metrics import get_metrics, increment_metric
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
        session.execute(delete(Company).where(Company.ticker == "METRICS_TEST"))
        session.commit()
    except Exception:
        session.rollback()
    
    yield session
    
    try:
        # Clean up after test
        session.execute(delete(EventScore))
        session.execute(delete(Event))
        session.execute(delete(Company).where(Company.ticker == "METRICS_TEST"))
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
            "sub": "free@metrics.test",
            "user_id": 3000,
            "plan": "free"
        },
        expires_delta=timedelta(hours=1)
    )


@pytest.fixture
def pro_token():
    """Generate a valid PRO plan JWT token."""
    return create_access_token(
        data={
            "sub": "pro@metrics.test",
            "user_id": 3001,
            "plan": "pro"
        },
        expires_delta=timedelta(hours=1)
    )


@pytest.fixture
def test_event_with_score(db_session):
    """Create a test event with score for metrics tests."""
    # Create company
    company = Company(
        ticker="METRICS_TEST",
        name="Metrics Test Company",
        sector="Technology",
        tracked=True
    )
    db_session.add(company)
    db_session.commit()
    
    # Create event
    event = Event(
        ticker="METRICS_TEST",
        company_name="Metrics Test Company",
        title="Metrics Test Event",
        event_type="earnings",
        date=datetime(2024, 6, 15, 16, 0, 0),
        source="test",
        impact_score=70,
        direction="positive",
        confidence=0.80,
        rationale="Test event for metrics"
    )
    db_session.add(event)
    db_session.commit()
    
    # Create score
    score = EventScore(
        event_id=event.id,
        ticker="METRICS_TEST",
        event_type="earnings",
        base_score=45,
        context_score=25,
        final_score=70,
        confidence=80,
        factor_sector=12,
        factor_volatility=8,
        factor_earnings_proximity=18,
        factor_market_mood=12,
        factor_after_hours=8,
        factor_duplicate_penalty=0,
        rationale="Metrics test score"
    )
    db_session.add(score)
    db_session.commit()
    
    return event


class TestMetricsEndpoint:
    """Test /metrics endpoint structure and content."""
    
    def test_metrics_endpoint_accessible(self):
        """Metrics endpoint should be publicly accessible (no auth required)."""
        client = TestClient(app)
        
        response = client.get("/metrics")
        
        assert response.status_code == 200, "Metrics endpoint should be accessible"
        assert response.headers.get("content-type") == "text/plain; charset=utf-8", "Should return plain text"
    
    def test_metrics_contains_required_counters(self):
        """Metrics response should contain all required Wave B counters."""
        client = TestClient(app)
        
        response = client.get("/metrics")
        content = response.text
        
        # Verify all required metrics are present
        required_metrics = [
            "scored_events_total",
            "score_cache_hits_total",
            "score_cache_misses_total",
            "scores_denied_free_total",
            "scores_served_total",
            "scores_cache_size",
            "rescore_requests_total",
        ]
        
        for metric in required_metrics:
            assert metric in content, f"Metrics should include {metric}"
    
    def test_metrics_prometheus_format(self):
        """Metrics should follow Prometheus text format."""
        client = TestClient(app)
        
        response = client.get("/metrics")
        content = response.text
        
        # Check for HELP and TYPE comments
        assert "# HELP" in content, "Should include HELP comments"
        assert "# TYPE" in content, "Should include TYPE comments"
        
        # Check for counter types
        assert "counter" in content, "Should have counter metrics"
        
        # Check for gauge types (cache size, uptime)
        assert "gauge" in content, "Should have gauge metrics"
    
    def test_metrics_include_uptime(self):
        """Metrics should include API uptime gauge."""
        client = TestClient(app)
        
        response = client.get("/metrics")
        content = response.text
        
        assert "api_uptime_seconds" in content, "Should include uptime metric"
        
        # Uptime should be a positive integer
        for line in content.split("\n"):
            if line.startswith("api_uptime_seconds "):
                uptime_str = line.split()[1]
                uptime = int(uptime_str)
                assert uptime >= 0, "Uptime should be non-negative"


class TestMetricsIncrement:
    """Test that metrics increment correctly based on API calls."""
    
    def test_free_user_denial_increments_denied_counter(
        self, test_event_with_score, free_token
    ):
        """FREE user accessing scores should increment denied counter."""
        client = TestClient(app)
        
        # Get baseline metrics
        baseline_response = client.get("/metrics")
        baseline_content = baseline_response.text
        baseline_denied = self._extract_metric_value(baseline_content, "scores_denied_free_total")
        
        # Make a FREE user request (should be denied)
        client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={"Authorization": f"Bearer {free_token}"}
        )
        
        # Get updated metrics
        updated_response = client.get("/metrics")
        updated_content = updated_response.text
        updated_denied = self._extract_metric_value(updated_content, "scores_denied_free_total")
        
        assert updated_denied > baseline_denied, "Denied counter should increment for FREE user"
    
    def test_pro_user_serve_increments_served_counter(
        self, test_event_with_score, pro_token
    ):
        """PRO user accessing scores should increment served counter."""
        client = TestClient(app)
        
        # Get baseline metrics
        baseline_response = client.get("/metrics")
        baseline_content = baseline_response.text
        baseline_served = self._extract_metric_value(baseline_content, "scores_served_total")
        
        # Make a PRO user request (should be served)
        client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={"Authorization": f"Bearer {pro_token}"}
        )
        
        # Get updated metrics
        updated_response = client.get("/metrics")
        updated_content = updated_response.text
        updated_served = self._extract_metric_value(updated_content, "scores_served_total")
        
        assert updated_served > baseline_served, "Served counter should increment for PRO user"
    
    def test_cache_hit_increments_cache_hit_counter(
        self, test_event_with_score, pro_token
    ):
        """Second identical request should increment cache hit counter."""
        client = TestClient(app)
        
        # Get baseline
        baseline_response = client.get("/metrics")
        baseline_content = baseline_response.text
        baseline_hits = self._extract_metric_value(baseline_content, "score_cache_hits_total")
        
        # First request (cache miss)
        response1 = client.get(
            f"/scores/events/{test_event_with_score.id}",
            headers={"Authorization": f"Bearer {pro_token}"}
        )
        etag = response1.headers.get("ETag") or response1.headers.get("etag")
        
        # Second request with ETag (cache hit)
        if etag:
            client.get(
                f"/scores/events/{test_event_with_score.id}",
                headers={
                    "Authorization": f"Bearer {pro_token}",
                    "If-None-Match": etag
                }
            )
            
            # Get updated metrics
            updated_response = client.get("/metrics")
            updated_content = updated_response.text
            updated_hits = self._extract_metric_value(updated_content, "score_cache_hits_total")
            
            assert updated_hits > baseline_hits, "Cache hit counter should increment on 304 response"
    
    def _extract_metric_value(self, metrics_text: str, metric_name: str) -> int:
        """Extract a metric value from Prometheus text format."""
        for line in metrics_text.split("\n"):
            if line.startswith(f"{metric_name} "):
                parts = line.split()
                if len(parts) >= 2:
                    return int(parts[1])
        return 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
