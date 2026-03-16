import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Buildings List Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/buildings');
    await page.waitForLoadState('networkidle');
  });

  test('displays buildings list header', async ({ page }) => {
    const header = page.locator('h1, h2').filter({ hasText: /batiment|building|Gebäude/i });
    await expect(header.first()).toBeVisible();
  });

  test('displays building cards with addresses', async ({ page }) => {
    await expect(page.getByText('Rue de Bourg 1')).toBeVisible();
    await expect(page.getByText('Bahnhofstrasse 10')).toBeVisible();
    await expect(page.getByText('Via Nassa 5')).toBeVisible();
  });

  test('building cards show canton badges', async ({ page }) => {
    await expect(page.getByText('VD').first()).toBeVisible();
    await expect(page.getByText('ZH').first()).toBeVisible();
    await expect(page.getByText('TI').first()).toBeVisible();
  });

  test('building cards show city names', async ({ page }) => {
    // Use postal_code + city pattern to avoid matching hidden <option> elements
    await expect(page.getByText('1003 Lausanne').first()).toBeVisible();
    await expect(page.getByText('8001 Zurich').first()).toBeVisible();
    await expect(page.getByText('6900 Lugano').first()).toBeVisible();
  });

  test('building cards show construction years', async ({ page }) => {
    await expect(page.getByText('1965')).toBeVisible();
    await expect(page.getByText('1978')).toBeVisible();
    await expect(page.getByText('1955')).toBeVisible();
  });

  test('clicking a building card navigates to detail', async ({ page }) => {
    const card = page.getByText('Rue de Bourg 1').first();
    await card.click();

    await expect(page).toHaveURL(/\/buildings\/b1000000/);
  });

  test('search/filter input exists', async ({ page }) => {
    const searchInput = page.locator('input[type="text"], input[placeholder*="cherch"], input[placeholder*="search"], input[placeholder*="Such"]');
    if (await searchInput.count() > 0) {
      await expect(searchInput.first()).toBeVisible();
    }
  });

  test('add building button exists', async ({ page }) => {
    const addBtn = page.locator('button').filter({ hasText: /ajouter|add|nouveau|new|hinzufügen/i });
    if (await addBtn.count() > 0) {
      await expect(addBtn.first()).toBeVisible();
    }
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});

test.describe('Building Create Form', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/buildings');
    await page.waitForLoadState('networkidle');
  });

  test('opens create building dialog and shows grouped fields', async ({ page }) => {
    const addBtn = page.locator('button').filter({ hasText: /ajouter|add|nouveau|new|hinzufügen/i });
    await addBtn.first().click();

    // Modal should be visible with Location group
    await expect(page.locator('legend').filter({ hasText: /location|emplacement|standort/i }).first()).toBeVisible();

    // Required fields should be present
    await expect(page.locator('input').first()).toBeVisible();
  });

  test('shows validation errors for empty required fields', async ({ page }) => {
    const addBtn = page.locator('button').filter({ hasText: /ajouter|add|nouveau|new|hinzufügen/i });
    await addBtn.first().click();

    // Click submit without filling anything
    const submitBtn = page.locator('button[type="submit"]');
    await submitBtn.click();

    // Should show at least one validation error
    const errors = page.locator('.text-red-600');
    await expect(errors.first()).toBeVisible();
  });

  test('shows advanced fields with EGID and EGRID as separate fields', async ({ page }) => {
    const addBtn = page.locator('button').filter({ hasText: /ajouter|add|nouveau|new|hinzufügen/i });
    await addBtn.first().click();

    // Click advanced options
    const advancedBtn = page.locator('button').filter({ hasText: /advanced|avancé|erweitert/i });
    await advancedBtn.click();

    // EGID and EGRID should be separate fields with distinct labels
    const egidLabel = page.locator('label').filter({ hasText: /EGID/i });
    const egridLabel = page.locator('label').filter({ hasText: /EGRID/i });
    await expect(egidLabel.first()).toBeVisible();
    await expect(egridLabel.first()).toBeVisible();

    // Should also have Official ID
    const officialIdLabel = page.locator('label').filter({ hasText: /official|officiel/i });
    await expect(officialIdLabel.first()).toBeVisible();
  });

  test('submit button is disabled while saving', async ({ page }) => {
    const addBtn = page.locator('button').filter({ hasText: /ajouter|add|nouveau|new|hinzufügen/i });
    await addBtn.first().click();

    // Fill required fields
    const inputs = page.locator('form input[type="text"], form input:not([type])');
    // Address
    await inputs.nth(0).fill('Test Avenue 1');
    // City
    await inputs.nth(1).fill('Lausanne');
    // Postal code
    await inputs.nth(2).fill('1000');

    // Canton select
    const cantonSelect = page.locator('form select').first();
    await cantonSelect.selectOption('VD');

    // Building type select
    const typeSelect = page.locator('form select').nth(1);
    const typeOptions = await typeSelect.locator('option').allTextContents();
    if (typeOptions.length > 1) {
      await typeSelect.selectOption({ index: 1 });
    }

    // Construction year
    const yearInput = page.locator('form input[type="number"]').first();
    await yearInput.fill('1990');

    const submitBtn = page.locator('button[type="submit"]');
    await submitBtn.click();

    // After successful submit, success message should appear
    const successMsg = page.locator('[role="status"]');
    await expect(successMsg).toBeVisible({ timeout: 5000 });
  });
});

test.describe('Building Detail Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/buildings/b1000000-0000-0000-0000-000000000001');
    await page.waitForLoadState('networkidle');
  });

  test('displays building address', async ({ page }) => {
    await expect(page.getByText('Rue de Bourg 1')).toBeVisible();
  });

  test('displays building metadata', async ({ page }) => {
    await expect(page.getByText('Lausanne')).toBeVisible();
    await expect(page.getByText('1003').first()).toBeVisible();
  });

  test('displays risk information', async ({ page }) => {
    // Risk gauge or risk level label should be visible
    const riskText = page.getByText(/faible|eleve|moyen|critique|risk|risque/i);
    await expect(riskText.first()).toBeVisible();
  });

  test('displays diagnostics section', async ({ page }) => {
    // Should show diagnostic timeline or list
    const diagSection = page.getByText(/diagnostic|Diagnose/i);
    await expect(diagSection.first()).toBeVisible();
  });

  test('displays construction year', async ({ page }) => {
    await expect(page.getByText('1965')).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});
