import { test, expect } from '@playwright/test';

test('find building detail crash source', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (error) => {
    errors.push(`${error.message}\n${error.stack}`);
  });

  // Login
  await page.goto('/login');
  await page.fill('input[name="email"]', 'admin@swissbuildingos.ch');
  await page.fill('input[name="password"]', 'noob42');
  await page.click('button[type="submit"]');
  await page.waitForURL('**/dashboard', { timeout: 15000 });

  // Go to building detail
  await page.goto('/buildings/c8f3dda1-f304-4d1c-a4d4-6e49c68a7f28');
  await page.waitForTimeout(10000); // Wait for all lazy components to load

  // Print all errors
  for (const e of errors) {
    console.log('PAGE ERROR:', e);
  }

  expect(errors).toHaveLength(0);
});
