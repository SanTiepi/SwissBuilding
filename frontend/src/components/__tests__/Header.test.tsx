import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Header } from '../Header';

const mockLogout = vi.fn();

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    user: {
      id: 'u-001',
      email: 'admin@swissbuildingos.ch',
      first_name: 'Robin',
      last_name: 'Fragniere',
      role: 'admin',
      organization_id: null,
      language: 'fr',
      is_active: true,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    logout: mockLogout,
  }),
}));

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false, gcTime: 0 } },
});

function renderHeader(props: { onMenuToggle?: () => void; onSearchOpen?: () => void } = {}, route = '/dashboard') {
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
        <Header {...props} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('Header', () => {
  beforeEach(() => {
    mockLogout.mockClear();
  });

  it('renders the page title based on current route', () => {
    renderHeader({}, '/buildings');

    expect(screen.getByText('nav.buildings')).toBeInTheDocument();
  });

  it('displays user initials', () => {
    renderHeader();

    expect(screen.getByText('RF')).toBeInTheDocument();
  });

  it('displays user full name', () => {
    renderHeader();

    // User name appears in the header button
    expect(screen.getByText('Robin Fragniere')).toBeInTheDocument();
  });

  it('toggles language dropdown on click', async () => {
    const user = userEvent.setup();
    renderHeader();

    const langButton = screen.getByLabelText('settings.language');
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();

    await user.click(langButton);

    // Language menu should be visible with language options
    const menus = screen.getAllByRole('menu');
    expect(menus.length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Francais')).toBeInTheDocument();
    expect(screen.getByText('Deutsch')).toBeInTheDocument();
  });

  it('toggles user menu and shows email', async () => {
    const user = userEvent.setup();
    renderHeader();

    const userButton = screen.getByLabelText('nav.profile');
    await user.click(userButton);

    expect(screen.getByText('admin@swissbuildingos.ch')).toBeInTheDocument();
    expect(screen.getByText('nav.logout')).toBeInTheDocument();
  });

  it('calls logout when logout button is clicked', async () => {
    const user = userEvent.setup();
    renderHeader();

    // Open user menu
    const userButton = screen.getByLabelText('nav.profile');
    await user.click(userButton);

    // Click logout
    await user.click(screen.getByText('nav.logout'));

    expect(mockLogout).toHaveBeenCalledOnce();
  });

  it('renders hamburger menu button when onMenuToggle is provided', async () => {
    const onMenuToggle = vi.fn();
    const user = userEvent.setup();
    renderHeader({ onMenuToggle });

    const menuButton = screen.getByLabelText('Menu');
    await user.click(menuButton);

    expect(onMenuToggle).toHaveBeenCalledOnce();
  });

  it('does not render hamburger button when onMenuToggle is not provided', () => {
    renderHeader();

    expect(screen.queryByLabelText('Menu')).not.toBeInTheDocument();
  });

  it('renders mobile search button when onSearchOpen is provided', () => {
    const onSearchOpen = vi.fn();
    renderHeader({ onSearchOpen });

    // Both desktop and mobile search buttons share the same aria-label
    const searchButtons = screen.getAllByLabelText('nav.search');
    expect(searchButtons.length).toBe(2);
  });

  it('mobile search button calls onSearchOpen on click', async () => {
    const onSearchOpen = vi.fn();
    const user = userEvent.setup();
    renderHeader({ onSearchOpen });

    // The mobile button is the first one (sm:hidden), desktop is second (hidden sm:flex)
    const searchButtons = screen.getAllByLabelText('nav.search');
    await user.click(searchButtons[0]);

    expect(onSearchOpen).toHaveBeenCalledOnce();
  });

  it('does not render search buttons when onSearchOpen is not provided', () => {
    renderHeader();

    expect(screen.queryByLabelText('nav.search')).not.toBeInTheDocument();
  });

  it('closes language dropdown on Escape key', async () => {
    const user = userEvent.setup();
    renderHeader();

    // Open language dropdown
    const langButton = screen.getByLabelText('settings.language');
    await user.click(langButton);
    expect(screen.getAllByRole('menu').length).toBeGreaterThanOrEqual(1);

    // Press Escape
    await user.keyboard('{Escape}');

    // Dropdown should be closed
    expect(screen.queryByRole('menu')).not.toBeInTheDocument();
  });

  it('closes user menu on Escape key', async () => {
    const user = userEvent.setup();
    renderHeader();

    // Open user menu
    const userButton = screen.getByLabelText('nav.profile');
    await user.click(userButton);
    expect(screen.getByText('admin@swissbuildingos.ch')).toBeInTheDocument();

    // Press Escape
    await user.keyboard('{Escape}');

    // User menu should be closed
    expect(screen.queryByText('admin@swissbuildingos.ch')).not.toBeInTheDocument();
  });

  it('language dropdown items have role="menuitem"', async () => {
    const user = userEvent.setup();
    renderHeader();

    // Open language dropdown
    await user.click(screen.getByLabelText('settings.language'));

    const menuItems = screen.getAllByRole('menuitem');
    expect(menuItems.length).toBeGreaterThanOrEqual(2);
  });

  it('user menu items have role="menuitem"', async () => {
    const user = userEvent.setup();
    renderHeader();

    // Open user menu
    await user.click(screen.getByLabelText('nav.profile'));

    const menuItems = screen.getAllByRole('menuitem');
    expect(menuItems.length).toBeGreaterThanOrEqual(2);
  });
});
