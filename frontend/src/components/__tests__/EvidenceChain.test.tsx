import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, cleanup, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { EvidenceChain } from '../EvidenceChain';
import type { EvidenceLink } from '@/types';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockList = vi.fn();
vi.mock('@/api/evidence', () => ({
  evidenceApi: { list: (...args: unknown[]) => mockList(...args) },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const sampleLinks: EvidenceLink[] = [
  {
    id: 'e1',
    source_type: 'diagnostic',
    source_id: 's1',
    target_type: 'risk_score',
    target_id: 't1',
    relationship: 'proves',
    confidence: 0.92,
    legal_reference: 'OTConst Art. 60a',
    explanation: 'Lab results confirm asbestos presence',
    created_by: null,
    created_at: '2025-01-01T00:00:00Z',
  },
  {
    id: 'e2',
    source_type: 'document',
    source_id: 's2',
    target_type: 'action_item',
    target_id: 't2',
    relationship: 'supports',
    confidence: null,
    legal_reference: null,
    explanation: null,
    created_by: null,
    created_at: '2025-01-02T00:00:00Z',
  },
];

describe('EvidenceChain', () => {
  beforeEach(() => {
    mockList.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('shows loading state while fetching', async () => {
    mockList.mockReturnValue(new Promise(() => {}));
    render(<EvidenceChain targetType="risk_score" targetId="t1" />, { wrapper });
    expect(screen.getByText('app.loading')).toBeInTheDocument();
  });

  it('renders nothing in compact mode when no links', async () => {
    mockList.mockResolvedValue([]);
    const { container } = render(<EvidenceChain targetType="risk_score" targetId="t1" compact />, { wrapper });
    await waitFor(() => {
      expect(screen.queryByText('app.loading')).not.toBeInTheDocument();
    });
    expect(container.innerHTML).toBe('');
  });

  it('shows "no evidence" message when empty and not compact', async () => {
    mockList.mockResolvedValue([]);
    render(<EvidenceChain targetType="risk_score" targetId="t1" />, { wrapper });
    expect(await screen.findByText('evidence.none')).toBeInTheDocument();
  });

  it('shows explicit error state when evidence loading fails', async () => {
    mockList.mockRejectedValue(new Error('boom'));
    render(<EvidenceChain targetType="risk_score" targetId="t1" />, { wrapper });
    expect(await screen.findByText('evidence.load_error')).toBeInTheDocument();
  });

  it('renders evidence count in compact mode', async () => {
    mockList.mockResolvedValue(sampleLinks);
    render(<EvidenceChain targetType="risk_score" targetId="t1" compact />, { wrapper });
    expect(await screen.findByText(/evidence\.links/)).toBeInTheDocument();
    expect(screen.getByText(/2/)).toBeInTheDocument();
  });

  it('renders evidence links with relationship badges', async () => {
    mockList.mockResolvedValue(sampleLinks);
    render(<EvidenceChain targetType="risk_score" targetId="t1" />, { wrapper });
    expect(await screen.findByText('evidence_rel.proves')).toBeInTheDocument();
    expect(screen.getByText('evidence_rel.supports')).toBeInTheDocument();
  });

  it('shows confidence percentage when available', async () => {
    mockList.mockResolvedValue(sampleLinks);
    render(<EvidenceChain targetType="risk_score" targetId="t1" />, { wrapper });
    expect(await screen.findByText('92%')).toBeInTheDocument();
  });

  it('shows legal reference when available', async () => {
    mockList.mockResolvedValue(sampleLinks);
    render(<EvidenceChain targetType="risk_score" targetId="t1" />, { wrapper });
    expect(await screen.findByText('OTConst Art. 60a')).toBeInTheDocument();
  });

  it('shows explanation text', async () => {
    mockList.mockResolvedValue(sampleLinks);
    render(<EvidenceChain targetType="risk_score" targetId="t1" />, { wrapper });
    expect(await screen.findByText('Lab results confirm asbestos presence')).toBeInTheDocument();
  });
});
