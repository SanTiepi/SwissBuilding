import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ContradictionCard } from '../ContradictionCard';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
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

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('ContradictionCard', () => {
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

  it('renders explicit error state when summary query fails', async () => {
    mockSummary.mockRejectedValue(new Error('boom'));
    render(<ContradictionCard buildingId="b1" />, { wrapper });

    expect(await screen.findByText('app.loading_error')).toBeInTheDocument();
  });

  it('renders no contradictions state', async () => {
    mockSummary.mockResolvedValue({ total: 0, by_type: {}, resolved: 0, unresolved: 0 });
    render(<ContradictionCard buildingId="b1" />, { wrapper });

    expect(await screen.findByText('contradiction.none')).toBeInTheDocument();
  });

  it('renders type pills and progress bar when contradictions exist', async () => {
    mockSummary.mockResolvedValue({
      total: 3,
      by_type: { conflicting_sample_results: 2, duplicate_samples: 1 },
      resolved: 1,
      unresolved: 2,
    });
    render(<ContradictionCard buildingId="b1" />, { wrapper });

    expect(await screen.findByText('contradiction.type.conflicting_sample_results')).toBeInTheDocument();
    expect(screen.getByText('contradiction.type.duplicate_samples')).toBeInTheDocument();
    expect(screen.getByText('1 contradiction.resolved')).toBeInTheDocument();
    expect(screen.getByText('2 contradiction.unresolved')).toBeInTheDocument();
  });

  it('shows view all button when contradictions exist', async () => {
    mockSummary.mockResolvedValue({
      total: 2,
      by_type: { conflicting_sample_results: 2 },
      resolved: 0,
      unresolved: 2,
    });
    render(<ContradictionCard buildingId="b1" />, { wrapper });

    expect(await screen.findByText('contradiction.view_all')).toBeInTheDocument();
  });

  it('toasts when contradiction scan fails', async () => {
    mockSummary.mockResolvedValue({
      total: 1,
      by_type: { conflicting_sample_results: 1 },
      resolved: 0,
      unresolved: 1,
    });
    mockDetect.mockRejectedValue(new Error('scan failed'));

    render(<ContradictionCard buildingId="b1" />, { wrapper });
    const button = await screen.findByText('contradiction.scan');
    fireEvent.click(button);

    await waitFor(() => {
      expect(mockToast).toHaveBeenCalledWith('scan failed');
    });
  });

  it('expands to full panel when view all is clicked', async () => {
    mockSummary.mockResolvedValue({
      total: 2,
      by_type: { conflicting_sample_results: 2 },
      resolved: 0,
      unresolved: 2,
    });
    mockList.mockResolvedValue({
      items: [
        {
          id: 'i1',
          building_id: 'b1',
          issue_type: 'contradiction',
          severity: 'high',
          status: 'open',
          entity_type: 'sample',
          entity_id: 'e1',
          field_name: 'conflicting_sample_results',
          description: 'Test contradiction',
          suggestion: 'Fix it',
          resolved_by: null,
          resolved_at: null,
          resolution_notes: null,
          detected_by: 'contradiction_detector',
          created_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      size: 100,
      pages: 1,
    });

    render(<ContradictionCard buildingId="b1" />, { wrapper });
    const viewAllBtn = await screen.findByText('contradiction.view_all');
    fireEvent.click(viewAllBtn);

    // Should now show the collapse button and panel content
    expect(await screen.findByText('contradiction.collapse')).toBeInTheDocument();
  });
});
