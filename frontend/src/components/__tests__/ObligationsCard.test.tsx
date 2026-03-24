import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { obligationsApi } from '@/api/obligations';
import ObligationsCard from '../building-detail/ObligationsCard';

function makeDateStr(offsetDays: number): string {
  const d = new Date();
  d.setDate(d.getDate() + offsetDays);
  return d.toISOString().split('T')[0];
}

vi.mock('@/api/obligations', () => ({
  obligationsApi: {
    listByBuilding: vi.fn().mockImplementation(() => {
      const pastDate = makeDateStr(-7);
      const soonDate = makeDateStr(15);
      const futureDate = makeDateStr(90);
      return Promise.resolve([
        {
          id: 'obl-1',
          building_id: 'b-1',
          title: 'Controle amiante annuel',
          description: 'Verification obligatoire',
          obligation_type: 'regulatory',
          priority: 'high',
          status: 'pending',
          due_date: pastDate,
          completed_at: null,
          created_at: '2025-01-01T00:00:00Z',
          updated_at: '2025-01-01T00:00:00Z',
        },
        {
          id: 'obl-2',
          building_id: 'b-1',
          title: 'Renouvellement contrat maintenance',
          description: null,
          obligation_type: 'contractual',
          priority: 'medium',
          status: 'in_progress',
          due_date: soonDate,
          completed_at: null,
          created_at: '2025-02-01T00:00:00Z',
          updated_at: '2025-02-01T00:00:00Z',
        },
        {
          id: 'obl-3',
          building_id: 'b-1',
          title: 'Inspection securite incendie',
          description: 'Prochaine inspection',
          obligation_type: 'safety',
          priority: 'low',
          status: 'pending',
          due_date: futureDate,
          completed_at: null,
          created_at: '2025-03-01T00:00:00Z',
          updated_at: '2025-03-01T00:00:00Z',
        },
        {
          id: 'obl-4',
          building_id: 'b-1',
          title: 'Audit energetique',
          description: null,
          obligation_type: 'environmental',
          priority: 'medium',
          status: 'completed',
          due_date: '2024-12-31',
          completed_at: '2024-12-20T00:00:00Z',
          created_at: '2024-06-01T00:00:00Z',
          updated_at: '2024-12-20T00:00:00Z',
        },
      ]);
    }),
    create: vi.fn().mockResolvedValue({ id: 'obl-5' }),
    complete: vi.fn().mockResolvedValue({ id: 'obl-1', status: 'completed' }),
    cancel: vi.fn().mockResolvedValue({ id: 'obl-1', status: 'cancelled' }),
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

describe('ObligationsCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders obligation items', async () => {
    render(<ObligationsCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('Controle amiante annuel')).toBeInTheDocument();
      expect(screen.getByText('Renouvellement contrat maintenance')).toBeInTheDocument();
      expect(screen.getByText('Inspection securite incendie')).toBeInTheDocument();
    });
  });

  it('renders overdue section for past-due items', async () => {
    render(<ObligationsCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('obligation-overdue-section')).toBeInTheDocument();
    });
  });

  it('renders due soon section', async () => {
    render(<ObligationsCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('obligation-due-soon-section')).toBeInTheDocument();
    });
  });

  it('renders type badges', async () => {
    render(<ObligationsCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const badges = screen.getAllByTestId('obligation-type-badge');
      expect(badges.length).toBeGreaterThanOrEqual(3);
    });
  });

  it('renders add obligation button', async () => {
    render(<ObligationsCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('obligation-add-btn')).toBeInTheDocument();
    });
  });

  it('opens add form when button clicked', async () => {
    render(<ObligationsCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('obligation-add-btn')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('obligation-add-btn'));
    expect(screen.getByTestId('obligation-add-form')).toBeInTheDocument();
    expect(screen.getByTestId('obligation-title-input')).toBeInTheDocument();
    expect(screen.getByTestId('obligation-type-select')).toBeInTheDocument();
    expect(screen.getByTestId('obligation-priority-select')).toBeInTheDocument();
    expect(screen.getByTestId('obligation-due-date-input')).toBeInTheDocument();
  });

  it('renders complete and cancel buttons for active items', async () => {
    render(<ObligationsCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const completeBtns = screen.getAllByTestId('obligation-complete-btn');
      expect(completeBtns.length).toBe(3);
      const cancelBtns = screen.getAllByTestId('obligation-cancel-btn');
      expect(cancelBtns.length).toBeGreaterThanOrEqual(3);
    });
  });

  it('shows empty state when no obligations', async () => {
    vi.mocked(obligationsApi.listByBuilding).mockResolvedValueOnce([]);
    render(<ObligationsCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('obligation-empty')).toBeInTheDocument();
    });
  });
});
