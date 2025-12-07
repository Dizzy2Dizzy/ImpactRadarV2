-- Migration 005: Add refinement feature tables
-- Purpose: Add tables for model explainability, custom alerts, sector metrics,
--          trade recommendations, historical patterns, user preferences, and email digests
-- Date: 2025-11-29

-- ============================================================================
-- PREDICTION EXPLANATIONS (Model Explainability)
-- ============================================================================
CREATE TABLE IF NOT EXISTS prediction_explanations (
    id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    horizon VARCHAR(10) NOT NULL DEFAULT '1d',
    feature_contributions JSONB NOT NULL DEFAULT '{}',
    top_factors JSONB NOT NULL DEFAULT '[]',
    shap_summary TEXT,
    model_version VARCHAR(50),
    computed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_prediction_explanations_event_id ON prediction_explanations(event_id);
CREATE INDEX IF NOT EXISTS ix_prediction_explanations_horizon ON prediction_explanations(horizon);
CREATE INDEX IF NOT EXISTS ix_prediction_explanations_computed_at ON prediction_explanations(computed_at);

-- ============================================================================
-- CUSTOM ALERT RULES (User-defined thresholds)
-- ============================================================================
CREATE TABLE IF NOT EXISTS custom_alert_rules (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    conditions JSONB NOT NULL DEFAULT '{}',
    tickers VARCHAR[] DEFAULT NULL,
    sectors VARCHAR[] DEFAULT NULL,
    event_types VARCHAR[] DEFAULT NULL,
    notification_channels VARCHAR[] DEFAULT ARRAY['in_app'],
    cooldown_minutes INTEGER DEFAULT 60,
    last_triggered_at TIMESTAMP WITH TIME ZONE,
    times_triggered INTEGER DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_custom_alert_rules_user_id ON custom_alert_rules(user_id);
CREATE INDEX IF NOT EXISTS ix_custom_alert_rules_active ON custom_alert_rules(active);

-- ============================================================================
-- SECTOR METRICS (Aggregated sector performance)
-- ============================================================================
CREATE TABLE IF NOT EXISTS sector_metrics (
    id SERIAL PRIMARY KEY,
    sector VARCHAR(100) NOT NULL,
    snapshot_date DATE NOT NULL,
    total_events INTEGER DEFAULT 0,
    win_rate FLOAT,
    avg_impact FLOAT,
    top_event_types JSONB DEFAULT '[]',
    bullish_ratio FLOAT,
    bearish_ratio FLOAT,
    rotation_signal VARCHAR(20) DEFAULT 'neutral',
    momentum_score FLOAT,
    correlation_with_spy FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(sector, snapshot_date)
);

CREATE INDEX IF NOT EXISTS ix_sector_metrics_sector ON sector_metrics(sector);
CREATE INDEX IF NOT EXISTS ix_sector_metrics_snapshot_date ON sector_metrics(snapshot_date);
CREATE INDEX IF NOT EXISTS ix_sector_metrics_rotation_signal ON sector_metrics(rotation_signal);

-- ============================================================================
-- TRADE RECOMMENDATIONS (Entry/exit suggestions)
-- ============================================================================
CREATE TABLE IF NOT EXISTS trade_recommendations (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id) ON DELETE SET NULL,
    ticker VARCHAR(20) NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    recommendation_type VARCHAR(20) NOT NULL,
    entry_price_target FLOAT,
    stop_loss FLOAT,
    take_profit FLOAT,
    position_size_pct FLOAT,
    confidence FLOAT,
    risk_reward_ratio FLOAT,
    holding_period_days INTEGER,
    rationale TEXT,
    expires_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_trade_recommendations_event_id ON trade_recommendations(event_id);
CREATE INDEX IF NOT EXISTS ix_trade_recommendations_ticker ON trade_recommendations(ticker);
CREATE INDEX IF NOT EXISTS ix_trade_recommendations_user_id ON trade_recommendations(user_id);
CREATE INDEX IF NOT EXISTS ix_trade_recommendations_type ON trade_recommendations(recommendation_type);
CREATE INDEX IF NOT EXISTS ix_trade_recommendations_expires_at ON trade_recommendations(expires_at);

-- ============================================================================
-- HISTORICAL PATTERNS (Similar event pattern library)
-- ============================================================================
CREATE TABLE IF NOT EXISTS historical_patterns (
    id SERIAL PRIMARY KEY,
    event_type VARCHAR(100) NOT NULL,
    ticker VARCHAR(20),
    sector VARCHAR(100),
    pattern_name VARCHAR(255) NOT NULL,
    pattern_description TEXT,
    sample_events INTEGER[] DEFAULT ARRAY[]::INTEGER[],
    avg_return_1d FLOAT,
    avg_return_7d FLOAT,
    avg_return_30d FLOAT,
    win_rate FLOAT,
    sample_size INTEGER DEFAULT 0,
    confidence_interval_low FLOAT,
    confidence_interval_high FLOAT,
    pattern_metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_historical_patterns_event_type ON historical_patterns(event_type);
CREATE INDEX IF NOT EXISTS ix_historical_patterns_ticker ON historical_patterns(ticker);
CREATE INDEX IF NOT EXISTS ix_historical_patterns_sector ON historical_patterns(sector);

-- ============================================================================
-- USER PREFERENCES (Theme, saved filters, settings)
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_preferences (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE UNIQUE,
    theme VARCHAR(20) DEFAULT 'dark',
    default_horizon VARCHAR(10) DEFAULT '1d',
    saved_filters JSONB DEFAULT '{}',
    dashboard_layout JSONB DEFAULT '{}',
    notification_settings JSONB DEFAULT '{"email": true, "sms": false, "in_app": true}',
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_user_preferences_user_id ON user_preferences(user_id);

-- ============================================================================
-- DIGEST SUBSCRIPTIONS (Email digest configuration)
-- ============================================================================
CREATE TABLE IF NOT EXISTS digest_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    frequency VARCHAR(20) DEFAULT 'daily',
    delivery_time VARCHAR(10) DEFAULT '08:00',
    delivery_day INTEGER DEFAULT 0,
    include_sections JSONB DEFAULT '{"top_events": true, "portfolio_summary": true, "alerts": true}',
    tickers_filter VARCHAR[] DEFAULT NULL,
    min_score_threshold INTEGER DEFAULT 50,
    last_sent_at TIMESTAMP WITH TIME ZONE,
    next_send_at TIMESTAMP WITH TIME ZONE,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_digest_subscriptions_user_id ON digest_subscriptions(user_id);
CREATE INDEX IF NOT EXISTS ix_digest_subscriptions_next_send_at ON digest_subscriptions(next_send_at);
CREATE INDEX IF NOT EXISTS ix_digest_subscriptions_active ON digest_subscriptions(active);

-- ============================================================================
-- Add comments for documentation
-- ============================================================================
COMMENT ON TABLE prediction_explanations IS 'Stores SHAP values and feature importance for ML model explainability';
COMMENT ON TABLE custom_alert_rules IS 'User-defined alert rules with custom thresholds and notification preferences';
COMMENT ON TABLE sector_metrics IS 'Aggregated sector-level performance statistics and rotation signals';
COMMENT ON TABLE trade_recommendations IS 'Entry/exit price suggestions with position sizing and risk management';
COMMENT ON TABLE historical_patterns IS 'Similar event pattern library for historical comparison';
COMMENT ON TABLE user_preferences IS 'User settings including theme, saved filters, and dashboard layout';
COMMENT ON TABLE digest_subscriptions IS 'Email digest configuration for daily/weekly summaries';
