import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import AdminCustomerSuccess from '@/pages/AdminCustomerSuccess';

const mockGet = vi.fn();

vi.mock('@/api/client', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
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

function setupMocks() {
  mockGet.mockImplementation((url: string) => {
    if (url.includes('customer-success')) {
      return Promise.resolve({
        data: {
          organization_id: 'org-1',
          milestones: [
            {
              id: 'ms-1',
              organization_id: 'org-1',
              milestone_type: 'first_building_added',
              status: 'achieved',
              achieved_at: '2026-03-01T00:00:00Z',
              evidence_entity_type: 'building',
              evidence_entity_id: 'b-1',
              evidence_summary: 'Building "10 Rue du Lac" added',
              blocker_description: null,
              created_at: '2026-03-01T00:00:00Z',
              updated_at: '2026-03-01T00:00:00Z',
            },
            {
              id: 'ms-2',
              organization_id: 'org-1',
              milestone_type: 'first_diagnostic_completed',
              status: 'blocked',
              achieved_at: null,
              evidence_entity_type: null,
              evidence_entity_id: null,
              evidence_summary: null,
              blocker_description: 'No diagnostic submitted yet',
              created_at: '2026-03-01T00:00:00Z',
              updated_at: '2026-03-01T00:00:00Z',
            },
          ],
          next_step: {
            milestone_type: 'first_diagnostic_completed',
            recommendation: 'Create and validate a diagnostic for any building.',
          },
        },
      });
    }
    if (url.includes('/organizations')) {
      return Promise.resolve({
        data: [
          { id: 'org-1', name: 'Regie Romande' },
          { id: 'org-2', name: 'DiagSwiss' },
        ],
      });
    }
    return Promise.resolve({ data: [] });
  });
}

async function selectOrg() {
  await waitFor(() => {
    expect(screen.getByTestId('cs-org-selector')).toBeInTheDocument();
    // Ensure orgs are loaded
    expect(screen.getByText('Regie Romande')).toBeInTheDocument();
  });
  const user = userEvent.setup();
  await act(async () => {
    await user.selectOptions(screen.getByTestId('cs-org-selector'), 'org-1');
  });
}

describe('AdminCustomerSuccess', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMocks();
  });

  it('renders page title', async () => {
    render(<AdminCustomerSuccess />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('customer_success.title')).toBeInTheDocument();
    });
  });

  it('renders org selector with options', async () => {
    render(<AdminCustomerSuccess />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('Regie Romande')).toBeInTheDocument();
      expect(screen.getByText('DiagSwiss')).toBeInTheDocument();
    });
  });

  it('shows prompt when no org selected', async () => {
    render(<AdminCustomerSuccess />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('customer_success.select_org_prompt')).toBeInTheDocument();
    });
  });

  it('renders milestones after org selection', async () => {
    render(<AdminCustomerSuccess />, { wrapper: createWrapper() });
    await selectOrg();
    await waitFor(() => {
      expect(screen.getByTestId('milestone-first_building_added')).toBeInTheDocument();
    });
  });

  it('renders achieved milestone with evidence', async () => {
    render(<AdminCustomerSuccess />, { wrapper: createWrapper() });
    await selectOrg();
    await waitFor(() => {
      expect(screen.getByTestId('milestone-achieved')).toBeInTheDocument();
    });
  });

  it('renders blocked milestone with blocker text', async () => {
    render(<AdminCustomerSuccess />, { wrapper: createWrapper() });
    await selectOrg();
    await waitFor(() => {
      expect(screen.getByTestId('milestone-blocked')).toBeInTheDocument();
    });
  });

  it('renders next step recommendation', async () => {
    render(<AdminCustomerSuccess />, { wrapper: createWrapper() });
    await selectOrg();
    await waitFor(() => {
      expect(screen.getByTestId('cs-next-step')).toBeInTheDocument();
      expect(screen.getByText(/Create and validate a diagnostic/)).toBeInTheDocument();
    });
  });

  it('renders check & advance button after org selection', async () => {
    render(<AdminCustomerSuccess />, { wrapper: createWrapper() });
    await selectOrg();
    await waitFor(() => {
      expect(screen.getByTestId('cs-check-advance')).toBeInTheDocument();
    });
  });
});
