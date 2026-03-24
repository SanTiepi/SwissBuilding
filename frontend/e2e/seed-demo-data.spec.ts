import { test, expect, APIRequestContext } from '@playwright/test';

/**
 * Seed demo data into a running SwissBuilding instance.
 *
 * Target: http://194.93.48.163:8080
 * Run:    npx playwright test e2e/seed-demo-data.spec.ts --config playwright.config.ts
 *
 * This script uses the REST API directly (no UI interactions for creation)
 * then verifies the data is visible in the UI.
 */

const BASE_URL = 'http://194.93.48.163:8080';
const API = `${BASE_URL}/api`;
const CREDENTIALS = { email: 'admin@swissbuildingos.ch', password: 'Admin2026!' };

// ---------------------------------------------------------------------------
// Demo buildings
// ---------------------------------------------------------------------------

interface DemoBuilding {
  address: string;
  postal_code: string;
  city: string;
  canton: string;
  building_type: string;
  construction_year: number | null;
  floors_above: number;
  floors_below: number;
  surface_area_m2: number;
  latitude: number;
  longitude: number;
  diagnostics: DemoDiagnostic[];
}

interface DemoDiagnostic {
  diagnostic_type: string; // asbestos, pcb, lead, hap, radon, full
  diagnostic_context: string;
  date_inspection: string; // YYYY-MM-DD
  laboratory: string | null;
  methodology: string | null;
  summary: string | null;
  samples: DemoSample[];
}

interface DemoSample {
  sample_number: string;
  location_floor: string;
  location_room: string;
  material_category: string;
  material_description: string;
  pollutant_type: string;
  pollutant_subtype: string | null;
  concentration: number;
  unit: string;
  material_state: string;
}

const DEMO_BUILDINGS: DemoBuilding[] = [
  // 1 — Lausanne, pre-1960, asbestos suspected
  {
    address: 'Rue du Bourg 12',
    postal_code: '1003',
    city: 'Lausanne',
    canton: 'VD',
    building_type: 'residential',
    construction_year: 1955,
    floors_above: 4,
    floors_below: 1,
    surface_area_m2: 620,
    latitude: 46.5197,
    longitude: 6.6323,
    diagnostics: [
      {
        diagnostic_type: 'asbestos',
        diagnostic_context: 'AvT',
        date_inspection: '2025-09-15',
        laboratory: 'Suisse Labo SA',
        methodology: 'PLM + MET conforme FACH 2021',
        summary:
          'Présence confirmée d\'amiante chrysotile dans les colles de faïence de la cuisine et dans les joints de fenêtre. Matériaux en état moyen. Mesures de confinement recommandées avant travaux.',
        samples: [
          {
            sample_number: 'LAU-A-001',
            location_floor: '2ème étage',
            location_room: 'Cuisine',
            material_category: 'colle',
            material_description: 'Colle de faïence grise',
            pollutant_type: 'asbestos',
            pollutant_subtype: 'chrysotile',
            concentration: 8.5,
            unit: 'percent_weight',
            material_state: 'moyen',
          },
          {
            sample_number: 'LAU-A-002',
            location_floor: '1er étage',
            location_room: 'Salon',
            material_category: 'joint',
            material_description: 'Joint de fenêtre mastic',
            pollutant_type: 'asbestos',
            pollutant_subtype: 'chrysotile',
            concentration: 3.2,
            unit: 'percent_weight',
            material_state: 'mauvais',
          },
          {
            sample_number: 'LAU-A-003',
            location_floor: 'Sous-sol',
            location_room: 'Chaufferie',
            material_category: 'calorifugeage',
            material_description: 'Isolation tuyaux chauffage',
            pollutant_type: 'asbestos',
            pollutant_subtype: 'amosite',
            concentration: 45.0,
            unit: 'percent_weight',
            material_state: 'degrade',
          },
        ],
      },
    ],
  },

  // 2 — Genève, 1975, PCB + lead
  {
    address: 'Chemin des Fleurs 8',
    postal_code: '1204',
    city: 'Genève',
    canton: 'GE',
    building_type: 'residential',
    construction_year: 1975,
    floors_above: 6,
    floors_below: 2,
    surface_area_m2: 1450,
    latitude: 46.2044,
    longitude: 6.1432,
    diagnostics: [
      {
        diagnostic_type: 'pcb',
        diagnostic_context: 'AvT',
        date_inspection: '2025-11-03',
        laboratory: 'AnalyticaLab Genève',
        methodology: 'GC-MS selon directive PCB OFEV 2003',
        summary:
          'Joints de dilatation entre dalles contaminés aux PCB avec concentration dépassant le seuil OLED de 50 mg/kg. Assainissement obligatoire selon OTConst.',
        samples: [
          {
            sample_number: 'GEN-P-001',
            location_floor: '3ème étage',
            location_room: 'Façade sud',
            material_category: 'joint',
            material_description: 'Joint élastique de dilatation entre dalles',
            pollutant_type: 'pcb',
            pollutant_subtype: 'PCB-138',
            concentration: 12500,
            unit: 'mg_per_kg',
            material_state: 'moyen',
          },
          {
            sample_number: 'GEN-P-002',
            location_floor: '1er étage',
            location_room: 'Cage d\'escalier',
            material_category: 'joint',
            material_description: 'Joint de vitrage intérieur',
            pollutant_type: 'pcb',
            pollutant_subtype: 'PCB-153',
            concentration: 340,
            unit: 'mg_per_kg',
            material_state: 'bon',
          },
        ],
      },
      {
        diagnostic_type: 'lead',
        diagnostic_context: 'AvT',
        date_inspection: '2025-11-04',
        laboratory: 'AnalyticaLab Genève',
        methodology: 'XRF in-situ + ICP-MS confirmation',
        summary:
          'Peintures au plomb détectées sur les boiseries des fenêtres et portes palières. Concentration supérieure à la valeur limite OLED. Décapage nécessaire avant rénovation.',
        samples: [
          {
            sample_number: 'GEN-L-001',
            location_floor: '2ème étage',
            location_room: 'Chambre principale',
            material_category: 'peinture',
            material_description: 'Peinture blanc cassé sur boiserie fenêtre',
            pollutant_type: 'lead',
            pollutant_subtype: null,
            concentration: 18500,
            unit: 'mg_per_kg',
            material_state: 'moyen',
          },
        ],
      },
    ],
  },

  // 3 — Zürich, modern 2010, clean
  {
    address: 'Bahnhofstrasse 45',
    postal_code: '8001',
    city: 'Zürich',
    canton: 'ZH',
    building_type: 'commercial',
    construction_year: 2010,
    floors_above: 8,
    floors_below: 3,
    surface_area_m2: 3200,
    latitude: 47.3769,
    longitude: 8.5417,
    diagnostics: [
      {
        diagnostic_type: 'full',
        diagnostic_context: 'AvT',
        date_inspection: '2026-01-20',
        laboratory: 'SGS Zürich',
        methodology: 'Volldiagnostik gemäss SUVA / FACH Richtlinien',
        summary:
          'Gebäude Baujahr 2010 — keine Schadstoffe nachgewiesen. Alle Proben unterhalb der Grenzwerte. Gebäude ist unbedenklich für Renovations- und Rückbauarbeiten.',
        samples: [
          {
            sample_number: 'ZUR-F-001',
            location_floor: '4. OG',
            location_room: 'Büro 401',
            material_category: 'peinture',
            material_description: 'Wandfarbe Dispersionsfarbe weiss',
            pollutant_type: 'lead',
            pollutant_subtype: null,
            concentration: 12,
            unit: 'mg_per_kg',
            material_state: 'bon',
          },
          {
            sample_number: 'ZUR-F-002',
            location_floor: '1. UG',
            location_room: 'Technikraum',
            material_category: 'joint',
            material_description: 'Fugenmasse Polyurethan',
            pollutant_type: 'pcb',
            pollutant_subtype: null,
            concentration: 2.1,
            unit: 'mg_per_kg',
            material_state: 'bon',
          },
        ],
      },
    ],
  },

  // 4 — Sion, 1985, partial diagnostics
  {
    address: 'Avenue de la Gare 3',
    postal_code: '1950',
    city: 'Sion',
    canton: 'VS',
    building_type: 'mixed',
    construction_year: 1985,
    floors_above: 5,
    floors_below: 1,
    surface_area_m2: 980,
    latitude: 46.2333,
    longitude: 7.3603,
    diagnostics: [
      {
        diagnostic_type: 'asbestos',
        diagnostic_context: 'AvT',
        date_inspection: '2026-02-10',
        laboratory: 'ValaisLab Sàrl',
        methodology: 'PLM conformément directive FACH',
        summary:
          'Diagnostic partiel — seuls les communs et la chaufferie ont été inspectés. Pas d\'amiante détecté dans les zones investiguées. Investigation complémentaire nécessaire pour les appartements.',
        samples: [
          {
            sample_number: 'SIO-A-001',
            location_floor: 'Sous-sol',
            location_room: 'Chaufferie',
            material_category: 'calorifugeage',
            material_description: 'Isolation conduits chauffage',
            pollutant_type: 'asbestos',
            pollutant_subtype: null,
            concentration: 0,
            unit: 'percent_weight',
            material_state: 'bon',
          },
        ],
      },
    ],
  },

  // 5 — Fribourg, industrial, HAP + amiante
  {
    address: 'Rue de l\'Industrie 22',
    postal_code: '1700',
    city: 'Fribourg',
    canton: 'FR',
    building_type: 'industrial',
    construction_year: 1968,
    floors_above: 2,
    floors_below: 1,
    surface_area_m2: 2100,
    latitude: 46.8065,
    longitude: 7.1620,
    diagnostics: [
      {
        diagnostic_type: 'hap',
        diagnostic_context: 'AvT',
        date_inspection: '2025-08-22',
        laboratory: 'Fribourg Environnement Lab',
        methodology: 'GC-MS analyse HAP 16 EPA',
        summary:
          'HAP détectés dans l\'étanchéité de la toiture (goudron) et dans les enrobés bitumineux du sol de l\'atelier. Concentrations supérieures au seuil OLED. Élimination en tant que déchet spécial requise.',
        samples: [
          {
            sample_number: 'FRI-H-001',
            location_floor: 'Toiture',
            location_room: 'Étanchéité toiture plate',
            material_category: 'etancheite',
            material_description: 'Membrane bitumineuse noire',
            pollutant_type: 'hap',
            pollutant_subtype: 'benzo[a]pyrène',
            concentration: 285,
            unit: 'mg_per_kg',
            material_state: 'moyen',
          },
          {
            sample_number: 'FRI-H-002',
            location_floor: 'Rez-de-chaussée',
            location_room: 'Atelier principal',
            material_category: 'revetement_sol',
            material_description: 'Enrobé bitumineux sol industriel',
            pollutant_type: 'hap',
            pollutant_subtype: 'naphtalène',
            concentration: 1540,
            unit: 'mg_per_kg',
            material_state: 'mauvais',
          },
        ],
      },
      {
        diagnostic_type: 'asbestos',
        diagnostic_context: 'AvT',
        date_inspection: '2025-08-23',
        laboratory: 'Fribourg Environnement Lab',
        methodology: 'PLM + MET conforme FACH 2021',
        summary:
          'Amiante chrysotile identifié dans les plaques ondulées Eternit de la toiture et dans les dalles de sol vinyl-amiante de l\'atelier. État dégradé pour la toiture. Assainissement urgent recommandé.',
        samples: [
          {
            sample_number: 'FRI-A-001',
            location_floor: 'Toiture',
            location_room: 'Couverture',
            material_category: 'fibrociment',
            material_description: 'Plaques ondulées Eternit',
            pollutant_type: 'asbestos',
            pollutant_subtype: 'chrysotile',
            concentration: 12.0,
            unit: 'percent_weight',
            material_state: 'degrade',
          },
          {
            sample_number: 'FRI-A-002',
            location_floor: 'Rez-de-chaussée',
            location_room: 'Atelier principal',
            material_category: 'revetement_sol',
            material_description: 'Dalles vinyl-amiante 30x30 cm',
            pollutant_type: 'asbestos',
            pollutant_subtype: 'chrysotile',
            concentration: 6.5,
            unit: 'percent_weight',
            material_state: 'moyen',
          },
          {
            sample_number: 'FRI-A-003',
            location_floor: '1er étage',
            location_room: 'Bureau',
            material_category: 'faux_plafond',
            material_description: 'Dalles de faux-plafond fibrées',
            pollutant_type: 'asbestos',
            pollutant_subtype: 'chrysotile',
            concentration: 4.2,
            unit: 'percent_weight',
            material_state: 'bon',
          },
        ],
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Test suite
// ---------------------------------------------------------------------------

test.describe('Seed demo data', () => {
  let token: string;
  const createdBuildingIds: string[] = [];

  test('authenticate and obtain JWT token', async ({ request }) => {
    const loginRes = await request.post(`${API}/auth/login`, {
      data: CREDENTIALS,
    });
    expect(loginRes.ok(), `Login failed: ${loginRes.status()}`).toBeTruthy();
    const body = await loginRes.json();
    expect(body.access_token).toBeTruthy();
    token = body.access_token;
  });

  test('create 5 demo buildings with diagnostics and samples', async ({ request }) => {
    // Obtain token first (cannot rely on test ordering in some runners)
    if (!token) {
      const loginRes = await request.post(`${API}/auth/login`, { data: CREDENTIALS });
      token = (await loginRes.json()).access_token;
    }

    const headers = { Authorization: `Bearer ${token}` };

    for (const demo of DEMO_BUILDINGS) {
      // --- Create building ---
      const buildingPayload = {
        address: demo.address,
        postal_code: demo.postal_code,
        city: demo.city,
        canton: demo.canton,
        building_type: demo.building_type,
        construction_year: demo.construction_year,
        floors_above: demo.floors_above,
        floors_below: demo.floors_below,
        surface_area_m2: demo.surface_area_m2,
        latitude: demo.latitude,
        longitude: demo.longitude,
      };

      const bldRes = await request.post(`${API}/buildings`, {
        headers,
        data: buildingPayload,
      });
      expect(
        bldRes.ok(),
        `Failed to create building "${demo.address}": ${bldRes.status()} ${await bldRes.text()}`
      ).toBeTruthy();
      const building = await bldRes.json();
      const buildingId: string = building.id;
      createdBuildingIds.push(buildingId);
      console.log(`  ✓ Building: ${demo.address} → ${buildingId}`);

      // --- Create diagnostics ---
      for (const diag of demo.diagnostics) {
        const diagPayload = {
          diagnostic_type: diag.diagnostic_type,
          diagnostic_context: diag.diagnostic_context,
          date_inspection: diag.date_inspection,
          laboratory: diag.laboratory,
          methodology: diag.methodology,
          summary: diag.summary,
        };

        const diagRes = await request.post(`${API}/buildings/${buildingId}/diagnostics`, {
          headers,
          data: diagPayload,
        });
        expect(
          diagRes.ok(),
          `Failed to create diagnostic "${diag.diagnostic_type}" for "${demo.address}": ${diagRes.status()} ${await diagRes.text()}`
        ).toBeTruthy();
        const diagnostic = await diagRes.json();
        const diagnosticId: string = diagnostic.id;
        console.log(`    ✓ Diagnostic: ${diag.diagnostic_type} → ${diagnosticId}`);

        // --- Create samples ---
        for (const sample of diag.samples) {
          const sampleRes = await request.post(`${API}/diagnostics/${diagnosticId}/samples`, {
            headers,
            data: sample,
          });
          expect(
            sampleRes.ok(),
            `Failed to create sample "${sample.sample_number}": ${sampleRes.status()} ${await sampleRes.text()}`
          ).toBeTruthy();
          console.log(`      ✓ Sample: ${sample.sample_number}`);
        }

        // --- Mark diagnostic as completed ---
        const updateRes = await request.put(`${API}/diagnostics/${diagnosticId}`, {
          headers,
          data: { status: 'completed' },
        });
        if (updateRes.ok()) {
          console.log(`    ✓ Diagnostic ${diagnosticId} marked as completed`);
        }
      }
    }

    expect(createdBuildingIds.length).toBe(5);
    console.log(`\n  ✅ Created ${createdBuildingIds.length} buildings with diagnostics and samples.`);
  });

  test('verify buildings appear in the API listing', async ({ request }) => {
    if (!token) {
      const loginRes = await request.post(`${API}/auth/login`, { data: CREDENTIALS });
      token = (await loginRes.json()).access_token;
    }
    const headers = { Authorization: `Bearer ${token}` };

    const listRes = await request.get(`${API}/buildings`, {
      headers,
      params: { size: 100 },
    });
    expect(listRes.ok()).toBeTruthy();
    const body = await listRes.json();
    const addresses: string[] = body.items.map((b: { address: string }) => b.address);

    for (const demo of DEMO_BUILDINGS) {
      expect(addresses, `Missing building: ${demo.address}`).toContain(demo.address);
    }
  });

  test('verify buildings are visible in the UI', async ({ page }) => {
    // Log in via UI
    await page.goto(`${BASE_URL}/login`);
    await page.locator('input[type="email"], input[name="email"]').fill(CREDENTIALS.email);
    await page.locator('input[type="password"], input[name="password"]').fill(CREDENTIALS.password);
    await page.locator('button[type="submit"]').click();

    // Wait for redirect to dashboard or buildings
    await page.waitForURL(/\/(dashboard|buildings)/, { timeout: 15000 });

    // Navigate to buildings list
    await page.goto(`${BASE_URL}/buildings`);
    await page.waitForLoadState('networkidle');

    // Wait for the list to render (look for any building card/row)
    await page.waitForSelector('[class*="card"], table tbody tr, [data-testid]', {
      timeout: 10000,
    });

    // Verify each demo building address is present on the page.
    // The list may be paginated, so we search broadly.
    for (const demo of DEMO_BUILDINGS) {
      // Search for the building if a search box is available
      const searchInput = page.locator(
        'input[type="text"][placeholder*="cherch"], input[type="text"][placeholder*="search"], input[type="text"][placeholder*="Such"], input[type="search"]'
      );
      if ((await searchInput.count()) > 0) {
        await searchInput.first().fill(demo.address);
        await page.waitForTimeout(800); // debounce
      }

      const addressLocator = page.getByText(demo.address, { exact: false });
      await expect(
        addressLocator.first(),
        `Building "${demo.address}" should be visible in the UI`
      ).toBeVisible({ timeout: 8000 });

      // Clear search for next iteration
      if ((await searchInput.count()) > 0) {
        await searchInput.first().clear();
        await page.waitForTimeout(500);
      }
    }
  });
});
