import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Actions Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/actions');
    await page.waitForLoadState('networkidle');
  });

  test('actions page loads with header', async ({ page }) => {
    const header = page.locator('h1').filter({ hasText: /action|Aktion|azione/i });
    await expect(header.first()).toBeVisible();
  });

  test('action items are listed', async ({ page }) => {
    await expect(page.getByText('Desamiantage facade nord')).toBeVisible();
    await expect(page.getByText('Notification SUVA requise')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Diagnostic PCB recommande' })).toBeVisible();
  });

  test('priority badges display', async ({ page }) => {
    // Mock has high, critical, medium, low priorities - use rounded-full badge selector
    // Priority labels: Haute, Critique, Moyenne, Basse (FR)
    const badge = page.locator('span.rounded-full').filter({ hasText: /haute|high|hoch|alta|critique|critical|kritisch|critico/i }).first();
    await expect(badge).toBeVisible();
  });

  test('status badges display', async ({ page }) => {
    // Mock has open, in_progress, done statuses - use rounded-full badge (not <option>)
    // Status labels: Ouvert, En cours, Termine (FR)
    const badge = page.locator('span.rounded-full').filter({ hasText: /ouvert|open|offen|aperto|en cours|in progress/i }).first();
    await expect(badge).toBeVisible();
  });

  test('source type badges display', async ({ page }) => {
    // Mock has diagnostic, compliance, risk, manual source types - use rounded-full badge
    const badge = page.locator('span.rounded-full').filter({ hasText: /diagnostic|Diagnose|diagnostico/i }).first();
    await expect(badge).toBeVisible();
  });

  test('action descriptions show', async ({ page }) => {
    await expect(page.getByText('Retrait des joints amiantees de la facade nord')).toBeVisible();
  });

  test('status filter dropdown exists', async ({ page }) => {
    const statusFilter = page.locator('select').first();
    await expect(statusFilter).toBeVisible();
  });

  test('status filtering works', async ({ page }) => {
    // Override actions endpoint to return filtered results when status=open
    await page.route(/\/api\/v1\/actions\?.*status=open/, (route) =>
      route.fulfill({
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
        ]),
      }),
    );

    // Select "open" status from filter
    const statusSelect = page.locator('select').first();
    await statusSelect.selectOption({ index: 1 });
    await page.waitForLoadState('networkidle');

    // The filtered action should be visible
    await expect(page.getByText('Desamiantage facade nord')).toBeVisible();
  });

  test('create action button exists', async ({ page }) => {
    // FR: "Nouvelle action", EN: "New action", DE: "Neue Aktion"
    const createBtn = page.locator('button').filter({ hasText: /nouvelle|new|neue|nuov/i });
    await expect(createBtn.first()).toBeVisible();
  });

  test('mark done button exists on open actions', async ({ page }) => {
    // FR: "Marquer comme fait", EN: "Mark as done"
    const doneBtn = page.locator('button').filter({ hasText: /marquer|mark.*done|als erledigt|fatto/i });
    await expect(doneBtn.first()).toBeVisible();
  });

  test('empty state shows when no actions', async ({ page }) => {
    // Override actions to return empty
    await page.route(/\/api\/v1\/actions/, (route) =>
      route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([]),
      }),
    );

    await page.goto('/actions');
    await page.waitForLoadState('networkidle');

    const emptyText = page.getByText(/aucune|no action|all done|toutes|keine|nessun/i);
    await expect(emptyText.first()).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});
