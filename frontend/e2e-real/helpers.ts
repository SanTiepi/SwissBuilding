import { Page, expect } from '@playwright/test';

import { AUTH_STORAGE_KEY } from './auth';

const DEFAULT_REAL_E2E_EMAIL = process.env.E2E_REAL_ADMIN_EMAIL || 'admin@swissbuildingos.ch';
const DEFAULT_REAL_E2E_PASSWORD = process.env.E2E_REAL_ADMIN_PASSWORD || 'noob42';

/**
 * Log in via the real UI login form.
 * Requires a running backend with seeded users.
 */
export async function loginViaUI(
  page: Page,
  email = DEFAULT_REAL_E2E_EMAIL,
  password = DEFAULT_REAL_E2E_PASSWORD,
): Promise<void> {
  await page.goto('/login');
  await page.locator('#email').fill(email);
  await page.locator('#password').fill(password);
  await page.getByRole('button', { name: /connecter|sign in|anmelden|accedi/i }).click();
  await page.waitForURL('**/dashboard', { timeout: 15_000 });
  await expect(page).toHaveURL(/\/dashboard/);
}

async function getStoredAuthToken(page: Page): Promise<string | null> {
  const state = await page.context().storageState();
  for (const origin of state.origins) {
    const entry = origin.localStorage.find((item) => item.name === AUTH_STORAGE_KEY);
    if (!entry) {
      continue;
    }
    try {
      const parsed = JSON.parse(entry.value);
      const token = parsed?.state?.token;
      return typeof token === 'string' && token.length > 0 ? token : null;
    } catch {
      return null;
    }
  }
  return null;
}

/**
 * Get a valid auth token or throw with an actionable message.
 */
export async function requireAuthToken(page: Page): Promise<string> {
  const token = await getStoredAuthToken(page);
  if (!token) {
    throw new Error(
      'No auth token found in storage. Auth setup may have failed — check auth.setup.ts.',
    );
  }
  return token;
}

/**
 * Assert that no React error boundary is visible on the current page.
 */
export async function assertNoErrorBoundary(page: Page): Promise<void> {
  const errorBoundary = page.locator('[data-testid="error-boundary"], .error-boundary');
  await expect(errorBoundary).toHaveCount(0);
}

// ---------------------------------------------------------------------------
// Building API helpers
// ---------------------------------------------------------------------------

export interface BuildingListItem {
  id: string;
  address?: string;
  city?: string;
  canton?: string;
  construction_year?: number;
  building_type?: string;
  status?: string;
}

/**
 * Fetch the first page of buildings from the API.
 * Returns the full item array for richer assertions.
 */
export async function fetchBuildings(
  page: Page,
  params: { pageIndex?: number; size?: number } = {},
): Promise<BuildingListItem[]> {
  const token = await requireAuthToken(page);
  const pageIndex = params.pageIndex ?? 1;
  const size = params.size ?? 100;
  const response = await page.request.get(`/api/v1/buildings?page=${pageIndex}&size=${size}`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok()) {
    throw new Error(`Buildings API returned ${response.status()}: ${await response.text()}`);
  }
  const data = await response.json();
  const items: BuildingListItem[] = data.items ?? data;
  if (!Array.isArray(items)) {
    throw new Error(`Unexpected buildings payload shape: ${JSON.stringify(data).slice(0, 300)}`);
  }
  return items;
}

/**
 * Get the first building ID from the buildings list API.
 * Useful for navigating to building-detail / diagnostic-detail.
 */
export async function getFirstBuildingId(page: Page): Promise<string | null> {
  try {
    const items = await fetchBuildings(page);
    return items.length > 0 ? items[0].id : null;
  } catch {
    return null;
  }
}

/**
 * Find a canonical scenario building by partial address match.
 * Scans up to 5 pages to locate the building.
 * Returns null only if no match found.
 */
export async function findScenarioBuildingByAddress(
  page: Page,
  addressFragment: string,
): Promise<BuildingListItem | null> {
  const fragment = addressFragment.toLowerCase();
  for (let pageIndex = 1; pageIndex <= 5; pageIndex++) {
    const items = await fetchBuildings(page, { pageIndex, size: 100 });
    if (items.length === 0) break;
    const match = items.find((b) => (b.address ?? '').toLowerCase().includes(fragment));
    if (match) return match;
  }
  return null;
}

/**
 * Get the first diagnostic ID for a given building.
 */
export async function getFirstDiagnosticId(
  page: Page,
  buildingId: string,
): Promise<string | null> {
  const token = await getStoredAuthToken(page);
  if (!token) return null;
  const response = await page.request.get(`/api/v1/buildings/${buildingId}/diagnostics`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok()) return null;
  const data = await response.json();
  const items = Array.isArray(data) ? data : (data.items ?? []);
  return items.length > 0 ? items[0].id : null;
}

export async function getFirstDiagnosticTarget(
  page: Page,
): Promise<{ buildingId: string; diagnosticId: string } | null> {
  const token = await getStoredAuthToken(page);
  if (!token) return null;

  for (let pageIndex = 1; pageIndex <= 10; pageIndex += 1) {
    const buildingsResponse = await page.request.get(
      `/api/v1/buildings?page=${pageIndex}&size=100`,
      {
        headers: { Authorization: `Bearer ${token}` },
      },
    );
    if (!buildingsResponse.ok()) return null;

    const data = await buildingsResponse.json();
    const items = Array.isArray(data) ? data : (data.items ?? []);
    if (!Array.isArray(items) || items.length === 0) {
      return null;
    }

    for (const building of items) {
      const buildingId = building?.id;
      if (!buildingId) {
        continue;
      }
      const diagnosticId = await getFirstDiagnosticId(page, buildingId);
      if (diagnosticId) {
        return { buildingId, diagnosticId };
      }
    }
  }
  return null;
}

// ---------------------------------------------------------------------------
// Dossier progression helpers (canonical scenario)
// ---------------------------------------------------------------------------

export interface DiagnosticSummary {
  id: string;
  status?: string;
  pollutant_type?: string;
  risk_level?: string;
}

/**
 * Fetch diagnostics for a building with full detail.
 */
export async function fetchBuildingDiagnostics(
  page: Page,
  buildingId: string,
): Promise<DiagnosticSummary[]> {
  const token = await requireAuthToken(page);
  const response = await page.request.get(`/api/v1/buildings/${buildingId}/diagnostics`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok()) {
    throw new Error(
      `Diagnostics API for building ${buildingId} returned ${response.status()}`,
    );
  }
  const data = await response.json();
  return Array.isArray(data) ? data : (data.items ?? []);
}

/**
 * Fetch actions for a building.
 */
export async function fetchBuildingActions(
  page: Page,
  buildingId: string,
): Promise<Array<{ id: string; status?: string; priority?: string }>> {
  const token = await requireAuthToken(page);
  const response = await page.request.get(
    `/api/v1/buildings/${buildingId}/actions?page=1&size=100`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!response.ok()) return [];
  const data = await response.json();
  return Array.isArray(data) ? data : (data.items ?? []);
}

/**
 * Fetch compliance artefacts for a building.
 */
export async function fetchBuildingArtefacts(
  page: Page,
  buildingId: string,
): Promise<Array<{ id: string; status?: string; artefact_type?: string }>> {
  const token = await requireAuthToken(page);
  const response = await page.request.get(
    `/api/v1/buildings/${buildingId}/compliance-artefacts?page=1&size=100`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!response.ok()) return [];
  const data = await response.json();
  return Array.isArray(data) ? data : (data.items ?? []);
}

/**
 * Fetch interventions for a building.
 */
export async function fetchBuildingInterventions(
  page: Page,
  buildingId: string,
): Promise<Array<{ id: string; status?: string; intervention_type?: string }>> {
  const token = await requireAuthToken(page);
  const response = await page.request.get(
    `/api/v1/buildings/${buildingId}/interventions?page=1&size=100`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!response.ok()) return [];
  const data = await response.json();
  return Array.isArray(data) ? data : (data.items ?? []);
}

// ---------------------------------------------------------------------------
// Canonical scenario building addresses (must match seed_data.py SCENARIO_IDS)
// ---------------------------------------------------------------------------

/** Partial address fragments for each scenario building from seed_data.py */
export const CANONICAL_SCENARIOS = {
  /** Building with contradictory diagnostics (positive vs negative asbestos) */
  contradiction: 'Contradictions',
  /** Building almost ready for safe-to-start (validated diag, artefacts) */
  nearlyReady: 'Presque Prêt',
  /** Building with completed intervention (post-works state) */
  postWorks: 'Post-Travaux',
  /** Building in a portfolio cluster */
  portfolioCluster: 'Lot Portefeuille',
  /** Raw building with no diagnostics or enrichment */
  emptyDossier: 'Nouveau Import',
} as const;
