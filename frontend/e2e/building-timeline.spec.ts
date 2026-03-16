import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes, mockApiError } from './helpers';

test.describe('Building Timeline Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/buildings/b1000000-0000-0000-0000-000000000001/timeline');
    await page.waitForLoadState('networkidle');
  });

  test('displays timeline page header', async ({ page }) => {
    const header = page.locator('h1').filter({ hasText: /historique|timeline|Verlauf|cronologia/i });
    await expect(header.first()).toBeVisible();
  });

  test('displays building address in header', async ({ page }) => {
    await expect(page.getByText('Rue de Bourg 1')).toBeVisible();
  });

  test('timeline entries are rendered', async ({ page }) => {
    await expect(page.getByText('Niveau de risque mis a jour')).toBeVisible();
    await expect(page.getByText('Diagnostic amiante termine')).toBeVisible();
    await expect(page.getByText('Echantillon ECH-001 preleve')).toBeVisible();
    await expect(page.getByText('Renovation facade nord planifiee')).toBeVisible();
    await expect(page.getByText('Construction du batiment')).toBeVisible();
  });

  test('filter chips are rendered', async ({ page }) => {
    // The "all" filter chip should be visible
    const allChip = page.locator('button').filter({ hasText: /tou|all|alle|tutt/i }).first();
    await expect(allChip).toBeVisible();
  });

  test('clicking a filter chip filters the view', async ({ page }) => {
    // Mock the filtered API call to return only diagnostic entries
    await page.route(/\/api\/v1\/buildings\/[^/]+\/timeline\?.*event_type=diagnostic/, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'tl-002',
              date: '2024-03-20T14:00:00Z',
              event_type: 'diagnostic',
              title: 'Diagnostic amiante termine',
              description: 'Amiante detecte dans les joints de facade',
              icon_hint: 'microscope',
              metadata: { diagnostic_type: 'asbestos', status: 'completed' },
              source_id: 'd1000000-0000-0000-0000-000000000001',
              source_type: 'diagnostic',
            },
          ],
          total: 1,
          page: 1,
          size: 50,
          pages: 1,
        }),
      }),
    );

    // Click the "diagnostic" filter chip
    const diagChip = page.locator('button').filter({ hasText: /diagnostic|Diagnose|diagnostico/i }).first();
    await diagChip.click();
    await page.waitForLoadState('networkidle');

    // Diagnostic entry should remain visible
    await expect(page.getByText('Diagnostic amiante termine')).toBeVisible();
  });

  test('empty state displays correctly', async ({ page }) => {
    // Override timeline to return empty
    await page.route(/\/api\/v1\/buildings\/[^/]+\/timeline/, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0, page: 1, size: 50, pages: 0 }),
      }),
    );

    await page.goto('/buildings/b1000000-0000-0000-0000-000000000001/timeline');
    await page.waitForLoadState('networkidle');

    const emptyText = page.getByText(/aucun|no.*event|empty|vide|leer|vuoto/i);
    await expect(emptyText.first()).toBeVisible();
  });

  test('back button links to building detail', async ({ page }) => {
    const backLink = page.locator('a[href*="/buildings/b1000000"]').first();
    await expect(backLink).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});
