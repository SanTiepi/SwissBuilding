import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockUser = { organization_id: 'org-1', role: 'admin' };
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: { user: typeof mockUser }) => unknown) => selector({ user: mockUser })),
}));

const mockGetValueLedger = vi.fn();
vi.mock('@/api/intelligence', () => ({
  intelligenceApi: {
    getValueLedger: (...args: unknown[]) => mockGetValueLedger(...args),
  },
}));

import { ValueBanner } from '../ValueBanner';

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('ValueBanner', () => {
  it('renders value metrics when data loads', async () => {
    mockGetValueLedger.mockResolvedValue({
      org_id: 'org-1',
      sources_unified_total: 45,
      contradictions_resolved_total: 12,
      proof_chains_created_total: 30,
      documents_secured_total: 50,
      decisions_backed_total: 20,
      hours_saved_estimate: 120,
      value_chf_estimate: 85000,
      days_active: 90,
      value_per_day: 944,
      trend: 'growing',
    });
    wrap(<ValueBanner />);

    // Banner text with interpolation key rendered
    expect(await screen.findByText('value.banner_text')).toBeInTheDocument();
  });

  it('shows trend indicator', async () => {
    mockGetValueLedger.mockResolvedValue({
      org_id: 'org-1',
      sources_unified_total: 45,
      contradictions_resolved_total: 12,
      proof_chains_created_total: 30,
      documents_secured_total: 50,
      decisions_backed_total: 20,
      hours_saved_estimate: 120,
      value_chf_estimate: 85000,
      days_active: 90,
      value_per_day: 944,
      trend: 'growing',
    });
    wrap(<ValueBanner />);

    const trendIcon = await screen.findByLabelText('growing');
    expect(trendIcon).toBeInTheDocument();
  });

  it('collapses and expands on toggle', async () => {
    mockGetValueLedger.mockResolvedValue({
      org_id: 'org-1',
      sources_unified_total: 45,
      contradictions_resolved_total: 12,
      proof_chains_created_total: 30,
      documents_secured_total: 50,
      decisions_backed_total: 20,
      hours_saved_estimate: 120,
      value_chf_estimate: 85000,
      days_active: 90,
      value_per_day: 944,
      trend: 'growing',
    });
    wrap(<ValueBanner />);

    await screen.findByText('value.banner_text');
    // Collapse
    fireEvent.click(screen.getByLabelText('Collapse'));
    expect(screen.queryByText('value.banner_text')).not.toBeInTheDocument();
  });
});
