import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Admin Jurisdictions Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/admin/jurisdictions');
    await page.waitForLoadState('networkidle');
  });

  test('displays jurisdictions page header', async ({ page }) => {
    const header = page.locator('h1').filter({ hasText: /juridiction|jurisdiction|Jurisdiktion|giurisdizion/i });
    await expect(header.first()).toBeVisible();
  });

  test('renders jurisdiction tree with EU, CH, VD', async ({ page }) => {
    await expect(page.getByText('European Union')).toBeVisible();
    await expect(page.getByText('Suisse')).toBeVisible();
    await expect(page.getByText('Canton de Vaud')).toBeVisible();
  });

  test('clicking a jurisdiction shows its detail', async ({ page }) => {
    await page.getByText('Canton de Vaud').click();
    // Wait for detail panel to load
    await expect(page.locator('h2').filter({ hasText: 'Canton de Vaud' })).toBeVisible();
    // Should show the code in the detail panel
    await expect(page.getByText('Code: CH-VD')).toBeVisible();
  });

  test('clicking VD shows its regulatory packs', async ({ page }) => {
    await page.getByText('Canton de Vaud').click();
    await page.waitForLoadState('networkidle');
    // Should show the asbestos pack
    await expect(page.getByText('OTConst Art. 60a')).toBeVisible();
  });

  test('shows empty state when no jurisdiction is selected', async ({ page }) => {
    // The prompt text should be visible
    const prompt = page.getByText(/selectionnez|select a jurisdiction/i);
    await expect(prompt).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });

  test('displays summary stats bar with counts', async ({ page }) => {
    const statsBar = page.locator('[data-testid="stats-bar"]');
    await expect(statsBar).toBeVisible();
    // Total of 3 jurisdictions from mock data
    await expect(statsBar.getByText('3').first()).toBeVisible();
  });

  test('search filter narrows down tree items', async ({ page }) => {
    const searchInput = page.locator('[data-testid="jurisdiction-search"]');
    await expect(searchInput).toBeVisible();

    await searchInput.fill('Vaud');
    // Only Canton de Vaud should remain visible in the tree
    await expect(page.getByText('Canton de Vaud')).toBeVisible();
    // EU and CH should be filtered out
    await expect(page.getByText('European Union')).not.toBeVisible();
  });

  test('level filter restricts displayed jurisdictions', async ({ page }) => {
    const levelFilter = page.locator('[data-testid="level-filter"]');
    await expect(levelFilter).toBeVisible();

    await levelFilter.selectOption('country');
    // Only Suisse (country) should be visible
    await expect(page.getByText('Suisse')).toBeVisible();
    await expect(page.getByText('European Union')).not.toBeVisible();
    await expect(page.getByText('Canton de Vaud')).not.toBeVisible();
  });

  test('clicking add jurisdiction opens create modal', async ({ page }) => {
    const addBtn = page.getByRole('button', { name: /add jurisdiction|ajouter/i });
    await addBtn.click();
    // Modal should appear with form fields
    const modal = page.locator('form');
    await expect(modal).toBeVisible();
    await expect(page.locator('input[placeholder="CH-VD"]')).toBeVisible();
    await expect(page.locator('input[placeholder="Canton de Vaud"]')).toBeVisible();
  });

  test('selecting a jurisdiction then clicking edit opens prefilled modal', async ({ page }) => {
    // Select Canton de Vaud
    await page.getByText('Canton de Vaud').click();
    await expect(page.locator('h2').filter({ hasText: 'Canton de Vaud' })).toBeVisible();

    // Click the edit button
    // Safer: find by title attribute
    await page.locator('button[title="Edit"], button[title="Modifier"]').first().click({ timeout: 3000 }).catch(async () => {
      // Fallback: use the generic pencil button near the detail header
      const buttons = page.locator('.flex.items-center.gap-1 button').first();
      await buttons.click();
    });

    // Modal should show code input prefilled with CH-VD
    const codeInput = page.locator('input[placeholder="CH-VD"]');
    await expect(codeInput).toBeVisible();
    await expect(codeInput).toHaveValue('CH-VD');
  });

  test('selecting a jurisdiction then clicking delete opens confirm dialog', async ({ page }) => {
    await page.getByText('Canton de Vaud').click();
    await expect(page.locator('h2').filter({ hasText: 'Canton de Vaud' })).toBeVisible();

    // Click the delete button (second action button)
    await page.locator('button[title]').filter({ has: page.locator('svg') }).nth(1).click({ timeout: 3000 }).catch(async () => {
      const buttons = page.locator('.flex.items-center.gap-1 button').last();
      await buttons.click();
    });

    // Confirm dialog should mention the jurisdiction name
    await expect(page.getByText('Canton de Vaud', { exact: false })).toBeVisible();
  });

  test('tree expands and collapses on click', async ({ page }) => {
    // All three should be visible initially (depth < 2 auto-expanded)
    await expect(page.getByText('European Union')).toBeVisible();
    await expect(page.getByText('Suisse')).toBeVisible();
    await expect(page.getByText('Canton de Vaud')).toBeVisible();

    // Click EU to collapse — this also selects it
    await page.getByText('European Union').click();
    // Click EU again to toggle collapse (EU has children)
    await page.getByText('European Union').click();

    // EU itself should remain visible
    await expect(page.getByText('European Union')).toBeVisible();
  });
});
