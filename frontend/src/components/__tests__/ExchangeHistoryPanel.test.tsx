import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ExchangeHistoryPanel from '../building-detail/ExchangeHistoryPanel';
import { exchangeApi, type Publication, type ImportReceipt } from '@/api/exchange';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/utils/formatters', () => ({
  cn: (...args: unknown[]) => args.filter(Boolean).join(' '),
  formatDate: (d: string) => d,
}));

vi.mock('@/api/exchange', () => ({
  exchangeApi: {
    listPublications: vi.fn(),
    listImportReceipts: vi.fn(),
  },
}));

const mockPublications: Publication[] = [
  {
    id: 'pub-1',
    building_id: 'b-1',
    contract_version_id: 'cv-1',
    audience_type: 'authority',
    publication_type: 'full_passport',
    pack_id: null,
    content_hash: 'deadbeef12345678',
    published_at: '2026-03-01T10:00:00Z',
    published_by_org_id: 'org-1',
    published_by_user_id: 'u-1',
    delivery_state: 'published',
    superseded_by_id: null,
    created_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-01T10:00:00Z',
  },
  {
    id: 'pub-2',
    building_id: 'b-1',
    contract_version_id: 'cv-1',
    audience_type: 'owner',
    publication_type: 'summary',
    pack_id: null,
    content_hash: 'cafebabe87654321',
    published_at: '2026-02-15T10:00:00Z',
    published_by_org_id: 'org-1',
    published_by_user_id: 'u-1',
    delivery_state: 'superseded',
    superseded_by_id: 'pub-1',
    created_at: '2026-02-15T10:00:00Z',
    updated_at: '2026-03-01T10:00:00Z',
  },
];

const mockImports: ImportReceipt[] = [
  {
    id: 'imp-1',
    building_id: 'b-1',
    source_system: 'ERP-Gerance',
    contract_code: 'bc-passport-v1',
    contract_version: 1,
    import_reference: 'ref-001',
    imported_at: '2026-03-02T10:00:00Z',
    status: 'accepted',
    content_hash: 'aabbccdd11223344',
    rejection_reason: null,
    matched_publication_id: 'pub-1',
    notes: null,
    created_at: '2026-03-02T10:00:00Z',
  },
];

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('ExchangeHistoryPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(exchangeApi.listPublications).mockResolvedValue(mockPublications);
    vi.mocked(exchangeApi.listImportReceipts).mockResolvedValue(mockImports);
  });

  it('renders loading state initially', () => {
    vi.mocked(exchangeApi.listPublications).mockReturnValue(new Promise(() => {}));
    render(<ExchangeHistoryPanel buildingId="b-1" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('exchange-history-loading')).toBeInTheDocument();
  });

  it('renders panel with title after loading', async () => {
    render(<ExchangeHistoryPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('exchange-history-panel')).toBeInTheDocument();
    });
    expect(screen.getByText('exchange.title')).toBeInTheDocument();
  });

  it('shows outbound publications section', async () => {
    render(<ExchangeHistoryPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('publications-section')).toBeInTheDocument();
    });
    expect(screen.getByTestId('pub-row-pub-1')).toBeInTheDocument();
    expect(screen.getByTestId('pub-row-pub-2')).toBeInTheDocument();
  });

  it('shows publication delivery state badges', async () => {
    render(<ExchangeHistoryPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pub-state-pub-1')).toHaveTextContent('published');
    });
    expect(screen.getByTestId('pub-state-pub-2')).toHaveTextContent('superseded');
  });

  it('shows content hash for publications', async () => {
    render(<ExchangeHistoryPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pub-hash-pub-1')).toHaveTextContent('deadbeef');
    });
  });

  it('shows superseded indicator', async () => {
    render(<ExchangeHistoryPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('pub-superseded-pub-2')).toBeInTheDocument();
    });
  });

  it('shows inbound imports section', async () => {
    render(<ExchangeHistoryPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('imports-section')).toBeInTheDocument();
    });
    expect(screen.getByTestId('import-row-imp-1')).toBeInTheDocument();
    expect(screen.getByTestId('import-status-imp-1')).toHaveTextContent('accepted');
  });

  it('shows empty state when no exchanges', async () => {
    vi.mocked(exchangeApi.listPublications).mockResolvedValue([]);
    vi.mocked(exchangeApi.listImportReceipts).mockResolvedValue([]);
    render(<ExchangeHistoryPanel buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('exchange-empty')).toBeInTheDocument();
    });
  });

  it('calls APIs with correct building ID', async () => {
    render(<ExchangeHistoryPanel buildingId="b-42" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(exchangeApi.listPublications).toHaveBeenCalledWith('b-42');
      expect(exchangeApi.listImportReceipts).toHaveBeenCalledWith('b-42');
    });
  });
});
