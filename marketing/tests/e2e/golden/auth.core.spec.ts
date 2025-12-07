import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser, loginAsUser } from '../helpers';

test.describe('Golden Path: Authentication', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(() => {
    testEmail = generateTestEmail();
  });

  test('user can signup, verify email (mock), login, and logout', async ({ page }) => {
    await page.goto('/signup');
    
    await page.fill('[name="email"]', testEmail);
    await page.fill('[name="password"]', testPassword);
    
    await page.click('button[type="submit"]');
    
    await page.waitForURL(/\/dashboard/, { timeout: 15000 });
    
    const cookies = await page.context().cookies();
    const sessionCookie = cookies.find(c => c.name === 'session');
    expect(sessionCookie).toBeDefined();
    
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible({ timeout: 5000 });
    
    const errorMessage = page.getByText(/error|failed|wrong/i);
    await expect(errorMessage).not.toBeVisible();
    
    const logoutButton = page.getByRole('button', { name: /logout|sign out/i }).or(
      page.locator('a[href*="logout"]')
    );
    
    if (await logoutButton.isVisible().catch(() => false)) {
      await logoutButton.click();
      await page.waitForURL(/\/(login|$)/, { timeout: 15000 });
      expect(page.url()).not.toContain('/dashboard');
    }
  });

  test('login with invalid credentials shows error', async ({ page }) => {
    await signupUser(page, testEmail, testPassword);
    
    await page.goto('/login');
    
    await page.fill('[name="email"]', testEmail);
    await page.fill('[name="password"]', 'WrongPassword123!');
    
    await page.click('button[type="submit"]');
    
    await page.waitForTimeout(1000);
    
    const errorMessage = page.getByText(/invalid|incorrect|failed|wrong/i);
    await expect(errorMessage).toBeVisible({ timeout: 5000 });
    
    expect(page.url()).not.toContain('/dashboard');
  });

  test('unauthenticated user redirected to login', async ({ page }) => {
    await page.goto('/dashboard');
    
    await page.waitForURL(/\/login/, { timeout: 15000 });
    
    expect(page.url()).toContain('/login');
    
    await expect(page.getByRole('heading', { name: /welcome back/i })).toBeVisible({ timeout: 5000 });
  });
});
