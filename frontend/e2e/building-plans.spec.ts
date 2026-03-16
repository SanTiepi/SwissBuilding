import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Building Plans Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/buildings/b1000000-0000-0000-0000-000000000001/plans');
    await page.waitForLoadState('networkidle');
  });

  test('displays plans page header', async ({ page }) => {
    const header = page.locator('h1, h2').filter({ hasText: /plan|plans/i });
    await expect(header.first()).toBeVisible();
  });

  test('shows plans grid with plan card', async ({ page }) => {
    await expect(page.getByText('Plan rez-de-chaussee')).toBeVisible();
  });

  test('plan card shows file name and size', async ({ page }) => {
    await expect(page.getByText('plan-rdc.pdf')).toBeVisible();
    // 2048000 bytes = ~2.0 MB
    await expect(page.getByText(/2\.0\s*MB/i).first()).toBeVisible();
  });

  test('shows type filter pills', async ({ page }) => {
    const allBtn = page.locator('button').filter({ hasText: /all|tous|tout/i });
    await expect(allBtn.first()).toBeVisible();
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
