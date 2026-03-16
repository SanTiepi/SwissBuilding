import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { Sidebar } from '../Sidebar';
import type { User } from '@/types';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockUser = {
  id: 'u-001',
  email: 'admin@swissbuildingos.ch',
  first_name: 'Robin',
  last_name: 'Fragniere',
  role: 'admin' as const,
  organization_id: null,
  language: 'fr',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

let currentMockUser: User | null = mockUser;

vi.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    user: currentMockUser,
  }),
}));

function renderSidebar(props: Partial<Parameters<typeof Sidebar>[0]> = {}) {
  const defaultProps = {
    collapsed: false,
    onToggle: vi.fn(),
  };
  return render(
    <MemoryRouter initialEntries={['/dashboard']} future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
      <Sidebar {...defaultProps} {...props} />
    </MemoryRouter>,
  );
}

describe('Sidebar', () => {
  beforeEach(() => {
    currentMockUser = { ...mockUser };
  });

  it('renders the app name when not collapsed', () => {
    renderSidebar({ collapsed: false });

    expect(screen.getByText('SwissBuildingOS')).toBeInTheDocument();
  });

  it('hides the app name when collapsed', () => {
    renderSidebar({ collapsed: true });

    expect(screen.queryByText('SwissBuildingOS')).not.toBeInTheDocument();
  });

  it('renders all nav items for admin role', () => {
    renderSidebar();

    expect(screen.getByText('nav.dashboard')).toBeInTheDocument();
    expect(screen.getByText('nav.buildings')).toBeInTheDocument();
    expect(screen.getByText('nav.map')).toBeInTheDocument();
    expect(screen.getByText('nav.simulation')).toBeInTheDocument();
    expect(screen.getByText('nav.documents')).toBeInTheDocument();
    expect(screen.getByText('nav.settings')).toBeInTheDocument();
  });

  it('hides risk-simulator for owner role (not in allowedRoles)', () => {
    currentMockUser = { ...mockUser, role: 'owner' };
    renderSidebar();

    expect(screen.getByText('nav.dashboard')).toBeInTheDocument();
    expect(screen.getByText('nav.buildings')).toBeInTheDocument();
    expect(screen.queryByText('nav.simulation')).not.toBeInTheDocument();
  });

  it('shows risk-simulator for diagnostician role', () => {
    currentMockUser = { ...mockUser, role: 'diagnostician' };
    renderSidebar();

    expect(screen.getByText('nav.simulation')).toBeInTheDocument();
  });

  it('calls onToggle when collapse button is clicked', async () => {
    const user = userEvent.setup();
    const onToggle = vi.fn();
    renderSidebar({ onToggle });

    const collapseButton = screen.getByLabelText('Collapse sidebar');
    await user.click(collapseButton);

    expect(onToggle).toHaveBeenCalledOnce();
  });

  it('shows expand label when collapsed', () => {
    renderSidebar({ collapsed: true });

    expect(screen.getByLabelText('Expand sidebar')).toBeInTheDocument();
  });

  it('hides collapse toggle on mobile and shows close button', async () => {
    const user = userEvent.setup();
    const onMobileClose = vi.fn();
    renderSidebar({ isMobile: true, onMobileClose });

    // Collapse toggle should not be present on mobile
    expect(screen.queryByLabelText('Collapse sidebar')).not.toBeInTheDocument();
    expect(screen.queryByLabelText('Expand sidebar')).not.toBeInTheDocument();

    // Close button should be present
    const closeButton = screen.getByLabelText('form.close');
    await user.click(closeButton);

    expect(onMobileClose).toHaveBeenCalledOnce();
  });
});
