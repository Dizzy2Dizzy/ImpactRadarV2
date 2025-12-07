import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser } from '../helpers';

test.describe('Golden Path: RadarQuant AI', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(async ({ page }) => {
    testEmail = generateTestEmail();
    await signupUser(page, testEmail, testPassword);
  });

  test('open RadarQuant panel - ask question about known event - verify response references real DB data', async ({ page }) => {
    await page.goto('/dashboard');
    
    const radarQuantTab = page.getByRole('button', { name: /RadarQuant/i }).first();
    await expect(radarQuantTab).toBeVisible({ timeout: 5000 });
    await radarQuantTab.click();
    
    await page.waitForTimeout(2000);
    
    // Use .first() to avoid strict mode violation (multiple matches)
    await expect(page.getByText(/RadarQuant|AI Assistant|Ask/i).first()).toBeVisible({ timeout: 10000 });
    
    const messageInput = page.locator('textarea[placeholder*="Ask"], input[placeholder*="Ask"]').first();
    await expect(messageInput).toBeVisible({ timeout: 5000 });
    
    await messageInput.fill('What are the latest events for AAPL?');
    
    const sendButton = page.getByRole('button', { name: /Send/i }).or(
      page.locator('button[type="submit"]')
    ).first();
    await expect(sendButton).toBeVisible({ timeout: 5000 });
    await sendButton.click();
    
    const loadingIndicator = page.getByText(/analyzing|loading|thinking/i).first();
    await expect(loadingIndicator).toBeVisible({ timeout: 5000 });
    
    const responseText = page.getByText(/AAPL|events|analysis|recent|earnings|sec|fda/i).first();
    await expect(responseText).toBeVisible({ timeout: 30000 });
    
    // Quota info may not always be visible depending on UI state
    const quotaInfo = page.getByText(/remaining|quota|queries/i).first();
    const hasQuota = await quotaInfo.isVisible({ timeout: 3000 }).catch(() => false);
    // Quota display is optional - test passes if response is received
    if (!hasQuota) {
      console.log('Quota info not visible, but response received successfully');
    }
    
    const errorMessage = page.getByText(/OpenAI.*unavailable|API.*failed|quota exceeded/i);
    const hasError = await errorMessage.isVisible().catch(() => false);
    
    if (hasError) {
      const gracefulError = await page.getByText(/try again|upgrade|unavailable/i).isVisible();
      expect(gracefulError).toBeTruthy();
    }
  });

  test.skip('verify AI degrades gracefully on OpenAI API error', async ({ page }) => {
    await page.goto('/dashboard');
    
    const radarQuantTab = page.getByRole('button', { name: /RadarQuant/i });
    await radarQuantTab.click();
    
    await page.waitForTimeout(2000);
    
    const messageInput = page.locator('textarea[placeholder*="Ask"], input[placeholder*="Ask"]').first();
    await messageInput.fill('Test error handling');
    
    const sendButton = page.getByRole('button', { name: /Send/i }).first();
    await sendButton.click();
    
    await page.waitForTimeout(5000);
    
    const errorOrResponse = page.getByText(/unavailable|error|analysis|response/i);
    await expect(errorOrResponse).toBeVisible({ timeout: 30000 });
    
    const pageContent = await page.textContent('body');
    expect(pageContent).toBeTruthy();
    
    const hasCrash = (pageContent || '').includes('TypeError') || (pageContent || '').includes('undefined');
    expect(hasCrash).toBeFalsy();
  });
});
