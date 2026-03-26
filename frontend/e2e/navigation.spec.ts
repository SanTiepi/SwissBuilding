import { test, expect } from '@playwright/test';
import { mockAuthState, mockApiRoutes } from './helpers';

test.describe('Navigation & Layout', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page, 'admin');
    await mockApiRoutes(page);
  });

  test('sidebar displays all navigation items for admin', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // All nav items should be visible
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();

    // Check nav links exist in sidebar
    await expect(sidebar.locator('a[href="/dashboard"]')).toBeVisible();
    await expect(sidebar.locator('a[href="/buildings"]')).toBeVisible();
    await expect(sidebar.locator('a[href="/map"]')).toBeVisible();
    await expect(sidebar.locator('a[href="/risk-simulator"]')).toBeVisible();
    await expect(sidebar.locator('a[href="/documents"]')).toBeVisible();
    await expect(sidebar.locator('a[href="/settings"]')).toBeVisible();
  });

  test('navigating through all pages works without errors', async ({ page }) => {
    const routes = [
      '/dashboard',
      '/buildings',
      '/map',
      '/risk-simulator',
      '/documents',
      '/settings',
    ];

    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState('networkidle');

      // No error boundary should be shown
      const errorBoundary = page.getByText('An error occurred');
      await expect(errorBoundary).not.toBeVisible();

      // No blank page - some content should exist
      const mainContent = page.locator('main, [role="main"], .min-h-screen');
      await expect(mainContent.first()).toBeVisible();
    }
  });

  test('dashboard link is active when on dashboard', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const dashboardLink = page.locator('a[href="/dashboard"]');
    const classes = await dashboardLink.getAttribute('class');
    expect(classes).toMatch(/bg-red-600/);
  });

  test('buildings link is active when on buildings page', async ({ page }) => {
    await page.goto('/buildings');
    await page.waitForLoadState('networkidle');

    const buildingsLink = page.locator('a[href="/buildings"]');
    const classes = await buildingsLink.getAttribute('class');
    expect(classes).toMatch(/bg-red-600/);
  });

  test('sidebar collapse toggle works', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Find the collapse button (ChevronLeft/ChevronRight)
    const collapseBtn = page.locator('aside button[aria-label]').last();
    if (await collapseBtn.isVisible()) {
      await collapseBtn.click();

      // After collapse, sidebar should be narrower (w-16)
      const aside = page.locator('aside');
      const classes = await aside.getAttribute('class');
      expect(classes).toContain('w-16');

      // Click again to expand
      await collapseBtn.click();
      const expandedClasses = await aside.getAttribute('class');
      expect(expandedClasses).toContain('w-64');
    }
  });

  test('SwissBuildingOS logo/brand is visible', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText('SwissBuildingOS').first()).toBeVisible();
  });

  test('header shows user info', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // The header should show user name or email
    const header = page.locator('header');
    if (await header.isVisible()) {
      const headerText = await header.textContent();
      expect(headerText).toBeTruthy();
    }
  });

  test('root URL redirects to dashboard', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/dashboard/);
  });
});

test.describe('Navigation for non-admin roles', () => {
  test('owner cannot see risk simulator link', async ({ page }) => {
    await mockAuthState(page, 'owner');
    await mockApiRoutes(page);
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Risk simulator should be hidden for owner role
    await expect(page.locator('a[href="/risk-simulator"]')).not.toBeVisible();
  });

  test('contractor cannot see risk simulator link', async ({ page }) => {
    await mockAuthState(page, 'contractor');
    await mockApiRoutes(page);
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('a[href="/risk-simulator"]')).not.toBeVisible();
  });

  test('diagnostician can see risk simulator link', async ({ page }) => {
    await mockAuthState(page, 'diagnostician');
    await mockApiRoutes(page);
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('a[href="/risk-simulator"]')).toBeVisible();
  });
});

test.describe('Keyboard & Focus', () => {
  test.beforeEach(async ({ page }) => {
    await mockAuthState(page, 'admin');
    await mockApiRoutes(page);
  });

  test('skip-to-content link is first focusable and targets #main-content', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // First Tab should focus the skip link
    await page.keyboard.press('Tab');
    const skipLink = page.locator('a[href="#main-content"]');
    const isFocused = await skipLink.evaluate((el) => el === document.activeElement);
    expect(isFocused).toBe(true);

    // Skip link should be visible when focused (focus-visible)
    await expect(skipLink).toBeVisible();

    // Main element should have the target id
    const mainEl = page.locator('main#main-content');
    await expect(mainEl).toBeVisible();
  });

  test('Tab navigates through header controls in order', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Focus the first header interactive element by pressing Tab from body
    await page.keyboard.press('Tab');

    // Collect focused elements as we Tab through header + sidebar
    const focusedTags: string[] = [];
    for (let i = 0; i < 20; i++) {
      const tag = await page.evaluate(() => {
        const el = document.activeElement;
        return el ? `${el.tagName.toLowerCase()}:${el.getAttribute('aria-label') || el.textContent?.trim().slice(0, 30) || ''}` : 'none';
      });
      focusedTags.push(tag);
      await page.keyboard.press('Tab');
    }

    // Should reach interactive elements (buttons or links) via Tab
    const interactiveCount = focusedTags.filter(
      (t) => t.startsWith('button:') || t.startsWith('a:'),
    ).length;
    expect(interactiveCount).toBeGreaterThanOrEqual(2);
  });

  test('Ctrl+K opens command palette and Escape closes it', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Open command palette with Ctrl+K
    await page.keyboard.press('Control+k');

    // Palette dialog should appear
    const palette = page.locator('[role="dialog"]');
    await expect(palette.first()).toBeVisible({ timeout: 3000 });

    // Input should be focused
    const focusedTag = await page.evaluate(() => document.activeElement?.tagName.toLowerCase());
    expect(focusedTag).toBe('input');

    // Escape closes the palette
    await page.keyboard.press('Escape');
    await expect(palette.first()).not.toBeVisible();
  });

  test('command palette keeps arrow navigation within input', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Open command palette
    await page.keyboard.press('Control+k');
    const palette = page.locator('[role="dialog"]');
    await expect(palette.first()).toBeVisible({ timeout: 3000 });

    // Type a search query
    await page.keyboard.type('test');

    // Wait for debounced search
    await page.waitForTimeout(400);

    // Arrow down should not move focus out of input (custom handler prevents it)
    await page.keyboard.press('ArrowDown');
    const stillInput = await page.evaluate(() => document.activeElement?.tagName.toLowerCase());
    expect(stillInput).toBe('input');
  });

  test('command palette dialog has aria-modal attribute', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await page.keyboard.press('Control+k');
    const dialog = page.locator('[role="dialog"]');
    await expect(dialog.first()).toBeVisible({ timeout: 3000 });

    const ariaModal = await dialog.first().getAttribute('aria-modal');
    expect(ariaModal).toBe('true');

    await page.keyboard.press('Escape');
  });

  test('command palette restores focus to trigger element on close', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Focus a known element first (e.g., a sidebar link)
    const sidebarLink = page.locator('aside nav a').first();
    await sidebarLink.focus();
    const beforeTag = await page.evaluate(() => document.activeElement?.tagName.toLowerCase());
    expect(beforeTag).toBe('a');

    // Open palette via Ctrl+K (which saves focus)
    await page.keyboard.press('Control+k');
    const palette = page.locator('[role="dialog"]');
    await expect(palette.first()).toBeVisible({ timeout: 3000 });

    // Close with Escape
    await page.keyboard.press('Escape');
    await expect(palette.first()).not.toBeVisible();

    // Focus should be restored to the sidebar link
    await page.waitForTimeout(100); // allow rAF to fire
    const afterTag = await page.evaluate(() => document.activeElement?.tagName.toLowerCase());
    expect(afterTag).toBe('a');
  });

  test('sidebar nav links are keyboard-focusable', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Focus sidebar by tabbing to it — sidebar links are <a> elements
    const sidebarLinks = page.locator('aside nav a');
    const count = await sidebarLinks.count();
    expect(count).toBeGreaterThan(0);

    // First sidebar link should be focusable
    await sidebarLinks.first().focus();
    const focused = await page.evaluate(() => document.activeElement?.tagName.toLowerCase());
    expect(focused).toBe('a');
  });

  test('sidebar collapse button has accessible label', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const collapseBtn = page.locator('aside button[aria-label]').last();
    if (await collapseBtn.isVisible()) {
      const label = await collapseBtn.getAttribute('aria-label');
      expect(label).toBeTruthy();
      expect(label).toMatch(/collapse|expand|sidebar/i);
    }
  });

  test('command palette close button is present with aria-label', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await page.keyboard.press('Control+k');
    const palette = page.locator('[role="dialog"]');
    await expect(palette.first()).toBeVisible({ timeout: 3000 });

    // Close button should exist with proper label
    const closeBtn = palette.locator('button[aria-label]').first();
    await expect(closeBtn).toBeVisible();
    const label = await closeBtn.getAttribute('aria-label');
    expect(label).toBeTruthy();
  });

  test('header language dropdown has aria-expanded', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Find language button by aria-haspopup
    const langButton = page.locator('header button[aria-haspopup="true"]').first();
    await expect(langButton).toBeVisible();

    // Initially collapsed
    const expanded = await langButton.getAttribute('aria-expanded');
    expect(expanded).toBe('false');

    // Click to open
    await langButton.click();
    const expandedAfter = await langButton.getAttribute('aria-expanded');
    expect(expandedAfter).toBe('true');
  });

  test('Escape closes user menu dropdown', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Open user menu (last button with aria-expanded + aria-haspopup)
    const userButton = page.locator('header button[aria-haspopup="true"][aria-expanded]').last();
    await userButton.click();
    await expect(userButton).toHaveAttribute('aria-expanded', 'true');

    // Verify menu is visible with menuitem roles
    const menuItems = page.locator('header [role="menuitem"]');
    const count = await menuItems.count();
    expect(count).toBeGreaterThanOrEqual(2);

    // Press Escape to close
    await page.keyboard.press('Escape');
    await expect(userButton).toHaveAttribute('aria-expanded', 'false');
  });

  test('sidebar nav has aria-label landmark', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const nav = page.locator('aside nav[aria-label]');
    await expect(nav).toBeVisible();
    const label = await nav.getAttribute('aria-label');
    expect(label).toBeTruthy();
  });
});

test.describe('Mobile navigation', () => {
  test.beforeEach(async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await mockAuthState(page, 'admin');
    await mockApiRoutes(page);
  });

  test('sidebar is hidden by default on mobile', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Sidebar should not be visible at mobile width
    const sidebar = page.locator('aside');
    await expect(sidebar).not.toBeVisible();

    // Hamburger menu button should be visible
    const menuButton = page.locator('button[aria-label="Menu"]');
    await expect(menuButton).toBeVisible();
  });

  test('hamburger opens sidebar overlay on mobile', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Open sidebar via hamburger
    const menuButton = page.locator('button[aria-label="Menu"]');
    await menuButton.click();

    // Sidebar should now be visible
    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();

    // Backdrop should be visible
    const backdrop = page.locator('[aria-hidden="true"][class*="fixed inset-0"]');
    await expect(backdrop).toBeVisible();

    // Navigation links should be accessible
    await expect(sidebar.locator('a[href="/dashboard"]')).toBeVisible();
    await expect(sidebar.locator('a[href="/buildings"]')).toBeVisible();
  });

  test('clicking nav link closes sidebar on mobile', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Open sidebar
    const menuButton = page.locator('button[aria-label="Menu"]');
    await menuButton.click();

    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();

    // Click buildings link
    await sidebar.locator('a[href="/buildings"]').click();
    await page.waitForLoadState('networkidle');

    // Sidebar should close after navigation
    await expect(sidebar).not.toBeVisible();

    // Should be on buildings page
    await expect(page).toHaveURL(/\/buildings/);
  });

  test('backdrop click closes sidebar on mobile', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Open sidebar
    const menuButton = page.locator('button[aria-label="Menu"]');
    await menuButton.click();

    const sidebar = page.locator('aside');
    await expect(sidebar).toBeVisible();

    // Click backdrop to close — use force:true because sidebar links may overlap
    const backdrop = page.locator('[aria-hidden="true"][class*="fixed inset-0"]');
    await backdrop.click({ force: true });

    // Sidebar should close
    await expect(sidebar).not.toBeVisible();
  });

  test('mobile search button is visible and opens command palette', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // Desktop search bar should be hidden at 375px
    const desktopSearch = page.locator('header button:has(kbd)');
    await expect(desktopSearch).not.toBeVisible();

    // Mobile search icon button should be visible
    const searchButton = page.locator('header button.sm\\:hidden').first();
    await expect(searchButton).toBeVisible();

    // Touch target must be at least 44px
    const box = await searchButton.boundingBox();
    expect(box).toBeTruthy();
    expect(box!.width).toBeGreaterThanOrEqual(44);
    expect(box!.height).toBeGreaterThanOrEqual(44);

    // Clicking should open the command palette
    await searchButton.click();

    // Command palette dialog/overlay should appear
    const palette = page.locator('[role="dialog"], [data-testid="command-palette"]');
    await expect(palette.first()).toBeVisible({ timeout: 3000 });
  });

  test('page transitions work on mobile viewport', async ({ page }) => {
    const routes = ['/dashboard', '/buildings', '/documents', '/settings'];

    for (const route of routes) {
      await page.goto(route);
      await page.waitForLoadState('networkidle');

      // No error boundary
      await expect(page.getByText('An error occurred')).not.toBeVisible();

      // Main content should be visible
      const mainContent = page.locator('main, [role="main"], .min-h-screen');
      await expect(mainContent.first()).toBeVisible();
    }
  });
});
