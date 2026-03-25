import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { demoPilotApi } from '@/api/demoPilot';
import DemoRunbook from '@/pages/DemoRunbook';

vi.mock('@/api/demoPilot', () => ({
  demoPilotApi: {
    listScenarios: vi.fn().mockResolvedValue([
      {
        id: 'sc-1',
        scenario_code: 'amiante-discovery',
        title: 'Amiante Discovery',
        persona_target: 'property_manager',
        starting_state_description: 'Building with unknown asbestos status',
        reveal_surfaces: ['passport', 'readiness'],
        proof_moment: 'Evidence chain validated',
        action_moment: 'Safe-to-start unlocked',
        seed_key: 'demo-amiante',
        is_active: true,
        created_at: '2026-01-01T00:00:00Z',
      },
      {
        id: 'sc-2',
        scenario_code: 'full-dossier',
        title: 'Full Dossier Build',
        persona_target: 'diagnostician',
        starting_state_description: 'Empty building record',
        reveal_surfaces: ['completeness'],
        proof_moment: null,
        action_moment: null,
        seed_key: null,
        is_active: true,
        created_at: '2026-01-02T00:00:00Z',
      },
    ]),
    getRunbook: vi.fn().mockResolvedValue({
      id: 'sc-1',
      scenario_code: 'amiante-discovery',
      title: 'Amiante Discovery',
      persona_target: 'property_manager',
      starting_state_description: 'Building with unknown asbestos status',
      reveal_surfaces: ['passport', 'readiness'],
      proof_moment: 'Evidence chain validated',
      action_moment: 'Safe-to-start unlocked',
      seed_key: 'demo-amiante',
      is_active: true,
      created_at: '2026-01-01T00:00:00Z',
      runbook_steps: [
        {
          id: 'step-1',
          scenario_id: 'sc-1',
          step_order: 1,
          title: 'Open building detail',
          description: 'Navigate to the seeded building',
          expected_ui_state: 'Overview tab visible',
          fallback_notes: null,
          created_at: '2026-01-01T00:00:00Z',
        },
        {
          id: 'step-2',
          scenario_id: 'sc-1',
          step_order: 2,
          title: 'Check passport grade',
          description: null,
          expected_ui_state: 'Grade D displayed',
          fallback_notes: null,
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
    }),
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
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
};

describe('DemoRunbook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    render(<DemoRunbook />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('demo_runbook.title')).toBeInTheDocument();
    });
  });

  it('renders scenario list with titles', async () => {
    render(<DemoRunbook />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('Amiante Discovery')).toBeInTheDocument();
      expect(screen.getByText('Full Dossier Build')).toBeInTheDocument();
    });
  });

  it('renders persona target badges', async () => {
    render(<DemoRunbook />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('property_manager')).toBeInTheDocument();
      expect(screen.getByText('diagnostician')).toBeInTheDocument();
    });
  });

  it('expands scenario to show runbook steps', async () => {
    render(<DemoRunbook />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('demo-scenario-amiante-discovery')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('demo-scenario-amiante-discovery'));

    await waitFor(() => {
      expect(screen.getByText('Open building detail')).toBeInTheDocument();
      expect(screen.getByText('Check passport grade')).toBeInTheDocument();
    });
  });

  it('shows expected_ui_state for runbook steps', async () => {
    render(<DemoRunbook />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('demo-scenario-amiante-discovery')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('demo-scenario-amiante-discovery'));

    await waitFor(() => {
      expect(screen.getByText(/Overview tab visible/)).toBeInTheDocument();
      expect(screen.getByText(/Grade D displayed/)).toBeInTheDocument();
    });
  });

  it('shows start demo link when seed_key is present', async () => {
    render(<DemoRunbook />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('demo-scenario-amiante-discovery')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('demo-scenario-amiante-discovery'));

    await waitFor(() => {
      expect(screen.getByTestId('start-demo-link')).toBeInTheDocument();
    });
  });

  it('renders empty state when no scenarios', async () => {
    vi.mocked(demoPilotApi.listScenarios).mockResolvedValueOnce([]);
    render(<DemoRunbook />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('demo_runbook.empty')).toBeInTheDocument();
    });
  });
});
