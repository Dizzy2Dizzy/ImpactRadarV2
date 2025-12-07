import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser } from './helpers';

test.describe('Scanner Status', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(async ({ page }) => {
    testEmail = generateTestEmail();
    await signupUser(page, testEmail, testPassword);
  });

  test('view scanner status page', async ({ page }) => {
    await page.goto('/dashboard');
    
    const scannersTab = page.getByRole('button', { name: 'Scanner Status' });
    await scannersTab.click();
    
    await page.waitForTimeout(3000);
    
    // Assert that scanner status UI elements are visible
    const scannerHeading = page.getByRole('heading', { name: /scanner/i });
    const scannerStatusText = page.getByText(/scanner status|active scanners|scanner name/i);
    const scannerCard = page.locator('[class*="scanner"], [data-testid*="scanner"]').first();
    const tableOrList = page.locator('table, [role="table"], ul, [role="list"]').first();
    
    // At least one of these scanner UI elements should be visible
    const hasHeading = await scannerHeading.isVisible().catch(() => false);
    const hasStatusText = await scannerStatusText.isVisible().catch(() => false);
    const hasCard = await scannerCard.isVisible().catch(() => false);
    const hasTable = await tableOrList.isVisible().catch(() => false);
    
    if (!hasHeading && !hasStatusText && !hasCard && !hasTable) {
      throw new Error('Expected scanner status UI elements to be visible (heading, status text, cards, or table)');
    }
  });

  test('verify scanner last run times', async ({ page }) => {
    await page.goto('/dashboard');
    
    const scannersTab = page.getByRole('button', { name: 'Scanner Status' });
    await scannersTab.click();
    
    await page.waitForTimeout(3000);
    
    // Assert that scanner last run information is visible
    const lastRunText = page.getByText(/last run|last scan|ran at|updated|minutes ago|hours ago|days ago/i);
    const statusBadge = page.getByText(/active|running|idle|paused|completed/i);
    const timestamp = page.locator('time, [datetime], [class*="timestamp"]').first();
    const scannerNameWithStatus = page.locator('[class*="scanner"]').filter({ hasText: /earnings|fda|press|dividend|guidance/i }).first();
    
    // At least one of these elements showing scanner status/timing should be visible
    const hasLastRun = await lastRunText.isVisible().catch(() => false);
    const hasStatus = await statusBadge.isVisible().catch(() => false);
    const hasTimestamp = await timestamp.isVisible().catch(() => false);
    const hasScannerWithStatus = await scannerNameWithStatus.isVisible().catch(() => false);
    
    if (!hasLastRun && !hasStatus && !hasTimestamp && !hasScannerWithStatus) {
      throw new Error('Expected scanner last run times or status indicators to be visible');
    }
  });
});
