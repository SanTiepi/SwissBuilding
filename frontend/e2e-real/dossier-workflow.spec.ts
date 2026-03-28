import { test, expect } from '@playwright/test';

import {
  assertNoErrorBoundary,
  CANONICAL_SCENARIOS,
  fetchBuildings,
  findScenarioBuildingByAddress,
  getFirstBuildingId,
  requireAuthToken,
} from './helpers';

test.describe('Safe-to-Start Dossier Workflow (real backend)', () => {
  // This test requires:
  // 1. Backend running at localhost:8000
  // 2. Database seeded with seed_data (includes scenario buildings)
  // 3. Auth credentials via auth.setup.ts (admin session)

  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('dossier workflow panel is visible on a building', async ({ page }) => {
    const buildingId = await getFirstBuildingId(page);
    if (!buildingId) {
      test.skip(true, 'No buildings in database -- seed data required');
      return;
    }
    await page.goto(`/buildings/${buildingId}`);
    await assertNoErrorBoundary(page);
    await page.waitForLoadState('networkidle');

    // Dossier workflow panel should be visible (French or English labels)
    const dossierIndicator = page.locator(
      'text=/dossier|readiness|completude|completeness|travaux|pre-work|safe.*start/i',
    );
    await expect(
      dossierIndicator.first(),
      'Dossier workflow panel not found on building detail page',
    ).toBeVisible({ timeout: 15_000 });
  });

  test('readiness assessment shows verdict on nearly-ready building', async ({
    page,
  }) => {
    const building = await findScenarioBuildingByAddress(
      page,
      CANONICAL_SCENARIOS.nearlyReady,
    );
    if (!building) {
      test.skip(true, 'Nearly-ready scenario building not found -- seed data required');
      return;
    }
    await page.goto(`/buildings/${building.id}`);
    await assertNoErrorBoundary(page);
    await page.waitForLoadState('networkidle');

    // Should show a readiness-related verdict somewhere on the page
    const readinessIndicator = page.locator(
      'text=/pret|ready|non.*pret|not.*ready|bloqu|blocked|conditionnel|conditional/i',
    );
    await expect(
      readinessIndicator.first(),
      'Readiness verdict not visible on nearly-ready building',
    ).toBeVisible({ timeout: 15_000 });
  });

  test('today page loads with content', async ({ page }) => {
    await page.goto('/today');
    await assertNoErrorBoundary(page);
    await page.waitForLoadState('networkidle');

    // Today page should show something (actions, deadlines, or empty state)
    const main = page.locator('main');
    await expect(main).not.toBeEmpty();
    // Verify a heading is present (page loaded correctly)
    const heading = page.getByRole('heading', { level: 1 });
    await expect(
      heading,
      'Today page heading not visible -- page may have failed to load',
    ).toBeVisible({ timeout: 10_000 });
  });

  test('authority pack can be generated via API', async ({ page }) => {
    const building = await findScenarioBuildingByAddress(
      page,
      CANONICAL_SCENARIOS.nearlyReady,
    );
    if (!building) {
      test.skip(true, 'Nearly-ready scenario building not found -- seed data required');
      return;
    }
    const token = await requireAuthToken(page);

    // Generate authority pack artifact via API
    const response = await page.request.post(
      `/api/v1/buildings/${building.id}/authority-pack/artifact`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        data: {
          language: 'fr',
          redact_financials: false,
        },
      },
    );

    expect(
      response.ok(),
      `Authority pack artifact API returned ${response.status()}: ${await response.text()}`,
    ).toBeTruthy();

    const result = await response.json();
    expect(result.artifact_path).toBeTruthy();
    expect(result.sha256).toBeTruthy();
    expect(result.sha256.length).toBe(64); // SHA-256 hex length
    expect(result.metadata.building_id).toBe(building.id);
    expect(result.metadata.version).toBeTruthy();
    expect(result.pack_data).toBeTruthy();
    expect(result.pack_data.sections.length).toBeGreaterThan(0);
  });

  test('building detail overview shows pilot scorecard content', async ({
    page,
  }) => {
    const buildingId = await getFirstBuildingId(page);
    if (!buildingId) {
      test.skip(true, 'No buildings in database -- seed data required');
      return;
    }
    await page.goto(`/buildings/${buildingId}`);
    await assertNoErrorBoundary(page);
    await page.waitForLoadState('networkidle');

    // Scorecard/overview should be somewhere in the building detail
    // (passport grade, trust, completeness, or risk indicators)
    const scoreIndicator = page.locator(
      'text=/grade|score|trust|confiance|completude|completeness|risque|risk/i',
    );
    await expect(
      scoreIndicator.first(),
      'No scorecard/grade/trust/completeness indicator found on building detail page',
    ).toBeVisible({ timeout: 15_000 });
  });

  test('buildings list loads and shows multiple buildings', async ({ page }) => {
    const buildings = await fetchBuildings(page);
    expect(
      buildings.length,
      'Expected at least 1 building in the seeded database',
    ).toBeGreaterThanOrEqual(1);

    await page.goto('/buildings');
    await assertNoErrorBoundary(page);

    // Building rows/cards should render
    const buildingRows = page.locator(
      'table tbody tr, [data-testid*="building"], a[href*="/buildings/"]',
    );
    await expect(buildingRows.first()).toBeVisible({ timeout: 10_000 });
  });
});
