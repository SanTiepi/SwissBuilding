import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { publicSectorApi } from '@/api/publicSector';
import { ReviewPackCard } from '../building-detail/ReviewPackCard';

vi.mock('@/api/publicSector', () => ({
  publicSectorApi: {
    listReviewPacks: vi.fn(),
    generateReviewPack: vi.fn(),
    circulateReviewPack: vi.fn(),
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

const mockPacks = [
  {
    id: 'pack-1',
    building_id: 'b-1',
    generated_by_user_id: 'u-1',
    pack_version: 1,
    status: 'draft',
    sections: null,
    content_hash: 'abc',
    review_deadline: '2026-04-01',
    circulated_to: null,
    notes: null,
    generated_at: '2026-03-20T10:00:00Z',
    created_at: '2026-03-20T10:00:00Z',
    updated_at: '2026-03-20T10:00:00Z',
  },
  {
    id: 'pack-2',
    building_id: 'b-1',
    generated_by_user_id: 'u-1',
    pack_version: 2,
    status: 'circulating',
    sections: null,
    content_hash: 'def',
    review_deadline: null,
    circulated_to: [{ org_name: 'Legal', role: 'reviewer', sent_at: '2026-03-21T10:00:00Z' }],
    notes: null,
    generated_at: '2026-03-21T10:00:00Z',
    created_at: '2026-03-21T10:00:00Z',
    updated_at: '2026-03-21T10:00:00Z',
  },
];

describe('ReviewPackCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders pack list with versions', async () => {
    vi.mocked(publicSectorApi.listReviewPacks).mockResolvedValue(mockPacks);
    render(<ReviewPackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByText('v1')).toBeInTheDocument();
      expect(screen.getByText('v2')).toBeInTheDocument();
    });
  });

  it('renders status badges', async () => {
    vi.mocked(publicSectorApi.listReviewPacks).mockResolvedValue(mockPacks);
    render(<ReviewPackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const badges = screen.getAllByTestId('review-pack-status');
      expect(badges.length).toBe(2);
    });
  });

  it('shows empty state when no packs', async () => {
    vi.mocked(publicSectorApi.listReviewPacks).mockResolvedValue([]);
    render(<ReviewPackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('review-pack-empty')).toBeInTheDocument();
    });
  });

  it('renders generate button', async () => {
    vi.mocked(publicSectorApi.listReviewPacks).mockResolvedValue([]);
    render(<ReviewPackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('generate-review-pack-button')).toBeInTheDocument();
    });
  });

  it('renders circulate button for draft packs', async () => {
    vi.mocked(publicSectorApi.listReviewPacks).mockResolvedValue(mockPacks);
    render(<ReviewPackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      const circulateButtons = screen.getAllByTestId('circulate-button');
      expect(circulateButtons.length).toBeGreaterThan(0);
    });
  });

  it('renders circulated-to list for circulating packs', async () => {
    vi.mocked(publicSectorApi.listReviewPacks).mockResolvedValue(mockPacks);
    render(<ReviewPackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('circulated-to-list')).toBeInTheDocument();
      expect(screen.getByText('Legal')).toBeInTheDocument();
    });
  });

  it('renders review deadline', async () => {
    vi.mocked(publicSectorApi.listReviewPacks).mockResolvedValue(mockPacks);
    render(<ReviewPackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('review-deadline')).toBeInTheDocument();
    });
  });

  it('calls generate API on button click', async () => {
    vi.mocked(publicSectorApi.listReviewPacks).mockResolvedValue([]);
    vi.mocked(publicSectorApi.generateReviewPack).mockResolvedValue(mockPacks[0]);
    render(<ReviewPackCard buildingId="b-1" />, { wrapper: createWrapper() });

    await waitFor(() => {
      expect(screen.getByTestId('generate-review-pack-button')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByTestId('generate-review-pack-button'));

    await waitFor(() => {
      expect(publicSectorApi.generateReviewPack).toHaveBeenCalledWith('b-1', {});
    });
  });
});
