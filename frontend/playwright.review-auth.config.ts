import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: 'ui-review-authenticated.spec.ts',
  timeout: 60000,
  retries: 0,
  workers: 1, // Sequential — shared auth context
  reporter: [['list'], ['html', { outputFolder: 'test-results/ui-review-auth-report' }]],
  use: {
    baseURL: process.env.REVIEW_URL || 'http://194.93.48.163:8080',
    headless: true,
    screenshot: 'on',
    trace: 'retain-on-failure',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
  ],
});
