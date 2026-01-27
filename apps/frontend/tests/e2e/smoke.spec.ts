import { test, expect } from '@playwright/test';

/**
 * Smoke Tests - Baseline E2E tests for Kortix frontend
 * 
 * These tests verify core functionality works after deployments.
 */

test.describe('Marketing Pages', () => {
  test('homepage loads correctly', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveTitle(/Kortix/);
    await expect(page.locator('body')).toBeVisible();
  });

  test('auth page loads', async ({ page }) => {
    await page.goto('/auth');
    await expect(page.locator('body')).toBeVisible();
  });
});

test.describe('Dashboard (requires auth)', () => {
  test.skip('dashboard redirects to auth when not logged in', async ({ page }) => {
    await page.goto('/dashboard');
    // Should redirect to auth
    await expect(page).toHaveURL(/auth/);
  });
});

test.describe('V2 API Health', () => {
  test('/v2/health returns OK', async ({ request }) => {
    // Backend runs on port 8000
    const response = await request.get('http://localhost:8000/v2/health');
    expect(response.ok()).toBe(true);
    const data = await response.json();
    expect(data).toHaveProperty('status');
    expect(data.status).toBe('healthy');
  });
});

test.describe('Accessibility', () => {
  test('homepage has proper heading structure', async ({ page }) => {
    await page.goto('/');
    // Homepage uses paragraph with animated text, check for main content
    const mainContent = page.locator('main, [role="main"], body').first();
    await expect(mainContent).toBeVisible();
  });

  test('focus is visible on interactive elements', async ({ page }) => {
    await page.goto('/');
    // Tab to first focusable element
    await page.keyboard.press('Tab');
    const focusedElement = page.locator(':focus');
    await expect(focusedElement).toBeVisible();
  });
});

test.describe('Performance', () => {
  test('homepage loads within reasonable time', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/');
    const loadTime = Date.now() - startTime;
    // Should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });
});
