# Impact Radar AI Rules & Project Documentation

## Project Overview

Impact Radar is a stock market intelligence platform that tracks upcoming company releases, product launches, and regulatory events impacting stock prices. Built with Streamlit and PostgreSQL, it provides real-time event tracking, portfolio analysis, and automated scanning capabilities.

**Tagline**: "Market-moving events, tracked to the second."

## Tech Stack

### Core Framework
- **Frontend**: Streamlit (Python web framework)
- **Backend**: Python 3.x
- **Database**: PostgreSQL (Neon-backed)
- **ORM**: SQLAlchemy

### Key Libraries
- **yfinance**: Real-time stock price data
- **Trafilatura**: Web content extraction
- **BeautifulSoup4**: HTML parsing (SEC EDGAR)
- **Requests**: HTTP client for web scraping
- **bcrypt**: Password hashing with salt
- **APScheduler**: Background task scheduling
- **Stripe**: Payment processing
- **Plotly**: Data visualization
- **Pandas**: Data manipulation

### External Services
- **SMTP**: Email verification codes
- **Twilio**: SMS verification codes
- **SEC EDGAR**: Regulatory filings
- **FDA.gov**: Pharmaceutical announcements
- **Yahoo Finance**: Stock price data via yfinance

## File Structure

```
/
├── app.py                    # Main Streamlit application
├── database.py               # Database models and initialization
├── data_manager.py           # Centralized data access layer (CRUD operations)
├── auth_service.py           # Authentication logic (login, signup, verification)
├── email_service.py          # SMTP email sending service
├── sms_service.py            # Twilio SMS service
├── scanner_service.py        # Automated scanners (SEC, FDA, Company Releases)
├── payment_service.py        # Stripe payment integration
├── populate_stocks.py        # Database population script (168 companies, 532 events)
├── AUTH_SETUP_GUIDE.md       # SMTP/Twilio configuration instructions
└── replit.md                 # Project memory and user preferences
```

## Architecture Patterns

### 1. Data Access Layer
**Pattern**: All database operations go through `DataManager` class
- Centralized CRUD operations
- Single source of truth
- Abstracts database implementation from UI

**Example**:
```python
from data_manager import get_data_manager
dm = get_data_manager()
events = dm.get_events()  # Never query database directly in app.py
```

### 2. Service Layer
**Pattern**: Business logic separated into service classes
- `AuthService`: User authentication, password hashing, verification codes
- `EmailService`: SMTP email sending
- `SMSService`: Twilio SMS sending
- `ScannerService`: Automated data collection
- `PaymentService`: Stripe integration

### 3. Session Management
**Pattern**: Streamlit session state for authentication
```python
st.session_state.authenticated  # Boolean
st.session_state.user_id        # Integer
st.session_state.user_email     # String or None
st.session_state.user_phone     # String or None
st.session_state.auth_page      # 'login', 'signup', or 'verify'
```

### 4. Form-Based UI
**Pattern**: All authentication pages use `st.form()` for stability
- Prevents Streamlit rerun conflicts
- Isolates form submissions
- Ensures stable rendering

## Database Schema

### Tables

**companies**
- `id` (serial, primary key)
- `name` (varchar, unique)
- `ticker` (varchar)
- `sector` (varchar) - Tech, Pharma, Finance, Retail, Gaming, Other
- `parent_company_id` (integer, nullable) - For subsidiaries
- `tracked` (boolean, default false) - Bookmark/watchlist status

**events**
- `id` (serial, primary key)
- `company_id` (integer, foreign key)
- `title` (text)
- `description` (text)
- `event_date` (timestamp)
- `impact_score` (integer, 0-100)
- `category` (varchar) - Regulatory Filing, Product Launch, Earnings Report, etc.
- `source_url` (text) - Direct link to original document
- `created_at` (timestamp)

**users**
- `id` (serial, primary key)
- `email` (varchar, unique, nullable)
- `phone` (varchar, unique, nullable)
- `password_hash` (varchar) - bcrypt hashed with salt
- `verification_method` (varchar) - 'email' or 'phone'
- `is_verified` (boolean, default false)
- `is_admin` (boolean, default false) - Administrator privileges
- `created_at` (timestamp)

**verification_codes**
- `id` (serial, primary key)
- `user_id` (integer, foreign key)
- `code` (varchar, 6 digits)
- `code_type` (varchar) - 'email' or 'phone'
- `expires_at` (timestamp) - 15 minutes from creation
- `created_at` (timestamp)

## Admin Features

### Admin Privileges
Administrators have:
- Unlimited manual scans (no rate limiting)
- Access to all premium features
- Crown badge in header (👑 ADMIN)
- Bypass pricing restrictions

### Granting Admin Access
```sql
-- Via SQL (development database only)
UPDATE users SET is_admin = true WHERE email = 'user@example.com';
```

### Admin Checks
```python
# Use helper function throughout app
if user_is_admin():
    # Grant unlimited access
    # Bypass pricing tier checks
    # Show admin-only features
```

**Security Note**: Admin status is:
1. Stored in database (`users.is_admin`)
2. Loaded into session state on login
3. Verified via `user_is_admin()` helper function
4. Cleared on logout

## Key Features & Implementation

### 1. Impact Scoring System
**Directional Impact**:
- Positive events: 60-90 range (green = 80+, yellow = 60-79)
- Negative events: 10-59 range (red)

**Color Coding**:
```python
if impact >= 80: color = "🟢"  # High positive
elif impact >= 60: color = "🟡"  # Moderate
else: color = "🔴"  # Low/negative
```

### 2. SEC Document Links
**Pattern**: Direct links to interactive filing viewer
```python
# Good: Interactive viewer
f"https://www.sec.gov/ix?doc=/Archives/edgar/data/{cik}/{accession}.htm"

# Bad: Search results page
f"https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK={ticker}"
```

### 3. Bookmark Workflow
**Pattern**: Users star companies → Scanners monitor only tracked companies
```python
# Feed tab: Users click star → sets company.tracked = True
# Scanner logic: Only scan companies where tracked = True
tracked_companies = dm.get_companies(tracked=True)
```

### 4. Authentication Flow
**Signup**:
1. User enters email/phone + password
2. `AuthService.create_user()` creates account with bcrypt hash
3. `AuthService.create_verification_code()` generates 6-digit code
4. `EmailService` or `SMSService` sends code
5. User enters code on verification page
6. `AuthService.verify_code()` activates account

**Login**:
1. User enters credentials
2. `AuthService.login()` verifies password with bcrypt
3. If verified: Set session state (authenticated, user_id, email/phone, is_admin), redirect to dashboard
4. If unverified: Redirect to verification page with new code

**Admin Session Setup**:
```python
# On successful login
st.session_state.is_admin = result.get('is_admin', False)

# Check admin status
if user_is_admin():
    # Admin privileges active
```

### 5. Portfolio Tracker (Earnings Tab)
**Pattern**: Live stock prices + event impact calculation
```python
# yfinance for real-time prices
stock = yf.Ticker(ticker)
current_price = stock.info['currentPrice']

# Calculate potential impact
investment_amount = user_input
projected_change = (impact_score / 100) * investment_amount
```

## Environment Variables (Replit Secrets)

### Database (Auto-configured)
- `DATABASE_URL`
- `PGHOST`, `PGPORT`, `PGDATABASE`, `PGUSER`, `PGPASSWORD`

### Authentication
- `SESSION_SECRET` - Session encryption key

### Email (User-configured)
- `SMTP_HOST` - e.g., smtp.gmail.com
- `SMTP_PORT` - Usually 587
- `SMTP_USER` - Email address
- `SMTP_PASSWORD` - App password (for Gmail)
- `FROM_EMAIL` - Sender address (defaults to SMTP_USER)

### SMS (User-configured)
- `TWILIO_ACCOUNT_SID`
- `TWILIO_AUTH_TOKEN`
- `TWILIO_PHONE_NUMBER` - Format: +1234567890

## Design Guidelines

### UI/UX Principles
1. **No emojis** in UI (professional appearance) - Only use in internal data
2. **Clean table-based layout** for event display
3. **Form isolation** for all authentication pages
4. **Color-coded impact** for quick visual assessment
5. **Tab-based navigation** for feature access

### Code Conventions
1. **Use DataManager** for all database operations
2. **Never query database directly** in app.py
3. **Use st.form()** for all user input forms
4. **Environment variables** for all credentials
5. **bcrypt** for all password operations
6. **Session state** for authentication status

### Security Rules
1. **NEVER** log or print secrets/API keys
2. **ALWAYS** use bcrypt for password hashing
3. **NEVER** store plain text passwords
4. **ALWAYS** validate user input
5. **NEVER** expose database credentials

## Common Tasks

### Adding a New Company
```python
dm = get_data_manager()
dm.add_company(
    name="Apple Inc.",
    ticker="AAPL",
    sector="Tech",
    tracked=False  # User must bookmark to activate scanning
)
```

### Adding a New Event
```python
dm.add_event(
    company_id=1,
    title="Q4 Earnings Report",
    description="Apple Inc. quarterly earnings announcement",
    event_date=datetime(2025, 1, 30, 16, 30),
    impact_score=75,  # 60-90 for positive, 10-59 for negative
    category="Earnings Report",
    source_url="https://www.sec.gov/ix?doc=/Archives/..."
)
```

### Updating Impact Scores
```python
# Positive event: Product launch, positive FDA approval
impact_score = 80  # Green indicator

# Neutral event: Standard earnings report
impact_score = 65  # Yellow indicator

# Negative event: Regulatory investigation, product recall
impact_score = 30  # Red indicator
```

### Running Scanners
```python
scanner_service = get_scanner_service()

# Scan only bookmarked companies
scanner_service.scan_sec_edgar()
scanner_service.scan_fda()
scanner_service.scan_company_releases()
```

## Data Integrity Rules

1. **No mock data** in production
2. **All events must have source URLs** linking to original documents
3. **Impact scores must reflect reality** (use historical data for reference)
4. **Subsidiaries must link to parent** via `parent_company_id`
5. **Verification codes expire** after 15 minutes

## Streamlit-Specific Rules

### Configuration
- Server port: **5000** (required for Replit deployment)
- Use `st.rerun()` NOT `experimental_rerun()`
- Config file: `.streamlit/config.toml` (DO NOT modify)

### Session State Management
```python
# Initialize at app start
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.auth_page = 'login'
    st.session_state.is_admin = False

# Protect main app
if not st.session_state.authenticated:
    show_auth_pages()
    st.stop()

# Check admin privileges
def user_is_admin():
    """Check if current user has admin privileges."""
    return st.session_state.get('is_admin', False)
```

### Form Best Practices
```python
# GOOD: Form isolation prevents rerun conflicts
with st.form("login_form"):
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    submitted = st.form_submit_button("Login")

# BAD: Direct buttons cause rendering issues
email = st.text_input("Email")
password = st.text_input("Password", type="password")
if st.button("Login"):  # Causes flickering
    pass
```

## Testing Guidelines

### Authentication Testing
1. Signup with email/phone
2. Verify code received (check logs if SMTP/Twilio not configured)
3. Login with credentials
4. Verify session persistence
5. Test logout functionality

### Data Testing
1. Verify all 168 companies loaded
2. Verify all 532 events loaded
3. Check impact score color coding
4. Verify SEC links go to interactive viewer
5. Test bookmark workflow

### Scanner Testing
1. Add tracked company
2. Run scanner
3. Verify new events discovered
4. Check AI summary generation
5. Verify source URL accuracy

## Deployment Notes

### Workflow Configuration
```
streamlit run app.py --server.port 5000
```

### Pre-deployment Checklist
1. All environment variables configured
2. Database initialized and populated
3. Authentication flow tested
4. Payment integration tested (if enabled)
5. Scanners tested with bookmarked companies

## Important Reminders

1. **Scanner Focus**: Only scan companies with `tracked=True`
2. **Password Security**: Always use bcrypt, never SHA-256 or plain text
3. **Form Stability**: All auth pages wrapped in `st.form()`
4. **Impact Direction**: 60+ positive (green/yellow), <60 negative (red)
5. **SEC Links**: Use interactive viewer URLs, not search pages
6. **Service Credentials**: Must restart app after adding secrets
7. **Professional Design**: No emojis in UI, clean tables only

## External Documentation

- See `AUTH_SETUP_GUIDE.md` for SMTP/Twilio configuration
- See `replit.md` for project history and user preferences
- See Streamlit docs for framework-specific questions
- See SQLAlchemy docs for ORM patterns

## Project Status

**Current State**: Production-ready with full authentication, event tracking, portfolio analysis, and automated scanning capabilities. Platform tracks 168 companies and 532 events across 6 sectors.

**Next Steps** (if requested):
- Link user accounts to personalized watchlists (user-specific bookmarks)
- Add user profile management page
- Implement subscription tier enforcement
- Add email notifications for tracked events
