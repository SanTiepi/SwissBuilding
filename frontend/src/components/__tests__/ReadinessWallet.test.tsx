import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ReadinessWallet from '@/pages/ReadinessWallet';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useBuildings', () => ({
  useBuilding: () => ({
    data: { address: 'Rue du Test 1' },
  }),
}));

const mockList = vi.fn();
const mockEvaluateAll = vi.fn();
vi.mock('@/api/readiness', () => ({
  readinessApi: {
    list: (...args: unknown[]) => mockList(...args),
    evaluateAll: (...args: unknown[]) => mockEvaluateAll(...args),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter
        initialEntries={['/buildings/b1/readiness']}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/buildings/:buildingId/readiness" element={children} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ReadinessWallet', () => {
  beforeEach(() => {
    mockList.mockReset();
    mockEvaluateAll.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when readiness query fails', async () => {
    mockList.mockRejectedValue(new Error('boom'));
    render(<ReadinessWallet />, { wrapper });

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });

  it('renders readiness cards when assessments load', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'ready',
          score: 0.9,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [{ label: 'Diagnostic present', passed: true, details: null }],
          blockers_json: [],
          conditions_json: [],
        },
      ],
      total: 1,
    });

    render(<ReadinessWallet />, { wrapper });

    expect(await screen.findByText('readiness.safe_to_start')).toBeInTheDocument();
    expect(screen.getByText('90%')).toBeInTheDocument();
    // Check label is inside collapsible section; verify gate card renders with show_checks toggle
    expect(screen.getByText('readiness.show_checks')).toBeInTheDocument();
  });

  it('renders prework trigger card when triggers are present', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'not_ready',
          score: 0.4,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [],
          blockers_json: [],
          conditions_json: [],
          prework_triggers: [
            {
              trigger_type: 'missing_diagnostic',
              reason: 'Asbestos diagnostic required before renovation',
              urgency: 'high',
              source_check: 'asbestos_coverage',
            },
            {
              trigger_type: 'missing_report',
              reason: 'Lab report pending',
              urgency: 'medium',
              source_check: 'lab_results',
            },
          ],
        },
      ],
      total: 1,
    });

    render(<ReadinessWallet />, { wrapper });

    expect(await screen.findByText('readiness.prework_triggers')).toBeInTheDocument();
    expect(screen.getByText('Asbestos diagnostic required before renovation')).toBeInTheDocument();
    expect(screen.getByText('Lab report pending')).toBeInTheDocument();
    expect(screen.getByText('missing_diagnostic')).toBeInTheDocument();
    expect(screen.getByText('missing_report')).toBeInTheDocument();
  });

  it('does not render prework trigger card when triggers array is empty', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'ready',
          score: 1.0,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [],
          blockers_json: [],
          conditions_json: [],
          prework_triggers: [],
        },
      ],
      total: 1,
    });

    render(<ReadinessWallet />, { wrapper });

    // Wait for content to load
    expect(await screen.findByText('readiness.safe_to_start')).toBeInTheDocument();
    // Trigger card should not be rendered
    expect(screen.queryByText('readiness.prework_triggers')).not.toBeInTheDocument();
  });

  it('renders pfas_check prework trigger alongside other triggers', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'not_ready',
          score: 0.3,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [{ label: 'PFAS assessment', passed: false, details: 'PFAS evaluation missing' }],
          blockers_json: [
            { label: 'PFAS assessment required', severity: 'high', details: 'No PFAS evaluation on file' },
          ],
          conditions_json: [],
          prework_triggers: [
            {
              trigger_type: 'pfas_check',
              reason: 'PFAS evaluation required before renovation',
              urgency: 'high',
              source_check: 'pfas_assessment',
            },
          ],
        },
      ],
      total: 1,
    });

    render(<ReadinessWallet />, { wrapper });

    expect(await screen.findByText('readiness.prework_triggers')).toBeInTheDocument();
    expect(screen.getByText('PFAS evaluation required before renovation')).toBeInTheDocument();
    expect(screen.getByText('pfas_check')).toBeInTheDocument();
    // Blocker should also appear
    expect(screen.getByText('PFAS assessment required')).toBeInTheDocument();
  });

  it('does not render prework trigger card when triggers field is missing', async () => {
    mockList.mockResolvedValue({
      items: [
        {
          readiness_type: 'safe_to_start',
          status: 'ready',
          score: 0.9,
          assessed_at: '2026-03-08T00:00:00Z',
          checks_json: [],
          blockers_json: [],
          conditions_json: [],
          // no prework_triggers field
        },
      ],
      total: 1,
    });

    render(<ReadinessWallet />, { wrapper });

    expect(await screen.findByText('readiness.safe_to_start')).toBeInTheDocument();
    expect(screen.queryByText('readiness.prework_triggers')).not.toBeInTheDocument();
  });
});
