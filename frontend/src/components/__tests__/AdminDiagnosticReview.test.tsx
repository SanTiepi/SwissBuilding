import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import AdminDiagnosticReview from '@/pages/AdminDiagnosticReview';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockAuthStore = vi.fn();
vi.mock('@/store/authStore', () => ({
  useAuthStore: Object.assign((selector: (s: unknown) => unknown) => mockAuthStore(selector), {
    getState: () => ({
      user: { role: 'admin' },
    }),
  }),
}));

const mockGetUnmatched = vi.fn();
const mockMatchToBuilding = vi.fn();

vi.mock('@/api/diagnosticReview', () => ({
  diagnosticReviewApi: {
    getUnmatched: (...args: unknown[]) => mockGetUnmatched(...args),
    matchToBuilding: (...args: unknown[]) => mockMatchToBuilding(...args),
  },
}));

const mockBuildingsList = vi.fn();
vi.mock('@/api/buildings', () => ({
  buildingsApi: {
    list: (...args: unknown[]) => mockBuildingsList(...args),
  },
}));

vi.mock('@/utils/formatters', () => ({
  cn: (...classes: (string | undefined | false)[]) => classes.filter(Boolean).join(' '),
}));

const mockPublications = [
  {
    id: 'pub-1',
    building_id: null,
    source_system: 'batiscan',
    source_mission_id: 'mission-001',
    current_version: 1,
    match_state: 'needs_review',
    match_key: '12345',
    match_key_type: 'egid',
    mission_type: 'asbestos_full',
    report_pdf_url: 'https://example.com/report.pdf',
    structured_summary: {
      pollutants_found: 3,
      fach_urgency: 'high',
      zones: 5,
    },
    annexes: [],
    payload_hash: 'abc123',
    published_at: '2026-03-20T10:00:00Z',
    is_immutable: false,
    created_at: '2026-03-20T10:00:00Z',
  },
  {
    id: 'pub-2',
    building_id: null,
    source_system: 'external-lab',
    source_mission_id: 'mission-002',
    current_version: 1,
    match_state: 'unmatched',
    match_key: null,
    match_key_type: null,
    mission_type: 'pcb',
    report_pdf_url: null,
    structured_summary: null,
    annexes: [],
    payload_hash: 'def456',
    published_at: '2026-03-18T15:30:00Z',
    is_immutable: false,
    created_at: '2026-03-18T15:30:00Z',
  },
];

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <AdminDiagnosticReview />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('AdminDiagnosticReview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthStore.mockImplementation((selector: (s: { user: { role: string } }) => unknown) =>
      selector({ user: { role: 'admin' } }),
    );
  });

  afterEach(cleanup);

  it('shows access denied for non-admin users', () => {
    mockAuthStore.mockImplementation((selector: (s: { user: { role: string } }) => unknown) =>
      selector({ user: { role: 'diagnostician' } }),
    );
    renderPage();
    expect(screen.getByTestId('diag-review-access-denied')).toBeInTheDocument();
  });

  it('shows loading state', () => {
    mockGetUnmatched.mockReturnValue(new Promise(() => {})); // never resolves
    renderPage();
    expect(screen.getByTestId('diag-review-loading')).toBeInTheDocument();
  });

  it('shows empty state when no unmatched publications', async () => {
    mockGetUnmatched.mockResolvedValue([]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('diag-review-empty')).toBeInTheDocument();
    });
  });

  it('renders publication cards with badges and identifiers', async () => {
    mockGetUnmatched.mockResolvedValue(mockPublications);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('diag-review-list')).toBeInTheDocument();
    });
    expect(screen.getByTestId('diag-review-card-pub-1')).toBeInTheDocument();
    expect(screen.getByTestId('diag-review-card-pub-2')).toBeInTheDocument();
    expect(screen.getByTestId('diag-review-count')).toHaveTextContent('2');

    // Check badges rendered (i18n keys as text since we mock t)
    const matchStates = screen.getAllByTestId('diag-review-match-state');
    expect(matchStates).toHaveLength(2);

    const missionTypes = screen.getAllByTestId('diag-review-mission-type');
    expect(missionTypes).toHaveLength(2);
  });

  it('shows structured summary when available', async () => {
    mockGetUnmatched.mockResolvedValue(mockPublications);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('diag-review-list')).toBeInTheDocument();
    });
    // pub-1 has structured_summary, pub-2 does not
    const summaries = screen.getAllByTestId('diag-review-summary');
    expect(summaries).toHaveLength(1);
  });

  it('opens match panel on button click', async () => {
    mockGetUnmatched.mockResolvedValue([mockPublications[0]]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('diag-review-match-btn')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('diag-review-match-btn'));
    expect(screen.getByTestId('diag-review-match-panel')).toBeInTheDocument();
    expect(screen.getByTestId('diag-review-building-search')).toBeInTheDocument();
  });

  it('closes match panel on cancel', async () => {
    mockGetUnmatched.mockResolvedValue([mockPublications[0]]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('diag-review-match-btn')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('diag-review-match-btn'));
    expect(screen.getByTestId('diag-review-match-panel')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('diag-review-match-cancel'));
    expect(screen.queryByTestId('diag-review-match-panel')).not.toBeInTheDocument();
  });

  it('searches for buildings when typing', async () => {
    mockGetUnmatched.mockResolvedValue([mockPublications[0]]);
    mockBuildingsList.mockResolvedValue({
      items: [{ id: 'b1', address: 'Rue de Lausanne 10', postal_code: '1000', city: 'Lausanne', egid: 12345 }],
      total: 1,
    });
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('diag-review-match-btn')).toBeInTheDocument();
    });
    fireEvent.click(screen.getByTestId('diag-review-match-btn'));
    const input = screen.getByTestId('diag-review-building-search');
    fireEvent.change(input, { target: { value: 'Lausanne' } });
    await waitFor(() => {
      expect(mockBuildingsList).toHaveBeenCalledWith({ search: 'Lausanne', size: 8 });
    });
  });

  it('shows PDF link when report_pdf_url is present', async () => {
    mockGetUnmatched.mockResolvedValue([mockPublications[0]]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('diag-review-card-pub-1')).toBeInTheDocument();
    });
    const pdfLinks = screen.getAllByTestId('diag-review-pdf-link');
    expect(pdfLinks).toHaveLength(1);
  });

  it('shows identifiers section with match key', async () => {
    mockGetUnmatched.mockResolvedValue([mockPublications[0]]);
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId('diag-review-card-pub-1')).toBeInTheDocument();
    });
    const identifiers = screen.getAllByTestId('diag-review-identifiers');
    expect(identifiers).toHaveLength(1);
    expect(identifiers[0]).toHaveTextContent('12345');
  });
});
