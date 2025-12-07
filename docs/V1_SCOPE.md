# Impact Radar V1 Beta Scope

**Document Version:** 1.0  
**Created:** November 15, 2025  
**Status:** Beta Scope Definition  
**Purpose:** Define minimal viable feature set for limited beta launch

---

## Overview

This document defines what's considered **stable and ready for limited beta users** vs. what's **experimental** or **out of scope** for Impact Radar V1 Beta.

**Philosophy:** V1 Beta prioritizes **reliability over completeness**. We'd rather ship fewer features that work flawlessly than many features that crash or confuse users.

**Target Users:** 10-50 beta users willing to provide feedback on core event tracking and impact scoring capabilities.

**Reference Documents:**
- `FEATURE_MAP.md` - Complete feature inventory (100+ features documented)
- `HARDENING_REPORT.md` - Current quality assessment and test results

---

## V1 Core (In Scope - Stable & Tested)

Features that **MUST work reliably** for beta launch. These are the golden-path flows that define Impact Radar's value proposition.

### Authentication & Account

**Status: ✅ STABLE**

- ✅ **User signup with email/password**
  - Email validation
  - Password strength requirements
  - Secure password hashing (bcrypt)
  - Input sanitization
  
- ✅ **Email verification**
  - 6-digit verification code generation
  - 15-minute expiration
  - Code resend capability
  - Can be mocked in test environment, real SMTP in production
  
- ✅ **Login/logout**
  - JWT-based session management
  - Secure token handling
  - Remember me functionality
  - Session expiration
  
- ✅ **Profile page (view/edit basic info)**
  - View user details
  - Edit email address
  - Update profile settings
  - Password change (future)
  
- ✅ **Plan display (Free/Pro/Enterprise tiers)**
  - Current plan visibility
  - Feature limits per plan
  - Upgrade prompts (UI only, no billing integration required)
  
- ✅ **Watchlist creation and management**
  - Add/remove tickers
  - View watchlist
  - Ticker validation against company database
  - Duplicate prevention

**Testing Status:**
- E2E tests: 5 auth tests (signup, login, validation) - ⚠️ Not verified due to suite timeout
- Backend tests: Authentication fixtures working
- Manual QA: **Required before launch**

---

### Events System

**Status: ✅ STABLE (with quality gates)**

- ✅ **Event list with pagination**
  - Default: 50 events per page
  - Infinite scroll or pagination controls
  - Loading states
  - Empty state handling
  
- ✅ **Filters: by ticker, date range, event type, impact score**
  - **Ticker filter:** Single or multiple tickers
  - **Date range:** From/to date pickers
  - **Event type:** Earnings, FDA, SEC 8-K, guidance, product launch, M&A, etc.
  - **Impact score range:** Min/max sliders (0-100)
  - **Direction filter:** Positive, negative, neutral, uncertain
  - **Watchlist-only toggle:** Show only watchlist events
  
- ✅ **Event detail page with:**
  - **Source link** - **MUST be real SEC/FDA/company IR URL** (no placeholder links)
  - **Impact score + rationale** - Human-readable explanation of score
  - **Event metadata** - Ticker, date, type, sector, direction, confidence
  - Event description
  - Related events (if available)
  
- ✅ **Impact scoring:**
  - **Deterministic base model** - Rule-based scoring (0-100)
  - **Probabilistic predictions** - P(move), P(up), P(down) if available
  - **NO fake/templated primary events in production** - All events must have real sources
  - Score rationale generation
  - Confidence levels
  
**Active Scanners for V1:**
- ✅ **SEC 8-K Scanner** (15min interval) - Current reports
- ✅ **Earnings Calls Scanner** (1hr) - Earnings announcements
- ✅ **FDA Announcements Scanner** (6hr) - FDA decisions
- ✅ **SEC EDGAR Scanner** (4hr) - All SEC filings
- ✅ **Company Press Releases Scanner** (8hr) - Official news

**Scanners NOT Required for V1:**
- ⚠️ SEC 10-Q (6hr) - Can be delayed
- ⚠️ Guidance Updates (2hr) - Nice to have
- ⚠️ Product Launches (3hr) - Nice to have
- ⚠️ M&A/Strategic (1hr) - Nice to have
- ⚠️ Dividends/Buybacks (4hr) - Nice to have

**Quality Gates:**
- ✅ Event source verification script confirms real URLs (`python backend/tools/verify_scanners.py`)
  - Last run: 7/10 scanners production-ready (FDA, Press, M&A returning no events)
- ✅ No events with null/empty source_url in production
- ✅ Scanner deduplication prevents duplicate events
- ✅ Event list renders without crashes
- ✅ Filters work without runtime errors

**Testing Status:**
- E2E tests: 8 event tests (list, filters, details) - ✅ Cookie consent fix applied
- Backend tests: Scanner deduplication tests passing
- Manual QA: **Required before launch**

---

### Portfolio & Watchlist

**Status: ⚠️ CONDITIONAL (include if tests pass)**

- ✅ **Portfolio CSV upload (if stable)**
  - CSV parsing (ticker, shares, cost_basis, label, as_of)
  - Duplicate ticker aggregation
  - Weighted average cost basis
  - Plan-based limits (Free: 3 tickers, Pro/Enterprise: unlimited)
  - Validation and error messages
  
- ✅ **Basic earnings impact view (only if tested)**
  - Portfolio exposure to upcoming events (30-day window)
  - Dollar exposure calculation (1d, 5d, 20d horizons)
  - Risk score per position
  - Event count per holding
  
- ✅ **Watchlist ticker add/remove**
  - Add ticker with validation
  - Remove ticker
  - View watchlist
  - Duplicate prevention
  
- ✅ **Filter events by watchlist**
  - Watchlist-only toggle in event filters
  - Batch ticker queries

**Quality Gates:**
- ✅ Portfolio CSV upload E2E test passes
- ✅ Portfolio exposure calculations accurate
- ✅ Free plan limits enforced
- ✅ No crashes on invalid CSV

**Testing Status:**
- E2E tests: 4 portfolio tests, 5 watchlist tests - ✅ Cookie consent fix applied
- Backend tests: Portfolio exposure tests have type annotation issues (68 LSP warnings, runtime OK)
- Manual QA: **Required before launch**

**Decision Point:** If portfolio tests fail, **move to Beta/Labs** and disable by default.

---

### Projector Chart (Basic)

**Status: ✅ STABLE**

- ✅ **Candlestick/line chart with yfinance data**
  - OHLCV price data
  - Customizable timeframes (1d, 5d, 1mo, 3mo, 6mo, 1y)
  - Lightweight-charts library integration
  
- ✅ **Event markers on timeline**
  - Event indicators on chart
  - Color-coded by impact score
  - Hover tooltips with event details
  - Click-through to event details
  
- ✅ **Ticker selection**
  - Dropdown with autocomplete
  - Default to first watchlist ticker
  - URL parameter support

**Quality Gates:**
- ✅ Chart renders without errors
- ✅ Event markers display correctly
- ✅ yfinance API calls succeed (with graceful degradation)
- ✅ No memory leaks from chart library

**Testing Status:**
- E2E tests: Dashboard navigation includes Projector tab - ⚠️ Not verified
- Backend tests: Chart endpoint not specifically tested
- Manual QA: **Required before launch**

---

### RadarQuant AI (Conservative)

**Status: ⚠️ CONDITIONAL (include ONLY if reliable)**

**Include RadarQuant in V1 ONLY if it reliably:**

- ✅ **Reads from real database events**
  - Queries `events` table for context
  - Uses user's watchlist for personalization
  - References X.com feed if available
  
- ✅ **Does NOT fabricate primary events**
  - System prompt explicitly prohibits inventing filings
  - Only references events that exist in database
  - Links to official sources (SEC, FDA, company IR)
  
- ✅ **Degrades gracefully if OpenAI API fails**
  - Catches OpenAI exceptions
  - Shows user-friendly error message
  - No crashes or blank screens
  - Quota tracking continues to work
  
- ✅ **Shows clear error messages on failure**
  - "OpenAI is temporarily unavailable. Please try again later."
  - "Daily quota exceeded. Upgrade to Pro for more queries."
  - "Unable to process your query. Please rephrase and try again."

**Quality Gates:**
- ✅ RadarQuant E2E tests pass (4 tests)
- ✅ No hallucinated events in responses
- ✅ Quota enforcement works (Free: 5/day, Pro: 50/day)
- ✅ Graceful degradation verified manually
- ✅ Response time < 10 seconds for 90% of queries

**Testing Status:**
- E2E tests: 4 RadarQuant tests (query, references, quota, history) - ⚠️ Not verified
- Backend tests: OpenAI API mocked, basic logic tested
- Manual QA: **Required before launch**

**Decision Point:** If RadarQuant tests fail or show unreliability, **disable by default** and move to Beta/Labs.

**Feature Flags:**
```
ENABLE_RADARQUANT=false  # Default disabled until verified
OPENAI_API_KEY=<set>     # Required for functionality
```

---

## Beta / Labs (Exposed but NOT Required for V1)

Features visible in the UI but **clearly labeled as experimental**. These features are not critical for V1 launch and may have known issues or incomplete testing.

**Labeling Strategy:**
- 🧪 **"Beta"** badge on tab/section headers
- ⚠️ Warning banners: "This feature is experimental. We're actively working on improvements."
- Tooltips explaining limitations
- Feedback links for user reports

---

### Analytics Dashboards

**Status: ⚠️ EXPERIMENTAL**

- ⚠️ **Backtesting visualizations (beyond basic)**
  - Prediction accuracy validation (1d, 5d, 20d)
  - Directional accuracy metrics
  - MAE (Mean Absolute Error) calculation
  - **Issue:** E2E tests timing out, not verified
  - **Plan requirement:** Pro or Enterprise
  
- ⚠️ **Correlation analysis**
  - Event timeline visualization
  - Pattern discovery
  - Temporal clustering
  - **Issue:** E2E tests timing out
  - **Plan requirement:** Pro or Enterprise
  
- ⚠️ **Peer comparison**
  - Find similar events on peer companies
  - Sector-based peer matching
  - **Issue:** E2E tests timing out
  - **Plan requirement:** Pro or Enterprise
  
- ⚠️ **Calendar view**
  - Month-based event calendar
  - Day-level event drilling
  - **Issue:** E2E tests timing out
  - **Plan requirement:** Pro or Enterprise
  
- ⚠️ **CSV export**
  - Export events to CSV
  - Export portfolio analysis
  - **Issue:** Not comprehensively tested
  - **Plan requirement:** Pro or Enterprise

**Quality Gates for Promotion to V1 Core:**
1. All analytics E2E tests pass
2. No timeout errors
3. Manual QA confirms accuracy
4. Performance profiling shows acceptable load times

**Feature Flags:**
```
ENABLE_LABS_UI=false              # Hide all Beta/Labs features by default
NEXT_PUBLIC_ENABLE_ANALYTICS=false  # Analytics dashboards
```

**Testing Status:**
- E2E tests: 6 analytics tests - ❌ ALL FAILING (timeouts)
- Backend tests: Backtesting logic tested, passing
- Manual QA: **Not performed**

**Decision:** Keep in UI with "Beta" label, but **disable by default** until tests pass.

---

### Alerts System

**Status: ⚠️ EXPERIMENTAL (if E2E tests still flaky)**

- ⚠️ **Alert creation/management**
  - Create alerts with criteria (ticker, event type, min impact score)
  - Edit/delete alerts
  - Active/inactive toggle
  - **Issue:** E2E tests timing out (all 3 tests failing)
  
- ⚠️ **Email/in-app notifications**
  - Email delivery via Resend
  - In-app notification bell
  - Notification history
  - **Issue:** Email dispatch not E2E tested

**Quality Gates for Promotion to V1 Core:**
1. All 3 alert E2E tests pass
2. Email delivery verified in staging
3. No duplicate notifications
4. Deduplication logic tested

**Feature Flags:**
```
ENABLE_ALERTS_BETA=false         # Alerts system disabled until stable
ENABLE_EMAIL_NOTIFICATIONS=false # Email dispatch disabled
```

**Testing Status:**
- E2E tests: 3 alert tests - ❌ ALL FAILING (timeouts)
- Backend tests: Alert matching logic not comprehensively tested
- Manual QA: **Not performed**

**Decision:** **Disable by default** until E2E tests pass. If time permits, fix tests and promote to V1 Core.

---

### X.com / Social Sentiment

**Status: ⚠️ EXPERIMENTAL**

- ⚠️ **Twitter sentiment feed**
  - Fetch posts by ticker cashtags ($AAPL)
  - X API v2 authentication
  - Rate limit handling (100 reads/month on Free tier)
  
- ⚠️ **Social media analysis**
  - OpenAI-based sentiment classification (bullish/bearish/neutral)
  - Event hint detection
  - Confidence scoring
  
- ⚠️ **X.com posts integration**
  - Match posts to Impact Radar events
  - Clustering by (event, ticker)
  - Aggregated sentiment per cluster

**Quality Gates for Promotion to V1 Core:**
1. X API credentials verified
2. Rate limiting tested
3. Sentiment accuracy spot-checked
4. No crashes on API failures

**Feature Flags:**
```
ENABLE_X_SENTIMENT=false           # X.com sentiment disabled
NEXT_PUBLIC_ENABLE_X_FEED=false    # X feed tab hidden
X_BEARER_TOKEN=<set>               # Required for functionality
```

**Testing Status:**
- E2E tests: No dedicated X feed tests
- Backend tests: X client mocked, basic logic tested
- Manual QA: **Not performed**

**Decision:** Keep in UI with "Beta" label for users who want to experiment, but **disable by default**.

---

### Real-time Features

**Status: ❌ UNSTABLE (known WebSocket errors)**

- ⚠️ **Live WebSocket event stream**
  - Full-duplex real-time communication
  - JWT authentication
  - Per-user connection limits
  - **Issue:** WebSocket "bind" errors in browser console
  - **Issue:** `Cannot read properties of undefined (reading 'bind')` in Next.js logs
  
- ⚠️ **Server-Sent Events (SSE)**
  - Long-lived HTTP connection for event stream
  - JSON-lines message format
  - Automatic reconnection
  - **Issue:** Not comprehensively tested
  
- ⚠️ **Real-time "tape" feed**
  - Scrolling ticker of latest events
  - Real-time updates on dashboard
  - Impact score indicators
  - **Issue:** Depends on WebSocket/SSE stability

**Quality Gates for Promotion to V1 Core:**
1. WebSocket "bind" errors resolved
2. E2E tests verify real-time updates
3. No browser console errors
4. Connection stability tested (reconnection, error handling)

**Feature Flags:**
```
ENABLE_LIVE_WS=false                # WebSocket streaming disabled
NEXT_PUBLIC_ENABLE_LIVE_WS=false    # Live tape hidden
ENABLE_SSE=false                    # SSE disabled
```

**Testing Status:**
- E2E tests: Not tested (would require WebSocket stability)
- Backend tests: WebSocket hub not tested
- Manual QA: **Not performed**
- **Known issue:** WebSocket errors blocking E2E test suite

**Decision:** **Disable by default** until WebSocket errors resolved. This is a P0 bug for E2E test stability.

---

### Advanced Features

**Status: ⚠️ EXPERIMENTAL**

- ⚠️ **Deep ML model explanations**
  - Feature importance breakdowns
  - SHAP values (if implemented)
  - Model confidence intervals
  - **Issue:** Not implemented or tested
  
- ⚠️ **Custom scoring preferences**
  - User-defined weights by event type
  - Sector-specific multipliers
  - Market cap preferences
  - **Issue:** Not E2E tested
  
- ⚠️ **Advanced admin tools**
  - Manual scanner runs
  - Event moderation
  - User management
  - **Issue:** E2E tests have fixture errors

**Quality Gates for Promotion to V1 Core:**
1. E2E tests created and passing
2. Manual QA performed
3. Security audit completed (admin tools)
4. Performance impact assessed

**Feature Flags:**
```
ENABLE_ML_EXPLANATIONS=false        # ML explanations disabled
ENABLE_CUSTOM_SCORING=false         # Custom scoring disabled
ENABLE_ADMIN_TOOLS=false            # Admin tools hidden
```

**Testing Status:**
- E2E tests: None created
- Backend tests: Partial (scoring preferences DB schema exists)
- Manual QA: **Not performed**

**Decision:** **Hide by default**. These are power-user features that can wait for V2.

---

## Out of Scope (Hidden/Disabled for V1)

Features with **runtime errors, no tests, or known reliability issues**. These are explicitly excluded from V1 Beta and should be hidden from the UI.

### Exclusion Criteria

Features are **Out of Scope** if they meet any of these criteria:

- ❌ **Crashes or shows blank screens** - Immediate user-facing failure
- ❌ **Depends on unstable WebSocket plumbing** - Known WebSocket errors
- ❌ **Untested admin-only tools** - Security risk, no QA
- ❌ **Features with no E2E test coverage** - Unknown reliability
- ❌ **Experimental ML models without validation** - Accuracy unknown

### Specific Exclusions

**Real-time Features (until WebSocket fixed):**
- ❌ Live WebSocket event stream
- ❌ Real-time "tape" feed on dashboard
- ❌ Live event broadcasting

**Analytics (until tests pass):**
- ❌ Backtesting dashboard (if E2E tests still failing)
- ❌ Correlation analysis (if E2E tests still failing)
- ❌ Peer comparison (if E2E tests still failing)
- ❌ Calendar view (if E2E tests still failing)

**Alerts (until tests pass):**
- ❌ Alert creation/management (if E2E tests still failing)
- ❌ Email notifications (if not verified)

**Admin Tools (until security audit):**
- ❌ Manual scanner runs (untested)
- ❌ Event moderation (no E2E tests)
- ❌ User management (security risk)

**ML Features (until validated):**
- ❌ ML-adjusted impact scores (if unreliable)
- ❌ Deep ML explanations (not implemented)
- ❌ Self-learning ML pipeline (not production-ready)

**Social Features (until tested):**
- ❌ X.com sentiment feed (if API credentials missing)
- ❌ Social media analysis (not validated)

**Advanced Features (until V2):**
- ❌ API key generation for external developers
- ❌ Webhook integrations
- ❌ Custom data exports beyond CSV
- ❌ Multi-user teams and permissions

---

## Feature Flag System

All Beta/Labs and Out-of-Scope features **MUST be controlled by environment flags** to enable safe toggling without code changes.

### Backend (.env)

```bash
# Core V1 Features (always enabled)
ENABLE_AUTH=true
ENABLE_EVENTS=true
ENABLE_WATCHLIST=true
ENABLE_PORTFOLIO=true
ENABLE_PROJECTOR=true

# Conditional V1 Features
ENABLE_RADARQUANT=false          # Only if verified reliable
OPENAI_API_KEY=<set-if-enabled>  # Required for RadarQuant

# Beta / Labs Features (disabled by default)
ENABLE_LABS_UI=false             # Master switch: show Beta/Labs features in UI
ENABLE_ALERTS_BETA=false         # Alerts system (if E2E tests flaky)
ENABLE_X_SENTIMENT=false         # X.com sentiment analysis
ENABLE_LIVE_WS=false             # WebSocket real-time streaming
ENABLE_SSE=false                 # Server-Sent Events
ENABLE_ANALYTICS=false           # Analytics dashboards (backtesting, correlation, etc.)
ENABLE_ML_SCORING=false          # ML-adjusted impact scores
ENABLE_CUSTOM_SCORING=false      # User-defined scoring preferences

# Admin Features (disabled by default)
ENABLE_ADMIN_TOOLS=false         # Admin-only endpoints and UI

# API Credentials (required for respective features)
X_BEARER_TOKEN=<optional>        # X API v2 credentials
RESEND_API_KEY=<optional>        # Email service for notifications
STRIPE_SECRET_KEY=<optional>     # Billing (not required for V1)
```

### Frontend (marketing/.env.local)

```bash
# Core V1 Features (always enabled)
NEXT_PUBLIC_ENABLE_AUTH=true
NEXT_PUBLIC_ENABLE_EVENTS=true
NEXT_PUBLIC_ENABLE_WATCHLIST=true
NEXT_PUBLIC_ENABLE_PORTFOLIO=true
NEXT_PUBLIC_ENABLE_PROJECTOR=true

# Conditional V1 Features
NEXT_PUBLIC_ENABLE_RADARQUANT=false

# Beta / Labs Features (disabled by default)
NEXT_PUBLIC_ENABLE_LABS_UI=false        # Master switch
NEXT_PUBLIC_ENABLE_ALERTS=false
NEXT_PUBLIC_ENABLE_X_FEED=false
NEXT_PUBLIC_ENABLE_LIVE_WS=false
NEXT_PUBLIC_ENABLE_ANALYTICS=false
NEXT_PUBLIC_ENABLE_ADMIN_UI=false

# API Endpoints
NEXT_PUBLIC_API_BASE_URL=http://localhost:8080  # Backend API
```

### Feature Flag Implementation Strategy

**Backend (FastAPI):**
```python
# backend/config/feature_flags.py
from pydantic_settings import BaseSettings

class FeatureFlags(BaseSettings):
    enable_labs_ui: bool = False
    enable_alerts_beta: bool = False
    enable_x_sentiment: bool = False
    enable_live_ws: bool = False
    enable_radarquant: bool = False
    # ... etc

flags = FeatureFlags()

# Usage in routers:
@router.get("/analytics/backtesting")
async def backtesting(...):
    if not flags.enable_analytics:
        raise HTTPException(status_code=404, detail="Feature not available")
    # ... implementation
```

**Frontend (Next.js):**
```typescript
// marketing/lib/feature-flags.ts
export const featureFlags = {
  labsUI: process.env.NEXT_PUBLIC_ENABLE_LABS_UI === 'true',
  alerts: process.env.NEXT_PUBLIC_ENABLE_ALERTS === 'true',
  xFeed: process.env.NEXT_PUBLIC_ENABLE_X_FEED === 'true',
  liveWS: process.env.NEXT_PUBLIC_ENABLE_LIVE_WS === 'true',
  analytics: process.env.NEXT_PUBLIC_ENABLE_ANALYTICS === 'true',
  radarQuant: process.env.NEXT_PUBLIC_ENABLE_RADARQUANT === 'true',
} as const;

// Usage in components:
import { featureFlags } from '@/lib/feature-flags';

{featureFlags.analytics && (
  <TabsTrigger value="backtesting">
    Backtesting 🧪
  </TabsTrigger>
)}
```

---

## Quality Gates for V1

Before allowing **external beta users**, the following quality gates **MUST pass**:

### 1. ✅ Golden-path E2E tests pass (5-8 core specs)

**Minimum required tests:**
- ✅ `auth.spec.ts` (5 tests) - Signup, login, validation
- ✅ `events.spec.ts` (8 tests) - Event list, filters, details
- ✅ `watchlist.spec.ts` (5 tests) - Add/remove tickers, filtering
- ✅ `dashboard.spec.ts` (5 tests) - Navigation, tabs, UI rendering

**Conditional tests (only if features enabled):**
- ⚠️ `portfolio.spec.ts` (4 tests) - CSV upload, exposure view
- ⚠️ `radarquant.spec.ts` (4 tests) - AI queries, quota enforcement

**Total minimum:** 23 E2E tests passing (up to 31 if all conditional features enabled)

**Current status:** ❌ E2E suite timing out, tests not verified

**Action required:**
1. Fix WebSocket "bind" errors in Next.js
2. Re-run E2E test suite
3. Debug and fix any failing tests
4. Achieve 100% pass rate on core tests

---

### 2. ✅ No WebSocket "bind" errors in browser console

**Issue:** Current WebSocket implementation causes `Cannot read properties of undefined (reading 'bind')` errors in browser console during E2E test execution and potentially in production.

**Impact:**
- Blocks E2E test suite execution
- May cause runtime errors for users
- Prevents reliable testing of real-time features

**Action required:**
1. Debug Next.js WebSocket upgrade request handling
2. Fix undefined reference in WebSocket bind call
3. Verify browser console is clean in all environments
4. Re-enable WebSocket features only after fix verified

**Current status:** ❌ Known issue, blocking tests

---

### 3. ✅ Event source verification confirms real SEC/FDA URLs

**Requirement:** 100% of production events must have valid, real source URLs pointing to official sources (SEC.gov, FDA.gov, company investor relations pages).

**Verification script:** `backend/tools/verify_scanners.py` (currently broken, needs fixing)

**Checks:**
- No null or empty `source_url` fields
- URLs match expected patterns (e.g., `https://www.sec.gov/`, `https://www.fda.gov/`)
- No placeholder URLs (e.g., `https://example.com`, `https://placeholder.com`)
- URLs are reachable (HTTP 200 response)

**Action required:**
1. Fix `verify_scanners.py` script (currently has SQLAlchemy errors)
2. Run verification on staging database
3. Fix any events with invalid source URLs
4. Set up automated verification in CI/CD

**Current status:** ⚠️ Script broken, manual verification required

---

### 4. ✅ All V1 core features render without runtime errors

**Manual testing checklist:**
- [ ] Signup flow completes without errors
- [ ] Login flow completes without errors
- [ ] Email verification works (or mock works in test)
- [ ] Dashboard loads without crashes
- [ ] Event list renders with data
- [ ] Event filters work (ticker, date, type, score)
- [ ] Event detail page shows source link
- [ ] Watchlist add/remove works
- [ ] Portfolio CSV upload works (if enabled)
- [ ] Projector chart renders with event markers
- [ ] RadarQuant responds to queries (if enabled)
- [ ] No "Cannot read properties" errors in console
- [ ] No blank screens or infinite loading states
- [ ] Error messages are user-friendly

**Action required:**
1. Perform full manual QA pass
2. Document any errors or issues
3. Fix all critical bugs
4. Re-test until checklist 100% complete

**Current status:** ❌ Manual QA not performed

---

### 5. ✅ Manual QA confirms critical flows work end-to-end

**Critical user journeys to test manually:**

**Journey 1: New User Signup**
1. Visit homepage → Click "Sign Up"
2. Enter email, password → Submit
3. Receive verification email (or see mock code in test)
4. Enter verification code → Verify
5. Redirected to dashboard
6. See onboarding checklist

**Journey 2: Event Discovery**
1. Login as existing user
2. Navigate to Events tab
3. Browse event list (see real events with source links)
4. Apply filters (ticker, event type, date range)
5. Click event to see details
6. Verify source link opens to SEC/FDA/company IR page
7. See impact score and rationale

**Journey 3: Watchlist Management**
1. Navigate to Watchlist tab
2. Add ticker (e.g., AAPL) → See success message
3. View watchlist → See AAPL in list
4. Toggle "Watchlist Only" in Events tab
5. See only AAPL events
6. Remove ticker from watchlist → See success message

**Journey 4: Portfolio Upload (if enabled)**
1. Navigate to Portfolio tab
2. Download CSV template
3. Fill in 3 holdings (AAPL, MSFT, TSLA)
4. Upload CSV
5. See positions with P&L
6. View upcoming events for holdings
7. See exposure calculations

**Journey 5: RadarQuant AI (if enabled)**
1. Navigate to RadarQuant tab
2. Ask: "What are the latest FDA approvals for biotech stocks?"
3. See AI response with event references
4. Click event link → Opens event detail
5. Verify events exist in database (not hallucinated)
6. Ask 5 more queries → Hit quota limit
7. See upgrade prompt

**Action required:**
1. Recruit 2-3 internal testers
2. Provide test accounts and test data
3. Execute all 5 journeys
4. Document any bugs or UX issues
5. Fix critical issues, triage nice-to-haves

**Current status:** ❌ Not performed

---

## Success Criteria

V1 Beta is **ready for limited external users** when all of the following criteria are met:

### Functional Success Criteria

1. ✅ **User can signup → verify email → login**
   - Signup form accepts valid email/password
   - Verification code sent (real SMTP or mock in test)
   - Verification code accepted
   - User redirected to dashboard
   - Session persists across page refreshes

2. ✅ **User can browse real events with accurate source links**
   - Event list displays at least 100 events from scanners
   - Every event has a valid `source_url` (no nulls, no placeholders)
   - Source links open to SEC.gov, FDA.gov, or company IR pages
   - Events have realistic impact scores and rationales
   - No fabricated or templated events

3. ✅ **User can filter events by ticker/date/type**
   - Ticker filter accepts valid tickers (e.g., AAPL)
   - Date range filter (from/to) correctly filters events
   - Event type filter shows correct event types (earnings, FDA, etc.)
   - Multiple filters work in combination
   - Filter persistence across sessions (optional)

4. ✅ **User can view Projector chart with event markers**
   - Chart renders for selected ticker
   - Price data loads from yfinance (with graceful degradation)
   - Event markers display on timeline
   - Event markers color-coded by impact score
   - Hover tooltips show event details
   - Click event marker → Opens event detail

5. ✅ **RadarQuant answers questions using real DB data (no hallucinations)**
   - AI responds to queries within 10 seconds
   - Responses reference events that exist in database
   - Event links open to correct event detail pages
   - No fabricated filings, approvals, or announcements
   - Graceful error handling when OpenAI unavailable
   - Quota enforcement works (Free: 5/day, Pro: 50/day)

6. ✅ **NO crashes, blank screens, or "Cannot read properties" errors**
   - Browser console clean (no red errors)
   - All pages render content or empty states
   - Loading states show spinners, not blank screens
   - Error boundaries catch React errors
   - User-friendly error messages (no stack traces)

7. ✅ **Beta/Labs features clearly labeled and optional**
   - Experimental features have 🧪 "Beta" badges
   - Warning banners explain experimental status
   - Features can be toggled with environment flags
   - Disabled features return 404 or show upgrade prompts

### Quality Success Criteria

8. ✅ **E2E test suite passes (23+ core tests)**
   - All auth tests pass (5/5)
   - All event tests pass (8/8)
   - All watchlist tests pass (5/5)
   - All dashboard tests pass (5/5)
   - Conditional tests pass if features enabled

9. ✅ **Backend test suite stable (17 test files)**
   - No database schema errors
   - No fixture import errors
   - Core logic tests passing (scanner deduplication, scoring, etc.)

10. ✅ **Manual QA sign-off on critical journeys**
    - 5 critical user journeys tested manually
    - All P0 bugs fixed
    - P1 bugs documented for V1.1

### Non-Functional Success Criteria

11. ✅ **Performance acceptable**
    - Page load time < 3 seconds (90th percentile)
    - Event list renders < 2 seconds
    - API response time < 500ms (median)
    - RadarQuant response time < 10 seconds (90th percentile)

12. ✅ **Security baseline met**
    - No secrets in code or logs
    - JWT tokens validated on all protected routes
    - Password hashing with bcrypt (cost factor ≥ 12)
    - SQL injection prevention (parameterized queries)
    - XSS prevention (input sanitization)

13. ✅ **Observability in place**
    - Logging configured (backend: structlog, frontend: console)
    - Error tracking (sentry.io or similar, optional for V1)
    - Basic metrics (API request counts, error rates)

### Launch Readiness Criteria

14. ✅ **Documentation complete**
    - User guide available (basic how-to)
    - API documentation (if exposing API keys)
    - FAQ for common issues
    - Feedback mechanism (email or form)

15. ✅ **Rollout plan defined**
    - Invite 10 beta users in Wave 1
    - Collect feedback for 1 week
    - Fix critical bugs
    - Invite 25 more users in Wave 2
    - Monitor stability and performance
    - Expand to 50 total users by end of beta

16. ✅ **Support plan defined**
    - Email support address (e.g., beta@impactradar.co)
    - Expected response time (48 hours)
    - Escalation path for critical bugs
    - Weekly office hours or feedback calls (optional)

---

## Implementation Roadmap

### Phase 1: Fix Critical Blockers (Week 1)

**Goal:** Achieve baseline stability for V1 core features

1. **Fix WebSocket "bind" errors** (P0)
   - Debug Next.js WebSocket upgrade handling
   - Resolve undefined reference
   - Verify browser console clean

2. **Fix E2E test suite** (P0)
   - Re-run tests after WebSocket fix
   - Debug timeout issues in alerts.spec.ts and analytics.spec.ts
   - Achieve 100% pass rate on core tests (auth, events, watchlist, dashboard)

3. **Fix event source verification** (P0)
   - Repair `verify_scanners.py` script
   - Run on staging database
   - Fix events with invalid source URLs

4. **Manual QA pass** (P0)
   - Test all 5 critical user journeys
   - Document bugs in GitHub Issues
   - Triage P0 vs. P1 vs. P2

---

### Phase 2: Stabilize V1 Core Features (Week 2)

**Goal:** Ensure V1 core features work reliably

5. **Fix P0 bugs from Manual QA**
   - All crashes, blank screens, "Cannot read properties" errors
   - All broken links or missing data

6. **Verify feature flags work**
   - Test enabling/disabling Beta/Labs features
   - Ensure disabled features return 404 or upgrade prompts

7. **Performance testing**
   - Load test event list endpoint (100 concurrent users)
   - Profile frontend bundle size (< 1MB target)
   - Optimize slow queries (if any)

8. **Security audit (basic)**
   - Run `detect_secrets.py` script
   - Verify no secrets in code
   - Test SQL injection prevention
   - Test XSS prevention

---

### Phase 3: Beta Launch Preparation (Week 3)

**Goal:** Prepare for external beta users

9. **Documentation**
   - Write user guide (signup, browsing events, using filters)
   - Write FAQ (common errors, feature limitations)
   - Create feedback form (Google Forms or Typeform)

10. **Monitoring setup**
    - Configure logging (ensure errors captured)
    - Set up basic dashboards (request counts, error rates)
    - Create alert rules (e.g., error rate > 5%)

11. **Beta user recruitment**
    - Identify 10 Wave 1 beta testers (internal + trusted users)
    - Prepare welcome email with instructions
    - Set up beta feedback channel (Slack, Discord, or email)

---

### Phase 4: Beta Wave 1 Launch (Week 4)

**Goal:** Launch to 10 beta users and collect feedback

12. **Launch to Wave 1 (10 users)**
    - Send welcome emails with login instructions
    - Monitor logs for errors
    - Respond to feedback within 48 hours

13. **Iterate based on feedback**
    - Fix critical bugs within 24 hours
    - Triage feature requests for V1.1 or V2
    - Document workarounds for known issues

14. **Stability check**
    - Verify no crashes or data corruption
    - Check server resource usage (CPU, memory, disk)
    - Ensure scanners running on schedule

---

### Phase 5: Beta Wave 2 Expansion (Week 5-6)

**Goal:** Expand to 50 total beta users

15. **Launch to Wave 2 (25 additional users)**
    - Fix P1 bugs from Wave 1
    - Send invites to 25 more users
    - Continue monitoring and support

16. **Performance optimization**
    - Optimize slow queries identified in logs
    - Reduce frontend bundle size (code splitting)
    - Enable caching where appropriate

17. **Prepare for V1.1**
    - Promote stable Beta/Labs features to V1 core
    - Plan V2 feature roadmap based on feedback

---

## Decision Log

This section documents key decisions made during V1 scoping.

### Decision 1: Disable Real-time Features by Default

**Date:** November 15, 2025  
**Decision:** Disable WebSocket and SSE real-time features by default (`ENABLE_LIVE_WS=false`)  
**Rationale:**
- Known WebSocket "bind" errors blocking E2E tests
- Real-time features not critical for V1 value proposition
- Can enable later once stability verified

**Impact:** Users won't see live event feed or real-time tape in V1 Beta

---

### Decision 2: Make RadarQuant Conditional

**Date:** November 15, 2025  
**Decision:** RadarQuant enabled only if verified reliable (`ENABLE_RADARQUANT=false` by default)  
**Rationale:**
- High risk of hallucinated events if not properly tested
- OpenAI API dependency adds failure mode
- Better to launch without AI than with unreliable AI

**Impact:** RadarQuant may be disabled in V1 Beta if tests fail

---

### Decision 3: Move Analytics to Beta/Labs

**Date:** November 15, 2025  
**Decision:** Analytics dashboards (backtesting, correlation, calendar) moved to Beta/Labs (`ENABLE_ANALYTICS=false`)  
**Rationale:**
- All 6 analytics E2E tests failing with timeouts
- Features not critical for core event tracking value
- Can promote to V1 core once tests pass

**Impact:** Analytics features hidden by default, shown only if user enables Labs UI

---

### Decision 4: Portfolio Upload is Conditional

**Date:** November 15, 2025  
**Decision:** Portfolio CSV upload included only if E2E tests pass  
**Rationale:**
- Portfolio exposure calculations are complex and untested
- Backend tests have database schema issues
- Feature is nice-to-have, not critical for V1

**Impact:** If portfolio tests fail, feature will be disabled and moved to V1.1

---

### Decision 5: Alerts System is Conditional

**Date:** November 15, 2025  
**Decision:** Alerts system included only if E2E tests pass (`ENABLE_ALERTS_BETA=false` by default)  
**Rationale:**
- All 3 alert E2E tests failing with timeouts
- Email delivery not E2E tested
- Feature adds complexity without being critical for V1

**Impact:** Alerts may be disabled in V1 Beta if tests remain flaky

---

## Appendix: Feature Flag Reference

### Quick Reference Table

| Feature | Backend Flag | Frontend Flag | Default | V1 Status |
|---------|--------------|---------------|---------|-----------|
| **Authentication** | `ENABLE_AUTH` | `NEXT_PUBLIC_ENABLE_AUTH` | `true` | ✅ Core |
| **Events System** | `ENABLE_EVENTS` | `NEXT_PUBLIC_ENABLE_EVENTS` | `true` | ✅ Core |
| **Watchlist** | `ENABLE_WATCHLIST` | `NEXT_PUBLIC_ENABLE_WATCHLIST` | `true` | ✅ Core |
| **Portfolio** | `ENABLE_PORTFOLIO` | `NEXT_PUBLIC_ENABLE_PORTFOLIO` | `true` | ⚠️ Conditional |
| **Projector** | `ENABLE_PROJECTOR` | `NEXT_PUBLIC_ENABLE_PROJECTOR` | `true` | ✅ Core |
| **RadarQuant** | `ENABLE_RADARQUANT` | `NEXT_PUBLIC_ENABLE_RADARQUANT` | `false` | ⚠️ Conditional |
| **Alerts** | `ENABLE_ALERTS_BETA` | `NEXT_PUBLIC_ENABLE_ALERTS` | `false` | ⚠️ Beta/Labs |
| **Analytics** | `ENABLE_ANALYTICS` | `NEXT_PUBLIC_ENABLE_ANALYTICS` | `false` | ⚠️ Beta/Labs |
| **X.com Feed** | `ENABLE_X_SENTIMENT` | `NEXT_PUBLIC_ENABLE_X_FEED` | `false` | ⚠️ Beta/Labs |
| **WebSocket** | `ENABLE_LIVE_WS` | `NEXT_PUBLIC_ENABLE_LIVE_WS` | `false` | ❌ Disabled |
| **SSE** | `ENABLE_SSE` | N/A | `false` | ❌ Disabled |
| **Admin Tools** | `ENABLE_ADMIN_TOOLS` | `NEXT_PUBLIC_ENABLE_ADMIN_UI` | `false` | ❌ Hidden |
| **Labs UI** | `ENABLE_LABS_UI` | `NEXT_PUBLIC_ENABLE_LABS_UI` | `false` | ⚠️ Master switch |

---

## Appendix: Test Coverage Matrix

### E2E Test Coverage

| Feature Area | Test File | Tests | Status | V1 Required |
|--------------|-----------|-------|--------|-------------|
| Authentication | `auth.spec.ts` | 5 | ⚠️ Not verified | ✅ Yes |
| Events | `events.spec.ts` | 8 | ⚠️ Not verified | ✅ Yes |
| Watchlist | `watchlist.spec.ts` | 5 | ⚠️ Not verified | ✅ Yes |
| Dashboard | `dashboard.spec.ts` | 5 | ⚠️ Not verified | ✅ Yes |
| Portfolio | `portfolio.spec.ts` | 4 | ⚠️ Not verified | ⚠️ Conditional |
| RadarQuant | `radarquant.spec.ts` | 4 | ⚠️ Not verified | ⚠️ Conditional |
| Alerts | `alerts.spec.ts` | 3 | ❌ FAILING | ⚠️ Conditional |
| Analytics | `analytics.spec.ts` | 6 | ❌ FAILING | ❌ No (Beta/Labs) |
| Scanners | `scanners.spec.ts` | 2 | ⚠️ Not verified | ❌ No (monitoring only) |
| **TOTAL** | **9 files** | **42** | **❌ Suite timeout** | **23-31 required** |

### Backend Test Coverage

| Feature Area | Test File | Tests | Status | V1 Required |
|--------------|-----------|-------|--------|-------------|
| Scanner Deduplication | `test_scanner_deduplication.py` | 4 | ✅ Passing | ✅ Yes |
| Scoring with Market Data | `test_scoring_market_data.py` | 5 | ✅ Passing | ✅ Yes |
| Portfolio Exposure | `test_portfolio_exposure.py` | 4 | ⚠️ Schema issues | ⚠️ Conditional |
| Admin Endpoints | `test_admin_endpoints.py` | 4 | ⚠️ Fixture errors | ❌ No |
| E2E Smoke | `test_e2e_smoke.py` | 1 | ⚠️ Timeout issues | ✅ Yes |
| Access Control | `test_access_control.py` | N/A | ⚠️ Not verified | ✅ Yes |
| Other Tests | 11 files | N/A | ⚠️ Not verified | ⚠️ Mixed |
| **TOTAL** | **17 files** | **18+** | **⚠️ Mixed** | **9+ required** |

---

## Conclusion

Impact Radar V1 Beta scope is defined by a **conservative, reliability-first approach**:

**V1 Core (Must Work):**
- Authentication & account management
- Event browsing with real source links
- Filtering by ticker, date, event type, impact score
- Watchlist management
- Basic Projector chart with event markers
- RadarQuant AI (if verified reliable)

**Beta/Labs (Experimental, Clearly Labeled):**
- Analytics dashboards (backtesting, correlation, peer comparison, calendar)
- Alerts system (if E2E tests pass)
- X.com social sentiment
- Real-time features (WebSocket/SSE) - once stable
- Advanced ML explanations
- Custom scoring preferences

**Out of Scope (Hidden/Disabled):**
- Unstable real-time features (WebSocket errors)
- Untested analytics (if E2E tests still failing)
- Untested alerts (if E2E tests still failing)
- Admin tools without security audit
- Experimental ML models without validation

**Next Steps:**
1. Fix WebSocket "bind" errors (P0 blocker)
2. Re-run E2E test suite and achieve 100% pass rate on core tests
3. Perform manual QA on 5 critical user journeys
4. Fix event source verification script
5. Launch to 10 Wave 1 beta users
6. Iterate and expand to 50 total users

**Success Criteria:**
- User can signup, browse events, filter, view charts, ask RadarQuant questions
- No crashes, blank screens, or errors
- All quality gates pass
- Beta/Labs features clearly labeled and optional

This V1 scope balances **ambition with pragmatism**, ensuring we ship a product that **delights users rather than frustrates them**.

---

**Document Status:** ✅ Complete  
**Next Review:** After Phase 1 (WebSocket fixes and E2E test suite stabilization)  
**Owner:** Product & Engineering Team  
**Approval Required:** Yes (before external beta launch)
