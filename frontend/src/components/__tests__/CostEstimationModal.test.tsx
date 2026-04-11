import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { CostPredictionResponse } from '@/api/costPrediction';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockPredict = vi.fn();
const mockExportPdf = vi.fn();

vi.mock('@/hooks/useCostPrediction', () => ({
  useCostPrediction: () => mockPredict(),
  useCostPredictionPdf: () => mockExportPdf(),
}));

vi.mock('@/store/toastStore', () => ({
  toast: vi.fn(),
}));

// Lazy import so mocks are in place
const { CostEstimationModal } = await import('@/components/CostEstimationModal');

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const MOCK_RESULT: CostPredictionResponse = {
  pollutant_type: 'asbestos',
  material_type: 'flocage',
  surface_m2: 100,
  cost_min: 15000,
  cost_median: 25000,
  cost_max: 35000,
  duration_days: 30,
  complexity: 'complexe',
  method: 'depose',
  canton_coefficient: 1.0,
  accessibility_coefficient: 1.0,
  breakdown: [
    { label: 'Depose / Intervention', percentage: 45, amount_min: 6750, amount_median: 11250, amount_max: 15750 },
    { label: 'Traitement dechets', percentage: 20, amount_min: 3000, amount_median: 5000, amount_max: 7000 },
    { label: 'Analyses controle', percentage: 8, amount_min: 1200, amount_median: 2000, amount_max: 2800 },
    { label: 'Remise en etat', percentage: 22, amount_min: 3300, amount_median: 5500, amount_max: 7700 },
    { label: 'Frais generaux', percentage: 5, amount_min: 750, amount_median: 1250, amount_max: 1750 },
  ],
  disclaimer: 'Estimation indicative basee sur les moyennes du marche suisse.',
};

function makeMutateMock(overrides: Record<string, unknown> = {}) {
  return {
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    ...overrides,
  };
}

describe('CostEstimationModal', () => {
  let mutateFn: ReturnType<typeof vi.fn>;
  let pdfMutateFn: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    mutateFn = vi.fn();
    pdfMutateFn = vi.fn();
    mockPredict.mockReturnValue(makeMutateMock({ mutate: mutateFn }));
    mockExportPdf.mockReturnValue(makeMutateMock({ mutate: pdfMutateFn }));
  });

  afterEach(() => {
    cleanup();
    vi.clearAllMocks();
  });

  it('renders nothing when open=false', () => {
    const { container } = render(
      <CostEstimationModal open={false} onClose={vi.fn()} />,
      { wrapper },
    );
    expect(container.innerHTML).toBe('');
  });

  it('renders modal with title when open=true', () => {
    render(<CostEstimationModal open={true} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByText('cost_prediction.title')).toBeInTheDocument();
  });

  it('renders all 6 form fields', () => {
    render(<CostEstimationModal open={true} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByText('cost_prediction.pollutant')).toBeInTheDocument();
    expect(screen.getByText('cost_prediction.material')).toBeInTheDocument();
    expect(screen.getByText('cost_prediction.condition')).toBeInTheDocument();
    expect(screen.getByText('cost_prediction.surface')).toBeInTheDocument();
    expect(screen.getByText('cost_prediction.canton')).toBeInTheDocument();
    expect(screen.getByText('cost_prediction.accessibility')).toBeInTheDocument();
  });

  it('renders estimate button', () => {
    render(<CostEstimationModal open={true} onClose={vi.fn()} />, { wrapper });
    expect(screen.getByText('cost_prediction.estimate')).toBeInTheDocument();
  });

  it('calls onClose when close button clicked', () => {
    const onClose = vi.fn();
    render(<CostEstimationModal open={true} onClose={onClose} />, { wrapper });
    // The backdrop click
    const backdrop = document.querySelector('.bg-black\\/40');
    if (backdrop) fireEvent.click(backdrop);
    expect(onClose).toHaveBeenCalled();
  });

  it('calls mutate with correct request on estimate click', () => {
    render(<CostEstimationModal open={true} onClose={vi.fn()} />, { wrapper });

    fireEvent.click(screen.getByText('cost_prediction.estimate'));

    expect(mutateFn).toHaveBeenCalledWith(
      {
        pollutant_type: 'asbestos',
        material_type: 'flocage',
        condition: 'bon',
        surface_m2: 50,
        canton: 'VD',
        accessibility: 'normal',
      },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it('uses defaultPollutant and defaultCanton props', () => {
    render(
      <CostEstimationModal open={true} onClose={vi.fn()} defaultPollutant="pcb" defaultCanton="GE" />,
      { wrapper },
    );

    fireEvent.click(screen.getByText('cost_prediction.estimate'));

    expect(mutateFn).toHaveBeenCalledWith(
      expect.objectContaining({ pollutant_type: 'pcb', canton: 'GE' }),
      expect.anything(),
    );
  });

  it('displays results after successful estimation', async () => {
    // Make mutate call onSuccess immediately
    mutateFn.mockImplementation((_req: unknown, opts: { onSuccess: (d: CostPredictionResponse) => void }) => {
      opts.onSuccess(MOCK_RESULT);
    });
    mockPredict.mockReturnValue(makeMutateMock({ mutate: mutateFn }));

    render(<CostEstimationModal open={true} onClose={vi.fn()} />, { wrapper });

    await act(async () => {
      fireEvent.click(screen.getByText('cost_prediction.estimate'));
    });

    // Cost range labels
    expect(screen.getByText('cost_prediction.result')).toBeInTheDocument();
    expect(screen.getByText('cost_prediction.range')).toBeInTheDocument();

    // Duration
    expect(screen.getByText('30')).toBeInTheDocument();
    expect(screen.getByText('cost_prediction.days')).toBeInTheDocument();

    // Complexity badge
    expect(screen.getByText('cost_prediction.complexity_complexe')).toBeInTheDocument();

    // Method
    expect(screen.getByText('depose')).toBeInTheDocument();

    // Coefficients (both are 1.00 so there will be two)
    expect(screen.getAllByText('1.00')).toHaveLength(2);

    // Disclaimer
    expect(screen.getByText(MOCK_RESULT.disclaimer)).toBeInTheDocument();

    // PDF export button
    expect(screen.getByText('cost_prediction.export_pdf')).toBeInTheDocument();
  });

  it('shows breakdown table when expanded', async () => {
    mutateFn.mockImplementation((_req: unknown, opts: { onSuccess: (d: CostPredictionResponse) => void }) => {
      opts.onSuccess(MOCK_RESULT);
    });
    mockPredict.mockReturnValue(makeMutateMock({ mutate: mutateFn }));

    render(<CostEstimationModal open={true} onClose={vi.fn()} />, { wrapper });

    await act(async () => {
      fireEvent.click(screen.getByText('cost_prediction.estimate'));
    });

    // Expand breakdown
    fireEvent.click(screen.getByText('cost_prediction.breakdown'));

    // Check breakdown row labels
    expect(screen.getByText('Depose / Intervention')).toBeInTheDocument();
    expect(screen.getByText('Traitement dechets')).toBeInTheDocument();
    expect(screen.getByText('Analyses controle')).toBeInTheDocument();
    expect(screen.getByText('Remise en etat')).toBeInTheDocument();
    expect(screen.getByText('Frais generaux')).toBeInTheDocument();
  });

  it('calls PDF export mutation when export button clicked', async () => {
    mutateFn.mockImplementation((_req: unknown, opts: { onSuccess: (d: CostPredictionResponse) => void }) => {
      opts.onSuccess(MOCK_RESULT);
    });
    mockPredict.mockReturnValue(makeMutateMock({ mutate: mutateFn }));

    render(<CostEstimationModal open={true} onClose={vi.fn()} />, { wrapper });

    await act(async () => {
      fireEvent.click(screen.getByText('cost_prediction.estimate'));
    });

    fireEvent.click(screen.getByText('cost_prediction.export_pdf'));
    expect(pdfMutateFn).toHaveBeenCalledWith({
      pollutant_type: 'asbestos',
      material_type: 'flocage',
      condition: 'bon',
      surface_m2: 50,
      canton: 'VD',
      accessibility: 'normal',
    });
  });

  it('disables estimate button when mutation is pending', () => {
    mockPredict.mockReturnValue(makeMutateMock({ isPending: true }));

    render(<CostEstimationModal open={true} onClose={vi.fn()} />, { wrapper });

    const button = screen.getByText('cost_prediction.estimate').closest('button');
    expect(button).toBeDisabled();
  });

  it('does not show results section before estimation', () => {
    render(<CostEstimationModal open={true} onClose={vi.fn()} />, { wrapper });
    expect(screen.queryByText('cost_prediction.result')).not.toBeInTheDocument();
  });

  it('updates surface via input', () => {
    render(<CostEstimationModal open={true} onClose={vi.fn()} />, { wrapper });

    const input = screen.getByDisplayValue('50');
    fireEvent.change(input, { target: { value: '200' } });

    fireEvent.click(screen.getByText('cost_prediction.estimate'));

    expect(mutateFn).toHaveBeenCalledWith(
      expect.objectContaining({ surface_m2: 200 }),
      expect.anything(),
    );
  });

  it('selects different pollutant from dropdown', () => {
    render(<CostEstimationModal open={true} onClose={vi.fn()} />, { wrapper });

    const selects = document.querySelectorAll('select');
    // First select is pollutant
    fireEvent.change(selects[0], { target: { value: 'lead' } });

    fireEvent.click(screen.getByText('cost_prediction.estimate'));

    expect(mutateFn).toHaveBeenCalledWith(
      expect.objectContaining({ pollutant_type: 'lead' }),
      expect.anything(),
    );
  });
});
