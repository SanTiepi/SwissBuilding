import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes, mockApiError } from './helpers';

test.describe('Unhappy paths — error scenarios', () => {
  test('login with invalid credentials shows error message', async ({ page }) => {
    // Mock login endpoint to return 401
    await page.route('**/api/v1/auth/login', (route) =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid email or password' }),
      })
    );

    await page.goto('/login');
    await page.locator('#email').fill('wrong@example.ch');
    await page.locator('#password').fill('wrongpassword');
    await page.getByRole('button', { name: /connecter|sign in|anmelden|accedi/i }).click();

    // Error message should be visible
    const errorBox = page.locator('.bg-red-50');
    await expect(errorBox).toBeVisible();

    // Should NOT navigate to dashboard
    await expect(page).toHaveURL(/\/login/);
  });

  test('expired token redirects to login', async ({ page }) => {
    // Set up auth state so the app thinks we're logged in
    await mockAuthState(page);
    await mockApiRoutes(page);

    // Mock /auth/me to return 401 (expired token) — overrides mockApiRoutes handler
    await page.route('**/api/v1/auth/me', (route) =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Token expired' }),
      })
    );

    // Mock buildings to also return 401 (simulates expired token on data fetch)
    await page.route(/\/api\/v1\/buildings(\?.*)?$/, (route) =>
      route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Not authenticated' }),
      })
    );

    await page.goto('/dashboard');

    // The axios interceptor should redirect to /login on 401
    await expect(page).toHaveURL(/\/login/, { timeout: 10_000 });
  });

  test('buildings list API 500 shows error state', async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);

    // Override buildings endpoint with 500 AFTER mockApiRoutes
    await mockApiError(page, /\/api\/v1\/buildings(\?.*)?$/, 500);

    await page.goto('/buildings');

    // Should show error state (red background with error message)
    // Timeout accounts for API retry logic (3 retries with exponential backoff ~7s)
    const errorBlock = page.locator('.bg-red-50');
    await expect(errorBlock).toBeVisible({ timeout: 30_000 });
    // Should NOT show loading spinner indefinitely
    await expect(page.locator('.animate-spin')).not.toBeVisible();
  });

  test('dashboard API 500 shows error state instead of empty data', async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);

    // Override buildings endpoint with 500
    await mockApiError(page, /\/api\/v1\/buildings(\?.*)?$/, 500);

    await page.goto('/dashboard');

    // Should show error state, not an empty dashboard with zeros
    // Timeout accounts for API retry logic (3 retries with exponential backoff ~7s)
    const errorBlock = page.locator('.bg-red-50');
    await expect(errorBlock).toBeVisible({ timeout: 30_000 });
  });

  test('building detail with missing risk_scores does not crash', async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);

    // Override building detail to return a building WITHOUT risk_scores
    await page.route('**/api/v1/buildings/b1000000-*', (route) => {
      if (route.request().method() !== 'GET') return route.fallback();
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'b1000000-0000-0000-0000-000000000001',
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
          risk_scores: null,
          created_at: '2024-01-15T10:00:00Z',
          updated_at: '2024-06-01T14:00:00Z',
        }),
      });
    });

    // Override risk analysis to return 404
    await mockApiError(page, '**/api/v1/risk-analysis/building/**', 404);

    await page.goto('/buildings/b1000000-0000-0000-0000-000000000001');

    // Page should load without crashing — address should be visible
    await expect(page.getByRole('heading', { name: 'Rue de Bourg 1' })).toBeVisible();

    // No error boundary should be triggered
    const errorBoundary = page.locator('[data-testid="error-boundary"], .error-boundary');
    await expect(errorBoundary).toHaveCount(0);

    // "No risk data" placeholder should appear
    const noRiskText = page.locator('text=/aucune donn|no risk data|keine risikodaten/i');
    await expect(noRiskText).toBeVisible();
  });

  test('create building mutation 500 shows toast error', async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);

    // Override POST /buildings to return 500
    await page.route('**/api/v1/buildings', (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      return route.fulfill({
        status: 500,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Database connection failed' }),
      });
    });

    await page.goto('/buildings');

    // Open create modal
    await page.getByRole('button', { name: /ajouter|add|hinzuf|aggiungi/i }).click();

    // Fill required fields
    await page.locator('input[name="address"]').fill('Rue Test 99');
    await page.locator('input[name="city"]').fill('Geneve');
    await page.locator('input[name="postal_code"]').fill('1200');
    await page.locator('select[name="canton"]').selectOption('GE');
    await page.locator('input[name="construction_year"]').fill('1970');
    await page.locator('select[name="building_type"]').selectOption('residential');

    // Submit
    await page.getByRole('button', { name: /cr[ée]er|create|erstellen|creare/i }).click();

    // Toast error should appear
    const toastContainer = page.locator('[data-testid="toast-container"]');
    await expect(toastContainer).toBeVisible({ timeout: 10_000 });
    await expect(toastContainer).toContainText('Database connection failed');
  });
});
