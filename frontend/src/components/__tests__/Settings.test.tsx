import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import Settings from '@/pages/Settings';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: {
      first_name: 'Robin',
      email: 'admin@swissbuildingos.ch',
      role: 'admin',
    },
  }),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: Object.assign(
    () => ({
      user: {
        role: 'admin',
      },
    }),
    {
      getState: () => ({
        user: {
          role: 'admin',
        },
        updateUser: vi.fn(),
      }),
    },
  ),
}));

const mockGetNotificationPreferences = vi.fn();
const mockUpdateNotificationPreferences = vi.fn();
vi.mock('@/api/settings', () => ({
  settingsApi: {
    updateProfile: vi.fn(),
    changePassword: vi.fn(),
    getNotificationPreferences: (...args: unknown[]) => mockGetNotificationPreferences(...args),
    updateNotificationPreferences: (...args: unknown[]) => mockUpdateNotificationPreferences(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('Settings', () => {
  beforeEach(() => {
    mockGetNotificationPreferences.mockReset();
    mockUpdateNotificationPreferences.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when notification preferences fail to load', async () => {
    mockGetNotificationPreferences.mockRejectedValue(new Error('boom'));
    render(<Settings />, { wrapper });

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });
});
