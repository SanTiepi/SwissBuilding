import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { AlertDashboard } from '../AlertDashboard';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGet = vi.fn();
const mockPost = vi.fn();
vi.mock('@/api/client', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
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

describe('AlertDashboard', () => {
  afterEach(() => {
    cleanup();
    mockGet.mockReset();
    mockPost.mockReset();
  });

  it('renders severity breakdown from summary', async () => {
    mockGet.mockResolvedValue({
      data: {
        total_alerts: 5,
        by_severity: { critical: 2, warning: 2, info: 1 },
        by_type: {},
        buildings_with_alerts: 3,
      },
    });

    render(<AlertDashboard />, { wrapper });

    expect(await screen.findByText('5')).toBeInTheDocument();
    expect(screen.getByText('2', { selector: '.text-red-700' })).toBeInTheDocument();
  });

  it('shows scan button and triggers portfolio scan', async () => {
    mockGet.mockResolvedValue({
      data: { total_alerts: 0, by_severity: { critical: 0, warning: 0, info: 0 }, by_type: {}, buildings_with_alerts: 0 },
    });
    mockPost.mockResolvedValue({ data: [] });

    render(<AlertDashboard />, { wrapper });

    const scanButton = await screen.findByText('alerts.scan_portfolio');
    fireEvent.click(scanButton);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith('/portfolio/alerts/scan');
    });
  });

  it('shows empty state after scan with no alerts', async () => {
    mockGet.mockResolvedValue({
      data: { total_alerts: 0, by_severity: { critical: 0, warning: 0, info: 0 }, by_type: {}, buildings_with_alerts: 0 },
    });
    mockPost.mockResolvedValue({ data: [] });

    render(<AlertDashboard />, { wrapper });

    const scanButton = await screen.findByText('alerts.scan_portfolio');
    fireEvent.click(scanButton);

    expect(await screen.findByText('alerts.no_alerts')).toBeInTheDocument();
  });
});
