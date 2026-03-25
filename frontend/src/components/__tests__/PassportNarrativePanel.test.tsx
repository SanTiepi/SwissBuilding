import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { remediationIntelligenceApi } from '@/api/remediationIntelligence';
import { PassportNarrativePanel } from '../building-detail/PassportNarrativePanel';

vi.mock('@/api/remediationIntelligence', () => ({
  remediationIntelligenceApi: {
    getPassportNarrative: vi.fn().mockResolvedValue({
      building_id: 'b-1',
      audience: 'owner',
      sections: [
        {
          title: 'Building Identity',
          body: 'Building located at Rue de Test 1, Lausanne.',
          evidence_refs: ['b-1'],
          caveats: [],
          audience_specific: false,
        },
        {
          title: 'Diagnostic Coverage',
          body: 'asbestos: 2 diagnostic(s). This determines your remediation obligations.',
          evidence_refs: [],
          caveats: [],
          audience_specific: false,
        },
        {
          title: 'Open Issues',
          body: '3 unresolved issues. These represent gaps.',
          evidence_refs: [],
          caveats: ['Some building data is incomplete.'],
          audience_specific: true,
        },
      ],
      generated_at: '2026-03-25T10:00:00Z',
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

describe('PassportNarrativePanel', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    vi.clearAllMocks();
  });

  const renderPanel = () =>
    render(
      <QueryClientProvider client={queryClient}>
        <PassportNarrativePanel buildingId="b-1" />
      </QueryClientProvider>,
    );

  it('renders narrative sections', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Building Identity')).toBeTruthy();
    });
  });

  it('shows diagnostic coverage', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText(/asbestos/)).toBeTruthy();
    });
  });

  it('shows caveats', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText(/incomplete/)).toBeTruthy();
    });
  });

  it('shows audience-specific badge', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('audience-specific')).toBeTruthy();
    });
  });

  it('renders audience selector buttons', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Owner')).toBeTruthy();
      expect(screen.getByText('Authority')).toBeTruthy();
      expect(screen.getByText('Contractor')).toBeTruthy();
    });
  });

  it('switches audience on click', async () => {
    renderPanel();
    await waitFor(() => {
      expect(screen.getByText('Authority')).toBeTruthy();
    });
    fireEvent.click(screen.getByText('Authority'));
    // The query should be called with authority audience
    await waitFor(() => {
      expect(remediationIntelligenceApi.getPassportNarrative).toHaveBeenCalledWith('b-1', 'authority');
    });
  });
});
