## Security Policy

Impact Radar implements enterprise-grade security practices for handling sensitive user data, credentials, and financial information.

---

### 🔒 Authentication & Authorization

#### Password Security
- **Hashing**: bcrypt with per-user salt (cost factor 12)
- **Minimum Requirements**:
  - 8+ characters
  - 1+ uppercase letter
  - 1+ lowercase letter
  - 1+ number
  - 1+ special character
- **Storage**: Only hashed passwords stored, never plaintext
- **Transmission**: HTTPS only in production

#### Email Verification
- 6-digit verification codes
- 15-minute expiry
- One-time use (invalidated after verification)
- 5-attempt lockout with exponential backoff
- Codes transmitted via SMTP (TLS encrypted)

#### SMS Verification (Optional)
- 6-digit verification codes
- 15-minute expiry
- Twilio API integration
- Rate limited to prevent abuse

#### Session Management
- Secure HTTP-only cookies
- 24-hour session expiry
- CSRF protection via `SESSION_SECRET`
- Automatic logout on suspicious activity

---

### 🔐 Secrets Management

#### Environment Variables
All secrets are loaded from environment variables, NEVER hard-coded:

```bash
# Required Secrets
DATABASE_URL=postgresql://...
SECRET_KEY=<random-32-char-string>
SESSION_SECRET=<random-32-char-string>

# Optional Service Secrets
SMTP_PASSWORD=<gmail-app-password>
TWILIO_AUTH_TOKEN=<twilio-token>
STRIPE_API_KEY=sk_test_...
```

#### Secret Rotation
- Rotate `SECRET_KEY` and `SESSION_SECRET` every 90 days
- Update API keys (Stripe, Twilio) annually
- Database credentials managed by hosting provider

#### Feature Flags
Use feature flags to disable unused integrations:
```bash
ENABLE_STRIPE=false          # Disable if not using payments
ENABLE_SMS_VERIFICATION=false # Disable if not using Twilio
ENABLE_CRYPTO_PAYMENTS=false  # ALWAYS disabled (not implemented)
```

---

### 🛡️ Data Protection

#### Personal Identifiable Information (PII)
- **Email addresses**: Stored lowercase, indexed for uniqueness
- **Phone numbers**: Stored in international format
- **Passwords**: bcrypt hashed, never logged or transmitted
- **Verification codes**: Automatically purged after expiry

#### PII Logging Protection
The `logging.py` module includes automatic PII redaction:
```python
# These fields are automatically [REDACTED] in logs
PII_FIELDS = {
    "email", "phone", "password", "token", "api_key", "secret",
    "code", "verification", "auth", "bearer", "stripe", "key_hash"
}
```

Example log output:
```json
{
  "timestamp": "2024-11-10T12:00:00Z",
  "level": "INFO",
  "message": "User login",
  "email": "[REDACTED]",
  "ip": "192.168.1.1"
}
```

#### Database Security
- TLS-encrypted connections (`sslmode=require`)
- Connection pooling prevents connection exhaustion
- SQL injection protection via SQLAlchemy parameterized queries
- Row-level security (future enhancement)

---

### 🚨 Input Validation

#### Pydantic Models
All external input is validated via Pydantic:

```python
from releaseradar.domain.events import EventInput

# This will raise ValidationError if invalid
event = EventInput(
    ticker="AAPL",  # Auto-uppercased
    event_type="earnings",  # Validated against VALID_EVENT_TYPES
    title="Q4 Earnings",  # Max 500 chars
    date=datetime.now()
)
```

#### Length Limits
```python
# Company
ticker: max 10 chars
name: max 200 chars

# Event
title: max 500 chars
description: max 5000 chars
source_url: max 1000 chars

# User
email: validated format, max 255 chars
notes: max 5000 chars
```

#### SQL Injection Prevention
- ✅ Always use SQLAlchemy ORM (parameterized queries)
- ✅ Repository pattern abstracts raw SQL
- ❌ Never concatenate user input into SQL strings

---

### 💳 Payment Security

#### Stripe Integration
- **Test Mode Only**: Production payments require PCI compliance
- **Webhook Verification**: All webhooks verify `stripe-signature` header
- **No Card Storage**: Stripe handles all payment data
- **Audit Logs**: All transactions logged with timestamps

#### Compliance
- **Not PCI Compliant**: Use Stripe's hosted checkout for production
- **No Financial Advice**: Clear disclaimers throughout UI
- **Terms of Service**: Required acceptance for paid tiers

---

### 🌐 Network Security

#### Rate Limiting
Per-domain rate limits prevent abuse:
```python
# SEC EDGAR
10 requests / 1 second

# FDA.gov
5 requests / 1 second

# Default (other domains)
100 requests / 60 seconds
```

#### CORS Configuration
```python
# .env
ALLOWED_ORIGINS=http://localhost:5000,https://yourdomain.replit.app
```

#### DDoS Protection
- Cloudflare integration recommended
- Application-level rate limiting (see above)
- Database connection pooling (max 10 connections)

---

### 📊 Audit Logging

#### Scanner Logs
All scanner activity is logged:
```python
from releaseradar.services.data import DataService

dm = DataService()
dm.log_scanner_event("sec", "Scanned 100 filings", level="info")
```

Levels: `info`, `warning`, `error`

#### Security Events
The following events are automatically logged:
- User login/logout
- Failed authentication attempts
- Verification code generation/validation
- Password changes
- Permission escalation (admin actions)

#### Log Retention
- Application logs: 10 days (rotated, compressed)
- Scanner logs: 30 days (database)
- Security events: 90 days (future enhancement)

---

### 🔍 Vulnerability Disclosure

#### Reporting Security Issues
**DO NOT** create public GitHub issues for security vulnerabilities.

Contact: security@impactradar.co

Include:
- Description of vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (optional)

#### Response Timeline
- Initial response: 48 hours
- Severity assessment: 7 days
- Fix deployment: 30 days (critical issues prioritized)

---

### ✅ Security Checklist

Before deploying to production:

- [ ] All secrets in environment variables (not hard-coded)
- [ ] `SECRET_KEY` and `SESSION_SECRET` are random 32+ character strings
- [ ] `DATABASE_URL` uses `sslmode=require`
- [ ] SMTP credentials use app-specific passwords (not account password)
- [ ] Stripe in test mode (`sk_test_...`) or disabled
- [ ] `ALLOWED_ORIGINS` configured for production domain
- [ ] HTTPS enabled (Replit Autoscale handles this)
- [ ] PII logging filter enabled (default in `logging.py`)
- [ ] Input validation on all user inputs
- [ ] SQL queries use SQLAlchemy ORM (no raw SQL)
- [ ] Rate limiting enabled (`RATE_LIMIT_ENABLED=true`)
- [ ] Pre-commit hooks installed (`pre-commit install`)

---

### 🛠️ Security Tools

#### Static Analysis
```bash
# Type checking
make typecheck

# Linting (includes security checks)
make lint
```

#### Dependency Scanning
```bash
# Check for known vulnerabilities
pip-audit

# Update dependencies
pip install --upgrade -r requirements.txt
```

#### Secrets Detection
Pre-commit hook automatically detects committed secrets:
```yaml
- id: detect-private-key  # Blocks commits with private keys
```

---

### 📜 Disclaimers

#### Investment Disclaimer
> Impact Radar provides information only. Not investment advice. No performance guarantees. Always verify with original filings. Past performance does not guarantee future results.

#### Data Accuracy
> Event data is sourced from public filings (SEC, FDA, company websites). Accuracy depends on source reliability and parsing logic. Always verify critical decisions with original documents.

#### Liability
> Impact Radar and its operators assume no liability for trading losses, missed events, or data errors. Use at your own risk.

---

### 🔄 Updates

This security policy is reviewed quarterly. Last updated: **November 2024**

Changes:
- Initial security policy creation
- Documented authentication, PII protection, payment security
- Added audit logging requirements
- Defined vulnerability disclosure process

---

## 🔒 Security Audit Report (November 2025)

### Comprehensive Security Hardening - 5 Risk Areas

#### 1. Access Control Audit ✅ PASSED

**Findings:**
- ✅ All user-scoped endpoints (alerts, portfolio, watchlist, notifications, API keys) properly enforce `user_id` isolation
- ✅ Admin-only endpoints (`/scores/rescore`, `/scanners/run/*`) protected by `require_admin` dependency
- ✅ `require_admin` implementation verifies JWT **and** checks `is_admin` flag in database (not just JWT claim)
- ✅ WebSocket hub filters broadcasts by `user_id` - connections only receive messages for their user
- ✅ DataManager methods properly scope queries by `user_id` when called from routers
- ✅ WebSocket MAX_CONNECTIONS_PER_USER = 5 enforced (prevents connection flood)

**Test Coverage:**
- `test_access_control.py` - 12 tests covering user isolation across all scoped endpoints
- Verified: User A cannot read/modify User B's alerts, portfolios, watchlists, API keys, or notifications
- Verified: Non-admin users receive 403 Forbidden on admin endpoints

**Security Posture:** NO CROSS-USER DATA LEAKS DETECTED

---

#### 2. Secrets & Key Management ✅ PASSED

**Findings:**
- ✅ No hardcoded secrets found in repository (verified via automated scan)
- ✅ All secrets loaded from environment variables (JWT_SECRET, STRIPE_SECRET_KEY, DATABASE_URL, etc.)
- ✅ PII_Filter enhanced to redact: email, phone, password, token, api_key, secret, code, verification, auth, bearer, stripe, key_hash
- ✅ API keys masked in responses (only last 4 chars shown)
- ✅ Password hashes use bcrypt with cost factor 12
- ✅ Next.js uses process.env for secrets (no client-side exposure)
- ✅ Authorization headers automatically redacted from logs via PII_Filter

**Automated Detection:**
- `scripts/detect_secrets.py` - Scans repo for 10+ secret patterns (Stripe keys, JWT secrets, AWS keys, etc.)
- Run in CI/CD to fail builds with hardcoded secrets

**Test Coverage:**
- `test_secrets.py` - 10 tests covering PII redaction, password hashing, secret masking
- Verified: No secrets in API responses, logs, or frontend bundles

**Security Posture:** NO SECRET LEAKS DETECTED

---

#### 3. XSS Protection ✅ PASSED

**Findings:**
- ✅ No `dangerouslySetInnerHTML` found in marketing/ components (verified via grep)
- ✅ React components render event data as plain text using `{curly}` braces (auto-escaped)
- ✅ API returns `application/json` content-type (browser auto-escapes)
- ✅ Event titles/descriptions with `<script>` tags rendered as literal text (not executed)
- ✅ Multiple XSS vectors tested: script, img, svg, iframe, onclick, onerror

**Frontend Rendering:**
- React default behavior escapes HTML in JSX expressions
- Event cards use `<h3>{event.title}</h3>` (safe) not `dangerouslySetInnerHTML` (unsafe)
- JSON API responses automatically escaped by browser

**Test Coverage:**
- `test_xss.py` - 8 tests with malicious payloads in event titles/descriptions
- Verified: `<script>alert("XSS")</script>` rendered as plain text, not executed

**Recommendation:**
- Add Content-Security-Policy header: `default-src 'self'; script-src 'self'; object-src 'none'`

**Security Posture:** NO XSS VULNERABILITIES DETECTED

---

#### 4. Webhook Security ✅ PASSED

**Findings:**
- ✅ Stripe webhooks validate signatures using `stripe.Webhook.construct_event()`
- ✅ Invalid signatures return 400 Bad Request (before processing)
- ✅ Webhook secret loaded from environment (STRIPE_WEBHOOK_SECRET)
- ✅ Plan changes only occur with valid Stripe signatures (prevents fake events)
- ✅ Idempotent webhook handling (duplicate events handled safely)
- ✅ Alert dispatch has rate limiting: 10 notifications per 5 minutes per user
- ✅ Email/SMS channels rate limited at dispatch layer

**Webhook Validation Flow:**
```python
# billing.py:167-175
event = stripe.Webhook.construct_event(
    payload=payload,
    sig_header=sig_header,
    secret=webhook_secret  # From env
)
# Raises SignatureVerificationError if invalid
```

**Alert Rate Limiting:**
- Implemented in `alerts/dispatch.py:92-94`
- Prevents spam via deduplication and per-user rate limits
- Metrics: `alerts_rate_limited_total`, `alerts_deduped_total`

**Test Coverage:**
- `test_webhook_security.py` - 9 tests covering signature validation, fake events, idempotency
- Verified: Invalid signatures rejected, plan changes require valid Stripe events

**Security Posture:** NO WEBHOOK SPOOFING VULNERABILITIES

---

#### 5. DoS Protection ✅ PASSED

**Findings:**
- ✅ Login endpoint rate limited: 10 attempts/minute (prevents brute force)
- ✅ Register endpoint rate limited: 5 registrations/minute (prevents account spam)
- ✅ Plan-based API rate limits: Free (30/min), Pro (600/min), Team (3000/min)
- ✅ WebSocket connection limit: MAX_CONNECTIONS_PER_USER = 5
- ✅ WebSocket heartbeat: 15-second pings (idle timeout protection)
- ✅ Message buffering: 500-message queue with FIFO drop on overflow
- ✅ Admin endpoints rate limited: `/scores/rescore` at 30/minute

**Rate Limiting Implementation:**
```python
# ratelimit.py
def plan_limit(request: Request) -> str:
    plan = getattr(request.state, "plan", "public")
    return {
        "public": "30/minute",
        "pro": "600/minute",
        "team": "3000/minute",
    }.get(plan, "60/minute")
```

**WebSocket Protection:**
- 5 concurrent connections per user (hub.py:107)
- 500-message buffer prevents memory exhaustion
- Backpressure handling: oldest messages dropped if queue full

**Test Coverage:**
- `test_rate_limiting.py` - 8 tests covering auth limits, plan limits, WebSocket limits
- Verified: Rate limits enforced, 429 responses returned

**Recommendations:**
- Add payload size limit (FastAPI `Request.body()` max size)
- Add IP-based rate limiting for unauthenticated public endpoints

**Security Posture:** COMPREHENSIVE DOS PROTECTION IN PLACE

---

### Security Testing Suite

**New Test Files:**
- `backend/tests/test_access_control.py` - 12 tests (user isolation)
- `backend/tests/test_webhook_security.py` - 9 tests (Stripe validation)
- `backend/tests/test_rate_limiting.py` - 8 tests (DoS protection)
- `backend/tests/test_secrets.py` - 10 tests (PII redaction)
- `backend/tests/test_xss.py` - 8 tests (XSS protection)

**Total:** 47 new security tests covering all 5 risk areas

**Run Tests:**
```bash
cd backend
pytest tests/test_access_control.py -v
pytest tests/test_webhook_security.py -v
pytest tests/test_rate_limiting.py -v
pytest tests/test_secrets.py -v
pytest tests/test_xss.py -v
```

---

### Automated Security Checks

**Secret Detection:**
```bash
cd backend
python3 scripts/detect_secrets.py
# Exit code 1 if secrets found, 0 otherwise
```

**Patterns Detected:**
- Stripe secret keys (sk_live_, sk_test_)
- JWT secrets (hardcoded values)
- Database URLs (hardcoded)
- Bearer tokens
- AWS access keys
- Private keys (PEM)
- GitHub tokens

**CI/CD Integration:**
```yaml
# .github/workflows/security.yml
- name: Detect Secrets
  run: python3 backend/scripts/detect_secrets.py
```

---

### Security Metrics

**Prometheus Metrics:**
- `alerts_rate_limited_total` - Alerts blocked by rate limiting
- `alerts_deduped_total` - Duplicate alerts prevented
- `score_cache_hits_total` - Cache efficiency
- `rescore_requests_total` - Admin operations tracked
- `alerts_sent_total{channel}` - Alert delivery by channel

**Logging:**
- All PII redacted automatically via `PII_Filter`
- Structured JSON logs with request IDs
- No secrets, tokens, or passwords in logs

---

### Compliance & Best Practices

**✅ OWASP Top 10 Coverage:**
1. Broken Access Control - PASS (user_id scoping enforced)
2. Cryptographic Failures - PASS (bcrypt, TLS, env vars)
3. Injection - PASS (SQLAlchemy parameterized queries)
4. Insecure Design - PASS (rate limiting, validation)
5. Security Misconfiguration - PASS (secrets from env)
6. Vulnerable Components - PASS (dependencies monitored)
7. Authentication Failures - PASS (bcrypt, rate limits, JWT)
8. Software/Data Integrity - PASS (Stripe signature validation)
9. Logging Failures - PASS (PII redaction, structured logs)
10. SSRF - N/A (no user-controlled URLs)

**✅ CWE Coverage:**
- CWE-79 (XSS) - PASS (React auto-escaping, no dangerouslySetInnerHTML)
- CWE-89 (SQL Injection) - PASS (SQLAlchemy parameterized)
- CWE-200 (Information Exposure) - PASS (PII redaction)
- CWE-352 (CSRF) - PASS (SESSION_SECRET, SameSite cookies)
- CWE-798 (Hardcoded Credentials) - PASS (env vars only)

---

### Audit Summary

**SECURITY POSTURE: PRODUCTION-READY ✅**

- ✅ Access control enforced across all endpoints
- ✅ No hardcoded secrets or PII leaks
- ✅ XSS protection via React auto-escaping
- ✅ Webhook signature validation prevents spoofing
- ✅ Comprehensive DoS protection via rate limiting

**Verified by:** 47 automated security tests + manual code audit

**Last Audit:** November 13, 2025

**Next Review:** February 2026 (Quarterly)

