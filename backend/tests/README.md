# ReleaseRadar Test Suite

This directory contains the automated test suite for ReleaseRadar Wave G features.

## Test Structure

### Core Test Files
- **`conftest.py`**: Shared pytest fixtures (database session, test client, users)
- **`test_scanner_deduplication.py`**: Unit tests for scanner event normalization and deduplication
- **`test_scoring_market_data.py`**: Unit tests for scoring with market data variations
- **`test_portfolio_exposure.py`**: Integration tests for portfolio calculations
- **`test_admin_endpoints.py`**: Integration tests for admin protection and rate limiting
- **`test_e2e_smoke.py`**: End-to-end smoke test for event ingestion → API flow

### Comprehensive Feature Tests (New)
- **`test_auth.py`**: Authentication tests (15 tests) - registration, login, JWT, email verification
- **`test_event_ingestion.py`**: Event scanner tests (18 tests) - SEC 8-K, FDA, Earnings scanners
- **`test_watchlist.py`**: Watchlist CRUD tests (11 tests) - add/remove tickers, validation
- **`test_alerts.py`**: Alert system tests (14 tests) - creation, matching, email dispatch
- **`test_radarquant.py`**: AI query tests (10 tests) - RadarQuant, context building, quotas
- **`test_ml.py`**: ML pipeline tests (11 tests) - feature extraction, model serving, predictions

### Security & Access Control
- **`test_access_control.py`**: Authorization and permission tests
- **`test_scores_authz.py`**: Score endpoint authorization tests
- **`test_webhook_security.py`**: Webhook signature verification tests
- **`test_rate_limiting.py`**: API rate limiting tests
- **`test_secrets.py`**: Secret key handling tests
- **`test_xss.py`**: XSS prevention tests

### Performance & Caching
- **`test_scores_caching.py`**: Score caching mechanism tests
- **`test_metrics.py`**: Metrics and monitoring tests
- **`test_info_tier.py`**: Tier-based information access tests

### Integration Tests
- **`integration/test_event_stats.py`**: Event statistics aggregation tests

## Running Tests

### Run All Tests
```bash
cd backend
pytest tests/
```

### Run Specific Test Files
```bash
# Authentication tests (15 tests)
pytest tests/test_auth.py -v

# Event ingestion tests (18 tests)
pytest tests/test_event_ingestion.py -v

# Watchlist tests (11 tests)
pytest tests/test_watchlist.py -v

# Alert tests (14 tests)
pytest tests/test_alerts.py -v

# AI/RadarQuant tests (10 tests)
pytest tests/test_radarquant.py -v

# ML pipeline tests (11 tests)
pytest tests/test_ml.py -v

# Scanner deduplication tests (4 tests)
pytest tests/test_scanner_deduplication.py -v

# Scoring market data tests (5 tests)
pytest tests/test_scoring_market_data.py -v

# Portfolio exposure tests (4 tests)
pytest tests/test_portfolio_exposure.py -v

# Admin protection tests (4 tests)
pytest tests/test_admin_endpoints.py -v

# E2E smoke test (1 test)
pytest tests/test_e2e_smoke.py -v
```

### Run Tests with Coverage
```bash
pytest tests/ --cov=. --cov-report=html
```

## Test Coverage Summary

**Total Test Count**: Comprehensive test suite across all categories
- Authentication: 15 tests
- Event Ingestion: 18 tests
- Watchlist: 11 tests
- Alerts: 14 tests
- AI/RadarQuant: 10 tests
- ML Pipeline: 11 tests
- Core Features: 18 tests
- Security: 15+ tests

**Important**: All tests use proper mocks for external dependencies (OpenAI API, model loading, SEC/FDA APIs) to ensure fast, reliable test execution without external API calls.

### Authentication Tests ✅ (test_auth.py)
**15 tests covering**:
- User registration and duplicate email handling
- Login with valid/invalid credentials
- Password hashing and verification (bcrypt)
- JWT token creation and validation
- Expired token rejection
- Email verification code generation and validation
- Session management
- Authentication middleware
- Rate limiting on auth endpoints

### Event Ingestion Tests ✅ (test_event_ingestion.py)
**18 tests covering**:
- SEC 8-K scanner integration
- FDA press release scanner
- Earnings calendar scanner
- Event normalization and deduplication
- Market data enrichment
- Impact score calculation
- Scanner error handling
- Multiple scanner orchestration

### Watchlist Tests ✅ (test_watchlist.py)
**11 tests covering**:
- Add/remove tickers from watchlist
- Ticker validation (symbol format, exchange checks)
- User isolation (users can't see others' watchlists)
- Duplicate ticker prevention
- Notes and metadata storage
- Upcoming events for watchlist tickers
- Rate limiting on watchlist operations

### Alert Tests ✅ (test_alerts.py)
**14 tests covering**:
- Alert rule creation (event type, ticker, score threshold)
- Alert matching engine
- Email dispatch via Resend
- Alert deduplication
- User-specific alert isolation
- Alert history tracking
- Email template rendering
- Rate limiting on alert creation

### AI/RadarQuant Tests ✅ (test_radarquant.py)
**10 tests covering**:
- Context building from portfolio data
- Context building from watchlist
- Context building from upcoming events
- Query handling with OpenAI
- Response formatting and disclaimers
- Domain restriction (Release Radar only)
- Quota enforcement (Pro/Team only)
- Free users prevented from access
- API endpoint authentication

### ML Pipeline Tests ✅ (test_ml.py)
**11 tests covering**:
- Feature extraction from events
- Timing features (hour, day of week, after hours)
- Market context features (SPY returns, volatility)
- Historical event statistics
- Batch feature extraction
- Model registry and versioning
- Model serving and caching
- Prediction generation
- Prediction blending with base scores
- Feature validation and defaults

### Scanner Deduplication Tests ✅
- `test_generate_raw_id_consistency()`: Same event data generates identical raw_id
- `test_generate_raw_id_uniqueness()`: Different events generate unique raw_ids
- `test_normalize_event()`: Event normalization to DataManager schema
- `test_sec_scanner_deduplication()`: SEC scanner doesn't insert duplicate events

### Scoring Market Data Tests ✅
- `test_scoring_with_high_beta()`: High beta (>1.5) increases score by 10-20%
- `test_scoring_with_high_atr()`: High ATR percentile (>80) increases score
- `test_scoring_with_down_market()`: Adverse market (SPY down) affects score
- `test_scoring_combined_factors()`: Combined factors provide 10-20% impact
- `test_scoring_graceful_degradation()`: Scoring works when market data unavailable

### Portfolio Exposure Tests ⚠️
- `test_portfolio_upload_csv()`: CSV upload creates holdings correctly
- `test_duplicate_ticker_aggregation()`: Duplicate tickers aggregate correctly
- `test_portfolio_exposure_calculation()`: Exposure calculations
- `test_free_plan_ticker_limit()`: Free users limited to 3 tickers

**Note**: Portfolio tests require database migrations to be run first.

### Admin Protection Tests ⚠️
- `test_manual_scan_requires_admin()`: Non-admin users get 403 on /scanners/run
- `test_rescan_company_requires_admin()`: Non-admin users get 403 on /scanners/rescan/company
- `test_admin_audit_logging()`: Admin actions logged
- `test_rate_limiting()`: Rate limits enforced

**Note**: Admin tests require database migrations to be run first.

### E2E Smoke Test ⚠️
- `test_event_ingestion_to_api()`: Full flow from event creation to API retrieval

**Note**: E2E test may timeout on slow systems.

## Test Fixtures

### Database Session (`db_session`)
Creates a fresh database session for each test and cleans up test data afterward.
- Cleans tables with `TEST_*` prefixes
- Automatically commits and rolls back as needed

### Test Client (`test_client`)
FastAPI TestClient for making HTTP requests to the API.

### Admin User (`admin_user`)
Creates an admin user with:
- Email: `test_admin@example.com`
- Plan: `team`
- Admin privileges: `True`
- Returns: `{user_id, email, token, is_admin, plan}`

### Regular User (`regular_user`)
Creates a non-admin user with:
- Email: `test_regular@example.com`
- Plan: `free`
- Admin privileges: `False`
- Returns: `{user_id, email, token, is_admin, plan}`

### Pro User (`pro_user`)
Creates a Pro plan user with:
- Email: `test_pro@example.com`
- Plan: `pro`
- Admin privileges: `False`
- Returns: `{user_id, email, token, is_admin, plan}`

### Test Company (`test_company`)
Creates a test company:
- Ticker: `TEST_AAPL`
- Name: `Test Apple Inc.`
- Sector: `Technology`

### Test Event (`test_event`)
Creates a test product launch event for the test company.

## Known Issues

1. **Database Schema Mismatch**: Some tests require database migrations to be run before they will pass. Run migrations with:
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Timeout on E2E Tests**: The E2E smoke test may timeout on slow systems. Increase timeout if needed.

3. **LSP Warnings**: SQLAlchemy ORM type warnings are false positives and can be ignored.

## Best Practices

1. **Clean Test Data**: All test data uses `TEST_*` prefixes for easy cleanup
2. **Isolation**: Each test runs in isolation with its own database session
3. **Fast Execution**: Tests should complete in <10 seconds total
4. **No External Dependencies**: Mock external APIs (yfinance, SEC RSS) to avoid rate limits

## Mocking Strategy

The test suite uses comprehensive mocking to prevent external dependencies:

### RadarQuant/OpenAI Mocks
- **File**: `test_radarquant.py`
- **Mocks**: `@patch('ai.radarquant.OpenAI')` and `@patch.dict(os.environ, {'OPENAI_API_KEY': 'test_key_12345'})`
- **Purpose**: Prevents hitting OpenAI API during tests
- **Implementation**: Mock OpenAI client initialization and completion responses

### ML Model Mocks
- **File**: `test_ml.py`
- **Mocks**: `@patch('releaseradar.ml.serving.joblib.load')`
- **Purpose**: Prevents loading models from disk and missing model file errors
- **Implementation**: Mock joblib.load to return MagicMock model with predict methods

### Scanner Mocks
- **File**: `test_event_ingestion.py`
- **Mocks**: 
  - `@patch('releaseradar.services.sec.get_recent_filings')` for SEC 8-K scanner
  - `@patch('scanners.impl.fda.fetch_fda_rss_feed')` for FDA scanner
- **Purpose**: Prevents hitting live SEC EDGAR and FDA.gov APIs
- **Implementation**: Return mock filing/announcement data structures

### Best Practices for Adding New Tests
1. **Always mock external APIs** - Use `@patch()` decorators for any external service calls
2. **Mock at the integration boundary** - Mock the service layer, not deep internals
3. **Return realistic test data** - Mock responses should match real API response structures
4. **Use environment variable mocks** - Use `@patch.dict(os.environ, {...})` for API keys
5. **Avoid disk I/O** - Mock file loading operations like `joblib.load()` or `pickle.load()`

## Contributing

When adding new tests:
1. Use existing fixtures from `conftest.py`
2. Prefix test data with `TEST_` for easy cleanup
3. Keep tests fast (<1 second per test)
4. Mock external API calls
5. Clean up test data in teardown
