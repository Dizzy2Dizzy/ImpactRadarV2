# Impact Radar

**Professional event-driven signal engine for active equity and biotech traders and small funds.**

Track SEC filings, FDA announcements, and corporate events with deterministic impact scoring, real-time monitoring, and portfolio earnings tracking.

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
make setup

# 2. Configure environment
cp .env.example .env
# Edit .env with your DATABASE_URL and other secrets

# 3. Run the application
make run
```

The app will be available at **http://localhost:5000**

---

## 📦 Features

- **Automated Scanners**: SEC EDGAR, FDA announcements, company press releases
- **Impact Scoring**: Deterministic scoring (0-100) with direction & confidence metrics
- **Portfolio Tracking**: Earnings calendar with P/L projections via yfinance
- **Watchlists**: User-specific ticker tracking with upcoming event previews
- **Event Filtering**: Comprehensive filters (date, sector, type, impact, direction)
- **Manual Scanning**: On-demand scanner execution
- **Authentication**: Email/SMS verification with bcrypt password hashing
- **Payments**: Stripe integration (test mode) for subscription tiers

---

## 🏗️ Architecture

### Modern Modular Structure

```
impactradar/
├── config.py              # Pydantic Settings with env variables
├── logging.py             # Structured logging (loguru + structlog)
├── db/
│   ├── models.py          # SQLAlchemy 2.0 models
│   ├── session.py         # Connection pooling & transactions
│   └── repositories.py    # Repository pattern (data access)
├── domain/
│   ├── events.py          # Pydantic models & validation
│   └── scoring.py         # Pure scoring functions
├── services/
│   ├── data.py            # DataService facade (backward compatible)
│   ├── auth.py            # Authentication service
│   └── scanners/          # SEC, FDA, Press scanners
├── ui/
│   └── streamlit_app.py   # Multi-page Streamlit UI
├── utils/
│   ├── cache.py           # Memory & disk caching
│   ├── rate_limit.py      # Per-domain rate limiting
│   └── errors.py          # Custom exceptions
└── tests/
    ├── unit/              # Unit tests
    └── integration/       # Integration tests
```

### Legacy Files (Compatibility Layer)

- `app.py` - Current Streamlit app (uses new DataService underneath)
- `database.py` - Original models (use `releaseradar.db.models` for new code)
- `data_manager.py` - Original service layer (use `releaseradar.services.data.DataService`)
- `impact_scoring.py` - Original scoring (use `releaseradar.domain.scoring`)

---

## 🛠️ Development

### Setup

```bash
# Install all dependencies (runtime + dev)
make setup

# Install pre-commit hooks
pre-commit install
```

### Code Quality

```bash
# Format code
make fmt

# Lint code
make lint

# Type check
make typecheck

# Run all checks
make check
```

### Testing

```bash
# Run all tests
make test

# Run unit tests only
make test-unit

# Run integration tests only
make test-integration

# Run backward compatibility smoke test
python smoke_test.py
```

### Database

```bash
# Initialize/create schema
python -m releaseradar.db.session

# Database migrations (Alembic)
cd releaseradar
alembic revision --autogenerate -m "Description"
alembic upgrade head
cd ..

# Seed with demo data
make seed
```

### Scanners

```bash
# Run manual scan
make scanners

# Start background scheduler
make scheduler
```

### Data Verification

Impact Radar includes comprehensive data verification tools to ensure data quality and prevent false information:

```bash
# Run full verification suite (all checks)
make verify

# Run individual verification tools
make verify.sources      # Verify source URLs
make verify.integrity    # Verify event data integrity
make verify.scanners     # Verify scanner output
```

**Verification Tools:**

1. **Source URL Validation** (`verify.sources`)
   - Checks all events have valid source URLs
   - Verifies URL format and structure
   - Confirms URLs point to authoritative sources (sec.gov, fda.gov, etc.)
   - Optional reachability checks (HTTP 200)
   - Flags missing, invalid, or broken URLs

2. **Event Data Integrity** (`verify.integrity`)
   - Verifies ticker symbols exist in companies table
   - Checks date ranges are reasonable (no excessive future dates)
   - Validates impact scores (0-100 range)
   - Confirms direction values (positive/negative/neutral/uncertain)
   - Detects duplicate events
   - Flags missing required fields

3. **Scanner Output Validation** (`verify.scanners`)
   - Tests scanner functions with mock data
   - Verifies output schema matches expected format
   - Validates field types and value ranges
   - Checks deduplication logic
   - Ensures event normalization works correctly

**Example Output:**
```bash
$ make verify
Running comprehensive verification suite...
[1/3] Source URL Validation: ✅ 650 events checked, 645 valid URLs
[2/3] Event Data Integrity: ✅ 650 events checked, 0 violations
[3/3] Scanner Output: ✅ 10/10 scanners passing
✅ ALL VERIFICATIONS PASSED!
```

---

## 📝 Configuration

### Environment Variables

Copy `.env.example` to `.env` and configure:

#### Required
- `DATABASE_URL` - PostgreSQL connection string
- `SECRET_KEY` - Session secret key
- `SESSION_SECRET` - Cookie encryption secret

#### Feature Flags
- `ENABLE_STRIPE=false` - Enable Stripe payments (default: false)
- `ENABLE_SMS_VERIFICATION=false` - Enable SMS verification via Twilio
- `ENABLE_EMAIL_VERIFICATION=true` - Enable email verification

#### External Services
- **SEC EDGAR**: `SEC_EDGAR_USER_AGENT`, rate limits
- **FDA**: `FDA_BASE_URL`, rate limits
- **Email (SMTP)**: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- **SMS (Twilio)**: `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE_NUMBER`
- **Stripe**: `STRIPE_API_KEY`, `STRIPE_WEBHOOK_SECRET`, price IDs

See `.env.example` for full configuration options.

---

## 📊 Database Schema

### Core Tables

**companies** - Tracked companies with sector/industry classification
```sql
id, ticker (unique), name, sector, industry, parent_id, tracked, created_at, updated_at
```

**events** - Company events with impact scoring
```sql
id, ticker, company_name, event_type, title, description, date, source, source_url,
impact_score (0-100), direction (positive/negative/neutral/uncertain), confidence (0-1), 
rationale, sector, created_at
```

**users** - User accounts with bcrypt authentication
```sql
id, email (unique), phone (unique), password_hash, is_verified, is_admin, created_at, last_login
```

**watchlist** - User-specific ticker watchlists
```sql
id, user_id, ticker, notes, created_at
```

**scanner_logs** - Scanner execution history
```sql
id, scanner, message, level (info/warning/error), timestamp
```

---

## 🎯 Event Types & Scoring

### FDA Events (High Impact: 70-95)
- `fda_approval` (85) - Drug/device approval ✅
- `fda_rejection` (80) - Application rejection ❌
- `fda_adcom` (75) - Advisory committee meeting
- `fda_crl` (75) - Complete Response Letter
- `fda_safety_alert` (70) - Safety warnings

### SEC Filings (Variable Impact: 50-75)
- `sec_8k` (65) - Current report (material events)
- `sec_10k` (55) - Annual report
- `sec_10q` (50) - Quarterly report
- `sec_13d` (75) - Activist/acquisition filing

### Earnings & Guidance (Medium-High: 60-80)
- `earnings` (70) - Quarterly earnings
- `guidance_raise` (75) - Guidance increase
- `guidance_lower` (75) - Guidance decrease

### Product Events (Medium: 50-80)
- `product_launch` (65) - Product release
- `product_recall` (80) - Safety recall
- `product_delay` (70) - Launch delay

---

## 🔒 Security

- **Password Hashing**: bcrypt with per-user salt
- **Email/SMS Verification**: 6-digit codes, 15-min expiry, 5-attempt lockout
- **Session Management**: Secure cookies with 24-hour expiry
- **Secrets**: Environment variables only, never hard-coded
- **PII Logging**: Automatic redaction in structured logs
- **Input Validation**: Pydantic models with length limits

See [SECURITY.md](SECURITY.md) for complete security documentation.

---

## 🗺️ Roadmap

### Phase 1: Foundation ✅ (Completed)
- [x] Modular architecture (config, logging, repositories, domain)
- [x] Repository pattern for data access
- [x] Pydantic validation & error handling
- [x] Backward-compatible DataService facade
- [x] Caching & rate limiting utilities

### Phase 2: Services (In Progress)
- [ ] Auth service with email/SMS verification
- [ ] Scanner refactoring (SEC, FDA, Press)
- [ ] HTTP client with retry/backoff
- [ ] Scheduler with APScheduler

### Phase 3: UI Modernization
- [ ] Multi-page Streamlit app
- [ ] Reusable UI components
- [ ] Enhanced filtering & visualization
- [ ] Real-time updates

### Phase 4: Testing & CI/CD
- [ ] Unit tests (domain, services)
- [ ] Integration tests (repositories, database)
- [ ] GitHub Actions CI pipeline
- [ ] Coverage ≥80%

### Phase 5: Future Enhancements
- [ ] FastAPI REST API layer
- [ ] React frontend (replace Streamlit)
- [ ] Broker integrations (TD Ameritrade, Interactive Brokers)
- [ ] Event backtesting module
- [ ] Webhook notifications

See [ROADMAP.md](ROADMAP.md) for detailed migration plan.

---

## 📚 API Reference

### DataService

```python
from releaseradar.services.data import DataService

dm = DataService()

# Get events with filtering
events = dm.get_events(
    ticker="AAPL",
    date_from=datetime.now(),
    min_impact=70,
    direction="positive"
)

# Create event with auto-scoring
event = dm.create_event(
    ticker="AAPL",
    company_name="Apple Inc.",
    event_type="earnings",
    title="Q4 2024 Earnings Release",
    date=datetime(2024, 11, 1),
    source="SEC",
    auto_score=True  # Automatically scores event
)

# Watchlist management
dm.add_to_watchlist("AAPL", user_id=1)
watchlist = dm.get_watchlist(user_id=1)
```

### Event Scoring

```python
from releaseradar.domain.scoring import score_event

result = score_event(
    event_type="fda_approval",
    title="FDA Approves New Cancer Drug",
    sector="Pharma"
)

print(f"Impact: {result.impact_score}/100")  # 102 (85 * 1.2 sector bonus)
print(f"Direction: {result.direction}")       # positive
print(f"Confidence: {result.confidence}")     # 0.85
print(f"Rationale: {result.rationale}")
```

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and checks (`make check`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

---

## 📄 License

Proprietary - All Rights Reserved

---

## 🆘 Support

For issues, questions, or feature requests:
- Check existing documentation (README, SECURITY, ROADMAP)
- Review [database schema](#database-schema)
- Contact: support@impactradar.co

---

## 🏆 Credits

Built with:
- [Streamlit](https://streamlit.io/) - Interactive web app framework
- [SQLAlchemy](https://www.sqlalchemy.org/) - Python SQL toolkit
- [Pydantic](https://docs.pydantic.dev/) - Data validation
- [yfinance](https://github.com/ranaroussi/yfinance) - Yahoo Finance data
- [Trafilatura](https://trafilatura.readthedocs.io/) - Web scraping
- [Beautiful Soup](https://www.crummy.com/software/BeautifulSoup/) - HTML parsing

---

**Disclaimer**: Impact Radar provides information only. Not investment advice. No performance guarantees. Always verify with original filings. See [legal disclaimers](SECURITY.md#disclaimers).
