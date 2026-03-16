import { test, expect } from '@playwright/test';
import { mockApiRoutes } from './helpers';

test.describe('Login Page', () => {
  test.beforeEach(async ({ page }) => {
    await mockApiRoutes(page);
    await page.goto('/login');
  });

  test('displays all login page elements', async ({ page }) => {
    // App branding
    await expect(page.getByRole('heading', { name: 'SwissBuildingOS' })).toBeVisible();

    // Form fields
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();

    // Submit button (FR: "Se connecter")
    await expect(page.getByRole('button', { name: /connecter|sign in|anmelden|accedi/i })).toBeVisible();

    // Language selector
    await expect(page.getByRole('button', { name: 'FR' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'DE' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'IT' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'EN' })).toBeVisible();
  });

  test('shows validation errors for empty form submission', async ({ page }) => {
    const submitBtn = page.getByRole('button', { name: /connecter|sign in|anmelden|accedi/i });
    await submitBtn.click();

    // Should show validation errors
    await expect(page.locator('[role="alert"]')).toHaveCount(2);
  });

  test('email field has HTML5 validation for invalid email', async ({ page }) => {
    const emailInput = page.locator('#email');
    await emailInput.fill('not-an-email');
    // HTML5 email validation should mark the field as invalid
    const isValid = await emailInput.evaluate((el: HTMLInputElement) => el.validity.valid);
    expect(isValid).toBe(false);
  });

  test('shows validation error for short password', async ({ page }) => {
    await page.locator('#email').fill('test@example.com');
    await page.locator('#password').fill('12345');
    const submitBtn = page.getByRole('button', { name: /connecter|sign in|anmelden|accedi/i });
    await submitBtn.click();

    await expect(page.locator('[role="alert"]')).toBeVisible();
  });

  test('successful login redirects to dashboard', async ({ page }) => {
    await page.locator('#email').fill('admin@swissbuildingos.ch');
    await page.locator('#password').fill('admin123');

    const submitBtn = page.getByRole('button', { name: /connecter|sign in|anmelden|accedi/i });
    await submitBtn.click();

    await page.waitForURL('**/dashboard');
    await expect(page).toHaveURL(/\/dashboard/);
  });

  test('language switcher changes UI language', async ({ page }) => {
    // Default is FR
    await expect(page.getByRole('button', { name: /connecter/i })).toBeVisible();

    // Switch to EN
    await page.getByRole('button', { name: 'EN' }).click();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();

    // Switch to DE
    await page.getByRole('button', { name: 'DE' }).click();
    await expect(page.getByRole('button', { name: /anmelden|einloggen/i })).toBeVisible();
  });

  test('unauthenticated access redirects to login', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });

  test('email field has proper autocomplete', async ({ page }) => {
    const emailInput = page.locator('#email');
    await expect(emailInput).toHaveAttribute('type', 'email');
    await expect(emailInput).toHaveAttribute('autocomplete', 'email');
  });

  test('password field is masked', async ({ page }) => {
    const passwordInput = page.locator('#password');
    await expect(passwordInput).toHaveAttribute('type', 'password');
  });
});
