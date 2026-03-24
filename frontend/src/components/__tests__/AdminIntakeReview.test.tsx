import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import AdminIntakeReview from '@/pages/AdminIntakeReview';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockAuthStore = vi.fn();
vi.mock('@/store/authStore', () => ({
  useAuthStore: Object.assign(
    (selector: (s: unknown) => unknown) => mockAuthStore(selector),
    {
      getState: () => ({
        user: { role: 'admin' },
      }),
    },
  ),
}));

const mockList = vi.fn();
const mockUpdateStatus = vi.fn();
const mockConvert = vi.fn();

vi.mock('@/api/intake', () => ({
  intakeApi: {
    list: (...args: unknown[]) => mockList(...args),
    updateStatus: (...args: unknown[]) => mockUpdateStatus(...args),
    convert: (...args: unknown[]) => mockConvert(...args),
  },
}));

vi.mock('@/utils/formatters', () => ({
  cn: (...classes: (string | undefined | false)[]) => classes.filter(Boolean).join(' '),
}));

const mockRequests = [
  {
    id: 'req-1',
    name: 'Jean Dupont',
    email: 'jean@test.ch',
    phone: '+41791234567',
    company: 'Dupont SA',
    building_address: 'Rue de Lausanne 10',
    city: 'Lausanne',
    postal_code: '1000',
    egid: '12345',
    request_type: 'asbestos',
    urgency: 'standard',
    description: 'Need asbestos check',
    status: 'new',
    created_at: '2026-03-20T10:00:00Z',
    updated_at: '2026-03-20T10:00:00Z',
  },
  {
    id: 'req-2',
    name: 'Marie Martin',
    email: 'marie@test.ch',
    phone: null,
    company: null,
    building_address: 'Avenue de la Gare 5',
    city: 'Geneva',
    postal_code: '1201',
    egid: null,
    request_type: 'pcb',
    urgency: 'urgent',
    description: null,
    status: 'qualified',
    created_at: '2026-03-21T14:00:00Z',
    updated_at: '2026-03-21T14:00:00Z',
  },
];

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <AdminIntakeReview />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AdminIntakeReview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthStore.mockImplementation((selector: (s: { user: { role: string } }) => unknown) =>
      selector({ user: { role: 'admin' } }),
    );
    mockList.mockResolvedValue({ items: mockRequests, total: 2 });
  });
  afterEach(cleanup);

  it('renders the title', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('intake-review-title')).toBeInTheDocument();
    });
  });

  it('shows access denied for non-admin', () => {
    mockAuthStore.mockImplementation((selector: (s: { user: { role: string } }) => unknown) =>
      selector({ user: { role: 'diagnostician' } }),
    );
    renderPage();
    expect(screen.queryByTestId('intake-review-title')).not.toBeInTheDocument();
  });

  it('renders status filter buttons', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('intake-filter-all')).toBeInTheDocument();
      expect(screen.getByTestId('intake-filter-new')).toBeInTheDocument();
      expect(screen.getByTestId('intake-filter-qualified')).toBeInTheDocument();
      expect(screen.getByTestId('intake-filter-converted')).toBeInTheDocument();
      expect(screen.getByTestId('intake-filter-rejected')).toBeInTheDocument();
    });
  });

  it('renders request cards', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('intake-card-req-1')).toBeInTheDocument();
      expect(screen.getByTestId('intake-card-req-2')).toBeInTheDocument();
    });
  });

  it('displays requester info on cards', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Jean Dupont')).toBeInTheDocument();
      expect(screen.getByText('jean@test.ch')).toBeInTheDocument();
      expect(screen.getByText('Rue de Lausanne 10, Lausanne 1000')).toBeInTheDocument();
    });
  });

  it('shows qualify button for new requests', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('intake-qualify-req-1')).toBeInTheDocument();
    });
  });

  it('shows convert button for new and qualified requests', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('intake-convert-req-1')).toBeInTheDocument();
      expect(screen.getByTestId('intake-convert-req-2')).toBeInTheDocument();
    });
  });

  it('shows reject button for non-final status requests', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('intake-reject-req-1')).toBeInTheDocument();
      expect(screen.getByTestId('intake-reject-req-2')).toBeInTheDocument();
    });
  });

  it('calls updateStatus on qualify click', async () => {
    mockUpdateStatus.mockResolvedValue({ ...mockRequests[0], status: 'qualified' });
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('intake-qualify-req-1')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('intake-qualify-req-1'));
    await waitFor(() => {
      expect(mockUpdateStatus).toHaveBeenCalledWith('req-1', 'qualified');
    });
  });

  it('shows empty state when no requests', async () => {
    mockList.mockResolvedValue({ items: [], total: 0 });
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('intake-empty')).toBeInTheDocument();
    });
  });

  it('changes filter on status button click', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('intake-filter-new')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('intake-filter-new'));
    await waitFor(() => {
      expect(mockList).toHaveBeenCalledWith({ status: 'new' });
    });
  });
});
