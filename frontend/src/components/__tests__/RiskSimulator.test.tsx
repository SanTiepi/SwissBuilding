import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import RiskSimulator from '@/pages/RiskSimulator';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockUseBuildings = vi.fn();
vi.mock('@/hooks/useBuildings', () => ({
  useBuildings: () => mockUseBuildings(),
}));

const mockListSimulations = vi.fn();
vi.mock('@/api/savedSimulations', () => ({
  savedSimulationsApi: {
    list: (...args: unknown[]) => mockListSimulations(...args),
    create: vi.fn(),
    delete: vi.fn(),
  },
}));

vi.mock('@/api/risk', () => ({
  riskApi: {
    simulate: vi.fn(),
  },
}));

vi.mock('@/store/toastStore', () => ({
  toast: vi.fn(),
}));

vi.mock('@/components/RiskGauge', () => ({
  RiskGauge: () => <div>RiskGauge</div>,
}));

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  });
  return (
    <QueryClientProvider client={client}>
      <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>{children}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('RiskSimulator', () => {
  beforeEach(() => {
    mockUseBuildings.mockReset();
    mockListSimulations.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders explicit error state when buildings fail to load', async () => {
    mockUseBuildings.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
    });

    render(<RiskSimulator />, { wrapper });

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });

  it('renders explicit error state when saved simulations fail to load', async () => {
    mockUseBuildings.mockReturnValue({
      data: {
        items: [
          {
            id: 'b1',
            address: 'Rue du Test 1',
            postal_code: '1000',
            city: 'Lausanne',
            canton: 'VD',
          },
        ],
      },
      isLoading: false,
      isError: false,
    });
    mockListSimulations.mockRejectedValue(new Error('boom'));

    render(<RiskSimulator />, { wrapper });

    fireEvent.change(screen.getByLabelText('building.search'), { target: { value: 'Rue' } });
    fireEvent.click(await screen.findByRole('button', { name: /Rue du Test 1/i }));
    fireEvent.click(screen.getByRole('button', { name: /History/i }));

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });
});
