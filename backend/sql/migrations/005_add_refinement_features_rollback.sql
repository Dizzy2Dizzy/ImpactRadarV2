-- Rollback Migration 005: Remove refinement feature tables
-- WARNING: This will delete all data in these tables!

DROP TABLE IF EXISTS digest_subscriptions CASCADE;
DROP TABLE IF EXISTS user_preferences CASCADE;
DROP TABLE IF EXISTS historical_patterns CASCADE;
DROP TABLE IF EXISTS trade_recommendations CASCADE;
DROP TABLE IF EXISTS sector_metrics CASCADE;
DROP TABLE IF EXISTS custom_alert_rules CASCADE;
DROP TABLE IF EXISTS prediction_explanations CASCADE;
