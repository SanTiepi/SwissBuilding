import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BuildingTimeline } from '../BuildingTimeline';
import type { TimelineEntry, PaginatedResponse } from '@/types';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockEntries: TimelineEntry[] = [
  {
    id: '1',
    date: '2024-06-15T00:00:00',
    event_type: 'diagnostic',
    title: 'Diagnostic asbestos (completed)',
    description: 'Asbestos found in ceiling tiles',
    icon_hint: 'microscope',
    metadata: { diagnostic_type: 'asbestos', status: 'completed' },
    source_id: '1',
    source_type: 'diagnostic',
  },
  {
    id: '2',
    date: '2024-03-01T00:00:00',
    event_type: 'document',
    title: 'Lab Report.pdf',
    description: 'Laboratory analysis report',
    icon_hint: 'file',
    metadata: { document_type: 'lab_analysis' },
    source_id: '2',
    source_type: 'document',
  },
  {
    id: '3',
    date: '1965-01-01T00:00:00',
    event_type: 'construction',
    title: 'Construction (1965)',
    description: 'Building constructed in 1965',
    icon_hint: 'building',
    metadata: { construction_year: 1965 },
    source_id: '3',
    source_type: 'building',
  },
];

const mockResponse: PaginatedResponse<TimelineEntry> = {
  items: mockEntries,
  total: 3,
  page: 1,
  size: 50,
  pages: 1,
};

const emptyResponse: PaginatedResponse<TimelineEntry> = {
  items: [],
  total: 0,
  page: 1,
  size: 50,
  pages: 0,
};

vi.mock('@/api/timeline', () => ({
  timelineApi: {
    list: vi.fn(),
  },
}));

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

describe('BuildingTimeline', () => {
  it('renders timeline entries', async () => {
    const { timelineApi } = await import('@/api/timeline');
    vi.mocked(timelineApi.list).mockResolvedValue(mockResponse);

    render(<BuildingTimeline buildingId="test-id" />, { wrapper: createWrapper() });

    expect(await screen.findByText('Diagnostic asbestos (completed)')).toBeInTheDocument();
    expect(screen.getByText('Lab Report.pdf')).toBeInTheDocument();
    expect(screen.getByText('Construction (1965)')).toBeInTheDocument();
  });

  it('renders empty state', async () => {
    const { timelineApi } = await import('@/api/timeline');
    vi.mocked(timelineApi.list).mockResolvedValue(emptyResponse);

    render(<BuildingTimeline buildingId="test-id" />, { wrapper: createWrapper() });

    expect(await screen.findByText('timeline.empty')).toBeInTheDocument();
  });

  it('renders explicit error state', async () => {
    const { timelineApi } = await import('@/api/timeline');
    vi.mocked(timelineApi.list).mockRejectedValue(new Error('boom'));

    render(<BuildingTimeline buildingId="test-id" />, { wrapper: createWrapper() });

    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders event type labels', async () => {
    const { timelineApi } = await import('@/api/timeline');
    vi.mocked(timelineApi.list).mockResolvedValue(mockResponse);

    render(<BuildingTimeline buildingId="test-id" />, { wrapper: createWrapper() });

    // The mocked t() returns the key itself
    expect(await screen.findByText('timeline.event_type.diagnostic')).toBeInTheDocument();
    expect(screen.getByText('timeline.event_type.document')).toBeInTheDocument();
    expect(screen.getByText('timeline.event_type.construction')).toBeInTheDocument();
  });
});
