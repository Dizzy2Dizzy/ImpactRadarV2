# Impact Radar Feature Map

**Document Version:** 1.0  
**Last Updated:** November 15, 2025  
**Purpose:** Comprehensive mapping of all features for QA testing and hardening

## Table of Contents
1. [Authentication & Authorization](#1-authentication--authorization)
2. [Event System](#2-event-system)
3. [Impact Scoring](#3-impact-scoring)
4. [Portfolio Management](#4-portfolio-management)
5. [Watchlist Management](#5-watchlist-management)
6. [Alerts & Notifications](#6-alerts--notifications)
7. [AI Features (RadarQuant)](#7-ai-features-radarquant)
8. [Analytics](#8-analytics)
9. [X.com / Social Sentiment](#9-xcom--social-sentiment)
10. [Charts & Projector](#10-charts--projector)
11. [Pricing & Billing](#11-pricing--billing)
12. [Admin & Scanner Status](#12-admin--scanner-status)
13. [Background Jobs](#13-background-jobs)
14. [Machine Learning (Self-Learning AI)](#14-machine-learning-self-learning-ai)

---

## 1. Authentication & Authorization

### 1.1 User Registration
- **Routes/Components:**
  - Backend: `backend/api/routers/auth.py` - `POST /auth/signup`
  - Frontend: `marketing/app/signup/page.tsx`
- **Services:** `backend/auth_service.py`
- **DB Tables:** `users`
- **Features:**
  - Email-based signup
  - Password hashing (bcrypt)
  - Email verification code generation
  - Input validation (email format, password strength)

### 1.2 Email Verification
- **Routes/Components:**
  - Backend: `POST /auth/verify-email`, `POST /auth/resend-code`
  - Frontend: `marketing/app/verify-email/page.tsx`
- **Services:** `backend/email_service.py`, `backend/alerts/email_service.py`
- **DB Tables:** `users` (verification_code, verification_code_expires)
- **Features:**
  - Verification code generation (6 digits)
  - Code expiry (15 minutes)
  - Code resend with rate limiting
  - Email delivery via SMTP/Resend

### 1.3 Login/Logout
- **Routes/Components:**
  - Backend: `POST /auth/login`, `POST /auth/logout`
  - Frontend: `marketing/app/login/page.tsx`
- **Services:** `backend/api/utils/auth.py`
- **DB Tables:** `users`
- **Features:**
  - JWT-based session management
  - Password verification
  - Token generation (access tokens)
  - Secure cookie handling

### 1.4 Session Management
- **Routes/Components:**
  - Backend: `GET /auth/me`
- **Services:** `backend/api/utils/auth.py`
- **Features:**
  - JWT token validation
  - User context retrieval
  - Plan-based access control
  - Token refresh mechanisms

### 1.5 API Key Management
- **Routes/Components:**
  - Backend: `backend/api/routers/keys.py`
  - Frontend: `marketing/app/account/api-keys/page.tsx`
- **DB Tables:** `api_keys`
- **Features:**
  - API key generation
  - Key rotation
  - Usage tracking (30-day rolling quotas)
  - Key-based authentication
  - Rate limiting per key

### 1.6 Account & Profile Management
- **Routes/Components:**
  - Backend: `backend/api/routers/account.py` - `GET /account`, `PUT /account`
  - Frontend: `marketing/components/dashboard/AccountTab.tsx`
- **DB Tables:** `users`
- **Features:**
  - Profile viewing and editing
  - Email address updates
  - Plan management (view current plan, upgrade options)
  - Account settings
  - Notification preferences
  - Password management

### 1.7 Onboarding
- **Routes/Components:**
  - Frontend: `marketing/components/dashboard/OnboardingChecklist.tsx`, `DashboardWithOnboarding.tsx`
- **Features:**
  - First-time user onboarding flow
  - Checklist of key actions:
    - Add tickers to watchlist
    - Upload portfolio
    - Set up alerts
    - Explore RadarQuant AI
  - Progress tracking
  - Dismiss/skip functionality

---

## 2. Event System

### 2.1 Event Display & Filtering
- **Routes/Components:**
  - Backend: `backend/api/routers/events.py` - `GET /events`, `GET /events/{id}`
  - Frontend: `marketing/components/dashboard/EventsTab.tsx`
- **Services:** `backend/data_manager.py`
- **DB Tables:** `events`, `companies`
- **Features:**
  - Event list with pagination
  - Multi-criteria filtering (ticker, event_type, sector, direction, date_range)
  - Impact score range filtering
  - Watchlist-only filtering
  - Info tier filtering (primary/secondary)
  - Event detail view with source links
  - Real-time event streaming (WebSocket)

### 2.2 Event Ingestion
- **Routes/Components:**
  - Backend: `backend/scanners/impl/` (all scanner implementations)
- **Services:**
  - `backend/scanners/impl/sec_edgar.py` - SEC EDGAR scanner
  - `backend/scanners/impl/sec_8k.py` - SEC 8-K scanner
  - `backend/scanners/impl/sec_10q.py` - SEC 10-Q scanner
  - `backend/scanners/impl/fda.py` - FDA announcements
  - `backend/scanners/impl/press.py` - Company press releases
  - `backend/scanners/impl/earnings.py` - Earnings calls
  - `backend/scanners/impl/guidance.py` - Guidance updates
  - `backend/scanners/impl/product_launch.py` - Product launches
  - `backend/scanners/impl/ma.py` - M&A activity
  - `backend/scanners/impl/dividend.py` - Dividends/buybacks
- **DB Tables:** `events`, `scanner_logs`
- **Features:**
  - Automated event scanning on schedules
  - Duplicate detection (ticker + event_type + date + title)
  - Source URL extraction and validation
  - Event normalization
  - Metadata extraction (e.g., 8-K items)

### 2.3 Global Scanners (10 Active)
- **Routes/Components:**
  - Backend: `backend/scanners/catalog.py` - Scanner registry
- **Features:**
  - **SEC EDGAR** (4hr interval) - All SEC filings
  - **FDA Announcements** (6hr) - FDA decisions and announcements
  - **Company Press Releases** (8hr) - Official company news
  - **Earnings Calls** (1hr) - Earnings announcements
  - **SEC 8-K** (15min) - Current reports
  - **SEC 10-Q** (6hr) - Quarterly reports
  - **Guidance Updates** (2hr) - Company guidance changes
  - **Product Launches** (3hr) - New product announcements
  - **M&A / Strategic** (1hr) - Merger and acquisition activity
  - **Dividends / Buybacks** (4hr) - Shareholder returns

### 2.4 Event Search
- **Routes/Components:**
  - Backend: `GET /events/search`
  - Frontend: `marketing/components/dashboard/AdvancedSearchModal.tsx`
- **Features:**
  - Keyword search across title and description
  - Boolean operators (AND, OR)
  - Multi-field filtering
  - Relevance scoring

### 2.5 Event Statistics
- **Routes/Components:**
  - Backend: `backend/api/routers/stats.py`
- **DB Tables:** `event_stats`
- **Features:**
  - Historical event counts by type
  - Average impact by event type
  - Typical price movements (1d, 5d, 20d)
  - Statistical aggregations

### 2.6 Real-time Event Streaming
- **Routes/Components:**
  - Backend: `backend/api/routers/stream.py` - `GET /stream/events` (SSE)
  - Backend: `backend/api/routers/websocket.py` - `GET /ws/events` (WebSocket)
  - Backend: `backend/api/websocket/hub.py` - WebSocket hub manager
  - Frontend: `marketing/components/dashboard/LiveEventsProvider.tsx`, `LiveTape.tsx`
  - Frontend: `marketing/stores/liveEventsStore.ts`
- **DB Tables:** `events`
- **Features:**
  - **SSE (Server-Sent Events):**
    - Long-lived HTTP connection for event stream
    - JSON-lines message format
    - Automatic reconnection
    - Plan-based filtering
  - **WebSocket:**
    - Full-duplex real-time communication
    - JWT authentication
    - Per-user connection limits
    - Backpressure handling
    - Graceful disconnect/reconnect
  - **Live Tape:**
    - Scrolling ticker of latest events
    - Real-time updates on dashboard
    - Impact score indicators
    - Click-through to event details
  - **Event Broadcasting:**
    - New events broadcast to all connected clients
    - Filtered by user plan and watchlist
    - Deduplication
    - Error handling and logging

---

## 3. Impact Scoring

### 3.1 Deterministic Scoring
- **Routes/Components:**
  - Backend: `backend/impact_scoring.py` - `ImpactScorer.score_event()`
- **DB Tables:** `events` (impact_score, direction, confidence, rationale)
- **Features:**
  - Base scores by event type (0-100)
  - Sector-specific multipliers
  - Market cap adjustments
  - Direction determination (positive/negative/neutral/uncertain)
  - Confidence calculation
  - Human-readable rationale generation
  - 8-K item-based scoring

### 3.2 Probabilistic Scoring
- **Routes/Components:**
  - Backend: `backend/impact_models/` - Event study models
- **Services:**
  - `backend/impact_models/event_study.py` - P(move), P(up), P(down)
  - `backend/impact_models/confidence.py` - Confidence calculation
- **DB Tables:** `events` (impact_p_move, impact_p_up, impact_p_down)
- **Features:**
  - Probability calculations based on historical priors
  - Normal distribution assumptions
  - Sample size adjustments
  - Noise penalty for high volatility groups

### 3.3 ML-Adjusted Scoring
- **Routes/Components:**
  - Backend: `backend/releaseradar/ml/serving.py` - `MLScoringService`
  - Backend: `backend/api/routers/ml_scores.py`
- **DB Tables:** `events` (ml_adjusted_score, ml_confidence, ml_model_version)
- **Features:**
  - Machine learning predictions (XGBoost)
  - Confidence-weighted blending with base score
  - Capped adjustments (±20 max delta)
  - Model version tracking
  - Graceful degradation when ML unavailable

### 3.4 Custom Scoring Preferences
- **Routes/Components:**
  - Backend: `backend/api/routers/preferences.py`
  - Frontend: `marketing/components/dashboard/ScoringPreferencesModal.tsx`
- **DB Tables:** `user_scoring_preferences`
- **Features:**
  - User-defined weights by event type
  - Sector-specific multipliers
  - Market cap preferences
  - Volatility adjustments
  - Personalized impact calculations

---

## 4. Portfolio Management

### 4.1 Portfolio Upload (CSV)
- **Routes/Components:**
  - Backend: `POST /portfolio/upload` - `backend/api/routers/portfolio.py`
  - Frontend: `marketing/components/dashboard/PortfolioTab.tsx`
- **DB Tables:** `portfolios`, `positions`
- **Features:**
  - CSV file parsing (ticker, shares, cost_basis, label, as_of)
  - Duplicate ticker aggregation
  - Weighted average cost basis calculation
  - Plan-based limits (Free: 3 tickers, Pro/Enterprise: unlimited)
  - Validation and error reporting
  - Ticker existence checking

### 4.2 Portfolio Holdings Management
- **Routes/Components:**
  - Backend: `GET /portfolio`, `GET /portfolio/holdings`, `DELETE /portfolio`
- **DB Tables:** `portfolios`, `positions`, `companies`
- **Features:**
  - View all positions
  - Position details with P&L
  - Current price fetching (yfinance)
  - Market value calculation
  - Portfolio deletion

### 4.3 Portfolio Insights & Exposure
- **Routes/Components:**
  - Backend: `GET /portfolio/insights` - `backend/api/routers/portfolio.py`
- **Services:** `backend/market_data_service.py`
- **DB Tables:** `portfolios`, `positions`, `events`
- **Features:**
  - Upcoming events analysis (default 30-day window)
  - Dollar exposure calculation (1d, 5d, 20d horizons)
  - Risk score per position
  - Typical price movement estimates
  - Event count per holding
  - Portfolio-level risk aggregation

### 4.4 Portfolio Export
- **Routes/Components:**
  - Backend: `GET /portfolio/export`
  - Frontend: `marketing/components/dashboard/PortfolioTab.tsx`
- **Features:**
  - CSV export of holdings
  - Portfolio analysis export
  - Excel-compatible formatting

---

## 5. Watchlist Management

### 5.1 Watchlist CRUD
- **Routes/Components:**
  - Backend: `backend/api/routers/watchlist.py`
  - Frontend: `marketing/components/dashboard/WatchlistTab.tsx`
- **DB Tables:** `watchlists`
- **Features:**
  - Add/remove tickers
  - View watchlist
  - Ticker validation
  - Multiple watchlists per user (future)

### 5.2 Watchlist Filtering
- **Routes/Components:**
  - Backend: `GET /events?watchlist_only=true`
- **Features:**
  - Event filtering by watchlist tickers
  - Batch ticker queries

---

## 6. Alerts & Notifications

### 6.1 Alert Creation
- **Routes/Components:**
  - Backend: `backend/api/routers/alerts.py` - `POST /alerts`
  - Frontend: `marketing/components/dashboard/AlertsTab.tsx`
- **DB Tables:** `user_alerts`
- **Features:**
  - User-defined alert criteria:
    - Ticker(s)
    - Event types
    - Minimum impact score
    - Specific direction
  - Alert name and description
  - Active/inactive toggle

### 6.2 Alert Matching & Dispatch
- **Routes/Components:**
  - Backend: `backend/alerts/dispatch.py` - `AlertDispatcher`
- **Services:** `backend/alerts/email_service.py`
- **DB Tables:** `user_alerts`, `alert_deliveries`
- **Features:**
  - Real-time event matching against alert criteria
  - Deduplication (prevent repeat notifications for same event)
  - Email notifications
  - In-app notification storage
  - Delivery tracking

### 6.3 Notifications Retrieval
- **Routes/Components:**
  - Backend: `GET /notifications` - `backend/api/routers/notifications.py`
  - Frontend: `marketing/components/dashboard/AccountTab.tsx`
- **DB Tables:** `notifications`
- **Features:**
  - Notification list with pagination
  - Mark as read
  - Notification clearing

---

## 7. AI Features (RadarQuant)

### 7.1 RadarQuant AI Assistant
- **Routes/Components:**
  - Backend: `backend/api/routers/ai.py` - `POST /ai/query`
  - Frontend: `marketing/components/dashboard/RadarQuantTab.tsx`
- **Services:** `backend/ai/radarquant.py` - `RadarQuantOrchestrator`
- **DB Tables:** `events`, `companies`, `watchlists`
- **Features:**
  - OpenAI GPT-4 integration
  - Context-aware responses using user watchlist, recent events, X.com feed
  - Plan-based quota limits (Free: 5/day, Pro: 50/day, Enterprise: unlimited)
  - Query history
  - Event references with links
  - Market analysis and insights
  - Prevents fabrication of non-existent events

### 7.2 AI Query Safeguards
- **Services:** `backend/ai/radarquant.py`
- **Features:**
  - System prompt instructs against inventing filings
  - Only references events from database
  - Links to official sources
  - Graceful handling when OpenAI unavailable

---

## 8. Analytics

### 8.1 Backtesting Engine
- **Routes/Components:**
  - Backend: `backend/api/routers/backtesting.py` - `GET /backtesting/validate`
  - Frontend: `marketing/components/dashboard/BacktestingTab.tsx`
- **Services:** `backend/backtesting.py`
- **DB Tables:** `events`, `price_history`
- **Features:**
  - Prediction accuracy validation (1d, 5d, 20d horizons)
  - Directional accuracy metrics
  - MAE (Mean Absolute Error) calculation
  - Filtering by ticker, event type, date range
  - Historical price data fetching (yfinance)
  - Plan requirement: Pro or Enterprise

### 8.2 Event Correlation
- **Routes/Components:**
  - Backend: `backend/api/routers/correlation.py`
  - Frontend: `marketing/components/dashboard/CorrelationTab.tsx`
- **Services:** `backend/correlation.py`
- **DB Tables:** `events`
- **Features:**
  - Event timeline visualization
  - Pattern discovery (related events on same ticker)
  - Temporal clustering
  - Event sequence analysis
  - Plan requirement: Pro or Enterprise

### 8.3 Peer Comparison
- **Routes/Components:**
  - Backend: `backend/api/routers/peers.py`
  - Frontend: `marketing/components/dashboard/PeerComparisonModal.tsx`
- **Services:** `backend/peers.py`
- **DB Tables:** `events`, `companies`
- **Features:**
  - Find similar events on peer companies
  - Sector-based peer matching
  - Event type matching
  - Contextualization of events
  - Plan requirement: Pro or Enterprise

### 8.4 Calendar View
- **Routes/Components:**
  - Frontend: `marketing/components/dashboard/CalendarTab.tsx`, `CalendarDayModal.tsx`
- **DB Tables:** `events`
- **Features:**
  - Month-based event calendar
  - Watchlist filtering
  - Impact score indicators
  - Day-level event drilling
  - Plan requirement: Pro or Enterprise

### 8.5 Data Export
- **Routes/Components:**
  - Backend: `GET /events/export`, `GET /portfolio/export`
- **Features:**
  - CSV export of events
  - CSV export of portfolio analysis
  - Comprehensive filtering support
  - Excel-compatible formatting
  - Plan requirement: Pro or Enterprise

---

## 9. X.com / Social Sentiment

### 9.1 X.com Feed Integration
- **Routes/Components:**
  - Backend: `backend/api/routers/x_feed.py` - `GET /x-feed/clusters`
  - Frontend: `marketing/components/dashboard/XFeedTab.tsx`
- **Services:**
  - `backend/social/x_client.py` - X API v2 client
  - `backend/social/x_sentiment.py` - Sentiment analysis
  - `backend/social/x_event_linker.py` - Event linking
- **DB Tables:** None (real-time fetching)
- **Features:**
  - Fetch posts by ticker symbols (cashtags $AAPL)
  - X API v2 authentication (Bearer token)
  - Rate limit handling (100 reads/month on Free tier)
  - Post metadata (likes, retweets, followers)
  - Official API only (no scraping)

### 9.2 Sentiment Analysis
- **Services:** `backend/social/x_sentiment.py`
- **Features:**
  - OpenAI-based sentiment classification (bullish/bearish/neutral)
  - Event hint detection (earnings, FDA, guidance, product, macro)
  - Fallback keyword-based analysis
  - Confidence scoring (0-1)
  - Strength measurement (0-1)

### 9.3 Event Linking
- **Services:** `backend/social/x_event_linker.py`
- **Features:**
  - Match posts to Impact Radar events
  - Time window matching (±3 days)
  - Event type hint matching
  - Clustering by (event, ticker)
  - Aggregated sentiment per cluster
  - Weighted averaging by author followers

### 9.4 Sentiment Filtering
- **Frontend:** `marketing/components/dashboard/XFeedTab.tsx`
- **Features:**
  - Filter by sentiment (bullish/bearish/neutral)
  - Sort by confidence or support count
  - Expand/collapse clusters
  - Direct links to X.com posts
  - Plan requirement: Pro or Enterprise

---

## 10. Charts & Projector

### 10.1 Price Charts
- **Routes/Components:**
  - Backend: `backend/api/routers/charts.py` - `GET /charts/ticker/{ticker}`
  - Frontend: `marketing/components/dashboard/PriceChartModal.tsx`
- **Services:** `backend/services/market_data_service.py`
- **DB Tables:** `events`
- **Features:**
  - OHLCV price data (yfinance)
  - Event markers on charts
  - Customizable timeframes (1d to 1y)
  - Event click-through to details
  - Plan requirement: Pro or Enterprise

### 10.2 Projector (Advanced Trading Charts)
- **Routes/Components:**
  - Backend: `backend/api/routers/projector.py` - `GET /projector/data`
  - Frontend: `marketing/components/dashboard/ProjectorTab.tsx`
- **Services:** `backend/services/market_data_service.py`
- **DB Tables:** `events`, `price_history`
- **Features:**
  - Interactive candlestick/line charts (lightweight-charts library)
  - Technical indicators:
    - SMAs (20, 50, 200)
    - EMAs (20, 50)
    - RSI
    - MACD
  - Event overlays
  - Multiple timeframes (1m, 5m, 15m, 1h, 1d, 1w)
  - Period selection (1d to 1y)
  - Chart type toggle (candlestick/line)
  - Indicator toggles
  - Plan requirement: Pro or Enterprise

---

## 11. Pricing & Billing

### 11.1 Plan Tiers
- **Routes/Components:**
  - Backend: `backend/api/routers/pricing.py`
  - Frontend: `marketing/app/pricing/page.tsx`, `marketing/data/plans.ts`
- **Features:**
  - **Free Plan:** 10 events/day, 3 watchlist tickers, 3 portfolio tickers, basic scoring
  - **Pro Plan ($49/month):** Unlimited events, unlimited watchlist, unlimited portfolio, ML scoring, analytics, X.com feed, RadarQuant AI (50 queries/day), advanced features
  - **Team Plan ($199/month):** Everything in Pro + API access (100k calls/mo), up to 10 seats, SSO (Google/OIDC), Slack/Discord webhooks, dedicated support + SLA

### 11.2 Stripe Integration
- **Routes/Components:**
  - Backend: `backend/api/routers/billing.py` - `POST /billing/create-checkout`
  - Backend: `POST /billing/webhook` - Stripe webhook handler
- **Services:** `backend/payment_service.py`
- **DB Tables:** `users` (plan, stripe_customer_id, stripe_subscription_id)
- **Features:**
  - Stripe Checkout session creation
  - Subscription management
  - Webhook handling (payment success, subscription updates)
  - Plan upgrades/downgrades
  - Automatic feature access control
  - Test mode support

### 11.3 Usage Tracking
- **Routes/Components:**
  - Backend: `backend/api/utils/usage_tracking.py`
- **DB Tables:** `api_keys` (quota_used, quota_period_start), `rate_limit_state`
- **Features:**
  - 30-day rolling quota enforcement
  - Atomic quota updates
  - Burst rate limiting (SlowAPI)
  - Plan-based limits
  - Usage reset on quota period expiry

---

## 12. Admin & Scanner Status

### 12.1 Scanner Status Monitoring
- **Routes/Components:**
  - Backend: `backend/api/routers/scanners.py` - `GET /scanners/status`
  - Frontend: `marketing/components/dashboard/ScannersTab.tsx`
- **DB Tables:** `scanner_logs`
- **Features:**
  - Last run time per scanner
  - Next scheduled run
  - Discovery counts
  - Error messages
  - Status indicators (success/running/error)
  - Public endpoint (no auth required)

### 12.2 Manual Scanner Triggers
- **Routes/Components:**
  - Backend: `POST /scanners/run` - `backend/api/routers/scanners.py`
- **Services:** `backend/jobs/scan_worker.py`
- **DB Tables:** `scan_jobs`
- **Features:**
  - Admin-only endpoint
  - Company-level scans
  - Scanner-level scans
  - Job queuing
  - Background processing
  - Audit trail logging

### 12.3 Scanner Logs
- **Services:** `backend/data_manager.py` - `add_scanner_log()`, `get_scanner_logs()`
- **DB Tables:** `scanner_logs`
- **Features:**
  - Start/finish timestamps
  - Discovery counts
  - Error logging
  - Source tracking
  - Historical log retention (last 50)

---

## 13. Background Jobs

### 13.1 Scheduled Scanner Runs
- **Services:**
  - `backend/api/scheduler.py` - APScheduler configuration
  - `backend/scanners/impl/*` - Scanner implementations
- **Features:**
  - Automated scanning on intervals (15min to 8hr)
  - All 10 scanners active
  - Automatic deduplication
  - Error handling and retry
  - Job logging

### 13.2 ML Training Pipeline
- **Services:**
  - `backend/jobs/daily_ml_retraining.py` - Daily retraining job
  - `backend/releaseradar/ml/pipelines/` - Pipeline stages
- **DB Tables:** `event_outcomes`, `price_history`, `event_stats`, `ml_models`
- **Features:**
  - Daily automated retraining
  - Event outcome labeling (realized price movements)
  - Feature extraction (50+ features)
  - XGBoost model training
  - Model version tracking
  - Performance metrics (MAE, R², directional accuracy)
  - Automatic model promotion

### 13.3 Price Data Fetching
- **Services:** `backend/jobs/fetch_prices.py`
- **DB Tables:** `price_history`
- **Features:**
  - Batch price fetching (yfinance)
  - Historical price caching
  - Daily OHLCV updates
  - Error handling for missing tickers

### 13.4 Event Stats Recomputation
- **Services:** `backend/jobs/recompute_event_stats.py`
- **DB Tables:** `event_stats`
- **Features:**
  - Statistical aggregation by (ticker, event_type)
  - Historical returns calculation
  - Sample size tracking
  - Priors for probabilistic scoring

---

## 14. Machine Learning (Self-Learning AI)

### 14.1 Outcome Labeling
- **Services:** `backend/releaseradar/ml/pipelines/label_outcomes.py`
- **DB Tables:** `event_outcomes`, `price_history`
- **Features:**
  - Realized abnormal returns calculation (vs SPY)
  - Multi-horizon labeling (T+1, T+5, T+20)
  - Data quality flags
  - Automatic price fetching

### 14.2 Feature Engineering
- **Services:** `backend/releaseradar/ml/features.py`, `backend/releaseradar/ml/pipelines/extract_features.py`
- **DB Tables:** `event_outcomes`, `event_stats`, `price_history`
- **Features:**
  - 50+ features extracted:
    - Deterministic score components
    - Market context (beta, ATR, SPY returns)
    - Timing features (day of week, market hours)
    - Historical event frequency
    - Sector/market cap dummies
  - Feature validation
  - Data availability tracking

### 14.3 Model Training
- **Services:** `backend/releaseradar/ml/training.py`
- **DB Tables:** `ml_models`
- **Features:**
  - XGBoost regression models
  - Separate models per horizon (1d, 5d, 20d)
  - Train/test splitting
  - Hyperparameter tuning
  - Feature importance analysis
  - Model serialization (joblib)

### 14.4 Model Registry
- **Services:** `backend/releaseradar/ml/training.py` - `MLModelRegistry`
- **DB Tables:** `ml_models`
- **Features:**
  - Versioned model storage
  - Status tracking (staging/active/archived)
  - Performance metrics (MAE, R², directional accuracy)
  - Automatic promotion logic
  - Model metadata (features, training date, sample size)

### 14.5 ML Serving
- **Services:** `backend/releaseradar/ml/serving.py` - `MLScoringService`
- **DB Tables:** `events`, `ml_models`
- **Features:**
  - Single event prediction
  - Batch prediction
  - Confidence scoring
  - Fallback to deterministic scores
  - Model version tracking per prediction
  - Capped adjustments (±20 max delta)

### 14.6 Drift Detection
- **Services:** `backend/releaseradar/ml/monitoring.py`
- **DB Tables:** `ml_models`, `event_outcomes`
- **Features:**
  - Population Stability Index (PSI) monitoring
  - Feature distribution change detection
  - Accuracy degradation alerts
  - Retraining recommendations
  - Dashboard metrics

---

## Database Tables Summary

| Table | Primary Features | Key Columns |
|-------|-----------------|-------------|
| `users` | Auth, plans, subscriptions | id, email, password_hash, plan, stripe_customer_id, is_admin |
| `companies` | Company universe | id, ticker, name, sector, industry, tracked |
| `events` | Event data, scoring | id, ticker, event_type, date, impact_score, direction, confidence, ml_adjusted_score, info_tier |
| `watchlists` | User watchlists | id, user_id, ticker |
| `portfolios` | Portfolio metadata | id, user_id, name |
| `positions` | Portfolio holdings | id, portfolio_id, ticker, quantity, cost_basis |
| `user_alerts` | Alert definitions | id, user_id, name, criteria (JSON), active |
| `alert_deliveries` | Alert notification tracking | id, alert_id, event_id, delivered_at |
| `notifications` | In-app notifications | id, user_id, message, read, created_at |
| `api_keys` | API key management | id, user_id, key_hash, quota_used, quota_limit, quota_period_start |
| `scanner_logs` | Scanner execution logs | id, source, started_at, finished_at, discoveries, error |
| `scan_jobs` | Manual scan job queue | id, scope, target, status, queued_at, started_at |
| `event_outcomes` | ML training data | id, event_id, abnormal_return_1d/5d/20d, has_price_history |
| `price_history` | Historical prices | id, ticker, date, open, high, low, close, volume |
| `event_stats` | Statistical priors | id, ticker, event_type, count, mean_return, std_return |
| `ml_models` | ML model registry | id, horizon, version, status, mae, r_squared, directional_accuracy |
| `user_scoring_preferences` | Custom scoring weights | id, user_id, weights (JSON) |

---

## Technology Stack

### Backend
- **Framework:** FastAPI (Python 3.11)
- **Database:** PostgreSQL (Neon-backed)
- **ORM:** SQLAlchemy 2.0
- **Migrations:** Alembic
- **ML:** XGBoost, scikit-learn, pandas, numpy
- **Scheduling:** APScheduler
- **Rate Limiting:** SlowAPI
- **Auth:** JWT (python-jose), bcrypt
- **Email:** Resend API
- **Payments:** Stripe
- **Social:** X.com API v2 (requests)
- **Market Data:** yfinance
- **Web Scraping:** trafilatura, BeautifulSoup4
- **Monitoring:** Prometheus metrics

### Frontend
- **Framework:** Next.js 14 (App Router)
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Components:** shadcn/ui, Radix UI
- **Charts:** lightweight-charts, Recharts
- **Animation:** Framer Motion
- **State:** Zustand
- **Testing:** Playwright

### Infrastructure
- **Runtime:** Node.js 20, Python 3.11
- **Package Managers:** npm, pip
- **Deployment:** Replit (dev), Replit Deployments (prod)
- **Database:** Neon PostgreSQL
- **Workflows:** 3 active (fastapi_backend, marketing_site, scan_worker)

---

## Feature Access Matrix

| Feature | Free | Pro | Enterprise |
|---------|------|-----|------------|
| Event browsing (daily limit) | 10 | Unlimited | Unlimited |
| Watchlist tickers | 3 | Unlimited | Unlimited |
| Portfolio tickers | 3 | Unlimited | Unlimited |
| Impact scoring | Base only | Base + ML | Base + ML |
| RadarQuant AI queries/day | 5 | 50 | Unlimited |
| Backtesting | ❌ | ✅ | ✅ |
| Correlation | ❌ | ✅ | ✅ |
| Peer comparison | ❌ | ✅ | ✅ |
| Calendar view | ❌ | ✅ | ✅ |
| Price charts | ❌ | ✅ | ✅ |
| Projector | ❌ | ✅ | ✅ |
| X.com sentiment | ❌ | ✅ | ✅ |
| CSV export | ❌ | ✅ | ✅ |
| Custom scoring | ❌ | ✅ | ✅ |
| API access | ❌ | ❌ | ✅ |
| Priority support | ❌ | ❌ | ✅ |

---

## API Endpoints Summary

### Public Endpoints (No Auth)
- `GET /` - Root
- `GET /healthz` - Health check
- `GET /metrics` - Prometheus metrics
- `GET /scanners/status` - Scanner status
- `GET /events/public` - Public event feed (limited)
- `GET /pricing/plans` - Pricing plans

### Auth Required
- `POST /auth/signup`, `/auth/login`, `/auth/logout`, `/auth/verify-email`
- `GET /auth/me` - Current user
- `GET /events` - Event list
- `GET /watchlist`, `POST /watchlist`, `DELETE /watchlist/{ticker}`
- `POST /portfolio/upload`, `GET /portfolio`, `DELETE /portfolio`
- `GET /portfolio/insights` - Risk exposure
- `POST /alerts`, `GET /alerts`, `PUT /alerts/{id}`, `DELETE /alerts/{id}`
- `GET /notifications` - User notifications
- `POST /ai/query` - RadarQuant AI

### Pro/Enterprise Required
- `GET /backtesting/validate` - Backtesting
- `GET /correlation/timeline` - Event correlation
- `GET /peers/similar` - Peer events
- `GET /charts/ticker/{ticker}` - Price charts
- `GET /projector/data` - Projector data
- `GET /x-feed/clusters` - X.com sentiment
- `GET /events/export`, `GET /portfolio/export` - CSV exports
- `GET /preferences`, `PUT /preferences` - Custom scoring

### Admin Only
- `POST /scanners/run` - Manual scanner trigger

### Enterprise Only
- `GET /keys` - API key management
- `POST /keys`, `DELETE /keys/{id}`

---

**End of Feature Map**
