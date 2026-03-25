import { describe, it, expect, vi, beforeEach } from 'vitest';
import { fireEvent, render, screen, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { rolloutApi } from '@/api/rollout';
import { PackagePresetPreview } from '@/components/building-detail/PackagePresetPreview';

vi.mock('@/api/rollout', () => ({
  rolloutApi: {
    listPresets: vi.fn().mockResolvedValue([
      { code: 'wedge', label: 'Wedge', description: 'Core pollutant diagnostics' },
      { code: 'operational', label: 'Operational', description: 'Full operational view' },
      { code: 'portfolio', label: 'Portfolio', description: 'Portfolio intelligence' },
    ]),
    previewPreset: vi.fn().mockResolvedValue({
      preset_code: 'wedge',
      included: ['Asbestos diagnostic', 'Risk scoring', 'Evidence pack'],
      excluded: ['Lease management', 'Financial entries'],
      unknown: ['PCB status'],
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

async function selectPreset() {
  await waitFor(() => {
    expect(screen.getByTestId('preset-selector')).toBeInTheDocument();
    // Wait for presets to be loaded into options
    expect(screen.getByText('Wedge')).toBeInTheDocument();
  });
  await act(async () => {
    fireEvent.change(screen.getByTestId('preset-selector'), { target: { value: 'wedge' } });
  });
  // Give React Query time to fire the enabled query
  await waitFor(() => {
    expect(rolloutApi.previewPreset).toHaveBeenCalled();
  });
}

describe('PackagePresetPreview', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders card with title', async () => {
    render(<PackagePresetPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByTestId('package-preset-preview')).toBeInTheDocument();
      expect(screen.getByText('package_preset.title')).toBeInTheDocument();
    });
  });

  it('renders preset selector with options', async () => {
    render(<PackagePresetPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('Wedge')).toBeInTheDocument();
      expect(screen.getByText('Operational')).toBeInTheDocument();
      expect(screen.getByText('Portfolio')).toBeInTheDocument();
    });
  });

  it('shows select hint before preset chosen', async () => {
    render(<PackagePresetPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await waitFor(() => {
      expect(screen.getByText('package_preset.select_hint')).toBeInTheDocument();
    });
  });

  it('renders included items after preset selection', async () => {
    render(<PackagePresetPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await selectPreset();
    await waitFor(() => {
      const included = screen.getAllByTestId('preset-included');
      expect(included.length).toBe(3);
    });
  });

  it('renders excluded items after preset selection', async () => {
    render(<PackagePresetPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await selectPreset();
    await waitFor(() => {
      const excluded = screen.getAllByTestId('preset-excluded');
      expect(excluded.length).toBe(2);
    });
  });

  it('renders unknown items after preset selection', async () => {
    render(<PackagePresetPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await selectPreset();
    await waitFor(() => {
      const unknown = screen.getAllByTestId('preset-unknown');
      expect(unknown.length).toBe(1);
    });
  });

  it('renders generate & share button after preset selection', async () => {
    render(<PackagePresetPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await selectPreset();
    await waitFor(() => {
      expect(screen.getByTestId('preset-generate-share')).toBeInTheDocument();
    });
  });

  it('calls previewPreset with correct args', async () => {
    render(<PackagePresetPreview buildingId="b-1" />, { wrapper: createWrapper() });
    await selectPreset();
    expect(rolloutApi.previewPreset).toHaveBeenCalledWith('b-1', 'wedge');
  });
});
