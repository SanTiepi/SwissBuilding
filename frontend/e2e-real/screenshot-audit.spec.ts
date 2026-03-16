import { test, expect } from '@playwright/test';
import {
  getFirstBuildingId,
  getFirstDiagnosticTarget,
} from './helpers';

const DESKTOP = { width: 1280, height: 720 };
const MOBILE = { width: 390, height: 844 };

interface PageDef {
  name: string;
  path: string | (() => Promise<string>);
}

test.describe('Screenshot audit — real backend', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  const staticPages: PageDef[] = [
    { name: 'dashboard', path: '/dashboard' },
    { name: 'buildings-list', path: '/buildings' },
    { name: 'documents', path: '/documents' },
    { name: 'settings', path: '/settings' },
    { name: 'risk-simulator', path: '/risk-simulator' },
    { name: 'map', path: '/map' },
  ];

  for (const viewport of [
    { label: 'desktop', size: DESKTOP },
    { label: 'mobile', size: MOBILE },
  ]) {
    for (const pageDef of staticPages) {
      test(`${pageDef.name} — ${viewport.label}`, async ({ page }) => {
        await page.setViewportSize(viewport.size);
        await page.goto(pageDef.path as string);
        await page.waitForTimeout(2000);
        await page.screenshot({
          path: `test-results/real-audit-${pageDef.name}-${viewport.label}.png`,
          fullPage: true,
        });
      });
    }

    test(`building-detail — ${viewport.label}`, async ({ page }) => {
      await page.setViewportSize(viewport.size);
      const buildingId = await getFirstBuildingId(page);
      if (!buildingId) {
        test.skip(true, 'No buildings');
        return;
      }
      await page.goto(`/buildings/${buildingId}`);
      await page.waitForTimeout(2000);
      await page.screenshot({
        path: `test-results/real-audit-building-detail-${viewport.label}.png`,
        fullPage: true,
      });
    });

    test(`diagnostic-detail — ${viewport.label}`, async ({ page }) => {
      await page.setViewportSize(viewport.size);
      const target = await getFirstDiagnosticTarget(page);
      if (!target) {
        test.skip(true, 'No diagnostics');
        return;
      }
      await page.goto(`/diagnostics/${target.diagnosticId}`);
      await page.waitForTimeout(2000);
      await page.screenshot({
        path: `test-results/real-audit-diagnostic-detail-${viewport.label}.png`,
        fullPage: true,
      });
    });
  }
});
