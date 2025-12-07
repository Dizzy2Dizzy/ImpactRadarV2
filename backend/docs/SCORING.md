# Dynamic Event Scoring System (Wave B)

## Overview

The dynamic event scoring system provides context-aware impact scores for financial events using a rule-based engine with multiple context multipliers. This system replaces static impact scoring with a sophisticated approach that considers event type, market conditions, company characteristics, and historical patterns.

## Scoring Formula

```
Final Score = clamp(Base Score + Context Score, 0, 100)

where:
- Base Score: Event type baseline (0-100) from config
- Context Score: Sum of multiplier contributions (-40 to +40)
- Final Score: Clamped to [0, 100] range
```

## Components

### 1. Base Score (0-100)

Each event type has a predefined base score representing its typical market impact:

| Event Type | Base Score | Rationale |
|-----------|------------|-----------|
| FDA Approval | 90 | High-impact regulatory milestone |
| IPO | 85 | Major liquidity event |
| Merger/Acquisition | 80/78 | Significant corporate action |
| Product Launch | 75 | Revenue driver |
| Clinical Trial | 72 | Biotech value catalyst |
| Guidance | 70 | Forward-looking signal |
| Earnings | 65 | Quarterly performance |
| SEC 8-K | 55 | Material event disclosure |
| SEC 10-K/10-Q | 50/48 | Periodic reporting |
| Downgrade | 40 | Negative sentiment |
| Recall | 35 | Product/safety issue |
| Lawsuit | 30 | Legal risk |
| Reg Investigation | 25 | Regulatory scrutiny |
| Bankruptcy | 15 | Extreme distress |

**Configuration:** `backend/config/scoring.yml` -> `base_scores`

### 2. Context Multipliers

#### Sector Beta (+0 to +10)

Adjusts score based on actual stock volatility vs market (using yfinance data when available):

- **High Beta** (β > 1.2): +10 points (~12-15% boost on typical 65-point event)
  - Technology, Biotech, Crypto, Fintech
- **Medium Beta** (0.8 ≤ β ≤ 1.2): +5 points (~7% boost)
  - Default for most sectors
- **Low Beta** (β < 0.8): +0 points
  - Utilities, Consumer Staples, Healthcare

**Data Source:** 60-day rolling beta calculated from daily returns vs SPY using yfinance.  
**Cache:** 24-hour TTL to minimize API calls.  
**Fallback:** If yfinance unavailable, estimate from sector heuristics.  
**Rationale:** Higher beta stocks amplify event impact due to greater price sensitivity.

#### Company Volatility (+0 to +10)

Based on Average True Range (ATR) percentile (14-day ATR vs 200-day distribution):

```
Score = 0 + (10 - 0) * (ATR_percentile / 100)
```

- **High Volatility** (p80+): +8-10 points (~12-15% boost on typical 65-point event)
- **Medium Volatility** (p50): +5 points (~7% boost)
- **Low Volatility** (p20-): +0-2 points

**Data Source:** 14-day ATR compared to rolling 200-day ATR distribution using yfinance.  
**Cache:** 24-hour TTL to minimize API calls.  
**Fallback:** Default to +5 (medium) if data unavailable.  
**Rationale:** More volatile stocks exhibit larger price swings on news, increasing event impact.

#### Earnings Proximity (+8 if within ±3 trading days)

Bonus applied when event occurs near earnings announcement:

- **Near Earnings**: +8 points
- **Otherwise**: +0 points

**Rationale:** Events near earnings create compounding attention and volatility.

#### Market Regime (-10 to +10)

Adjusts for broader market sentiment using SPY 5-day returns:

```
SPY 5d Return | Score Adjustment | Regime
--------------|------------------|--------
≤ -5%         | -10 (bearish)    | "bear"
-5% to +5%    | -10 to +10       | "neutral"
≥ +5%         | +10 (bullish)    | "bull"
```

**Data Source:** SPY 1-day, 5-day, and 20-day returns using yfinance. Primary indicator is 5-day return.  
**Cache:** 24-hour TTL to minimize API calls.  
**Fallback:** Default to 0 (neutral) if data unavailable.  
**Rationale:** Bull markets amplify positive news; bear markets amplify negative news. Events matter more in extreme market conditions (~15% impact swing between bull and bear).

#### After-Hours Flag (+4)

Bonus for events announced outside regular trading hours (before 9:30 AM or after 4:00 PM ET):

- **After Hours**: +4 points
- **Regular Hours**: +0 points

**Rationale:** After-hours news creates overnight gaps and higher opening volatility.

#### Duplicate Penalty (-8 if within 7 days)

Reduces score for repeated similar events:

- **Recent Duplicate**: -8 points
- **No Duplicate**: +0 points

**Rationale:** Market desensitization reduces impact of redundant information.

### 2.1 Market Data Factors

The scoring system integrates real-time market data to enhance accuracy:

#### Beta (Stock Volatility vs Market)

- **Definition:** 60-day rolling beta measuring stock returns vs SPY
- **Range:** Typically 0.5 to 2.0 (can be negative or >2 for extreme cases)
- **Impact:** High beta stocks (>1.5) get +10 points (~15% boost on 65-point base)
- **Data Source:** yfinance, 24h cache
- **Interpretation:**
  - β > 1.5: High volatility stock, amplifies event impact
  - β = 1.0: Moves with market
  - β < 0.8: Low volatility, defensive stock

#### ATR Percentile (Recent Volatility)

- **Definition:** 14-day Average True Range vs 200-day ATR distribution
- **Range:** 0-100 percentile
- **Impact:** ATR >80th percentile gets +8-10 points (~12-15% boost on 65-point base)
- **Data Source:** yfinance, 24h cache
- **Interpretation:**
  - p80+: Very high recent volatility, expect large price swings
  - p50: Average volatility
  - p20-: Low volatility, expect muted reaction

#### Market Regime (SPY Returns)

- **Definition:** SPY 1-day, 5-day, and 20-day returns (primary: 5-day)
- **Range:** -10 to +10 points
- **Impact:** 
  - Bull market (+5% in 5d): +10 points
  - Bear market (-5% in 5d): -10 points
  - Combined with high beta + high ATR: total boost of 25-45%
- **Data Source:** yfinance, 24h cache
- **Interpretation:**
  - "bull": SPY up >2% in 5d, >5% in 20d
  - "bear": SPY down >2% in 5d, >5% in 20d
  - "neutral": Otherwise

**Example Cumulative Impact:**
```
Event: Earnings (base 65)
Beta: 1.8 (high) → +10
ATR: 85th percentile → +8
Market: Bull (+3% in 5d) → +6
Near earnings → +8
Total: 65 + 32 = 97 (49% boost from market data)
```

### 3. Confidence Score (0-100)

Confidence is computed as the **minimum** of three factors:

#### A. Sample Size Confidence

Based on historical event count from `EventStats`:

| Sample Size | Confidence |
|-------------|------------|
| ≥ 30 events | 100 |
| 20-29 events | 85 |
| 10-19 events | 70 |
| 5-9 events | 55 |
| < 5 events | 40 |

#### B. Source Credibility

| Source Type | Confidence |
|-------------|------------|
| EDGAR/SEC | 100 |
| FDA | 100 |
| Official Newsroom | 85 |
| Press Release | 80 |
| Third Party | 70 |
| Unknown | 60 |

#### C. Data Completeness

| Completeness | Confidence |
|-------------|------------|
| Full (has EventStats) | 100 |
| Partial (no EventStats) | 70 |

**Final Confidence** = min(Sample Size Confidence, Source Credibility, Data Completeness)

**Rationale:** Confidence reflects weakest link in data quality chain.

## Output Contract

```json
{
  "base_score": 65,
  "context_score": 14,
  "final_score": 79,
  "confidence": 70,
  "rationale": [
    "Base=earnings(65)",
    "Sector beta +5",
    "ATR p80 +6",
    "After hours +4",
    "Market regime -1",
    "Confidence: 70%"
  ]
}
```

## UI Visual Scale

The frontend displays scores using a color-coded system with confidence indicators:

### Score Color Mapping

Final scores are rendered as colored pills with the following scale:

| Score Range | Color | Label | Interpretation |
|-------------|-------|-------|----------------|
| 80-100 | Red/Crimson | CRITICAL | Maximum market impact expected |
| 70-79 | Orange | HIGH | Significant impact likely |
| 60-69 | Yellow/Amber | ELEVATED | Moderate-to-high impact |
| 50-59 | Light Blue | MODERATE | Standard market reaction |
| 0-49 | Gray | LOW | Minimal expected impact |

### Confidence Display

Each score includes a visual confidence bar showing the reliability of the prediction:

- **100% confidence**: Solid bar, based on 30+ historical events and verified sources
- **85% confidence**: Strong bar, 20-29 historical events
- **70% confidence**: Medium bar, 10-19 historical events
- **55% confidence**: Weak bar, 5-9 historical events
- **40% confidence**: Minimal bar, <5 historical events

### Factor Breakdown Tooltips

Hover over any score pill to see the top 3 contributing factors:

**Example Tooltip:**
```
Score: 79 (High Impact)
Confidence: 70%

Top Factors:
• Base: Earnings (65)
• ATR Volatility p80: +6
• After Hours: +4
```

### UI Integration Points

- **Events Table**: Color-coded score pills in dedicated column
- **Company Events Timeline**: Expandable rows show score history
- **Watchlist**: Upcoming events display predicted scores with confidence
- **Filter Controls**: Sort by score (descending/ascending), filter by impact level

## API Endpoints

### GET /scores/events/{event_id}

Retrieve score for a specific event.

**Response:** `EventScoreResponse`
**Cache:** 60 seconds
**Target Latency:** <200ms warm

**Example:**
```bash
GET /scores/events/12345
```

### GET /scores/?ticker=AAPL&limit=50

List recent event scores with optional filtering.

**Query Parameters:**
- `ticker` (optional): Filter by stock ticker
- `limit` (default: 50, max: 100): Number of results

**Cache:** 30 seconds

### POST /scores/rescore?ticker=AAPL&force=true

Admin endpoint to recompute scores in batch.

**Query Parameters:**
- `ticker` (optional): Filter by stock ticker
- `limit` (optional, max: 10000): Maximum events to process
- `force` (default: false): Recompute even if score exists

**Note:** Long-running operation, processes in batches of 100.

## Configuration Files

### backend/config/scoring.yml

Defines tunable parameters:

- **base_scores**: Event type → base score mapping
- **context_weights**: Multiplier weights and ranges
- **source_credibility**: Source type → confidence mapping
- **confidence.sample_size_quantiles**: Sample size thresholds
- **confidence.data_completeness**: Completeness scores

**Hot-reload:** No (requires app restart)

## Background Jobs

### jobs/compute_event_scores.py

**Schedule:** Nightly (can be configured)
**Function:** Compute scores for all events without scores
**Batch Size:** 100 events per commit
**Limit:** 1000 events per run (prevents long runs)
**Idempotence:** Yes

**Manual Execution:**
```bash
cd backend
python jobs/compute_event_scores.py
```

## Performance

### Caching Strategy

- **Event score endpoint:** 60-second TTL
- **List scores endpoint:** 30-second TTL
- **Implementation:** In-memory dictionary with expiration timestamps
- **Cache invalidation:** On rescore operation

### Latency Targets

- **GET /scores/events/{id}** (warm): <200ms
- **GET /scores/** (warm): <300ms
- **POST /scores/rescore**: Variable (long-running, 100-1000+ events)

### Database Indexes

- `ix_event_scores_event_id`: Unique event lookup
- `ix_event_scores_ticker`: Ticker filtering
- `ix_event_scores_ticker_event_type`: Combined filtering

## Tuning Guide

### Increasing Event Impact

To make specific event types score higher:

1. Edit `backend/config/scoring.yml`
2. Increase `base_scores.{event_type}` value
3. Restart API server
4. Run rescore: `POST /scores/rescore?force=true`

**Example:** Increase FDA approvals from 90 to 95:
```yaml
base_scores:
  fda_approval: 95
```

### Adjusting Context Weights

To modify multiplier influence:

1. Edit `context_weights` in `scoring.yml`
2. Adjust min/max or fixed values
3. Restart and rescore

**Example:** Reduce after-hours bonus from +4 to +2:
```yaml
context_weights:
  after_hours: 2
```

### Confidence Calibration

To require more historical data for high confidence:

```yaml
confidence:
  sample_size_quantiles:
    q90: 50  # Require 50+ events for 100% confidence (was 30)
```

## Invariants

1. **Final Score Range:** Always [0, 100]
2. **Confidence Range:** Always [0, 100]
3. **Idempotence:** Recomputing same event produces identical score
4. **Determinism:** Same inputs → same outputs (no randomness)
5. **Database Consistency:** One EventScore per Event (enforced by unique constraint)

## Examples

### Example 1: High-Impact FDA Approval

**Input:**
- Event: FDA approval for biotech company
- Sector: Biotech (high beta)
- Volatility: p85 (high)
- Sample Size: 25 historical FDA approvals

**Computation:**
```
Base Score: 90 (fda_approval)
Context:
  + Sector beta: +10 (high beta)
  + Volatility: +9 (p85)
  + After hours: +4 (announced 5:00 PM)
Context Score: +23

Final Score: min(100, 90 + 23) = 100
Confidence: min(85, 100, 100) = 85
```

### Example 2: Routine Earnings with Duplicate

**Input:**
- Event: Q3 earnings
- Similar earnings filed 3 days ago
- Sector: Consumer Staples (low beta)
- Market: Down -3% (bearish)

**Computation:**
```
Base Score: 65 (earnings)
Context:
  + Sector beta: +0 (low beta)
  + Market regime: -6 (bearish)
  + Duplicate penalty: -8
Context Score: -14

Final Score: max(0, 65 - 14) = 51
Confidence: min(70, 85, 100) = 70
```

## Testing

See `backend/tests/unit/test_scoring.py` for unit tests covering:
- Base score lookup
- Context multiplier calculations
- Score clamping
- Confidence computation
- Edge cases (missing data, extreme values)

See `backend/tests/integration/test_event_scoring.py` for integration tests.

## Machine Learning Integration (Implemented - Dec 2025)

The dynamic scoring system now integrates with the **Market Echo Engine**, a self-learning ML system that improves predictions based on realized stock price movements.

### ML Scoring Features

1. **Multi-Horizon Predictions:** XGBoost + Neural Network ensemble generates predictions for 1d, 5d, and 20d horizons
2. **Directional Accuracy:** Separate accuracy tracking for bullish vs. bearish predictions
3. **Probabilistic Forecasting:** Prediction intervals (10th-90th percentile) with conformal calibration
4. **Automated Hourly Scoring:** All new events receive ML predictions within one hour
5. **Model Drift Detection:** Automatic alerts when accuracy drops >5% from baseline

### Topology-Enhanced Features

The ML models incorporate persistent homology features from topological data analysis:

- **Betti Counts (β₀/β₁):** Connected components and loops in price attractor
- **Persistence Metrics:** Max/mean lifetimes, total persistence, entropy
- **Topological Complexity:** Weighted composite of structural features

### 3-Tier Accuracy System

1. **Tier 1 - Drift Monitoring:** Rolling window metrics (7d/30d/90d), CalibrationService with ECE computation
2. **Tier 2 - Feature Store & Stacked Ensemble:** XGBoost + LightGBM + topology-weighted meta-learner
3. **Tier 3 - Probabilistic Forecasting:** QuantileRegressor with options data integration (IV, skew, put-call ratio)

### API Endpoints (ML)

- `GET /ml/predictions/{event_id}` - Get ML prediction with confidence intervals
- `GET /ml/accuracy` - Model performance dashboard data
- `POST /ml/retrain` - Trigger model retraining (admin)

## Future Enhancements

Potential improvements for future waves:

1. ~~**Machine Learning:** Replace rule-based scoring with trained models~~ ✅ IMPLEMENTED
2. ~~**Real-time Market Data:** Incorporate live volatility and sentiment~~ ✅ IMPLEMENTED
3. **Sector-Specific Rules:** Custom multipliers per industry
4. **Event Clustering:** Detect related events for better duplicate detection
5. ~~**Historical Accuracy Tracking:** Monitor prediction vs. actual moves~~ ✅ IMPLEMENTED

## Troubleshooting

### Scores Not Appearing

**Symptom:** Events have no scores in database

**Solutions:**
1. Check if nightly job is running: `grep "scoring job" /var/log/releaseradar/api.log`
2. Manually trigger scoring: `POST /scores/rescore`
3. Check for errors in logs

### Low Confidence Scores

**Symptom:** All confidence scores are <50

**Causes:**
- Insufficient EventStats historical data (run Wave A backfill)
- Unknown source types (add to config)
- Data completeness flag incorrectly set

### Unexpected Score Values

**Debug Steps:**
1. Check `rationale` field in EventScore for factor breakdown
2. Verify config values in `scoring.yml`
3. Test individual multiplier functions with sample data

## References

- **Code:** `backend/analytics/scoring.py`
- **Config:** `backend/config/scoring.yml`
- **Models:** `backend/releaseradar/db/models.py` (EventScore)
- **API:** `backend/api/routers/scores.py`
- **Jobs:** `backend/jobs/compute_event_scores.py`
