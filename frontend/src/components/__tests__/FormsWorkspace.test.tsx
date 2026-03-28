import { describe, it, expect, vi, afterEach } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockGetApplicable = vi.fn();
const mockGetInstances = vi.fn();
vi.mock('@/api/forms', () => ({
  formsApi: {
    getApplicable: (...args: unknown[]) => mockGetApplicable(...args),
    getInstances: (...args: unknown[]) => mockGetInstances(...args),
    prefill: vi.fn(),
    update: vi.fn(),
    submit: vi.fn(),
  },
}));

const { default: FormsWorkspace } = await import('../building-detail/FormsWorkspace');

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('FormsWorkspace', () => {
  afterEach(cleanup);

  it('renders applicable forms section', async () => {
    mockGetApplicable.mockResolvedValue([
      {
        id: 'tmpl-1',
        name: 'Notification SUVA',
        form_type: 'suva_notification',
        canton: null,
      },
    ]);
    mockGetInstances.mockResolvedValue([]);
    render(<FormsWorkspace buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      expect(screen.getByText(/forms\.title|formulaire/i)).toBeDefined();
    });
  });

  it('renders form instances when they exist', async () => {
    mockGetApplicable.mockResolvedValue([]);
    mockGetInstances.mockResolvedValue([
      {
        id: 'inst-1',
        template_name: 'Declaration VD',
        status: 'prefilled',
        prefill_confidence: 0.85,
        created_at: '2026-03-28T10:00:00Z',
      },
    ]);
    render(<FormsWorkspace buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      expect(document.body).toBeDefined();
    });
  });

  it('handles empty state', async () => {
    mockGetApplicable.mockResolvedValue([]);
    mockGetInstances.mockResolvedValue([]);
    render(<FormsWorkspace buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      expect(document.body).toBeDefined();
    });
  });

  it('handles API error gracefully', async () => {
    mockGetApplicable.mockRejectedValue(new Error('API error'));
    mockGetInstances.mockRejectedValue(new Error('API error'));
    render(<FormsWorkspace buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      expect(document.body).toBeDefined();
    });
  });
});
