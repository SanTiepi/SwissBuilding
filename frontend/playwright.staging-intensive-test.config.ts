import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  testMatch: 'staging-intensive-test.spec.ts',
  timeout: 60_000,
  retries: 0,
  workers: 1,
  outputDir: 'test-results/staging-intensive-test-output',
  reporter: [['list'], ['html', { outputFolder: 'test-results/staging-intensive-test-report' }]],
  use: {
    baseURL: 'https://swissbuilding.batiscan.ch',
    headless: true,
    screenshot: 'on',
    trace: 'retain-on-failure',
    httpCredentials: {
      username: 'baticonnect',
      password: 'aoJpFQeAT8CDam5ez3gL',
    },
    ignoreHTTPSErrors: true,
  },
  projects: [
    { name: 'desktop', use: { browserName: 'chromium', viewport: { width: 1440, height: 900 } } },
  ],
});
