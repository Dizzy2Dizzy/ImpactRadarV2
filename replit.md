# Impact Radar

## Overview
Impact Radar is an event-driven signal engine for traders and small funds. It automates ingestion and analysis of SEC filings, FDA announcements, and other events to provide impact scoring with directional confidence metrics. The platform aims to enhance market analysis capabilities and provide a competitive edge through verifiable events, source links, impact rationale, and metadata.

## User Preferences
Preferred communication style: Simple, everyday language
Design preference: Clean, professional interface without emojis

## System Architecture

### High-Level Architecture
Impact Radar employs a modular, layered architecture emphasizing the isolation of pure business logic from side effects, with clear separation of configuration, logging, database interaction, domain logic, services, and UI.

### Frontend Architecture
The system uses a dual-frontend approach:
1.  **Marketing Website**: A public site built with Next.js 14 (App Router, TypeScript, Tailwind CSS, Framer Motion, shadcn/ui) for product information, documentation, and authentication (including pricing and trials).
2.  **Streamlit Application Interface**: A Python-native dashboard for registered users with tab-based navigation, interactive score displays, and detailed event views.

### Backend Architecture
The backend uses PostgreSQL with SQLAlchemy 2.0 and a repository pattern. Key features include:
-   **Monetization**: 30-day rolling quotas, atomic quota enforcement, burst rate limiting (SlowAPI), API key management, and Stripe integration.
-   **Observability**: `/healthz` and `/metrics` (Prometheus) endpoints.
-   **Caching**: ETag-based HTTP caching for score endpoints.
-   **Access Control**: Plan-based access control using JWT tokens.
-   **Alerts System**: User-defined criteria, CRUD API, multi-channel notifications (in-app, email, SMS, webhook, Slack, Discord), matching, and deduplication. Webhook/Slack/Discord integrations are Team plan exclusive with URL validation and async-safe delivery.
-   **Portfolio Risk**: CSV upload, ticker validation, and an insights endpoint for event exposure calculations.
-   **Realtime Stream**: WebSocket endpoint (`GET /ws/events`) for live event delivery with JWT auth, JSON lines messages, per-user connection limits, and backpressure handling.
-   **AI Assistant**: RadarQuant AI for intelligent event analysis and market insights with plan-based quotas using OpenAI GPT-5.1. Features conversational Grok/Claude-style responses, full portfolio access in forum (@Quant mentions), and web search capability for current news/market queries via OpenAI Responses API.
-   **Information Tiers**: Events classified into "primary" and "secondary" with granular subtypes.
-   **Analytics Engine**: Backtesting engine, correlation engine, and peer engine for validating predictions, discovering patterns, and contextualization.
-   **Custom Scoring**: User scoring preferences stored in the database allow personalized impact weighting.
-   **Data Export**: CSV generation endpoints for events and portfolio analysis.
-   **Self-Learning AI System (Market Echo Engine)**: Continuous machine learning system improving event impact predictions from realized stock price movements. Features a hierarchical model architecture (XGBoost, Neural Network Ensemble), automated learning pipeline, model registry, ML scoring API, and drift detection. Incorporates enhanced features, market regime detection, horizon-specific models, multi-task neural networks, and cleaner training labels for improved accuracy. **Automated hourly ML scoring** ensures all new events receive predictions within the hour. Feature compatibility layer handles model version differences gracefully.
-   **3-Tier Accuracy Improvement System** (Dec 2025):
    -   **Tier 1 - Drift Monitoring**: DriftMonitor class for comparing ML predictions vs outcomes, CalibrationService with ECE computation, ModelPerformanceSnapshot and DriftAlert database tables for tracking rolling window metrics (7d/30d/90d), automatic drift alerts when accuracy drops >5%.
    -   **Tier 2 - Feature Store & Stacked Ensemble**: FeatureRegistry with versioned features (v1.0→v1.4: 17 base → 33+ features), TopologyFeatureExtractor for deep persistent homology integration, FeatureCache with TTL and LRU eviction, StackedImpactEnsemble combining XGBoost + LightGBM + topology-weighted meta-learner using out-of-fold predictions and Ridge regression blending.
    -   **Tier 3 - Probabilistic Forecasting**: QuantileRegressor for prediction intervals (10th-90th percentile), ConformalCalibrator for guaranteed coverage, OptionsDataService integrating yfinance for free ATM implied volatility/IV skew/put-call ratio, ProbabilisticPrediction schema with confidence bands, predict_with_intervals() method in MLScoringService.
-   **Persistent Homology Pipeline**: Topological data analysis using Takens delay embeddings and Vietoris-Rips complexes. Extracts 10 persistent homology features: Betti counts (β₀/β₁), max/mean lifetimes, total persistence, persistence entropy, Betti curve means, and topological complexity scores. POC validation shows +39.2% accuracy improvement potential.
-   **Twitter/X Social Sentiment**: Real-time social sentiment integration for market signals via Tweepy v2 client and a rule-based financial sentiment scoring engine.
-   **Data Quality & Validation System**: Comprehensive infrastructure for data validation, freshness indicators, quality dashboards, pipeline health monitoring, audit logging, data lineage tracking, and automated validation reporting.
-   **Quantitative Analytics Suite**:
    -   **Accuracy Dashboard**: Real-time model performance tracking.
    -   **Strategy Backtesting**: Customizable trading strategy builder with historical execution.
    -   **Enhanced Portfolio Risk**: Advanced analytics including VaR-95, CVaR, and hedge recommendations.
    -   **Event Pattern Detection**: Multi-event correlation engine identifying complex patterns.
    -   **Insider Trading Monitor**: SEC Form 4 parser with sentiment scoring for insider transactions.
-   **Platform Refinement Features** (Nov 2025):
    -   **Model Explainability**: SHAP-based feature contribution visualization for prediction transparency with multi-horizon support (1d/7d/30d).
    -   **Custom Alert Rules**: User-defined alert thresholds with conditions (>, <, =) for impact score, sector, ticker filters.
    -   **Sector Analysis**: Sector-level performance metrics with rotation signals (inflow/outflow) and momentum scoring.
    -   **Trade Recommendations**: Entry/exit price targets, stop-loss, take-profit, position sizing, and risk/reward ratios.
    -   **Historical Pattern Matching**: Pattern library with similar event lookup and outcome tracking. HistoricalEventMatcher service for finding similar past events with their 1d/5d/20d price outcomes.
    -   **User Preferences**: Theme toggle (dark/light/system), saved filters, notification settings.
    -   **Email Digests**: Daily/weekly digest subscriptions with configurable content sections via Resend integration.
    -   **CSV Export**: Event and portfolio data export in CSV format.
    -   **Community Forum Enhancements**: Discord-style chat for Pro/Team users with image uploads (URL-based), GIF picker with 20 curated financial memes, reply-to-message threading, @mention autocomplete with real-time notifications, and full-height responsive layout.
-   **Modeling Workspace** (Dec 2025):
    -   **Shape Explorer**: 3D Takens delay embedding visualization using Plotly for attractor geometry analysis. Tunable parameters: embedding dimension (m=2-8), time delay (τ=1-10), lookback period (20-180 days).
    -   **Topology Analyzer**: Persistence diagrams and Betti curves from ripser. Displays H₀/H₁ features, max/mean lifetimes, persistence entropy, and topological complexity metrics.
    -   **Strategy Lab**: Backtesting interface for topology-based trading strategies with configurable entry conditions (high loops/entropy), exit conditions (complexity threshold), position sizing, and stop-loss/take-profit levels. Shows backtest metrics: trades, wins, losses, win rate, total return, max drawdown, Sharpe ratio.
-   **Playbook Library** (Dec 2025):
    -   **Trading Strategy Templates**: Pre-built playbooks for event-driven trading strategies (earnings beats, FDA approvals, insider buying, M&A arbitrage, etc.). Each playbook includes setup conditions, entry/exit logic, stop-loss/take-profit templates, holding periods, and historical performance stats (win rate, avg R, sample size).
    -   **Event-to-Playbook Matching**: Automatic matching of events to relevant playbooks based on configurable rules (event type, sector, score range, direction).
    -   **PlaybooksTab**: Dashboard component displaying playbook cards with category filtering and detailed views.
    -   **CRUD API**: Full playbook management endpoints with Team/Admin plan access control.
-   **Impact Radar Insights** (Dec 2025):
    -   **Digest Generator**: Automated daily/weekly market briefing generation analyzing event outcomes, playbook performance, and notable events.
    -   **Email Distribution**: Subscription-based digest delivery via Resend integration.
    -   **Content Sections**: Headline, summary, top events, playbook matches, accuracy metrics, and chart references.
    -   **Admin Controls**: Generate, preview, send, and manage digests with subscriber management.
-   **Enhanced AI Analysis** (Dec 2025):
    -   **FilingContentService**: Fetches and parses actual SEC EDGAR and FDA filing content with caching and rate limiting.
    -   **Selective Content Reading**: Reads full content for high-value filings (8-K items 1.01, 2.01, 2.02, 7.01; FDA approvals, 13D, S-1, M&A).
    -   **AI Summaries with Source Content**: GPT-5.1-powered summaries now analyze actual filing text, extracting key sections, financial data, and specific details.
    -   **Historical Similar Events API**: GET /events/{id}/similar endpoint finds similar past events by ticker/sector/keywords with their actual 1d/5d/20d outcomes.

### System Design Choices
-   **Layered Architecture**: Clear separation of concerns.
-   **Pure Domain Layer**: Business logic free from side effects.
-   **Repository Pattern**: Abstracted data access.
-   **Type Safety**: Comprehensive type hinting.
-   **Testability**: Designed for easy unit testing.
-   **Observability**: Structured logging with PII redaction.
-   **Security**: Strong hashing, input validation, environment-based secrets.
-   **Performance Optimizations**: Optimized database indices and N+1 query patterns.

### Company and Event Model
The system supports a hierarchical company structure. Events are processed through a deterministic impact scoring system generating an Impact Score, Direction, Confidence, and Rationale.

## External Dependencies

### Core Frameworks
-   **Streamlit**: User interface and application framework.
-   **Next.js 14**: Marketing website framework.

### AI Services
-   **OpenAI GPT-5.1**: Powers RadarQuant AI assistant and event analysis summaries (using Responses API).

### Financial Data & Visualization
-   **yfinance**: Historical stock prices and company information.
-   **Recharts**: Interactive charting library.

### Machine Learning & Analytics
-   **XGBoost**: Gradient boosting framework.
-   **PyTorch**: Neural network ensemble model.
-   **scikit-learn**: Feature engineering, model evaluation, and validation.
-   **pandas/numpy**: Data manipulation and numerical computing.
-   **joblib**: Model serialization.
-   **ripser**: Vietoris-Rips persistent homology computation for topological data analysis.
-   **persim**: Persistence image and diagram utilities for TDA features.

### Social Media Integration
-   **Tweepy**: Twitter API v2 client for sentiment analysis.

### Web Scraping & Data Extraction
-   **Trafilatura**: Main content extraction.
-   **BeautifulSoup4**: HTML parsing.
-   **Requests**: HTTP client.

### Data Sources
-   **SEC EDGAR**: Public company filings.
-   **FDA.gov**: FDA announcements.
-   **Company Websites**: Direct company press releases.

### Data Storage & Scheduling
-   **PostgreSQL**: Relational database.
-   **APScheduler**: Background job scheduler.

### Authentication & Payments
-   **bcrypt**: Password hashing.
-   **jose library**: JWT-based session management.
-   **Stripe**: Payment processing and subscription management.

### API Management
-   **SlowAPI**: Burst rate limiting.