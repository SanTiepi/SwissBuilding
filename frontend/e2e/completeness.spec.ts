import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Completeness Gauge on Building Detail', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/buildings/b1000000-0000-0000-0000-000000000001');
    await page.waitForLoadState('networkidle');
  });

  test('CompletenessGauge appears on building detail page', async ({ page }) => {
    // The gauge component renders with a circular SVG gauge and percentage
    // 75% from the completeness API mock (overall_score: 0.75)
    const gauge = page.locator('svg circle');
    await expect(gauge.first()).toBeVisible();
  });

  test('score percentage is displayed', async ({ page }) => {
    // 75% from mock data (overall_score: 0.75) - displayed inside the gauge circle
    // Use a more specific locator to avoid matching the inline completeness section
    const scoreText = page.locator('.relative.w-24.h-24').getByText('75%');
    await expect(scoreText).toBeVisible();
  });

  test('check list is rendered with categories', async ({ page }) => {
    // The component groups checks by category - verify at least one category header
    const categoryHeaders = page.locator('h4');
    expect(await categoryHeaders.count()).toBeGreaterThan(0);
  });

  test('not-ready badge shows when score is below threshold', async ({ page }) => {
    // Mock returns ready_to_proceed: false, so "Not ready" badge should show
    const notReadyBadge = page.getByText(/not ready|pas encore pret|noch nicht bereit|non ancora pronto/i);
    await expect(notReadyBadge.first()).toBeVisible();
  });

  test('ready badge shows when score is high enough', async ({ page }) => {
    // Override completeness with ready_to_proceed: true
    await page.route(/\/api\/v1\/buildings\/[^/]+\/completeness/, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          building_id: 'b1000000-0000-0000-0000-000000000001',
          workflow_stage: 'avt',
          overall_score: 0.95,
          checks: [
            {
              id: 'diag_asbestos',
              category: 'diagnostic',
              label_key: 'completeness.check.has_diagnostic',
              status: 'complete',
              weight: 1,
              details: null,
            },
          ],
          missing_items: [],
          ready_to_proceed: true,
          evaluated_at: '2024-06-01T14:00:00Z',
        }),
      }),
    );

    await page.goto('/buildings/b1000000-0000-0000-0000-000000000001');
    await page.waitForLoadState('networkidle');

    const readyBadge = page.getByText(/ready to proceed|pret|bereit|pronto/i);
    await expect(readyBadge.first()).toBeVisible();
  });

  test('missing items are highlighted', async ({ page }) => {
    // Mock data has missing_items: ['Diagnostic PCB manquant', 'Plan de desamiantage requis']
    await expect(page.getByText('Diagnostic PCB manquant')).toBeVisible();
    await expect(page.getByText('Plan de desamiantage requis')).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});
