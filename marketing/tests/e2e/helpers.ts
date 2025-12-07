import { Page } from '@playwright/test';

/**
 * Dismiss cookie consent banner if present.
 * This banner appears after 1 second and blocks all page interactions.
 */
export async function dismissCookieConsent(page: Page) {
  // Set cookie consent in localStorage before page loads to prevent banner
  await page.addInitScript(() => {
    localStorage.setItem('cookie-consent', JSON.stringify({
      necessary: true,
      analytics: false,
      marketing: false,
    }));
    localStorage.setItem('cookie-consent-date', new Date().toISOString());
  });
}

export async function loginAsUser(page: Page, email: string, password: string) {
  await dismissCookieConsent(page);
  await page.goto('/login');
  await page.fill('[name="email"]', email);
  await page.fill('[name="password"]', password);
  await page.click('button[type="submit"]');
  await page.waitForURL(/\/dashboard/, { timeout: 30000 });
}

export async function signupUser(page: Page, email: string, password: string) {
  await dismissCookieConsent(page);
  await page.goto('/signup');
  await page.fill('[name="email"]', email);
  await page.fill('[name="password"]', password);
  await page.click('button[type="submit"]');
  
  // Test users (test_e2e_*) are auto-verified and go directly to /dashboard
  // Increased timeout to 90s due to backend performance variability during test runs
  await page.waitForURL(/\/dashboard/, { timeout: 90000 });
}

export async function createTestUserViaAPI(email: string, password: string): Promise<void> {
  const response = await fetch('http://localhost:5000/api/auth/signup', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const data = await response.json();
    throw new Error(data.error || 'Failed to create test user');
  }
}

export function generateTestEmail(): string {
  const timestamp = Date.now();
  const random = Math.floor(Math.random() * 10000);
  return `test_e2e_${timestamp}_${random}@example.com`;
}

export async function cleanupTestUser(email: string): Promise<void> {
  try {
    const response = await fetch(`http://localhost:8080/api/test/cleanup-user`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (!response.ok) {
      console.warn(`Failed to cleanup test user ${email}`);
    }
  } catch (error) {
    console.warn(`Error cleaning up test user ${email}:`, error);
  }
}

export async function waitForElement(page: Page, selector: string, timeout = 5000) {
  await page.waitForSelector(selector, { timeout, state: 'visible' });
}
