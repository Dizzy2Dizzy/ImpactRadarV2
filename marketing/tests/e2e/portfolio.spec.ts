import { test, expect } from '@playwright/test';
import { generateTestEmail, signupUser } from './helpers';
import path from 'path';

test.describe('Portfolio Upload', () => {
  let testEmail: string;
  const testPassword = 'TestPassword123!';

  test.beforeEach(async ({ page }) => {
    testEmail = generateTestEmail();
    await signupUser(page, testEmail, testPassword);
  });

  test('upload portfolio CSV and see positions', async ({ page }) => {
    await page.goto('/dashboard');
    
    const portfolioTab = page.getByRole('button', { name: 'Portfolio' });
    await portfolioTab.click();
    
    await expect(page.getByText(/No Portfolio Uploaded|Portfolio Risk/i)).toBeVisible({ timeout: 5000 });
    
    const fileInput = page.locator('input[type="file"]');
    const filePath = path.join(__dirname, 'fixtures', 'sample-portfolio.csv');
    
    await fileInput.setInputFiles(filePath);
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/AAPL|positions/i)).toBeVisible({ timeout: 15000 });
  });

  test('upload invalid CSV shows error', async ({ page }) => {
    await page.goto('/dashboard');
    
    const portfolioTab = page.getByRole('button', { name: 'Portfolio' });
    await portfolioTab.click();
    
    const fileInput = page.locator('input[type="file"]');
    const filePath = path.join(__dirname, 'fixtures', 'invalid-portfolio.csv');
    
    await fileInput.setInputFiles(filePath);
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/error|invalid|failed/i)).toBeVisible({ timeout: 10000 });
  });

  test('download template CSV works', async ({ page }) => {
    await page.goto('/dashboard');
    
    const portfolioTab = page.getByRole('button', { name: 'Portfolio' });
    await portfolioTab.click();
    
    const downloadPromise = page.waitForEvent('download');
    
    const downloadButton = page.getByRole('button', { name: /Download.*Template/i }).or(
      page.locator('button:has-text("Download"), a:has-text("Download")')
    );
    await downloadButton.click();
    
    const download = await downloadPromise;
    expect(download.suggestedFilename()).toContain('.csv');
  });

  test('can delete uploaded portfolio', async ({ page }) => {
    await page.goto('/dashboard');
    
    const portfolioTab = page.getByRole('button', { name: 'Portfolio' });
    await portfolioTab.click();
    
    const fileInput = page.locator('input[type="file"]');
    const filePath = path.join(__dirname, 'fixtures', 'sample-portfolio.csv');
    
    await fileInput.setInputFiles(filePath);
    
    await page.waitForTimeout(2000);
    
    await expect(page.getByText(/AAPL|positions/i)).toBeVisible({ timeout: 15000 });
    
    page.on('dialog', dialog => dialog.accept());
    
    const deleteButton = page.getByRole('button', { name: /Delete/i });
    await deleteButton.click();
    
    await expect(page.getByText(/No Portfolio Uploaded/i)).toBeVisible({ timeout: 5000 });
  });
});
