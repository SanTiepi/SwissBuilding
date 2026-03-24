import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import AdminJurisdictions from '@/pages/AdminJurisdictions';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: Object.assign(
    () => ({
      user: { role: 'admin' },
    }),
    {
      getState: () => ({
        user: { role: 'admin' },
      }),
    },
  ),
}));

const mockList = vi.fn();
const mockGet = vi.fn();
const mockCreate = vi.fn();
const mockUpdate = vi.fn();
const mockDelete = vi.fn();

vi.mock('@/api/jurisdictions', () => ({
  jurisdictionsApi: {
    list: (...args: unknown[]) => mockList(...args),
    get: (...args: unknown[]) => mockGet(...args),
    create: (...args: unknown[]) => mockCreate(...args),
    update: (...args: unknown[]) => mockUpdate(...args),
    delete: (...args: unknown[]) => mockDelete(...args),
    listPacks: vi.fn().mockResolvedValue([]),
    createPack: vi.fn(),
    updatePack: vi.fn(),
    deletePack: vi.fn(),
  },
}));

const mockJurisdictions = [
  {
    id: 'j1',
    code: 'EU',
    name: 'European Union',
    parent_id: null,
    level: 'supranational',
    country_code: null,
    is_active: true,
    metadata_json: null,
    created_at: '2024-01-01T00:00:00Z',
    regulatory_packs: [],
  },
  {
    id: 'j2',
    code: 'CH',
    name: 'Suisse',
    parent_id: 'j1',
    level: 'country',
    country_code: 'CH',
    is_active: true,
    metadata_json: null,
    created_at: '2024-01-01T00:00:00Z',
    regulatory_packs: [
      {
        id: 'rp1',
        jurisdiction_id: 'j2',
        pollutant_type: 'asbestos',
        version: '1.0',
        is_active: true,
        threshold_value: 1.0,
        threshold_unit: 'percent_weight',
        threshold_action: 'remediate',
        risk_year_start: 1904,
        risk_year_end: 1990,
        base_probability: 0.85,
        work_categories_json: null,
        waste_classification_json: null,
        legal_reference: 'OTConst',
        legal_url: null,
        description_fr: null,
        description_de: null,
        notification_required: false,
        notification_authority: null,
        notification_delay_days: null,
        created_at: '2024-01-01T00:00:00Z',
        updated_at: '2024-01-01T00:00:00Z',
      },
    ],
  },
  {
    id: 'j3',
    code: 'CH-VD',
    name: 'Canton de Vaud',
    parent_id: 'j2',
    level: 'region',
    country_code: 'CH',
    is_active: false,
    metadata_json: null,
    created_at: '2024-01-01T00:00:00Z',
    regulatory_packs: [],
  },
];

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

describe('AdminJurisdictions', () => {
  beforeEach(() => {
    mockList.mockReset();
    mockGet.mockReset();
    mockCreate.mockReset();
    mockUpdate.mockReset();
    mockDelete.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('renders loading state', () => {
    mockList.mockReturnValue(new Promise(() => {})); // never resolves
    render(<AdminJurisdictions />, { wrapper });
    // The Loader2 spinner should be present (it has animate-spin class)
    const spinner = document.querySelector('.animate-spin');
    expect(spinner).toBeTruthy();
  });

  it('renders jurisdiction tree after data loads', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    render(<AdminJurisdictions />, { wrapper });

    expect(await screen.findByText('European Union')).toBeInTheDocument();
    expect(screen.getByText('Suisse')).toBeInTheDocument();
    expect(screen.getByText('Canton de Vaud')).toBeInTheDocument();
  });

  it('renders summary stats bar', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');
    const statsBar = screen.getByTestId('stats-bar');
    expect(statsBar).toBeInTheDocument();
    // Total = 3
    expect(statsBar.textContent).toContain('3');
  });

  it('search filter filters jurisdictions by name', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');

    const searchInput = screen.getByTestId('jurisdiction-search');
    fireEvent.change(searchInput, { target: { value: 'vaud' } });

    expect(screen.getByText('Canton de Vaud')).toBeInTheDocument();
    expect(screen.queryByText('European Union')).not.toBeInTheDocument();
    expect(screen.queryByText('Suisse')).not.toBeInTheDocument();
  });

  it('search filter filters jurisdictions by code', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');

    const searchInput = screen.getByTestId('jurisdiction-search');
    fireEvent.change(searchInput, { target: { value: 'CH-VD' } });

    expect(screen.getByText('Canton de Vaud')).toBeInTheDocument();
    expect(screen.queryByText('European Union')).not.toBeInTheDocument();
  });

  it('level filter works', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');

    const levelSelect = screen.getByTestId('level-filter');
    fireEvent.change(levelSelect, { target: { value: 'country' } });

    expect(screen.getByText('Suisse')).toBeInTheDocument();
    expect(screen.queryByText('European Union')).not.toBeInTheDocument();
    expect(screen.queryByText('Canton de Vaud')).not.toBeInTheDocument();
  });

  it('active/inactive filter works', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');

    const activeSelect = screen.getByTestId('active-filter');
    fireEvent.change(activeSelect, { target: { value: 'inactive' } });

    expect(screen.getByText('Canton de Vaud')).toBeInTheDocument();
    expect(screen.queryByText('European Union')).not.toBeInTheDocument();
    expect(screen.queryByText('Suisse')).not.toBeInTheDocument();
  });

  it('shows filtered count when filters are active', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');

    const searchInput = screen.getByTestId('jurisdiction-search');
    fireEvent.change(searchInput, { target: { value: 'Suisse' } });

    expect(screen.getByText(/1 \/ 3/)).toBeInTheDocument();
  });

  it('create modal opens when add button clicked', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');

    const addButton = screen.getByText('jurisdiction.add');
    fireEvent.click(addButton);

    // Modal heading should appear
    expect(screen.getAllByText('jurisdiction.add').length).toBeGreaterThanOrEqual(2);
  });

  it('edit modal opens with prefilled data when jurisdiction selected and edit clicked', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    mockGet.mockResolvedValue(mockJurisdictions[1]); // Suisse

    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');

    // Click Suisse to select it
    fireEvent.click(screen.getByText('Suisse'));
    // Wait for detail panel — the detail h2 shows the jurisdiction name with font-bold and text-lg
    const detailHeading = await screen.findByText('Suisse', { selector: 'h2.text-lg' });
    expect(detailHeading).toBeInTheDocument();

    // The detail panel has edit/delete buttons in a .flex.items-center.gap-1 container
    const actionButtons = document.querySelectorAll('.flex.items-center.gap-1 button');
    expect(actionButtons.length).toBeGreaterThanOrEqual(2);
    fireEvent.click(actionButtons[0]); // edit button

    // Modal should contain the pre-filled code input
    const codeInput = document.querySelector('input[placeholder="CH-VD"]') as HTMLInputElement;
    expect(codeInput).toBeTruthy();
    expect(codeInput.value).toBe('CH');
  });

  it('delete confirmation dialog appears', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    mockGet.mockResolvedValue(mockJurisdictions[1]);

    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');

    fireEvent.click(screen.getByText('Suisse'));
    const detailHeading = await screen.findByText('Suisse', { selector: 'h2.text-lg' });
    expect(detailHeading).toBeInTheDocument();

    // The delete button is the second button in the action container
    const actionButtons = document.querySelectorAll('.flex.items-center.gap-1 button');
    expect(actionButtons.length).toBeGreaterThanOrEqual(2);
    fireEvent.click(actionButtons[1]); // delete button

    // Confirm dialog should show the delete heading
    expect(screen.getByText('jurisdiction.delete')).toBeInTheDocument();
  });

  it('renders mobile pack cards when jurisdiction with packs is selected', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    mockGet.mockResolvedValue(mockJurisdictions[1]); // Suisse with 1 pack

    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');

    // Click Suisse to select it
    fireEvent.click(screen.getByText('Suisse'));
    await screen.findByText('Suisse', { selector: 'h2.text-lg' });

    // Mobile cards container should exist
    const mobileCards = screen.getByTestId('packs-mobile-cards');
    expect(mobileCards).toBeInTheDocument();

    // Desktop table should also exist (hidden via CSS)
    const desktopTable = screen.getByTestId('packs-desktop-table');
    expect(desktopTable).toBeInTheDocument();

    // Individual mobile card should render
    const cards = screen.getAllByTestId('pack-mobile-card');
    expect(cards).toHaveLength(1);
  });

  it('mobile pack card displays key fields', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    mockGet.mockResolvedValue(mockJurisdictions[1]);

    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');
    fireEvent.click(screen.getByText('Suisse'));
    await screen.findByText('Suisse', { selector: 'h2.text-lg' });

    const card = screen.getByTestId('pack-mobile-card');
    // pollutant badge
    expect(card.textContent).toContain('pollutant.asbestos');
    // threshold value
    expect(card.textContent).toContain('1');
    // unit
    expect(card.textContent).toContain('percent_weight');
    // risk years
    expect(card.textContent).toContain('1904');
    expect(card.textContent).toContain('1990');
    // legal reference
    expect(card.textContent).toContain('OTConst');
  });

  it('renders error state when API fails', async () => {
    mockList.mockRejectedValue(new Error('Network error'));
    render(<AdminJurisdictions />, { wrapper });

    expect(await screen.findByText('app.error')).toBeInTheDocument();
  });

  it('shows no-results message when filters match nothing', async () => {
    mockList.mockResolvedValue({ items: mockJurisdictions, total: 3, page: 1, size: 100, pages: 1 });
    render(<AdminJurisdictions />, { wrapper });

    await screen.findByText('European Union');

    const searchInput = screen.getByTestId('jurisdiction-search');
    fireEvent.change(searchInput, { target: { value: 'xyznotexist' } });

    expect(screen.getByText('jurisdiction.no_results')).toBeInTheDocument();
  });
});
