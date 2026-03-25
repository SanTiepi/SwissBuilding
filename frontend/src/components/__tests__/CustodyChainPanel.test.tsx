import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CustodyChainPanel } from '../building-detail/CustodyChainPanel';
import { artifactCustodyApi } from '@/api/artifactCustody';

vi.mock('@/api/artifactCustody', () => ({
  artifactCustodyApi: {
    getArchivePosture: vi.fn(),
    getVersionEvents: vi.fn(),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>;
}

const mockGetArchivePosture = vi.mocked(artifactCustodyApi.getArchivePosture);

describe('CustodyChainPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no versions', async () => {
    mockGetArchivePosture.mockResolvedValue({
      building_id: 'test-id',
      total_artifacts: 0,
      total_versions: 0,
      superseded_count: 0,
      archived_count: 0,
      withdrawn_count: 0,
      current_count: 0,
      last_custody_event: null,
    });

    render(<CustodyChainPanel buildingId="test-id" />, { wrapper });
    expect(await screen.findByText('artifact_custody.no_versions')).toBeTruthy();
  });

  it('renders version counts from posture', async () => {
    mockGetArchivePosture.mockResolvedValue({
      building_id: 'test-id',
      total_artifacts: 3,
      total_versions: 5,
      superseded_count: 2,
      archived_count: 0,
      withdrawn_count: 0,
      current_count: 3,
      last_custody_event: null,
    });

    render(<CustodyChainPanel buildingId="test-id" />, { wrapper });
    expect(await screen.findByText('5 artifact_custody.versions')).toBeTruthy();
  });

  it('renders loading state', () => {
    mockGetArchivePosture.mockReturnValue(new Promise(() => {}));

    render(<CustodyChainPanel buildingId="test-id" />, { wrapper });
    expect(screen.getByText('Loading custody chain...')).toBeTruthy();
  });

  it('shows last event details when present', async () => {
    mockGetArchivePosture.mockResolvedValue({
      building_id: 'test-id',
      total_artifacts: 1,
      total_versions: 2,
      superseded_count: 1,
      archived_count: 0,
      withdrawn_count: 0,
      current_count: 1,
      last_custody_event: {
        id: 'evt-1',
        artifact_version_id: 'v-1',
        event_type: 'acknowledged',
        actor_type: 'authority',
        actor_id: null,
        actor_name: 'Canton VD',
        recipient_org_id: null,
        details: null,
        occurred_at: '2026-03-20T14:00:00Z',
        created_at: '2026-03-20T14:00:00Z',
      },
    });

    render(<CustodyChainPanel buildingId="test-id" />, { wrapper });
    expect(await screen.findByText(/acknowledged/)).toBeTruthy();
    expect(await screen.findByText(/Canton VD/)).toBeTruthy();
  });
});
