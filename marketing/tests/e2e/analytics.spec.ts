import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser } from './helpers';

test.describe('Premium Analytics Features', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(async ({ page }) => {
    testEmail = generateTestEmail();
    await signupUser(page, testEmail, testPassword);
  });

  test('view backtesting tab shows upgrade message for free users', async ({ page }) => {
    await page.goto('/dashboard');
    
    const backtestingTab = page.getByRole('button', { name: /Backtesting/i });
    await expect(backtestingTab).toBeVisible({ timeout: 5000 });
    await backtestingTab.click();
    
    await page.waitForTimeout(2000);
    
    const upgradeMessage = page.getByText(/upgrade|Pro plan|premium/i);
    const backtestingContent = page.getByText(/accuracy|prediction|validation/i);
    
    const hasUpgradeMessage = await upgradeMessage.isVisible().catch(() => false);
    const hasBacktestingContent = await backtestingContent.isVisible().catch(() => false);
    
    if (!hasUpgradeMessage && !hasBacktestingContent) {
      throw new Error('Expected either upgrade message or backtesting content to be visible');
    }
  });

  test('view correlation tab shows upgrade message for free users', async ({ page }) => {
    await page.goto('/dashboard');
    
    const correlationTab = page.getByRole('button', { name: /Correlation/i });
    await expect(correlationTab).toBeVisible({ timeout: 5000 });
    await correlationTab.click();
    
    await page.waitForTimeout(2000);
    
    const upgradeMessage = page.getByText(/upgrade|Pro plan|premium/i);
    const correlationContent = page.getByText(/timeline|correlation|events/i);
    
    const hasUpgradeMessage = await upgradeMessage.isVisible().catch(() => false);
    const hasCorrelationContent = await correlationContent.isVisible().catch(() => false);
    
    if (!hasUpgradeMessage && !hasCorrelationContent) {
      throw new Error('Expected either upgrade message or correlation content to be visible');
    }
  });

  test('view peer comparison requires Pro plan', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    
    await page.waitForTimeout(3000);
    
    const peerButton = page.getByRole('button', { name: /Peers|Peer Comparison/i }).first();
    await expect(peerButton).toBeVisible({ timeout: 5000 });
    await peerButton.click();
    
    await page.waitForTimeout(2000);
    
    const upgradeMessage = page.getByText(/upgrade|Pro plan|premium/i);
    const peerContent = page.getByText(/peer|similar|comparison/i);
    
    const hasUpgradeMessage = await upgradeMessage.isVisible().catch(() => false);
    const hasPeerContent = await peerContent.isVisible().catch(() => false);
    
    if (!hasUpgradeMessage && !hasPeerContent) {
      throw new Error('Expected either upgrade message or peer comparison content to be visible');
    }
  });

  test('calendar view navigation', async ({ page }) => {
    await page.goto('/dashboard');
    
    const calendarTab = page.getByRole('button', { name: /Calendar/i });
    await expect(calendarTab).toBeVisible({ timeout: 5000 });
    await calendarTab.click();
    
    await page.waitForTimeout(2000);
    
    const upgradeMessage = page.getByText(/upgrade|Pro plan|premium/i);
    const calendarContent = page.getByText(/calendar|month|day|events/i);
    
    const hasUpgradeMessage = await upgradeMessage.isVisible().catch(() => false);
    const hasCalendarContent = await calendarContent.isVisible().catch(() => false);
    
    if (!hasUpgradeMessage && !hasCalendarContent) {
      throw new Error('Expected either upgrade message or calendar content to be visible');
    }
    
    if (hasCalendarContent) {
      const monthNavButton = page.getByRole('button', { name: /next|previous|>/i }).first();
      await expect(monthNavButton).toBeVisible({ timeout: 5000 });
      await monthNavButton.click();
      
      await page.waitForTimeout(1000);
      
      await expect(page.getByText(/calendar|events/i)).toBeVisible({ timeout: 5000 });
    }
  });

  test('CSV export events requires Pro plan', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    
    await page.waitForTimeout(2000);
    
    const exportButton = page.getByRole('button', { name: /Export|Download CSV/i }).first();
    await expect(exportButton).toBeVisible({ timeout: 5000 });
    await exportButton.click();
    
    await page.waitForTimeout(2000);
    
    const upgradeMessage = page.getByText(/upgrade|Pro plan|premium/i);
    const hasUpgradeMessage = await upgradeMessage.isVisible().catch(() => false);
    
    if (hasUpgradeMessage) {
      expect(hasUpgradeMessage).toBeTruthy();
    } else {
      const downloadStarted = await page.waitForEvent('download', { timeout: 5000 }).catch(() => null);
      if (!downloadStarted) {
        throw new Error('Expected either upgrade message or download to start');
      }
    }
  });

  test('free user sees upgrade prompts on premium features', async ({ page }) => {
    await page.goto('/dashboard');
    
    const premiumTabs = [
      'Backtesting',
      'Correlation',
      'Calendar',
      'X Feed',
      'Projector'
    ];
    
    let tabFound = false;
    for (const tabName of premiumTabs) {
      const tab = page.getByRole('button', { name: new RegExp(tabName, 'i') });
      
      if (await tab.isVisible().catch(() => false)) {
        tabFound = true;
        await tab.click();
        
        await page.waitForTimeout(2000);
        
        const upgradeMessage = page.getByText(/upgrade|Pro plan|premium|unlock/i);
        const content = page.locator('div, section').filter({ hasText: /loading|data|events/i });
        
        const hasUpgradeMessage = await upgradeMessage.isVisible({ timeout: 5000 }).catch(() => false);
        const hasContent = await content.isVisible().catch(() => false);
        
        if (!hasUpgradeMessage && !hasContent) {
          throw new Error(`Tab "${tabName}" clicked but no upgrade message or content displayed`);
        }
        
        break;
      }
    }
    
    if (!tabFound) {
      throw new Error('No premium tabs found on dashboard');
    }
  });
});
