"""
DEPRECATED: Use releaseradar.db.session instead.

This module re-exports session management from releaseradar.db.session
for backward compatibility. All new code should import from releaseradar.db.session.
"""

from releaseradar.db.session import (
    engine,
    SessionLocal,
    init_db,
    get_db,
    close_db,
    close_db_session,
    get_db_context,
    get_db_transaction,
    get_scanner_db_context,
    scanner_circuit_breaker,
    pool_health,
    check_db_health,
    reset_db_connections,
    cleanup_idle_transactions,
    CircuitBreaker,
    ConnectionPoolHealth,
)

from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Company(Base):
    """Company model for tracking tickers, subsidiaries, and parent relationships."""
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey('companies.id'), nullable=True)
    tracked = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Event(Base):
    """Event model for tracking company events with impact scoring and directional analysis."""
    __tablename__ = "events"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, index=True, nullable=False)
    company_name = Column(String, nullable=False)
    event_type = Column(String, nullable=False)  # earnings, sec_filing, fda, product_launch, guidance, corporate_action
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String, nullable=False)  # SEC, FDA, IR, Manual
    source_url = Column(String, nullable=True)
    raw_id = Column(String, nullable=True, index=True)
    source_scanner = Column(String, nullable=True, index=True)
    impact_score = Column(Integer, default=50)  # 0-100
    direction = Column(String, nullable=True)  # positive, negative, neutral, uncertain
    confidence = Column(Float, default=0.5)  # 0-1
    rationale = Column(Text, nullable=True)  # Impact scoring rationale
    subsidiary_name = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    info_tier = Column(String, nullable=False, default="primary", index=True)  # "primary" or "secondary"
    info_subtype = Column(String, nullable=True)  # Optional granular classification
    impact_p_move = Column(Float, nullable=True)  # Probability of significant move (0-1)
    impact_p_up = Column(Float, nullable=True)  # Probability of upward move (0-1)
    impact_p_down = Column(Float, nullable=True)  # Probability of downward move (0-1)
    impact_score_version = Column(Integer, nullable=True)  # 1=deterministic, 2=probabilistic
    ml_adjusted_score = Column(Integer, nullable=True)  # ML-predicted impact score (0-100)
    ml_confidence = Column(Float, nullable=True)  # ML model confidence (0.0-1.0)
    ml_model_version = Column(String, nullable=True)  # Version identifier of ML model used
    model_source = Column(String, nullable=True)  # "family-specific", "global", or "deterministic"
    delta_applied = Column(Float, nullable=True)  # Change from base score (ML adjustment delta)
    detected_at = Column(DateTime(timezone=True), nullable=True, default=datetime.utcnow, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class WatchlistItem(Base):
    """User watchlist items for tracking specific tickers."""
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)  # nullable for now, default 1
    ticker = Column(String, index=True, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class ScannerLog(Base):
    """Scanner execution logs for monitoring and debugging."""
    __tablename__ = "scanner_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    scanner = Column(String, index=True, nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String, default="info")  # info, error, warning

class User(Base):
    """User model with bcrypt password hashing and verification."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=False)  # bcrypt hashed
    plan = Column(String, nullable=False, default="free")  # free, pro, team
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    verification_method = Column(String, nullable=True)  # email or phone
    dashboard_mode = Column(String, nullable=False, default="watchlist")  # watchlist, portfolio
    username = Column(String, nullable=True)  # Display name / username
    avatar_url = Column(Text, nullable=True)  # Base64 encoded avatar image or URL
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

class VerificationCode(Base):
    """Verification codes for email/SMS authentication with expiry enforcement."""
    __tablename__ = "verification_codes"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    code = Column(String, nullable=False)
    method = Column(String, nullable=False)  # email or phone
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
