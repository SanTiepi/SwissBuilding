import { defineConfig, devices } from '@playwright/test';
import { AUTH_FILE } from './e2e-real/auth';

/**
 * Playwright config for real backend e2e tests.
 *
 * Requires a running backend (port 8000) with seeded data.
 * Uses a dedicated Vite dev server on port 4000 (avoids collision with
 * a manually started `npm run dev` on port 3000).
 * The Vite proxy forwards /api to localhost:8000.
 *
 * Usage: npm run test:e2e:real
 */
export default defineConfig({
  testDir: './e2e-real',
  timeout: 60_000,
  retries: 1,
  use: {
    baseURL: 'http://localhost:4000',
    headless: true,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure',
  },
  webServer: {
    command: 'npx vite --port 4000',
    port: 4000,
    reuseExistingServer: false,
    timeout: 30_000,
  },
  projects: [
    {
      name: 'setup',
      testMatch: /auth\.setup\.ts/,
    },
    {
      name: 'desktop-chromium',
      use: {
        ...devices['Desktop Chrome'],
        storageState: AUTH_FILE,
      },
      dependencies: ['setup'],
    },
    {
      name: 'mobile-chrome',
      use: {
        ...devices['Pixel 5'],
        storageState: AUTH_FILE,
      },
      dependencies: ['setup'],
    },
  ],
});
