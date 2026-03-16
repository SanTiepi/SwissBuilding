import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { NotificationBell } from '../NotificationBell';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGet = vi.fn();
vi.mock('@/api/client', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('NotificationBell', () => {
  beforeEach(() => {
    mockGet.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('shows explicit error state when recent notifications fail to load', async () => {
    mockGet.mockImplementation((url: string) => {
      if (url === '/notifications/unread-count') {
        return Promise.resolve({ data: { count: 2 } });
      }
      if (url === '/notifications') {
        return Promise.reject(new Error('boom'));
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    render(<NotificationBell />, { wrapper });

    fireEvent.click(screen.getByLabelText('notification.title'));

    expect(await screen.findByText('notification.load_error')).toBeInTheDocument();
  });
});
