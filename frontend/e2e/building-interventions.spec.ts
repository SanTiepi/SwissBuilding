import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Building Interventions Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/buildings/b1000000-0000-0000-0000-000000000001/interventions');
    await page.waitForLoadState('networkidle');
  });

  test('displays interventions page header', async ({ page }) => {
    const header = page.locator('h1, h2').filter({ hasText: /intervention/i });
    await expect(header.first()).toBeVisible();
  });

  test('shows intervention list with title', async ({ page }) => {
    await expect(page.getByText('Renovation facade nord')).toBeVisible();
  });

  test('shows intervention description', async ({ page }) => {
    await expect(page.getByText('Remplacement des joints amiantees')).toBeVisible();
  });

  test('shows status filter pills', async ({ page }) => {
    // The page renders status filter buttons including "All"
    const allBtn = page.locator('button').filter({ hasText: /all|tous|tout/i });
    await expect(allBtn.first()).toBeVisible();
  });

  test('shows contractor name', async ({ page }) => {
    await expect(page.getByText('SanaCore AG')).toBeVisible();
  });

  test('back link navigates to building detail', async ({ page }) => {
    const backLink = page.locator('a[href*="/buildings/b1000000"]').first();
    await expect(backLink).toBeVisible();
  });

  test('no JS errors on page', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.waitForTimeout(1000);
    expect(errors).toEqual([]);
  });
});
