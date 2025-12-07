-- Migration: Add bearish signal fields to events table
-- Description: Adds fields for tracking negative/bearish stock predictions
-- Date: 2025-11-28

-- Add bearish signal fields
ALTER TABLE events 
ADD COLUMN IF NOT EXISTS bearish_signal BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS bearish_score FLOAT,
ADD COLUMN IF NOT EXISTS bearish_confidence FLOAT,
ADD COLUMN IF NOT EXISTS bearish_rationale TEXT;

-- Add index for bearish signal filtering
CREATE INDEX IF NOT EXISTS ix_events_bearish_signal ON events(bearish_signal) WHERE bearish_signal = TRUE;

-- Composite index for bearish event queries by ticker
CREATE INDEX IF NOT EXISTS ix_events_ticker_bearish ON events(ticker, bearish_signal, date DESC) WHERE bearish_signal = TRUE;

COMMENT ON COLUMN events.bearish_signal IS 'True if event has high-confidence bearish/negative prediction';
COMMENT ON COLUMN events.bearish_score IS 'Normalized bearish severity score (0.0-1.0)';
COMMENT ON COLUMN events.bearish_confidence IS 'Confidence in bearish signal determination (0.0-1.0)';
COMMENT ON COLUMN events.bearish_rationale IS 'Human-readable explanation for bearish classification';
