import { test, expect, type Page } from '@playwright/test';

// Staging review suite for https://swissbuilding.batiscan.ch
// Basic auth is handled by playwright.staging.config.ts httpCredentials

const STAGING_ADMIN_EMAIL = process.env.E2E_REAL_ADMIN_EMAIL || 'admin@swissbuildingos.ch';
const STAGING_ADMIN_PASSWORD = process.env.E2E_REAL_ADMIN_PASSWORD || 'noob42';

async function loginAsAdmin(page: Page) {
  await page.goto('/login');
  await page.waitForLoadState('networkidle');

  const emailInput = page.locator('input[type="email"], input[name="email"]').first();
  const passwordInput = page.locator('input[type="password"]').first();

  await expect(emailInput).toBeVisible();
  await expect(passwordInput).toBeVisible();

  await emailInput.fill(STAGING_ADMIN_EMAIL);
  await passwordInput.fill(STAGING_ADMIN_PASSWORD);
  await page.locator('button[type="submit"]').first().click();

  await page.waitForURL((url) => !url.pathname.includes('/login'), { timeout: 10_000 });
  await expect(page).not.toHaveURL(/login/);
}

test.describe('Health & Infrastructure', () => {
  test('health endpoint returns OK', async ({ request }) => {
    const resp = await request.get('/health');
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe('ok');
    expect(body.service).toBe('swissbuildingos');
  });

  test('API base responds', async ({ request }) => {
    const resp = await request.get('/api/v1/auth/me');
    // 401 is expected without JWT — proves API is reachable
    expect([401, 403]).toContain(resp.status());
  });
});

test.describe('Public Pages Load', () => {
  test('login page loads without crash', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    // Should not show error boundary
    const errorBoundary = page.locator('text=Something went wrong');
    await expect(errorBoundary).not.toBeVisible({ timeout: 5000 });
    // Should show login form or redirect
    await expect(page).toHaveURL(/login/);
  });

  test('login page has no console errors', async ({ page }) => {
    const errors: string[] = [];
    page.on('pageerror', (err) => errors.push(err.message));
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    // Filter out known non-critical errors (PWA, manifest)
    const criticalErrors = errors.filter(
      (e) => !e.includes('manifest') && !e.includes('service-worker') && !e.includes('workbox')
    );
    expect(criticalErrors).toHaveLength(0);
  });

  test('root redirects to login', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/login/);
  });
});

test.describe('Static Assets', () => {
  test('favicon loads (icon.svg)', async ({ request }) => {
    const resp = await request.get('/icon.svg');
    expect(resp.status()).toBe(200);
  });

  test('no 404 on critical assets', async ({ page }) => {
    const notFound: string[] = [];
    page.on('response', (resp) => {
      if (resp.status() === 404 && !resp.url().includes('sockjs')) {
        notFound.push(resp.url());
      }
    });
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    expect(notFound).toHaveLength(0);
  });
});

test.describe('Login Flow', () => {
  test('login form is visible', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');
    // Look for email/password inputs
    const emailInput = page.locator('input[type="email"], input[name="email"]');
    const passwordInput = page.locator('input[type="password"]');
    // At least one should be visible (form exists)
    const hasForm = (await emailInput.count()) > 0 || (await passwordInput.count()) > 0;
    expect(hasForm).toBeTruthy();
  });

  test('login with admin credentials', async ({ page }) => {
    await loginAsAdmin(page);
    await expect(page).toHaveURL(/dashboard|control-tower|buildings|portfolio|marketplace/);
  });
});

test.describe('Authenticated Pages (if login succeeds)', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('dashboard loads', async ({ page }) => {
    await page.goto('/');
    await page.waitForLoadState('networkidle');
    // Should show dashboard or redirect to it
    const pageContent = await page.content();
    expect(pageContent.length).toBeGreaterThan(100);
  });

  test('buildings list loads', async ({ page }) => {
    await page.goto('/buildings');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/staging-buildings.png' });
  });

  test('control tower loads', async ({ page }) => {
    await page.goto('/control-tower');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/staging-control-tower.png' });
  });

  test('marketplace companies loads', async ({ page }) => {
    await page.goto('/marketplace/companies');
    await page.waitForLoadState('networkidle');
    await page.waitForTimeout(2000);
    await page.screenshot({ path: 'test-results/staging-marketplace.png' });
  });

  test('no error boundaries on main pages', async ({ page }) => {
    const pages = ['/', '/buildings', '/control-tower', '/marketplace/companies'];
    for (const p of pages) {
      await page.goto(p);
      await page.waitForLoadState('networkidle');
      const errorBoundary = page.locator('text=Something went wrong');
      await expect(errorBoundary).not.toBeVisible({ timeout: 3000 });
    }
  });
});
