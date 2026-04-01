import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('5-Hub Shell Navigation', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
  });

  test('default route redirects to Today', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/today');
  });

  test('Today hub loads without crash', async ({ page }) => {
    await page.goto('/today');
    await page.waitForLoadState('networkidle');
    // Page should load without a fatal error (no unhandled exception overlay)
    const errorOverlay = page.locator('[data-testid="error-boundary"]');
    await expect(errorOverlay).toHaveCount(0);
  });

  test('Buildings hub loads', async ({ page }) => {
    await page.goto('/buildings');
    await page.waitForLoadState('networkidle');
    const header = page.locator('h1, h2').filter({ hasText: /batiment|building|Gebäude/i });
    await expect(header.first()).toBeVisible();
  });

  test('Cases hub loads', async ({ page }) => {
    await page.goto('/cases');
    await page.waitForLoadState('networkidle');
    const header = page.locator('h1, h2').filter({ hasText: /dossier|case/i });
    await expect(header.first()).toBeVisible();
  });

  test('Finance hub loads', async ({ page }) => {
    await page.goto('/finance');
    await page.waitForLoadState('networkidle');
    const header = page.locator('h1, h2').filter({ hasText: /finance/i });
    await expect(header.first()).toBeVisible();
  });

  test('Portfolio hub loads without crash', async ({ page }) => {
    await page.goto('/portfolio-command');
    await page.waitForLoadState('networkidle');
    const errorOverlay = page.locator('[data-testid="error-boundary"]');
    await expect(errorOverlay).toHaveCount(0);
  });

  test('sidebar shows exactly 5 primary hub links', async ({ page }) => {
    await page.goto('/today');
    await page.waitForLoadState('networkidle');
    // The sidebar primary section should have 5 nav items
    const sidebar = page.locator('nav, aside').first();
    const primaryLinks = sidebar.locator('a[href="/today"], a[href="/buildings"], a[href="/cases"], a[href="/finance"], a[href="/portfolio-command"]');
    await expect(primaryLinks).toHaveCount(5);
  });

  test('absorbed routes redirect to hubs', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/today');
  });

  test('absorbed portfolio route redirects', async ({ page }) => {
    await page.goto('/portfolio');
    await page.waitForLoadState('networkidle');
    expect(page.url()).toContain('/portfolio-command');
  });
});
