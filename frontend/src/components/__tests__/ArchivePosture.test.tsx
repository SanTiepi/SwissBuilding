import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ArchivePosture } from '../building-detail/ArchivePosture';
import { artifactCustodyApi } from '@/api/artifactCustody';

vi.mock('@/api/artifactCustody', () => ({
  artifactCustodyApi: {
    getArchivePosture: vi.fn(),
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

describe('ArchivePosture', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders loading skeleton initially', () => {
    mockGetArchivePosture.mockReturnValue(new Promise(() => {}));

    render(<ArchivePosture buildingId="test-id" />, { wrapper });
    expect(document.querySelector('.animate-pulse')).toBeTruthy();
  });

  it('renders posture data', async () => {
    mockGetArchivePosture.mockResolvedValue({
      building_id: 'test-id',
      total_artifacts: 5,
      total_versions: 8,
      superseded_count: 2,
      archived_count: 1,
      withdrawn_count: 0,
      current_count: 5,
      last_custody_event: null,
    });

    render(<ArchivePosture buildingId="test-id" />, { wrapper });

    // Wait for data to render - check that posture title appears
    expect(await screen.findByText('artifact_custody.archive_posture')).toBeTruthy();
    // Check artifacts and superseded counts are present
    expect(screen.getByText('artifact_custody.artifacts')).toBeTruthy();
    expect(screen.getByText('artifact_custody.superseded')).toBeTruthy();
  });

  it('shows traceable badge when no withdrawn artifacts', async () => {
    mockGetArchivePosture.mockResolvedValue({
      building_id: 'test-id',
      total_artifacts: 3,
      total_versions: 4,
      superseded_count: 1,
      archived_count: 0,
      withdrawn_count: 0,
      current_count: 3,
      last_custody_event: null,
    });

    render(<ArchivePosture buildingId="test-id" />, { wrapper });

    expect(await screen.findByText('artifact_custody.all_traceable')).toBeTruthy();
  });

  it('shows last custody event when present', async () => {
    mockGetArchivePosture.mockResolvedValue({
      building_id: 'test-id',
      total_artifacts: 1,
      total_versions: 1,
      superseded_count: 0,
      archived_count: 0,
      withdrawn_count: 0,
      current_count: 1,
      last_custody_event: {
        id: 'evt-1',
        artifact_version_id: 'v-1',
        event_type: 'published',
        actor_type: 'user',
        actor_id: null,
        actor_name: null,
        recipient_org_id: null,
        details: null,
        occurred_at: '2026-03-25T10:00:00Z',
        created_at: '2026-03-25T10:00:00Z',
      },
    });

    render(<ArchivePosture buildingId="test-id" />, { wrapper });

    expect(await screen.findByText(/published/)).toBeTruthy();
  });
});
