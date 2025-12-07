# E2E Test Suite for ReleaseRadar

This directory contains comprehensive end-to-end tests for the ReleaseRadar frontend using Playwright.

## Setup

### Prerequisites

1. Make sure both the marketing site and backend API are running:
   ```bash
   # The workflows should already be running
   # Marketing site: http://localhost:5000
   # Backend API: http://localhost:8080
   ```

2. Install Playwright browsers (first time only):
   ```bash
   cd marketing
   npx playwright install chromium
   ```

## Running Tests

### Run all tests
```bash
cd marketing
npm run test:e2e
```

### Run tests in UI mode (interactive)
```bash
npm run test:e2e:ui
```

### Run tests in headed mode (see browser)
```bash
npm run test:e2e:headed
```

### Run tests in debug mode
```bash
npm run test:e2e:debug
```

### Run specific test file
```bash
npx playwright test tests/e2e/auth.spec.ts
```

### Run specific test by name
```bash
npx playwright test -g "sign up creates account"
```

## Test Structure

### Test Files

- **`auth.spec.ts`** - Authentication flows (signup, login, errors)
- **`alerts.spec.ts`** - Alert creation and management
- **`portfolio.spec.ts`** - Portfolio CSV upload and validation
- **`dashboard.spec.ts`** - Dashboard tab navigation

### Helper Functions (`helpers.ts`)

- `loginAsUser(page, email, password)` - Login helper
- `signupUser(page, email, password)` - Signup helper
- `generateTestEmail()` - Generate unique test email
- `createTestUserViaAPI(email, password)` - Create user via API
- `cleanupTestUser(email)` - Cleanup test user (optional)

### Test Fixtures (`fixtures/`)

- `sample-portfolio.csv` - Valid portfolio CSV for testing uploads
- `invalid-portfolio.csv` - Invalid portfolio CSV for error testing

## Test Coverage

### Authentication (auth.spec.ts)
- ✅ Sign up creates account and redirects to dashboard
- ✅ Login with existing credentials
- ✅ Login with invalid credentials shows error
- ✅ Signup with weak password shows error
- ✅ Redirect to login when accessing dashboard without auth

### Alerts (alerts.spec.ts)
- ✅ Create alert and verify it appears in UI
- ✅ Alert dialog can be cancelled
- ✅ Alert displays active status correctly

### Portfolio (portfolio.spec.ts)
- ✅ Upload portfolio CSV and see positions
- ✅ Upload invalid CSV shows error
- ✅ Download template CSV works
- ✅ Can delete uploaded portfolio

### Dashboard (dashboard.spec.ts)
- ✅ Navigate dashboard tabs
- ✅ Overview tab shows dashboard content
- ✅ Tabs maintain active state
- ✅ Can navigate between tabs multiple times
- ✅ Dashboard header displays correctly

## Configuration

The test suite is configured in `playwright.config.ts`:

- **Base URL**: http://localhost:5000
- **Timeout**: 30 seconds per test
- **Retries**: 2 on CI, 0 locally
- **Workers**: 3 parallel workers
- **Screenshots**: Captured on failure
- **Video**: Recorded on retry
- **Browser**: Chromium (Desktop Chrome viewport)

## Database Strategy

Tests use the development database and follow these practices:

1. **Unique Test Users**: Each test generates a unique email prefixed with `test_e2e_` to avoid conflicts
2. **Self-Contained**: Tests create their own data and don't depend on pre-existing data
3. **Parallel Safe**: Tests can run in parallel without interfering with each other
4. **Optional Cleanup**: The `cleanupTestUser` helper can be used to clean up test data

## Test Data

Test emails are generated dynamically using:
```typescript
const testEmail = generateTestEmail();
// Returns: test_e2e_1699999999999_1234@example.com
```

This ensures:
- No conflicts between parallel test runs
- Each test is isolated
- Tests can be run multiple times

## Debugging

### View test report after failure
```bash
npx playwright show-report
```

### Run specific test in debug mode
```bash
npx playwright test tests/e2e/auth.spec.ts --debug
```

### Generate trace file
```bash
npx playwright test --trace on
```

## CI/CD Integration

The test suite is configured for CI environments:

- Automatically retries failed tests (2 retries in CI)
- Runs with 3 parallel workers
- Skips browser installation if already present (via `reuseExistingServer`)
- Captures screenshots and videos for debugging failures

## Best Practices

1. **Use helper functions** for common operations (login, signup)
2. **Generate unique test data** to avoid conflicts
3. **Use proper waitFor assertions** instead of hardcoded waits
4. **Keep tests focused** - one test should test one user flow
5. **Clean up after tests** if needed (optional, tests use unique emails)

## Troubleshooting

### Tests timeout
- Ensure marketing site is running on port 5000
- Ensure backend API is running on port 8080
- Increase timeout in `playwright.config.ts` if needed

### Browser not found
- Run `npx playwright install chromium`
- Or use system chromium: `PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 npx playwright test`

### Tests fail randomly
- Check for race conditions in the application
- Ensure proper `waitFor` assertions are used
- Review test isolation (each test should be independent)

### Port already in use
- Make sure only one instance of the marketing site is running
- Check if the webServer configuration in playwright.config.ts has `reuseExistingServer: true`

## Future Enhancements

- Add visual regression tests
- Add API mocking for flaky external dependencies
- Add performance benchmarks
- Add accessibility testing
- Add cross-browser testing (Firefox, Safari)
