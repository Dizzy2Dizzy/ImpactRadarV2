import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser } from '../helpers';
import path from 'path';

test.describe('Golden Path: Portfolio', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(async ({ page }) => {
    testEmail = generateTestEmail();
    await signupUser(page, testEmail, testPassword);
  });

  test('upload CSV portfolio - view holdings - see event exposure', async ({ page }) => {
    await page.goto('/dashboard');
    
    const portfolioTab = page.getByRole('button', { name: 'Portfolio', exact: true }).first();
    await expect(portfolioTab).toBeVisible({ timeout: 5000 });
    await portfolioTab.click();
    
    await page.waitForTimeout(3000);
    
    // Wait for loading to complete - either the loading text disappears or the actual content appears
    await page.waitForFunction(
      () => !document.body.textContent?.includes('Loading portfolio...') || 
            document.body.textContent?.includes('No Portfolio Uploaded') || 
            document.body.textContent?.includes('Portfolio Risk'),
      { timeout: 20000 }
    );
    
    await expect(page.getByText(/No Portfolio Uploaded|Portfolio Risk|Upload/i).first()).toBeVisible({ timeout: 5000 });
    
    // File input is hidden (class="hidden"), accessed via button click
    const fileInput = page.locator('input[type="file"]');
    
    const filePath = path.join(__dirname, '../fixtures', 'sample-portfolio.csv');
    await fileInput.setInputFiles(filePath);
    
    await page.waitForTimeout(3000);
    
    const portfolioLoaded = page.getByText(/AAPL|MSFT|TSLA|positions|holdings/i).first();
    await expect(portfolioLoaded).toBeVisible({ timeout: 15000 });
    
    const hasHoldings = await page.getByText(/AAPL/).isVisible().catch(() => false);
    expect(hasHoldings).toBeTruthy();
    
    const exposureOrEvents = page.getByText(/exposure|event|risk|upcoming/i);
    const hasExposure = await exposureOrEvents.isVisible({ timeout: 5000 }).catch(() => false);
    
    if (hasExposure) {
      const impactOrScore = page.getByText(/impact|score|\$|%/i);
      await expect(impactOrScore).toBeVisible({ timeout: 5000 });
    }
    
    const errorMessage = page.getByText(/error|failed|something went wrong/i);
    await expect(errorMessage).not.toBeVisible();
  });
});
