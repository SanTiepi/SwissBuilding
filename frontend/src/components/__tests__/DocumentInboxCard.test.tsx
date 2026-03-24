import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { documentInboxApi } from '@/api/documentInbox';
import DocumentInboxCard from '../building-detail/DocumentInboxCard';

vi.mock('@/api/documentInbox', () => ({
  documentInboxApi: {
    list: vi.fn().mockResolvedValue({
      total: 3,
      pending: 2,
      linked: 1,
      classified: 0,
      rejected: 0,
      items: [
        {
          id: 'di-1',
          building_id: 'b-1',
          filename: 'rapport-amiante.pdf',
          source: 'email',
          status: 'pending',
          document_type: null,
          uploaded_at: '2025-03-01T10:00:00Z',
          processed_at: null,
        },
        {
          id: 'di-2',
          building_id: 'b-1',
          filename: 'plan-etage-3.dwg',
          source: 'upload',
          status: 'pending',
          document_type: null,
          uploaded_at: '2025-03-02T14:00:00Z',
          processed_at: null,
        },
        {
          id: 'di-3',
          building_id: 'b-1',
          filename: 'facture-renovation.pdf',
          source: 'scan',
          status: 'linked',
          document_type: 'invoice',
          uploaded_at: '2025-02-20T09:00:00Z',
          processed_at: '2025-02-21T10:00:00Z',
        },
      ],
    }),
    link: vi.fn().mockResolvedValue({ id: 'di-1', status: 'linked' }),
    classify: vi.fn().mockResolvedValue({ id: 'di-1', status: 'classified' }),
    reject: vi.fn().mockResolvedValue({ id: 'di-1', status: 'rejected' }),
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

describe('DocumentInboxCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders inbox items with filenames', async () => {
    render(<DocumentInboxCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('rapport-amiante.pdf')).toBeInTheDocument();
      expect(screen.getByText('plan-etage-3.dwg')).toBeInTheDocument();
      expect(screen.getByText('facture-renovation.pdf')).toBeInTheDocument();
    });
  });

  it('renders pending count badge', async () => {
    render(<DocumentInboxCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('inbox-pending-count')).toHaveTextContent('2');
    });
  });

  it('renders status badges', async () => {
    render(<DocumentInboxCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const badges = screen.getAllByTestId('inbox-status-badge');
      expect(badges.length).toBe(3);
    });
  });

  it('renders source labels', async () => {
    render(<DocumentInboxCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('email')).toBeInTheDocument();
      expect(screen.getByText('upload')).toBeInTheDocument();
    });
  });

  it('renders action buttons for pending items', async () => {
    render(<DocumentInboxCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const linkBtns = screen.getAllByTestId('inbox-link-btn');
      expect(linkBtns.length).toBe(2);
      const classifyBtns = screen.getAllByTestId('inbox-classify-btn');
      expect(classifyBtns.length).toBe(2);
      const rejectBtns = screen.getAllByTestId('inbox-reject-btn');
      expect(rejectBtns.length).toBe(2);
    });
  });

  it('opens classify input when classify clicked', async () => {
    render(<DocumentInboxCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByTestId('inbox-classify-btn').length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getAllByTestId('inbox-classify-btn')[0]);
    expect(screen.getByTestId('inbox-classify-input')).toBeInTheDocument();
    expect(screen.getByTestId('inbox-classify-confirm-btn')).toBeInTheDocument();
  });

  it('shows empty state when no items', async () => {
    vi.mocked(documentInboxApi.list).mockResolvedValueOnce({
      total: 0,
      pending: 0,
      linked: 0,
      classified: 0,
      rejected: 0,
      items: [],
    });
    render(<DocumentInboxCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('inbox-empty')).toBeInTheDocument();
    });
  });

  it('calls reject API when reject clicked', async () => {
    render(<DocumentInboxCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getAllByTestId('inbox-reject-btn').length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getAllByTestId('inbox-reject-btn')[0]);
    await waitFor(() => {
      expect(documentInboxApi.reject).toHaveBeenCalledWith('di-1');
    });
  });
});
