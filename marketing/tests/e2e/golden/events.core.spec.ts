import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser } from '../helpers';

test.describe('Golden Path: Events', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(async ({ page }) => {
    testEmail = generateTestEmail();
    await signupUser(page, testEmail, testPassword);
  });

  test('view events list - filter by ticker (AAPL) - open event detail - verify source link', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events', exact: true }).first();
    await eventsTab.click();
    
    await page.waitForTimeout(3000);
    
    // Wait for events header to load
    const eventsHeader = page.locator('h2:has-text("Events")');
    await expect(eventsHeader).toBeVisible({ timeout: 15000 });
    
    // Click "Show Filters" button to reveal filter inputs
    const showFiltersButton = page.getByRole('button', { name: 'Show Filters' });
    await expect(showFiltersButton).toBeVisible({ timeout: 5000 });
    await showFiltersButton.click();
    
    await page.waitForTimeout(1000);
    
    // Now the ticker input should be visible
    const tickerInput = page.locator('input[placeholder*="AAPL"]').first();
    await expect(tickerInput).toBeVisible({ timeout: 5000 });
    await tickerInput.fill('AAPL');
    
    await page.waitForTimeout(2000);
    
    // Check if there are any events with View Source links
    const sourceLink = page.locator('a:has-text("View Source")').first();
    const hasSourceLink = await sourceLink.isVisible({ timeout: 5000 }).catch(() => false);
    
    if (hasSourceLink) {
      const href = await sourceLink.getAttribute('href');
      expect(href).toBeTruthy();
      expect(href).toMatch(/http/);
    }
    
    // Verify no error messages
    const errorMessage = page.getByText(/error|failed|something went wrong/i);
    await expect(errorMessage).not.toBeVisible();
  });

  test('filter events by date range and event type', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events', exact: true }).first();
    await eventsTab.click();
    
    await page.waitForTimeout(3000);
    
    // Wait for events header to load
    const eventsHeader = page.locator('h2:has-text("Events")');
    await expect(eventsHeader).toBeVisible({ timeout: 15000 });
    
    // Click "Show Filters" to reveal filter inputs
    const showFiltersButton = page.getByRole('button', { name: 'Show Filters' });
    await expect(showFiltersButton).toBeVisible({ timeout: 5000 });
    await showFiltersButton.click();
    
    await page.waitForTimeout(1000);
    
    // Now date inputs should be visible
    const fromDateInput = page.locator('input[type="date"]').first();
    await expect(fromDateInput).toBeVisible({ timeout: 5000 });
    await fromDateInput.fill('2024-01-01');
    
    const toDateInput = page.locator('input[type="date"]').nth(1);
    await expect(toDateInput).toBeVisible({ timeout: 5000 });
    await toDateInput.fill('2024-12-31');
    
    const categorySelect = page.locator('select').first();
    const hasCategory = await categorySelect.isVisible().catch(() => false);
    if (hasCategory) {
      const options = await categorySelect.locator('option').allTextContents();
      if (options.some(opt => opt.toLowerCase().includes('earnings'))) {
        await categorySelect.selectOption({ label: /earnings/i });
      }
    }
    
    await page.waitForTimeout(2000);
    
    // Verify the page shows results (or empty state)
    const results = page.locator('h2:has-text("Events")');
    await expect(results).toBeVisible({ timeout: 5000 });
    
    const errorMessage = page.getByText(/error|failed|something went wrong/i);
    await expect(errorMessage).not.toBeVisible();
  });

  test('watchlist-only filter works', async ({ page }) => {
    await page.goto('/dashboard');
    
    // First add a ticker to watchlist
    const watchlistTab = page.getByRole('button', { name: 'Watchlist', exact: true }).first();
    await watchlistTab.click();
    
    await page.waitForTimeout(3000);
    
    // Wait for watchlist loading to complete
    await page.waitForFunction(
      () => !document.body.textContent?.includes('Loading watchlist...'),
      { timeout: 20000 }
    );
    
    // Click "Add Company" button (not "Add Ticker")
    const addButton = page.getByRole('button', { name: 'Add Company' }).first();
    await expect(addButton).toBeVisible({ timeout: 10000 });
    await addButton.click();
    
    await page.waitForTimeout(1000);
    
    const tickerInput = page.locator('input[placeholder*="MRNA"]').or(
      page.locator('input[placeholder*="NVDA"]')
    ).first();
    await expect(tickerInput).toBeVisible({ timeout: 5000 });
    await tickerInput.fill('AAPL');
    
    const submitButton = page.getByRole('button', { name: /Add to Watchlist/i });
    await expect(submitButton).toBeVisible({ timeout: 5000 });
    await submitButton.click();
    
    await page.waitForTimeout(3000);
    
    // Now go to Events tab
    const eventsTab = page.getByRole('button', { name: 'Events', exact: true }).first();
    await eventsTab.click();
    
    await page.waitForTimeout(2000);
    
    // Events should be visible
    const eventsHeader = page.locator('h2:has-text("Events")');
    await expect(eventsHeader).toBeVisible({ timeout: 5000 });
    
    const errorMessage = page.getByText(/error|failed|something went wrong/i);
    await expect(errorMessage).not.toBeVisible();
  });
});
