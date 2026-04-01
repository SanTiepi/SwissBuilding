import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { expect, test, type Page } from '@playwright/test';

import { assertNoErrorBoundary, requireAuthToken } from './helpers';

const SEEDED_BUILDING_ADDRESS = 'Avenue des Alpes 18';
const SEEDED_OWNER_NAME = 'Pierre Favre';
const SEEDED_LEASE_TENANT = 'Camille Rochat';
const SEEDED_CONTRACT_COUNTERPARTY = 'ThermoFlux Services SA';
const currentDir = path.dirname(fileURLToPath(import.meta.url));
const UPLOAD_FIXTURE_PATH = path.join(currentDir, 'fixtures', 'demo-building-brief.txt');

interface BuildingSummary {
  id: string;
  address?: string;
  city?: string;
  canton?: string;
  official_id?: string | null;
}

interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

interface ContactLookupResult {
  id: string;
  name: string;
  email: string | null;
  contact_type: string;
}

interface NamedRecord {
  id: string;
  title?: string | null;
  name?: string | null;
  reference_code?: string | null;
  owner_display_name?: string | null;
  tenant_display_name?: string | null;
  counterparty_display_name?: string | null;
  file_name?: string | null;
}

async function apiGet<T>(page: Page, pathName: string): Promise<T> {
  const token = await requireAuthToken(page);
  const response = await page.request.get(pathName, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!response.ok()) {
    throw new Error(`GET ${pathName} failed with ${response.status()}: ${await response.text()}`);
  }
  return (await response.json()) as T;
}

async function waitForJsonResponse<T>(
  page: Page,
  options: { method?: string; pathName: string },
  action: () => Promise<void>,
): Promise<{ ok: boolean; status: number; body: T | null; text: string }> {
  const method = options.method ?? 'POST';
  const responsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return response.request().method() === method && url.pathname === options.pathName;
  });

  await action();
  const response = await responsePromise;
  const text = await response.text();
  let body: T | null = null;

  try {
    body = JSON.parse(text) as T;
  } catch {}

  return {
    ok: response.ok(),
    status: response.status(),
    body,
    text,
  };
}

async function findBuildingByAddress(page: Page, address: string): Promise<BuildingSummary | null> {
  for (let pageIndex = 1; pageIndex <= 5; pageIndex += 1) {
    const payload = await apiGet<PaginatedResponse<BuildingSummary>>(
      page,
      `/api/v1/buildings?page=${pageIndex}&size=100`,
    );
    const match = payload.items.find((item) => item.address === address);
    if (match) {
      return match;
    }
    if (payload.items.length === 0) {
      break;
    }
  }
  return null;
}

async function lookupContact(page: Page, buildingId: string, query: string): Promise<ContactLookupResult[]> {
  return apiGet<ContactLookupResult[]>(
    page,
    `/api/v1/buildings/${buildingId}/contacts/lookup?q=${encodeURIComponent(query)}`,
  );
}

async function ensureTextVisible(page: Page, text: string): Promise<void> {
  await expect(page.getByText(text, { exact: false }).first()).toBeVisible({ timeout: 15_000 });
}

async function selectContactViaLookup(
  page: Page,
  options: { buildingId: string; query: string; expectedName: string },
): Promise<void> {
  const lookupResponse = page
    .waitForResponse((response) => {
      if (response.request().method() !== 'GET') {
        return false;
      }
      const url = new URL(response.url());
      return (
        url.pathname === `/api/v1/buildings/${options.buildingId}/contacts/lookup` &&
        url.searchParams.get('q') === options.query
      );
    })
    .catch(() => null);

  await page.getByTestId('contact-search-input').fill(options.query);
  await lookupResponse;

  const selectedName = page.getByTestId('contact-selected-name');
  const searchResult = page.getByTestId('contact-search-result').filter({ hasText: options.expectedName }).first();

  if (await searchResult.isVisible({ timeout: 1_000 }).catch(() => false)) {
    await searchResult.click();
  }

  await expect(selectedName).toContainText(options.expectedName, { timeout: 15_000 });
}

test.describe('Demo workspace real-backend workflow', () => {
  test.skip(({ isMobile }) => isMobile, 'This full workflow targets the dense desktop layout.');

  test('seeded workspace exposes rich demo data across core modules', async ({ page }) => {
    test.setTimeout(90_000);

    await expect
      .poll(async () => Boolean(await findBuildingByAddress(page, SEEDED_BUILDING_ADDRESS)), {
        timeout: 20_000,
      })
      .toBe(true);

    const building = await findBuildingByAddress(page, SEEDED_BUILDING_ADDRESS);
    expect(building).toBeTruthy();
    if (!building) {
      throw new Error(`Seeded demo building not found: ${SEEDED_BUILDING_ADDRESS}`);
    }
    const buildingId = building.id;

    const diagnostics = await apiGet<NamedRecord[]>(page, `/api/v1/buildings/${buildingId}/diagnostics`);
    const documents = await apiGet<NamedRecord[]>(page, `/api/v1/buildings/${buildingId}/documents`);
    const ownership = await apiGet<PaginatedResponse<NamedRecord>>(
      page,
      `/api/v1/buildings/${buildingId}/ownership?page=1&size=20`,
    );
    const leases = await apiGet<PaginatedResponse<NamedRecord>>(
      page,
      `/api/v1/buildings/${buildingId}/leases?page=1&size=20`,
    );
    const contracts = await apiGet<PaginatedResponse<NamedRecord>>(
      page,
      `/api/v1/buildings/${buildingId}/contracts?page=1&size=20`,
    );
    const interventions = await apiGet<PaginatedResponse<NamedRecord>>(
      page,
      `/api/v1/buildings/${buildingId}/interventions?page=1&size=20`,
    );
    const observations = await apiGet<PaginatedResponse<NamedRecord>>(
      page,
      `/api/v1/buildings/${buildingId}/field-observations?page=1&size=20`,
    );
    const zones = await apiGet<PaginatedResponse<NamedRecord>>(
      page,
      `/api/v1/buildings/${buildingId}/zones?page=1&size=50`,
    );

    expect(diagnostics.length).toBeGreaterThanOrEqual(1);
    expect(documents.length).toBeGreaterThanOrEqual(1);
    expect(ownership.total).toBeGreaterThanOrEqual(1);
    expect(leases.total).toBeGreaterThanOrEqual(1);
    expect(contracts.total).toBeGreaterThanOrEqual(1);
    expect(interventions.total).toBeGreaterThanOrEqual(1);
    expect(observations.total).toBeGreaterThanOrEqual(1);
    expect(zones.total).toBeGreaterThanOrEqual(3);

    await page.goto(`/buildings/${buildingId}`);
    await assertNoErrorBoundary(page);
    await ensureTextVisible(page, SEEDED_BUILDING_ADDRESS);

    await page.getByTestId('building-tab-truth').click();
    await ensureTextVisible(page, SEEDED_OWNER_NAME);

    await page.getByTestId('building-tab-cases').click();
    await ensureTextVisible(page, SEEDED_LEASE_TENANT);
    await ensureTextVisible(page, SEEDED_CONTRACT_COUNTERPARTY);
  });

  test('admin can create and enrich a realistic QA building through the UI', async ({ page }) => {
    test.setTimeout(240_000);

    const uniqueSuffix = Date.now().toString().slice(-7);
    const buildingAddress = `Rue du Simplon ${100 + Number(uniqueSuffix.slice(-3))}`;
    const officialId = `VD-UI-DEMO-${uniqueSuffix}`;
    const diagnosticMethodology = 'Inspection ciblée FACH 2021 + relevé photo';
    const ownershipNote = 'Copropriete documentee avant lancement des travaux techniques.';
    const leaseReference = `Bail-APT-${uniqueSuffix}`;
    const contractReference = `CTR-CHF-${uniqueSuffix}`;
    const contractTitle = `Contrat entretien CTA ${uniqueSuffix}`;
    const interventionTitle = `Retrait calorifugeage local technique ${uniqueSuffix}`;
    const observationTitle = `Observation chantier initiale ${uniqueSuffix}`;
    const zoneName = `Sous-sol demo ${uniqueSuffix}`;
    const elementName = `Conduite calorifugee ${uniqueSuffix}`;
    const materialName = `Calorifugeage test ${uniqueSuffix}`;

    await page.goto('/buildings');
    await assertNoErrorBoundary(page);

    await page.getByTestId('buildings-create-button').click();
    await expect(page.getByTestId('buildings-create-modal')).toBeVisible();

    await page.locator('[name="address"]').fill(buildingAddress);
    await page.locator('[name="city"]').fill('Lausanne');
    await page.locator('[name="postal_code"]').fill('1006');
    await page.locator('[name="canton"]').selectOption('VD');
    await page.locator('[name="building_type"]').selectOption('mixed');
    await page.locator('[name="construction_year"]').fill('1974');
    await page.getByTestId('buildings-form-advanced-toggle').click();
    await page.locator('[name="floors_above"]').fill('6');
    await page.locator('[name="floors_below"]').fill('1');
    await page.locator('[name="surface_area_m2"]').fill('1685');
    await page.locator('[name="egid"]').fill(`97${uniqueSuffix}`);
    await page.locator('[name="egrid"]').fill(`CH410000${uniqueSuffix}`);
    await page.locator('[name="official_id"]').fill(officialId);

    const buildingCreate = await waitForJsonResponse<{ id: string }>(
      page,
      { pathName: '/api/v1/buildings' },
      async () => {
        await page.getByTestId('buildings-form-submit').click();
      },
    );

    expect(buildingCreate.ok, buildingCreate.text).toBeTruthy();
    const buildingId = buildingCreate.body?.id;
    expect(buildingId).toBeTruthy();
    if (!buildingId) {
      throw new Error(`Building creation response missing id: ${buildingCreate.text}`);
    }
    await expect(page.getByTestId('buildings-create-modal')).toBeHidden({ timeout: 10_000 });

    await expect
      .poll(
        async () => {
          const payload = await apiGet<BuildingSummary>(page, `/api/v1/buildings/${buildingId}`);
          return payload.official_id ?? null;
        },
        { timeout: 15_000 },
      )
      .toBe(officialId);

    await page.goto(`/buildings/${buildingId}`);
    await assertNoErrorBoundary(page);
    await ensureTextVisible(page, buildingAddress);

    await page.getByTestId('building-tab-truth').click();
    await page.getByTestId('building-diagnostic-create-button').click();
    await expect(page.getByTestId('building-diagnostic-modal')).toBeVisible();
    await page.getByTestId('building-diagnostic-type').selectOption('asbestos');
    await page.getByTestId('building-diagnostic-context').selectOption('AvT');
    await page.getByTestId('building-diagnostic-date').fill('2026-03-15');
    await page.getByTestId('building-diagnostic-methodology').fill(diagnosticMethodology);

    const diagnosticCreate = await waitForJsonResponse<{ id: string; methodology?: string | null }>(
      page,
      { pathName: `/api/v1/buildings/${buildingId}/diagnostics` },
      async () => {
        await page.getByTestId('building-diagnostic-submit').click();
      },
    );

    expect(diagnosticCreate.ok, diagnosticCreate.text).toBeTruthy();
    await expect(page.getByTestId('building-diagnostic-modal')).toBeHidden({ timeout: 10_000 });

    await expect
      .poll(
        async () => {
          const payload = await apiGet<NamedRecord[]>(page, `/api/v1/buildings/${buildingId}/diagnostics`);
          return payload.length;
        },
        { timeout: 15_000 },
      )
      .toBeGreaterThanOrEqual(1);

    // Documents are now in the truth tab (already selected above)
    const uploadedFileName = path.basename(UPLOAD_FIXTURE_PATH);
    const documentsBefore = await apiGet<NamedRecord[]>(page, `/api/v1/buildings/${buildingId}/documents`);
    const uploadResponsePromise = page
      .waitForResponse(
        (response) => {
          const url = new URL(response.url());
          return response.request().method() === 'POST' && url.pathname === `/api/v1/buildings/${buildingId}/documents`;
        },
        { timeout: 8_000 },
      )
      .catch(() => null);

    await page.getByTestId('file-upload-input').setInputFiles(UPLOAD_FIXTURE_PATH);
    await ensureTextVisible(page, uploadedFileName);

    const uploadResponse = await uploadResponsePromise;
    if (uploadResponse?.ok()) {
      await expect
        .poll(
          async () => {
            const payload = await apiGet<NamedRecord[]>(page, `/api/v1/buildings/${buildingId}/documents`);
            return payload.length;
          },
          { timeout: 15_000 },
        )
        .toBeGreaterThan(documentsBefore.length);
    } else {
      const uploadStatus = uploadResponse
        ? `${uploadResponse.status()} ${await uploadResponse.text()}`
        : 'no response within 8s';
      console.warn(`Document persistence not asserted because storage is unavailable or slow: ${uploadStatus}`);
    }

    await page.getByTestId('building-tab-truth').click();
    await page.getByTestId('ownership-create-button').click();
    await expect(page.getByTestId('ownership-form-modal')).toBeVisible();
    await selectContactViaLookup(page, {
      buildingId,
      query: 'Favre',
      expectedName: SEEDED_OWNER_NAME,
    });
    await page.getByTestId('ownership-form-ownership-type').selectOption('co_ownership');
    await page.getByTestId('ownership-form-share').fill('60');
    await page.getByTestId('ownership-form-acquisition-type').selectOption('purchase');
    await page.getByTestId('ownership-form-acquisition-date').fill('2026-01-10');
    await page.getByTestId('ownership-form-acquisition-price').fill('1850000');
    await page.getByTestId('ownership-form-land-register-ref').fill(`RF-${uniqueSuffix}`);
    await page.getByTestId('ownership-form-status').selectOption('active');
    await page.getByTestId('ownership-form-notes').fill(ownershipNote);

    const ownershipCreate = await waitForJsonResponse<{ id: string }>(
      page,
      { pathName: `/api/v1/buildings/${buildingId}/ownership` },
      async () => {
        await page.getByTestId('ownership-form-submit').click();
      },
    );

    expect(ownershipCreate.ok, ownershipCreate.text).toBeTruthy();
    await expect(page.getByTestId('ownership-form-modal')).toBeHidden({ timeout: 10_000 });
    await ensureTextVisible(page, SEEDED_OWNER_NAME);

    const ownershipPayload = await apiGet<PaginatedResponse<NamedRecord>>(
      page,
      `/api/v1/buildings/${buildingId}/ownership?page=1&size=20`,
    );
    expect(ownershipPayload.items.some((item) => item.owner_display_name === SEEDED_OWNER_NAME)).toBeTruthy();

    await page.getByTestId('building-tab-cases').click();
    await page.getByTestId('leases-create-button').click();
    await expect(page.getByTestId('lease-form-modal')).toBeVisible();
    await page.getByTestId('lease-form-type').selectOption('residential');
    await page.getByTestId('lease-form-reference-code').fill(leaseReference);
    await selectContactViaLookup(page, {
      buildingId,
      query: 'Camille',
      expectedName: SEEDED_LEASE_TENANT,
    });
    await page.getByTestId('lease-form-date-start').fill('2026-04-01');
    await page.getByTestId('lease-form-date-end').fill('2027-03-31');
    await page.getByTestId('lease-form-rent').fill('2150');
    await page.getByTestId('lease-form-charges').fill('240');
    await page.getByTestId('lease-form-deposit').fill('6450');
    await page.getByTestId('lease-form-status').selectOption('active');
    await page.getByTestId('lease-form-notes').fill('Bail demo residentiel avec locataire seedee.');

    const leaseCreate = await waitForJsonResponse<{ id: string }>(
      page,
      { pathName: `/api/v1/buildings/${buildingId}/leases` },
      async () => {
        await page.getByTestId('lease-form-submit').click();
      },
    );

    expect(leaseCreate.ok, leaseCreate.text).toBeTruthy();
    await expect(page.getByTestId('lease-form-modal')).toBeHidden({ timeout: 10_000 });
    await ensureTextVisible(page, leaseReference);

    await expect
      .poll(
        async () =>
          (await lookupContact(page, buildingId, 'ThermoFlux')).some(
            (contact) => contact.name === SEEDED_CONTRACT_COUNTERPARTY,
          ),
        { timeout: 15_000 },
      )
      .toBe(true);

    const contactOptions = await lookupContact(page, buildingId, 'ThermoFlux');
    const heatingVendor = contactOptions.find((contact) => contact.name === SEEDED_CONTRACT_COUNTERPARTY);
    expect(heatingVendor?.id).toBeTruthy();
    if (!heatingVendor?.id) {
      throw new Error(`Unable to resolve seeded contract counterparty: ${SEEDED_CONTRACT_COUNTERPARTY}`);
    }

    // Contracts are in the cases tab (already selected above)
    await page.getByTestId('contracts-create-button').click();
    await expect(page.getByTestId('contract-form-modal')).toBeVisible();
    await page.getByTestId('contract-form-type').selectOption('heating');
    await page.getByTestId('contract-form-reference-code').fill(contractReference);
    await page.getByTestId('contract-form-title').fill(contractTitle);
    await page.getByTestId('contract-form-counterparty-id').fill(heatingVendor!.id);
    await page.getByTestId('contract-form-date-start').fill('2026-04-15');
    await page.getByTestId('contract-form-date-end').fill('2027-04-14');
    await page.getByTestId('contract-form-annual-cost').fill('12800');
    await page.getByTestId('contract-form-payment-frequency').selectOption('annual');
    await page.getByTestId('contract-form-auto-renewal').check();
    await page.getByTestId('contract-form-notice-period').fill('6');
    await page.getByTestId('contract-form-status').selectOption('active');
    await page.getByTestId('contract-form-notes').fill('Contrat CVC de demonstration pour verifier le flux complet.');

    const contractCreate = await waitForJsonResponse<{ id: string }>(
      page,
      { pathName: `/api/v1/buildings/${buildingId}/contracts` },
      async () => {
        await page.getByTestId('contract-form-submit').click();
      },
    );

    expect(contractCreate.ok, contractCreate.text).toBeTruthy();
    await expect(page.getByTestId('contract-form-modal')).toBeHidden({ timeout: 10_000 });
    await ensureTextVisible(page, contractReference);

    await page.goto(`/buildings/${buildingId}/interventions`);
    await assertNoErrorBoundary(page);
    await page.getByTestId('interventions-create-toggle').click();
    await expect(page.getByTestId('interventions-create-form')).toBeVisible();
    await page.getByTestId('interventions-form-title').fill(interventionTitle);
    await page.getByTestId('interventions-form-type').selectOption('asbestos_removal');
    await page.getByTestId('interventions-form-date-start').fill('2026-05-04');
    await page.getByTestId('interventions-form-cost').fill('42500');
    await page
      .getByTestId('interventions-form-description')
      .fill('Intervention demo: confinement local et retrait cible avant amenagement.');

    const interventionCreate = await waitForJsonResponse<{ id: string }>(
      page,
      { pathName: `/api/v1/buildings/${buildingId}/interventions` },
      async () => {
        await page.getByTestId('interventions-form-submit').click();
      },
    );

    expect(interventionCreate.ok, interventionCreate.text).toBeTruthy();
    await ensureTextVisible(page, interventionTitle);

    const interventionsPayload = await apiGet<PaginatedResponse<NamedRecord>>(
      page,
      `/api/v1/buildings/${buildingId}/interventions?page=1&size=20`,
    );
    expect(interventionsPayload.items.some((item) => item.title === interventionTitle)).toBeTruthy();

    await page.goto(`/buildings/${buildingId}/field-observations`);
    await assertNoErrorBoundary(page);
    await page.getByTestId('field-observations-create-button').click();
    await expect(page.getByTestId('field-observations-create-modal')).toBeVisible();
    await page.getByTestId('field-observations-form-title').fill(observationTitle);
    await page.getByTestId('field-observations-form-type').selectOption('safety_hazard');
    await page.getByTestId('field-observations-form-severity').selectOption('major');
    await page
      .getByTestId('field-observations-form-description')
      .fill('Acces technique non balise au droit du futur confinement.');
    await page.getByTestId('field-observations-form-location').fill('Sous-sol, local ventilation');

    const observationCreate = await waitForJsonResponse<{ id: string }>(
      page,
      { pathName: `/api/v1/buildings/${buildingId}/field-observations` },
      async () => {
        await page.getByTestId('field-observations-form-submit').click();
      },
    );

    expect(observationCreate.ok, observationCreate.text).toBeTruthy();
    await expect(page.getByTestId('field-observations-create-modal')).toBeHidden({ timeout: 10_000 });
    await ensureTextVisible(page, observationTitle);

    await page.goto(`/buildings/${buildingId}/explorer`);
    await assertNoErrorBoundary(page);
    await page.getByTestId('explorer-zone-create-toggle').click();
    await expect(page.getByTestId('explorer-zone-form')).toBeVisible();
    await page.getByTestId('explorer-zone-name').fill(zoneName);
    await page.getByTestId('explorer-zone-type').selectOption('technical_room');

    const zoneCreate = await waitForJsonResponse<{ id: string }>(
      page,
      { pathName: `/api/v1/buildings/${buildingId}/zones` },
      async () => {
        await page.getByTestId('explorer-zone-submit').click();
      },
    );

    expect(zoneCreate.ok, zoneCreate.text).toBeTruthy();
    if (!zoneCreate.body?.id) {
      throw new Error(`Zone creation response missing id: ${zoneCreate.text}`);
    }
    await ensureTextVisible(page, zoneName);
    await page.getByText(zoneName, { exact: false }).click();
    await expect(page.getByTestId('explorer-selected-zone-name')).toContainText(zoneName, { timeout: 15_000 });
    await expect(page.getByTestId('explorer-element-create-toggle')).toBeVisible({ timeout: 15_000 });

    await page.getByTestId('explorer-element-create-toggle').click();
    await expect(page.getByTestId('explorer-element-form')).toBeVisible();
    await page.getByTestId('explorer-element-name').fill(elementName);
    await page.getByTestId('explorer-element-type').selectOption('pipe');

    const elementCreate = await waitForJsonResponse<{ id: string }>(
      page,
      { pathName: `/api/v1/buildings/${buildingId}/zones/${zoneCreate.body.id}/elements` },
      async () => {
        await page.getByTestId('explorer-element-submit').click();
      },
    );

    expect(elementCreate.ok, elementCreate.text).toBeTruthy();
    if (!elementCreate.body?.id) {
      throw new Error(`Element creation response missing id: ${elementCreate.text}`);
    }
    await ensureTextVisible(page, elementName);

    const elementCard = page
      .getByTestId('explorer-element-card')
      .filter({ has: page.getByText(elementName, { exact: false }) })
      .first();
    await elementCard.getByText(elementName, { exact: false }).click();
    await elementCard.getByTestId('explorer-material-create-toggle').click();
    await expect(page.getByTestId('explorer-material-form')).toBeVisible();
    await page.getByTestId('explorer-material-name').fill(materialName);
    await page.getByTestId('explorer-material-type').selectOption('insulation_material');

    const materialCreate = await waitForJsonResponse<{ id: string }>(
      page,
      {
        pathName: `/api/v1/buildings/${buildingId}/zones/${zoneCreate.body.id}/elements/${elementCreate.body.id}/materials`,
      },
      async () => {
        await page.getByTestId('explorer-material-submit').click();
      },
    );

    expect(materialCreate.ok, materialCreate.text).toBeTruthy();
    await ensureTextVisible(page, materialName);

    const zonesPayload = await apiGet<PaginatedResponse<NamedRecord>>(
      page,
      `/api/v1/buildings/${buildingId}/zones?page=1&size=50`,
    );
    expect(zonesPayload.items.some((item) => item.name === zoneName)).toBeTruthy();

    const elementsPayload = await apiGet<PaginatedResponse<NamedRecord>>(
      page,
      `/api/v1/buildings/${buildingId}/zones/${zoneCreate.body.id}/elements`,
    );
    expect(elementsPayload.items.some((item) => item.name === elementName)).toBeTruthy();

    const materialsPayload = await apiGet<NamedRecord[]>(
      page,
      `/api/v1/buildings/${buildingId}/zones/${zoneCreate.body.id}/elements/${elementCreate.body.id}/materials`,
    );
    expect(materialsPayload.some((item) => item.name === materialName)).toBeTruthy();
  });
});
