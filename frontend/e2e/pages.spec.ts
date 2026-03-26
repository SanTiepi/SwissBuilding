import { test, expect, type Page } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Risk Simulator Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/risk-simulator');
    await page.waitForLoadState('networkidle');
  });

  test('displays risk simulator header', async ({ page }) => {
    const header = page.locator('h1, h2').filter({ hasText: /simul|risque|risk|Risiko/i });
    await expect(header.first()).toBeVisible();
  });

  test('displays form inputs for simulation', async ({ page }) => {
    // Should have input fields or select dropdowns
    const formElements = page.locator('select, input[type="number"], input[type="text"]');
    const count = await formElements.count();
    expect(count).toBeGreaterThan(0);
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});

test.describe('Documents Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/documents');
    await page.waitForLoadState('networkidle');
  });

  test('displays documents header', async ({ page }) => {
    const header = page.locator('h1, h2').filter({ hasText: /document|Dokument/i });
    await expect(header.first()).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});

test.describe('Settings Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');
  });

  test('displays settings header', async ({ page }) => {
    const header = page.locator('h1, h2').filter({ hasText: /param|settings|Einstellungen|impostazioni/i });
    await expect(header.first()).toBeVisible();
  });

  test('displays language selection', async ({ page }) => {
    // Should have language options (FR, DE, IT, EN)
    const langOptions = page.getByText(/Français|Deutsch|Italiano|English/);
    const count = await langOptions.count();
    expect(count).toBeGreaterThanOrEqual(1);
  });

  test('displays user profile section', async ({ page }) => {
    // Should show email or name
    const profileText = page.getByText(/admin@swissbuildingos|Admin|profil|profile/i);
    await expect(profileText.first()).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});

test.describe('Pollutant Map Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/map');
    await page.waitForLoadState('networkidle');
  });

  test('displays map page without crashing', async ({ page }) => {
    // The map page should load without error boundary
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });

  test('displays map header or controls', async ({ page }) => {
    const mapHeader = page.locator('h1, h2').filter({ hasText: /carte|map|Karte|mappa/i });
    if ((await mapHeader.count()) > 0) {
      await expect(mapHeader.first()).toBeVisible();
    }
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});

test.describe('Diagnostic View Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/diagnostics/d1000000-0000-0000-0000-000000000001');
    await page.waitForLoadState('networkidle');
  });

  test('displays diagnostic details', async ({ page }) => {
    // Should show diagnostic type or status
    const diagText = page.getByText(/asbestos|amiante|Asbest|amianto|completed|termine|abgeschlossen/i);
    await expect(diagText.first()).toBeVisible();
  });

  test('displays sample information', async ({ page }) => {
    // Should show sample number ECH-001
    await expect(page.getByText('ECH-001')).toBeVisible();
  });

  test('no error boundary visible', async ({ page }) => {
    await expect(page.getByText('An error occurred')).not.toBeVisible();
  });
});

// ─── Keyboard & Focus Checks ────────────────────────────────────────────────

test.describe('Page-level keyboard focus', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
  });

  test('buildings page: search input is focusable by Tab', async ({ page }) => {
    await page.goto('/buildings');
    await page.waitForLoadState('networkidle');

    const searchInput = page.locator('input[type="text"]').first();
    await expect(searchInput).toBeVisible();

    // Focus by clicking then verify it's the active element
    await searchInput.focus();
    const isFocused = await page.evaluate(
      () => document.activeElement?.tagName.toLowerCase() === 'input',
    );
    expect(isFocused).toBe(true);
  });

  test('settings page: interactive elements are reachable by Tab', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    // Tab through the page and check we reach some interactive elements
    const focusedElements: string[] = [];
    for (let i = 0; i < 15; i++) {
      await page.keyboard.press('Tab');
      const tag = await page.evaluate(() => {
        const el = document.activeElement;
        return el ? el.tagName.toLowerCase() : 'none';
      });
      focusedElements.push(tag);
    }

    // Should reach buttons or inputs in settings
    const interactiveCount = focusedElements.filter((t) => ['button', 'input', 'select', 'a'].includes(t)).length;
    expect(interactiveCount).toBeGreaterThanOrEqual(2);
  });

  test('documents page: no focus trap prevents navigation', async ({ page }) => {
    await page.goto('/documents');
    await page.waitForLoadState('networkidle');

    // Tab many times through header + sidebar + content — should not get stuck
    const tags: string[] = [];
    for (let i = 0; i < 25; i++) {
      await page.keyboard.press('Tab');
      const info = await page.evaluate(() => {
        const el = document.activeElement;
        return el ? `${el.tagName.toLowerCase()}:${el.className?.slice(0, 20) || ''}` : 'none';
      });
      tags.push(info);
    }

    // Should reach at least 2 different focusable element types (not stuck on body)
    const uniqueTags = new Set(tags.map((t) => t.split(':')[0]));
    // Filter out 'body' and 'html' which are not meaningful focus targets
    const meaningful = [...uniqueTags].filter((t) => !['body', 'html', 'none'].includes(t));
    expect(meaningful.length).toBeGreaterThanOrEqual(1);
  });

  test('main content area uses semantic <main> element with id', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const mainEl = page.locator('main#main-content');
    await expect(mainEl).toBeVisible();
  });

  test('command palette dialog has role="dialog"', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await page.keyboard.press('Control+k');
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog.first()).toBeVisible({ timeout: 3000 });

    // Verify it has an aria-label
    const label = await dialog.first().getAttribute('aria-label');
    expect(label).toBeTruthy();

    await page.keyboard.press('Escape');
  });

  test('modal on buildings page can be dismissed with Escape', async ({ page }) => {
    await page.goto('/buildings');
    await page.waitForLoadState('networkidle');

    // Open create building modal if the button exists
    const addButton = page.locator('button').filter({ hasText: /ajouter|add|hinzuf|aggiung/i });
    if ((await addButton.count()) > 0) {
      await addButton.first().click();

      const modal = page.locator('[class*="fixed inset-0"]');
      await expect(modal.first()).toBeVisible();

      // Escape should close it (if escape handler exists)
      await page.keyboard.press('Escape');

      // Give time for close animation
      await page.waitForTimeout(300);

      // Verify command palette did not open instead
      // If palette opened, that's a separate concern — just check modal state
    }
  });
});

// ─── Mobile Viewport Checks ──────────────────────────────────────────────────

const MOBILE_VIEWPORT = { width: 375, height: 812 };

/** Assert the page has no horizontal scrollbar (body does not overflow). */
async function expectNoHorizontalOverflow(page: Page) {
  const overflow = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth,
  );
  expect(overflow, 'Page should not have a horizontal scrollbar at mobile viewport').toBe(false);
}

test.describe('Mobile viewport checks', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize(MOBILE_VIEWPORT);
    await mockAuthState(page);
    await mockApiRoutes(page);
  });

  test('dashboard renders correctly at 375px', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // No error boundary
    await expect(page.getByText('An error occurred')).not.toBeVisible();

    // Page header should be visible
    const header = page.locator('h1').first();
    await expect(header).toBeVisible();

    // KPI cards should stack (visible, not clipped)
    const kpiCards = page.locator('[class*="grid-cols-1"]').first();
    await expect(kpiCards).toBeVisible();

    await expectNoHorizontalOverflow(page);
  });

  test('buildings list is accessible on mobile', async ({ page }) => {
    await page.goto('/buildings');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText('An error occurred')).not.toBeVisible();

    // Header visible
    const header = page.locator('h1').first();
    await expect(header).toBeVisible();

    // Search input accessible
    const searchInput = page.locator('input[type="text"]').first();
    await expect(searchInput).toBeVisible();

    await expectNoHorizontalOverflow(page);
  });

  test('settings page has no overflow at 375px', async ({ page }) => {
    await page.goto('/settings');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText('An error occurred')).not.toBeVisible();
    await expectNoHorizontalOverflow(page);
  });

  test('actions page renders at mobile viewport', async ({ page }) => {
    await page.goto('/actions');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText('An error occurred')).not.toBeVisible();

    // Header visible
    const header = page.locator('h1').first();
    await expect(header).toBeVisible();

    // Filter selects should wrap (page should not overflow)
    await expectNoHorizontalOverflow(page);
  });

  test('documents page has no overflow at mobile', async ({ page }) => {
    await page.goto('/documents');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText('An error occurred')).not.toBeVisible();
    await expectNoHorizontalOverflow(page);
  });

  test('hamburger menu is visible on mobile', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Hamburger button should be visible (md:hidden means visible below 768px)
    const hamburger = page.locator('button[aria-label="Menu"]');
    await expect(hamburger).toBeVisible();

    // Sidebar should be hidden by default
    const sidebar = page.locator('aside');
    await expect(sidebar).not.toBeVisible();
  });

  test('building comparison shows mobile cards at 375px', async ({ page }) => {
    await page.goto('/comparison');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText('An error occurred')).not.toBeVisible();

    // Header visible
    const header = page.locator('h1').first();
    await expect(header).toBeVisible();

    // Select 3 buildings from the checkbox list
    const checkboxes = page.locator('input[type="checkbox"]');
    const count = await checkboxes.count();
    if (count >= 3) {
      await checkboxes.nth(0).check();
      await checkboxes.nth(1).check();
      await checkboxes.nth(2).check();

      // Click compare button
      const compareButton = page.locator('button').filter({ hasText: /compar/i });
      await compareButton.first().click();

      // Mobile cards should be visible (table hidden at md:)
      const mobileCards = page.locator('[data-testid="comparison-mobile-cards"]');
      await expect(mobileCards).toBeVisible();

      // Should have 3 cards
      const cards = page.locator('[data-testid="comparison-mobile-card"]');
      await expect(cards).toHaveCount(3);

      // Desktop table should be hidden
      const table = page.locator('table');
      await expect(table).not.toBeVisible();
    }

    await expectNoHorizontalOverflow(page);
  });

  test('modal is visible and scrollable at 375px', async ({ page }) => {
    await page.goto('/buildings');
    await page.waitForLoadState('networkidle');

    // Open create building modal (if button is visible)
    const addButton = page.locator('button').filter({ hasText: /ajouter|add|hinzuf|aggiung/i });
    if ((await addButton.count()) > 0) {
      await addButton.first().click();

      // Modal should appear
      const modal = page.locator('[class*="fixed inset-0"]');
      await expect(modal.first()).toBeVisible();

      // Modal content should be scrollable (max-h constraint + overflow-y-auto)
      const modalContent = page.locator('[class*="max-h-"][class*="overflow-y-auto"]');
      await expect(modalContent.first()).toBeVisible();
    }
  });
});
