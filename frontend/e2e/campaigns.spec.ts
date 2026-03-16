import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

const MOCK_CAMPAIGNS = {
  items: [
    {
      id: 'c1000000-0000-0000-0000-000000000001',
      title: 'Campagne diagnostic amiante 2026',
      description: 'Diagnostic amiante systématique sur le parc résidentiel',
      campaign_type: 'diagnostic',
      status: 'active',
      priority: 'high',
      organization_id: null,
      building_ids: ['b1', 'b2', 'b3', 'b4', 'b5'],
      target_count: 5,
      completed_count: 2,
      date_start: '2026-01-15',
      date_end: '2026-06-30',
      budget_chf: 75000,
      spent_chf: 28000,
      criteria_json: null,
      notes: null,
      created_by: null,
      created_at: '2026-01-10T08:00:00Z',
      updated_at: '2026-02-15T14:30:00Z',
      progress_pct: 40,
    },
    {
      id: 'c1000000-0000-0000-0000-000000000002',
      title: 'Maintenance préventive Q2',
      description: null,
      campaign_type: 'maintenance',
      status: 'draft',
      priority: 'medium',
      organization_id: null,
      building_ids: ['b1', 'b2', 'b3'],
      target_count: 3,
      completed_count: 0,
      date_start: '2026-04-01',
      date_end: null,
      budget_chf: null,
      spent_chf: null,
      criteria_json: null,
      notes: null,
      created_by: null,
      created_at: '2026-03-01T10:00:00Z',
      updated_at: '2026-03-01T10:00:00Z',
      progress_pct: 0,
    },
  ],
  total: 2,
  page: 1,
  size: 50,
  pages: 1,
};

test.describe('Campaigns Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);

    await page.route('**/api/v1/campaigns*', (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify(MOCK_CAMPAIGNS),
        });
      }
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            ...MOCK_CAMPAIGNS.items[0],
            id: 'new-campaign-id',
            title: 'New Campaign',
          }),
        });
      }
      if (route.request().method() === 'DELETE') {
        return route.fulfill({ status: 204 });
      }
      return route.fulfill({ status: 200 });
    });

    await page.goto('/campaigns');
    await page.waitForLoadState('networkidle');
  });

  test('displays page header with title', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    const heading = page.locator('h1').filter({ hasText: /campagne|campaign|kampagne/i });
    await expect(heading).toBeVisible();
  });

  test('displays campaign cards', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    await expect(page.getByText('Campagne diagnostic amiante 2026')).toBeVisible();
    await expect(page.getByText('Maintenance préventive Q2')).toBeVisible();
  });

  test('shows campaign status badges', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    // Active and Draft statuses should be visible
    const statusBadges = page.locator('span').filter({ hasText: /active|activ|brouillon|draft|entwurf/i });
    const count = await statusBadges.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('shows progress bars', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    // Progress text "2/5" should be visible for the first campaign
    await expect(page.getByText('2/5')).toBeVisible();
  });

  test('shows create button for admin', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    const createButton = page.getByRole('button', {
      name: /nouvelle campagne|new campaign|neue kampagne/i,
    });
    await expect(createButton).toBeVisible();
  });

  test('opens campaign detail on click', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    await page.getByText('Campagne diagnostic amiante 2026').click();

    // Detail modal should appear — look for budget info within the modal overlay
    const modal = page.locator('.fixed.inset-0.z-50');
    await expect(modal).toBeVisible();
    await expect(modal.getByText(/75/)).toBeVisible();
  });

  test('filter by status works', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    const statusSelect = page.locator('select').first();
    await statusSelect.selectOption('active');
    // Should trigger a re-fetch (mocked, so same data appears)
    await expect(page.getByText('Campagne diagnostic amiante 2026')).toBeVisible();
  });

  test('filter by type works', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    const selects = page.locator('select');
    const typeSelect = selects.nth(1);
    await typeSelect.selectOption('diagnostic');
    await expect(page.getByText('Campagne diagnostic amiante 2026')).toBeVisible();
  });

  test('create modal opens and has form fields', async ({ page }) => {
    await page.waitForSelector('h1', { timeout: 10000 });
    const createButton = page.getByRole('button', {
      name: /nouvelle campagne|new campaign|neue kampagne/i,
    });
    await createButton.click();

    // Modal should be visible with form elements
    const nameInput = page.locator('input[type="text"]');
    await expect(nameInput).toBeVisible();
    const textarea = page.locator('textarea');
    await expect(textarea).toBeVisible();
  });

  test('displays empty state when no campaigns', async ({ page }) => {
    // Override with empty response
    await page.route('**/api/v1/campaigns*', (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ items: [], total: 0, page: 1, size: 50, pages: 0 }),
      }),
    );
    await page.goto('/campaigns');
    await page.waitForLoadState('networkidle');
    await page.waitForSelector('h1', { timeout: 10000 });

    const emptyText = page.getByText(
      /aucune campagne|no campaigns|keine kampagnen|nessuna campagna/i,
    );
    await expect(emptyText).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});
