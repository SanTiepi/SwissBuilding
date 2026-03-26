import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Completeness on Building Detail', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/buildings/b1000000-0000-0000-0000-000000000001');
    await page.waitForLoadState('networkidle');
  });

  test('SVG gauge circles appear on building detail page', async ({ page }) => {
    // Various gauge components render circular SVG elements
    const gauge = page.locator('svg circle');
    await expect(gauge.first()).toBeVisible();
  });

  test('completeness score is displayed from dashboard aggregate', async ({ page }) => {
    // Dashboard mock returns completeness.overall_score: 0.68 → displayed as 68%
    const scoreText = page.getByText('68%');
    await expect(scoreText.first()).toBeVisible();
  });

  test('section headers are rendered', async ({ page }) => {
    // The overview tab renders multiple sections with headings
    const headers = page.locator('h2, h3');
    expect(await headers.count()).toBeGreaterThan(0);
  });

  test('readiness status is shown', async ({ page }) => {
    // Dashboard mock returns readiness.overall_status: 'partially_ready'
    // This should be displayed somewhere on the page
    const readinessText = page.getByText(/partially|partiellement|teilweise|parzialmente|blocked|bloque/i);
    await expect(readinessText.first()).toBeVisible();
  });

  test('passport grade is displayed', async ({ page }) => {
    // Dashboard mock returns passport_grade: 'B'
    // Passport summary mock returns passport_grade: 'C'
    // One of these should be visible
    const grade = page.getByText(/^[A-F]$/).first();
    await expect(grade).toBeVisible();
  });

  test('trust score is displayed', async ({ page }) => {
    // Dashboard mock returns trust.score: 0.82 → 82%
    const trustText = page.getByText('82%');
    await expect(trustText.first()).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});
