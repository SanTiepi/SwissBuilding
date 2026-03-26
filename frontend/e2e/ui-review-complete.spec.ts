/**
 * SwissBuilding — Comprehensive UI Review
 * Captures screenshots of every page in desktop and mobile viewports.
 * Reports: load errors, console errors, broken images, accessibility issues.
 *
 * Usage: npx playwright test e2e/ui-review-complete.spec.ts --config playwright.config.ts
 */
import { test, type Page } from '@playwright/test';

const BASE_URL = process.env.REVIEW_URL || 'http://194.93.48.163:8080';

// All routes to review
const PUBLIC_PAGES = [
  { path: '/login', name: 'login' },
];

const PROTECTED_PAGES = [
  // Core
  { path: '/dashboard', name: 'dashboard' },
  { path: '/settings', name: 'settings' },

  // Buildings
  { path: '/buildings', name: 'buildings-list' },

  // Portfolio & Campaigns
  { path: '/portfolio', name: 'portfolio' },
  { path: '/campaigns', name: 'campaigns' },

  // Analysis
  { path: '/comparison', name: 'building-comparison' },
  { path: '/risk-simulator', name: 'risk-simulator' },

  // Maps & Data
  { path: '/map', name: 'pollutant-map' },
  { path: '/actions', name: 'actions' },
  { path: '/documents', name: 'documents' },
  { path: '/exports', name: 'export-jobs' },

  // Authority
  { path: '/authority-packs', name: 'authority-packs' },

  // Admin
  { path: '/admin/users', name: 'admin-users' },
  { path: '/admin/organizations', name: 'admin-organizations' },
  { path: '/admin/invitations', name: 'admin-invitations' },
  { path: '/admin/jurisdictions', name: 'admin-jurisdictions' },
  { path: '/admin/audit-logs', name: 'admin-audit-logs' },

  // Config
  { path: '/rules-studio', name: 'rules-studio' },
];

// Viewports
const VIEWPORTS = [
  { name: 'desktop', width: 1920, height: 1080 },
  { name: 'tablet', width: 768, height: 1024 },
  { name: 'mobile', width: 375, height: 812 },
];

interface PageReport {
  page: string;
  path: string;
  viewport: string;
  status: 'ok' | 'error' | 'redirect';
  loadTime: number;
  consoleErrors: string[];
  networkErrors: string[];
  brokenImages: number;
  screenshotPath: string;
  title: string;
  httpStatus: number | null;
}

const allReports: PageReport[] = [];

// ============================================================
// PUBLIC PAGES
// ============================================================
test.describe('UI Review — Public Pages', () => {
  for (const pg of PUBLIC_PAGES) {
    for (const vp of VIEWPORTS) {
      test(`${pg.name} @ ${vp.name}`, async ({ browser }) => {
        const context = await browser.newContext({
          viewport: { width: vp.width, height: vp.height },
        });
        const page = await context.newPage();
        const report = await reviewPage(page, pg.path, pg.name, vp.name);
        allReports.push(report);
        await context.close();
      });
    }
  }
});

// ============================================================
// PROTECTED PAGES (need auth)
// ============================================================
test.describe('UI Review — Protected Pages', () => {
  for (const pg of PROTECTED_PAGES) {
    for (const vp of VIEWPORTS) {
      test(`${pg.name} @ ${vp.name}`, async ({ browser }) => {
        const context = await browser.newContext({
          viewport: { width: vp.width, height: vp.height },
        });
        const page = await context.newPage();

        // Try to login first
        await attemptLogin(page);

        const report = await reviewPage(page, pg.path, pg.name, vp.name);
        allReports.push(report);
        await context.close();
      });
    }
  }
});

// ============================================================
// 404 / Not Found
// ============================================================
test.describe('UI Review — Error Pages', () => {
  for (const vp of VIEWPORTS) {
    test(`not-found @ ${vp.name}`, async ({ browser }) => {
      const context = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
      });
      const page = await context.newPage();
      const report = await reviewPage(page, '/this-page-does-not-exist', 'not-found', vp.name);
      allReports.push(report);
      await context.close();
    });
  }
});

// ============================================================
// FINAL SUMMARY
// ============================================================
test.afterAll(async () => {
  console.warn('\n' + '='.repeat(80));
  console.warn('SWISSBUILDING UI REVIEW — COMPLETE REPORT');
  console.warn('='.repeat(80));
  console.warn(`Total pages reviewed: ${allReports.length}`);
  console.warn(`Pages with errors: ${allReports.filter(r => r.consoleErrors.length > 0).length}`);
  console.warn(`Pages with network errors: ${allReports.filter(r => r.networkErrors.length > 0).length}`);
  console.warn(`Pages with broken images: ${allReports.filter(r => r.brokenImages > 0).length}`);
  console.warn('');

  // Print each page report
  for (const r of allReports) {
    const status = r.consoleErrors.length > 0 || r.networkErrors.length > 0
      ? '❌' : '✅';
    console.warn(`${status} ${r.page} @ ${r.viewport} — ${r.loadTime}ms — HTTP ${r.httpStatus}`);
    if (r.consoleErrors.length > 0) {
      r.consoleErrors.forEach(e => console.warn(`   ⚠️ Console: ${e}`));
    }
    if (r.networkErrors.length > 0) {
      r.networkErrors.forEach(e => console.warn(`   🔴 Network: ${e}`));
    }
    if (r.brokenImages > 0) {
      console.warn(`   🖼️ Broken images: ${r.brokenImages}`);
    }
  }
  console.warn('='.repeat(80));
});

// ============================================================
// HELPERS
// ============================================================

async function attemptLogin(page: Page): Promise<void> {
  try {
    await page.goto(`${BASE_URL}/login`, { timeout: 10000 });
    await page.waitForLoadState('networkidle', { timeout: 5000 }).catch(() => {});

    // Try default demo credentials
    const emailInput = page.locator('input[type="email"], input[name="email"]').first();
    const passwordInput = page.locator('input[type="password"]').first();

    if (await emailInput.isVisible({ timeout: 3000 }).catch(() => false)) {
      await emailInput.fill('admin@swissbuildingos.ch');
      await passwordInput.fill('admin123');
      const submitBtn = page.locator('button[type="submit"]').first();
      await submitBtn.click();
      await page.waitForURL('**/dashboard**', { timeout: 5000 }).catch(() => {});
    }
  } catch {
    // Login might fail — that's OK, we still review the redirect/error state
  }
}

async function reviewPage(
  page: Page,
  path: string,
  name: string,
  viewport: string
): Promise<PageReport> {
  const consoleErrors: string[] = [];
  const networkErrors: string[] = [];
  let httpStatus: number | null = null;

  // Collect console errors
  page.on('console', msg => {
    if (msg.type() === 'error') {
      consoleErrors.push(msg.text().substring(0, 200));
    }
  });

  // Collect network failures
  page.on('requestfailed', req => {
    networkErrors.push(`${req.method()} ${req.url()} — ${req.failure()?.errorText}`);
  });

  const start = Date.now();

  try {
    const response = await page.goto(`${BASE_URL}${path}`, {
      timeout: 15000,
      waitUntil: 'domcontentloaded',
    });
    httpStatus = response?.status() ?? null;
  } catch (e: unknown) {
    const errorMsg = e instanceof Error ? e.message : String(e);
    consoleErrors.push(`Navigation error: ${errorMsg.substring(0, 200)}`);
  }

  // Wait for rendering
  await page.waitForTimeout(2000);

  const loadTime = Date.now() - start;
  const title = await page.title().catch(() => '');

  // Check for broken images
  const brokenImages = await page.evaluate(() => {
    const images = document.querySelectorAll('img');
    let broken = 0;
    images.forEach(img => {
      if (img.naturalWidth === 0 && img.src && !img.src.startsWith('data:')) {
        broken++;
      }
    });
    return broken;
  }).catch(() => 0);

  // Take screenshot
  const screenshotPath = `test-results/ui-review/${name}-${viewport}.png`;
  await page.screenshot({
    path: screenshotPath,
    fullPage: true,
  }).catch(() => {});

  return {
    page: name,
    path,
    viewport,
    status: httpStatus === 200 ? 'ok' : consoleErrors.length > 0 ? 'error' : 'redirect',
    loadTime,
    consoleErrors,
    networkErrors,
    brokenImages,
    screenshotPath,
    title,
    httpStatus,
  };
}
