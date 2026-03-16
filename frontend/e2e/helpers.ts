import { Page } from '@playwright/test';

/**
 * Override a specific API route to return an error status.
 * Must be called AFTER mockApiRoutes() to take precedence.
 */
export async function mockApiError(
  page: Page,
  pattern: string | RegExp,
  status: number,
  body?: Record<string, unknown>,
) {
  await page.route(pattern, (route) =>
    route.fulfill({
      status,
      contentType: 'application/json',
      body: JSON.stringify(body ?? { detail: `Mocked ${status} error` }),
    })
  );
}

/**
 * Mock the auth store in localStorage to simulate a logged-in user.
 * This bypasses the login API call and directly injects auth state.
 */
export async function mockAuthState(page: Page, role: string = 'admin') {
  const fakeUser = {
    id: '00000000-0000-0000-0000-000000000001',
    email: 'admin@swissbuildingos.ch',
    first_name: 'Admin',
    last_name: 'Test',
    role,
    language: 'fr',
    is_active: true,
    organization_id: '00000000-0000-0000-0000-000000000010',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  const authState = {
    state: {
      token: 'fake-jwt-token-for-testing',
      user: fakeUser,
      isAuthenticated: true,
    },
    version: 0,
  };

  await page.addInitScript((state) => {
    localStorage.setItem('swissbuildingos-auth', JSON.stringify(state));
  }, authState);
}

/**
 * Mock API responses to avoid needing a running backend.
 */
export async function mockApiRoutes(page: Page) {
  // Auth
  await page.route('**/api/v1/auth/me', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: '00000000-0000-0000-0000-000000000001',
        email: 'admin@swissbuildingos.ch',
        first_name: 'Admin',
        last_name: 'Test',
        role: 'admin',
        language: 'fr',
        is_active: true,
        organization_id: '00000000-0000-0000-0000-000000000010',
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      }),
    })
  );

  // Buildings list (match with or without query params)
  await page.route(/\/api\/v1\/buildings(\?.*)?$/, (route) => {
    if (route.request().method() === 'POST') {
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'b4000000-0000-0000-0000-000000000004',
          egid: null,
          egrid: null,
          address: 'New Building Address',
          postal_code: '1000',
          city: 'Lausanne',
          canton: 'VD',
          building_type: 'residential',
          construction_year: 2000,
          floors_above: null,
          floors_below: null,
          surface_area_m2: null,
          volume_m3: null,
          status: 'active',
          owner_id: null,
          official_id: null,
          parcel_number: null,
          renovation_year: null,
          latitude: null,
          longitude: null,
          risk_scores: null,
          created_at: '2024-06-01T10:00:00Z',
          updated_at: '2024-06-01T10:00:00Z',
        }),
      });
    }
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: 'b1000000-0000-0000-0000-000000000001',
            egid: 1001,
            egrid: 'CH123456789',
            address: 'Rue de Bourg 1',
            postal_code: '1003',
            city: 'Lausanne',
            canton: 'VD',
            building_type: 'residential',
            construction_year: 1965,
            floors_above: 4,
            floors_below: 1,
            surface_area_m2: 850,
            volume_m3: null,
            status: 'active',
            owner_id: null,
            official_id: null,
            parcel_number: null,
            renovation_year: null,
            latitude: 46.5197,
            longitude: 6.6323,
            risk_scores: { overall_risk_level: 'high' },
            created_at: '2024-01-15T10:00:00Z',
            updated_at: '2024-06-01T14:00:00Z',
          },
          {
            id: 'b2000000-0000-0000-0000-000000000002',
            egid: 1002,
            egrid: 'CH987654321',
            address: 'Bahnhofstrasse 10',
            postal_code: '8001',
            city: 'Zurich',
            canton: 'ZH',
            building_type: 'commercial',
            construction_year: 1978,
            floors_above: 6,
            floors_below: 1,
            surface_area_m2: 2400,
            volume_m3: null,
            status: 'active',
            owner_id: null,
            official_id: null,
            parcel_number: null,
            renovation_year: null,
            latitude: 47.3769,
            longitude: 8.5417,
            risk_scores: { overall_risk_level: 'medium' },
            created_at: '2024-02-01T09:00:00Z',
            updated_at: '2024-05-15T11:00:00Z',
          },
          {
            id: 'b3000000-0000-0000-0000-000000000003',
            egid: 1003,
            egrid: 'CH111222333',
            address: 'Via Nassa 5',
            postal_code: '6900',
            city: 'Lugano',
            canton: 'TI',
            building_type: 'public',
            construction_year: 1955,
            floors_above: 3,
            floors_below: 1,
            surface_area_m2: 1200,
            volume_m3: null,
            status: 'active',
            owner_id: null,
            official_id: null,
            parcel_number: null,
            renovation_year: null,
            latitude: 46.0037,
            longitude: 8.9511,
            risk_scores: { overall_risk_level: 'critical' },
            created_at: '2024-03-01T08:00:00Z',
            updated_at: '2024-04-20T16:00:00Z',
          },
        ],
        total: 3,
        page: 1,
        size: 20,
        pages: 1,
      }),
    });
  });

  // Building detail
  await page.route('**/api/v1/buildings/b1000000-*', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'b1000000-0000-0000-0000-000000000001',
          egid: 1001,
          egrid: 'CH123456789',
          address: 'Rue de Bourg 1',
          postal_code: '1003',
          city: 'Lausanne',
          canton: 'VD',
          building_type: 'residential',
          construction_year: 1965,
          floors_above: 4,
          floors_below: 1,
          surface_area_m2: 850,
          volume_m3: null,
          status: 'active',
          owner_id: null,
          official_id: null,
          parcel_number: null,
          renovation_year: null,
          latitude: 46.5197,
          longitude: 6.6323,
          risk_scores: {
            overall_risk_level: 'high',
            asbestos_probability: 0.85,
            pcb_probability: 0.45,
            lead_probability: 0.60,
            hap_probability: 0.20,
            radon_probability: 0.15,
          },
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-06-01T14:00:00Z',
        }),
      });
    }
    return route.fulfill({ status: 200, body: '{}' });
  });

  // Diagnostics for building
  await page.route('**/api/v1/buildings/*/diagnostics', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'd1000000-0000-0000-0000-000000000001',
          building_id: 'b1000000-0000-0000-0000-000000000001',
          diagnostic_type: 'asbestos',
          diagnostic_context: 'AvT',
          status: 'completed',
          diagnostician_id: '00000000-0000-0000-0000-000000000002',
          laboratory: 'LabSwiss AG',
          date_inspection: '2024-03-15',
          report_file_path: null,
          summary: 'Amiante detecte dans les joints de facade',
          conclusion: null,
          methodology: null,
          suva_notification_required: false,
          suva_notification_date: null,
          canton_notification_date: null,
          laboratory_report_number: null,
          date_report: null,
          created_at: '2024-03-15T09:00:00Z',
          updated_at: '2024-03-20T14:00:00Z',
        },
      ]),
    })
  );

  // Diagnostic detail
  await page.route('**/api/v1/diagnostics/d1000000-*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'd1000000-0000-0000-0000-000000000001',
        building_id: 'b1000000-0000-0000-0000-000000000001',
        diagnostic_type: 'asbestos',
        diagnostic_context: 'AvT',
        status: 'completed',
        diagnostician_id: '00000000-0000-0000-0000-000000000002',
        laboratory: 'LabSwiss AG',
        date_inspection: '2024-03-15',
        report_file_path: null,
        summary: 'Amiante detecte dans les joints de facade',
        conclusion: null,
        methodology: null,
        suva_notification_required: false,
        suva_notification_date: null,
        canton_notification_date: null,
        laboratory_report_number: null,
        date_report: null,
        created_at: '2024-03-15T09:00:00Z',
        updated_at: '2024-03-20T14:00:00Z',
      }),
    })
  );

  // Samples for diagnostic
  await page.route('**/api/v1/diagnostics/*/samples', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 's1000000-0000-0000-0000-000000000001',
          diagnostic_id: 'd1000000-0000-0000-0000-000000000001',
          sample_number: 'ECH-001',
          location_floor: '2',
          location_room: 'Couloir',
          location_detail: 'Joint de facade',
          material_category: 'hard',
          material_description: 'Fibre-ciment',
          material_state: 'bon',
          pollutant_type: 'asbestos',
          pollutant_subtype: 'chrysotile',
          concentration: 2.5,
          unit: 'percent_weight',
          threshold_exceeded: true,
          risk_level: 'high',
          cfst_work_category: 'major',
          action_required: 'Desamiantage obligatoire avant travaux',
          waste_disposal_type: 'special',
          notes: null,
          created_at: '2024-03-15T10:00:00Z',
        },
      ]),
    })
  );

  // Documents
  await page.route('**/api/v1/buildings/*/documents', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  );

  // Events
  await page.route('**/api/v1/buildings/*/events', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  );

  // Risk analysis (building risk score - matches RiskScoreRead schema)
  await page.route('**/api/v1/risk-analysis/building/**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'r1000000-0000-0000-0000-000000000001',
        building_id: 'b1000000-0000-0000-0000-000000000001',
        overall_risk_level: 'high',
        asbestos_probability: 0.85,
        pcb_probability: 0.45,
        lead_probability: 0.60,
        hap_probability: 0.20,
        radon_probability: 0.15,
        confidence: 0.78,
        factors_json: null,
        data_source: 'algorithm',
        last_updated: '2024-06-01T14:00:00Z',
      }),
    })
  );

  // Pollutant map
  await page.route('**/api/v1/pollutant-map/**', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  );

  // Users
  await page.route('**/api/v1/users*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [],
        total: 0,
        page: 1,
        size: 20,
        pages: 0,
      }),
    })
  );

  // Login
  await page.route('**/api/v1/auth/login', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        access_token: 'fake-jwt-token',
        token_type: 'bearer',
        expires_in: 28800,
        user: {
          id: '00000000-0000-0000-0000-000000000001',
          email: 'admin@swissbuildingos.ch',
          first_name: 'Admin',
          last_name: 'Test',
          role: 'admin',
          language: 'fr',
          is_active: true,
          organization_id: '00000000-0000-0000-0000-000000000010',
          created_at: '2024-01-01T00:00:00Z',
          updated_at: '2024-01-01T00:00:00Z',
        },
      }),
    })
  );

  // Risk simulation
  await page.route('**/api/v1/risk-analysis/simulate', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        building_id: 'b1000000-0000-0000-0000-000000000001',
        renovation_type: 'full_renovation',
        pollutant_risks: [
          {
            pollutant: 'asbestos',
            probability: 0.85,
            risk_level: 'high',
            exposure_factor: 0.7,
            materials_at_risk: ['Joint de facade', 'Fibre-ciment'],
            estimated_cost_chf: 45000,
          },
          {
            pollutant: 'pcb',
            probability: 0.45,
            risk_level: 'medium',
            exposure_factor: 0.5,
            materials_at_risk: ['Joints d\'etancheite'],
            estimated_cost_chf: 30000,
          },
        ],
        total_estimated_cost_chf: 75000,
        required_diagnostics: ['Diagnostic amiante obligatoire', 'Analyse PCB recommandee'],
        compliance_requirements: [
          {
            requirement: 'Diagnostic amiante avant travaux',
            legal_reference: 'OTConst Art. 60a',
            mandatory: true,
            deadline_days: 30,
          },
        ],
        timeline_weeks: 12,
      }),
    })
  );

  // Zones for building
  await page.route('**/api/v1/buildings/*/zones*', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'z1000000-0000-0000-0000-000000000001',
              building_id: 'b1000000-0000-0000-0000-000000000001',
              parent_zone_id: null,
              zone_type: 'floor',
              name: 'Rez-de-chaussee',
              description: null,
              floor_number: 0,
              surface_area_m2: 200,
              created_by: null,
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-01T00:00:00Z',
              children_count: 2,
              elements_count: 5,
            },
            {
              id: 'z2000000-0000-0000-0000-000000000002',
              building_id: 'b1000000-0000-0000-0000-000000000001',
              parent_zone_id: null,
              zone_type: 'basement',
              name: 'Sous-sol',
              description: null,
              floor_number: -1,
              surface_area_m2: 150,
              created_by: null,
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-01T00:00:00Z',
              children_count: 0,
              elements_count: 3,
            },
          ],
          total: 2,
          page: 1,
          size: 50,
          pages: 1,
        }),
      });
    }
    return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({}) });
  });

  // Elements for zone
  await page.route('**/api/v1/buildings/*/zones/*/elements*', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'e1000000-0000-0000-0000-000000000001',
            zone_id: 'z1000000-0000-0000-0000-000000000001',
            element_type: 'wall',
            name: 'Mur porteur nord',
            description: null,
            condition: 'fair',
            installation_year: 1965,
            last_inspected_at: null,
            created_by: null,
            created_at: '2024-01-01T00:00:00Z',
            updated_at: '2024-01-01T00:00:00Z',
            materials_count: 2,
          },
        ]),
      });
    }
    return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({}) });
  });

  // Materials for element
  await page.route('**/api/v1/buildings/*/zones/*/elements/*/materials*', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'm1000000-0000-0000-0000-000000000001',
            element_id: 'e1000000-0000-0000-0000-000000000001',
            material_type: 'plaster',
            name: 'Enduit interieur',
            description: null,
            manufacturer: null,
            installation_year: 1965,
            contains_pollutant: false,
            pollutant_type: null,
            pollutant_confirmed: false,
            sample_id: null,
            source: 'visual_inspection',
            notes: null,
            created_by: null,
            created_at: '2024-01-01T00:00:00Z',
          },
        ]),
      });
    }
    return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({}) });
  });

  // Interventions for building
  await page.route('**/api/v1/buildings/*/interventions*', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: 'i1000000-0000-0000-0000-000000000001',
              building_id: 'b1000000-0000-0000-0000-000000000001',
              intervention_type: 'renovation',
              title: 'Renovation facade nord',
              description: 'Remplacement des joints amiantees',
              status: 'planned',
              date_start: '2024-06-01',
              date_end: null,
              contractor_name: 'SanaCore AG',
              contractor_id: null,
              cost_chf: 45000,
              zones_affected: null,
              materials_used: null,
              diagnostic_id: null,
              notes: null,
              created_by: null,
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-01T00:00:00Z',
            },
          ],
          total: 1,
          page: 1,
          size: 20,
          pages: 1,
        }),
      });
    }
    return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({}) });
  });

  // Plans for building
  await page.route('**/api/v1/buildings/*/plans*', (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'p1000000-0000-0000-0000-000000000001',
            building_id: 'b1000000-0000-0000-0000-000000000001',
            plan_type: 'floor_plan',
            title: 'Plan rez-de-chaussee',
            description: null,
            floor_number: 0,
            version: '1.0',
            file_path: '/files/plans/plan-rdc.pdf',
            file_name: 'plan-rdc.pdf',
            mime_type: 'application/pdf',
            file_size_bytes: 2048000,
            zone_id: null,
            uploaded_by: null,
            created_at: '2024-01-01T00:00:00Z',
          },
        ]),
      });
    }
    return route.fulfill({ status: 201, contentType: 'application/json', body: JSON.stringify({}) });
  });

  // Quality score
  await page.route('**/api/v1/buildings/*/quality', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        overall_score: 0.65,
        sections: {
          identity: { score: 1.0, details: 'Complete' },
          diagnostics: { score: 0.8, details: 'Has diagnostics' },
          zones: { score: 0.5, details: 'Some zones defined' },
          materials: { score: 0.3, details: 'Few materials' },
          interventions: { score: 0.7, details: 'Some interventions' },
          documents: { score: 0.5, details: 'Some documents' },
          plans: { score: 0.6, details: 'Has plans' },
          evidence: { score: 0.8, details: 'Good evidence' },
        },
        missing: ['zones_incomplete', 'materials_missing'],
      }),
    })
  );

  // Dossier
  await page.route('**/api/v1/buildings/*/dossier/preview', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'text/html',
      body: '<html><body><h1>Dossier Preview</h1></body></html>',
    })
  );
  await page.route('**/api/v1/buildings/*/dossier', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ job_id: 'job-001', status: 'queued' }),
    })
  );

  // Evidence
  await page.route('**/api/v1/evidence*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    })
  );

  // Readiness evaluate-all
  await page.route(/\/api\/v1\/buildings\/[^/]+\/readiness\/evaluate-all$/, (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'ra100000-0000-0000-0000-000000000010',
          building_id: 'b1000000-0000-0000-0000-000000000001',
          readiness_type: 'safe_to_start',
          status: 'conditionally_ready',
          score: 0.72,
          checks_json: [
            { label: 'Diagnostic amiante', passed: true, details: null },
            { label: 'Plan de desamiantage', passed: false, details: 'Manquant' },
            { label: 'Notification SUVA', passed: true, details: null },
          ],
          blockers_json: [],
          conditions_json: [
            { label: 'Plan de desamiantage requis', details: 'Avant demarrage des travaux' },
          ],
          assessed_at: '2024-06-15T10:00:00Z',
          valid_until: null,
          assessed_by: '00000000-0000-0000-0000-000000000001',
          notes: null,
        },
        {
          id: 'ra200000-0000-0000-0000-000000000020',
          building_id: 'b1000000-0000-0000-0000-000000000001',
          readiness_type: 'safe_to_tender',
          status: 'blocked',
          score: 0.3,
          checks_json: [
            { label: 'Diagnostic complet', passed: false, details: 'PCB manquant' },
            { label: 'Estimation des couts', passed: true, details: null },
          ],
          blockers_json: [
            { label: 'Evaluation PCB absente', severity: 'critical', details: null },
          ],
          conditions_json: [],
          assessed_at: '2024-06-15T10:00:00Z',
          valid_until: null,
          assessed_by: '00000000-0000-0000-0000-000000000001',
          notes: null,
        },
        {
          id: 'ra300000-0000-0000-0000-000000000030',
          building_id: 'b1000000-0000-0000-0000-000000000001',
          readiness_type: 'safe_to_reopen',
          status: 'ready',
          score: 0.95,
          checks_json: [
            { label: 'Mesures post-travaux', passed: true, details: null },
            { label: 'Certificat de conformite', passed: true, details: null },
          ],
          blockers_json: [],
          conditions_json: [],
          assessed_at: '2024-06-15T10:00:00Z',
          valid_until: null,
          assessed_by: '00000000-0000-0000-0000-000000000001',
          notes: null,
        },
        {
          id: 'ra400000-0000-0000-0000-000000000040',
          building_id: 'b1000000-0000-0000-0000-000000000001',
          readiness_type: 'safe_to_requalify',
          status: 'not_ready',
          score: 0.15,
          checks_json: [
            { label: 'Documentation complete', passed: false, details: 'Incomplet' },
            { label: 'Verification independante', passed: false, details: 'Non effectuee' },
          ],
          blockers_json: [
            { label: 'Documentation incomplete', severity: 'high', details: 'Rapports manquants' },
          ],
          conditions_json: [],
          assessed_at: '2024-06-15T10:00:00Z',
          valid_until: null,
          assessed_by: '00000000-0000-0000-0000-000000000001',
          notes: null,
        },
      ]),
    });
  });

  // Readiness assessments for building
  await page.route(/\/api\/v1\/buildings\/[^/]+\/readiness(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: 'ra100000-0000-0000-0000-000000000001',
            building_id: 'b1000000-0000-0000-0000-000000000001',
            readiness_type: 'safe_to_start',
            status: 'conditionally_ready',
            score: 0.65,
            checks_json: [
              { label: 'Diagnostic amiante', passed: true, details: null },
              { label: 'Plan de desamiantage', passed: false, details: 'Manquant' },
            ],
            blockers_json: [
              { label: 'Plan de retrait amiante requis', severity: 'high', details: null },
            ],
            conditions_json: [],
            assessed_at: '2024-06-01T14:00:00Z',
            valid_until: null,
            assessed_by: null,
            notes: null,
          },
          {
            id: 'ra200000-0000-0000-0000-000000000002',
            building_id: 'b1000000-0000-0000-0000-000000000001',
            readiness_type: 'safe_to_tender',
            status: 'not_ready',
            score: 0.3,
            checks_json: [],
            blockers_json: [
              { label: 'Evaluation PCB absente', severity: 'critical', details: null },
              { label: 'Devis non finalise', severity: 'high', details: null },
            ],
            conditions_json: [],
            assessed_at: '2024-06-01T14:00:00Z',
            valid_until: null,
            assessed_by: null,
            notes: null,
          },
        ],
        total: 2,
        page: 1,
        size: 50,
        pages: 1,
      }),
    });
  });

  // Trust scores for building
  await page.route(/\/api\/v1\/buildings\/[^/]+\/trust-scores(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: 'ts100000-0000-0000-0000-000000000001',
            building_id: 'b1000000-0000-0000-0000-000000000001',
            overall_score: 0.72,
            percent_proven: 45,
            percent_inferred: 25,
            percent_declared: 20,
            percent_obsolete: 7,
            percent_contradictory: 3,
            total_data_points: 42,
            proven_count: 19,
            inferred_count: 11,
            declared_count: 8,
            obsolete_count: 3,
            contradictory_count: 1,
            trend: 'improving',
            previous_score: 0.65,
            assessed_at: '2024-06-01T14:00:00Z',
            assessed_by: 'system',
            notes: null,
          },
        ],
        total: 1,
        page: 1,
        size: 1,
        pages: 1,
      }),
    });
  });

  // Unknown issues for building
  await page.route(/\/api\/v1\/buildings\/[^/]+\/unknowns(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: 'ui100000-0000-0000-0000-000000000001',
            building_id: 'b1000000-0000-0000-0000-000000000001',
            unknown_type: 'missing_pollutant_evaluation',
            severity: 'high',
            status: 'open',
            title: 'Evaluation PCB manquante',
            description: 'Aucun diagnostic PCB pour ce batiment',
            entity_type: 'pollutant:pcb',
            entity_id: null,
            blocks_readiness: true,
            readiness_types_affected: 'safe_to_start,safe_to_tender',
            resolved_by: null,
            resolved_at: null,
            resolution_notes: null,
            detected_by: 'system',
            created_at: '2024-05-15T10:00:00Z',
          },
          {
            id: 'ui200000-0000-0000-0000-000000000002',
            building_id: 'b1000000-0000-0000-0000-000000000001',
            unknown_type: 'uninspected_zone',
            severity: 'medium',
            status: 'open',
            title: 'Sous-sol non inspecte',
            description: 'Zone sous-sol sans inspection documentee',
            entity_type: 'zone',
            entity_id: 'z2000000-0000-0000-0000-000000000002',
            blocks_readiness: false,
            readiness_types_affected: null,
            resolved_by: null,
            resolved_at: null,
            resolution_notes: null,
            detected_by: 'system',
            created_at: '2024-05-15T10:00:00Z',
          },
        ],
        total: 2,
        page: 1,
        size: 50,
        pages: 1,
      }),
    });
  });

  // Change signals for building
  await page.route(/\/api\/v1\/buildings\/[^/]+\/change-signals(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: 'cs100000-0000-0000-0000-000000000001',
            building_id: 'b1000000-0000-0000-0000-000000000001',
            signal_type: 'diagnostic_completed',
            severity: 'info',
            status: 'active',
            title: 'Diagnostic amiante termine',
            description: 'Le diagnostic amiante a ete complete',
            source: 'diagnostic',
            entity_type: 'diagnostic',
            entity_id: 'd1000000-0000-0000-0000-000000000001',
            metadata_json: null,
            detected_at: '2024-03-20T14:00:00Z',
            acknowledged_by: null,
            acknowledged_at: null,
          },
          {
            id: 'cs200000-0000-0000-0000-000000000002',
            building_id: 'b1000000-0000-0000-0000-000000000001',
            signal_type: 'new_positive_sample',
            severity: 'warning',
            status: 'active',
            title: 'Echantillon positif amiante',
            description: "Nouvel echantillon positif pour l'amiante detecte",
            source: 'sample',
            entity_type: 'sample',
            entity_id: 's1000000-0000-0000-0000-000000000001',
            metadata_json: null,
            detected_at: '2024-03-15T10:00:00Z',
            acknowledged_by: null,
            acknowledged_at: null,
          },
        ],
        total: 2,
        page: 1,
        size: 50,
        pages: 1,
      }),
    });
  });

  // Post-works compare
  await page.route(/\/api\/v1\/buildings\/[^/]+\/post-works\/compare(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        building_id: 'b1000000-0000-0000-0000-000000000001',
        intervention_id: null,
        before: {
          total_positive_samples: 5,
          by_pollutant: { asbestos: 3, pcb: 2 },
          risk_areas: [],
        },
        after: {
          removed: 2,
          remaining: 1,
          encapsulated: 1,
          treated: 1,
          unknown_after_intervention: 0,
          recheck_needed: 0,
          by_pollutant: {},
        },
        summary: {
          remediation_rate: 0.8,
          verification_rate: 0.6,
          residual_risk_count: 1,
        },
      }),
    });
  });

  // Post-works list
  await page.route(/\/api\/v1\/buildings\/[^/]+\/post-works(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [],
        total: 0,
        page: 1,
        size: 50,
        pages: 0,
      }),
    });
  });

  // Jurisdictions list
  await page.route(/\/api\/v1\/jurisdictions(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: 'j1000000-0000-0000-0000-000000000001',
            code: 'EU',
            name: 'European Union',
            parent_id: null,
            level: 'supranational',
            country_code: null,
            is_active: true,
            metadata_json: null,
            created_at: '2024-01-01T00:00:00Z',
          },
          {
            id: 'j2000000-0000-0000-0000-000000000002',
            code: 'CH',
            name: 'Suisse',
            parent_id: 'j1000000-0000-0000-0000-000000000001',
            level: 'country',
            country_code: 'CH',
            is_active: true,
            metadata_json: null,
            created_at: '2024-01-01T00:00:00Z',
          },
          {
            id: 'j3000000-0000-0000-0000-000000000003',
            code: 'CH-VD',
            name: 'Canton de Vaud',
            parent_id: 'j2000000-0000-0000-0000-000000000002',
            level: 'region',
            country_code: 'CH',
            is_active: true,
            metadata_json: null,
            created_at: '2024-01-01T00:00:00Z',
          },
        ],
        total: 3,
        page: 1,
        size: 100,
        pages: 1,
      }),
    });
  });

  // Jurisdiction detail (with packs)
  await page.route(/\/api\/v1\/jurisdictions\/j[0-9]/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = route.request().url();
    if (url.includes('j3000000')) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'j3000000-0000-0000-0000-000000000003',
          code: 'CH-VD',
          name: 'Canton de Vaud',
          parent_id: 'j2000000-0000-0000-0000-000000000002',
          level: 'region',
          country_code: 'CH',
          is_active: true,
          metadata_json: null,
          created_at: '2024-01-01T00:00:00Z',
          regulatory_packs: [
            {
              id: 'rp100000-0000-0000-0000-000000000001',
              jurisdiction_id: 'j3000000-0000-0000-0000-000000000003',
              pollutant_type: 'asbestos',
              version: '1.0',
              is_active: true,
              threshold_value: 1.0,
              threshold_unit: 'percent_weight',
              threshold_action: 'remediate',
              risk_year_start: 1904,
              risk_year_end: 1990,
              base_probability: 0.85,
              work_categories_json: { minor: 'no_restriction', medium: 'suva_plan', major: 'suva_full' },
              waste_classification_json: null,
              legal_reference: 'OTConst Art. 60a',
              legal_url: null,
              description_fr: 'Amiante dans les materiaux de construction',
              description_de: null,
              notification_required: true,
              notification_authority: 'SUVA',
              notification_delay_days: 14,
              created_at: '2024-01-01T00:00:00Z',
              updated_at: '2024-01-01T00:00:00Z',
            },
          ],
        }),
      });
    }
    // Default: return jurisdiction without packs
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'j2000000-0000-0000-0000-000000000002',
        code: 'CH',
        name: 'Suisse',
        parent_id: 'j1000000-0000-0000-0000-000000000001',
        level: 'country',
        country_code: 'CH',
        is_active: true,
        metadata_json: null,
        created_at: '2024-01-01T00:00:00Z',
        regulatory_packs: [],
      }),
    });
  });

  // Timeline for building
  await page.route(/\/api\/v1\/buildings\/[^/]+\/timeline(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: 'tl-001',
            date: '2024-06-01T14:00:00Z',
            event_type: 'risk_change',
            title: 'Niveau de risque mis a jour',
            description: 'Le niveau de risque global est passe a eleve',
            icon_hint: 'shield',
            metadata: { previous_level: 'medium', new_level: 'high' },
            source_id: null,
            source_type: null,
          },
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
          {
            id: 'tl-003',
            date: '2024-03-15T10:00:00Z',
            event_type: 'sample',
            title: 'Echantillon ECH-001 preleve',
            description: 'Fibre-ciment - Joint de facade',
            icon_hint: 'flask',
            metadata: { sample_number: 'ECH-001', risk_level: 'high' },
            source_id: 's1000000-0000-0000-0000-000000000001',
            source_type: 'sample',
          },
          {
            id: 'tl-004',
            date: '2024-01-20T09:00:00Z',
            event_type: 'document',
            title: 'Plan rez-de-chaussee ajoute',
            description: 'plan-rdc.pdf',
            icon_hint: 'file',
            metadata: { file_name: 'plan-rdc.pdf' },
            source_id: null,
            source_type: 'plan',
          },
          {
            id: 'tl-005',
            date: '2024-01-15T10:00:00Z',
            event_type: 'intervention',
            title: 'Renovation facade nord planifiee',
            description: 'Remplacement des joints amiantees',
            icon_hint: 'wrench',
            metadata: { status: 'planned', cost_chf: 45000 },
            source_id: null,
            source_type: 'intervention',
          },
          {
            id: 'tl-006',
            date: '1965-01-01T00:00:00Z',
            event_type: 'construction',
            title: 'Construction du batiment',
            description: 'Annee de construction: 1965',
            icon_hint: 'building',
            metadata: { year: 1965 },
            source_id: null,
            source_type: null,
          },
        ],
        total: 6,
        page: 1,
        size: 50,
        pages: 1,
      }),
    });
  });

  // Completeness for building
  await page.route(/\/api\/v1\/buildings\/[^/]+\/completeness(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        building_id: 'b1000000-0000-0000-0000-000000000001',
        workflow_stage: 'avt',
        overall_score: 0.75,
        checks: [
          {
            id: 'diag_asbestos',
            category: 'diagnostic',
            label_key: 'completeness.check.has_diagnostic',
            status: 'complete',
            weight: 1,
            details: 'Diagnostic amiante termine',
          },
          {
            id: 'diag_pcb',
            category: 'diagnostic',
            label_key: 'completeness.check.has_pcb_samples',
            status: 'missing',
            weight: 1,
            details: null,
          },
          {
            id: 'evidence_photos',
            category: 'evidence',
            label_key: 'completeness.check.no_missing_risk_level',
            status: 'complete',
            weight: 0.5,
            details: '3 photos',
          },
          {
            id: 'document_report',
            category: 'document',
            label_key: 'completeness.check.has_report',
            status: 'partial',
            weight: 1,
            details: 'Rapport partiel',
          },
          {
            id: 'regulatory_suva',
            category: 'regulatory',
            label_key: 'completeness.check.suva_notified',
            status: 'complete',
            weight: 1,
            details: null,
          },
          {
            id: 'action_desamiantage',
            category: 'action',
            label_key: 'completeness.check.actions_assigned',
            status: 'missing',
            weight: 1,
            details: null,
          },
        ],
        missing_items: ['Diagnostic PCB manquant', 'Plan de desamiantage requis'],
        ready_to_proceed: false,
        evaluated_at: '2024-06-01T14:00:00Z',
      }),
    });
  });

  // Actions list
  await page.route(/\/api\/v1\/actions(\?.*)?$/, (route) => {
    if (route.request().method() === 'PUT') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'a1000000-0000-0000-0000-000000000001',
          building_id: 'b1000000-0000-0000-0000-000000000001',
          diagnostic_id: 'd1000000-0000-0000-0000-000000000001',
          sample_id: null,
          source_type: 'diagnostic',
          action_type: 'remediation',
          title: 'Desamiantage facade nord',
          description: 'Retrait des joints amiantees de la facade nord',
          priority: 'high',
          status: 'open',
          due_date: '2024-09-01',
          assigned_to: null,
          created_by: null,
          metadata_json: null,
          created_at: '2024-03-20T14:00:00Z',
          updated_at: '2024-03-20T14:00:00Z',
          completed_at: null,
        },
        {
          id: 'a2000000-0000-0000-0000-000000000002',
          building_id: 'b1000000-0000-0000-0000-000000000001',
          diagnostic_id: null,
          sample_id: null,
          source_type: 'compliance',
          action_type: 'notification',
          title: 'Notification SUVA requise',
          description: 'Notifier la SUVA avant debut des travaux',
          priority: 'critical',
          status: 'in_progress',
          due_date: '2024-07-15',
          assigned_to: null,
          created_by: null,
          metadata_json: null,
          created_at: '2024-03-21T09:00:00Z',
          updated_at: '2024-04-01T10:00:00Z',
          completed_at: null,
        },
        {
          id: 'a3000000-0000-0000-0000-000000000003',
          building_id: 'b2000000-0000-0000-0000-000000000002',
          diagnostic_id: null,
          sample_id: null,
          source_type: 'risk',
          action_type: 'diagnostic',
          title: 'Diagnostic PCB recommande',
          description: 'Batiment construit en 1978, diagnostic PCB recommande',
          priority: 'medium',
          status: 'open',
          due_date: null,
          assigned_to: null,
          created_by: null,
          metadata_json: null,
          created_at: '2024-04-01T08:00:00Z',
          updated_at: '2024-04-01T08:00:00Z',
          completed_at: null,
        },
        {
          id: 'a4000000-0000-0000-0000-000000000004',
          building_id: 'b1000000-0000-0000-0000-000000000001',
          diagnostic_id: null,
          sample_id: null,
          source_type: 'manual',
          action_type: 'inspection',
          title: 'Verification etancheite toiture',
          description: null,
          priority: 'low',
          status: 'done',
          due_date: '2024-05-01',
          assigned_to: null,
          created_by: null,
          metadata_json: null,
          created_at: '2024-02-01T08:00:00Z',
          updated_at: '2024-05-01T16:00:00Z',
          completed_at: '2024-05-01T16:00:00Z',
        },
      ]),
    });
  });

  // Actions list for a specific building
  await page.route(/\/api\/v1\/buildings\/[^/]+\/actions(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const url = route.request().url();
    const buildingIdMatch = url.match(/\/buildings\/([^/]+)\/actions/);
    const buildingId = buildingIdMatch?.[1];
    const allItems = [
      {
        id: 'a1000000-0000-0000-0000-000000000001',
        building_id: 'b1000000-0000-0000-0000-000000000001',
        diagnostic_id: 'd1000000-0000-0000-0000-000000000001',
        sample_id: null,
        source_type: 'diagnostic',
        action_type: 'remediation',
        title: 'Desamiantage facade nord',
        description: 'Retrait des joints amiantees de la facade nord',
        priority: 'high',
        status: 'open',
        due_date: '2024-09-01',
        assigned_to: null,
        created_by: null,
        metadata_json: null,
        created_at: '2024-03-20T14:00:00Z',
        updated_at: '2024-03-20T14:00:00Z',
        completed_at: null,
      },
      {
        id: 'a2000000-0000-0000-0000-000000000002',
        building_id: 'b1000000-0000-0000-0000-000000000001',
        diagnostic_id: null,
        sample_id: null,
        source_type: 'compliance',
        action_type: 'notification',
        title: 'Notification SUVA requise',
        description: 'Notifier la SUVA avant debut des travaux',
        priority: 'critical',
        status: 'in_progress',
        due_date: '2024-07-15',
        assigned_to: null,
        created_by: null,
        metadata_json: null,
        created_at: '2024-03-21T09:00:00Z',
        updated_at: '2024-04-01T10:00:00Z',
        completed_at: null,
      },
      {
        id: 'a3000000-0000-0000-0000-000000000003',
        building_id: 'b2000000-0000-0000-0000-000000000002',
        diagnostic_id: null,
        sample_id: null,
        source_type: 'risk',
        action_type: 'diagnostic',
        title: 'Diagnostic PCB recommande',
        description: 'Batiment construit en 1978, diagnostic PCB recommande',
        priority: 'medium',
        status: 'open',
        due_date: null,
        assigned_to: null,
        created_by: null,
        metadata_json: null,
        created_at: '2024-04-01T08:00:00Z',
        updated_at: '2024-04-01T08:00:00Z',
        completed_at: null,
      },
      {
        id: 'a4000000-0000-0000-0000-000000000004',
        building_id: 'b1000000-0000-0000-0000-000000000001',
        diagnostic_id: null,
        sample_id: null,
        source_type: 'manual',
        action_type: 'inspection',
        title: 'Verification etancheite toiture',
        description: null,
        priority: 'low',
        status: 'done',
        due_date: '2024-05-01',
        assigned_to: null,
        created_by: null,
        metadata_json: null,
        created_at: '2024-02-01T08:00:00Z',
        updated_at: '2024-05-01T16:00:00Z',
        completed_at: '2024-05-01T16:00:00Z',
      },
    ];
    const items = buildingId ? allItems.filter((item) => item.building_id === buildingId) : allItems;
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify(items),
    });
  });

  // Action update (PUT)
  await page.route('**/api/v1/actions/*', (route) => {
    if (route.request().method() !== 'PUT') return route.fallback();
    const body = route.request().postDataJSON();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ id: 'a1000000-0000-0000-0000-000000000001', ...body }),
    });
  });

  // Diagnostic validate (PATCH)
  await page.route('**/api/v1/diagnostics/*/validate', (route) => {
    if (route.request().method() !== 'PATCH') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'd1000000-0000-0000-0000-000000000001',
        status: 'validated',
        generated_actions_count: 2,
      }),
    });
  });

  // Create building (POST only)
  await page.route('**/api/v1/buildings', (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    const body = route.request().postDataJSON();
    return route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        id: 'b9000000-0000-0000-0000-000000000009',
        ...body,
        risk_scores: null,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      }),
    });
  });

  // Audit logs
  await page.route(/\/api\/v1\/audit-logs(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: 'al100000-0000-0000-0000-000000000001',
            user_id: '00000000-0000-0000-0000-000000000001',
            action: 'create',
            entity_type: 'building',
            entity_id: 'b1000000-0000-0000-0000-000000000001',
            details: { address: 'Rue de Bourg 1' },
            ip_address: '192.168.1.1',
            timestamp: '2024-06-01T14:00:00Z',
            user_email: 'admin@swissbuildingos.ch',
            user_name: 'Admin Test',
          },
          {
            id: 'al200000-0000-0000-0000-000000000002',
            user_id: '00000000-0000-0000-0000-000000000002',
            action: 'update',
            entity_type: 'diagnostic',
            entity_id: 'd1000000-0000-0000-0000-000000000001',
            details: null,
            ip_address: '10.0.0.1',
            timestamp: '2024-05-15T10:30:00Z',
            user_email: 'diag@swissbuildingos.ch',
            user_name: 'Jean Muller',
          },
        ],
        total: 2,
        page: 1,
        size: 20,
        pages: 1,
      }),
    });
  });

  // Export jobs
  await page.route(/\/api\/v1\/exports(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: 'exp10000-0000-0000-0000-000000000001',
            type: 'building_dossier',
            building_id: 'b1000000-0000-0000-0000-000000000001',
            organization_id: null,
            status: 'completed',
            requested_by: '00000000-0000-0000-0000-000000000001',
            file_path: '/exports/dossier-001.pdf',
            error_message: null,
            created_at: '2024-06-01T14:00:00Z',
            completed_at: '2024-06-01T14:02:00Z',
          },
          {
            id: 'exp20000-0000-0000-0000-000000000002',
            type: 'handoff_pack',
            building_id: 'b2000000-0000-0000-0000-000000000002',
            organization_id: null,
            status: 'processing',
            requested_by: '00000000-0000-0000-0000-000000000001',
            file_path: null,
            error_message: null,
            created_at: '2024-06-02T10:00:00Z',
            completed_at: null,
          },
        ],
        total: 2,
        page: 1,
        size: 20,
        pages: 1,
      }),
    });
  });

  // Saved simulations for building
  await page.route(/\/api\/v1\/buildings\/[^/]+\/simulations(\?.*)?$/, (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          size: 50,
          pages: 0,
        }),
      });
    }
    if (route.request().method() === 'POST') {
      const body = route.request().postDataJSON();
      return route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'sim10000-0000-0000-0000-000000000001',
          building_id: 'b1000000-0000-0000-0000-000000000001',
          title: body?.title ?? 'Test Simulation',
          description: null,
          simulation_type: 'renovation',
          parameters_json: body?.parameters_json ?? {},
          results_json: body?.results_json ?? {},
          total_cost_chf: body?.total_cost_chf ?? null,
          total_duration_weeks: body?.total_duration_weeks ?? null,
          risk_level_before: null,
          risk_level_after: null,
          created_by: '00000000-0000-0000-0000-000000000001',
          created_at: new Date().toISOString(),
        }),
      });
    }
    return route.fulfill({ status: 204 });
  });

  // Portfolio change signals
  await page.route(/\/api\/v1\/portfolio\/change-signals(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        items: [
          {
            id: 'cs-1',
            building_id: 'b1',
            signal_type: 'new_positive_sample',
            severity: 'warning',
            status: 'active',
            title: 'Positive sample: asbestos',
            description: 'Sample exceeded threshold',
            source: 'sample_analysis',
            entity_type: 'sample',
            entity_id: 's1',
            metadata_json: null,
            detected_at: '2026-03-07T10:00:00Z',
            acknowledged_by: null,
            acknowledged_at: null,
          },
          {
            id: 'cs-2',
            building_id: 'b2',
            signal_type: 'diagnostic_expiring',
            severity: 'warning',
            status: 'active',
            title: 'Diagnostic expiring soon',
            description: 'Diagnostic approaching 5-year limit',
            source: 'requalification_monitor',
            entity_type: 'diagnostic',
            entity_id: 'd1',
            metadata_json: null,
            detected_at: '2026-03-06T14:00:00Z',
            acknowledged_by: null,
            acknowledged_at: null,
          },
        ],
        total: 2,
        page: 1,
        size: 20,
        pages: 1,
      }),
    });
  });

  // Contradictions summary
  await page.route('**/api/v1/buildings/*/contradictions/summary', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        total: 3,
        by_type: { conflicting_sample_results: 2, inconsistent_risk_levels: 1 },
        resolved: 1,
        unresolved: 2,
      }),
    });
  });

  // Contradictions detect
  await page.route('**/api/v1/buildings/*/contradictions/detect', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  // Building snapshots (Time Machine)
  await page.route('**/api/v1/buildings/*/snapshots/compare*', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        building_id: '00000000-0000-0000-0000-000000000099',
        snapshot_a: {
          id: '00000000-0000-0000-0000-0000000000a1',
          captured_at: '2026-01-15T10:00:00Z',
          passport_grade: 'D',
          overall_trust: 0.45,
          completeness_score: 0.38,
        },
        snapshot_b: {
          id: '00000000-0000-0000-0000-0000000000a2',
          captured_at: '2026-03-01T10:00:00Z',
          passport_grade: 'C',
          overall_trust: 0.62,
          completeness_score: 0.55,
        },
        changes: {
          trust_delta: 0.17,
          completeness_delta: 0.17,
          grade_change: 'D\u2192C',
          readiness_changes: [{ type: 'asbestos', from: 'not_ready', to: 'ready' }],
          new_contradictions: 0,
          resolved_contradictions: 1,
        },
      }),
    });
  });

  await page.route('**/api/v1/buildings/*/snapshots', (route) => {
    if (route.request().method() === 'POST') {
      route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          id: '00000000-0000-0000-0000-0000000000a3',
          building_id: '00000000-0000-0000-0000-000000000099',
          snapshot_type: 'manual',
          trigger_event: null,
          passport_state_json: null,
          trust_state_json: null,
          readiness_state_json: null,
          evidence_counts_json: null,
          passport_grade: 'C',
          overall_trust: 0.62,
          completeness_score: 0.55,
          captured_at: '2026-03-08T12:00:00Z',
          captured_by: '00000000-0000-0000-0000-000000000001',
          notes: null,
        }),
      });
    } else {
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          items: [
            {
              id: '00000000-0000-0000-0000-0000000000a1',
              building_id: '00000000-0000-0000-0000-000000000099',
              snapshot_type: 'manual',
              trigger_event: null,
              passport_state_json: null,
              trust_state_json: null,
              readiness_state_json: null,
              evidence_counts_json: null,
              passport_grade: 'D',
              overall_trust: 0.45,
              completeness_score: 0.38,
              captured_at: '2026-01-15T10:00:00Z',
              captured_by: null,
              notes: null,
            },
            {
              id: '00000000-0000-0000-0000-0000000000a2',
              building_id: '00000000-0000-0000-0000-000000000099',
              snapshot_type: 'automatic',
              trigger_event: 'diagnostic_completed',
              passport_state_json: null,
              trust_state_json: null,
              readiness_state_json: null,
              evidence_counts_json: null,
              passport_grade: 'C',
              overall_trust: 0.62,
              completeness_score: 0.55,
              captured_at: '2026-03-01T10:00:00Z',
              captured_by: null,
              notes: null,
            },
          ],
          total: 2,
          page: 1,
          size: 20,
          pages: 1,
        }),
      });
    }
  });

  // Intervention simulator
  await page.route('**/api/v1/buildings/*/interventions/simulate', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        current_state: {
          passport_grade: 'C',
          trust_score: 0.62,
          completeness_score: 0.55,
          blocker_count: 2,
          open_actions_count: 5,
        },
        projected_state: {
          passport_grade: 'B',
          trust_score: 0.72,
          completeness_score: 0.63,
          blocker_count: 0,
          open_actions_count: 2,
        },
        impact_summary: {
          actions_resolved: 3,
          readiness_improvement: 'blocked \u2192 ready',
          trust_delta: 0.1,
          completeness_delta: 0.08,
          grade_change: 'C \u2192 B',
          risk_reduction: { asbestos: 'high \u2192 low', pcb: 'medium \u2192 low' },
          estimated_total_cost: 45000.0,
        },
        recommendations: [
          'Consider adding diagnostic inspections to improve trust score above 0.6',
          'Consider adding hap remediation to improve grade to A',
          'Consider adding radon remediation to improve grade to A',
        ],
      }),
    });
  });

  // Passport summary
  await page.route('**/api/v1/buildings/*/passport/summary', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        building_id: '00000000-0000-0000-0000-000000000099',
        knowledge_state: {
          proven_pct: 0.45,
          inferred_pct: 0.2,
          declared_pct: 0.15,
          obsolete_pct: 0.1,
          contradictory_pct: 0.1,
          overall_trust: 0.72,
          total_data_points: 85,
          trend: 'improving',
        },
        completeness: { overall_score: 0.68, category_scores: {} },
        readiness: {
          safe_to_start: { status: 'blocked', score: 0.5, blockers_count: 2 },
          safe_to_tender: { status: 'conditional', score: 0.75, blockers_count: 0 },
          safe_to_reopen: { status: 'ready', score: 1.0, blockers_count: 0 },
          safe_to_requalify: { status: 'conditional', score: 0.5, blockers_count: 0 },
        },
        blind_spots: {
          total_open: 3,
          blocking: 1,
          by_type: { missing_diagnostic: 2, missing_documentation: 1 },
        },
        contradictions: {
          total: 2,
          unresolved: 1,
          by_type: { conflicting_sample_results: 1 },
        },
        evidence_coverage: {
          diagnostics_count: 3,
          samples_count: 15,
          documents_count: 8,
          interventions_count: 2,
          latest_diagnostic_date: '2025-11-15',
          latest_document_date: '2026-02-10',
        },
        passport_grade: 'C',
        assessed_at: '2026-03-08T10:00:00Z',
      }),
    });
  });

  // Requalification timeline
  await page.route('**/api/v1/buildings/*/requalification/timeline', (route) => {
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        building_id: '00000000-0000-0000-0000-000000000001',
        entries: [
          {
            timestamp: '2026-03-08T09:00:00Z',
            entry_type: 'grade_change',
            title: 'Grade upgraded after intervention',
            description: 'Asbestos removal completed, grade improved',
            severity: null,
            signal_type: null,
            grade_before: 'D',
            grade_after: 'B',
            metadata: null,
          },
          {
            timestamp: '2026-03-05T14:30:00Z',
            entry_type: 'intervention',
            title: 'Asbestos removal - Floor 2',
            description: 'Complete encapsulation of identified asbestos materials',
            severity: null,
            signal_type: null,
            grade_before: null,
            grade_after: null,
            metadata: null,
          },
          {
            timestamp: '2026-03-01T10:00:00Z',
            entry_type: 'signal',
            title: 'New diagnostic results available',
            description: 'Diagnostic D-2026-001 completed with high-risk findings',
            severity: 'high',
            signal_type: 'diagnostic_completed',
            grade_before: null,
            grade_after: null,
            metadata: null,
          },
          {
            timestamp: '2026-02-15T08:00:00Z',
            entry_type: 'snapshot',
            title: 'Quarterly snapshot captured',
            description: 'Automatic quarterly building state snapshot',
            severity: null,
            signal_type: null,
            grade_before: null,
            grade_after: null,
            metadata: null,
          },
        ],
        current_grade: 'B',
        grade_history: [
          { grade: 'D', date: '2026-01-01' },
          { grade: 'B', date: '2026-03-08' },
        ],
      }),
    });
  });

  // Transfer package
  await page.route('**/api/v1/buildings/*/transfer-package', (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        package_id: 'tp000000-0000-0000-0000-000000000001',
        building_id: '00000000-0000-0000-0000-000000000099',
        generated_at: '2026-03-08T12:00:00Z',
        schema_version: '1.0',
        building_summary: { address: 'Rue de Bourg 1', city: 'Lausanne', canton: 'VD' },
        passport: { grade: 'C', trust: 0.72 },
        diagnostics_summary: { total: 3, completed: 2 },
        documents_summary: { total: 8 },
        interventions_summary: { total: 2, completed: 1 },
        actions_summary: { total: 5, open: 3, critical: 1 },
        evidence_coverage: { diagnostics_count: 3, samples_count: 15, documents_count: 8 },
        contradictions: { total: 2, unresolved: 1 },
        unknowns: { total_open: 3, blocking: 1 },
        snapshots: [{ id: 's1', captured_at: '2026-03-01T10:00:00Z' }],
        completeness: { overall_score: 0.68, category_scores: {} },
        readiness: { safe_to_start: { status: 'blocked', score: 0.5, blockers_count: 2 } },
        metadata: { generated_by: 'system', format_version: '1.0' },
      }),
    });
  });

  // Transaction Readiness (Safe to X)
  await page.route(/\/api\/v1\/buildings\/[^/]+\/transaction-readiness$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          building_id: 'b1000000-0000-0000-0000-000000000001',
          transaction_type: 'sell',
          overall_status: 'conditional',
          score: 0.72,
          checks: [
            { label: 'Diagnostic amiante complet', passed: true, details: null },
            { label: 'Diagnostic PCB complet', passed: true, details: null },
            { label: 'Certificat energetique (CECB)', passed: false, details: 'Expire' },
          ],
          blockers: [],
          conditions: [
            { label: 'Renouveler le CECB avant la vente', severity: 'medium', details: null },
          ],
          recommendations: [
            { label: 'Mettre a jour le dossier de pollution', severity: 'low', details: null },
          ],
          evaluated_at: '2026-03-01T10:00:00Z',
        },
        {
          building_id: 'b1000000-0000-0000-0000-000000000001',
          transaction_type: 'insure',
          overall_status: 'not_ready',
          score: 0.35,
          checks: [
            { label: 'Inventaire des polluants', passed: false, details: 'Incomplet' },
            { label: 'Etat structurel documente', passed: false, details: 'Manquant' },
          ],
          blockers: [
            { label: 'Inventaire polluants incomplet', severity: 'critical', details: 'PCB et plomb non evalues' },
            { label: 'Rapport structurel manquant', severity: 'high', details: null },
          ],
          conditions: [],
          recommendations: [
            { label: 'Planifier un diagnostic complet', severity: 'medium', details: null },
          ],
          evaluated_at: '2026-03-01T10:00:00Z',
        },
        {
          building_id: 'b1000000-0000-0000-0000-000000000001',
          transaction_type: 'finance',
          overall_status: 'ready',
          score: 0.92,
          checks: [
            { label: 'Valeur estimee disponible', passed: true, details: null },
            { label: 'Diagnostics a jour', passed: true, details: null },
            { label: 'Pas de contentieux en cours', passed: true, details: null },
          ],
          blockers: [],
          conditions: [],
          recommendations: [],
          evaluated_at: '2026-03-01T10:00:00Z',
        },
        {
          building_id: 'b1000000-0000-0000-0000-000000000001',
          transaction_type: 'lease',
          overall_status: 'conditional',
          score: 0.6,
          checks: [
            { label: 'Conformite incendie', passed: true, details: null },
            { label: 'Habitabilite confirmee', passed: false, details: 'Zone B non evaluee' },
          ],
          blockers: [],
          conditions: [
            { label: 'Evaluer habitabilite zone B', severity: 'high', details: null },
            { label: 'Mettre a jour le bail-type', severity: 'medium', details: null },
          ],
          recommendations: [
            { label: 'Verifier la conformite acoustique', severity: 'low', details: null },
          ],
          evaluated_at: '2026-03-01T10:00:00Z',
        },
      ]),
    });
  });

  // Building Comparison
  await page.route('**/api/v1/buildings/compare', (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        buildings: [
          {
            building_id: 'b1000000-0000-0000-0000-000000000001',
            building_name: 'Immeuble Lausanne Centre',
            address: 'Rue du Marche 12, 1003 Lausanne',
            passport_grade: 'B',
            passport_score: 0.78,
            trust_score: 0.85,
            completeness_score: 0.9,
            readiness_summary: { asbestos: true, pcb: true, lead: false },
            open_actions_count: 3,
            open_unknowns_count: 1,
            contradictions_count: 0,
            diagnostic_count: 4,
            last_diagnostic_date: '2026-02-15T10:00:00Z',
          },
          {
            building_id: 'b1000000-0000-0000-0000-000000000002',
            building_name: 'Residence Geneve Lac',
            address: 'Quai du Mont-Blanc 5, 1201 Geneve',
            passport_grade: 'C',
            passport_score: 0.55,
            trust_score: 0.62,
            completeness_score: 0.7,
            readiness_summary: { asbestos: false, pcb: true, lead: false },
            open_actions_count: 7,
            open_unknowns_count: 4,
            contradictions_count: 2,
            diagnostic_count: 2,
            last_diagnostic_date: '2025-11-20T10:00:00Z',
          },
          {
            building_id: 'b1000000-0000-0000-0000-000000000003',
            building_name: 'Batiment Industriel Yverdon',
            address: 'Zone Industrielle 8, 1400 Yverdon',
            passport_grade: 'A',
            passport_score: 0.92,
            trust_score: 0.95,
            completeness_score: 0.98,
            readiness_summary: { asbestos: true, pcb: true, lead: true },
            open_actions_count: 0,
            open_unknowns_count: 0,
            contradictions_count: 0,
            diagnostic_count: 6,
            last_diagnostic_date: '2026-03-01T10:00:00Z',
          },
        ],
        comparison_dimensions: [
          'passport_grade',
          'trust_score',
          'completeness_score',
          'open_actions_count',
          'open_unknowns_count',
          'contradictions_count',
          'diagnostic_count',
        ],
        best_passport: 'Batiment Industriel Yverdon',
        worst_passport: 'Residence Geneve Lac',
        average_trust: 0.807,
        average_completeness: 0.86,
      }),
    });
  });

  // Portfolio map buildings
  await page.route('**/api/v1/portfolio/map-buildings*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        type: 'FeatureCollection',
        features: [
          {
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [6.6323, 46.5197] },
            properties: {
              id: 'b0000000-0000-0000-0000-000000000001',
              address: 'Rue de Bourg 1',
              city: 'Lausanne',
              canton: 'VD',
              construction_year: 1965,
              overall_risk_level: 'high',
              risk_score: 0.78,
              completeness_score: 0.65,
            },
          },
          {
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [6.1466, 46.2044] },
            properties: {
              id: 'b0000000-0000-0000-0000-000000000002',
              address: 'Rue du Rhone 10',
              city: 'Geneve',
              canton: 'GE',
              construction_year: 1972,
              overall_risk_level: 'critical',
              risk_score: 0.92,
              completeness_score: 0.80,
            },
          },
          {
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [7.4474, 46.9480] },
            properties: {
              id: 'b0000000-0000-0000-0000-000000000003',
              address: 'Bundesplatz 3',
              city: 'Bern',
              canton: 'BE',
              construction_year: 1950,
              overall_risk_level: 'medium',
              risk_score: 0.45,
              completeness_score: 0.70,
            },
          },
          {
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [8.5417, 47.3769] },
            properties: {
              id: 'b0000000-0000-0000-0000-000000000004',
              address: 'Bahnhofstrasse 20',
              city: 'Zurich',
              canton: 'ZH',
              construction_year: 1980,
              overall_risk_level: 'low',
              risk_score: 0.15,
              completeness_score: 0.90,
            },
          },
          {
            type: 'Feature',
            geometry: { type: 'Point', coordinates: [7.5886, 47.5596] },
            properties: {
              id: 'b0000000-0000-0000-0000-000000000005',
              address: 'Marktplatz 5',
              city: 'Basel',
              canton: 'BS',
              construction_year: 1958,
              overall_risk_level: 'high',
              risk_score: 0.72,
              completeness_score: 0.55,
            },
          },
        ],
      }),
    }),
  );

  // Portfolio summary
  await page.route('**/api/v1/portfolio/summary*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        overview: {
          total_buildings: 150,
          total_diagnostics: 85,
          total_interventions: 32,
          total_documents: 210,
          active_campaigns: 3,
          avg_completeness: 0.72,
          avg_trust: 0.65,
        },
        risk: {
          by_level: { low: 40, medium: 60, high: 35, critical: 15, unknown: 0 },
          avg_risk_score: 0.55,
          buildings_above_threshold: 50,
        },
        compliance: {
          compliant_count: 80,
          non_compliant_count: 25,
          partially_compliant_count: 30,
          unknown_count: 15,
          total_overdue_deadlines: 8,
        },
        readiness: {
          ready_count: 45,
          partially_ready_count: 60,
          not_ready_count: 35,
          unknown_count: 10,
        },
        grades: {
          by_grade: { A: 20, B: 35, C: 50, D: 30, E: 10, None: 5 },
        },
        actions: {
          total_open: 45,
          total_in_progress: 28,
          total_completed: 120,
          by_priority: { high: 18, medium: 35, low: 20 },
          overdue_count: 12,
        },
        alerts: {
          total_weak_signals: 15,
          buildings_on_critical_path: 8,
          total_constraint_blockers: 5,
          buildings_with_stale_diagnostics: 12,
        },
        generated_at: new Date().toISOString(),
        organization_id: null,
      }),
    }),
  );

  // Portfolio health score
  await page.route('**/api/v1/portfolio/health-score*', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        score: 62.5,
        breakdown: {
          risk: { score: 66.7, weight: 0.3 },
          compliance: { score: 53.3, weight: 0.25 },
          readiness: { score: 60.0, weight: 0.25 },
          completeness: { score: 72.0, weight: 0.2 },
        },
        total_buildings: 150,
        organization_id: null,
      }),
    }),
  );

  // Campaign impact
  await page.route('**/api/v1/campaigns/*/impact', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        buildings_affected: 5,
        actions_total: 12,
        actions_completed: 7,
        actions_in_progress: 3,
        completion_rate: 0.583,
        velocity: 0.35,
        budget_utilization: 0.45,
        estimated_completion_date: '2024-12-15',
        days_remaining: 45,
        is_at_risk: false,
      }),
    }),
  );

  // Plan heatmap
  await page.route('**/api/v1/plans/*/heatmap', (route) =>
    route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        plan_id: 'p1000000-0000-0000-0000-000000000001',
        building_id: 'b1000000-0000-0000-0000-000000000001',
        total_points: 6,
        coverage_score: 0.72,
        points: [
          { x: 0.2, y: 0.3, intensity: 0.9, category: 'trust', label: 'Confirmed safe zone', annotation_id: null, zone_id: null },
          { x: 0.5, y: 0.2, intensity: 0.6, category: 'unknown', label: 'Pending analysis', annotation_id: null, zone_id: null },
          { x: 0.7, y: 0.6, intensity: 0.85, category: 'contradiction', label: 'Conflicting reports', annotation_id: null, zone_id: null },
          { x: 0.3, y: 0.7, intensity: 0.95, category: 'hazard', label: 'Asbestos detected', annotation_id: null, zone_id: null },
          { x: 0.8, y: 0.4, intensity: 0.5, category: 'sample', label: 'Sample A-12', annotation_id: null, zone_id: null },
          { x: 0.4, y: 0.5, intensity: 0.7, category: 'trust', label: 'Verified material', annotation_id: null, zone_id: null },
        ],
        summary: { trust: 2, unknown: 1, contradiction: 1, hazard: 1, sample: 1 },
      }),
    }),
  );

  // Authority packs list
  await page.route(/\/api\/v1\/buildings\/[^/]+\/authority-packs(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          pack_id: 'ap100000-0000-0000-0000-000000000001',
          building_id: 'b1000000-0000-0000-0000-000000000001',
          canton: 'VD',
          overall_completeness: 0.87,
          generated_at: '2025-11-15T10:30:00Z',
          status: 'ready',
        },
        {
          pack_id: 'ap100000-0000-0000-0000-000000000002',
          building_id: 'b1000000-0000-0000-0000-000000000001',
          canton: 'VD',
          overall_completeness: 0.62,
          generated_at: '2025-10-01T08:00:00Z',
          status: 'draft',
        },
      ]),
    });
  });

  // Authority pack generate
  await page.route(/\/api\/v1\/buildings\/[^/]+\/authority-packs\/generate$/, (route) => {
    if (route.request().method() !== 'POST') return route.fallback();
    return route.fulfill({
      status: 201,
      contentType: 'application/json',
      body: JSON.stringify({
        pack_id: 'ap100000-0000-0000-0000-000000000003',
        building_id: 'b1000000-0000-0000-0000-000000000001',
        canton: 'VD',
        sections: [],
        total_sections: 0,
        overall_completeness: 0.0,
        generated_at: new Date().toISOString(),
        warnings: [],
      }),
    });
  });

  // Evidence facade summary
  await page.route('**/api/v1/buildings/*/evidence/summary', (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        building_id: 'b1000000-0000-0000-0000-000000000001',
        diagnostics_count: 3,
        diagnostics_by_status: { completed: 2, in_progress: 1 },
        samples_count: 12,
        samples_positive: 5,
        samples_negative: 7,
        samples_by_pollutant: {
          asbestos: { positive: 3, negative: 2, total: 5 },
          pcb: { positive: 1, negative: 2, total: 3 },
          lead: { positive: 1, negative: 1, total: 2 },
          hap: { positive: 0, negative: 1, total: 1 },
          radon: { positive: 0, negative: 1, total: 1 },
        },
        documents_count: 8,
        evidence_links_count: 14,
        coverage_ratio: 1.0,
      }),
    });
  });

  // Remediation facade summary
  await page.route('**/api/v1/buildings/*/remediation/summary', (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        building_id: 'b1000000-0000-0000-0000-000000000001',
        actions: {
          total: 5,
          open: 3,
          done: 1,
          blocked: 1,
          by_priority: { critical: 1, high: 2, medium: 1, low: 1 },
        },
        interventions: {
          total: 2,
          by_status: { completed: 1, planned: 1 },
        },
        post_works_states_count: 1,
        has_completed_remediation: true,
      }),
    });
  });

  // Compliance facade summary
  await page.route('**/api/v1/buildings/*/compliance/summary', (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        building_id: 'b1000000-0000-0000-0000-000000000001',
        completeness_score: 0.72,
        completeness_ready: false,
        missing_items: ['laboratory_report', 'radon_measurement', 'site_plan'],
        artefacts: {
          total: 4,
          by_status: { draft: 2, submitted: 1, acknowledged: 1 },
          pending_submissions: 2,
        },
        readiness: {
          safe_to_start: { status: 'conditionally_ready', score: 0.8, blockers_count: 1 },
          safe_to_tender: { status: 'not_ready', score: 0.5, blockers_count: 3 },
          safe_to_reopen: { status: 'not_evaluated', score: 0.0, blockers_count: 0 },
          safe_to_requalify: { status: 'not_evaluated', score: 0.0, blockers_count: 0 },
        },
        regulatory_checks: {
          identity: { total: 3, complete: 3, missing: 0 },
          diagnostics: { total: 4, complete: 3, missing: 1 },
          documents: { total: 5, complete: 3, missing: 2 },
          zones: { total: 2, complete: 1, missing: 1 },
          samples: { total: 2, complete: 2, missing: 0 },
        },
      }),
    });
  });

  // Building Dashboard aggregate
  await page.route('**/api/v1/buildings/*/dashboard', (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        building_id: 'b1000000-0000-0000-0000-000000000001',
        address: 'Rue du Marche 12',
        city: 'Lausanne',
        canton: 'VD',
        passport_grade: 'B',
        trust: { score: 0.82, level: 'high', trend: 'stable' },
        readiness: { overall_status: 'partially_ready', blocked_count: 1, gate_count: 3 },
        completeness: {
          overall_score: 0.68,
          category_scores: { identity: 1.0, diagnostics: 0.8, documents: 0.5, zones: 0.4 },
          missing_count: 3,
        },
        risk: {
          risk_level: 'medium',
          risk_score: 0.55,
          pollutant_risks: { asbestos: 'high', pcb: 'medium', lead: 'low', hap: 'low', radon: 'low' },
        },
        compliance: { status: 'partially_compliant', overdue_count: 1, upcoming_deadlines: 2, gap_count: 1 },
        activity: {
          total_diagnostics: 3,
          completed_diagnostics: 2,
          total_interventions: 2,
          active_interventions: 1,
          open_actions: 4,
          total_documents: 8,
          total_zones: 5,
          total_samples: 12,
        },
        alerts: { weak_signals: 2, constraint_blockers: 1, quality_issues: 1, open_unknowns: 3 },
        last_updated: '2026-03-08T12:00:00Z',
      }),
    });
  });

  // Shared link passport (public, no auth)
  await page.route('**/api/v1/shared/*/passport', (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        building_address: 'Rue du Marche 12',
        building_city: 'Lausanne',
        building_canton: 'VD',
        building_postal_code: '1003',
        passport: {
          building_id: '00000000-0000-0000-0000-000000000099',
          knowledge_state: {
            proven_pct: 0.45,
            inferred_pct: 0.15,
            declared_pct: 0.1,
            obsolete_pct: 0.05,
            contradictory_pct: 0.02,
            overall_trust: 0.72,
            total_data_points: 85,
            trend: 'improving',
          },
          completeness: {
            overall_score: 0.68,
            category_scores: { safe_to_start: 0.8, safe_to_tender: 0.7, safe_to_reopen: 0.6, safe_to_requalify: 0.5 },
          },
          readiness: {
            safe_to_start: { status: 'ready', score: 0.9, blockers_count: 0 },
            safe_to_tender: { status: 'blocked', score: 0.6, blockers_count: 2 },
            safe_to_reopen: { status: 'not_evaluated', score: 0.0, blockers_count: 0 },
            safe_to_requalify: { status: 'not_evaluated', score: 0.0, blockers_count: 0 },
          },
          blind_spots: { total_open: 3, blocking: 1, by_type: { missing_diagnostic: 2, missing_sample: 1 } },
          contradictions: { total: 2, unresolved: 1, by_type: { construction_year: 1, material_type: 1 } },
          evidence_coverage: {
            diagnostics_count: 3,
            samples_count: 12,
            documents_count: 8,
            interventions_count: 2,
            latest_diagnostic_date: '2025-11-15',
            latest_document_date: '2026-02-10',
          },
          passport_grade: 'C',
          assessed_at: '2026-03-08T10:00:00Z',
        },
        shared_by_org: 'DiagSwiss SA',
        expires_at: '2026-04-08T00:00:00Z',
        audience_type: 'buyer',
      }),
    });
  });

  // Shared link validation (public, no auth)
  await page.route('**/api/v1/shared/*', (route) => {
    const url = route.request().url();
    // Skip if already matched by /shared/*/passport
    if (url.includes('/passport')) return route.fallback();
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        is_valid: true,
        resource_type: 'building',
        resource_id: '00000000-0000-0000-0000-000000000099',
        allowed_sections: null,
        audience_type: 'buyer',
      }),
    });
  });
}
