import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Building Explorer Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/buildings/b1000000-0000-0000-0000-000000000001/explorer');
    await page.waitForLoadState('networkidle');
  });

  test('displays explorer page header', async ({ page }) => {
    const header = page.locator('h1, h2').filter({ hasText: /explorer|structure|zones/i });
    await expect(header.first()).toBeVisible();
  });

  test('shows zone list', async ({ page }) => {
    await expect(page.getByText('Rez-de-chaussee').first()).toBeVisible();
    await expect(page.getByText('Sous-sol').first()).toBeVisible();
  });

  test('back link navigates to building detail', async ({ page }) => {
    const backLink = page.locator('a[href*="/buildings/b1000000"]').first();
    await expect(backLink).toBeVisible();
  });

  test('zones show element counts', async ({ page }) => {
    // Each zone row shows its elements_count
    await expect(page.getByText(/5\s*(elements|element)/i).first()).toBeVisible();
  });

  test('no JS errors on page', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.waitForTimeout(1000);
    expect(errors).toEqual([]);
  });
});
