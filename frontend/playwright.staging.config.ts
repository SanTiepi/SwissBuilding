import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: 'staging-review.spec.ts',
  timeout: 30000,
  retries: 0,
  reporter: [['list'], ['html', { outputFolder: 'test-results/staging-review-report' }]],
  use: {
    baseURL: 'https://swissbuilding.batiscan.ch',
    headless: true,
    screenshot: 'on',
    trace: 'retain-on-failure',
    httpCredentials: {
      username: 'staging',
      password: 'staging2026',
    },
    ignoreHTTPSErrors: true,
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium', viewport: { width: 1440, height: 900 } } },
    { name: 'mobile', use: { browserName: 'chromium', viewport: { width: 390, height: 844 } } },
  ],
});
