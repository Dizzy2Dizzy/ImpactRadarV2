import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser, loginAsUser } from './helpers';

test.describe('Authentication Flows', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(() => {
    testEmail = generateTestEmail();
  });

  test('sign up creates account and redirects to dashboard', async ({ page }) => {
    await page.goto('/signup');
    
    await page.fill('[name="email"]', testEmail);
    await page.fill('[name="password"]', testPassword);
    
    await page.click('button[type="submit"]');
    
    await page.waitForURL('/dashboard', { timeout: 10000 });
    
    expect(page.url()).toContain('/dashboard');
    
    const cookies = await page.context().cookies();
    const sessionCookie = cookies.find(c => c.name === 'session');
    expect(sessionCookie).toBeDefined();
    
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });

  test('login with existing credentials redirects to dashboard', async ({ page }) => {
    await signupUser(page, testEmail, testPassword);
    
    await page.goto('/login');
    
    await page.fill('[name="email"]', testEmail);
    await page.fill('[name="password"]', testPassword);
    
    await page.click('button[type="submit"]');
    
    await page.waitForURL('/dashboard', { timeout: 10000 });
    
    expect(page.url()).toContain('/dashboard');
    await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible();
  });

  test('login with invalid credentials shows error', async ({ page }) => {
    await signupUser(page, testEmail, testPassword);
    
    await page.goto('/login');
    
    await page.fill('[name="email"]', testEmail);
    await page.fill('[name="password"]', 'WrongPassword123!');
    
    await page.click('button[type="submit"]');
    
    await expect(page.getByText(/Login failed|Invalid credentials|error/i)).toBeVisible({ timeout: 5000 });
    
    expect(page.url()).not.toContain('/dashboard');
  });

  test('signup with weak password shows error', async ({ page }) => {
    await page.goto('/signup');
    
    await page.fill('[name="email"]', testEmail);
    await page.fill('[name="password"]', 'weak');
    
    await page.click('button[type="submit"]');
    
    await expect(page.locator('.bg-red-500\\/10').getByText(/at least 8 characters/i)).toBeVisible({ timeout: 5000 });
  });

  test('redirect to login when accessing dashboard without auth', async ({ page }) => {
    await page.goto('/dashboard');
    
    await page.waitForURL('/login', { timeout: 10000 });
    
    expect(page.url()).toContain('/login');
  });
});
