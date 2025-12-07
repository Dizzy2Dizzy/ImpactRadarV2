import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser } from './helpers';

test.describe('Dashboard Navigation', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(async ({ page }) => {
    testEmail = generateTestEmail();
    await signupUser(page, testEmail, testPassword);
  });

  test('navigate dashboard tabs', async ({ page }) => {
    await page.goto('/dashboard');
    
    await expect(page.getByText('Dashboard')).toBeVisible();
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    await expect(page.getByText(/Events|No events|Loading/i)).toBeVisible({ timeout: 5000 });
    
    const companiesTab = page.getByRole('button', { name: 'Companies' });
    await companiesTab.click();
    await expect(page.getByText(/Companies|No companies|Loading/i)).toBeVisible({ timeout: 5000 });
    
    const watchlistTab = page.getByRole('button', { name: 'Watchlist' });
    await watchlistTab.click();
    await expect(page.getByText(/Watchlist|Add.*ticker|Loading/i)).toBeVisible({ timeout: 5000 });
    
    const portfolioTab = page.getByRole('button', { name: 'Portfolio' });
    await portfolioTab.click();
    await expect(page.getByText(/Portfolio|Upload|Loading/i)).toBeVisible({ timeout: 5000 });
    
    const scannersTab = page.getByRole('button', { name: /Scanner/i });
    await scannersTab.click();
    await expect(page.getByText(/Scanner|Status|Loading/i)).toBeVisible({ timeout: 5000 });
    
    const alertsTab = page.getByRole('button', { name: 'Alerts' });
    await alertsTab.click();
    await expect(page.getByText(/Alerts|Create Alert|Loading/i)).toBeVisible({ timeout: 5000 });
  });

  test('overview tab shows dashboard content', async ({ page }) => {
    await page.goto('/dashboard');
    
    const overviewTab = page.getByRole('button', { name: 'Overview' });
    await overviewTab.click();
    
    await expect(page.getByText(/Welcome|Recent|Activity|Events/i)).toBeVisible({ timeout: 5000 });
  });

  test('tabs maintain active state', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    await eventsTab.click();
    
    await expect(eventsTab).toHaveClass(/text-\[--primary\]/);
  });

  test('can navigate between tabs multiple times', async ({ page }) => {
    await page.goto('/dashboard');
    
    const eventsTab = page.getByRole('button', { name: 'Events' });
    const portfolioTab = page.getByRole('button', { name: 'Portfolio' });
    
    await eventsTab.click();
    await expect(page.getByText(/Events|No events|Loading/i)).toBeVisible({ timeout: 5000 });
    
    await portfolioTab.click();
    await expect(page.getByText(/Portfolio|Upload|Loading/i)).toBeVisible({ timeout: 5000 });
    
    await eventsTab.click();
    await expect(page.getByText(/Events|No events|Loading/i)).toBeVisible({ timeout: 5000 });
  });

  test('dashboard header displays correctly', async ({ page }) => {
    await page.goto('/dashboard');
    
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
    await expect(page.getByText(/Welcome to Impact Radar/i)).toBeVisible();
  });
});
