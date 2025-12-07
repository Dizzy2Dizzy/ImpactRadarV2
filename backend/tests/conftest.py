"""
Shared pytest fixtures for Impact Radar test suite.

Provides test database, test client, and user fixtures for integration tests.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, delete
from sqlalchemy.orm import sessionmaker, Session

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.main import app
from api.utils.auth import create_access_token
from releaseradar.db.models import (
    User, Company, Event, EventScore, PortfolioPosition, 
    UserPortfolio, ScanJob
)
from releaseradar.db.session import SessionLocal

# Pre-computed bcrypt hashes for test passwords (to avoid bcrypt initialization issues)
# These are hashes of: "testpass123"
TEST_PASSWORD_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5GyYqNY5o3nGO"


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.
    
    Uses the same database as the app but cleans up test data after each test.
    For production tests, consider using a separate test database or in-memory SQLite.
    """
    session = SessionLocal()
    
    try:
        # Clean up any existing test data using raw SQL for simplicity
        # This avoids SQLAlchemy session complexity and FK issues
        from sqlalchemy import text
        
        # Delete test data in correct order (dependent tables first)
        session.execute(text("DELETE FROM event_scores WHERE ticker LIKE 'TEST_%'"))
        session.execute(text("DELETE FROM alert_logs WHERE alert_id IN (SELECT id FROM alerts WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com'))"))
        session.execute(text("DELETE FROM alerts WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com')"))
        session.execute(text("DELETE FROM user_notifications WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com')"))
        session.execute(text("DELETE FROM api_keys WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com')"))
        session.execute(text("DELETE FROM scan_jobs WHERE created_by IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com')"))
        session.execute(text("DELETE FROM portfolio_positions WHERE portfolio_id IN (SELECT id FROM user_portfolios WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com'))"))
        session.execute(text("DELETE FROM user_portfolios WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com')"))
        session.execute(text("DELETE FROM events WHERE ticker LIKE 'TEST_%'"))
        session.execute(text("DELETE FROM companies WHERE ticker LIKE 'TEST_%'"))
        session.execute(text("DELETE FROM users WHERE email LIKE 'test_%@example.com'"))
        session.commit()
    except Exception as e:
        session.rollback()
    
    yield session
    
    try:
        # Clean up after test using raw SQL
        from sqlalchemy import text
        
        session.execute(text("DELETE FROM event_scores WHERE ticker LIKE 'TEST_%'"))
        session.execute(text("DELETE FROM alert_logs WHERE alert_id IN (SELECT id FROM alerts WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com'))"))
        session.execute(text("DELETE FROM alerts WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com')"))
        session.execute(text("DELETE FROM user_notifications WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com')"))
        session.execute(text("DELETE FROM api_keys WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com')"))
        session.execute(text("DELETE FROM scan_jobs WHERE created_by IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com')"))
        session.execute(text("DELETE FROM portfolio_positions WHERE portfolio_id IN (SELECT id FROM user_portfolios WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com'))"))
        session.execute(text("DELETE FROM user_portfolios WHERE user_id IN (SELECT id FROM users WHERE email LIKE 'test_%@example.com')"))
        session.execute(text("DELETE FROM events WHERE ticker LIKE 'TEST_%'"))
        session.execute(text("DELETE FROM companies WHERE ticker LIKE 'TEST_%'"))
        session.execute(text("DELETE FROM users WHERE email LIKE 'test_%@example.com'"))
        session.commit()
    except Exception as e:
        session.rollback()
    finally:
        session.close()


@pytest.fixture
def test_client():
    """FastAPI test client for making HTTP requests."""
    return TestClient(app)


@pytest.fixture
def admin_user(db_session: Session):
    """
    Create an admin user for testing admin-protected endpoints.
    
    Returns dict with user_id, email, token, and is_admin flag.
    """
    # Create admin user (use pre-computed hash to avoid bcrypt issues)
    admin = User(
        email="test_admin@example.com",
        password_hash=TEST_PASSWORD_HASH,
        plan="team",
        is_admin=True,
        is_verified=True
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)
    
    # Create admin token
    token = create_access_token(
        data={
            "sub": admin.email,
            "user_id": admin.id,
            "plan": admin.plan
        },
        expires_delta=timedelta(hours=1)
    )
    
    return {
        "user_id": admin.id,
        "email": admin.email,
        "token": token,
        "is_admin": True,
        "plan": "team"
    }


@pytest.fixture
def regular_user(db_session: Session):
    """
    Create a regular (non-admin) user for testing access control.
    
    Returns dict with user_id, email, token, and is_admin flag.
    """
    # Create regular user (use pre-computed hash to avoid bcrypt issues)
    user = User(
        email="test_regular@example.com",
        password_hash=TEST_PASSWORD_HASH,
        plan="free",
        is_admin=False,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    # Create user token
    token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "plan": user.plan
        },
        expires_delta=timedelta(hours=1)
    )
    
    return {
        "user_id": user.id,
        "email": user.email,
        "token": token,
        "is_admin": False,
        "plan": "free"
    }


@pytest.fixture
def pro_user(db_session: Session):
    """
    Create a Pro plan user for testing plan-based features.
    
    Returns dict with user_id, email, token, and plan.
    """
    user = User(
        email="test_pro@example.com",
        password_hash=TEST_PASSWORD_HASH,
        plan="pro",
        is_admin=False,
        is_verified=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "plan": user.plan
        },
        expires_delta=timedelta(hours=1)
    )
    
    return {
        "user_id": user.id,
        "email": user.email,
        "token": token,
        "is_admin": False,
        "plan": "pro"
    }


@pytest.fixture
def test_company(db_session: Session):
    """Create a test company for testing."""
    company = Company(
        ticker="TEST_AAPL",
        name="Test Apple Inc.",
        sector="Technology",
        industry="Consumer Electronics",
        tracked=True
    )
    db_session.add(company)
    db_session.commit()
    db_session.refresh(company)
    return company


@pytest.fixture
def test_event(db_session: Session, test_company):
    """Create a test event for testing."""
    event = Event(
        ticker=test_company.ticker,
        company_name=test_company.name,
        title="Test Product Launch",
        event_type="product_launch",
        date=datetime.now(timezone.utc),
        source="Test Source",
        source_url="https://example.com/test",
        raw_id="test_product_launch_test_aapl_20251113_abc123",
        source_scanner="test_scanner",
        sector=test_company.sector,
        impact_score=75,
        direction="positive",
        confidence=0.85
    )
    db_session.add(event)
    db_session.commit()
    db_session.refresh(event)
    return event
