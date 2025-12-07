# Impact Radar Roadmap

This document outlines the phased migration plan for completing the enterprise refactoring and future enhancements.

---

## ✅ Phase 1: Foundation (COMPLETED)

**Status**: 100% Complete  
**Timeline**: November 2024

### Deliverables
- [x] Modular architecture (`releaseradar/` package)
- [x] Configuration management (Pydantic Settings)
- [x] Structured logging (loguru + structlog)
- [x] Database layer (SQLAlchemy 2.0 models, session management, repositories)
- [x] Domain layer (Pydantic validation, pure scoring functions)
- [x] Utilities (caching, rate limiting, custom exceptions)
- [x] DataService facade (backward-compatible with existing app.py)
- [x] Alembic migrations (initial migration: 19b2e0c29f39)
- [x] Backward compatibility validation (smoke_test.py - 10/10 tests passed)
- [x] Pre-commit hooks (.pre-commit-config.yaml)
- [x] Comprehensive documentation (README, SECURITY, ROADMAP)

### Architecture
```
releaseradar/
├── config.py              ✅ Pydantic Settings
├── logging.py             ✅ structlog + loguru
├── db/
│   ├── models.py          ✅ SQLAlchemy 2.0
│   ├── session.py         ✅ Connection pooling
│   ├── repositories.py    ✅ Repository pattern
│   └── migrations/        ✅ Alembic migrations
├── domain/
│   ├── events.py          ✅ Pydantic models
│   └── scoring.py         ✅ Pure functions
├── services/
│   └── data.py            ✅ Facade for compatibility
└── utils/
    ├── cache.py           ✅ Memory + disk cache
    ├── rate_limit.py      ✅ Token bucket
    └── errors.py          ✅ Custom exceptions
```

### Validation
- ✅ **Smoke Test**: 10/10 tests passed
  - DataService interface compatibility with DataManager
  - Database operations (companies, events, watchlist, scanner logs)
  - Model and domain module imports
  - Proven drop-in replacement for legacy code

---

## 🚧 Phase 2: Services Layer

**Status**: 0% Complete  
**Timeline**: Q1 2025  
**Estimated Effort**: 2-3 weeks

### 2.1 Authentication Service
- [ ] `releaseradar/services/auth.py`
  - Migrate `auth_service.py` to use UserRepository
  - Implement bcrypt password hashing
  - Email verification workflow
  - SMS verification workflow (optional)
  - Session management
  - Password reset flow

### 2.2 Communication Services
- [ ] `releaseradar/services/email.py`
  - Migrate `email_service.py`
  - SMTP client with TLS
  - Template system for verification emails
  - Rate limiting for email sends

- [ ] `releaseradar/services/sms.py`
  - Migrate `sms_service.py`
  - Twilio API integration
  - Template system for SMS codes
  - Cost tracking per message

### 2.3 Payment Service
- [ ] `releaseradar/services/payments.py`
  - Migrate `payment_service.py`
  - Stripe integration (test mode)
  - Webhook handling
  - Subscription management
  - Invoice generation

### 2.4 Scraping Infrastructure
- [ ] `releaseradar/services/scraping/fetch.py`
  - httpx client with retry/backoff (tenacity)
  - User-Agent rotation
  - robots.txt compliance
  - HTTP caching integration

- [ ] `releaseradar/services/scraping/parse.py`
  - Trafilatura for content extraction
  - BeautifulSoup for structured data
  - Error handling for malformed HTML
  - Unit tests with real-world examples

### 2.5 Scanner Services
- [ ] `releaseradar/services/scanners/sec.py`
  - Refactor SEC EDGAR scanner from `scanner_service.py`
  - Use fetch/parse infrastructure
  - Rate limiting integration
  - Form type mapping (8-K, 10-K, 10-Q)
  - Duplicate detection via `EventInput.dedupe_key()`

- [ ] `releaseradar/services/scanners/fda.py`
  - Refactor FDA scanner
  - Parse approval/rejection/CRL announcements
  - Sector validation (pharma/biotech only)

- [ ] `releaseradar/services/scanners/press.py`
  - Refactor company press release scanner
  - RSS feed parsing
  - Curated URL lists per company

### 2.6 Impact Service
- [ ] `releaseradar/services/impact.py`
  - Wrapper around `domain.scoring.score_event`
  - Batch scoring for multiple events
  - Historical scoring comparisons

---

## 🎨 Phase 3: UI Modernization

**Status**: 0% Complete  
**Timeline**: Q1-Q2 2025  
**Estimated Effort**: 3-4 weeks

### 3.1 Reusable Components
- [ ] `releaseradar/ui/components.py`
  - Score pills (color-coded by impact)
  - Direction indicators (emoji + color)
  - Event cards
  - Filter panels
  - Toast notifications
  - Loading spinners
  - Empty states

### 3.2 Multi-Page Streamlit App
- [ ] `releaseradar/ui/streamlit_app.py`
  - Dashboard page
    - Event table with virtualization
    - Multi-filter interface
    - Quick actions (bookmark, share)
    - Real-time updates
  
  - Companies page
    - Company cards with event counts
    - Sector filtering
    - Watchlist star toggle
    - Event timeline per company
  
  - Earnings page
    - Portfolio tracker
    - Ticker input with autocomplete
    - Position size calculator
    - P/L projections
    - Earnings calendar
  
  - Scanners page
    - Health dashboard
    - Last run timestamps
    - Success/error metrics
    - Manual scan button
    - Log viewer with filtering
  
  - Pricing page
    - Free / Pro / Team comparison
    - Feature matrix
    - Stripe checkout integration
    - Billing portal link
  
  - Account page
    - Email/SMS verification status
    - Password change
    - 2FA setup (optional)
    - API key management (future)

### 3.3 Compatibility & Migration
- [ ] Update `app.py`
  - Add deprecation warning
  - Redirect to new UI with query params
  - Maintain session state during migration

- [ ] Gradual migration strategy
  - Phase 3.3.1: Dashboard + Companies (new UI)
  - Phase 3.3.2: Earnings + Scanners (new UI)
  - Phase 3.3.3: Pricing + Account (new UI)
  - Phase 3.3.4: Deprecate old `app.py`

---

## 📋 Phase 4: Scheduler & Background Jobs

**Status**: 0% Complete  
**Timeline**: Q2 2025  
**Estimated Effort**: 1 week

### 4.1 Scheduler Service
- [ ] `releaseradar/tasks/scheduler.py`
  - APScheduler configuration
  - Job definitions:
    - Priority scanner (every 5 min for watchlist)
    - General scanner (every 30 min for all companies)
    - Housekeeping (daily cleanup of expired codes)
    - Event recalculation (on scoring logic changes)
  - Error handling & retry logic
  - Job status monitoring

### 4.2 Runner Scripts
- [ ] `releaseradar/tasks/run_scanners.py`
  - CLI for manual scanner execution
  - Argument parsing (--scanner, --ticker)

- [ ] `releaseradar/tasks/run_scheduler.py`
  - Background process for continuous scanning

---

## 🧪 Phase 5: Testing & CI/CD

**Status**: 0% Complete  
**Timeline**: Q2 2025  
**Estimated Effort**: 2 weeks

### 5.1 Unit Tests
- [ ] `releaseradar/tests/unit/test_scoring.py`
  - FDA approval/rejection scoring
  - Earnings beat/miss scenarios
  - Product launch/delay events
  - Sector multipliers (pharma FDA +20%)
  - Market cap multipliers
  - Direction determination

- [ ] `releaseradar/tests/unit/test_events.py`
  - EventInput validation (valid/invalid types)
  - dedupe_key() generation
  - merge_events() logic

- [ ] `releaseradar/tests/unit/test_cache.py`
  - Memory cache TTL
  - Disk cache persistence
  - Cache decorator

- [ ] `releaseradar/tests/unit/test_rate_limit.py`
  - Token bucket algorithm
  - Per-domain limits
  - wait_if_needed() behavior

### 5.2 Integration Tests
- [ ] `releaseradar/tests/integration/test_repositories.py`
  - CRUD operations for all repositories
  - Transaction handling
  - Constraint validation

- [ ] `releaseradar/tests/integration/test_scanners.py`
  - Mock SEC/FDA/Press APIs with VCR.py
  - End-to-end scanner flow
  - Duplicate detection

### 5.3 End-to-End Tests
- [ ] Playwright tests (via Replit's `run_test` tool)
  - Login/logout flow
  - Event filtering
  - Watchlist add/remove
  - Manual scan execution
  - Earnings P/L calculation

### 5.4 CI/CD Pipeline
- [ ] `.github/workflows/ci.yml`
  - Lint (ruff)
  - Format check (black, isort)
  - Type check (mypy)
  - Unit tests (pytest)
  - Coverage report (≥80%)

- [ ] `.github/workflows/deploy.yml`
  - Auto-deploy on main branch merge
  - Database migrations
  - Health check after deployment

---

## 🔧 Phase 6: Database Migrations

**Status**: 0% Complete  
**Timeline**: Q2 2025  
**Estimated Effort**: 3 days

### 6.1 Alembic Setup
- [ ] `releaseradar/db/alembic.ini`
- [ ] `releaseradar/db/migrations/env.py`
- [ ] Initial migration (auto-generated from existing schema)

### 6.2 Migration Scripts
- [ ] Data backfill for new columns (if needed)
- [ ] Index creation for performance
- [ ] Constraint additions

### 6.3 Makefile Targets
- [ ] `make migrate` - Create new migration
- [ ] `make upgrade` - Apply pending migrations
- [ ] `make downgrade` - Rollback last migration

---

## 🚀 Phase 7: Future Enhancements

**Status**: Planned  
**Timeline**: 2025-2026

### 7.1 FastAPI REST API (Q3 2025)
- RESTful API alongside Streamlit UI
- JWT authentication
- Rate limiting per API key
- OpenAPI/Swagger documentation
- Webhook support for real-time notifications

### 7.2 React Frontend (Q4 2025)
- Replace Streamlit with React
- TanStack Query for data fetching
- shadcn/ui component library
- Real-time updates via WebSocket
- Mobile-responsive design

### 7.3 Broker Integrations (2026)
- TD Ameritrade API
- Interactive Brokers TWS
- Alpaca Markets
- Automatic order placement (with confirmations)

### 7.4 Backtesting Module (2026)
- Historical event impact analysis
- P/L simulation
- Strategy optimization
- Risk metrics (Sharpe, max drawdown)

### 7.5 Advanced Features
- Portfolio risk analysis
- Correlation analysis between events
- ML-based impact prediction (enhance scoring)
- Custom alerts (email, SMS, Slack, Discord)
- Excel/CSV export with advanced filtering

---

## 📊 Migration Strategy

### Principles
1. **Incremental**: One phase at a time, no big bang
2. **Backward Compatible**: Old code works during migration
3. **Tested**: Every phase has passing tests before next phase
4. **Documented**: Update docs as features migrate

### Current State
- ✅ **Foundation complete**: New architecture is ready
- ⏸️ **Compatibility layer**: DataService facade allows old app.py to use new infra
- 🎯 **Next step**: Migrate services (auth, email, SMS, scanners)

### Rollback Plan
- Keep `app_old.py`, `data_manager.py`, `impact_scoring.py` until Phase 3 complete
- Git tags for each phase completion
- Database backups before Alembic migrations

---

## 🎯 Success Metrics

### Phase 2-3 (Services + UI)
- [ ] All existing features work in new UI
- [ ] No regressions in event detection
- [ ] Response times <300ms for cached data
- [ ] Zero data loss during migration

### Phase 4-5 (Scheduler + Tests)
- [ ] Scanners run without blocking UI
- [ ] Unit test coverage ≥80%
- [ ] CI pipeline passes on all PRs

### Phase 6 (Migrations)
- [ ] Alembic migrations are idempotent
- [ ] Zero-downtime deployments

### Phase 7 (Future)
- [ ] API rate limits enforced
- [ ] React UI launches <2s
- [ ] Broker integrations tested in paper trading

---

## 🤝 Contributing

See [README.md](README.md#contributing) for contribution guidelines.

To propose new roadmap items, open a GitHub issue with:
- Feature description
- User value
- Technical approach
- Estimated effort

---

**Last Updated**: November 2024
