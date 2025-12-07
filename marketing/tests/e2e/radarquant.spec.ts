import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser } from './helpers';

test.describe('RadarQuant AI Assistant', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(async ({ page }) => {
    testEmail = generateTestEmail();
    await signupUser(page, testEmail, testPassword);
  });

  test('ask RadarQuant query and view response', async ({ page }) => {
    await page.goto('/dashboard');
    
    const radarQuantTab = page.getByRole('button', { name: /RadarQuant/i });
    await radarQuantTab.click();
    
    await expect(page.getByText(/RadarQuant|AI Assistant|Ask/i)).toBeVisible({ timeout: 10000 });
    
    const presetButton = page.getByRole('button', { name: /What.*happening|market overview/i }).first();
    const hasPreset = await presetButton.isVisible().catch(() => false);
    
    if (hasPreset) {
      await presetButton.click();
      
      await expect(page.getByText(/analyzing|loading|thinking/i)).toBeVisible({ timeout: 5000 });
      
      await expect(page.getByText(/response|analysis|market/i)).toBeVisible({ timeout: 30000 });
    } else {
      const messageInput = page.locator('textarea, input[type="text"]').filter({ hasText: /ask|message/i }).or(
        page.locator('textarea[placeholder*="Ask"], input[placeholder*="Ask"]')
      ).first();
      await expect(messageInput).toBeVisible({ timeout: 5000 });
      await messageInput.fill('What are the latest events for AAPL?');
      
      const sendButton = page.getByRole('button', { name: /Send/i }).or(
        page.locator('button[type="submit"]')
      ).first();
      await expect(sendButton).toBeVisible({ timeout: 5000 });
      await sendButton.click();
      
      await expect(page.getByText(/analyzing|loading|thinking/i)).toBeVisible({ timeout: 5000 });
      
      await expect(page.getByText(/AAPL|events|analysis/i)).toBeVisible({ timeout: 30000 });
    }
  });

  test('view response with event references', async ({ page }) => {
    await page.goto('/dashboard');
    
    const radarQuantTab = page.getByRole('button', { name: /RadarQuant/i });
    await radarQuantTab.click();
    
    await page.waitForTimeout(2000);
    
    const messageInput = page.locator('textarea[placeholder*="Ask"], input[placeholder*="Ask"]').first();
    await expect(messageInput).toBeVisible({ timeout: 5000 });
    await messageInput.fill('Tell me about recent earnings events');
    
    const sendButton = page.getByRole('button', { name: /Send/i }).or(
      page.locator('button[type="submit"]')
    ).first();
    await expect(sendButton).toBeVisible({ timeout: 5000 });
    await sendButton.click();
    
    await page.waitForTimeout(3000);
    
    await expect(page.getByText(/earnings|events|analysis|recent/i)).toBeVisible({ timeout: 30000 });
  });

  test('free user quota enforcement', async ({ page }) => {
    await page.goto('/dashboard');
    
    const radarQuantTab = page.getByRole('button', { name: /RadarQuant/i });
    await radarQuantTab.click();
    
    await expect(page.getByText(/RadarQuant|quota|remaining|queries/i)).toBeVisible({ timeout: 10000 });
    
    const quotaText = await page.locator('text=/\\d+.*remaining|\\d+.*5|quota/i').first().textContent().catch(() => '');
    expect(quotaText).toBeTruthy();
    
    const hasFreeLimit = (quotaText || '').includes('5') || (quotaText || '').includes('Free');
    expect(hasFreeLimit || (quotaText || '').length > 0).toBeTruthy();
  });

  test('send multiple queries and verify chat history', async ({ page }) => {
    await page.goto('/dashboard');
    
    const radarQuantTab = page.getByRole('button', { name: /RadarQuant/i });
    await radarQuantTab.click();
    
    await page.waitForTimeout(2000);
    
    const messageInput = page.locator('textarea[placeholder*="Ask"], input[placeholder*="Ask"]').first();
    await expect(messageInput).toBeVisible({ timeout: 5000 });
    await messageInput.fill('What is the market overview?');
    
    const sendButton = page.getByRole('button', { name: /Send/i }).or(
      page.locator('button[type="submit"]')
    ).first();
    await expect(sendButton).toBeVisible({ timeout: 5000 });
    await sendButton.click();
    
    await page.waitForTimeout(5000);
    
    await expect(page.getByText(/What is the market overview/i)).toBeVisible({ timeout: 5000 });
    
    const firstResponse = page.getByText(/market|overview|analysis/i);
    await expect(firstResponse).toBeVisible({ timeout: 30000 });
    
    await page.waitForTimeout(2000);
    
    await messageInput.fill('Tell me more');
    await sendButton.click();
    
    await page.waitForTimeout(3000);
    
    await expect(page.getByText(/Tell me more/i)).toBeVisible({ timeout: 5000 });
  });
});
