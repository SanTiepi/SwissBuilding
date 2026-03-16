import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Admin Audit Logs Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/admin/audit-logs');
    await page.waitForLoadState('networkidle');
  });

  test('displays audit log page header', async ({ page }) => {
    const header = page.locator('h1').filter({ hasText: /audit|journal/i });
    await expect(header.first()).toBeVisible();
  });

  test('renders audit log table rows', async ({ page }) => {
    // Should show both mock entries in table cells
    await expect(page.getByRole('cell', { name: 'Admin Test' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'Jean Muller' })).toBeVisible();
  });

  test('shows action badges in table', async ({ page }) => {
    const table = page.locator('table');
    await expect(table.getByText('create')).toBeVisible();
    await expect(table.getByText('update')).toBeVisible();
  });

  test('shows entity types in table', async ({ page }) => {
    await expect(page.getByRole('cell', { name: 'building' })).toBeVisible();
    await expect(page.getByRole('cell', { name: 'diagnostic' })).toBeVisible();
  });

  test('has filter dropdowns', async ({ page }) => {
    const entityFilter = page.locator('select').filter({ hasText: /entity|entite/i });
    await expect(entityFilter.first()).toBeVisible();

    const actionFilter = page.locator('select').filter({ hasText: /action/i });
    await expect(actionFilter.first()).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });

  test('expanding row shows details JSON', async ({ page }) => {
    // Click the table cell with "Admin Test" to expand the row
    await page.getByRole('cell', { name: 'Admin Test' }).click();
    // Should show the details JSON
    await expect(page.getByText('Rue de Bourg 1')).toBeVisible();
  });
});
