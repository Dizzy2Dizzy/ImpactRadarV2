-- Migration 002: Add Quantitative Features
-- Adds tables for Accuracy Dashboard, Pattern Detection, Portfolio Risk, Insider Trading, and Strategy Backtesting

-- ==================== ACCURACY DASHBOARD TABLES ====================

CREATE TABLE IF NOT EXISTS prediction_metrics (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    horizon VARCHAR NOT NULL,
    date DATE NOT NULL,
    
    -- Accuracy metrics
    total_predictions INTEGER NOT NULL DEFAULT 0,
    correct_direction INTEGER NOT NULL DEFAULT 0,
    win_rate FLOAT,
    mae FLOAT,
    rmse FLOAT,
    sharpe_ratio FLOAT,
    avg_confidence FLOAT,
    
    -- Performance by confidence bucket
    high_conf_win_rate FLOAT,
    med_conf_win_rate FLOAT,
    low_conf_win_rate FLOAT,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT uq_prediction_metrics UNIQUE (model_version, event_type, horizon, date)
);

CREATE INDEX ix_prediction_metrics_date ON prediction_metrics(date);
CREATE INDEX ix_prediction_metrics_model_version ON prediction_metrics(model_version);

CREATE TABLE IF NOT EXISTS prediction_snapshots (
    id SERIAL PRIMARY KEY,
    model_version VARCHAR NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    overall_win_rate FLOAT,
    overall_mae FLOAT,
    total_events_scored INTEGER NOT NULL DEFAULT 0,
    metrics_json JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_prediction_snapshots_timestamp ON prediction_snapshots(timestamp);
CREATE INDEX ix_prediction_snapshots_model_version ON prediction_snapshots(model_version);


-- ==================== EVENT PATTERN DETECTION TABLES ====================

CREATE TABLE IF NOT EXISTS pattern_definitions (
    id SERIAL PRIMARY KEY,
    name VARCHAR NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(id),
    active BOOLEAN DEFAULT TRUE,
    
    -- Pattern conditions
    conditions JSONB NOT NULL,
    time_window_days INTEGER DEFAULT 7,
    min_correlation_score FLOAT DEFAULT 0.6,
    
    -- Alert settings
    alert_channels VARCHAR[],
    priority VARCHAR DEFAULT 'medium',
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_pattern_definitions_created_by ON pattern_definitions(created_by);
CREATE INDEX ix_pattern_definitions_active ON pattern_definitions(active);

CREATE TABLE IF NOT EXISTS pattern_alerts (
    id SERIAL PRIMARY KEY,
    pattern_id INTEGER NOT NULL REFERENCES pattern_definitions(id),
    user_id INTEGER REFERENCES users(id),
    ticker VARCHAR NOT NULL,
    company_name VARCHAR NOT NULL,
    
    -- Pattern details
    event_ids INTEGER[] NOT NULL,
    correlation_score FLOAT NOT NULL,
    aggregated_impact_score INTEGER NOT NULL,
    aggregated_direction VARCHAR NOT NULL,
    rationale TEXT,
    
    -- Status
    status VARCHAR DEFAULT 'active',
    detected_at TIMESTAMP DEFAULT NOW(),
    acknowledged_at TIMESTAMP
);

CREATE INDEX ix_pattern_alerts_ticker ON pattern_alerts(ticker);
CREATE INDEX ix_pattern_alerts_detected_at ON pattern_alerts(detected_at);
CREATE INDEX ix_pattern_alerts_user_id ON pattern_alerts(user_id);


-- ==================== PORTFOLIO RISK TABLES ====================

CREATE TABLE IF NOT EXISTS portfolio_risk_snapshots (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES user_portfolios(id),
    snapshot_date TIMESTAMP NOT NULL,
    
    -- Risk metrics
    total_event_exposure FLOAT,
    concentration_risk_score FLOAT,
    sector_diversification_score FLOAT,
    var_95 FLOAT,
    expected_shortfall FLOAT,
    
    -- Top risks
    top_event_risks_json JSONB,
    correlation_matrix_json JSONB,
    
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_portfolio_risk_snapshots_portfolio_id ON portfolio_risk_snapshots(portfolio_id);
CREATE INDEX ix_portfolio_risk_snapshots_snapshot_date ON portfolio_risk_snapshots(snapshot_date);

CREATE TABLE IF NOT EXISTS portfolio_event_exposure (
    id SERIAL PRIMARY KEY,
    portfolio_id INTEGER NOT NULL REFERENCES user_portfolios(id),
    position_id INTEGER NOT NULL REFERENCES portfolio_positions(id),
    event_id INTEGER NOT NULL REFERENCES events(id),
    
    -- Exposure details
    position_size_pct FLOAT NOT NULL,
    estimated_impact_pct FLOAT,
    dollar_exposure FLOAT,
    hedge_recommendation TEXT,
    
    calculated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_portfolio_event_exposure_portfolio_id ON portfolio_event_exposure(portfolio_id);
CREATE INDEX ix_portfolio_event_exposure_event_id ON portfolio_event_exposure(event_id);


-- ==================== INSIDER TRADING TABLE ====================

CREATE TABLE IF NOT EXISTS insider_transactions (
    id SERIAL PRIMARY KEY,
    ticker VARCHAR NOT NULL,
    company_name VARCHAR NOT NULL,
    
    -- Insider details
    insider_name VARCHAR NOT NULL,
    insider_title VARCHAR,
    is_ten_percent_owner BOOLEAN DEFAULT FALSE,
    is_officer BOOLEAN DEFAULT FALSE,
    is_director BOOLEAN DEFAULT FALSE,
    
    -- Transaction details
    transaction_date DATE NOT NULL,
    transaction_code VARCHAR NOT NULL,
    shares FLOAT NOT NULL,
    price_per_share FLOAT,
    transaction_value FLOAT,
    shares_owned_after FLOAT,
    
    -- Sentiment analysis
    sentiment_score FLOAT,
    sentiment_rationale TEXT,
    
    -- Source
    form_4_url VARCHAR,
    filed_date DATE,
    
    created_at TIMESTAMP DEFAULT NOW(),
    
    CONSTRAINT uq_insider_transaction UNIQUE (ticker, transaction_date, insider_name, transaction_code, shares)
);

CREATE INDEX ix_insider_transactions_ticker ON insider_transactions(ticker);
CREATE INDEX ix_insider_transactions_date ON insider_transactions(transaction_date);
CREATE INDEX ix_insider_transactions_sentiment ON insider_transactions(sentiment_score);


-- ==================== STRATEGY BACKTESTING TABLES ====================

CREATE TABLE IF NOT EXISTS user_strategies (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    name VARCHAR NOT NULL,
    description TEXT,
    active BOOLEAN DEFAULT TRUE,
    
    -- Strategy definition
    entry_conditions JSONB NOT NULL,
    exit_conditions JSONB,
    position_sizing JSONB,
    risk_management JSONB,
    
    -- Filters
    tickers VARCHAR[],
    sectors VARCHAR[],
    min_score_threshold INTEGER,
    
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX ix_user_strategies_user_id ON user_strategies(user_id);
CREATE INDEX ix_user_strategies_active ON user_strategies(active);

CREATE TABLE IF NOT EXISTS backtest_runs (
    id SERIAL PRIMARY KEY,
    strategy_id INTEGER NOT NULL REFERENCES user_strategies(id),
    user_id INTEGER NOT NULL REFERENCES users(id),
    
    -- Backtest parameters
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    initial_capital FLOAT DEFAULT 100000.0,
    
    -- Execution status
    status VARCHAR DEFAULT 'running',
    started_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    error_message TEXT,
    
    -- Summary metrics
    total_trades INTEGER,
    win_rate FLOAT,
    total_return_pct FLOAT,
    sharpe_ratio FLOAT,
    max_drawdown_pct FLOAT
);

CREATE INDEX ix_backtest_runs_strategy_id ON backtest_runs(strategy_id);
CREATE INDEX ix_backtest_runs_started_at ON backtest_runs(started_at);

CREATE TABLE IF NOT EXISTS backtest_results (
    id SERIAL PRIMARY KEY,
    run_id INTEGER NOT NULL REFERENCES backtest_runs(id),
    
    -- Trade details
    ticker VARCHAR NOT NULL,
    event_id INTEGER REFERENCES events(id),
    entry_date DATE NOT NULL,
    entry_price FLOAT NOT NULL,
    exit_date DATE,
    exit_price FLOAT,
    shares FLOAT NOT NULL,
    
    -- P&L
    position_value FLOAT NOT NULL,
    return_pct FLOAT,
    profit_loss FLOAT,
    
    -- Trade metadata
    exit_reason VARCHAR,
    holding_period_days INTEGER
);

CREATE INDEX ix_backtest_results_run_id ON backtest_results(run_id);
CREATE INDEX ix_backtest_results_entry_date ON backtest_results(entry_date);

-- Add comment to track migration
COMMENT ON TABLE prediction_metrics IS 'Migration 002: Quantitative Features - Accuracy tracking';
COMMENT ON TABLE pattern_definitions IS 'Migration 002: Quantitative Features - Event pattern detection';
COMMENT ON TABLE portfolio_risk_snapshots IS 'Migration 002: Quantitative Features - Portfolio risk analysis';
COMMENT ON TABLE insider_transactions IS 'Migration 002: Quantitative Features - SEC Form 4 tracking';
COMMENT ON TABLE user_strategies IS 'Migration 002: Quantitative Features - Strategy backtesting';
