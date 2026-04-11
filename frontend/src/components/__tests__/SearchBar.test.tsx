import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { SearchBar } from '../SearchBar';

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

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('SearchBar', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearch.mockResolvedValue({ query: '', results: [], total: 0 });
  });

  afterEach(cleanup);

  it('renders search input', () => {
    render(<SearchBar />, { wrapper });
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('shows keyboard shortcut hint', () => {
    render(<SearchBar />, { wrapper });
    expect(screen.getByText('⌘K')).toBeInTheDocument();
  });

  it('calls search API on input', async () => {
    mockSearch.mockResolvedValue({
      query: 'test',
      results: [
        { index: 'buildings', id: '1', title: 'Rue du Test', subtitle: '1000 Lausanne', url: '/buildings/1', score: 0.9 },
      ],
      total: 1,
    });

    render(<SearchBar />, { wrapper });
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'test' } });

    await waitFor(() => {
      expect(mockSearch).toHaveBeenCalledWith('test', undefined, 6);
    });
  });

  it('shows dropdown results', async () => {
    mockSearch.mockResolvedValue({
      query: 'lausanne',
      results: [
        { index: 'buildings', id: '1', title: 'Rue de Lausanne 10', subtitle: '1000 Lausanne', url: '/buildings/1', score: 0.9 },
      ],
      total: 1,
    });

    render(<SearchBar />, { wrapper });
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'lausanne' } });

    await waitFor(() => {
      expect(screen.getByText('Rue de Lausanne 10')).toBeInTheDocument();
    });
  });

  it('navigates on result click', async () => {
    mockSearch.mockResolvedValue({
      query: 'test',
      results: [
        { index: 'buildings', id: '1', title: 'Building A', subtitle: 'Sub A', url: '/buildings/1', score: 0.9 },
      ],
      total: 1,
    });

    render(<SearchBar />, { wrapper });
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'test' } });

    await waitFor(() => {
      expect(screen.getByText('Building A')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Building A'));
    expect(mockNavigate).toHaveBeenCalledWith('/buildings/1');
  });

  it('navigates on Enter key', async () => {
    mockSearch.mockResolvedValue({
      query: 'test',
      results: [
        { index: 'buildings', id: '2', title: 'Building B', subtitle: 'Sub B', url: '/buildings/2', score: 0.8 },
      ],
      total: 1,
    });

    render(<SearchBar />, { wrapper });
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'test' } });

    await waitFor(() => {
      expect(screen.getByText('Building B')).toBeInTheDocument();
    });

    fireEvent.keyDown(input, { key: 'Enter' });
    expect(mockNavigate).toHaveBeenCalledWith('/buildings/2');
  });

  it('closes dropdown on Escape', async () => {
    mockSearch.mockResolvedValue({
      query: 'test',
      results: [
        { index: 'buildings', id: '1', title: 'Building C', subtitle: 'Sub C', url: '/buildings/1', score: 0.9 },
      ],
      total: 1,
    });

    render(<SearchBar />, { wrapper });
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'test' } });

    await waitFor(() => {
      expect(screen.getByText('Building C')).toBeInTheDocument();
    });

    fireEvent.keyDown(input, { key: 'Escape' });
    expect(screen.queryByText('Building C')).not.toBeInTheDocument();
  });

  it('clears input on X button click', async () => {
    render(<SearchBar />, { wrapper });
    const input = screen.getByRole('textbox');
    fireEvent.change(input, { target: { value: 'test query' } });

    await waitFor(() => {
      const clearBtn = screen.getByLabelText('form.clear');
      expect(clearBtn).toBeInTheDocument();
      fireEvent.click(clearBtn);
    });

    expect(input).toHaveValue('');
  });

  it('does not search for single character', async () => {
    render(<SearchBar />, { wrapper });
    fireEvent.change(screen.getByRole('textbox'), { target: { value: 'a' } });

    // Wait a tick and verify search was NOT called
    await new Promise((r) => setTimeout(r, 50));
    expect(mockSearch).not.toHaveBeenCalled();
  });
});
