import { test } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

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
  await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(resolve)));
}

test.describe('UI Screenshot Audit', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page);
    await mockApiRoutes(page);
  });

  const pages = [
    { name: 'dashboard', url: '/dashboard' },
    { name: 'buildings-list', url: '/buildings' },
    { name: 'building-detail', url: '/buildings/b1000000-0000-0000-0000-000000000001' },
    { name: 'diagnostic-detail', url: '/diagnostics/d1000000-0000-0000-0000-000000000001' },
    { name: 'documents', url: '/documents' },
    { name: 'settings', url: '/settings' },
    { name: 'risk-simulator', url: '/risk-simulator' },
    { name: 'map', url: '/map' },
  ];

  for (const p of pages) {
    test(`screenshot ${p.name} desktop`, async ({ page }) => {
      await page.setViewportSize({ width: 1440, height: 900 });
      await page.goto(p.url);
      await waitForPageStable(page);
      await page.screenshot({
        path: `test-results/audit-${p.name}-desktop.png`,
        fullPage: true,
        animations: 'disabled',
      });
    });

    test(`screenshot ${p.name} mobile`, async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 812 });
      await page.goto(p.url);
      await waitForPageStable(page);
      await page.screenshot({
        path: `test-results/audit-${p.name}-mobile.png`,
        fullPage: true,
        animations: 'disabled',
      });
    });
  }
});
