import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { diagnosticIntegrationApi } from '@/api/diagnosticIntegration';
import type { ImportedDiagnosticSummaryDto } from '@/api/diagnosticIntegration';
import ImportedDiagnosticSummary from '../building-detail/ImportedDiagnosticSummary';

vi.mock('@/api/diagnosticIntegration', () => ({
  diagnosticIntegrationApi: {
    getImportedDiagnosticSummaries: vi.fn().mockResolvedValue([]),
    getPublicationsForBuilding: vi.fn().mockResolvedValue([]),
    getMissionOrdersForBuilding: vi.fn().mockResolvedValue([]),
    createMissionOrder: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, string | number>) => {
      if (params) {
        let result = key;
        Object.entries(params).forEach(([k, v]) => {
          result = result.replace(new RegExp(`\\{${k}\\}`, 'g'), String(v));
        });
        return result;
      }
      return key;
    },
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

const nominalSummary: ImportedDiagnosticSummaryDto = {
  source_system: 'batiscan',
  mission_ref: 'M-001',
  published_at: '2026-03-20T10:00:00Z',
  consumer_state: 'ingested',
  match_state: 'auto_matched',
  match_key_type: 'egid',
  building_id: 'b-1',
  report_readiness_status: 'ready',
  snapshot_version: 1,
  payload_hash: 'abc123',
  contract_version: 'v1.0',
  sample_count: 12,
  positive_count: 3,
  review_count: 1,
  not_analyzed_count: 0,
  ai_summary_text: 'Asbestos found in floor tiles.',
  has_ai: true,
  has_remediation: true,
  is_partial: false,
  flags: [],
};

describe('ImportedDiagnosticSummary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders nominal summary with source label and mission ref and samples', async () => {
    vi.mocked(diagnosticIntegrationApi.getImportedDiagnosticSummaries).mockResolvedValue([
      nominalSummary,
    ]);
    render(<ImportedDiagnosticSummary buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('imported-diagnostic-summaries')).toBeInTheDocument();
    });
    expect(screen.getByTestId('mission-ref')).toHaveTextContent('M-001');
    expect(screen.getByTestId('sample-summary')).toBeInTheDocument();
    expect(screen.getByTestId('readiness-badge')).toBeInTheDocument();
  });

  it('shows no_ai flag badge when has_ai is false', async () => {
    vi.mocked(diagnosticIntegrationApi.getImportedDiagnosticSummaries).mockResolvedValue([
      { ...nominalSummary, has_ai: false, ai_summary_text: null, flags: ['no_ai'] },
    ]);
    render(<ImportedDiagnosticSummary buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('flag-no_ai')).toBeInTheDocument();
    });
  });

  it('shows no_remediation flag badge', async () => {
    vi.mocked(diagnosticIntegrationApi.getImportedDiagnosticSummaries).mockResolvedValue([
      { ...nominalSummary, has_remediation: false, flags: ['no_remediation'] },
    ]);
    render(<ImportedDiagnosticSummary buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('flag-no_remediation')).toBeInTheDocument();
    });
  });

  it('shows review_required warning banner when match_state is needs_review', async () => {
    vi.mocked(diagnosticIntegrationApi.getImportedDiagnosticSummaries).mockResolvedValue([
      { ...nominalSummary, match_state: 'needs_review' },
    ]);
    render(<ImportedDiagnosticSummary buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('banner-review-required')).toBeInTheDocument();
    });
  });

  it('shows rejected_source red badge', async () => {
    vi.mocked(diagnosticIntegrationApi.getImportedDiagnosticSummaries).mockResolvedValue([
      {
        ...nominalSummary,
        consumer_state: 'rejected_source',
        flags: ['rejected_source'],
      },
    ]);
    render(<ImportedDiagnosticSummary buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('flag-rejected_source')).toBeInTheDocument();
    });
  });

  it('renders nothing when no summaries (empty state)', async () => {
    vi.mocked(diagnosticIntegrationApi.getImportedDiagnosticSummaries).mockResolvedValue([]);
    const { container } = render(<ImportedDiagnosticSummary buildingId="b-1" />, {
      wrapper: createWrapper(),
    });
    await waitFor(() => {
      expect(diagnosticIntegrationApi.getImportedDiagnosticSummaries).toHaveBeenCalled();
    });
    expect(container.querySelector('[data-testid="imported-diagnostic-summaries"]')).toBeNull();
  });
});
