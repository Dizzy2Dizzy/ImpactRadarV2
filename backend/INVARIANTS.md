# System Invariants and Design Contracts

This document defines the core invariants and contracts that must be maintained across the ReleaseRadar system to ensure correctness, data integrity, and predictable behavior.

## Wave A: Historical Event Backtesting

### Data Integrity Invariants

#### Invariant 1: Complete Price Coverage Requirement
**Statement**: An `EventStats` row exists for a given `(ticker, event_type)` pair if and only if at least one historical event has complete price coverage for all required windows (1d, 5d, 20d).

**Rationale**: Option B (Lenient) - preserve historical insights when available, even if recent events lack complete data.

**Implementation Contract**:
```python
def compute_stats_for_ticker_event_type(session, ticker, event_type) -> dict:
    """
    Returns: {"action": "update", "payload": {...}} | {"action": "delete"}
    
    Invariants:
    1. If NO events have complete 1d/5d/20d coverage → DELETE EventStats row
    2. If ANY event has complete coverage → UPDATE EventStats with computed stats
    3. sample_size reflects ONLY events with complete coverage
    4. Idempotent: calling twice produces identical results
    """
```

**Verification**: 
- `tests/integration/test_event_stats.py::TestEventStatsInvariant` validates this invariant
- Test cases cover: full coverage, missing data, partial coverage, mixed completeness

#### Invariant 2: Sample Size Accuracy
**Statement**: `EventStats.sample_size` always equals the exact count of events with complete price coverage used to compute the statistics.

**Contract**:
- `sample_size > 0` implies stats were computed from real data
- `sample_size == 0` is impossible (EventStats row deleted instead)
- Events without complete coverage are excluded from sample_size

#### Invariant 3: Deletion Behavior
**Statement**: If an `EventStats` row exists for `(ticker, event_type)`, the system will delete it if all associated events no longer have complete price coverage.

**Contract**:
- Stale EventStats rows are purged when price data becomes incomplete
- No orphaned stats rows persist after recomputation
- Deletion is deterministic and idempotent

### Operational Invariants

#### Invariant 4: Idempotence
**Statement**: Calling `recompute_all_stats()` multiple times on the same data produces identical `EventStats` rows (excluding `updated_at` timestamp).

**Contract**:
- Row count remains constant across runs
- Statistical values (mean_move_1d, win_rate, etc.) remain unchanged
- No duplicate rows are created

**Verification**: `tests/integration/test_event_stats.py::TestRecomputeJobIdempotence`

#### Invariant 5: Action-Based Contract
**Statement**: All computation functions return a structured action contract indicating the operation performed.

**Contract**:
```python
# Update action - computed stats available
{
    "action": "update",
    "payload": {
        "ticker": str,
        "event_type": str,
        "sample_size": int,  # Always > 0
        "win_rate": float,
        "mean_move_1d": float,
        ...
    }
}

# Delete action - insufficient data
{
    "action": "delete"
}
```

**Verification**: `tests/integration/test_event_stats.py::TestActionBasedContract`

### Date Handling Invariants

#### Invariant 6: Timezone Consistency
**Statement**: All event dates are stored in UTC and price data lookups handle timezone conversion correctly.

**Contract**:
- Event dates stored as naive UTC datetimes
- Price data queries convert to market timezone (US/Eastern)
- Weekend/holiday events align to nearest trading day
- No off-by-one date errors

**Verification**: `tests/integration/test_event_stats.py::test_weekend_timezone_alignment`

## Wave B: Dynamic Event Scoring (Implemented)

### Scoring System Invariants

#### Invariant 7: Score Range Enforcement
**Statement**: All computed impact scores are clamped to the range [0, 100].

**Contract**:
- `final_score = clamp(base_score + context_score, 0, 100)`
- No score exceeds 100 or drops below 0
- Context modifiers can push raw score outside range before clamping

#### Invariant 8: Confidence Floor
**Statement**: Confidence scores always reflect the weakest link in the data quality chain.

**Contract**:
- `confidence = min(sample_size_confidence, source_credibility, data_completeness)`
- Confidence is never higher than the lowest contributing factor
- Unknown sources default to 60% credibility

#### Invariant 9: Scoring Determinism
**Statement**: Given identical inputs (event data, market data, configuration), the scoring system produces identical outputs.

**Contract**:
- No randomness in scoring calculations
- Same event rescored produces same score
- Market data is cached to ensure consistency within time window

## Wave C: Personalized Alerts (Implemented)

### Alert System Invariants

#### Invariant 10: Alert Delivery Guarantee
**Statement**: Every triggered alert is delivered through at least one configured channel.

**Contract**:
- In-app notifications are always created for matched alerts
- External channels (email, SMS, webhook) are attempted with retry logic
- Failed deliveries are logged but don't block other channels

#### Invariant 11: Alert Deduplication
**Statement**: Duplicate alerts for the same (pattern, ticker, user, date) combination are prevented.

**Contract**:
- Deduplication is scoped by user context
- System alerts (user_id=NULL) don't block user-specific alerts
- Daily reset allows same pattern to trigger again next day

## Wave D: Portfolio-Aware Insights (Implemented)

### Portfolio Risk Invariants

#### Invariant 12: Portfolio Event Exposure
**Statement**: Portfolio risk calculations accurately reflect exposure to pending events.

**Contract**:
- Only holdings with ticker matches are included in exposure calculations
- VaR-95 and CVaR calculations use validated historical data
- Missing price data results in conservative estimates, not errors

## Wave E: Real-time WebSocket Streaming (Implemented)

### WebSocket Invariants

#### Invariant 13: Connection Limits
**Statement**: Each user has at most N concurrent WebSocket connections.

**Contract**:
- Connection limit enforced per user
- New connections beyond limit are rejected with appropriate error
- Disconnected connections are cleaned up promptly

#### Invariant 14: Event Delivery Order
**Statement**: Events are delivered in chronological order within each stream.

**Contract**:
- Events are ordered by timestamp
- Backpressure handling may drop events but never reorders them
- Heartbeat messages maintain connection health

## Wave F: Machine Learning Scoring (Implemented - Dec 2025)

### ML Model Invariants

#### Invariant 15: Model Version Compatibility
**Statement**: The ML scoring system gracefully handles feature differences across model versions.

**Contract**:
- FeatureCompatibilityLayer bridges model version differences
- Missing features are filled with sensible defaults
- Model version is tracked in predictions for debugging

#### Invariant 16: Hourly Scoring Guarantee
**Statement**: All new events receive ML predictions within one hour of creation.

**Contract**:
- Automated hourly job processes unscored events
- Events are scored in batches to manage resources
- Failed scoring attempts are logged and retried

#### Invariant 17: Drift Detection
**Statement**: Model accuracy is continuously monitored with automatic alerts on degradation.

**Contract**:
- Rolling window metrics (7d/30d/90d) are computed daily
- Drift alerts trigger when accuracy drops >5% from baseline
- Alert includes affected time window and degradation magnitude

## Wave G: Enhanced AI Analysis (Implemented - Dec 2025)

### Filing Content Invariants

#### Invariant 18: Filing Content Caching
**Statement**: Error responses are never cached; only successful content fetches are cached.

**Contract**:
- Cache TTL is 24 hours for successful fetches
- Error responses return immediately without caching
- Rate limits (SEC EDGAR 10 req/sec) are respected

#### Invariant 19: Similar Event Matching
**Statement**: Historical similar event queries use proper SQL parameter binding.

**Contract**:
- All date intervals use bound parameters (`NOW() - :min_days * INTERVAL '1 day'`)
- No string interpolation in SQL queries
- Results include enriched price outcomes (1d/5d/20d)

---

## Maintaining Invariants

### When Adding New Features
1. Identify new invariants introduced by the feature
2. Document the invariant in this file
3. Write integration tests to verify the invariant
4. Add contracts to function docstrings

### When Modifying Existing Code
1. Review invariants affected by the change
2. Ensure tests still validate the invariants
3. Update documentation if contracts change
4. Never weaken an invariant without team discussion

### Testing Strategy
- **Integration tests** verify invariants across multiple components
- **Unit tests** verify contracts at the function level
- **Property-based tests** (future) verify invariants across random inputs
