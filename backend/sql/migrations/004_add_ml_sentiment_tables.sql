-- Migration 004: Add ML Ensemble and Social Sentiment tables
-- Created: 2025-11-28
-- Purpose: Support Market Echo Engine enhancements (neural ensemble, Twitter sentiment)

-- Create model_performance_records table
CREATE TABLE IF NOT EXISTS model_performance_records (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    model_type VARCHAR(100) NOT NULL,
    horizon VARCHAR(50) NOT NULL DEFAULT '1d',
    directional_accuracy FLOAT,
    mae FLOAT,
    rmse FLOAT,
    sharpe_ratio FLOAT,
    n_samples INTEGER DEFAULT 0,
    weight FLOAT DEFAULT 0.5,
    evaluated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for model performance queries
CREATE INDEX IF NOT EXISTS idx_model_performance_model_name ON model_performance_records(model_name);
CREATE INDEX IF NOT EXISTS idx_model_performance_evaluated ON model_performance_records(evaluated_at);

-- Create social_event_signals table
CREATE TABLE IF NOT EXISTS social_event_signals (
    id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(id) ON DELETE CASCADE,
    ticker VARCHAR(20) NOT NULL,
    platform VARCHAR(50) NOT NULL DEFAULT 'twitter',
    aggregated_sentiment FLOAT,
    sentiment_std FLOAT,
    volume INTEGER DEFAULT 0,
    volume_zscore FLOAT,
    engagement_score FLOAT,
    influencer_ratio FLOAT,
    bullish_ratio FLOAT,
    bearish_ratio FLOAT,
    neutral_ratio FLOAT,
    sample_size INTEGER DEFAULT 0,
    collected_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for social signal queries
CREATE INDEX IF NOT EXISTS idx_social_signals_event ON social_event_signals(event_id);
CREATE INDEX IF NOT EXISTS idx_social_signals_ticker ON social_event_signals(ticker);
CREATE INDEX IF NOT EXISTS idx_social_signals_collected ON social_event_signals(collected_at);

-- Create neural_model_registry table
CREATE TABLE IF NOT EXISTS neural_model_registry (
    id SERIAL PRIMARY KEY,
    model_name VARCHAR(255) NOT NULL,
    version VARCHAR(50) NOT NULL,
    model_type VARCHAR(100) DEFAULT 'neural',
    architecture JSONB,
    training_metrics JSONB,
    input_dim INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deployed_at TIMESTAMP WITH TIME ZONE,
    is_active BOOLEAN DEFAULT FALSE,
    UNIQUE(model_name, version)
);

-- Create index for active model queries
CREATE INDEX IF NOT EXISTS idx_neural_registry_active ON neural_model_registry(is_active);
CREATE INDEX IF NOT EXISTS idx_neural_registry_name ON neural_model_registry(model_name);

-- Success message
DO $$
BEGIN
    RAISE NOTICE 'Migration 004 completed: ML ensemble and sentiment tables created';
END $$;
