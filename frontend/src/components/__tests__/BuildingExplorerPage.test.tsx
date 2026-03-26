import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import BuildingExplorer from '@/pages/BuildingExplorer';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: vi.fn(),
}));

const mockListZones = vi.fn();
const mockCreateZone = vi.fn();
const mockDeleteZone = vi.fn();
vi.mock('@/api/zones', () => ({
  zonesApi: {
    list: (...args: unknown[]) => mockListZones(...args),
    create: (...args: unknown[]) => mockCreateZone(...args),
    delete: (...args: unknown[]) => mockDeleteZone(...args),
  },
}));

const mockListElements = vi.fn();
const mockCreateElement = vi.fn();
const mockDeleteElement = vi.fn();
vi.mock('@/api/elements', () => ({
  elementsApi: {
    list: (...args: unknown[]) => mockListElements(...args),
    create: (...args: unknown[]) => mockCreateElement(...args),
    delete: (...args: unknown[]) => mockDeleteElement(...args),
  },
}));

const mockListMaterials = vi.fn();
const mockCreateMaterial = vi.fn();
const mockDeleteMaterial = vi.fn();
vi.mock('@/api/materials', () => ({
  materialsApi: {
    list: (...args: unknown[]) => mockListMaterials(...args),
    create: (...args: unknown[]) => mockCreateMaterial(...args),
    delete: (...args: unknown[]) => mockDeleteMaterial(...args),
  },
}));

const mockListPlans = vi.fn();
vi.mock('@/api/plans', () => ({
  plansApi: {
    list: (...args: unknown[]) => mockListPlans(...args),
  },
}));

vi.mock('@/store/toastStore', () => ({
  toast: vi.fn(),
}));

vi.mock('@/components/RoleGate', () => ({
  RoleGate: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

vi.mock('@/components/PollutantBadge', () => ({
  PollutantBadge: () => <div>PollutantBadge</div>,
}));

vi.mock('@/components/ProofHeatmapOverlay', () => ({
  ProofHeatmapOverlay: () => <div>ProofHeatmapOverlay</div>,
}));

vi.mock('@/components/BuildingSubNav', () => ({
  BuildingSubNav: () => <div>BuildingSubNav</div>,
}));

function renderPage() {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter
        initialEntries={['/buildings/building-1/explorer']}
        future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
      >
        <Routes>
          <Route path="/buildings/:buildingId/explorer" element={<BuildingExplorer />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe('BuildingExplorer page', () => {
  beforeEach(() => {
    mockListZones.mockReset();
    mockCreateZone.mockReset();
    mockDeleteZone.mockReset();
    mockListElements.mockReset();
    mockCreateElement.mockReset();
    mockDeleteElement.mockReset();
    mockListMaterials.mockReset();
    mockCreateMaterial.mockReset();
    mockDeleteMaterial.mockReset();
    mockListPlans.mockReset();

    mockListZones.mockResolvedValue({
      items: [
        {
          id: 'zone-1',
          building_id: 'building-1',
          parent_zone_id: null,
          zone_type: 'technical_room',
          name: 'Sous-sol demo',
          description: null,
          floor_number: -1,
          surface_area_m2: 42,
          created_by: null,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
          children_count: 0,
          elements_count: 1,
        },
      ],
      total: 1,
      page: 1,
      size: 200,
      pages: 1,
    });
    mockListElements.mockResolvedValue({
      items: [
        {
          id: 'element-1',
          zone_id: 'zone-1',
          element_type: 'pipe',
          name: 'Conduite principale',
          description: null,
          condition: 'poor',
          installation_year: 1970,
          last_inspected_at: null,
          created_by: null,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
          materials_count: 2,
        },
      ],
      total: 1,
      page: 1,
      size: 20,
      pages: 1,
    });
    mockListMaterials.mockResolvedValue([]);
    mockListPlans.mockResolvedValue([]);
  });

  afterEach(() => {
    cleanup();
  });

  it('renders paginated element responses without crashing when a zone is selected', async () => {
    renderPage();

    fireEvent.click(await screen.findByText('Sous-sol demo'));

    await waitFor(() => {
      expect(screen.getByTestId('explorer-selected-zone-name')).toHaveTextContent('Sous-sol demo');
    });
    expect(await screen.findByText('Conduite principale')).toBeInTheDocument();
    expect(mockListElements).toHaveBeenCalledWith('building-1', 'zone-1');
  });
});
