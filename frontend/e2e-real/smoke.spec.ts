import { test, expect } from '@playwright/test';
import {
  assertNoErrorBoundary,
  CANONICAL_SCENARIOS,
  fetchBuildings,
  fetchBuildingArtefacts,
  fetchBuildingDiagnostics,
  fetchBuildingInterventions,
  findScenarioBuildingByAddress,
  getFirstBuildingId,
  getFirstDiagnosticTarget,
} from './helpers';

test.describe('Smoke tests — real backend', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('dashboard loads with KPI cards', async ({ page }) => {
    await expect(page).toHaveURL(/\/dashboard/);
    await assertNoErrorBoundary(page);
    // Dashboard must show the main heading
    await expect(page.getByRole('heading', { level: 1 })).toBeVisible();
    // At least one stat card should be rendered (role=region or card-like container)
    const cards = page.locator('[class*="stat"], [class*="card"], [class*="Card"], .bg-white');
    await expect(cards.first()).toBeVisible({ timeout: 10_000 });
  });

  test('buildings list shows seeded buildings with addresses', async ({ page }) => {
    await page.goto('/buildings');
    await assertNoErrorBoundary(page);
    // Verify via API that seeded buildings exist and have addresses
    const buildings = await fetchBuildings(page);
    expect(
      buildings.length,
      `Expected at least 3 seeded buildings, got ${buildings.length}`,
    ).toBeGreaterThanOrEqual(3);

    // At least one building must have a non-empty address (seed_data guarantee)
    const withAddress = buildings.filter((b) => b.address && b.address.length > 5);
    expect(
      withAddress.length,
      'No buildings with valid addresses found — seed data may be missing',
    ).toBeGreaterThan(0);

    // UI: wait for building rows/cards to render (not a raw timeout)
    const buildingRows = page.locator('table tbody tr, [data-testid*="building"], a[href*="/buildings/"]');
    await expect(buildingRows.first()).toBeVisible({ timeout: 10_000 });
  });

  test('building detail loads with seeded building content', async ({ page }) => {
    const buildingId = await getFirstBuildingId(page);
    if (!buildingId) {
      test.skip(true, 'No buildings in database — seed data required');
      return;
    }
    await page.goto(`/buildings/${buildingId}`);
    await assertNoErrorBoundary(page);
    // Building detail must show a heading (building address or name)
    await expect(
      page.getByRole('heading', { level: 1 }),
      'Building detail page heading not visible — page may have failed to load',
    ).toBeVisible({ timeout: 10_000 });
  });

  test('diagnostic detail loads with status badge', async ({ page }) => {
    const target = await getFirstDiagnosticTarget(page);
    if (!target) {
      test.skip(true, 'No diagnostics found in seeded dataset');
      return;
    }
    await page.goto(`/diagnostics/${target.diagnosticId}`);
    await assertNoErrorBoundary(page);
    // Diagnostic page must show a heading
    await expect(
      page.getByRole('heading', { level: 1 }),
      'Diagnostic detail heading not visible',
    ).toBeVisible({ timeout: 10_000 });
    // Status badge must be present (draft/in_progress/completed/validated)
    const statusBadge = page.locator(
      '[class*="badge"], [class*="Badge"], [data-testid*="status"]',
    );
    await expect(
      statusBadge.first(),
      'Diagnostic status badge not found on detail page',
    ).toBeVisible({ timeout: 5_000 });
  });

  test('documents page loads', async ({ page }) => {
    await page.goto('/documents');
    await assertNoErrorBoundary(page);
    await expect(
      page.locator('main').getByRole('heading', { level: 1, name: /document/i }),
    ).toBeVisible();
  });

  test('settings page loads with profile', async ({ page }) => {
    await page.goto('/settings');
    await assertNoErrorBoundary(page);
    await expect(
      page.locator('main').getByRole('heading', { level: 1, name: /param|settings/i }),
    ).toBeVisible();
  });

  test('risk simulator page loads', async ({ page }) => {
    await page.goto('/risk-simulator');
    await assertNoErrorBoundary(page);
    await expect(
      page.locator('main').getByRole('heading', { level: 1, name: /simulation|simulator/i }),
    ).toBeVisible();
  });

  test('map page loads without crash', async ({ page }) => {
    await page.goto('/map');
    await assertNoErrorBoundary(page);
    await expect(page.locator('input[type="checkbox"]').first()).toBeVisible();
  });

  test('unauthenticated access redirects to login', async ({ page }) => {
    await page.context().clearCookies();
    await page.goto('/login');
    await page.evaluate(() => localStorage.clear());
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });
});

// ---------------------------------------------------------------------------
// Canonical Dossier Progression Scenario
// ---------------------------------------------------------------------------
// These tests verify the seeded scenario buildings exist and represent
// distinct dossier states, proving the raw → complete progression chain.
// The canonical building is "nearly_ready" (Immeuble Presque Prêt):
//   - has validated diagnostics, compliance artefacts, samples
//   - represents the closest-to-complete dossier in seed data
// The contrast building is "empty_dossier" (Nouveau Import):
//   - raw import with no diagnostics or enrichment

test.describe('Canonical dossier progression — seeded scenario', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('scenario buildings exist in seeded data', async ({ page }) => {
    // Verify all 5 scenario buildings are present
    for (const [scenarioName, addressFragment] of Object.entries(CANONICAL_SCENARIOS)) {
      const building = await findScenarioBuildingByAddress(page, addressFragment);
      expect(
        building,
        `Scenario building "${scenarioName}" (address containing "${addressFragment}") not found. Run seed_data to populate.`,
      ).not.toBeNull();
      expect(
        building!.id,
        `Scenario building "${scenarioName}" has no ID`,
      ).toBeTruthy();
    }
  });

  test('empty dossier building has no diagnostics (raw state)', async ({ page }) => {
    const building = await findScenarioBuildingByAddress(
      page,
      CANONICAL_SCENARIOS.emptyDossier,
    );
    expect(building, 'Empty dossier scenario building not found').not.toBeNull();

    const diagnostics = await fetchBuildingDiagnostics(page, building!.id);
    expect(
      diagnostics.length,
      `Empty dossier building should have 0 diagnostics (raw state), got ${diagnostics.length}`,
    ).toBe(0);
  });

  test('nearly-ready building has diagnostics and artefacts (advanced state)', async ({
    page,
  }) => {
    const building = await findScenarioBuildingByAddress(
      page,
      CANONICAL_SCENARIOS.nearlyReady,
    );
    expect(building, 'Nearly-ready scenario building not found').not.toBeNull();

    // Must have at least 1 diagnostic
    const diagnostics = await fetchBuildingDiagnostics(page, building!.id);
    expect(
      diagnostics.length,
      `Nearly-ready building must have diagnostics, got ${diagnostics.length}`,
    ).toBeGreaterThanOrEqual(1);

    // Must have at least 1 compliance artefact
    const artefacts = await fetchBuildingArtefacts(page, building!.id);
    expect(
      artefacts.length,
      `Nearly-ready building must have compliance artefacts, got ${artefacts.length}`,
    ).toBeGreaterThanOrEqual(1);
  });

  test('post-works building has interventions (completed works state)', async ({ page }) => {
    const building = await findScenarioBuildingByAddress(
      page,
      CANONICAL_SCENARIOS.postWorks,
    );
    expect(building, 'Post-works scenario building not found').not.toBeNull();

    // Must have at least 1 diagnostic
    const diagnostics = await fetchBuildingDiagnostics(page, building!.id);
    expect(
      diagnostics.length,
      `Post-works building must have diagnostics, got ${diagnostics.length}`,
    ).toBeGreaterThanOrEqual(1);

    // Must have at least 1 intervention
    const interventions = await fetchBuildingInterventions(page, building!.id);
    expect(
      interventions.length,
      `Post-works building must have interventions, got ${interventions.length}`,
    ).toBeGreaterThanOrEqual(1);
  });

  test('contradiction building has multiple diagnostics', async ({ page }) => {
    const building = await findScenarioBuildingByAddress(
      page,
      CANONICAL_SCENARIOS.contradiction,
    );
    expect(building, 'Contradiction scenario building not found').not.toBeNull();

    // Must have at least 2 diagnostics (positive and negative)
    const diagnostics = await fetchBuildingDiagnostics(page, building!.id);
    expect(
      diagnostics.length,
      `Contradiction building must have >=2 diagnostics (positive+negative), got ${diagnostics.length}`,
    ).toBeGreaterThanOrEqual(2);
  });

  test('nearly-ready building detail renders in UI', async ({ page }) => {
    const building = await findScenarioBuildingByAddress(
      page,
      CANONICAL_SCENARIOS.nearlyReady,
    );
    expect(building, 'Nearly-ready scenario building not found').not.toBeNull();

    await page.goto(`/buildings/${building!.id}`);
    await assertNoErrorBoundary(page);

    // Building heading must contain part of the address
    const heading = page.getByRole('heading', { level: 1 });
    await expect(heading).toBeVisible({ timeout: 10_000 });

    // Page must show diagnostic-related content (tabs, cards, or sections)
    const diagnosticSection = page.locator(
      '[data-testid*="diagnostic"], a[href*="diagnostic"], button:has-text("Diagnostic"), [role="tab"]',
    );
    await expect(
      diagnosticSection.first(),
      'Building detail page should show diagnostic-related UI elements',
    ).toBeVisible({ timeout: 10_000 });
  });

  test('dossier progression: empty vs nearly-ready have different data depth', async ({
    page,
  }) => {
    // This test explicitly proves that different scenario buildings represent
    // different dossier progression states via API-level assertions.
    const emptyBuilding = await findScenarioBuildingByAddress(
      page,
      CANONICAL_SCENARIOS.emptyDossier,
    );
    const nearlyReadyBuilding = await findScenarioBuildingByAddress(
      page,
      CANONICAL_SCENARIOS.nearlyReady,
    );

    expect(emptyBuilding, 'Empty dossier building not found').not.toBeNull();
    expect(nearlyReadyBuilding, 'Nearly-ready building not found').not.toBeNull();

    // Confirm they are different buildings
    expect(emptyBuilding!.id).not.toEqual(nearlyReadyBuilding!.id);

    const emptyDiagnostics = await fetchBuildingDiagnostics(page, emptyBuilding!.id);
    const readyDiagnostics = await fetchBuildingDiagnostics(page, nearlyReadyBuilding!.id);

    expect(
      readyDiagnostics.length,
      'Nearly-ready building must have more diagnostic data than empty building',
    ).toBeGreaterThan(emptyDiagnostics.length);

    const emptyArtefacts = await fetchBuildingArtefacts(page, emptyBuilding!.id);
    const readyArtefacts = await fetchBuildingArtefacts(page, nearlyReadyBuilding!.id);

    expect(
      readyArtefacts.length,
      'Nearly-ready building must have artefacts while empty building has none',
    ).toBeGreaterThan(emptyArtefacts.length);
  });
});
