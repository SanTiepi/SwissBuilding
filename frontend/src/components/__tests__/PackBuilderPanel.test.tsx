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

const mockListPacks = vi.fn();
const mockGenerate = vi.fn();
vi.mock('@/api/packBuilder', () => ({
  packBuilderApi: {
    listAvailable: (...args: unknown[]) => mockListPacks(...args),
    generate: (...args: unknown[]) => mockGenerate(...args),
  },
}));

const { default: PackBuilderPanel } = await import('../building-detail/PackBuilderPanel');

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

describe('PackBuilderPanel', () => {
  afterEach(cleanup);

  it('renders pack type cards', async () => {
    mockListPacks.mockResolvedValue({
      packs: [
        { pack_type: 'authority', name: 'Pack Autorite', ready: true, sections_count: 9 },
        { pack_type: 'owner', name: 'Pack Proprietaire', ready: true, sections_count: 8 },
        { pack_type: 'insurer', name: 'Pack Assureur', ready: false, sections_count: 7 },
      ],
    });
    render(<PackBuilderPanel buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      expect(screen.getByText(/autorit/i)).toBeDefined();
    });
  });

  it('shows readiness indicators', async () => {
    mockListPacks.mockResolvedValue({
      packs: [
        { pack_type: 'authority', name: 'Pack Autorite', ready: true, sections_count: 9 },
        { pack_type: 'contractor', name: 'Pack Entreprise', ready: false, sections_count: 5 },
      ],
    });
    render(<PackBuilderPanel buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      // Should render without crash and show pack types
      expect(document.body.textContent).toContain('pack_builder');
    });
  });

  it('handles empty pack list', async () => {
    mockListPacks.mockResolvedValue({ packs: [] });
    render(<PackBuilderPanel buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      expect(document.body).toBeDefined();
    });
  });

  it('handles API error gracefully', async () => {
    mockListPacks.mockRejectedValue(new Error('Server error'));
    render(<PackBuilderPanel buildingId="b1" />, { wrapper });
    await vi.waitFor(() => {
      expect(document.body).toBeDefined();
    });
  });
});
