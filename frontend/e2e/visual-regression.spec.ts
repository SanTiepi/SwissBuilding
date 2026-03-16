import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

const SCREENSHOT_OPTIONS = {
  maxDiffPixelRatio: 0.02,
  animations: 'disabled' as const,
};

// Inject CSS to disable all animations and transitions for deterministic screenshots
async function disableAnimations(page: import('@playwright/test').Page) {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
        caret-color: transparent !important;
      }
    `,
  });
}

// Wait until the page is fully stable for screenshotting
async function waitForPageStable(page: import('@playwright/test').Page) {
  await page.waitForLoadState('networkidle');
  await page.waitForLoadState('domcontentloaded');
  await disableAnimations(page);
  // Let the render cycle complete after disabling animations
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(resolve)));
}

test.describe('Visual Regression Tests', () => {
  test('login page', async ({ page }) => {
    await mockApiRoutes(page);
    await page.goto('/login');
    await waitForPageStable(page);
    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page).toHaveScreenshot('login.png', SCREENSHOT_OPTIONS);
  });

  test('dashboard page', async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/dashboard');
    await waitForPageStable(page);
    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page).toHaveScreenshot('dashboard.png', SCREENSHOT_OPTIONS);
  });

  test('buildings list page', async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/buildings');
    await waitForPageStable(page);
    await expect(page.locator('h1').first()).toBeVisible();
    await expect(page).toHaveScreenshot('buildings-list.png', SCREENSHOT_OPTIONS);
  });

  test('documents page', async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/documents');
    await waitForPageStable(page);
    const header = page.locator('h1, h2').filter({ hasText: /document|Dokument/i });
    await expect(header.first()).toBeVisible();
    await expect(page).toHaveScreenshot('documents.png', SCREENSHOT_OPTIONS);
  });

  test('settings page', async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/settings');
    await waitForPageStable(page);
    const header = page.locator('h1, h2').filter({ hasText: /param|settings|Einstellungen/i });
    await expect(header.first()).toBeVisible();
    await expect(page).toHaveScreenshot('settings.png', SCREENSHOT_OPTIONS);
  });

  test('risk simulator page', async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
    await page.goto('/risk-simulator');
    await waitForPageStable(page);
    const header = page.locator('h1, h2').filter({ hasText: /simul|risque|risk|Risiko/i });
    await expect(header.first()).toBeVisible();
    await expect(page).toHaveScreenshot('risk-simulator.png', SCREENSHOT_OPTIONS);
  });
});
