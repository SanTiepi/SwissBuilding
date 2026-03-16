import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ContradictionPanel } from '../ContradictionPanel';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string, params?: Record<string, string | number>) => {
      if (params) {
        let val = key;
        Object.entries(params).forEach(([k, v]) => {
          val = val.replace(`{${k}}`, String(v));
        });
        return val;
      }
      return key;
    },
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockToast = vi.fn();
vi.mock('@/store/toastStore', () => ({
  toast: (...args: unknown[]) => mockToast(...args),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ user: { id: 'u1', email: 'test@test.com' }, token: 'tok' }),
}));

const mockSummary = vi.fn();
const mockDetect = vi.fn();
const mockList = vi.fn();
const mockUpdate = vi.fn();
vi.mock('@/api/contradictions', () => ({
  contradictionsApi: {
    summary: (...args: unknown[]) => mockSummary(...args),
    detect: (...args: unknown[]) => mockDetect(...args),
    list: (...args: unknown[]) => mockList(...args),
    get: vi.fn(),
    update: (...args: unknown[]) => mockUpdate(...args),
  },
}));

const MOCK_ISSUE = {
  id: 'i1',
  building_id: 'b1',
  issue_type: 'contradiction',
  severity: 'high',
  status: 'open',
  entity_type: 'sample',
  entity_id: 'e1e1e1e1-0000-0000-0000-000000000000',
  field_name: 'conflicting_sample_results',
  description: 'Conflicting results for asbestos in Kitchen',
  suggestion: 'Review samples for this location',
  resolved_by: null,
  resolved_at: null,
  resolution_notes: null,
  detected_by: 'contradiction_detector',
  created_at: '2026-01-15T10:00:00Z',
};

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('ContradictionPanel', () => {
  beforeEach(() => {
    mockSummary.mockReset();
    mockDetect.mockReset();
    mockList.mockReset();
    mockUpdate.mockReset();
    mockToast.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('shows loading state', () => {
    mockSummary.mockReturnValue(new Promise(() => {}));
    mockList.mockReturnValue(new Promise(() => {}));
    render(<ContradictionPanel buildingId="b1" />, { wrapper });

    expect(screen.getByText('contradiction.title')).toBeInTheDocument();
  });

  it('shows empty state when no contradictions', async () => {
    mockSummary.mockResolvedValue({ total: 0, by_type: {}, resolved: 0, unresolved: 0 });
    mockList.mockResolvedValue({ items: [], total: 0, page: 1, size: 100, pages: 0 });

    render(<ContradictionPanel buildingId="b1" />, { wrapper });

    expect(await screen.findByText('contradiction.none')).toBeInTheDocument();
  });

  it('renders summary cards and issue list', async () => {
    mockSummary.mockResolvedValue({
      total: 2,
      by_type: { conflicting_sample_results: 1, duplicate_samples: 1 },
      resolved: 1,
      unresolved: 1,
    });
    mockList.mockResolvedValue({
      items: [MOCK_ISSUE],
      total: 1,
      page: 1,
      size: 100,
      pages: 1,
    });

    render(<ContradictionPanel buildingId="b1" />, { wrapper });

    // Summary
    expect(await screen.findByText('50%')).toBeInTheDocument(); // resolution rate
    // Issue row
    expect(await screen.findByText('Conflicting results for asbestos in Kitchen')).toBeInTheDocument();
  });

  it('expands issue detail on click', async () => {
    mockSummary.mockResolvedValue({
      total: 1,
      by_type: { conflicting_sample_results: 1 },
      resolved: 0,
      unresolved: 1,
    });
    mockList.mockResolvedValue({
      items: [MOCK_ISSUE],
      total: 1,
      page: 1,
      size: 100,
      pages: 1,
    });

    render(<ContradictionPanel buildingId="b1" />, { wrapper });

    const row = await screen.findByText('Conflicting results for asbestos in Kitchen');
    fireEvent.click(row);

    // Detail section should show
    expect(await screen.findByText('contradiction.conflicting_data')).toBeInTheDocument();
    expect(screen.getByText('contradiction.resolution_workflow')).toBeInTheDocument();
    expect(screen.getByText('contradiction.action_investigate')).toBeInTheDocument();
  });

  it('calls detect mutation on scan button click', async () => {
    mockSummary.mockResolvedValue({ total: 0, by_type: {}, resolved: 0, unresolved: 0 });
    mockList.mockResolvedValue({ items: [], total: 0, page: 1, size: 100, pages: 0 });
    mockDetect.mockResolvedValue([]);

    render(<ContradictionPanel buildingId="b1" />, { wrapper });

    const scanBtn = await screen.findByText('contradiction.scan');
    fireEvent.click(scanBtn);

    await waitFor(() => {
      expect(mockDetect).toHaveBeenCalledWith('b1');
    });
  });

  it('updates issue status when investigate is clicked', async () => {
    mockSummary.mockResolvedValue({
      total: 1,
      by_type: { conflicting_sample_results: 1 },
      resolved: 0,
      unresolved: 1,
    });
    mockList.mockResolvedValue({
      items: [MOCK_ISSUE],
      total: 1,
      page: 1,
      size: 100,
      pages: 1,
    });
    mockUpdate.mockResolvedValue({ ...MOCK_ISSUE, status: 'investigating' });

    render(<ContradictionPanel buildingId="b1" />, { wrapper });

    // Expand
    const row = await screen.findByText('Conflicting results for asbestos in Kitchen');
    fireEvent.click(row);

    // Click investigate
    const investigateBtn = await screen.findByText('contradiction.action_investigate');
    fireEvent.click(investigateBtn);

    await waitFor(() => {
      expect(mockUpdate).toHaveBeenCalledWith('b1', 'i1', { status: 'investigating' });
    });
  });

  it('shows filter panel when filter button is clicked', async () => {
    mockSummary.mockResolvedValue({ total: 0, by_type: {}, resolved: 0, unresolved: 0 });
    mockList.mockResolvedValue({ items: [], total: 0, page: 1, size: 100, pages: 0 });

    render(<ContradictionPanel buildingId="b1" />, { wrapper });

    const filterBtn = await screen.findByText('common.filter');
    fireEvent.click(filterBtn);

    expect(screen.getByText('contradiction.filter_type')).toBeInTheDocument();
    expect(screen.getByText('contradiction.filter_status')).toBeInTheDocument();
    expect(screen.getByText('contradiction.filter_severity')).toBeInTheDocument();
  });
});
