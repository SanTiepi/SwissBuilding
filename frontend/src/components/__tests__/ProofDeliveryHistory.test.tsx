import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ProofDeliveryHistory from '../building-detail/ProofDeliveryHistory';
import { proofDeliveryApi, type ProofDelivery } from '@/api/proofDelivery';

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

vi.mock('@/api/proofDelivery', () => ({
  proofDeliveryApi: {
    listByBuilding: vi.fn(),
  },
}));

const mockDeliveries: ProofDelivery[] = [
  {
    id: 'del-1',
    building_id: 'b-1',
    target_type: 'document',
    target_id: 'doc-1',
    target_name: 'Rapport amiante 2025',
    audience: 'owner',
    method: 'email',
    status: 'delivered',
    content_hash: 'abc123def456',
    version: 2,
    created_at: '2026-03-01T10:00:00Z',
    updated_at: '2026-03-02T10:00:00Z',
  },
  {
    id: 'del-2',
    building_id: 'b-1',
    target_type: 'document',
    target_id: 'doc-1',
    target_name: 'Rapport amiante 2025',
    audience: 'authority',
    method: 'api',
    status: 'acknowledged',
    content_hash: 'abc123def456',
    version: 2,
    created_at: '2026-03-01T12:00:00Z',
    updated_at: '2026-03-03T10:00:00Z',
  },
  {
    id: 'del-3',
    building_id: 'b-1',
    target_type: 'pack',
    target_id: 'pack-1',
    target_name: 'Dossier complet',
    audience: 'contractor',
    method: 'download',
    status: 'queued',
    content_hash: null,
    version: 1,
    created_at: '2026-03-04T10:00:00Z',
    updated_at: '2026-03-04T10:00:00Z',
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

describe('ProofDeliveryHistory', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(proofDeliveryApi.listByBuilding).mockResolvedValue(mockDeliveries);
  });

  it('renders loading state initially', () => {
    vi.mocked(proofDeliveryApi.listByBuilding).mockReturnValue(new Promise(() => {}));
    render(<ProofDeliveryHistory buildingId="b-1" />, { wrapper: createWrapper() });
    expect(screen.getByTestId('proof-delivery-loading')).toBeInTheDocument();
  });

  it('renders the component with title', async () => {
    render(<ProofDeliveryHistory buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('proof-delivery-history')).toBeInTheDocument();
    });
    expect(screen.getByText('proof_delivery.title')).toBeInTheDocument();
  });

  it('groups deliveries by target', async () => {
    render(<ProofDeliveryHistory buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('proof-delivery-list')).toBeInTheDocument();
    });
    // Two groups: document:doc-1 and pack:pack-1
    expect(screen.getByTestId('delivery-group-document:doc-1')).toBeInTheDocument();
    expect(screen.getByTestId('delivery-group-pack:pack-1')).toBeInTheDocument();
  });

  it('renders delivery rows with audience badges', async () => {
    render(<ProofDeliveryHistory buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('delivery-row-del-1')).toBeInTheDocument();
    });
    expect(screen.getByTestId('audience-badge-del-1')).toHaveTextContent('owner');
    expect(screen.getByTestId('audience-badge-del-2')).toHaveTextContent('authority');
  });

  it('shows content hash and version', async () => {
    render(<ProofDeliveryHistory buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('delivery-row-del-1')).toBeInTheDocument();
    });
    expect(screen.getByTestId('hash-del-1')).toHaveTextContent('#abc123de');
    expect(screen.getByTestId('version-del-1')).toHaveTextContent('v2');
  });

  it('shows empty state when no deliveries', async () => {
    vi.mocked(proofDeliveryApi.listByBuilding).mockResolvedValue([]);
    render(<ProofDeliveryHistory buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('proof-delivery-empty')).toBeInTheDocument();
    });
  });

  it('renders status step indicators', async () => {
    render(<ProofDeliveryHistory buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('status-steps-del-1')).toBeInTheDocument();
    });
  });

  it('calls API with correct building ID', async () => {
    render(<ProofDeliveryHistory buildingId="b-42" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(proofDeliveryApi.listByBuilding).toHaveBeenCalledWith('b-42');
    });
  });
});
