import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser } from './helpers';

test.describe('Watchlist Management', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(async ({ page }) => {
    testEmail = generateTestEmail();
    await signupUser(page, testEmail, testPassword);
  });

  test('add ticker to watchlist', async ({ page }) => {
    await page.goto('/dashboard');
    
    const watchlistTab = page.getByRole('button', { name: 'Watchlist' });
    await watchlistTab.click();
    
    await expect(page.getByText(/Watchlist|Add.*ticker|Loading/i)).toBeVisible({ timeout: 5000 });
    
    const addButton = page.getByRole('button', { name: /Add.*Ticker|Add to Watchlist/i }).first();
    await addButton.click();
    
    await page.waitForSelector('input[placeholder*="AAPL"], input[name="ticker"]', { timeout: 5000 });
    
    const tickerInput = page.locator('input[placeholder*="AAPL"], input[name="ticker"]').first();
    await tickerInput.fill('AAPL');
    
    const submitButton = page.getByRole('button', { name: /^Add$|Submit/i });
    await submitButton.click();
    
    await expect(page.getByText(/AAPL|Apple/i)).toBeVisible({ timeout: 15000 });
  });

  test('remove ticker from watchlist', async ({ page }) => {
    await page.goto('/dashboard');
    
    const watchlistTab = page.getByRole('button', { name: 'Watchlist' });
    await watchlistTab.click();
    
    await page.waitForTimeout(2000);
    
    const addButton = page.getByRole('button', { name: /Add.*Ticker|Add to Watchlist/i }).first();
    await addButton.click();
    
    const tickerInput = page.locator('input[placeholder*="AAPL"], input[name="ticker"]').first();
    await tickerInput.fill('MSFT');
    
    const submitButton = page.getByRole('button', { name: /^Add$|Submit/i });
    await submitButton.click();
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/MSFT|Microsoft/i)).toBeVisible({ timeout: 15000 });
    
    const removeButton = page.getByRole('button', { name: /Remove|Delete/i }).first();
    await removeButton.click();
    
    await page.waitForTimeout(2000);
    
    const tickerStillVisible = await page.getByText(/MSFT/).isVisible().catch(() => false);
    expect(tickerStillVisible).toBeFalsy();
  });

  test('view watchlist events', async ({ page }) => {
    await page.goto('/dashboard');
    
    const watchlistTab = page.getByRole('button', { name: 'Watchlist' });
    await watchlistTab.click();
    
    await page.waitForTimeout(2000);
    
    const addButton = page.getByRole('button', { name: /Add.*Ticker|Add to Watchlist/i }).first();
    await addButton.click();
    
    const tickerInput = page.locator('input[placeholder*="AAPL"], input[name="ticker"]').first();
    await tickerInput.fill('AAPL');
    
    const submitButton = page.getByRole('button', { name: /^Add$|Submit/i });
    await submitButton.click();
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/AAPL|Upcoming Events|No upcoming events/i)).toBeVisible({ timeout: 10000 });
    
    const hasEvents = await page.getByText(/event|upcoming/i).isVisible().catch(() => false);
    expect(hasEvents).toBeTruthy();
  });

  test('invalid ticker validation', async ({ page }) => {
    await page.goto('/dashboard');
    
    const watchlistTab = page.getByRole('button', { name: 'Watchlist' });
    await watchlistTab.click();
    
    await page.waitForTimeout(2000);
    
    const addButton = page.getByRole('button', { name: /Add.*Ticker|Add to Watchlist/i }).first();
    await addButton.click();
    
    const tickerInput = page.locator('input[placeholder*="AAPL"], input[name="ticker"]').first();
    await tickerInput.fill('INVALIDTICKER12345');
    
    const submitButton = page.getByRole('button', { name: /^Add$|Submit/i });
    await submitButton.click();
    
    await expect(page.getByText(/not found|invalid|error/i)).toBeVisible({ timeout: 10000 });
  });

  test('duplicate ticker prevention', async ({ page }) => {
    await page.goto('/dashboard');
    
    const watchlistTab = page.getByRole('button', { name: 'Watchlist' });
    await watchlistTab.click();
    
    await page.waitForTimeout(2000);
    
    const addButton = page.getByRole('button', { name: /Add.*Ticker|Add to Watchlist/i }).first();
    await addButton.click();
    
    let tickerInput = page.locator('input[placeholder*="AAPL"], input[name="ticker"]').first();
    await tickerInput.fill('AAPL');
    
    let submitButton = page.getByRole('button', { name: /^Add$|Submit/i });
    await submitButton.click();
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/AAPL/i)).toBeVisible({ timeout: 15000 });
    
    const addButtonAgain = page.getByRole('button', { name: /Add.*Ticker|Add to Watchlist/i }).first();
    await addButtonAgain.click();
    
    tickerInput = page.locator('input[placeholder*="AAPL"], input[name="ticker"]').first();
    await tickerInput.fill('AAPL');
    
    submitButton = page.getByRole('button', { name: /^Add$|Submit/i });
    await submitButton.click();
    
    await expect(page.getByText(/already.*watchlist|duplicate/i)).toBeVisible({ timeout: 10000 });
  });
});
