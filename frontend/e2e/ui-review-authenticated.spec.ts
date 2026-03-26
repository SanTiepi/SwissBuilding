/**
 * SwissBuilding — Authenticated UI Review
 * Logs in then captures EVERY page with real content visible.
 */
import { test, type Page, type BrowserContext } from '@playwright/test';

const BASE_URL = process.env.REVIEW_URL || 'http://194.93.48.163:8080';
const EMAIL = 'admin@swissbuildingos.ch';
const PASSWORD = 'Admin2026!';

const PAGES = [
  { path: '/dashboard', name: 'dashboard' },
  { path: '/settings', name: 'settings' },
  { path: '/buildings', name: 'buildings-list' },
  { path: '/portfolio', name: 'portfolio' },
  { path: '/campaigns', name: 'campaigns' },
  { path: '/comparison', name: 'building-comparison' },
  { path: '/risk-simulator', name: 'risk-simulator' },
  { path: '/map', name: 'pollutant-map' },
  { path: '/actions', name: 'actions' },
  { path: '/documents', name: 'documents' },
  { path: '/exports', name: 'export-jobs' },
  { path: '/authority-packs', name: 'authority-packs' },
  { path: '/admin/users', name: 'admin-users' },
  { path: '/admin/organizations', name: 'admin-organizations' },
  { path: '/admin/invitations', name: 'admin-invitations' },
  { path: '/admin/jurisdictions', name: 'admin-jurisdictions' },
  { path: '/admin/audit-logs', name: 'admin-audit-logs' },
  { path: '/rules-studio', name: 'rules-studio' },
];

const VIEWPORTS = [
  { name: 'desktop', width: 1920, height: 1080 },
  { name: 'mobile', width: 375, height: 812 },
];

interface PageResult {
  name: string;
  viewport: string;
  httpStatus: number | null;
  loadTime: number;
  consoleErrors: string[];
  networkErrors: string[];
  brokenImages: number;
  hasContent: boolean;
  visibleText: string;
}

const results: PageResult[] = [];

async function login(page: Page): Promise<boolean> {
  await page.goto(`${BASE_URL}/login`, { timeout: 15000 });
  await page.waitForLoadState('networkidle', { timeout: 8000 }).catch(() => {});

  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passwordInput = page.locator('input[type="password"]').first();

  if (!(await emailInput.isVisible({ timeout: 5000 }).catch(() => false))) {
    return false;
  }

  await emailInput.fill(EMAIL);
  await passwordInput.fill(PASSWORD);

  const submitBtn = page.locator('button[type="submit"]').first();
  await submitBtn.click();

  // Wait for redirect away from login
  try {
    await page.waitForURL(url => !url.toString().includes('/login'), { timeout: 10000 });
    return true;
  } catch {
    return false;
  }
}

test.describe('Authenticated UI Review', () => {
  let sharedContext: BrowserContext;
  let loggedIn = false;

  test.beforeAll(async ({ browser }) => {
    sharedContext = await browser.newContext({
      viewport: { width: 1920, height: 1080 },
    });
    const page = await sharedContext.newPage();
    loggedIn = await login(page);
    console.warn(`Login: ${loggedIn ? 'SUCCESS' : 'FAILED'}`);
    await page.close();
  });

  test.afterAll(async () => {
    await sharedContext?.close();

    // Print report
    console.warn('\n' + '='.repeat(80));
    console.warn('SWISSBUILDING AUTHENTICATED UI REVIEW');
    console.warn('='.repeat(80));
    console.warn(`Login: ${loggedIn ? 'SUCCESS' : 'FAILED'}`);
    console.warn(`Pages reviewed: ${results.length}`);

    const withErrors = results.filter(r => r.consoleErrors.length > 0);
    const withNetErrors = results.filter(r => r.networkErrors.length > 0);
    const withContent = results.filter(r => r.hasContent);
    const withBroken = results.filter(r => r.brokenImages > 0);

    console.warn(`Pages with real content: ${withContent.length}/${results.length}`);
    console.warn(`Pages with console errors: ${withErrors.length}`);
    console.warn(`Pages with network errors: ${withNetErrors.length}`);
    console.warn(`Pages with broken images: ${withBroken.length}`);
    console.warn('');

    for (const r of results) {
      const icon = r.consoleErrors.length > 0 || r.networkErrors.length > 0 ? '❌' :
                   r.hasContent ? '✅' : '⚠️';
      console.warn(`${icon} ${r.name} @ ${r.viewport} — ${r.loadTime}ms — HTTP ${r.httpStatus} — content: ${r.hasContent}`);
      if (r.consoleErrors.length > 0) {
        r.consoleErrors.slice(0, 3).forEach(e => console.warn(`   ⚠ Console: ${e}`));
      }
      if (r.networkErrors.length > 0) {
        r.networkErrors.slice(0, 3).forEach(e => console.warn(`   🔴 Network: ${e}`));
      }
      if (r.brokenImages > 0) {
        console.warn(`   🖼 Broken images: ${r.brokenImages}`);
      }
      if (r.visibleText) {
        console.warn(`   📄 "${r.visibleText.substring(0, 100)}"`);
      }
    }
    console.warn('='.repeat(80));
  });

  for (const pg of PAGES) {
    for (const vp of VIEWPORTS) {
      test(`${pg.name} @ ${vp.name}`, async () => {
        const page = await sharedContext.newPage();
        await page.setViewportSize({ width: vp.width, height: vp.height });

        const consoleErrors: string[] = [];
        const networkErrors: string[] = [];

        page.on('console', msg => {
          if (msg.type() === 'error') {
            consoleErrors.push(msg.text().substring(0, 200));
          }
        });
        page.on('requestfailed', req => {
          networkErrors.push(`${req.method()} ${req.url().substring(0, 100)} — ${req.failure()?.errorText}`);
        });

        const start = Date.now();
        let httpStatus: number | null = null;

        try {
          const resp = await page.goto(`${BASE_URL}${pg.path}`, {
            timeout: 15000,
            waitUntil: 'domcontentloaded',
          });
          httpStatus = resp?.status() ?? null;
        } catch (e: unknown) {
          const msg = e instanceof Error ? e.message : String(e);
          consoleErrors.push(`Nav error: ${msg.substring(0, 150)}`);
        }

        // Wait for async content to load
        await page.waitForTimeout(3000);
        const loadTime = Date.now() - start;

        // Check if we see real content (not just login page)
        const bodyText = await page.locator('body').innerText().catch(() => '');
        const isOnLogin = bodyText.includes('Se connecter') || bodyText.includes('Mot de passe');
        const hasContent = !isOnLogin && bodyText.length > 50;

        // Get first meaningful heading or text
        const heading = await page.locator('h1, h2, [class*="title"]').first().innerText()
          .catch(() => '');

        // Check broken images
        const brokenImages = await page.evaluate(() => {
          const imgs = document.querySelectorAll('img');
          let broken = 0;
          imgs.forEach(img => {
            if (img.naturalWidth === 0 && img.src && !img.src.startsWith('data:')) broken++;
          });
          return broken;
        }).catch(() => 0);

        // Screenshot
        const ssPath = `test-results/ui-review-auth/${pg.name}-${vp.name}.png`;
        await page.screenshot({ path: ssPath, fullPage: true }).catch(() => {});

        results.push({
          name: pg.name,
          viewport: vp.name,
          httpStatus,
          loadTime,
          consoleErrors,
          networkErrors,
          brokenImages,
          hasContent,
          visibleText: heading || bodyText.substring(0, 100),
        });

        await page.close();
      });
    }
  }
});
