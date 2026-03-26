import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { intelligenceApi } from '@/api/intelligence';
import PortfolioTriage from '@/pages/PortfolioTriage';

vi.mock('@/api/intelligence', () => ({
  intelligenceApi: {
    getPortfolioTriage: vi.fn(),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({ user: { id: 'u-1', role: 'admin' }, isAuthenticated: true }),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ user: { id: 'u-1', organization_id: 'org-1', role: 'admin' } }),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockTriageData = {
  org_id: 'org-1',
  critical_count: 2,
  action_needed_count: 3,
  monitored_count: 5,
  under_control_count: 10,
  buildings: [
    {
      id: 'b-1',
      address: 'Rue du Midi 15, 1003 Lausanne',
      status: 'critical',
      top_blocker: 'Diagnostic amiante manquant',
      risk_score: 0.92,
      next_action: 'Commander diagnostic',
      passport_grade: 'E',
    },
    {
      id: 'b-2',
      address: 'Avenue de la Gare 8, 1003 Lausanne',
      status: 'critical',
      top_blocker: 'AvT expire',
      risk_score: 0.85,
      next_action: 'Renouveler AvT',
      passport_grade: 'F',
    },
    {
      id: 'b-3',
      address: 'Chemin des Vignes 3, 1007 Lausanne',
      status: 'action_needed',
      top_blocker: null,
      risk_score: 0.55,
      next_action: 'Planifier assainissement',
      passport_grade: 'D',
    },
    {
      id: 'b-4',
      address: 'Place du Tunnel 1, 1005 Lausanne',
      status: 'under_control',
      top_blocker: null,
      risk_score: 0.1,
      next_action: null,
      passport_grade: 'B',
    },
  ],
};

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter>
        <PortfolioTriage />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('PortfolioTriage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(intelligenceApi.getPortfolioTriage).mockResolvedValue(mockTriageData);
  });

  it('renders title', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('triage-title')).toBeInTheDocument();
    });
  });

  it('renders 4 summary cards with correct counts', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('summary-cards')).toBeInTheDocument();
    });
    expect(screen.getByTestId('summary-card-critical')).toHaveTextContent('2');
    expect(screen.getByTestId('summary-card-action_needed')).toHaveTextContent('3');
    expect(screen.getByTestId('summary-card-monitored')).toHaveTextContent('5');
    expect(screen.getByTestId('summary-card-under_control')).toHaveTextContent('10');
  });

  it('renders building list', async () => {
    renderPage();
    await waitFor(() => {
      const rows = screen.getAllByTestId('building-row');
      expect(rows.length).toBe(4);
    });
  });

  it('shows building addresses', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByText('Rue du Midi 15, 1003 Lausanne')).toBeInTheDocument();
      expect(screen.getByText('Avenue de la Gare 8, 1003 Lausanne')).toBeInTheDocument();
    });
  });

  it('shows grade badges', async () => {
    renderPage();
    await waitFor(() => {
      const badges = screen.getAllByTestId('mini-grade-badge');
      expect(badges.length).toBe(4);
      expect(badges[0]).toHaveTextContent('E'); // first is critical with E grade
    });
  });

  it('filters by status when clicking summary card', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('summary-card-critical')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('summary-card-critical'));

    await waitFor(() => {
      const rows = screen.getAllByTestId('building-row');
      expect(rows.length).toBe(2); // only critical buildings
    });
    expect(screen.getByTestId('clear-filter')).toBeInTheDocument();
  });

  it('clears filter when clicking clear button', async () => {
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('summary-card-critical')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('summary-card-critical'));
    await waitFor(() => {
      expect(screen.getAllByTestId('building-row').length).toBe(2);
    });

    fireEvent.click(screen.getByTestId('clear-filter'));
    await waitFor(() => {
      expect(screen.getAllByTestId('building-row').length).toBe(4);
    });
  });

  it('navigates to building detail on row click', async () => {
    renderPage();
    await waitFor(() => {
      const rows = screen.getAllByTestId('building-row');
      fireEvent.click(rows[0]);
    });
    expect(mockNavigate).toHaveBeenCalledWith('/buildings/b-1');
  });

  it('shows loading state', () => {
    vi.mocked(intelligenceApi.getPortfolioTriage).mockReturnValue(new Promise(() => {}));
    renderPage();
    expect(screen.getByTestId('triage-loading')).toBeInTheDocument();
  });
});
