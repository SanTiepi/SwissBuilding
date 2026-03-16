import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { CommandPalette } from '../CommandPalette';

const mockT = vi.fn((key: string) => key);
const mockSetLocale = vi.fn();
vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: mockT,
    locale: 'fr',
    setLocale: mockSetLocale,
  }),
}));

const mockNavigate = vi.fn();
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual<typeof import('react-router-dom')>('react-router-dom');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

const mockSearch = vi.fn();
vi.mock('@/api/search', () => ({
  searchApi: {
    search: (...args: unknown[]) => mockSearch(...args),
  },
}));

vi.mock('@/hooks/useDebouncedValue', () => ({
  useDebouncedValue: (value: string) => value,
}));

const mockBuildingsList = vi.fn();
vi.mock('@/api/buildings', () => ({
  buildingsApi: {
    list: (...args: unknown[]) => mockBuildingsList(...args),
  },
}));

vi.mock('@/components/SearchEvidencePreview', () => ({
  SearchEvidencePreview: () => <div data-testid="evidence-preview" />,
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

/** Helper: set up a successful cross-entity search returning mixed result types */
function mockCrossEntityResults() {
  mockSearch.mockResolvedValue({
    results: [
      {
        id: 'b1',
        index: 'buildings',
        title: 'Rue de Lausanne 10',
        subtitle: '1000 Lausanne (VD)',
        url: '/buildings/b1',
      },
      {
        id: 'd1',
        index: 'diagnostics',
        title: 'Diag Amiante 2024',
        subtitle: 'Building b1 - Amiante',
        url: '/diagnostics/d1',
      },
      { id: 'doc1', index: 'documents', title: 'Rapport lab', subtitle: 'PDF 2.3MB', url: '/documents/doc1' },
    ],
  });
}

describe('CommandPalette', () => {
  beforeEach(() => {
    mockNavigate.mockReset();
    mockSearch.mockReset();
    mockBuildingsList.mockReset();
    mockT.mockClear();
    mockSetLocale.mockClear();
    vi.stubGlobal('requestAnimationFrame', (cb: FrameRequestCallback) => {
      cb(0);
      return 0;
    });
    vi.stubGlobal('cancelAnimationFrame', vi.fn());
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    cleanup();
  });

  it('falls back to building search when cross-entity search is unavailable', async () => {
    mockSearch.mockRejectedValue(new Error('search down'));
    mockBuildingsList.mockResolvedValue({
      items: [
        {
          id: 'b1',
          address: 'Rue de Lausanne 10',
          postal_code: '1000',
          city: 'Lausanne',
          canton: 'VD',
        },
      ],
    });

    render(<CommandPalette open onClose={vi.fn()} />, { wrapper });

    fireEvent.change(screen.getByRole('textbox', { name: 'nav.search' }), { target: { value: 'laus' } });

    expect(await screen.findByText('Rue de Lausanne 10')).toBeInTheDocument();
    expect(screen.queryByText('search.load_error')).not.toBeInTheDocument();
  });

  it('shows explicit error state when search and fallback both fail', async () => {
    mockSearch.mockRejectedValue(new Error('search down'));
    mockBuildingsList.mockRejectedValue(new Error('buildings down'));

    render(<CommandPalette open onClose={vi.fn()} />, { wrapper });

    fireEvent.change(screen.getByRole('textbox', { name: 'nav.search' }), { target: { value: 'laus' } });

    expect(await screen.findByText('search.load_error')).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.queryByText('search.no_results')).not.toBeInTheDocument();
    });
  });

  it('renders grouped results from successful cross-entity search', async () => {
    mockCrossEntityResults();

    render(<CommandPalette open onClose={vi.fn()} />, { wrapper });
    fireEvent.change(screen.getByRole('textbox', { name: 'nav.search' }), { target: { value: 'lausanne' } });

    // All three result types rendered
    expect(await screen.findByText('Rue de Lausanne 10')).toBeInTheDocument();
    expect(screen.getByText('Diag Amiante 2024')).toBeInTheDocument();
    expect(screen.getByText('Rapport lab')).toBeInTheDocument();

    // Group headers present
    expect(screen.getByRole('group', { name: 'search.filter_buildings' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'search.filter_diagnostics' })).toBeInTheDocument();
    expect(screen.getByRole('group', { name: 'search.filter_documents' })).toBeInTheDocument();
  });

  it('navigates to selected result on Enter and closes palette', async () => {
    mockCrossEntityResults();
    const onClose = vi.fn();

    render(<CommandPalette open onClose={onClose} />, { wrapper });
    const input = screen.getByRole('textbox', { name: 'nav.search' });
    fireEvent.change(input, { target: { value: 'lausanne' } });

    await screen.findByText('Rue de Lausanne 10');

    // First result is selected by default — press Enter
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockNavigate).toHaveBeenCalledWith('/buildings/b1');
    expect(onClose).toHaveBeenCalled();
  });

  it('supports keyboard navigation (ArrowDown/ArrowUp) across results', async () => {
    mockCrossEntityResults();
    const onClose = vi.fn();

    render(<CommandPalette open onClose={onClose} />, { wrapper });
    const input = screen.getByRole('textbox', { name: 'nav.search' });
    fireEvent.change(input, { target: { value: 'lausanne' } });

    await screen.findByText('Rue de Lausanne 10');

    // Move down to second result (diagnostic)
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    // Move down to third result (document)
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    // Press Enter — should navigate to documents/doc1
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockNavigate).toHaveBeenCalledWith('/documents/doc1');
    expect(onClose).toHaveBeenCalled();
  });

  it('closes on Escape key', async () => {
    const onClose = vi.fn();
    render(<CommandPalette open onClose={onClose} />, { wrapper });

    const input = screen.getByRole('textbox', { name: 'nav.search' });
    fireEvent.keyDown(input, { key: 'Escape' });

    expect(onClose).toHaveBeenCalledOnce();
  });

  it('applies type filter when filter pill is clicked', async () => {
    mockCrossEntityResults();

    render(<CommandPalette open onClose={vi.fn()} />, { wrapper });
    const input = screen.getByRole('textbox', { name: 'nav.search' });
    fireEvent.change(input, { target: { value: 'lausanne' } });

    await screen.findByText('Rue de Lausanne 10');

    // Filter pill and group header both show this text — select the button element
    const diagButtons = screen.getAllByText('search.filter_diagnostics').filter((el) => el.tagName === 'BUTTON');
    fireEvent.click(diagButtons[0]);

    // searchApi.search should be called again with the diagnostics filter
    await waitFor(() => {
      const calls = mockSearch.mock.calls;
      const lastCall = calls[calls.length - 1];
      expect(lastCall[1]).toBe('diagnostics');
    });
  });

  it('dialog has aria-modal="true"', () => {
    render(<CommandPalette open onClose={vi.fn()} />, { wrapper });
    const dialog = screen.getByRole('dialog');
    expect(dialog).toHaveAttribute('aria-modal', 'true');
  });

  it('Tab does not preventDefault when no building result is selected', async () => {
    // Search returns only documents (no building), so Tab should not be intercepted
    mockSearch.mockResolvedValue({
      results: [
        { id: 'doc1', index: 'documents', title: 'Rapport lab', subtitle: 'PDF 2.3MB', url: '/documents/doc1' },
      ],
    });

    render(<CommandPalette open onClose={vi.fn()} />, { wrapper });
    const input = screen.getByRole('textbox', { name: 'nav.search' });
    fireEvent.change(input, { target: { value: 'rapport' } });

    await screen.findByText('Rapport lab');

    // Tab should NOT be prevented — verify by checking that the event is not default-prevented
    const tabEvent = new KeyboardEvent('keydown', { key: 'Tab', bubbles: true, cancelable: true });
    const prevented = !input.dispatchEvent(tabEvent);
    expect(prevented).toBe(false);
  });

  it('Tab is prevented when building result is selected to open quick actions', async () => {
    mockSearch.mockResolvedValue({
      results: [
        { id: 'b1', index: 'buildings', title: 'Rue du Marche 5', subtitle: '1003 Lausanne', url: '/buildings/b1' },
      ],
    });

    render(<CommandPalette open onClose={vi.fn()} />, { wrapper });
    const input = screen.getByRole('textbox', { name: 'nav.search' });
    fireEvent.change(input, { target: { value: 'marche' } });

    await screen.findByText('Rue du Marche 5');

    // Tab on a building result opens quick actions (preventDefault)
    fireEvent.keyDown(input, { key: 'Tab' });
    expect(screen.getByText('search.quick_actions')).toBeInTheDocument();
  });

  it('opens quick actions via Tab when a building result is selected', async () => {
    mockSearch.mockResolvedValue({
      results: [
        { id: 'b1', index: 'buildings', title: 'Rue du Marche 5', subtitle: '1003 Lausanne', url: '/buildings/b1' },
      ],
    });

    const onClose = vi.fn();
    render(<CommandPalette open onClose={onClose} />, { wrapper });
    const input = screen.getByRole('textbox', { name: 'nav.search' });
    fireEvent.change(input, { target: { value: 'marche' } });

    await screen.findByText('Rue du Marche 5');

    // Tab opens quick actions panel
    fireEvent.keyDown(input, { key: 'Tab' });

    // Quick actions panel should be visible with action labels
    expect(screen.getByText('search.quick_actions')).toBeInTheDocument();

    // Navigate down in quick actions and select "timeline" (index 2)
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'ArrowDown' });
    fireEvent.keyDown(input, { key: 'Enter' });

    expect(mockNavigate).toHaveBeenCalledWith('/buildings/b1/timeline');
    expect(onClose).toHaveBeenCalled();
  });
});
