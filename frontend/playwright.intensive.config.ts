import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: 'staging-intensive.spec.ts',
  timeout: 30000,
  retries: 0,
  outputDir: 'test-results/intensive-output',
  reporter: [['list'], ['html', { outputFolder: 'test-results/intensive-report' }]],
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
    { name: 'desktop', use: { browserName: 'chromium', viewport: { width: 1440, height: 900 } } },
  ],
});
