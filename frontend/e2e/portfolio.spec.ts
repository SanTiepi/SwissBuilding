import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

const MOCK_PORTFOLIO_METRICS = {
  total_buildings: 150,
  risk_distribution: { low: 40, medium: 60, high: 35, critical: 15 },
  completeness_avg: 0.72,
  buildings_ready: 45,
  buildings_not_ready: 105,
  pollutant_prevalence: { asbestos: 85, pcb: 30, lead: 45, hap: 20, radon: 10 },
  actions_pending: 230,
  actions_critical: 15,
  recent_diagnostics: 12,
  interventions_in_progress: 8,
};

test.describe('Portfolio Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);

    // Mock portfolio metrics API
    await page.route('**/api/v1/portfolio/metrics', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(MOCK_PORTFOLIO_METRICS),
      }),
    );

    await page.goto('/portfolio');
    await page.waitForLoadState('networkidle');
  });

  test('displays page header', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    const heading = page.getByRole('heading', { name: /portfolio/i });
    await expect(heading).toBeVisible();
  });

  test('displays KPI cards with numbers', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });

    // Check that KPI values are rendered
    await expect(page.getByText('150')).toBeVisible();
    await expect(page.getByText('72%')).toBeVisible();
    await expect(page.getByText('45', { exact: true }).first()).toBeVisible();
    await expect(page.getByText('15').first()).toBeVisible();
  });

  test('displays risk distribution chart', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });

    // Recharts renders SVG elements
    const chartSection = page.locator('.recharts-responsive-container').first();
    await expect(chartSection).toBeVisible();
  });

  test('displays pollutant prevalence chart', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });

    // Should have at least 2 chart containers (risk + pollutant)
    const charts = page.locator('.recharts-responsive-container');
    const count = await charts.count();
    expect(count).toBeGreaterThanOrEqual(2);
  });

  test('displays activity summary section', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });

    // Check activity numbers
    await expect(page.getByText('12')).toBeVisible();
    await expect(page.getByText('8')).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});
