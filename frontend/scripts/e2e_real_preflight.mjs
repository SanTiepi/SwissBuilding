import process from 'node:process';

const DEFAULTS = {
  apiBase: 'http://localhost:8000',
  email: 'admin@swissbuildingos.ch',
  password: 'noob42',
  minBuildings: 3,
  minDiagnostics: 1,
  minActions: 1,
  minInterventions: 1,
  minArtefacts: 1,
  timeoutMs: 10000,
  maxBuildingScan: 25,
  pageSize: 100,
};

/**
 * Partial address fragments for canonical scenario buildings.
 * Must match seed_data.py SCENARIO_IDS building addresses.
 */
const CANONICAL_SCENARIO_ADDRESSES = {
  contradiction: 'Contradictions',
  nearly_ready: 'Presque Prêt',
  post_works: 'Post-Travaux',
  portfolio_cluster: 'Lot Portefeuille',
  empty_dossier: 'Nouveau Import',
};

function getIntEnv(name, fallback) {
  const raw = process.env[name];
  if (!raw) {
    return fallback;
  }
  const parsed = Number.parseInt(raw, 10);
  return Number.isFinite(parsed) ? parsed : fallback;
}

const config = {
  apiBase: (process.env.E2E_REAL_API_BASE || DEFAULTS.apiBase).replace(/\/+$/, ''),
  email: process.env.E2E_REAL_ADMIN_EMAIL || DEFAULTS.email,
  password: process.env.E2E_REAL_ADMIN_PASSWORD || DEFAULTS.password,
  minBuildings: getIntEnv('E2E_REAL_MIN_BUILDINGS', DEFAULTS.minBuildings),
  minDiagnostics: getIntEnv('E2E_REAL_MIN_DIAGNOSTICS', DEFAULTS.minDiagnostics),
  minActions: getIntEnv('E2E_REAL_MIN_ACTIONS', DEFAULTS.minActions),
  minInterventions: getIntEnv('E2E_REAL_MIN_INTERVENTIONS', DEFAULTS.minInterventions),
  minArtefacts: getIntEnv('E2E_REAL_MIN_ARTEFACTS', DEFAULTS.minArtefacts),
  timeoutMs: getIntEnv('E2E_REAL_TIMEOUT_MS', DEFAULTS.timeoutMs),
  maxBuildingScan: getIntEnv('E2E_REAL_MAX_BUILDING_SCAN', DEFAULTS.maxBuildingScan),
  pageSize: getIntEnv('E2E_REAL_PAGE_SIZE', DEFAULTS.pageSize),
};

function logStep(message) {
  console.log(`[preflight] ${message}`);
}

function logWarn(message) {
  console.warn(`[preflight:warn] ${message}`);
}

function makeFailureError(message) {
  console.error(`[preflight:error] ${message}`);
  console.error('[preflight:hint] Typical recovery flow:');
  console.error('  1) cd infrastructure && docker compose up -d');
  console.error('  2) cd backend && python -m app.seeds.seed_demo --commune Lausanne --limit 150');
  console.error('  3) cd backend && python -m app.seeds.seed_verify');
  console.error('[preflight:hint] If another API already uses :8000, point frontend/e2e to SwissBuilding explicitly:');
  console.error('  - set E2E_REAL_API_BASE=http://localhost:<your_backend_port>');
  console.error('  - set VITE_API_PROXY_TARGET=http://localhost:<your_backend_port>');
  console.error('[preflight:hint] If admin credentials differ, set:');
  console.error('  - E2E_REAL_ADMIN_EMAIL');
  console.error('  - E2E_REAL_ADMIN_PASSWORD');
  const error = new Error(message);
  error.preflightPrinted = true;
  return error;
}

function parseItems(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (payload && Array.isArray(payload.items)) {
    return payload.items;
  }
  return [];
}

function parseItemsCount(payload) {
  if (typeof payload?.total === 'number') {
    return payload.total;
  }
  return parseItems(payload).length;
}

function isSwissBuildingBackend(healthPayload) {
  const service = typeof healthPayload?.service === 'string' ? healthPayload.service.toLowerCase() : '';
  const app = typeof healthPayload?.app === 'string' ? healthPayload.app.toLowerCase() : '';
  return service.includes('swissbuilding') || app.includes('swissbuilding');
}

async function requestJson(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), config.timeoutMs);
  try {
    const response = await fetch(`${config.apiBase}${path}`, {
      ...options,
      signal: controller.signal,
      headers: {
        Accept: 'application/json',
        ...(options.headers || {}),
      },
    });

    const text = await response.text();
    const data = text ? safeParseJson(text) : null;

    if (!response.ok) {
      const bodyRaw = (typeof data === 'object' && data !== null && 'detail' in data ? data.detail : data) || text;
      const body = typeof bodyRaw === 'string' ? bodyRaw : JSON.stringify(bodyRaw);
      throw new Error(`HTTP ${response.status} on ${path}: ${String(body).slice(0, 400)}`);
    }
    return data;
  } catch (error) {
    if (error?.name === 'AbortError') {
      throw new Error(
        `Request to ${path} timed out after ${config.timeoutMs}ms. ` +
          `Is the backend running at ${config.apiBase}?`
      );
    }
    throw error;
  } finally {
    clearTimeout(timer);
  }
}

function safeParseJson(text) {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

async function main() {
  if (process.env.SKIP_REAL_E2E_PREFLIGHT === '1') {
    logStep('Skipping preflight due to SKIP_REAL_E2E_PREFLIGHT=1');
    return;
  }

  // ── Phase 1: Backend health ──────────────────────────────────────────
  logStep(`Checking backend at ${config.apiBase}`);
  const health = await requestJson('/health', { method: 'GET' });
  if (!health || health.status !== 'ok') {
    throw makeFailureError(`Backend health endpoint returned unexpected payload: ${JSON.stringify(health)}`);
  }
  if (!isSwissBuildingBackend(health)) {
    throw makeFailureError(
      `Backend at ${config.apiBase} does not look like SwissBuilding (health payload: ${JSON.stringify(health)}).`
    );
  }
  logStep('Backend health is OK');

  // ── Phase 2: Authentication ──────────────────────────────────────────
  let loginPayload;
  try {
    loginPayload = await requestJson('/api/v1/auth/login', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        email: config.email,
        password: config.password,
      }),
    });
  } catch (error) {
    throw makeFailureError(`Login failed for ${config.email}: ${error instanceof Error ? error.message : String(error)}`);
  }

  const token = loginPayload?.access_token;
  if (!token || typeof token !== 'string') {
    throw makeFailureError('Login succeeded but no access_token was returned.');
  }
  logStep(`Auth login is OK (${config.email})`);

  const mePayload = await requestJson('/api/v1/auth/me', {
    method: 'GET',
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  const meRole = mePayload?.role;
  if (meRole !== 'admin') {
    logWarn(`Authenticated user role is "${meRole}" (expected "admin"). Some tests may lack permissions.`);
  }
  logStep(`Auth /me is OK (role: ${meRole || 'unknown'})`);

  const authHeaders = { Authorization: `Bearer ${token}` };

  // ── Phase 3: Buildings baseline ──────────────────────────────────────
  const buildingsPayload = await requestJson(`/api/v1/buildings?page=1&size=${config.pageSize}`, {
    method: 'GET',
    headers: authHeaders,
  });
  const buildings = parseItems(buildingsPayload);
  logStep(`Buildings available: ${buildings.length}`);

  if (buildings.length < config.minBuildings) {
    throw makeFailureError(
      `Insufficient seeded buildings: got ${buildings.length}, need at least ${config.minBuildings}.`
    );
  }

  // ── Phase 4: Diagnostics baseline ────────────────────────────────────
  let diagnosticsFound = 0;
  const maxScan = Math.min(config.maxBuildingScan, buildings.length);
  for (let i = 0; i < maxScan && diagnosticsFound < config.minDiagnostics; i += 1) {
    const buildingId = buildings[i]?.id;
    if (!buildingId) {
      continue;
    }
    const diagnosticsPayload = await requestJson(`/api/v1/buildings/${buildingId}/diagnostics`, {
      method: 'GET',
      headers: authHeaders,
    });
    const diagnostics = parseItems(diagnosticsPayload);
    diagnosticsFound += diagnostics.length;
  }

  logStep(`Diagnostics found across scanned buildings: ${diagnosticsFound}`);
  if (diagnosticsFound < config.minDiagnostics) {
    throw makeFailureError(
      `Insufficient diagnostics for real e2e: got ${diagnosticsFound}, need at least ${config.minDiagnostics}.`
    );
  }

  // ── Phase 5: Canonical scenario buildings ────────────────────────────
  // These checks verify that the 5 scenario buildings from seed_data.py
  // are present. This is critical for the dossier progression tests.
  logStep('Checking canonical scenario buildings...');

  // Collect all buildings across pages for scenario matching
  let allBuildings = [...buildings];
  const totalBuildings = buildingsPayload?.total ?? buildings.length;
  if (totalBuildings > config.pageSize) {
    const extraPages = Math.min(Math.ceil(totalBuildings / config.pageSize), 5);
    for (let p = 2; p <= extraPages; p++) {
      const extraPayload = await requestJson(`/api/v1/buildings?page=${p}&size=${config.pageSize}`, {
        method: 'GET',
        headers: authHeaders,
      });
      allBuildings = allBuildings.concat(parseItems(extraPayload));
    }
  }

  const scenarioErrors = [];
  for (const [scenarioName, addressFragment] of Object.entries(CANONICAL_SCENARIO_ADDRESSES)) {
    const fragment = addressFragment.toLowerCase();
    const found = allBuildings.find(
      (b) => typeof b.address === 'string' && b.address.toLowerCase().includes(fragment)
    );
    if (found) {
      logStep(`  Scenario "${scenarioName}": found (id=${found.id})`);
    } else {
      scenarioErrors.push(
        `Scenario "${scenarioName}" building (address containing "${addressFragment}") not found in ${allBuildings.length} buildings.`
      );
    }
  }

  if (scenarioErrors.length > 0) {
    throw makeFailureError(
      `Missing canonical scenario buildings:\n  - ${scenarioErrors.join('\n  - ')}\n` +
        'Run: python -m app.seeds.seed_data'
    );
  }
  logStep('All 5 canonical scenario buildings present');

  // ── Phase 6: Scenario data depth checks ──────────────────────────────
  // These are now hard failures (not warnings) because the canonical
  // dossier progression tests depend on them.
  const scenarioDataErrors = [];

  // Check actions (global endpoint)
  try {
    const actionsPayload = await requestJson('/api/v1/actions?page=1&size=1', {
      method: 'GET',
      headers: authHeaders,
    });
    const actionsCount = parseItemsCount(actionsPayload);
    logStep(`Actions available: ${actionsCount}`);
    if (actionsCount < config.minActions) {
      scenarioDataErrors.push(
        `Actions: found ${actionsCount}, expected at least ${config.minActions}. ` +
          'Run: python -m app.seeds.seed_demo_enrich'
      );
    }
  } catch (error) {
    scenarioDataErrors.push(`Actions check failed: ${error instanceof Error ? error.message : String(error)}`);
  }

  // Check interventions (building-scoped — scan first buildings)
  let interventionsFound = 0;
  try {
    for (let i = 0; i < maxScan && interventionsFound < config.minInterventions; i += 1) {
      const buildingId = buildings[i]?.id;
      if (!buildingId) continue;
      const interventionsPayload = await requestJson(
        `/api/v1/buildings/${buildingId}/interventions?page=1&size=1`,
        { method: 'GET', headers: authHeaders }
      );
      interventionsFound += parseItemsCount(interventionsPayload);
    }
    logStep(`Interventions found across scanned buildings: ${interventionsFound}`);
    if (interventionsFound < config.minInterventions) {
      scenarioDataErrors.push(
        `Interventions: found ${interventionsFound}, expected at least ${config.minInterventions}. ` +
          'Run: python -m app.seeds.seed_demo_enrich'
      );
    }
  } catch (error) {
    scenarioDataErrors.push(`Interventions check failed: ${error instanceof Error ? error.message : String(error)}`);
  }

  // Check compliance artefacts (building-scoped — scan first buildings)
  let artefactsFound = 0;
  try {
    for (let i = 0; i < maxScan && artefactsFound < config.minArtefacts; i += 1) {
      const buildingId = buildings[i]?.id;
      if (!buildingId) continue;
      const artefactsPayload = await requestJson(
        `/api/v1/buildings/${buildingId}/compliance-artefacts?page=1&size=1`,
        { method: 'GET', headers: authHeaders }
      );
      artefactsFound += parseItemsCount(artefactsPayload);
    }
    logStep(`Compliance artefacts found across scanned buildings: ${artefactsFound}`);
    if (artefactsFound < config.minArtefacts) {
      scenarioDataErrors.push(
        `Compliance artefacts: found ${artefactsFound}, expected at least ${config.minArtefacts}. ` +
          'Run: python -m app.seeds.seed_demo_authority'
      );
    }
  } catch (error) {
    scenarioDataErrors.push(
      `Compliance artefacts check failed: ${error instanceof Error ? error.message : String(error)}`
    );
  }

  // Report scenario data issues — now hard failures
  if (scenarioDataErrors.length > 0) {
    throw makeFailureError(
      `Scenario data insufficient for canonical dossier progression:\n  - ${scenarioDataErrors.join('\n  - ')}`
    );
  }

  logStep('All scenario data checks passed');
  logStep('Real e2e preflight passed');
}

main().catch((error) => {
  if (!error?.preflightPrinted) {
    const message = error instanceof Error ? error.message : String(error);
    console.error(`[preflight:error] ${message}`);
  }
  process.exitCode = 1;
});
