# Sentry Error Monitoring Setup Guide

This guide explains how to set up Sentry error monitoring for Impact Radar's Next.js marketing site and FastAPI backend.

## Overview

Sentry provides real-time error tracking and performance monitoring for both the frontend (Next.js) and backend (FastAPI). This integration helps you:

- **Catch and track errors** before users report them
- **Monitor performance** with distributed tracing
- **Debug faster** with detailed error context and stack traces
- **Protect user privacy** with PII redaction
- **Control costs** with configurable sampling rates

## Prerequisites

1. Create a Sentry account at [sentry.io](https://sentry.io)
2. Create two projects in your Sentry organization:
   - **Next.js project** for the marketing site frontend
   - **Python/FastAPI project** for the backend API

## Installation

### Next.js (Marketing Site)

```bash
cd marketing
npm install @sentry/nextjs --save
```

### FastAPI (Backend)

```bash
cd backend
pip install sentry-sdk[fastapi]
# Or add to requirements.txt (already added)
```

## Environment Variables

### Next.js Environment Variables

Create `marketing/.env.local` with the following variables:

```bash
# Sentry Configuration
# Get these values from your Sentry dashboard: Settings > Projects > [Your Project] > Client Keys (DSN)

# Public DSN for client-side error tracking (safe to expose in browser)
NEXT_PUBLIC_SENTRY_DSN=https://your-key@o1234567.ingest.sentry.io/1234567

# Environment (development/staging/production)
NEXT_PUBLIC_SENTRY_ENVIRONMENT=development
SENTRY_ENVIRONMENT=development

# For source map uploads (optional, improves stack traces)
SENTRY_AUTH_TOKEN=your-auth-token-here
SENTRY_ORG=your-org-slug
SENTRY_PROJECT=your-project-slug
```

### FastAPI Environment Variables

Add to your `.env` file or environment:

```bash
# Sentry DSN for backend error tracking
SENTRY_DSN=https://your-key@o1234567.ingest.sentry.io/1234567

# Environment (development/staging/production)
SENTRY_ENVIRONMENT=development
ENV=development
```

## Getting Your DSN Values

1. Log in to [sentry.io](https://sentry.io)
2. Navigate to **Settings** > **Projects**
3. Select your project (Next.js or Python/FastAPI)
4. Go to **Client Keys (DSN)**
5. Copy the **DSN** value
6. Paste into the appropriate environment variable

**Important:** Use the **same DSN** for both `NEXT_PUBLIC_SENTRY_DSN` (Next.js) and the backend if you want errors from both to go to the same project, or use **different DSNs** if you created separate projects.

## Getting Your Auth Token (Optional)

For source map uploads (improves stack trace readability):

1. Go to **Settings** > **Auth Tokens**
2. Click **Create New Token**
3. Select scopes: `project:releases`, `project:write`, `org:read`
4. Copy the token and add to `SENTRY_AUTH_TOKEN`

## Configuration Files

All configuration files have been created for you:

### Next.js Configuration Files

- ✅ `marketing/sentry.client.config.ts` - Browser-side monitoring
- ✅ `marketing/sentry.server.config.ts` - Server-side monitoring
- ✅ `marketing/sentry.edge.config.ts` - Edge runtime monitoring
- ✅ `marketing/instrumentation.ts` - Instrumentation entry point
- ✅ `marketing/app/global-error.tsx` - Global error boundary
- ✅ `marketing/next.config.js` - Updated with `withSentryConfig`

### FastAPI Configuration

- ✅ `backend/api/main.py` - Sentry initialization added
- ✅ `backend/requirements.txt` - `sentry-sdk[fastapi]` added

## Sample Rates & Performance

### Production Recommendations

**Next.js:**
- `tracesSampleRate: 0.1 to 0.2` - Capture 10-20% of performance transactions
- `replaysSessionSampleRate: 0.01` - Record 1% of user sessions
- `replaysOnErrorSampleRate: 1.0` - Record 100% of sessions with errors

**FastAPI:**
- `traces_sample_rate: 0.2` - Capture 20% of API requests for performance monitoring

**Why lower rates in production?**
- Reduces Sentry quota usage and costs
- Still captures enough data for statistical analysis
- Error sampling is always at 100%

### Development Settings

Both integrations are configured to use **100% sampling** in development for easier debugging.

## Security & Privacy

### PII Protection

Both integrations include **automatic PII redaction** to prevent sending sensitive user data to Sentry:

**Redacted Data:**
- User emails and IP addresses
- Cookies and authorization headers
- API keys, tokens, passwords
- Database connection strings
- Secret environment variables

**What IS sent:**
- Error messages and stack traces
- Request URLs (with query params sanitized)
- Browser/OS information (Next.js)
- Performance metrics
- Error context and breadcrumbs

### Configuration

- FastAPI: `send_default_pii=False` prevents automatic PII collection
- Next.js: `beforeSend` hook strips sensitive data before transmission
- Both: Environment variables are **never** sent to Sentry

## Testing the Integration

### Test Next.js Integration

1. Start the development server:
   ```bash
   cd marketing
   npm run dev
   ```

2. Navigate to: `http://localhost:3000/sentry-test`

3. Click the test buttons to trigger errors:
   - **Uncaught Error** - Tests global error boundary
   - **Caught Error** - Tests manual error reporting
   - **Info Message** - Tests message tracking

4. Check your Sentry dashboard for the test errors

### Test FastAPI Integration

1. Start the backend server:
   ```bash
   cd backend
   uvicorn api.main:app --host 0.0.0.0 --port 8080
   ```

2. Visit the test endpoint:
   ```bash
   curl http://localhost:8080/debug-sentry
   ```

3. You should see an error response, and the error will appear in Sentry

4. Check your Sentry dashboard under **Issues** or **Events**

### Verification Checklist

- [ ] Error appears in Sentry dashboard within 1 minute
- [ ] Stack trace shows correct file and line numbers
- [ ] Sensitive data (passwords, tokens) is redacted
- [ ] User email/IP is not present in error context
- [ ] Environment is correctly set (development/staging/production)
- [ ] Error grouping works (similar errors group together)

## What Data is Sent to Sentry?

### Included in Error Reports

✅ **Error Information:**
- Exception type and message
- Stack trace with file names and line numbers
- Error severity level
- Timestamp

✅ **Request Context:**
- HTTP method (GET, POST, etc.)
- Request URL (sanitized query params)
- User agent (browser/device info)
- Response status code

✅ **Application Context:**
- Environment (development/staging/production)
- Release version (if configured)
- Server/runtime information
- Performance metrics (duration, traces)

✅ **Breadcrumbs:**
- User actions leading to the error
- Console logs (sanitized)
- Navigation history
- API calls made before error

### Excluded from Error Reports

❌ **PII (Personally Identifiable Information):**
- User emails
- IP addresses
- Phone numbers
- Physical addresses

❌ **Credentials & Secrets:**
- Passwords (form inputs)
- API keys and tokens
- Authorization headers
- Database connection strings
- Environment variable secrets

❌ **Financial Data:**
- Credit card numbers
- Bank account numbers
- Transaction details

## Troubleshooting

### Errors Not Appearing in Sentry

1. **Check DSN is set:**
   ```bash
   # Next.js
   echo $NEXT_PUBLIC_SENTRY_DSN
   
   # FastAPI
   echo $SENTRY_DSN
   ```

2. **Verify initialization:**
   - Next.js: Check browser console for "Sentry initialized" message
   - FastAPI: Check server logs for "Sentry error monitoring initialized"

3. **Check environment:**
   - Make sure `.env.local` exists in `marketing/`
   - Make sure `.env` or environment variables are set for backend

4. **Test with debug mode:**
   - Set `debug: true` in Sentry config (already enabled in development)
   - Check console/logs for Sentry debug output

### Source Maps Not Working

1. Set `SENTRY_AUTH_TOKEN` in environment
2. Set `SENTRY_ORG` and `SENTRY_PROJECT`
3. Run build with source maps enabled:
   ```bash
   npm run build
   ```

### Too Many Events (Quota Exceeded)

1. Lower sample rates in production:
   - `tracesSampleRate: 0.1` (10%)
   - `replaysSessionSampleRate: 0.01` (1%)

2. Add error filtering in `beforeSend`:
   ```typescript
   beforeSend(event, hint) {
     // Ignore specific errors
     if (event.exception?.values?.[0]?.value?.includes('ignore this')) {
       return null;
     }
     return event;
   }
   ```

## Additional Resources

- [Sentry Next.js Documentation](https://docs.sentry.io/platforms/javascript/guides/nextjs/)
- [Sentry Python/FastAPI Documentation](https://docs.sentry.io/platforms/python/guides/fastapi/)
- [Sentry PII and Data Scrubbing](https://docs.sentry.io/platforms/javascript/data-management/sensitive-data/)
- [Sentry Performance Monitoring](https://docs.sentry.io/product/performance/)

## Support

For issues with Sentry integration:
1. Check this setup guide
2. Review Sentry documentation
3. Check Sentry status at [status.sentry.io](https://status.sentry.io)
4. Contact Impact Radar support: support@impactradar.co

---

**Last Updated:** November 18, 2025
