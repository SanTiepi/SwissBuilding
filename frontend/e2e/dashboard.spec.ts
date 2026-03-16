import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Dashboard Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
  });

  test('displays welcome message with user name', async ({ page }) => {
    // Wait for dashboard to finish loading
    await page.waitForSelector('h1', { timeout: 10000 });
    await expect(page.getByText('Admin').first()).toBeVisible();
  });

  test('displays KPI cards', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    // KPI cards should exist
    const kpiCards = page.locator('.bg-white.rounded-xl.border');
    const count = await kpiCards.count();
    expect(count).toBeGreaterThanOrEqual(4);
  });

  test('displays action buttons', async ({ page }) => {
    // "Add building" button
    const addBuildingBtn = page.locator('button').filter({ hasText: /batiment|building|Gebäude/i });
    await expect(addBuildingBtn.first()).toBeVisible();
  });

  test('add building button navigates to buildings page', async ({ page }) => {
    const addBtn = page.locator('button').filter({ hasText: /batiment|building/i }).first();
    await addBtn.click();

    await expect(page).toHaveURL(/\/buildings/);
  });

  test('displays chart sections', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    // Chart section headers (h2 elements within the dashboard)
    const chartHeaders = page.locator('h2');
    const count = await chartHeaders.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('displays recent activity section', async ({ page }) => {
    // Recent activity section should exist
    const activitySection = page.locator('h2').filter({ hasText: /activit|Aktivität|activity/i });
    await expect(activitySection).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});
