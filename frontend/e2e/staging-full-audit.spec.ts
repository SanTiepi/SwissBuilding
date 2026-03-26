import { test, expect, type Page } from '@playwright/test';

/**
 * Comprehensive staging audit — visits every route, checks for crashes,
 * collects console errors, validates API endpoints.
 */

// ── Helpers ──────────────────────────────────────────────────────────

interface PageResult {
  route: string;
  status: 'pass' | 'fail' | 'error-boundary';
  detail?: string;
}

interface ApiResult {
  endpoint: string;
  status: number;
  ok: boolean;
  detail?: string;
}

const consoleErrors: { page: string; message: string }[] = [];

// login is inlined in the test to capture the auth response

async function getAuthToken(page: Page): Promise<string> {
  const token = await page.evaluate(() => {
    // Try zustand persisted auth store (name = 'swissbuildingos-auth')
    for (const key of ['swissbuildingos-auth', 'auth-storage', 'token']) {
      const raw = localStorage.getItem(key);
      if (raw) {
        try {
          const parsed = JSON.parse(raw);
          if (parsed?.state?.token) return parsed.state.token;
          if (parsed?.token) return parsed.token;
          if (typeof parsed === 'string' && parsed.length > 20) return parsed;
        } catch {
          if (raw.length > 20) return raw;
        }
      }
    }
    return '';
  });
  return token;
}

async function visitPage(page: Page, route: string, label: string): Promise<PageResult> {
  try {
    await page.goto(route, { timeout: 30000 });
    // Give lazy-loaded pages time to settle
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    // Extra settle time for heavy pages
    await page.waitForTimeout(1500);

    // Check for error boundary
    const errorBoundary = await page.locator('[data-testid="error-boundary"], [data-testid="page-error-boundary"]').count();
    if (errorBoundary > 0) {
      const errorText = await page.locator('[data-testid="error-boundary"], [data-testid="page-error-boundary"]').first().textContent();
      return { route: label, status: 'error-boundary', detail: errorText?.slice(0, 200) };
    }

    // Check page rendered something (not completely blank)
    const bodyText = await page.locator('body').textContent();
    if (!bodyText || bodyText.trim().length < 10) {
      return { route: label, status: 'fail', detail: 'Page appears blank or nearly empty' };
    }

    return { route: label, status: 'pass' };
  } catch (err: any) {
    return { route: label, status: 'fail', detail: err.message?.slice(0, 200) };
  }
}

// ── Test ─────────────────────────────────────────────────────────────

test.describe('Staging Full Audit', () => {
  let authToken: string;
  let buildingId: string;
  let orgId: string;
  const pageResults: PageResult[] = [];
  const apiResults: ApiResult[] = [];

  test('Complete staging audit — all routes + API endpoints', async ({ page }) => {
    // Collect console errors globally
    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        consoleErrors.push({ page: page.url(), message: msg.text().slice(0, 300) });
      }
    });
    page.on('pageerror', (err) => {
      consoleErrors.push({ page: page.url(), message: `[PAGE ERROR] ${err.message?.slice(0, 300)}` });
    });

    // ── 1. Login ──
    console.log('=== STEP 1: Login ===');

    // UI login — intercept the /auth/login response to capture the token
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    const loginResponsePromise = page.waitForResponse(
      (r) => r.url().includes('/api/v1/auth/login') && r.status() === 200,
      { timeout: 15000 },
    ).catch(() => null);

    await page.fill('input[name="email"], input[type="email"]', 'admin@swissbuildingos.ch');
    await page.fill('input[name="password"], input[type="password"]', 'noob42');
    await page.click('button[type="submit"]');

    const loginResponse = await loginResponsePromise;
    if (loginResponse) {
      try {
        const body = await loginResponse.json();
        authToken = body.access_token || body.token || '';
      } catch { /* ignore */ }
    }

    // Wait for redirect
    await page.waitForURL('**/dashboard', { timeout: 15000 }).catch(() => {});
    await page.waitForLoadState('networkidle').catch(() => {});

    // Fallback: try localStorage
    if (!authToken) {
      authToken = await getAuthToken(page);
    }
    console.log(`Auth token obtained: ${authToken ? 'YES (' + authToken.slice(0, 20) + '...)' : 'NO'}`);

    // ── 2. Get a real building ID + org ID from API ──
    console.log('\n=== STEP 2: Fetch building & org IDs ===');
    try {
      const buildingsData = await page.evaluate(async (token) => {
        const resp = await fetch('/api/v1/buildings', {
          headers: token ? { Authorization: `Bearer ${token}` } : {},
        });
        if (!resp.ok) return { ok: false, status: resp.status, items: [], raw: '' };
        const data = await resp.json();
        // API may return array directly or {items: [...]} or {results: [...]}
        const items = Array.isArray(data) ? data : (data.items || data.results || data.data || []);
        return { ok: true, status: resp.status, items, raw: JSON.stringify(data).slice(0, 300) };
      }, authToken);
      console.log(`Buildings API status: ${buildingsData.status}, items: ${buildingsData.items.length}`);
      if (buildingsData.items.length === 0) {
        console.log(`Buildings API raw: ${buildingsData.raw}`);
      }
      if (buildingsData.ok && buildingsData.items.length > 0) {
        buildingId = buildingsData.items[0].id;
        orgId = buildingsData.items[0].organization_id;
      }
    } catch (e: any) {
      console.log(`Buildings API error: ${e.message}`);
    }

    // Fallback: extract building ID from the buildings list page
    if (!buildingId) {
      console.log('Trying to extract building ID from UI...');
      await page.goto('/buildings', { timeout: 30000 });
      await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
      await page.waitForTimeout(3000);
      // Look for links to /buildings/{uuid}
      try {
        const buildingLink = await page.locator('a[href*="/buildings/"]').first().getAttribute('href', { timeout: 10000 });
        if (buildingLink) {
          const match = buildingLink.match(/\/buildings\/([a-f0-9-]+)/);
          if (match) buildingId = match[1];
        }
      } catch {
        console.log('No building links found in UI');
      }
    }

    console.log(`Building ID: ${buildingId || 'NOT FOUND'}`);
    console.log(`Org ID: ${orgId || 'NOT FOUND'}`);

    if (!buildingId) {
      console.log('WARNING: No building ID found. Building-specific routes will be skipped.');
    }

    // ── 3. Visit every route ──
    console.log('\n=== STEP 3: Visit all routes ===');

    // --- Static routes (no params) ---
    const staticRoutes = [
      '/dashboard',
      '/control-tower',
      '/buildings',
      '/portfolio',
      '/comparison',
      '/map',
      '/risk-simulator',
      '/actions',
      '/campaigns',
      '/exports',
      '/authority-packs',
      '/documents',
      '/settings',
      '/address-preview',
      '/portfolio-triage',
      '/demo-path',
      '/pilot-scorecard',
      '/indispensability',
      '/rules-studio',
      // Admin routes
      '/admin/users',
      '/admin/organizations',
      '/admin/invitations',
      '/admin/jurisdictions',
      '/admin/audit-logs',
      '/admin/procedures',
      '/admin/diagnostic-review',
      '/admin/intake-review',
      '/admin/demo-runbook',
      '/admin/pilot-dashboard',
      '/admin/rollout',
      '/admin/expansion',
      '/admin/customer-success',
      '/admin/governance-signals',
      '/admin/import-review',
      '/admin/contributor-gateway',
      '/admin/marketplace-reviews',
      '/admin/remediation-intelligence',
      // Marketplace routes
      '/marketplace/companies',
      '/marketplace/rfq',
      '/marketplace/company-workspace',
      '/marketplace/operator-workspace',
    ];

    for (const route of staticRoutes) {
      const result = await visitPage(page, route, route);
      pageResults.push(result);
      const icon = result.status === 'pass' ? 'OK' : 'FAIL';
      console.log(`  [${icon}] ${route}${result.detail ? ' — ' + result.detail : ''}`);
    }

    // --- Building-specific routes ---
    if (buildingId) {
      const buildingRoutes = [
        { path: `/buildings/${buildingId}`, label: '/buildings/{id}' },
        { path: `/buildings/${buildingId}/explorer`, label: '/buildings/{id}/explorer' },
        { path: `/buildings/${buildingId}/interventions`, label: '/buildings/{id}/interventions' },
        { path: `/buildings/${buildingId}/plans`, label: '/buildings/{id}/plans' },
        { path: `/buildings/${buildingId}/readiness`, label: '/buildings/{id}/readiness' },
        { path: `/buildings/${buildingId}/safe-to-x`, label: '/buildings/{id}/safe-to-x' },
        { path: `/buildings/${buildingId}/simulator`, label: '/buildings/{id}/simulator' },
        { path: `/buildings/${buildingId}/decision`, label: '/buildings/{id}/decision' },
        { path: `/buildings/${buildingId}/field-observations`, label: '/buildings/{id}/field-observations' },
        { path: `/buildings/${buildingId}/timeline`, label: '/buildings/{id}/timeline' },
        { path: `/indispensability-export/${buildingId}`, label: '/indispensability-export/{id}' },
      ];

      for (const { path, label } of buildingRoutes) {
        const result = await visitPage(page, path, label);
        pageResults.push(result);
        const icon = result.status === 'pass' ? 'OK' : 'FAIL';
        console.log(`  [${icon}] ${label}${result.detail ? ' — ' + result.detail : ''}`);
      }
    } else {
      console.log('  [SKIP] Building-specific routes — no building ID available');
    }

    // ── 4. Building detail tabs ──
    console.log('\n=== STEP 4: Building detail tabs ===');
    if (!buildingId) {
      console.log('  [SKIP] No building ID available');
    } else {
    await page.goto(`/buildings/${buildingId}`, { timeout: 30000 });
    await page.waitForLoadState('networkidle', { timeout: 15000 }).catch(() => {});
    await page.waitForTimeout(2000);

    const tabNames = ['overview', 'activity', 'diagnostics', 'documents', 'details'];
    for (const tabName of tabNames) {
      try {
        // Try clicking the tab by various selectors
        const tabClicked = await page
          .locator(`button:has-text("${tabName}"), [role="tab"]:has-text("${tabName}"), a:has-text("${tabName}")`)
          .first()
          .click({ timeout: 5000 })
          .then(() => true)
          .catch(() => false);

        if (tabClicked) {
          await page.waitForTimeout(1500);
          const errorBoundary = await page.locator('[data-testid="error-boundary"], [data-testid="page-error-boundary"]').count();
          if (errorBoundary > 0) {
            pageResults.push({ route: `tab:${tabName}`, status: 'error-boundary' });
            console.log(`  [FAIL] Tab: ${tabName} — error boundary`);
          } else {
            pageResults.push({ route: `tab:${tabName}`, status: 'pass' });
            console.log(`  [OK] Tab: ${tabName}`);
          }
        } else {
          pageResults.push({ route: `tab:${tabName}`, status: 'fail', detail: 'Tab button not found' });
          console.log(`  [FAIL] Tab: ${tabName} — button not found`);
        }
      } catch (err: any) {
        pageResults.push({ route: `tab:${tabName}`, status: 'fail', detail: err.message?.slice(0, 150) });
        console.log(`  [FAIL] Tab: ${tabName} — ${err.message?.slice(0, 100)}`);
      }
    } // end tabs loop
    } // end buildingId check for tabs

    // ── 5. API health checks ──
    console.log('\n=== STEP 5: API health checks ===');
    const apiEndpoints: { url: string; label: string }[] = [
      { url: '/api/v1/buildings', label: 'GET /api/v1/buildings' },
      { url: '/api/v1/erp/version', label: 'GET /api/v1/erp/version' },
      { url: '/api/v1/demo/paths', label: 'GET /api/v1/demo/paths' },
      { url: '/api/v1/demo/paths/property_manager', label: 'GET /api/v1/demo/paths/property_manager' },
    ];
    if (buildingId) {
      apiEndpoints.push(
        { url: `/api/v1/buildings/${buildingId}`, label: 'GET /api/v1/buildings/{id}' },
        { url: `/api/v1/buildings/${buildingId}/instant-card`, label: 'GET /api/v1/buildings/{id}/instant-card' },
        { url: `/api/v1/buildings/${buildingId}/indispensability`, label: 'GET /api/v1/buildings/{id}/indispensability' },
        { url: `/api/v1/buildings/${buildingId}/gates/status`, label: 'GET /api/v1/buildings/{id}/gates/status' },
        { url: `/api/v1/buildings/${buildingId}/engagement-summary`, label: 'GET /api/v1/buildings/{id}/engagement-summary' },
        { url: `/api/v1/buildings/${buildingId}/continuity-score`, label: 'GET /api/v1/buildings/{id}/continuity-score' },
        { url: `/api/v1/buildings/${buildingId}/score-explainability`, label: 'GET /api/v1/buildings/{id}/score-explainability' },
        { url: `/api/v1/erp/buildings/${buildingId}`, label: 'GET /api/v1/erp/buildings/{id}' },
      );
    }
    if (orgId) {
      apiEndpoints.push(
        { url: `/api/v1/organizations/${orgId}/value-ledger`, label: 'GET /api/v1/organizations/{org_id}/value-ledger' },
        { url: `/api/v1/organizations/${orgId}/portfolio-triage`, label: 'GET /api/v1/organizations/{org_id}/portfolio-triage' },
        { url: `/api/v1/organizations/${orgId}/portfolio-benchmark`, label: 'GET /api/v1/organizations/{org_id}/portfolio-benchmark' },
      );
    }

    // Use page.evaluate + fetch to call APIs — avoids httpCredentials interference
    for (const { url, label } of apiEndpoints) {
      try {
        const { status, ok, body } = await page.evaluate(
          async ({ url, token }) => {
            try {
              const resp = await fetch(url, {
                headers: token ? { Authorization: `Bearer ${token}` } : {},
              });
              const body = resp.ok ? '' : await resp.text().catch(() => '');
              return { status: resp.status, ok: resp.ok, body: body.slice(0, 200) };
            } catch (e: any) {
              return { status: 0, ok: false, body: e.message || 'fetch error' };
            }
          },
          { url: `https://swissbuilding.batiscan.ch${url}`, token: authToken },
        );
        const result: ApiResult = {
          endpoint: label,
          status,
          ok,
        };
        if (!ok) {
          result.detail = body;
        }
        apiResults.push(result);
        const icon = ok ? 'OK' : 'FAIL';
        console.log(`  [${icon}] ${label} => ${status}${result.detail ? ' — ' + result.detail : ''}`);
      } catch (err: any) {
        apiResults.push({ endpoint: label, status: 0, ok: false, detail: err.message?.slice(0, 200) });
        console.log(`  [FAIL] ${label} => ERROR — ${err.message?.slice(0, 100)}`);
      }
    }

    // ── 6. Summary report ──
    console.log('\n\n========================================');
    console.log('          STAGING AUDIT SUMMARY');
    console.log('========================================\n');

    const passPages = pageResults.filter((r) => r.status === 'pass');
    const failPages = pageResults.filter((r) => r.status !== 'pass');
    console.log(`PAGES: ${passPages.length} pass / ${failPages.length} fail / ${pageResults.length} total\n`);

    if (failPages.length > 0) {
      console.log('--- FAILED PAGES ---');
      for (const r of failPages) {
        console.log(`  [${r.status.toUpperCase()}] ${r.route}${r.detail ? ' — ' + r.detail : ''}`);
      }
      console.log('');
    }

    const passApis = apiResults.filter((r) => r.ok);
    const failApis = apiResults.filter((r) => !r.ok);
    console.log(`APIs: ${passApis.length} pass / ${failApis.length} fail / ${apiResults.length} total\n`);

    if (failApis.length > 0) {
      console.log('--- FAILED APIs ---');
      for (const r of failApis) {
        console.log(`  [${r.status}] ${r.endpoint}${r.detail ? ' — ' + r.detail : ''}`);
      }
      console.log('');
    }

    if (consoleErrors.length > 0) {
      console.log(`CONSOLE ERRORS: ${consoleErrors.length} total`);
      // Deduplicate by message
      const seen = new Set<string>();
      for (const e of consoleErrors) {
        const key = e.message.slice(0, 100);
        if (!seen.has(key)) {
          seen.add(key);
          console.log(`  [${e.page}] ${e.message}`);
        }
      }
    } else {
      console.log('CONSOLE ERRORS: 0');
    }

    console.log('\n========================================');
    console.log('          END OF AUDIT');
    console.log('========================================');

    // Soft-fail: log failures but don't crash the test so we get the full report
    // Only fail if more than 50% of pages crashed
    const crashRate = failPages.length / pageResults.length;
    if (crashRate > 0.5) {
      throw new Error(`Too many pages failed: ${failPages.length}/${pageResults.length}`);
    }
  });
});
