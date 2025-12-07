import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser } from './helpers';

test.describe('Alert Creation', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(async ({ page }) => {
    testEmail = generateTestEmail();
    await signupUser(page, testEmail, testPassword);
  });

  test('create alert and verify it appears in UI', async ({ page }) => {
    await page.goto('/dashboard');
    
    const alertsTab = page.getByRole('button', { name: 'Alerts' });
    await alertsTab.click();
    
    await expect(page.getByText(/Create Alert|No alerts configured/i)).toBeVisible({ timeout: 5000 });
    
    const createButton = page.getByRole('button', { name: /Create Alert|Create Your First Alert/i });
    await createButton.click();
    
    await page.waitForSelector('[placeholder*="High Impact"]', { timeout: 5000 });
    
    await page.fill('input[type="text"]', 'Test AAPL Alert');
    
    const scoreSlider = page.locator('input[type="range"]');
    await scoreSlider.fill('70');
    
    const tickerInput = page.locator('input[placeholder*="AAPL"]');
    await tickerInput.fill('AAPL');
    await page.getByRole('button', { name: 'Add' }).first().click();
    
    const emailCheckbox = page.locator('input[type="checkbox"]').filter({ hasText: /Email/i }).or(
      page.locator('label:has-text("Email") input[type="checkbox"]')
    );
    if (await emailCheckbox.count() > 0) {
      await emailCheckbox.check();
    }
    
    const submitButton = page.getByRole('button', { name: /^Create Alert$/i });
    await submitButton.click();
    
    await expect(page.getByText('Test AAPL Alert')).toBeVisible({ timeout: 10000 });
    await expect(page.getByText(/AAPL/)).toBeVisible();
    await expect(page.getByText(/70/)).toBeVisible();
  });

  test('alert dialog can be cancelled', async ({ page }) => {
    await page.goto('/dashboard');
    
    const alertsTab = page.getByRole('button', { name: 'Alerts' });
    await alertsTab.click();
    
    const createButton = page.getByRole('button', { name: /Create Alert|Create Your First Alert/i });
    await createButton.click();
    
    await page.waitForSelector('[placeholder*="High Impact"]', { timeout: 5000 });
    
    const cancelButton = page.getByRole('button', { name: 'Cancel' });
    await cancelButton.click();
    
    await expect(page.locator('[placeholder*="High Impact"]')).not.toBeVisible();
  });

  test('alert displays active status correctly', async ({ page }) => {
    await page.goto('/dashboard');
    
    const alertsTab = page.getByRole('button', { name: 'Alerts' });
    await alertsTab.click();
    
    const createButton = page.getByRole('button', { name: /Create Alert|Create Your First Alert/i });
    await createButton.click();
    
    await page.waitForSelector('[placeholder*="High Impact"]', { timeout: 5000 });
    
    await page.fill('input[type="text"]', 'Active Alert Test');
    
    const submitButton = page.getByRole('button', { name: /^Create Alert$/i });
    await submitButton.click();
    
    await expect(page.getByText(/Active/i)).toBeVisible({ timeout: 10000 });
  });
});
