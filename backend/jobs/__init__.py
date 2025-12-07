"""
Background jobs for Impact Radar.

Jobs:
- fetch_prices: Nightly backfill of historical price data from Yahoo Finance
- recompute_event_stats: Calculate historical event impact statistics
- dispatch_alerts: Process and send user alerts based on event filters
"""
