# Market Echo Engine - ML Architecture Map

**Last Updated:** November 20, 2025  
**Purpose:** Internal reference for ML system components, data flow, and implementation details

---

## System Overview

The Market Echo Engine is a self-learning ML system that improves event impact predictions by learning from realized stock price movements. It operates in a continuous feedback loop:

1. **Predict** → Events get scored (deterministic + ML-adjusted)
2. **Label** → After T+1/T+5/T+20 days, realized price movements are recorded
3. **Train** → ML models learn from labeled outcomes
4. **Improve** → Next predictions use learned patterns

---

## Core Components

### 1. Labeling Pipeline (`backend/jobs/ml_learning_pipeline.py`)

**Entry Point:** `run_ml_etl_pipeline(lookback_days=60)`

**Stages:**
1. **Label Outcomes** → `OutcomeLabeler.label_events()` from `backend/releaseradar/ml/pipelines/label_outcomes.py`
   - Fetches price data via yfinance
   - Computes abnormal returns (stock - SPY benchmark)
   - Stores in `event_outcomes` table
   
2. **Compute Stats** → `OutcomeLabeler.compute_event_stats()`
   - Aggregates historical patterns by (ticker, event_type)
   - Updates `event_stats` table
   
3. **Extract Features** → `FeaturePipeline.extract_features_for_events()` from `backend/releaseradar/ml/pipelines/extract_features.py`
   - Generates 50+ features per event
   - Stores in `model_features` table

**Idempotency:** Uses UniqueConstraint on `(event_id, horizon)` to prevent duplicates

**Scheduled:** Daily via `backend/jobs/daily_ml_retraining.py` (calls this pipeline first)

---

### 2. Training Pipeline (`backend/jobs/daily_ml_retraining.py`)

**Entry Point:** `run_daily_ml_retraining()`

**Flow:**
1. Run ETL pipeline (labeling)
2. Check retraining triggers (via `ModelMonitor.should_retrain()`)
3. Train models for each horizon (1d, 5d, 20d)
4. Promote models if 2%+ accuracy improvement
5. Health check on active models

**Retraining Triggers:**
- 50+ new labeled samples available
- 7+ days since last training
- Accuracy drops >2% from baseline

**Implementation:** `HierarchicalRetrainingPipeline` in `backend/releaseradar/ml/pipelines/retrain_model.py`
- Trains family-specific models (e.g., `sec_8k`) when 100+ samples + 20+ tickers
- Trains global models as fallback

---

### 3. Prediction Service (`backend/releaseradar/ml/serving.py`)

**Class:** `MLScoringService`

**Methods:**
- `predict_single(event_id, horizon)` → ML prediction for one event
- `predict_batch(event_ids, horizon)` → Batch predictions
- `get_best_model_for_event(event_type, horizon)` → Hierarchical model lookup

**Model Selection Logic:**
1. Try family-specific model (e.g., "sec_8k" family)
2. Fall back to global model (event_type_family="all")
3. Fall back to deterministic only (model=None)

**Caching:** Model availability cached to avoid repeated DB lookups

**Score Adjustment:** ML can adjust impact_score by ±20 points max, weighted by confidence

---

### 4. Monitoring & Health (`backend/releaseradar/ml/monitoring.py`)

**Class:** `ModelMonitor`

**Key Methods:**
- `get_model_health(model_name, horizon)` → Health status and drift metrics
- `should_retrain(model_name, horizon)` → Retraining recommendation
- `calculate_recent_accuracy(model_name, horizon, lookback_days=7)` → Recent performance

**Tracked Metrics:**
- Directional accuracy (1d, 5d, 20d)
- MAE (Mean Absolute Error)
- RMSE (Root Mean Squared Error)
- Accuracy degradation vs baseline

---

## Database Tables

### `event_outcomes`
**Purpose:** Labeled training data (realized price movements)

**Schema:**
- `event_id` (FK to events) + `horizon` (1d/5d/20d) → UniqueConstraint
- `price_before`, `price_after` → Raw prices
- `return_pct_raw` → Raw stock return
- `benchmark_return_pct` → SPY return for same period
- `return_pct` → **Abnormal return** (stock - SPY) ← **PRIMARY ML TARGET**
- `abs_return_pct` → Absolute abnormal return
- `direction_correct` → Was prediction direction correct?
- `has_benchmark_data` → Whether SPY data was available
- `label_date` → When this label was computed

**Current Data:** 355 labeled events (Nov 15-16, 2025)

---

### `model_registry`
**Purpose:** Tracks trained ML models and their versions

**Schema:**
- `name` → e.g., "xgboost_impact_1d_sec_8k"
- `version` → Semantic version (e.g., "1.0.2")
- `event_type_family` → "sec_8k", "earnings", "all", etc.
- `horizon` → "1d", "5d", "20d"
- `status` → "staging" | "active" | "archived"
- `model_path` → Path to serialized .joblib file
- `metrics` → JSON with MAE, RMSE, directional_accuracy
- `trained_at`, `promoted_at` → Timestamps
- `feature_version` → Compatible feature schema

**Active Models (5):**
- xgboost_impact_1d_sec_8k (v1.0.2) → 60.4% accuracy
- xgboost_impact_5d_sec_8k (v1.0.2) → 58.3% accuracy
- xgboost_impact_1d_global (v1.0.0) → 60.4% accuracy
- xgboost_impact_5d_global (v1.0.0) → 58.3% accuracy
- xgboost_impact_20d_global (v1.0.0) → 60.0% accuracy

---

### `model_features`
**Purpose:** Engineered features for ML training/prediction

**Schema:**
- `event_id` (FK) + `horizon` → UniqueConstraint
- `features` → JSON with full feature vector (50+ features)
- `feature_version` → Schema version
- Scalar fields (duplicated for fast filtering):
  - `base_score`, `sector`, `event_type`, `market_vol`, `info_tier`

**Feature Engineering:** `FeatureExtractor` class in `backend/releaseradar/ml/features.py`

---

### `price_history`
**Purpose:** Historical OHLCV data for backtesting

**Schema:**
- `ticker`, `date` → UniqueConstraint
- `open`, `close`, `high`, `low`, `volume`
- `source` → "yahoo" (yfinance)

**Usage:** Primarily used by backtesting engine (`BacktestEngine` in `backend/backtesting.py`)

---

### `event_stats`
**Purpose:** Aggregated historical patterns by (ticker, event_type)

**Schema:**
- `ticker`, `event_type` → UniqueConstraint
- `sample_size` → Number of historical events
- `win_rate` → % of events where stock went up
- `avg_abs_move_1d/5d/20d` → Average absolute price move
- `mean_move_1d/5d/20d` → Average directional move

**Computed By:** `OutcomeLabeler.compute_event_stats()` during ETL pipeline

---

## Backtesting & Accuracy Computation

### BacktestEngine (`backend/backtesting.py`)

**Purpose:** Validate predictions against actual price movements

**Key Methods:**
- `analyze_event_accuracy(event_id)` → Single-event analysis
- `aggregate_accuracy_by_type(event_type, sector, ...)` → Aggregate metrics
- `get_family_coverage_summary(tickers)` → Model coverage by family

**Metrics Computed:**
- Directional accuracy (1d, 5d, 20d)
- High-confidence accuracy (score ≥ 70)
- Magnitude error (predicted_score vs actual_return)
- Average actual returns

**Data Flow:**
1. Fetch events with `event_outcomes` (labeled data only)
2. Compare predicted direction/score to actual return
3. Compute accuracy metrics per horizon
4. Group by event_type, sector, or family

**NOTE:** Uses existing `event_outcomes` table for accuracy (no separate backtesting table)

---

## API Endpoints

### ML Scoring (`backend/api/routers/ml_scores.py`)

**Endpoints:**
- `GET /ml-scores/predict/{event_id}?horizon=1d` → Single prediction
- `POST /ml-scores/predict/batch` → Batch predictions
- `GET /ml-scores/model-info?horizon=1d` → Active models by family
- `GET /ml-scores/model-info/{horizon}` → Specific horizon model
- `GET /ml-scores/performance/{horizon}` → Model health metrics
- `GET /ml-scores/stats` → Overall ML system stats

**Response Fields:**
- `base_score` → Deterministic score (0-100)
- `ml_prediction` → Raw ML model output
- `ml_adjusted_score` → Final blended score
- `ml_confidence` → Model confidence (0.0-1.0)
- `delta_applied` → Actual adjustment made
- `model_source` → "family-specific" | "global" | "deterministic"
- `predicted_return_1d` → ML predicted return %

---

## UI Components

### Backtesting Tab (`marketing/components/dashboard/BacktestingTab.tsx`)

**Sections:**
1. **Coverage Summary** → Shows labeled events by family + horizon
2. **Model Health** → Active model status + metrics
3. **Detailed Accuracy** → Event-by-event analysis with filters
4. **Visualizations** → Circular progress bars for accuracy metrics

**Data Sources:**
- `GET /backtesting/family-coverage` → Family stats
- `GET /backtesting/accuracy?event_type=...` → Detailed metrics
- `GET /ml-scores/model-info` → Model info

---

### Market Echo Page (`marketing/app/market-echo/page.tsx`)

**Purpose:** Public-facing explanation of the Market Echo Engine

**Content:**
- 4 Phases (Predict → Echo → Learn → Improve)
- Key Features (Abnormal Returns, AI Guardrails, Transparency)
- Technical Highlights (355+ labeled events, hierarchical models)

---

### RadarQuant AI Tab (`marketing/components/dashboard/RadarQuantTab.tsx`)

**Purpose:** AI chat interface (uses OpenAI GPT-4)

**Features:**
- Preset questions about events and market patterns
- Streaming responses
- Plan-based usage quotas

**NOTE:** Separate from Market Echo Engine (GPT-4 chat vs XGBoost predictions)

---

## Data Flow Summary

```
┌─────────────────┐
│  Events Created │ (SEC, FDA, etc.)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Deterministic   │ impact_score (0-100)
│ Scoring         │ direction (bullish/bearish/neutral)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ ML Prediction   │ ml_adjusted_score
│ (if available)  │ ml_confidence
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Event Stored    │ (events table)
└────────┬────────┘
         │
  [T+1, T+5, T+20 days pass]
         │
         ▼
┌─────────────────┐
│ ETL Pipeline    │ (nightly job)
│ Labels Outcomes │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ event_outcomes  │ return_pct (abnormal return)
│ + model_features│ features JSON
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Training        │ (when 50+ new samples)
│ Pipeline        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ model_registry  │ (new version promoted)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Next Event      │ Uses improved model!
│ Gets Predicted  │
└─────────────────┘
```

---

## Key File Locations

**Labeling & ETL:**
- `backend/jobs/ml_learning_pipeline.py` → Main ETL orchestrator
- `backend/releaseradar/ml/pipelines/label_outcomes.py` → OutcomeLabeler class
- `backend/releaseradar/ml/pipelines/extract_features.py` → FeaturePipeline class

**Training:**
- `backend/jobs/daily_ml_retraining.py` → Daily retraining orchestrator
- `backend/releaseradar/ml/pipelines/retrain_model.py` → HierarchicalRetrainingPipeline
- `backend/releaseradar/ml/training.py` → ModelTrainer (XGBoost wrapper)

**Prediction:**
- `backend/releaseradar/ml/serving.py` → MLScoringService
- `backend/data_manager.py` → Calls MLScoringService during event creation

**Monitoring:**
- `backend/releaseradar/ml/monitoring.py` → ModelMonitor class

**Backtesting:**
- `backend/backtesting.py` → BacktestEngine class

**API:**
- `backend/api/routers/ml_scores.py` → ML prediction endpoints

**UI:**
- `marketing/components/dashboard/BacktestingTab.tsx` → Backtesting UI
- `marketing/app/market-echo/page.tsx` → Market Echo landing page

---

## Current Status (Nov 20, 2025)

**Training Data:**
- 355 labeled SEC 8-K events
- 238 unique tickers
- 2 days of labeled data (Nov 15-16)

**Model Performance:**
- 1-day accuracy: **71.3%** (253/355 correct)
- 5-day accuracy: **57.3%** (184/321 correct)
- 20-day accuracy: **56.6%** (43/76 correct)

**Active Models:** 5 models (2 family-specific sec_8k, 3 global fallback)

**Next Steps:** (see hardening spec)
- Scale to 1,000-1,500+ labeled events
- Add CLI tool for manual labeling
- Build ML monitoring dashboard
- Improve UI labeling (base vs ML-adjusted)
- Add prototype disclaimers
