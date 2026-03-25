import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { audiencePacksApi } from '@/api/audiencePacks';
import AudiencePackPreview from '../building-detail/AudiencePackPreview';

vi.mock('@/api/audiencePacks', () => ({
  audiencePacksApi: {
    listByBuilding: vi.fn().mockResolvedValue([
      {
        id: 'pack-1',
        building_id: 'b-1',
        pack_type: 'insurer',
        pack_version: 1,
        status: 'draft',
        generated_at: '2026-03-01T10:00:00Z',
        content_hash: 'abc123def456',
        created_at: '2026-03-01T10:00:00Z',
      },
      {
        id: 'pack-2',
        building_id: 'b-1',
        pack_type: 'insurer',
        pack_version: 2,
        status: 'ready',
        generated_at: '2026-03-15T10:00:00Z',
        content_hash: 'def456ghi789',
        created_at: '2026-03-15T10:00:00Z',
      },
    ]),
    get: vi.fn().mockResolvedValue({
      id: 'pack-1',
      building_id: 'b-1',
      pack_type: 'insurer',
      pack_version: 1,
      status: 'draft',
      generated_by_user_id: null,
      sections: {
        diagnostics: { name: 'diagnostics', included: true, blocked: false },
        financial: { name: 'financial', included: true, blocked: false },
        ownership: { name: 'ownership', included: false, blocked: true },
      },
      unknowns_summary: [{ category: 'material', description: 'Missing asbestos survey', severity: 'high' }],
      contradictions_summary: [{ type: 'date', description: 'Construction year mismatch', severity: 'medium' }],
      residual_risk_summary: [{ source: 'asbestos', description: 'Potential asbestos in basement', level: 'medium' }],
      trust_refs: [{ source: 'diagnostic_lab', confidence: 0.92, freshness: 'recent' }],
      proof_refs: [{ document_id: 'doc-1', title: 'Asbestos report', version: 2, freshness: 'current' }],
      content_hash: 'abc123def456abcdef',
      generated_at: '2026-03-01T10:00:00Z',
      superseded_by_id: null,
      created_at: '2026-03-01T10:00:00Z',
      updated_at: '2026-03-01T10:00:00Z',
      caveats: [{ caveat_type: 'freshness_warning', severity: 'medium', message: 'Data older than 6 months', applies_when: {} }],
    }),
    generate: vi.fn().mockResolvedValue({
      id: 'pack-new',
      building_id: 'b-1',
      pack_type: 'insurer',
      pack_version: 3,
      status: 'draft',
    }),
    share: vi.fn().mockResolvedValue({ id: 'pack-1', status: 'shared' }),
    compare: vi.fn().mockResolvedValue({
      pack_1: { id: 'pack-1', pack_type: 'insurer', pack_version: 1, status: 'draft', sections: {}, caveats: [] },
      pack_2: { id: 'pack-2', pack_type: 'insurer', pack_version: 2, status: 'ready', sections: {}, caveats: [] },
      section_diff: {},
      caveat_diff: {},
    }),
    getCaveats: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('AudiencePackPreview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the component with title', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('audience-pack-preview')).toBeInTheDocument();
    });
    expect(screen.getByText('audience_pack.title')).toBeInTheDocument();
  });

  it('renders audience type tabs', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('audience-tabs')).toBeInTheDocument();
    });
    expect(screen.getByTestId('audience-tab-insurer')).toBeInTheDocument();
    expect(screen.getByTestId('audience-tab-fiduciary')).toBeInTheDocument();
    expect(screen.getByTestId('audience-tab-transaction')).toBeInTheDocument();
    expect(screen.getByTestId('audience-tab-lender')).toBeInTheDocument();
  });

  it('loads and displays pack list items', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getAllByTestId('pack-list-item')).toHaveLength(2);
    });
  });

  it('displays pack detail with sections when pack selected', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pack-detail')).toBeInTheDocument();
    });
    expect(screen.getAllByTestId('included-section').length).toBeGreaterThan(0);
    expect(screen.getAllByTestId('blocked-section').length).toBeGreaterThan(0);
  });

  it('displays unknowns summary', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pack-detail')).toBeInTheDocument();
    });
    expect(screen.getAllByTestId('unknown-item').length).toBeGreaterThan(0);
    expect(screen.getByText('Missing asbestos survey')).toBeInTheDocument();
  });

  it('displays contradictions summary', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pack-detail')).toBeInTheDocument();
    });
    expect(screen.getAllByTestId('contradiction-item').length).toBeGreaterThan(0);
    expect(screen.getByText('Construction year mismatch')).toBeInTheDocument();
  });

  it('displays residual risks', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pack-detail')).toBeInTheDocument();
    });
    expect(screen.getAllByTestId('risk-item').length).toBeGreaterThan(0);
  });

  it('displays trust and proof refs', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pack-detail')).toBeInTheDocument();
    });
    expect(screen.getAllByTestId('trust-ref').length).toBeGreaterThan(0);
    expect(screen.getAllByTestId('proof-ref').length).toBeGreaterThan(0);
  });

  it('displays content hash', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('content-hash')).toBeInTheDocument();
    });
  });

  it('shows generate button and calls API', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('generate-pack-button')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('generate-pack-button'));
    await waitFor(() => {
      expect(audiencePacksApi.generate).toHaveBeenCalledWith('b-1', 'insurer');
    });
  });

  it('shows share button for draft pack and calls API', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('share-button')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('share-button'));
    await waitFor(() => {
      expect(audiencePacksApi.share).toHaveBeenCalledWith('pack-1');
    });
  });

  it('switches audience type on tab click', async () => {
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('audience-tab-fiduciary')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('audience-tab-fiduciary'));
    await waitFor(() => {
      expect(audiencePacksApi.listByBuilding).toHaveBeenCalledWith('b-1', 'fiduciary');
    });
  });

  it('shows empty state when no packs', async () => {
    vi.mocked(audiencePacksApi.listByBuilding).mockResolvedValueOnce([]);
    render(<AudiencePackPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pack-empty')).toBeInTheDocument();
    });
  });
});
