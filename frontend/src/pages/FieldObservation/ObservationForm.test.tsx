import { describe, expect, it, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import ObservationForm from './ObservationForm';

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
vi.mock('@/api/fieldObservations', () => ({
  fieldObservationsApi: {
    create: (...args: unknown[]) => mockCreate(...args),
    createGeneral: vi.fn(),
    list: vi.fn(),
    get: vi.fn(),
    update: vi.fn(),
    verify: vi.fn(),
    summary: vi.fn(),
    search: vi.fn(),
    patterns: vi.fn(),
    upvote: vi.fn(),
    verifyAdmin: vi.fn(),
    getRiskScore: vi.fn(),
    computeRiskScore: vi.fn(),
  },
}));

function renderForm() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={['/buildings/b1/observe']}>
        <Routes>
          <Route path="/buildings/:buildingId/observe" element={<ObservationForm />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('ObservationForm (mobile)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders step 1 — building element selector', () => {
    renderForm();
    expect(screen.getByTestId('building-element-selector')).toBeInTheDocument();
    expect(screen.getByTestId('next-step')).toBeInTheDocument();
  });

  it('next button disabled until element selected', () => {
    renderForm();
    expect(screen.getByTestId('next-step')).toBeDisabled();
  });

  it('enables next after element selection', () => {
    renderForm();
    fireEvent.click(screen.getByTestId('element-roof'));
    expect(screen.getByTestId('next-step')).not.toBeDisabled();
  });

  it('navigates to step 2 — condition picker', () => {
    renderForm();
    fireEvent.click(screen.getByTestId('element-walls'));
    fireEvent.click(screen.getByTestId('next-step'));
    expect(screen.getByTestId('condition-picker')).toBeInTheDocument();
    expect(screen.getByTestId('risk-flag-checkboxes')).toBeInTheDocument();
  });

  it('condition picker shows A/B/C/D buttons', () => {
    renderForm();
    fireEvent.click(screen.getByTestId('element-roof'));
    fireEvent.click(screen.getByTestId('next-step'));
    expect(screen.getByTestId('condition-good')).toBeInTheDocument();
    expect(screen.getByTestId('condition-fair')).toBeInTheDocument();
    expect(screen.getByTestId('condition-poor')).toBeInTheDocument();
    expect(screen.getByTestId('condition-critical')).toBeInTheDocument();
  });

  it('risk flags are toggleable', () => {
    renderForm();
    fireEvent.click(screen.getByTestId('element-roof'));
    fireEvent.click(screen.getByTestId('next-step'));
    const moldBtn = screen.getByTestId('flag-mold');
    fireEvent.click(moldBtn);
    // Toggle on — check it has the active class
    expect(moldBtn.className).toContain('border-red');
    // Toggle off
    fireEvent.click(moldBtn);
    expect(moldBtn.className).not.toContain('border-red');
  });

  it('navigates to step 3 — photo capture', () => {
    renderForm();
    fireEvent.click(screen.getByTestId('element-roof'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('condition-fair'));
    fireEvent.click(screen.getByTestId('next-step'));
    expect(screen.getByTestId('photo-capture-widget')).toBeInTheDocument();
  });

  it('navigates to step 4 — details (voice + name)', () => {
    renderForm();
    fireEvent.click(screen.getByTestId('element-roof'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('condition-fair'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('next-step'));
    expect(screen.getByTestId('voice-input')).toBeInTheDocument();
    expect(screen.getByTestId('observer-name-input')).toBeInTheDocument();
  });

  it('navigates to step 5 — preview screen', () => {
    renderForm();
    // Step through
    fireEvent.click(screen.getByTestId('element-facade'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('condition-poor'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('next-step'));
    expect(screen.getByTestId('preview-screen')).toBeInTheDocument();
    expect(screen.getByTestId('submit-observation')).toBeInTheDocument();
  });

  it('back button navigates to previous step', () => {
    renderForm();
    fireEvent.click(screen.getByTestId('element-roof'));
    fireEvent.click(screen.getByTestId('next-step'));
    expect(screen.getByTestId('condition-picker')).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('back-button'));
    expect(screen.getByTestId('building-element-selector')).toBeInTheDocument();
  });

  it('submits observation and shows done screen', async () => {
    mockCreate.mockResolvedValueOnce({
      id: 'obs-1',
      title: 'roof — poor',
      observation_type: 'visual_inspection',
      condition_assessment: 'poor',
    });

    renderForm();
    // Walk through all steps
    fireEvent.click(screen.getByTestId('element-roof'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('condition-poor'));
    fireEvent.click(screen.getByTestId('flag-crack'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('submit-observation'));

    await waitFor(() => {
      expect(mockCreate).toHaveBeenCalledWith(
        'b1',
        expect.objectContaining({
          condition_assessment: 'poor',
          risk_flags: ['crack'],
          observation_type: 'visual_inspection',
        }),
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId('done-screen')).toBeInTheDocument();
    });
  });

  it('done screen has new observation button', async () => {
    mockCreate.mockResolvedValueOnce({ id: 'obs-2' });
    renderForm();
    fireEvent.click(screen.getByTestId('element-roof'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('condition-good'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('submit-observation'));

    await waitFor(() => {
      expect(screen.getByTestId('done-screen')).toBeInTheDocument();
    });

    expect(screen.getByTestId('new-observation-button')).toBeInTheDocument();
  });

  it('notes textarea accepts text input', () => {
    renderForm();
    fireEvent.click(screen.getByTestId('element-roof'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('condition-fair'));
    fireEvent.click(screen.getByTestId('next-step'));
    fireEvent.click(screen.getByTestId('next-step'));
    const textarea = screen.getByTestId('notes-textarea');
    fireEvent.change(textarea, { target: { value: 'Visible crack on north wall' } });
    expect(textarea).toHaveValue('Visible crack on north wall');
  });
});
