"""
SQLAlchemy 2.0 database models for Impact Radar.

Migrated from database.py with improved type hints, constraints, and indexes.
Schema remains identical to preserve existing data.
"""

from datetime import datetime
from typing import Optional

from sqlalchemy import (
    ARRAY,
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import ARRAY as PG_ARRAY, JSON
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Company(Base):
    """Company model for tracking tickers, subsidiaries, and parent relationships."""
    
    __tablename__ = "companies"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, nullable=False)
    sector = Column(String, nullable=True)
    industry = Column(String, nullable=True)
    parent_id = Column(Integer, ForeignKey("companies.id"), nullable=True)
    tracked = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    parent = relationship("Company", remote_side=[id], backref="subsidiaries")
    
    def __repr__(self) -> str:
        return f"<Company(id={self.id}, ticker={self.ticker}, name={self.name})>"


class Event(Base):
    """Event model for tracking company events with impact scoring and directional analysis."""
    
    __tablename__ = "events"
    __table_args__ = (
        UniqueConstraint('ticker', 'event_type', 'raw_id', name='uix_event_natural_key'),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, index=True, nullable=False)
    company_name = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    source = Column(String, nullable=False)
    source_url = Column(String, nullable=True)
    raw_id = Column(String, nullable=True, index=True)
    source_scanner = Column(String, nullable=True, index=True)
    impact_score = Column(Integer, default=50)
    direction = Column(String, nullable=True)
    confidence = Column(Float, default=0.5)
    rationale = Column(Text, nullable=True)
    subsidiary_name = Column(String, nullable=True)
    sector = Column(String, nullable=True)
    
    # Probabilistic scoring fields
    impact_p_move = Column(Float, nullable=True)  # Probability of |move| > threshold
    impact_p_up = Column(Float, nullable=True)    # Probability of upward move > threshold
    impact_p_down = Column(Float, nullable=True)  # Probability of downward move > threshold
    impact_score_version = Column(Integer, default=1)  # 1=deterministic, 2=probabilistic
    
    # Wave J: Information Tiers
    info_tier = Column(String, nullable=False, default="primary", index=True)  # "primary" or "secondary"
    info_subtype = Column(String, nullable=True)  # Optional granular classification (e.g., "ipo", "earnings", "regulatory_primary")
    
    # ML-adjusted scoring fields (Wave L: AI Self-Learning)
    ml_adjusted_score = Column(Integer, nullable=True)  # ML-predicted impact score (0-100)
    ml_confidence = Column(Float, nullable=True)  # ML model confidence (0.0-1.0)
    ml_model_version = Column(String, nullable=True)  # Version identifier of ML model used
    model_source = Column(String, nullable=True)  # "family-specific", "global", or "deterministic"
    delta_applied = Column(Float, nullable=True)  # Change from base score (ML adjustment delta)
    
    # Growth marketing: Track when event was first detected for time-advantage metrics
    detected_at = Column(DateTime(timezone=True), nullable=True, default=datetime.utcnow, index=True)
    
    # Bearish signal fields for negative stock predictions
    bearish_signal = Column(Boolean, nullable=True, default=False, index=True)  # True if high-confidence bearish prediction
    bearish_score = Column(Float, nullable=True)  # Normalized bearish severity score (0.0-1.0)
    bearish_confidence = Column(Float, nullable=True)  # Confidence in bearish signal (0.0-1.0)
    bearish_rationale = Column(Text, nullable=True)  # Explanation for bearish classification
    
    # Contrarian/Hidden Bearish fields (Market Echo Engine learning from outcomes)
    contrarian_outcome = Column(Boolean, nullable=True, index=True)  # True if actual outcome contradicted prediction
    realized_direction = Column(String, nullable=True)  # Actual direction based on T+1 price movement
    realized_return_1d = Column(Float, nullable=True)  # Actual T+1 return percentage
    hidden_bearish_prob = Column(Float, nullable=True)  # Probability of hidden bearish (from contrarian patterns)
    hidden_bearish_signal = Column(Boolean, nullable=True, index=True)  # True if hidden bearish based on patterns
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<Event(id={self.id}, ticker={self.ticker}, type={self.event_type}, date={self.date})>"


class WatchlistItem(Base):
    """User watchlist items for tracking specific tickers."""
    
    __tablename__ = "watchlist"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=True, index=True)
    ticker = Column(String, index=True, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<WatchlistItem(id={self.id}, user_id={self.user_id}, ticker={self.ticker})>"


class ScannerLog(Base):
    """Scanner execution logs for monitoring and debugging."""
    
    __tablename__ = "scanner_logs"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    scanner = Column(String, index=True, nullable=False)
    message = Column(Text, nullable=False)
    level = Column(String, default="info")
    
    def __repr__(self) -> str:
        return f"<ScannerLog(id={self.id}, scanner={self.scanner}, level={self.level})>"


class ScanJob(Base):
    """Manual scan job queue for on-demand company or scanner rescans."""
    
    __tablename__ = "scan_jobs"
    __table_args__ = (
        Index("ix_scan_jobs_status_created", "status", "created_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # Null for system/admin-triggered scans
    scope = Column(String, nullable=False)  # "company" or "scanner"
    ticker = Column(String, nullable=True)
    scanner_key = Column(String, nullable=True)
    status = Column(String, nullable=False, default="queued", index=True)  # queued, running, success, error
    started_at = Column(DateTime, nullable=True)
    finished_at = Column(DateTime, nullable=True)
    items_found = Column(Integer, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self) -> str:
        return f"<ScanJob(id={self.id}, scope={self.scope}, status={self.status})>"


class User(Base):
    """User model with bcrypt password hashing and verification."""
    
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    email = Column(String, unique=True, index=True, nullable=True)
    phone = Column(String, unique=True, index=True, nullable=True)
    password_hash = Column(String, nullable=False)
    plan = Column(String, nullable=False, default="free")  # free, pro, team
    is_verified = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    verification_method = Column(String, nullable=True)
    dashboard_mode = Column(String, nullable=False, default="watchlist")  # watchlist, portfolio
    username = Column(String, nullable=True)  # Display name / username
    avatar_url = Column(Text, nullable=True)  # Base64 encoded avatar image or URL
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    trial_ends_at = Column(DateTime, nullable=True)
    stripe_customer_id = Column(String, unique=True, index=True, nullable=True)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email}, verified={self.is_verified}, plan={self.plan})>"


class VerificationCode(Base):
    """Verification codes for email/SMS authentication with expiry enforcement."""
    
    __tablename__ = "verification_codes"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, nullable=False)
    code = Column(String, nullable=False)
    method = Column(String, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<VerificationCode(id={self.id}, user_id={self.user_id}, method={self.method})>"


class ApiKey(Base):
    """API keys for Pro and Team plan users with SHA-256 hashed storage and quota tracking."""
    
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    key_hash = Column(String(128), nullable=False, unique=True, index=True)
    plan = Column(String(16), nullable=False)
    status = Column(String(16), default="active")
    monthly_call_limit = Column(Integer, nullable=False, default=10000)
    calls_used = Column(Integer, nullable=False, default=0)
    cycle_start = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_used_at = Column(DateTime, nullable=True)
    
    def __repr__(self) -> str:
        return f"<ApiKey(id={self.id}, user_id={self.user_id}, plan={self.plan}, status={self.status})>"


# ============================================================================
# WAVE A: BACKTESTING MODELS
# ============================================================================

class PriceHistory(Base):
    """Historical price data for backtesting event impact analysis."""
    
    __tablename__ = "price_history"
    __table_args__ = (
        UniqueConstraint("ticker", "date", name="uq_price_history_ticker_date"),
        Index("ix_price_history_ticker", "ticker"),
        Index("ix_price_history_date", "date"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, nullable=False)
    date = Column(Date, nullable=False)
    open = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    source = Column(String, default="yahoo")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<PriceHistory(ticker={self.ticker}, date={self.date}, close={self.close})>"


class EventStats(Base):
    """Statistical analysis of historical event impact by ticker and event type."""
    
    __tablename__ = "event_stats"
    __table_args__ = (
        UniqueConstraint("ticker", "event_type", name="uq_event_stats_ticker_event_type"),
        Index("ix_event_stats_ticker", "ticker"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, nullable=False)
    event_type = Column(String, nullable=False)
    sample_size = Column(Integer, nullable=False, default=0)
    win_rate = Column(Float, nullable=True)
    avg_abs_move_1d = Column(Float, nullable=True)
    avg_abs_move_5d = Column(Float, nullable=True)
    avg_abs_move_20d = Column(Float, nullable=True)
    mean_move_1d = Column(Float, nullable=True)
    mean_move_5d = Column(Float, nullable=True)
    mean_move_20d = Column(Float, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<EventStats(ticker={self.ticker}, type={self.event_type}, samples={self.sample_size})>"


# ============================================================================
# WAVE B: DYNAMIC SCORING MODELS
# ============================================================================

class EventScore(Base):
    """Dynamic context-aware scoring for events with rule-based engine."""
    
    __tablename__ = "event_scores"
    __table_args__ = (
        Index("ix_event_scores_event_id", "event_id"),
        Index("ix_event_scores_ticker", "ticker"),
        Index("ix_event_scores_ticker_event_type", "ticker", "event_type"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, unique=True)
    ticker = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=False)
    base_score = Column(Integer, nullable=False)
    context_score = Column(Integer, nullable=False)
    final_score = Column(Integer, nullable=False)
    confidence = Column(Integer, nullable=False, default=70)
    rationale = Column(Text, nullable=True)
    
    # Individual factor contributions (Wave B)
    factor_sector = Column(Integer, nullable=False, default=0)
    factor_volatility = Column(Integer, nullable=False, default=0)
    factor_earnings_proximity = Column(Integer, nullable=False, default=0)
    factor_market_mood = Column(Integer, nullable=False, default=0)
    factor_after_hours = Column(Integer, nullable=False, default=0)
    factor_duplicate_penalty = Column(Integer, nullable=False, default=0)
    
    # ML-adjusted scoring fields (Wave L: AI Self-Learning)
    ml_adjusted_score = Column(Integer, nullable=True)  # ML-predicted impact score (0-100)
    ml_confidence = Column(Float, nullable=True)  # ML model confidence (0.0-1.0)
    ml_model_version = Column(String, nullable=True)  # Version identifier of ML model used
    
    computed_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    event = relationship("Event", backref="score")
    
    def __repr__(self) -> str:
        return f"<EventScore(event_id={self.event_id}, ticker={self.ticker}, final={self.final_score}, conf={self.confidence})>"


# ============================================================================
# WAVE C: ALERTS MODELS
# ============================================================================

class Alert(Base):
    """User-configured alerts with filters for tickers, sectors, scores, and keywords."""
    
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_user_id", "user_id"),
        Index("ix_alerts_active", "active"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    min_score = Column(Integer, default=0)
    tickers = Column(PG_ARRAY(String), nullable=True)
    sectors = Column(PG_ARRAY(String), nullable=True)
    event_types = Column(PG_ARRAY(String), nullable=True)
    keywords = Column(PG_ARRAY(String), nullable=True)
    channels = Column(PG_ARRAY(String), default=["in_app"])
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Webhook integration fields (Team plan only)
    webhook_url = Column(String, nullable=True)  # Custom webhook URL
    slack_webhook_url = Column(String, nullable=True)  # Slack incoming webhook URL
    discord_webhook_url = Column(String, nullable=True)  # Discord webhook URL
    
    # Relationship
    user = relationship("User", backref="alerts")
    
    def __repr__(self) -> str:
        return f"<Alert(id={self.id}, user_id={self.user_id}, name={self.name})>"


class AlertLog(Base):
    """Log of triggered alerts for auditing, deduplication, and rate limiting."""
    
    __tablename__ = "alert_logs"
    __table_args__ = (
        Index("ix_alert_logs_alert_id", "alert_id"),
        Index("ix_alert_logs_sent_at", "sent_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    sent_at = Column(DateTime, default=datetime.utcnow)
    channel = Column(String, nullable=False)
    status = Column(String, default="pending")  # pending, sent, failed
    dedupe_key = Column(String, nullable=False, unique=True, index=True)  # "{alert_id}:{event_id}:{channel}"
    error = Column(Text, nullable=True)
    
    # Relationships
    alert = relationship("Alert", backref="logs")
    event = relationship("Event", backref="alert_logs")
    
    def __repr__(self) -> str:
        return f"<AlertLog(id={self.id}, alert_id={self.alert_id}, status={self.status})>"


class UserNotification(Base):
    """In-app notifications for users."""
    
    __tablename__ = "user_notifications"
    __table_args__ = (
        Index("ix_user_notifications_user_id", "user_id"),
        Index("ix_user_notifications_created_at", "created_at"),
        Index("ix_user_notifications_read_at", "read_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    body = Column(Text, nullable=False)
    url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    read_at = Column(DateTime, nullable=True)
    
    # Relationship
    user = relationship("User", backref="notifications")
    
    def __repr__(self) -> str:
        return f"<UserNotification(id={self.id}, user_id={self.user_id}, title={self.title})>"


# ============================================================================
# WAVE D: PORTFOLIO MODELS
# ============================================================================

class UserPortfolio(Base):
    """User portfolio container for grouping positions."""
    
    __tablename__ = "user_portfolios"
    __table_args__ = (
        Index("ix_user_portfolios_user_id", "user_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", backref="portfolios")
    
    def __repr__(self) -> str:
        return f"<UserPortfolio(id={self.id}, user_id={self.user_id}, name={self.name})>"


class PortfolioPosition(Base):
    """Individual positions within a portfolio."""
    
    __tablename__ = "portfolio_positions"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "ticker", name="uq_portfolio_positions_portfolio_ticker"),
        Index("ix_portfolio_positions_portfolio_id", "portfolio_id"),
        Index("ix_portfolio_positions_ticker", "ticker"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("user_portfolios.id", ondelete="CASCADE"), nullable=False)
    ticker = Column(String, nullable=False)
    qty = Column(Float, nullable=False)
    avg_price = Column(Float, nullable=False)
    as_of = Column(Date, nullable=False)
    label = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    portfolio = relationship("UserPortfolio", backref="positions")
    
    def __repr__(self) -> str:
        return f"<PortfolioPosition(portfolio_id={self.portfolio_id}, ticker={self.ticker}, qty={self.qty})>"


# ============================================================================
# WAVE J: INFORMATION TIERS - CONTEXT SIGNALS
# ============================================================================

class ContextSignal(Base):
    """Secondary context signals for environmental, infrastructure, and macro risk factors.
    
    These represent contextual risks that may influence stock sensitivity to events,
    but are not direct market-moving catalysts like SEC/FDA filings.
    """
    
    __tablename__ = "context_signals"
    __table_args__ = (
        Index("ix_context_signals_ticker", "ticker"),
        Index("ix_context_signals_source", "source"),
        Index("ix_context_signals_observed_at", "observed_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, index=True, nullable=False)
    source = Column(String, nullable=False)  # e.g., "env", "infra", "macro", "geopolitical"
    signal_type = Column(String, nullable=False)  # e.g., "water_risk", "power_risk", "supply_chain_risk"
    severity = Column(Integer, nullable=False, default=50)  # 0-100 risk score
    description = Column(Text, nullable=False)
    observed_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<ContextSignal(ticker={self.ticker}, type={self.signal_type}, severity={self.severity})>"


# ============================================================================
# PROBABILISTIC IMPACT SCORING MODELS
# ============================================================================

class EventGroupPrior(Base):
    """Historical event statistics grouped by event type, sector, and market cap.
    
    Used for probabilistic impact scoring based on historical abnormal returns.
    Each group represents a collection of similar events with computed mean, 
    standard deviation, and sample size.
    """
    
    __tablename__ = "event_group_priors"
    __table_args__ = (
        UniqueConstraint("event_type", "sector", "cap_bucket", name="uq_event_group_priors_key"),
        Index("ix_event_group_priors_event_type", "event_type"),
        Index("ix_event_group_priors_sector", "sector"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    sector = Column(String, nullable=False)
    cap_bucket = Column(String, nullable=False)  # "small", "mid", "large"
    mu = Column(Float, nullable=False)  # mean abnormal return (%)
    sigma = Column(Float, nullable=False)  # std dev of abnormal returns (%)
    n = Column(Integer, nullable=False)  # number of historical events
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<EventGroupPrior(type={self.event_type}, sector={self.sector}, cap={self.cap_bucket}, n={self.n})>"


# ============================================================================
# WAVE K: CUSTOM SCORING PREFERENCES
# ============================================================================

class UserScoringPreference(Base):
    """User-specific scoring preferences for customizing impact scoring weights.
    
    Allows traders to adjust scoring based on their trading strategy and risk preferences.
    """
    
    __tablename__ = "user_scoring_preferences"
    __table_args__ = (
        Index("ix_user_scoring_preferences_user_id", "user_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    event_type_weights = Column(JSON, nullable=True)  # {"fda_approval": 1.5, "sec_8k": 0.8}
    sector_weights = Column(JSON, nullable=True)  # {"Healthcare": 1.2, "Technology": 1.0}
    confidence_threshold = Column(Float, default=0.5)  # Only show events above this confidence
    min_impact_score = Column(Integer, default=0)  # Filter out low-impact events
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", backref="scoring_preferences")
    
    def __repr__(self) -> str:
        return f"<UserScoringPreference(user_id={self.user_id})>"


# ============================================================================
# WAVE L: AI SELF-LEARNING IMPACT SCORING
# ============================================================================

class EventOutcome(Base):
    """Stores realized price movements (T+1) for events to create training labels.
    
    Captures actual stock price movements after events to train ML models that
    predict future event impact. Supports multiple time horizons (1d, 5d, 20d).
    """
    
    __tablename__ = "event_outcomes"
    __table_args__ = (
        UniqueConstraint("event_id", "horizon", name="uq_event_outcomes_event_horizon"),
        Index("ix_event_outcomes_event_id", "event_id"),
        Index("ix_event_outcomes_ticker", "ticker"),
        Index("ix_event_outcomes_label_date", "label_date"),
        Index("ix_event_outcomes_horizon", "horizon"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    ticker = Column(String, nullable=False)
    horizon = Column(String, nullable=False)  # "1d", "5d", "20d"
    price_before = Column(Float, nullable=False)  # Close price before event
    price_after = Column(Float, nullable=False)  # Close price after horizon
    return_pct_raw = Column(Float, nullable=True)  # Raw stock return (before benchmark adjustment)
    benchmark_return_pct = Column(Float, nullable=True)  # SPY benchmark return for same period
    return_pct = Column(Float, nullable=False)  # Abnormal return (stock - benchmark) - PRIMARY TARGET
    abs_return_pct = Column(Float, nullable=False)  # Absolute return (for impact magnitude)
    direction_correct = Column(Boolean, nullable=True)  # Was predicted direction correct?
    has_benchmark_data = Column(Boolean, default=False)  # True if SPY data was available
    label_date = Column(Date, nullable=False)  # Date when label was computed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    event = relationship("Event", backref="outcomes")
    
    def __repr__(self) -> str:
        return f"<EventOutcome(event_id={self.event_id}, ticker={self.ticker}, horizon={self.horizon}, return={self.return_pct:.2f}%)>"


class ModelFeature(Base):
    """Feature snapshots for ML training.
    
    Stores engineered features at event time for training and prediction.
    Features include base scores, market context, sector, volatility, etc.
    """
    
    __tablename__ = "model_features"
    __table_args__ = (
        UniqueConstraint("event_id", "horizon", name="uq_model_features_event_horizon"),
        Index("ix_model_features_event_id", "event_id"),
        Index("ix_model_features_feature_version", "feature_version"),
        Index("ix_model_features_extracted_at", "extracted_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    horizon = Column(String, nullable=False)  # "1d", "5d", "20d"
    features = Column(JSON, nullable=False)  # Full feature vector as JSON
    feature_version = Column(String, nullable=False)  # Feature schema version (e.g., "v1.0")
    
    # Key scalar features (duplicated for fast filtering/analysis)
    base_score = Column(Integer, nullable=True)
    sector = Column(String, nullable=True)
    event_type = Column(String, nullable=True)
    market_vol = Column(Float, nullable=True)
    info_tier = Column(String, nullable=True)
    
    extracted_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    event = relationship("Event", backref="features")
    
    def __repr__(self) -> str:
        return f"<ModelFeature(event_id={self.event_id}, horizon={self.horizon}, version={self.feature_version})>"


class ModelRegistry(Base):
    """Tracks trained ML models and their performance metrics.
    
    Maintains model versioning, status (staging/active/archived), and performance
    metrics for model promotion and rollback decisions.
    """
    
    __tablename__ = "model_registry"
    __table_args__ = (
        UniqueConstraint("name", "version", name="uq_model_registry_name_version"),
        Index("ix_model_registry_status", "status"),
        Index("ix_model_registry_trained_at", "trained_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)  # Model name (e.g., "xgboost_impact_1d_sec_8k")
    version = Column(String, nullable=False)  # Semantic version (e.g., "1.2.3")
    event_type_family = Column(String, nullable=True, index=True)  # Event family this model was trained on (e.g., "sec_8k", "earnings", "all")
    horizon = Column(String, nullable=True, index=True)  # Time horizon (e.g., "1d", "5d", "20d")
    status = Column(String, nullable=False, default="staging")  # "staging", "active", "archived"
    model_path = Column(String, nullable=False)  # Path to serialized model file
    metrics = Column(JSON, nullable=False)  # Performance metrics (MAE, RMSE, directional_accuracy, etc.)
    feature_version = Column(String, nullable=False)  # Compatible feature schema version
    trained_at = Column(DateTime, default=datetime.utcnow)
    promoted_at = Column(DateTime, nullable=True)  # When model was promoted to active
    cohort_pct = Column(Float, nullable=True)  # % of traffic to route to this model (for A/B testing)
    
    def __repr__(self) -> str:
        return f"<ModelRegistry(name={self.name}, version={self.version}, status={self.status})>"


# ============================================================================
# DATA QUALITY AND VALIDATION MODELS
# ============================================================================

class DataQualitySnapshot(Base):
    """Data quality snapshots for monitoring metric freshness and completeness.
    
    Tracks quality metrics for various data sources and scopes (global, portfolio, watchlist).
    Used to surface data quality warnings in dashboards and admin panels.
    """
    
    __tablename__ = "data_quality_snapshots"
    __table_args__ = (
        Index("ix_data_quality_snapshots_metric_key", "metric_key"),
        Index("ix_data_quality_snapshots_created_at", "created_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    metric_key = Column(String, nullable=False, index=True)  # e.g., "events_total", "prices_spy", "ml_outcomes_1d"
    scope = Column(String, nullable=False)  # "global", "portfolio", "watchlist"
    sample_count = Column(Integer, nullable=False)  # Number of records in this snapshot
    freshness_ts = Column(DateTime, nullable=False)  # Timestamp of most recent data point
    source_job = Column(String, nullable=False)  # Job that generated this snapshot (e.g., "fetch_prices", "ml_learning_pipeline")
    quality_grade = Column(String, nullable=False)  # "excellent", "good", "fair", "stale"
    summary_json = Column(JSON, nullable=True)  # Additional metadata (e.g., {"avg_age_hours": 2.5, "missing_tickers": []})
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self) -> str:
        return f"<DataQualitySnapshot(metric_key={self.metric_key}, grade={self.quality_grade}, samples={self.sample_count})>"


class DataPipelineRun(Base):
    """Pipeline execution logs for data jobs (ETL, scanners, backfills).
    
    Tracks job execution status, timing, and outcomes for monitoring and debugging.
    Used to detect pipeline failures and surface alerts to ops team.
    """
    
    __tablename__ = "data_pipeline_runs"
    __table_args__ = (
        Index("ix_data_pipeline_runs_job_name", "job_name"),
        Index("ix_data_pipeline_runs_status", "status"),
        Index("ix_data_pipeline_runs_started_at", "started_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    job_name = Column(String, nullable=False, index=True)  # e.g., "fetch_prices", "ml_learning_pipeline", "scanner_fda"
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, nullable=False, index=True)  # "running", "success", "failure"
    rows_written = Column(Integer, nullable=True)  # Number of records created/updated
    source_hash = Column(String, nullable=True)  # Hash of source data for change detection
    error_blob = Column(Text, nullable=True)  # Error message/stack trace if failed
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<DataPipelineRun(job_name={self.job_name}, status={self.status}, rows={self.rows_written})>"


class DataLineageRecord(Base):
    """Data lineage tracking for provenance and debugging.
    
    Tracks source URLs and payloads for events, outcomes, prices, and models.
    Used to trace back where data came from and verify data integrity.
    """
    
    __tablename__ = "data_lineage_records"
    __table_args__ = (
        Index("ix_data_lineage_records_metric_key", "metric_key"),
        Index("ix_data_lineage_records_entity_type", "entity_type"),
        Index("ix_data_lineage_records_observed_at", "observed_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    metric_key = Column(String, nullable=False, index=True)  # e.g., "event_created", "outcome_labeled", "price_backfilled"
    entity_id = Column(Integer, nullable=False)  # ID of the created/updated entity
    entity_type = Column(String, nullable=False, index=True)  # "event", "outcome", "price", "model"
    source_url = Column(String, nullable=True)  # Original source URL (e.g., SEC filing URL, FDA announcement URL)
    payload_hash = Column(String, nullable=True)  # Hash of source payload for deduplication
    observed_at = Column(DateTime, nullable=False, index=True)
    
    def __repr__(self) -> str:
        return f"<DataLineageRecord(metric_key={self.metric_key}, entity_type={self.entity_type}, entity_id={self.entity_id})>"


class AuditLogEntry(Base):
    """Audit log for tracking entity mutations (create, update, delete).
    
    Records all data modifications for compliance, debugging, and security.
    Includes diffs for updates and optional digital signatures for tamper detection.
    """
    
    __tablename__ = "audit_log_entries"
    __table_args__ = (
        Index("ix_audit_log_entries_entity_type", "entity_type"),
        Index("ix_audit_log_entries_created_at", "created_at"),
        Index("ix_audit_log_entries_performed_by", "performed_by"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    entity_type = Column(String, nullable=False, index=True)  # "event", "user", "portfolio", etc.
    entity_id = Column(Integer, nullable=False)
    action = Column(String, nullable=False)  # "create", "update", "delete"
    performed_by = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # user_id (null for system actions)
    diff_json = Column(JSON, nullable=True)  # JSON diff for updates ({"field": {"old": x, "new": y}})
    signature = Column(String, nullable=True)  # Optional digital signature for tamper detection
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", backref="audit_logs")
    
    def __repr__(self) -> str:
        return f"<AuditLogEntry(entity_type={self.entity_type}, entity_id={self.entity_id}, action={self.action})>"


# ==================== ACCURACY DASHBOARD MODELS ====================

class PredictionMetrics(Base):
    """Aggregated prediction accuracy metrics by model, event type, and time horizon.
    
    Tracks win rates, MAE, directional accuracy, and other performance metrics.
    Updated daily by scheduled job comparing predictions to actual outcomes.
    """
    
    __tablename__ = "prediction_metrics"
    __table_args__ = (
        UniqueConstraint("model_version", "event_type", "horizon", "date", name="uq_prediction_metrics"),
        Index("ix_prediction_metrics_date", "date"),
        Index("ix_prediction_metrics_model_version", "model_version"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_version = Column(String, nullable=False)  # "v1.0", "v2.0", etc.
    event_type = Column(String, nullable=False)  # "fda_approval", "earnings", etc.
    horizon = Column(String, nullable=False)  # "1d", "7d", "30d"
    date = Column(Date, nullable=False, index=True)  # Date of metric calculation
    
    # Accuracy metrics
    total_predictions = Column(Integer, nullable=False, default=0)
    correct_direction = Column(Integer, nullable=False, default=0)
    win_rate = Column(Float, nullable=True)  # Percentage of correct directions
    mae = Column(Float, nullable=True)  # Mean absolute error (predicted vs actual return)
    rmse = Column(Float, nullable=True)  # Root mean squared error
    sharpe_ratio = Column(Float, nullable=True)  # Risk-adjusted returns
    avg_confidence = Column(Float, nullable=True)  # Average model confidence
    
    # Performance by confidence bucket
    high_conf_win_rate = Column(Float, nullable=True)  # Win rate for confidence > 0.7
    med_conf_win_rate = Column(Float, nullable=True)  # Win rate for 0.4 < confidence <= 0.7
    low_conf_win_rate = Column(Float, nullable=True)  # Win rate for confidence <= 0.4
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<PredictionMetrics(model={self.model_version}, type={self.event_type}, horizon={self.horizon}, win_rate={self.win_rate})>"


class PredictionSnapshot(Base):
    """Individual prediction snapshots for trend tracking and debugging.
    
    Stores point-in-time accuracy metrics for charting performance over time.
    """
    
    __tablename__ = "prediction_snapshots"
    __table_args__ = (
        Index("ix_prediction_snapshots_timestamp", "timestamp"),
        Index("ix_prediction_snapshots_model_version", "model_version"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_version = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)
    overall_win_rate = Column(Float, nullable=True)
    overall_mae = Column(Float, nullable=True)
    total_events_scored = Column(Integer, nullable=False, default=0)
    metrics_json = Column(JSON, nullable=True)  # Full metrics breakdown
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<PredictionSnapshot(model={self.model_version}, time={self.timestamp}, win_rate={self.overall_win_rate})>"


# ==================== EVENT PATTERN DETECTION MODELS ====================

class PatternDefinition(Base):
    """User-defined or system patterns for multi-event correlation detection.
    
    Defines conditions that trigger pattern alerts when multiple signals align.
    """
    
    __tablename__ = "pattern_definitions"
    __table_args__ = (
        Index("ix_pattern_definitions_created_by", "created_by"),
        Index("ix_pattern_definitions_active", "active"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String, nullable=False)  # "Bullish Convergence", "FDA + Insider Buying"
    description = Column(Text, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)  # null for system patterns
    active = Column(Boolean, default=True, index=True)
    
    # Pattern conditions (JSON)
    conditions = Column(JSON, nullable=False)  # {"event_types": ["fda_approval", "insider_buy"], "min_score": 70}
    time_window_days = Column(Integer, default=7)  # Events must occur within this window
    min_correlation_score = Column(Float, default=0.6)  # Minimum correlation threshold
    
    # Alert settings
    alert_channels = Column(PG_ARRAY(String), nullable=True)  # ["email", "in_app"]
    priority = Column(String, default="medium")  # "low", "medium", "high"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", backref="pattern_definitions")
    
    def __repr__(self) -> str:
        return f"<PatternDefinition(id={self.id}, name={self.name}, active={self.active})>"


class PatternAlert(Base):
    """Triggered pattern alerts when multiple events align for same company.
    
    Records detected multi-event correlations with aggregated impact score.
    """
    
    __tablename__ = "pattern_alerts"
    __table_args__ = (
        Index("ix_pattern_alerts_ticker", "ticker"),
        Index("ix_pattern_alerts_detected_at", "detected_at"),
        Index("ix_pattern_alerts_user_id", "user_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    pattern_id = Column(Integer, ForeignKey("pattern_definitions.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    ticker = Column(String, nullable=False, index=True)
    company_name = Column(String, nullable=False)
    
    # Pattern details
    event_ids = Column(PG_ARRAY(Integer), nullable=False)  # IDs of correlated events
    correlation_score = Column(Float, nullable=False)  # How well events correlate
    aggregated_impact_score = Column(Integer, nullable=False)  # Combined impact
    aggregated_direction = Column(String, nullable=False)  # "positive", "negative", "neutral"
    rationale = Column(Text, nullable=True)  # Why this pattern is significant
    
    # Status
    status = Column(String, default="active")  # "active", "acknowledged", "dismissed"
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    acknowledged_at = Column(DateTime, nullable=True)
    
    # Relationships
    pattern = relationship("PatternDefinition", backref="alerts")
    user = relationship("User", backref="pattern_alerts")
    
    def __repr__(self) -> str:
        return f"<PatternAlert(ticker={self.ticker}, pattern_id={self.pattern_id}, score={self.correlation_score})>"


# ==================== PORTFOLIO RISK MODELS ====================

class PortfolioRiskSnapshot(Base):
    """Periodic snapshots of portfolio risk metrics.
    
    Captures point-in-time risk calculations including event exposure,
    concentration risk, sector correlations, and VaR estimates.
    """
    
    __tablename__ = "portfolio_risk_snapshots"
    __table_args__ = (
        Index("ix_portfolio_risk_snapshots_portfolio_id", "portfolio_id"),
        Index("ix_portfolio_risk_snapshots_snapshot_date", "snapshot_date"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("user_portfolios.id"), nullable=False)
    snapshot_date = Column(DateTime, nullable=False, index=True)
    
    # Risk metrics
    total_event_exposure = Column(Float, nullable=True)  # % of portfolio exposed to events
    concentration_risk_score = Column(Float, nullable=True)  # 0-100, higher = more concentrated
    sector_diversification_score = Column(Float, nullable=True)  # 0-100, higher = more diversified
    var_95 = Column(Float, nullable=True)  # Value at Risk (95% confidence)
    expected_shortfall = Column(Float, nullable=True)  # CVaR/Expected Shortfall
    
    # Top risks
    top_event_risks_json = Column(JSON, nullable=True)  # Top 10 event exposures
    correlation_matrix_json = Column(JSON, nullable=True)  # Sector correlation matrix
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    portfolio = relationship("UserPortfolio", backref="risk_snapshots")
    
    def __repr__(self) -> str:
        return f"<PortfolioRiskSnapshot(portfolio_id={self.portfolio_id}, date={self.snapshot_date})>"


class PortfolioEventExposure(Base):
    """Tracks specific event exposures for portfolio positions.
    
    Links portfolio holdings to upcoming/recent events with impact estimates.
    """
    
    __tablename__ = "portfolio_event_exposure"
    __table_args__ = (
        Index("ix_portfolio_event_exposure_portfolio_id", "portfolio_id"),
        Index("ix_portfolio_event_exposure_event_id", "event_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    portfolio_id = Column(Integer, ForeignKey("user_portfolios.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("portfolio_positions.id"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    
    # Exposure details
    position_size_pct = Column(Float, nullable=False)  # % of portfolio in this position
    estimated_impact_pct = Column(Float, nullable=True)  # Estimated price impact (%)
    dollar_exposure = Column(Float, nullable=True)  # Estimated dollar risk
    hedge_recommendation = Column(Text, nullable=True)  # Suggested hedge (e.g., "Buy protective puts")
    
    calculated_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    portfolio = relationship("UserPortfolio", backref="event_exposures")
    position = relationship("PortfolioPosition", backref="event_exposures")
    event = relationship("Event", backref="portfolio_exposures")
    
    def __repr__(self) -> str:
        return f"<PortfolioEventExposure(portfolio_id={self.portfolio_id}, event_id={self.event_id})>"


# ==================== INSIDER TRADING MODELS ====================

class InsiderTransaction(Base):
    """SEC Form 4 insider trading transactions.
    
    Tracks buy/sell transactions by company insiders (officers, directors).
    Sentiment scores feed into event scoring and portfolio risk analysis.
    """
    
    __tablename__ = "insider_transactions"
    __table_args__ = (
        UniqueConstraint("ticker", "transaction_date", "insider_name", "transaction_code", "shares", 
                        name="uq_insider_transaction"),
        Index("ix_insider_transactions_ticker", "ticker"),
        Index("ix_insider_transactions_date", "transaction_date"),
        Index("ix_insider_transactions_sentiment", "sentiment_score"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ticker = Column(String, nullable=False, index=True)
    company_name = Column(String, nullable=False)
    
    # Insider details
    insider_name = Column(String, nullable=False)
    insider_title = Column(String, nullable=True)  # "CEO", "Director", etc.
    is_ten_percent_owner = Column(Boolean, default=False)
    is_officer = Column(Boolean, default=False)
    is_director = Column(Boolean, default=False)
    
    # Transaction details
    transaction_date = Column(Date, nullable=False, index=True)
    transaction_code = Column(String, nullable=False)  # "P" (purchase), "S" (sale), etc.
    shares = Column(Float, nullable=False)  # Number of shares
    price_per_share = Column(Float, nullable=True)
    transaction_value = Column(Float, nullable=True)  # Total dollar value
    shares_owned_after = Column(Float, nullable=True)
    
    # Sentiment analysis
    sentiment_score = Column(Float, nullable=True)  # -1 (bearish) to +1 (bullish)
    sentiment_rationale = Column(Text, nullable=True)  # Why this transaction is significant
    
    # Source
    form_4_url = Column(String, nullable=True)  # Link to SEC filing
    filed_date = Column(Date, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<InsiderTransaction(ticker={self.ticker}, insider={self.insider_name}, code={self.transaction_code}, shares={self.shares})>"


# ==================== STRATEGY BACKTESTING MODELS ====================

class UserStrategy(Base):
    """User-defined trading strategies for backtesting.
    
    Stores custom event patterns and conditions that trigger buy/sell signals.
    """
    
    __tablename__ = "user_strategies"
    __table_args__ = (
        Index("ix_user_strategies_user_id", "user_id"),
        Index("ix_user_strategies_active", "active"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True, index=True)
    
    # Strategy definition (JSON)
    entry_conditions = Column(JSON, nullable=False)  # When to enter position
    exit_conditions = Column(JSON, nullable=True)  # When to exit (or use fixed horizon)
    position_sizing = Column(JSON, nullable=True)  # How much to invest
    risk_management = Column(JSON, nullable=True)  # Stop loss, take profit rules
    
    # Filters
    tickers = Column(PG_ARRAY(String), nullable=True)  # Specific tickers or null for all
    sectors = Column(PG_ARRAY(String), nullable=True)  # Specific sectors or null for all
    min_score_threshold = Column(Integer, nullable=True)  # Minimum impact score
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", backref="strategies")
    
    def __repr__(self) -> str:
        return f"<UserStrategy(id={self.id}, user_id={self.user_id}, name={self.name})>"


class BacktestRun(Base):
    """Backtest execution records.
    
    Tracks when strategies were backtested and against what data.
    """
    
    __tablename__ = "backtest_runs"
    __table_args__ = (
        Index("ix_backtest_runs_strategy_id", "strategy_id"),
        Index("ix_backtest_runs_started_at", "started_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    strategy_id = Column(Integer, ForeignKey("user_strategies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Backtest parameters
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_capital = Column(Float, default=100000.0)
    
    # Execution status
    status = Column(String, default="running")  # "running", "completed", "failed"
    started_at = Column(DateTime, default=datetime.utcnow, index=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    
    # Summary metrics (populated after completion)
    total_trades = Column(Integer, nullable=True)
    win_rate = Column(Float, nullable=True)
    total_return_pct = Column(Float, nullable=True)
    sharpe_ratio = Column(Float, nullable=True)
    max_drawdown_pct = Column(Float, nullable=True)
    
    # Phase 1 Quantitative Metrics
    sortino_ratio = Column(Float, nullable=True)
    avg_atr = Column(Float, nullable=True)
    parkinson_volatility = Column(Float, nullable=True)
    
    # Relationships
    strategy = relationship("UserStrategy", backref="backtest_runs")
    user = relationship("User", backref="backtest_runs")
    
    def __repr__(self) -> str:
        return f"<BacktestRun(id={self.id}, strategy_id={self.strategy_id}, status={self.status})>"


class BacktestResult(Base):
    """Individual trade results from backtest execution.
    
    Stores each simulated trade with entry/exit details and P&L.
    """
    
    __tablename__ = "backtest_results"
    __table_args__ = (
        Index("ix_backtest_results_run_id", "run_id"),
        Index("ix_backtest_results_entry_date", "entry_date"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    run_id = Column(Integer, ForeignKey("backtest_runs.id"), nullable=False)
    
    # Trade details
    ticker = Column(String, nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)  # Event that triggered entry
    entry_date = Column(Date, nullable=False, index=True)
    entry_price = Column(Float, nullable=False)
    exit_date = Column(Date, nullable=True)
    exit_price = Column(Float, nullable=True)
    shares = Column(Float, nullable=False)
    
    # P&L
    position_value = Column(Float, nullable=False)  # entry_price * shares
    return_pct = Column(Float, nullable=True)  # (exit_price - entry_price) / entry_price * 100
    profit_loss = Column(Float, nullable=True)  # Dollar P&L
    
    # Trade metadata
    exit_reason = Column(String, nullable=True)  # "take_profit", "stop_loss", "exit_signal", "backtest_end"
    holding_period_days = Column(Integer, nullable=True)
    
    # Relationship
    run = relationship("BacktestRun", backref="results")
    event = relationship("Event", backref="backtest_trades")
    
    def __repr__(self) -> str:
        return f"<BacktestResult(run_id={self.run_id}, ticker={self.ticker}, return={self.return_pct})>"


class ModelPerformanceRecord(Base):
    """Rolling performance metrics for ML models.
    
    Tracks directional accuracy, MAE, RMSE, and other metrics over time
    for dynamic ensemble weighting between neural network and XGBoost.
    """
    
    __tablename__ = "model_performance_records"
    __table_args__ = (
        UniqueConstraint("model_name", "horizon", "recorded_date", name="uq_model_perf_unique"),
        Index("ix_model_perf_model_name", "model_name"),
        Index("ix_model_perf_recorded_date", "recorded_date"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_name = Column(String, nullable=False)  # e.g., "xgboost_impact_1d", "neural_impact_1d"
    model_type = Column(String, nullable=False)  # "xgboost", "neural", "ensemble"
    horizon = Column(String, nullable=False)  # "1d", "5d", "20d"
    
    # Performance metrics
    directional_accuracy = Column(Float, nullable=False)  # Primary metric for weighting
    mae = Column(Float, nullable=True)  # Mean absolute error
    rmse = Column(Float, nullable=True)  # Root mean squared error
    sharpe_ratio = Column(Float, nullable=True)  # Risk-adjusted returns
    
    # Sample information
    n_samples = Column(Integer, nullable=False)  # Number of predictions evaluated
    lookback_days = Column(Integer, default=30)  # Rolling window size
    
    # Weight assignment
    ensemble_weight = Column(Float, nullable=True)  # Assigned weight in ensemble
    is_primary = Column(Boolean, default=False)  # True if this model is primary in ensemble
    
    recorded_date = Column(Date, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<ModelPerformanceRecord(model={self.model_name}, accuracy={self.directional_accuracy:.2%})>"


class SocialEventSignal(Base):
    """Aggregated social sentiment signals for events.
    
    Stores Twitter/X sentiment analysis linked to financial events
    for sentiment-enhanced ML predictions.
    """
    
    __tablename__ = "social_event_signals"
    __table_args__ = (
        UniqueConstraint("event_id", name="uq_social_signal_event"),
        Index("ix_social_signal_ticker", "ticker"),
        Index("ix_social_signal_created_at", "created_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    ticker = Column(String, nullable=False, index=True)
    event_type = Column(String, nullable=True)
    
    # Volume metrics
    tweet_count = Column(Integer, nullable=False, default=0)
    unique_authors = Column(Integer, nullable=False, default=0)
    
    # Sentiment metrics
    avg_sentiment = Column(Float, nullable=False, default=0.0)  # -1.0 to 1.0
    sentiment_std = Column(Float, nullable=True)  # Sentiment variance
    positive_ratio = Column(Float, nullable=True)  # % positive tweets
    negative_ratio = Column(Float, nullable=True)  # % negative tweets
    neutral_ratio = Column(Float, nullable=True)  # % neutral tweets
    
    # Engagement metrics
    total_engagement = Column(Float, nullable=True)  # Normalized engagement score
    influencer_count = Column(Integer, nullable=True)  # Accounts with >10k followers
    influencer_sentiment = Column(Float, nullable=True)  # Influencer-weighted sentiment
    
    # Volume analysis
    volume_zscore = Column(Float, nullable=True)  # Z-score vs baseline volume
    peak_hour = Column(Integer, nullable=True)  # Hour with most activity (0-23)
    tweet_velocity = Column(Float, nullable=True)  # Tweets per hour
    
    # Sample data
    sample_tweets = Column(JSON, nullable=True)  # Top 5 sample tweets
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    event = relationship("Event", backref="social_signals")
    
    def __repr__(self) -> str:
        return f"<SocialEventSignal(event_id={self.event_id}, sentiment={self.avg_sentiment:.2f})>"


class NeuralModelRegistry(Base):
    """Registry for trained neural network models.
    
    Tracks model versions, training metrics, and deployment status.
    """
    
    __tablename__ = "neural_model_registry"
    __table_args__ = (
        UniqueConstraint("model_name", "version", name="uq_neural_model_version"),
        Index("ix_neural_registry_status", "status"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_name = Column(String, nullable=False)  # e.g., "impact_neural"
    version = Column(String, nullable=False)  # e.g., "1.0.0"
    
    # Architecture config
    config = Column(JSON, nullable=False)  # NeuralModelConfig as JSON
    
    # Training metrics
    training_samples = Column(Integer, nullable=True)
    epochs_trained = Column(Integer, nullable=True)
    final_train_loss = Column(Float, nullable=True)
    final_val_loss = Column(Float, nullable=True)
    directional_accuracy = Column(Float, nullable=True)
    
    # Deployment status
    status = Column(String, default="training")  # "training", "staged", "active", "retired"
    deployed_at = Column(DateTime, nullable=True)
    
    # File paths
    model_path = Column(String, nullable=True)  # Path to saved model
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<NeuralModelRegistry(name={self.model_name}, version={self.version}, status={self.status})>"


# ============================================================================
# MODEL EXPLAINABILITY MODELS
# ============================================================================

class PredictionExplanation(Base):
    """Store SHAP values and feature importance for model explainability.
    
    Tracks feature contributions to predictions for transparency and debugging.
    Supports multiple prediction horizons (1d, 7d, 30d).
    """
    
    __tablename__ = "prediction_explanations"
    __table_args__ = (
        Index("ix_prediction_explanations_event_id", "event_id"),
        Index("ix_prediction_explanations_horizon", "horizon"),
        Index("ix_prediction_explanations_model_version", "model_version"),
        Index("ix_prediction_explanations_computed_at", "computed_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    prediction_id = Column(Integer, nullable=True)
    horizon = Column(String, nullable=False)  # "1d", "7d", "30d"
    feature_contributions = Column(JSON, nullable=False)  # {"sector_volatility": 0.15, "event_type": 0.25, ...}
    top_factors = Column(JSON, nullable=False)  # Ordered list of top contributing factors
    shap_summary = Column(Text, nullable=True)  # Human-readable explanation
    model_version = Column(String, nullable=False)
    computed_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    event = relationship("Event", backref="prediction_explanations")
    
    def __repr__(self) -> str:
        return f"<PredictionExplanation(event_id={self.event_id}, horizon={self.horizon}, model={self.model_version})>"


# ============================================================================
# CUSTOM ALERT RULES MODELS
# ============================================================================

class CustomAlertRule(Base):
    """User-defined alert rules with custom thresholds and conditions.
    
    Allows users to create sophisticated alert rules based on confidence,
    impact scores, directions, tickers, sectors, and event types.
    """
    
    __tablename__ = "custom_alert_rules"
    __table_args__ = (
        Index("ix_custom_alert_rules_user_id", "user_id"),
        Index("ix_custom_alert_rules_active", "active"),
        Index("ix_custom_alert_rules_last_triggered_at", "last_triggered_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    conditions = Column(JSON, nullable=False)  # {"min_confidence": 0.8, "min_impact": 70, "directions": ["positive"]}
    tickers = Column(PG_ARRAY(String), nullable=True)
    sectors = Column(PG_ARRAY(String), nullable=True)
    event_types = Column(PG_ARRAY(String), nullable=True)
    notification_channels = Column(PG_ARRAY(String), nullable=False, default=["in_app"])  # ["email", "sms", "in_app"]
    cooldown_minutes = Column(Integer, nullable=False, default=60)  # Minimum time between alerts
    last_triggered_at = Column(DateTime, nullable=True)
    times_triggered = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", backref="custom_alert_rules")
    
    def __repr__(self) -> str:
        return f"<CustomAlertRule(id={self.id}, user_id={self.user_id}, name={self.name}, active={self.active})>"


# ============================================================================
# SECTOR METRICS MODELS
# ============================================================================

class SectorMetrics(Base):
    """Aggregated sector-level performance statistics.
    
    Tracks sector-wide metrics including win rates, event counts, 
    rotation signals, and correlation with market benchmarks.
    """
    
    __tablename__ = "sector_metrics"
    __table_args__ = (
        UniqueConstraint("sector", "snapshot_date", name="uq_sector_metrics_sector_date"),
        Index("ix_sector_metrics_sector", "sector"),
        Index("ix_sector_metrics_snapshot_date", "snapshot_date"),
        Index("ix_sector_metrics_rotation_signal", "rotation_signal"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    sector = Column(String, nullable=False)
    snapshot_date = Column(Date, nullable=False)
    total_events = Column(Integer, nullable=False, default=0)
    win_rate = Column(Float, nullable=True)
    avg_impact = Column(Float, nullable=True)
    top_event_types = Column(JSON, nullable=True)  # Ranked list of most common event types
    bullish_ratio = Column(Float, nullable=True)  # Ratio of bullish events
    bearish_ratio = Column(Float, nullable=True)  # Ratio of bearish events
    rotation_signal = Column(String, nullable=True)  # "inflow", "outflow", "neutral"
    momentum_score = Column(Float, nullable=True)  # Sector momentum indicator
    correlation_with_spy = Column(Float, nullable=True)  # Correlation with SPY benchmark
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<SectorMetrics(sector={self.sector}, date={self.snapshot_date}, win_rate={self.win_rate})>"


# ============================================================================
# TRADE RECOMMENDATION MODELS
# ============================================================================

class TradeRecommendation(Base):
    """Entry/exit suggestions with position sizing.
    
    Provides actionable trade recommendations based on event analysis,
    including entry/exit points, stop-loss, take-profit, and position sizing.
    """
    
    __tablename__ = "trade_recommendations"
    __table_args__ = (
        Index("ix_trade_recommendations_event_id", "event_id"),
        Index("ix_trade_recommendations_ticker", "ticker"),
        Index("ix_trade_recommendations_user_id", "user_id"),
        Index("ix_trade_recommendations_recommendation_type", "recommendation_type"),
        Index("ix_trade_recommendations_expires_at", "expires_at"),
        Index("ix_trade_recommendations_created_at", "created_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    ticker = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # Optional - for user-specific recommendations
    recommendation_type = Column(String, nullable=False)  # "entry", "exit", "hold"
    entry_price_target = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    position_size_pct = Column(Float, nullable=True)  # Recommended portfolio allocation percentage
    confidence = Column(Float, nullable=False, default=0.5)  # 0.0-1.0
    risk_reward_ratio = Column(Float, nullable=True)
    holding_period_days = Column(Integer, nullable=True)  # Recommended holding period
    rationale = Column(Text, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    event = relationship("Event", backref="trade_recommendations")
    user = relationship("User", backref="trade_recommendations")
    
    def __repr__(self) -> str:
        return f"<TradeRecommendation(id={self.id}, ticker={self.ticker}, type={self.recommendation_type}, confidence={self.confidence})>"


# ============================================================================
# HISTORICAL PATTERN MODELS
# ============================================================================

class HistoricalPattern(Base):
    """Similar event pattern library.
    
    Stores patterns discovered from historical events with their average
    returns, win rates, and sample sizes for pattern-based predictions.
    """
    
    __tablename__ = "historical_patterns"
    __table_args__ = (
        Index("ix_historical_patterns_event_type", "event_type"),
        Index("ix_historical_patterns_ticker", "ticker"),
        Index("ix_historical_patterns_sector", "sector"),
        Index("ix_historical_patterns_pattern_name", "pattern_name"),
        Index("ix_historical_patterns_win_rate", "win_rate"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_type = Column(String, nullable=False)
    ticker = Column(String, nullable=True)  # Optional - for ticker-specific patterns
    sector = Column(String, nullable=True)  # Optional - for sector-specific patterns
    pattern_name = Column(String, nullable=False)
    pattern_description = Column(Text, nullable=True)
    sample_events = Column(PG_ARRAY(Integer), nullable=True)  # Event IDs that match this pattern
    avg_return_1d = Column(Float, nullable=True)
    avg_return_7d = Column(Float, nullable=True)
    avg_return_30d = Column(Float, nullable=True)
    win_rate = Column(Float, nullable=True)  # Historical win rate (0.0-1.0)
    sample_size = Column(Integer, nullable=False, default=0)
    confidence_interval_low = Column(Float, nullable=True)
    confidence_interval_high = Column(Float, nullable=True)
    pattern_metadata = Column(JSON, nullable=True)  # Additional pattern-specific metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self) -> str:
        return f"<HistoricalPattern(name={self.pattern_name}, event_type={self.event_type}, win_rate={self.win_rate})>"


# ============================================================================
# USER PREFERENCE MODELS
# ============================================================================

class UserPreference(Base):
    """User settings, saved filters, and theme preferences.
    
    Stores user-specific preferences for dashboard customization,
    notification settings, and default filters.
    """
    
    __tablename__ = "user_preferences"
    __table_args__ = (
        Index("ix_user_preferences_user_id", "user_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    theme = Column(String, nullable=False, default="system")  # "dark", "light", "system"
    default_horizon = Column(String, nullable=False, default="1d")  # "1d", "7d", "30d"
    saved_filters = Column(JSON, nullable=True)  # {"event_types": ["earnings"], "sectors": ["tech"]}
    dashboard_layout = Column(JSON, nullable=True)  # Widget preferences and positions
    notification_settings = Column(JSON, nullable=True)  # {"email": true, "sms": false, "in_app": true}
    timezone = Column(String, nullable=True, default="UTC")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    user = relationship("User", backref="preferences")
    
    def __repr__(self) -> str:
        return f"<UserPreference(user_id={self.user_id}, theme={self.theme}, timezone={self.timezone})>"


# ============================================================================
# DIGEST SUBSCRIPTION MODELS
# ============================================================================

class DigestSubscription(Base):
    """Email digest configuration for scheduled event summaries.
    
    Configures digest frequency, delivery time, and content filters
    for automated email summaries.
    """
    
    __tablename__ = "digest_subscriptions"
    __table_args__ = (
        Index("ix_digest_subscriptions_user_id", "user_id"),
        Index("ix_digest_subscriptions_frequency", "frequency"),
        Index("ix_digest_subscriptions_next_send_at", "next_send_at"),
        Index("ix_digest_subscriptions_active", "active"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    frequency = Column(String, nullable=False, default="daily")  # "daily", "weekly", "none"
    delivery_time = Column(String, nullable=False, default="08:00")  # Time in HH:MM format
    delivery_day = Column(Integer, nullable=True)  # Day of week for weekly (0=Monday, 6=Sunday)
    include_sections = Column(JSON, nullable=True)  # {"top_events": true, "portfolio_summary": true}
    tickers_filter = Column(PG_ARRAY(String), nullable=True)  # Optional ticker filter
    min_score_threshold = Column(Integer, nullable=False, default=0)  # Minimum impact score to include
    last_sent_at = Column(DateTime, nullable=True)
    next_send_at = Column(DateTime, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationship
    user = relationship("User", backref="digest_subscriptions")
    
    def __repr__(self) -> str:
        return f"<DigestSubscription(user_id={self.user_id}, frequency={self.frequency}, active={self.active})>"


# ============================================================================
# FORUM / COMMUNITY CHAT MODELS
# ============================================================================

class ForumMessage(Base):
    """Community forum messages for Pro and Team plan users.
    
    Discord-style chat messages with @Quant AI integration.
    Each message displays: username, profile picture, plan badge, timestamp.
    """
    
    __tablename__ = "forum_messages"
    __table_args__ = (
        Index("ix_forum_messages_created_at", "created_at"),
        Index("ix_forum_messages_user_id", "user_id"),
        Index("ix_forum_messages_is_ai_response", "is_ai_response"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    image_url = Column(String(2000), nullable=True)  # Image or GIF URL for message attachments
    is_ai_response = Column(Boolean, default=False, index=True)  # True if message is from @Quant AI
    ai_prompt = Column(Text, nullable=True)  # Original @Quant query (if AI response)
    parent_message_id = Column(Integer, ForeignKey("forum_messages.id"), nullable=True)  # For AI responses linked to original message or replies
    edited_at = Column(DateTime, nullable=True)
    deleted_at = Column(DateTime, nullable=True)  # Soft delete
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Relationship
    user = relationship("User", backref="forum_messages")
    parent_message = relationship("ForumMessage", remote_side=[id], backref="ai_responses")
    
    def __repr__(self) -> str:
        return f"<ForumMessage(id={self.id}, user_id={self.user_id}, is_ai={self.is_ai_response})>"


class ForumReaction(Base):
    """Reactions (emoji) on forum messages.
    
    Allows users to react to messages with emojis like Discord.
    """
    
    __tablename__ = "forum_reactions"
    __table_args__ = (
        UniqueConstraint("message_id", "user_id", "emoji", name="uq_forum_reaction_user_message_emoji"),
        Index("ix_forum_reactions_message_id", "message_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    message_id = Column(Integer, ForeignKey("forum_messages.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    emoji = Column(String(32), nullable=False)  # Emoji code like "thumbs_up", "rocket", "fire"
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    message = relationship("ForumMessage", backref="reactions")
    user = relationship("User", backref="forum_reactions")
    
    def __repr__(self) -> str:
        return f"<ForumReaction(message_id={self.message_id}, user_id={self.user_id}, emoji={self.emoji})>"


# ============================================================================
# ML DRIFT MONITORING AND CALIBRATION MODELS
# ============================================================================

class ModelPerformanceSnapshot(Base):
    """Periodic performance snapshot for ML model monitoring.
    
    Tracks directional accuracy, MAE, RMSE, and calibration error over
    rolling time windows (7d, 30d, 90d) for drift detection.
    """
    
    __tablename__ = "model_performance_snapshots"
    __table_args__ = (
        UniqueConstraint("model_id", "horizon", "snapshot_date", "window_days", 
                        name="uq_model_perf_snapshot"),
        Index("ix_model_perf_snapshot_model_id", "model_id"),
        Index("ix_model_perf_snapshot_date", "snapshot_date"),
        Index("ix_model_perf_snapshot_horizon", "horizon"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("model_registry.id"), nullable=False)
    horizon = Column(String, nullable=False)  # "1d", "5d", "20d"
    snapshot_date = Column(Date, nullable=False, index=True)
    
    direction_accuracy = Column(Float, nullable=True)
    mae = Column(Float, nullable=True)
    rmse = Column(Float, nullable=True)
    calibration_error = Column(Float, nullable=True)
    
    sample_count = Column(Integer, nullable=False, default=0)
    window_days = Column(Integer, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    model = relationship("ModelRegistry", backref="performance_snapshots")
    
    def __repr__(self) -> str:
        return f"<ModelPerformanceSnapshot(model_id={self.model_id}, horizon={self.horizon}, date={self.snapshot_date}, accuracy={self.direction_accuracy})>"


class DriftAlert(Base):
    """Drift alert when model performance degrades.
    
    Generated when direction accuracy drops >5% or calibration error spikes,
    stored for tracking and resolution.
    """
    
    __tablename__ = "drift_alerts"
    __table_args__ = (
        Index("ix_drift_alerts_model_id", "model_id"),
        Index("ix_drift_alerts_detected_at", "detected_at"),
        Index("ix_drift_alerts_severity", "severity"),
        Index("ix_drift_alerts_resolved_at", "resolved_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("model_registry.id"), nullable=False)
    horizon = Column(String, nullable=False)  # "1d", "5d", "20d"
    alert_type = Column(String, nullable=False)  # "accuracy_drop", "calibration_drift", "mae_spike"
    severity = Column(String, nullable=False, default="medium")  # "low", "medium", "high"
    
    metrics_before = Column(JSON, nullable=True)
    metrics_after = Column(JSON, nullable=True)
    
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    
    model = relationship("ModelRegistry", backref="drift_alerts")
    
    def __repr__(self) -> str:
        return f"<DriftAlert(model_id={self.model_id}, type={self.alert_type}, severity={self.severity})>"


class CalibrationSnapshot(Base):
    """Calibration snapshot for reliability diagram data.
    
    Stores predicted probability vs actual frequency for calibration analysis.
    Enables plotting reliability diagrams and computing Expected Calibration Error.
    """
    
    __tablename__ = "calibration_snapshots"
    __table_args__ = (
        UniqueConstraint("model_id", "horizon", "snapshot_date", name="uq_calibration_snapshot"),
        Index("ix_calibration_snapshot_model_id", "model_id"),
        Index("ix_calibration_snapshot_date", "snapshot_date"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey("model_registry.id"), nullable=False)
    horizon = Column(String, nullable=False)  # "1d", "5d"
    snapshot_date = Column(Date, nullable=False, index=True)
    
    expected_calibration_error = Column(Float, nullable=True)
    max_calibration_error = Column(Float, nullable=True)
    
    bin_data = Column(JSON, nullable=True)
    
    sample_count = Column(Integer, nullable=False, default=0)
    window_days = Column(Integer, nullable=False, default=30)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    model = relationship("ModelRegistry", backref="calibration_snapshots")
    
    def __repr__(self) -> str:
        return f"<CalibrationSnapshot(model_id={self.model_id}, horizon={self.horizon}, ece={self.expected_calibration_error})>"


class ChangelogRelease(Base):
    """Changelog release version for public release notes.
    
    Stores version information and release metadata for the changelog page.
    """
    
    __tablename__ = "changelog_releases"
    __table_args__ = (
        Index("ix_changelog_releases_version", "version"),
        Index("ix_changelog_releases_date", "release_date"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    version = Column(String, unique=True, nullable=False)
    title = Column(String, nullable=False)
    release_date = Column(Date, nullable=False, index=True)
    is_published = Column(Boolean, default=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    items = relationship("ChangelogItem", back_populates="release", cascade="all, delete-orphan", order_by="ChangelogItem.sort_order")
    
    def __repr__(self) -> str:
        return f"<ChangelogRelease(id={self.id}, version={self.version}, title={self.title})>"


class ChangelogItem(Base):
    """Individual changelog item within a release.
    
    Stores category, description, and icon for each changelog entry.
    """
    
    __tablename__ = "changelog_items"
    __table_args__ = (
        Index("ix_changelog_items_release_id", "release_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    release_id = Column(Integer, ForeignKey("changelog_releases.id", ondelete="CASCADE"), nullable=False)
    category = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String, nullable=True, default="CheckCircle2")
    sort_order = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    release = relationship("ChangelogRelease", back_populates="items")
    
    def __repr__(self) -> str:
        return f"<ChangelogItem(id={self.id}, category={self.category})>"


# ============================================================================
# PLAYBOOK LIBRARY MODELS
# ============================================================================

class Playbook(Base):
    """Trading strategy playbook template.
    
    Contains setup conditions, entry/exit logic, and historical performance stats
    for event-driven trading strategies like "Earnings Beat, Gap < 8%, Uptrend".
    """
    
    __tablename__ = "playbooks"
    __table_args__ = (
        Index("ix_playbooks_slug", "slug"),
        Index("ix_playbooks_category", "category"),
        Index("ix_playbooks_is_active", "is_active"),
        Index("ix_playbooks_display_order", "display_order"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    slug = Column(String, unique=True, nullable=False)  # URL-friendly identifier
    title = Column(String, nullable=False)  # "Earnings Beat, Gap < 8%, Uptrend"
    category = Column(String, nullable=False)  # "earnings", "fda", "sec", "corporate"
    description = Column(Text, nullable=True)  # Brief overview of the playbook
    
    # Setup conditions (JSON for flexibility)
    setup_conditions = Column(JSON, nullable=False)  # {"event_type": "earnings", "gap_range": [-8, 8], "trend": "uptrend", ...}
    
    # Trading logic
    entry_logic = Column(Text, nullable=False)  # Human-readable entry rules
    stop_template = Column(Text, nullable=True)  # Stop-loss rules
    target_template = Column(Text, nullable=True)  # Take-profit rules
    holding_period = Column(String, nullable=True)  # "3-5 days", "5-20 days", etc.
    
    # Historical statistics (placeholders initially)
    win_rate = Column(Float, nullable=True)  # 0.0-1.0
    avg_r = Column(Float, nullable=True)  # Average R-multiple
    sample_size = Column(Integer, nullable=True, default=0)
    stats_metadata = Column(JSON, nullable=True)  # Additional stats like avg_move_1d, max_win, max_loss
    
    # Display settings
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    is_featured = Column(Boolean, default=False)
    
    # Ownership
    author_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null for system playbooks
    visibility = Column(String, default="public")  # "public", "pro", "team"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    author = relationship("User", backref="playbooks")
    screenshots = relationship("PlaybookScreenshot", back_populates="playbook", cascade="all, delete-orphan", order_by="PlaybookScreenshot.slot_index")
    rules = relationship("PlaybookRule", back_populates="playbook", cascade="all, delete-orphan")
    
    def __repr__(self) -> str:
        return f"<Playbook(id={self.id}, slug={self.slug}, title={self.title})>"


class PlaybookScreenshot(Base):
    """Screenshot slots for playbook chart/event references.
    
    Each playbook can have 1-3 screenshots demonstrating the setup.
    """
    
    __tablename__ = "playbook_screenshots"
    __table_args__ = (
        UniqueConstraint("playbook_id", "slot_index", name="uq_playbook_screenshot_slot"),
        Index("ix_playbook_screenshots_playbook_id", "playbook_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    playbook_id = Column(Integer, ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False)
    slot_index = Column(Integer, nullable=False)  # 0, 1, or 2
    image_url = Column(String(2000), nullable=True)  # External URL or base64
    caption = Column(String, nullable=True)  # Optional caption
    event_ref = Column(Integer, ForeignKey("events.id"), nullable=True)  # Reference to specific event
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    playbook = relationship("Playbook", back_populates="screenshots")
    event = relationship("Event", backref="playbook_screenshots")
    
    def __repr__(self) -> str:
        return f"<PlaybookScreenshot(playbook_id={self.playbook_id}, slot={self.slot_index})>"


class PlaybookRule(Base):
    """Matching rules for automatic event-to-playbook association.
    
    Defines conditions that must be met for an event to match a playbook.
    """
    
    __tablename__ = "playbook_rules"
    __table_args__ = (
        Index("ix_playbook_rules_playbook_id", "playbook_id"),
        Index("ix_playbook_rules_rule_type", "rule_type"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    playbook_id = Column(Integer, ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False)
    rule_type = Column(String, nullable=False)  # "event_type", "keyword", "score_range", "sector", "market_cap", "direction"
    operator = Column(String, nullable=False, default="eq")  # "eq", "ne", "gt", "lt", "gte", "lte", "in", "contains"
    value = Column(JSON, nullable=False)  # The value to compare against
    is_required = Column(Boolean, default=True)  # Must match vs optional
    weight = Column(Float, default=1.0)  # Weight for scoring partial matches
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    playbook = relationship("Playbook", back_populates="rules")
    
    def __repr__(self) -> str:
        return f"<PlaybookRule(playbook_id={self.playbook_id}, type={self.rule_type}, op={self.operator})>"


class EventPlaybookMatch(Base):
    """Tracks which playbooks an event matches.
    
    Stores both automatic matches (from rule evaluation) and manual overrides.
    """
    
    __tablename__ = "event_playbook_matches"
    __table_args__ = (
        UniqueConstraint("event_id", "playbook_id", name="uq_event_playbook_match"),
        Index("ix_event_playbook_matches_event_id", "event_id"),
        Index("ix_event_playbook_matches_playbook_id", "playbook_id"),
        Index("ix_event_playbook_matches_match_source", "match_source"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    event_id = Column(Integer, ForeignKey("events.id", ondelete="CASCADE"), nullable=False)
    playbook_id = Column(Integer, ForeignKey("playbooks.id", ondelete="CASCADE"), nullable=False)
    match_source = Column(String, nullable=False, default="auto")  # "auto", "manual"
    confidence = Column(Float, nullable=True)  # Match confidence score (0.0-1.0)
    rules_matched = Column(JSON, nullable=True)  # Which rules matched
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    event = relationship("Event", backref="playbook_matches")
    playbook = relationship("Playbook", backref="event_matches")
    
    def __repr__(self) -> str:
        return f"<EventPlaybookMatch(event_id={self.event_id}, playbook_id={self.playbook_id}, source={self.match_source})>"


# ============================================================================
# IMPACT RADAR INSIGHTS MODELS
# ============================================================================

class InsightDigest(Base):
    """Auto-generated market insight digest for daily/weekly briefings.
    
    Contains the generated content, stats, and delivery status for
    automated email summaries like "How the market reacted to FDA approvals".
    """
    
    __tablename__ = "insight_digests"
    __table_args__ = (
        Index("ix_insight_digests_cadence", "cadence"),
        Index("ix_insight_digests_period_start", "period_start"),
        Index("ix_insight_digests_status", "status"),
        Index("ix_insight_digests_generated_at", "generated_at"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    cadence = Column(String, nullable=False)  # "daily", "weekly"
    period_start = Column(Date, nullable=False)  # Start of the analysis period
    period_end = Column(Date, nullable=False)  # End of the analysis period
    
    # Content
    subject = Column(String, nullable=False)  # Email subject line
    headline = Column(String, nullable=True)  # Main headline/title
    html_body = Column(Text, nullable=True)  # Full HTML content
    text_body = Column(Text, nullable=True)  # Plain text version
    
    # Highlights (JSON for structured data)
    highlights = Column(JSON, nullable=True)  # Key insights array
    playbook_stats = Column(JSON, nullable=True)  # Playbook performance data
    
    # Aggregated metrics for the period
    total_events = Column(Integer, nullable=True)
    avg_move_1d = Column(Float, nullable=True)
    avg_move_5d = Column(Float, nullable=True)
    top_sectors = Column(JSON, nullable=True)
    top_event_types = Column(JSON, nullable=True)
    
    # Status
    status = Column(String, default="draft")  # "draft", "generated", "sent", "failed"
    generated_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    recipients_count = Column(Integer, default=0)
    
    # Error tracking
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    events = relationship("InsightDigestEvent", back_populates="digest", cascade="all, delete-orphan", order_by="InsightDigestEvent.ordering")
    
    def __repr__(self) -> str:
        return f"<InsightDigest(id={self.id}, cadence={self.cadence}, period={self.period_start} to {self.period_end})>"


class InsightDigestEvent(Base):
    """Individual events featured in an insight digest.
    
    Links specific notable events to a digest with summary and stats.
    """
    
    __tablename__ = "insight_digest_events"
    __table_args__ = (
        UniqueConstraint("digest_id", "event_id", name="uq_insight_digest_event"),
        Index("ix_insight_digest_events_digest_id", "digest_id"),
        Index("ix_insight_digest_events_event_id", "event_id"),
    )
    
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    digest_id = Column(Integer, ForeignKey("insight_digests.id", ondelete="CASCADE"), nullable=False)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False)
    ordering = Column(Integer, default=0)  # Display order in the digest
    
    # Event-specific summary for this digest
    summary = Column(Text, nullable=True)  # Brief narrative about this event
    stats = Column(JSON, nullable=True)  # {"move_1d": 2.5, "move_5d": 4.1, ...}
    screenshot_ref = Column(String, nullable=True)  # Optional chart screenshot URL
    
    # Context
    section = Column(String, nullable=True)  # "top_movers", "fda_roundup", "earnings_watch"
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    digest = relationship("InsightDigest", back_populates="events")
    event = relationship("Event", backref="digest_features")
    
    def __repr__(self) -> str:
        return f"<InsightDigestEvent(digest_id={self.digest_id}, event_id={self.event_id}, section={self.section})>"
