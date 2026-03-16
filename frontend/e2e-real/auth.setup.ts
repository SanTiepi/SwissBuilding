import fs from 'node:fs/promises';
import path from 'node:path';
import { test as setup } from '@playwright/test';

import { AUTH_FILE } from './auth';
import { loginViaUI } from './helpers';

setup('authenticate admin session', async ({ page }) => {
  await fs.mkdir(path.dirname(AUTH_FILE), { recursive: true });
  await loginViaUI(page);
  await page.context().storageState({ path: AUTH_FILE });
});
