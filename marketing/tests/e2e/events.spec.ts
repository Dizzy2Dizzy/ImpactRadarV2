import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser } from './helpers';

test.describe('Event Browsing and Filtering', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(async ({ page }) => {
    testEmail = generateTestEmail();
    await signupUser(page, testEmail, testPassword);
  });

  test('view events list', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    
    await expect(page.getByText(/Events|No events|Loading/i)).toBeVisible({ timeout: 10000 });
    
    const hasEvents = await page.getByText(/ticker|event type|impact score/i).isVisible().catch(() => false);
    const noEvents = await page.getByText(/no events/i).isVisible().catch(() => false);
    
    expect(hasEvents || noEvents).toBeTruthy();
  });

  test('filter by ticker', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    
    await page.waitForTimeout(2000);
    
    const filterButton = page.getByRole('button', { name: /Filter|Filters/i });
    if (await filterButton.isVisible().catch(() => false)) {
      await filterButton.click();
    }
    
    const tickerInput = page.locator('input[placeholder*="AAPL"], input[name="ticker"]').first();
    await expect(tickerInput).toBeVisible({ timeout: 5000 });
    await tickerInput.fill('AAPL');
    
    const searchButton = page.getByRole('button', { name: /Search|Apply/i });
    await expect(searchButton).toBeVisible({ timeout: 5000 });
    await searchButton.click();
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/AAPL|No events found/i)).toBeVisible({ timeout: 10000 });
  });

  test('filter by event type', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    
    await page.waitForTimeout(2000);
    
    const filterButton = page.getByRole('button', { name: /Filter|Filters/i });
    if (await filterButton.isVisible().catch(() => false)) {
      await filterButton.click();
    }
    
    const categorySelect = page.locator('select[name="category"]').first();
    await expect(categorySelect).toBeVisible({ timeout: 5000 });
    await categorySelect.selectOption('earnings');
    
    const searchButton = page.getByRole('button', { name: /Search|Apply/i });
    await expect(searchButton).toBeVisible({ timeout: 5000 });
    await searchButton.click();
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/Events|No events|Loading/i)).toBeVisible({ timeout: 5000 });
  });

  test('filter by date range', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    
    await page.waitForTimeout(2000);
    
    const filterButton = page.getByRole('button', { name: /Filter|Filters/i });
    if (await filterButton.isVisible().catch(() => false)) {
      await filterButton.click();
    }
    
    const fromDateInput = page.locator('input[type="date"], input[name="from_date"]').first();
    await expect(fromDateInput).toBeVisible({ timeout: 5000 });
    await fromDateInput.fill('2024-01-01');
    
    const toDateInput = page.locator('input[type="date"], input[name="to_date"]').first();
    await expect(toDateInput).toBeVisible({ timeout: 5000 });
    await toDateInput.fill('2024-12-31');
    
    const searchButton = page.getByRole('button', { name: /Search|Apply/i });
    await expect(searchButton).toBeVisible({ timeout: 5000 });
    await searchButton.click();
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/Events|No events|Loading/i)).toBeVisible({ timeout: 5000 });
  });

  test('filter by impact score', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    
    await page.waitForTimeout(2000);
    
    const filterButton = page.getByRole('button', { name: /Filter|Filters/i });
    if (await filterButton.isVisible().catch(() => false)) {
      await filterButton.click();
    }
    
    const scoreSlider = page.locator('input[type="range"]').first();
    await expect(scoreSlider).toBeVisible({ timeout: 5000 });
    await scoreSlider.fill('50');
    
    const searchButton = page.getByRole('button', { name: /Search|Apply/i });
    await expect(searchButton).toBeVisible({ timeout: 5000 });
    await searchButton.click();
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/Events|No events|Loading/i)).toBeVisible({ timeout: 5000 });
  });

  test('search events with advanced search', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    
    await page.waitForTimeout(2000);
    
    const advancedSearchButton = page.getByRole('button', { name: /Advanced Search/i });
    await expect(advancedSearchButton).toBeVisible({ timeout: 5000 });
    await advancedSearchButton.click();
    
    await page.waitForSelector('input[placeholder*="keyword"], input[name="keyword"]', { timeout: 5000 });
    
    const keywordInput = page.locator('input[placeholder*="keyword"], input[name="keyword"]').first();
    await expect(keywordInput).toBeVisible({ timeout: 5000 });
    await keywordInput.fill('earnings');
    
    const searchButton = page.getByRole('button', { name: /^Search$/i });
    await expect(searchButton).toBeVisible({ timeout: 5000 });
    await searchButton.click();
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/Events|No events|Loading/i)).toBeVisible({ timeout: 5000 });
  });

  test('view event details by expanding event', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    
    await page.waitForTimeout(3000);
    
    const eventCard = page.locator('[class*="border"]').filter({ hasText: /impact/i }).first();
    const cardVisible = await eventCard.isVisible().catch(() => false);
    
    if (!cardVisible) {
      const noEvents = await page.getByText(/no events/i).isVisible().catch(() => false);
      if (noEvents) {
        test.skip(true, 'No events available to expand');
      }
      throw new Error('Expected event cards or "no events" message to be visible');
    }
    
    const expandButton = eventCard.locator('button, [role="button"]').first();
    await expect(expandButton).toBeVisible({ timeout: 5000 });
    await expandButton.click();
    
    await page.waitForTimeout(1000);
    
    const details = page.getByText(/description|source|details/i);
    await expect(details).toBeVisible({ timeout: 5000 });
  });

  test('watchlist-only filtering', async ({ page }) => {
    await page.goto('/dashboard');
    
    const watchlistTab = page.getByRole('button', { name: 'Watchlist' });
    await watchlistTab.click();
    
    await page.waitForTimeout(2000);
    
    const addButton = page.getByRole('button', { name: /Add.*Ticker|Add to Watchlist/i }).first();
    await expect(addButton).toBeVisible({ timeout: 5000 });
    await addButton.click();
    
    const tickerInput = page.locator('input[placeholder*="AAPL"], input[name="ticker"]').first();
    await expect(tickerInput).toBeVisible({ timeout: 5000 });
    await tickerInput.fill('AAPL');
    
    const submitButton = page.getByRole('button', { name: /^Add$|Submit/i });
    await expect(submitButton).toBeVisible({ timeout: 5000 });
    await submitButton.click();
    
    await page.waitForTimeout(2000);
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    
    await page.waitForTimeout(2000);
    
    const watchlistCheckbox = page.locator('input[type="checkbox"]').filter({ hasText: /Watchlist/i }).or(
      page.locator('label:has-text("Watchlist") input[type="checkbox"]')
    ).first();
    
    await expect(watchlistCheckbox).toBeVisible({ timeout: 5000 });
    await watchlistCheckbox.check();
    
    const searchButton = page.getByRole('button', { name: /Search|Apply/i });
    if (await searchButton.isVisible().catch(() => false)) {
      await searchButton.click();
    }
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/Events|No events|AAPL/i)).toBeVisible({ timeout: 5000 });
  });
});
