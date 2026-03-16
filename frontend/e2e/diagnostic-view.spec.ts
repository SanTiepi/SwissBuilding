import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Diagnostic View Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/diagnostics/d1000000-0000-0000-0000-000000000001');
    await page.waitForLoadState('networkidle');
  });

  test('diagnostic detail page loads', async ({ page }) => {
    // Should show the diagnostic type badge (asbestos)
    const pollutantBadge = page.getByText(/amiante|asbestos|Asbest|amianto/i);
    await expect(pollutantBadge.first()).toBeVisible();
  });

  test('status badge displays correctly', async ({ page }) => {
    // Status is 'completed' in mock data
    const statusBadge = page.getByText(/termine|completed|abgeschlossen|completato/i);
    await expect(statusBadge.first()).toBeVisible();
  });

  test('laboratory info is displayed', async ({ page }) => {
    await expect(page.getByText('LabSwiss AG')).toBeVisible();
  });

  test('sample table is rendered', async ({ page }) => {
    // Mock has one sample ECH-001
    await expect(page.getByText('ECH-001')).toBeVisible();
  });

  test('sample shows risk level badge', async ({ page }) => {
    // Sample has risk_level: 'high'
    const riskBadge = page.getByText(/eleve|high|hoch|elevato/i);
    await expect(riskBadge.first()).toBeVisible();
  });

  test('sample shows material description', async ({ page }) => {
    await expect(page.getByText('Fibre-ciment')).toBeVisible();
  });

  test('sample shows location detail', async ({ page }) => {
    await expect(page.getByText(/Joint de facade/)).toBeVisible();
  });

  test('validate button is visible for admin', async ({ page }) => {
    const validateBtn = page.locator('button').filter({ hasText: /valider|validate|validieren|validare/i });
    await expect(validateBtn.first()).toBeVisible();
  });

  test('add sample button is visible for admin', async ({ page }) => {
    const addBtn = page.locator('button').filter({ hasText: /ajouter|add|hinzufügen|aggiungere/i });
    await expect(addBtn.first()).toBeVisible();
  });

  test('back link navigates to building', async ({ page }) => {
    const backLink = page.locator('a[href*="/buildings/"]').first();
    await expect(backLink).toBeVisible();
  });

  test('SUVA notification section is displayed', async ({ page }) => {
    const suvaText = page.getByText(/SUVA/i);
    await expect(suvaText.first()).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});

test.describe('Diagnostic View - Role restrictions', () => {
  test('validate button hidden for owner role', async ({ page }) => {
    await mockAuthState(page, 'owner');
    await mockApiRoutes(page);
    await page.goto('/diagnostics/d1000000-0000-0000-0000-000000000001');
    await page.waitForLoadState('networkidle');

    // Validate button should not be visible for owners (RoleGate allows admin/authority)
    const validateBtn = page.locator('button').filter({ hasText: /valider|validate|validieren|validare/i });
    await expect(validateBtn).toHaveCount(0);
  });
});
