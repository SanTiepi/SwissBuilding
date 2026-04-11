import { describe, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { FieldObservationForm } from '../FieldObservationForm';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/store/toastStore', () => ({
  toast: vi.fn(),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: (selector: (s: Record<string, unknown>) => unknown) =>
    selector({ user: { id: 'u1', email: 'test@test.com' }, token: 'tok' }),
}));

const mockCreate = vi.fn();
const mockCreateGeneral = vi.fn();
vi.mock('@/api/fieldObservations', () => ({
  fieldObservationsApi: {
    create: (...args: unknown[]) => mockCreate(...args),
    createGeneral: (...args: unknown[]) => mockCreateGeneral(...args),
    list: vi.fn(),
    get: vi.fn(),
    update: vi.fn(),
    verify: vi.fn(),
    summary: vi.fn(),
    search: vi.fn(),
    patterns: vi.fn(),
    upvote: vi.fn(),
    verifyAdmin: vi.fn(),
  },
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe('FieldObservationForm', () => {
  it('renders form fields', () => {
    render(<FieldObservationForm buildingId="b1" />, { wrapper });

    // Title input should be present
    expect(screen.getByPlaceholderText('field_memory.title_placeholder')).toBeInTheDocument();
    // Mode toggle buttons
    expect(screen.getByText('field_memory.quick_note')).toBeInTheDocument();
    expect(screen.getByText('field_memory.detailed')).toBeInTheDocument();
    // Submit button
    expect(screen.getByText('field_memory.add_observation')).toBeInTheDocument();
  });

  it('shows detailed fields when detailed mode is clicked', () => {
    render(<FieldObservationForm buildingId="b1" />, { wrapper });

    fireEvent.click(screen.getByText('field_memory.detailed'));

    // Confidence radio labels should appear
    expect(screen.getByText('field_memory.confidence_certain')).toBeInTheDocument();
    expect(screen.getByText('field_memory.confidence_likely')).toBeInTheDocument();
    // Tags placeholder
    expect(screen.getByPlaceholderText('field_memory.tags_placeholder')).toBeInTheDocument();
  });

  it('submits with building_id', async () => {
    mockCreate.mockResolvedValueOnce({
      id: 'obs-1',
      title: 'Test obs',
      observation_type: 'tip',
      confidence: 'likely',
      upvotes: 0,
      is_verified: false,
    });

    const onSuccess = vi.fn();
    render(<FieldObservationForm buildingId="b1" onSuccess={onSuccess} />, { wrapper });

    const titleInput = screen.getByPlaceholderText('field_memory.title_placeholder');
    fireEvent.change(titleInput, { target: { value: 'PCB in joints' } });
    fireEvent.click(screen.getByText('field_memory.add_observation'));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith('b1', expect.objectContaining({ title: 'PCB in joints' }));
    });
  });

  it('submits general observation without building_id', async () => {
    mockCreateGeneral.mockResolvedValueOnce({
      id: 'obs-2',
      title: 'General tip',
      observation_type: 'tip',
      confidence: 'likely',
      upvotes: 0,
      is_verified: false,
    });

    render(<FieldObservationForm />, { wrapper });

    const titleInput = screen.getByPlaceholderText('field_memory.title_placeholder');
    fireEvent.change(titleInput, { target: { value: 'General tip' } });
    fireEvent.click(screen.getByText('field_memory.add_observation'));

    await waitFor(() => {
      expect(mockCreateGeneral).toHaveBeenCalledWith(expect.objectContaining({ title: 'General tip' }));
    });
  });
});
