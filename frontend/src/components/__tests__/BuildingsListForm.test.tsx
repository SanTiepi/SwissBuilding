import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router-dom';
import BuildingsList from '@/pages/BuildingsList';

const mockMutateAsync = vi.fn();
let mockIsPending = false;

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'u-1', role: 'admin', email: 'test@test.ch' },
    token: 'fake-token',
    isAuthenticated: true,
  }),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: () => ({
    user: {
      id: 'u-1',
      role: 'admin',
      email: 'test@test.ch',
      first_name: 'Test',
      last_name: 'Admin',
      language: 'fr',
      is_active: true,
      organization_id: null,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z',
    },
    token: 'fake-token',
    isAuthenticated: true,
    setAuth: vi.fn(),
    logout: vi.fn(),
    updateUser: vi.fn(),
  }),
}));

vi.mock('@/hooks/useBuildings', () => ({
  useBuildings: () => ({
    data: { items: [], total: 0, page: 1, size: 20, pages: 1 },
    isLoading: false,
    isError: false,
  }),
  useCreateBuilding: () => ({
    mutateAsync: mockMutateAsync,
    isPending: mockIsPending,
  }),
}));

vi.mock('@/api/buildingDashboard', () => ({
  buildingDashboardApi: { get: vi.fn() },
}));

vi.mock('@/api/buildings', () => ({
  buildingsApi: { get: vi.fn(), list: vi.fn() },
}));

function renderWithProviders() {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <BuildingsList />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

async function openCreateModal() {
  const user = userEvent.setup();
  // Use the specific testid for the legacy create form button (not the wizard button)
  const addBtn = screen.getByTestId('buildings-create-button');
  await user.click(addBtn);
}

describe('BuildingsList Create Form', () => {
  beforeEach(() => {
    mockMutateAsync.mockReset();
    mockIsPending = false;
  });

  it('renders the add building button', () => {
    renderWithProviders();
    expect(screen.getByText('building.add')).toBeInTheDocument();
  });

  it('opens modal and renders all required fields', async () => {
    renderWithProviders();
    await openCreateModal();

    // Required field labels should be present (t() returns key as-is)
    expect(screen.getByText(/building\.address/)).toBeInTheDocument();
    expect(screen.getByText(/building\.city/)).toBeInTheDocument();
    expect(screen.getByText(/building\.postal_code/)).toBeInTheDocument();
    expect(screen.getByText(/building\.canton/)).toBeInTheDocument();
    expect(screen.getByText(/building\.construction_year/)).toBeInTheDocument();
    expect(screen.getByText(/building\.building_type/)).toBeInTheDocument();
  });

  it('shows validation errors for empty required fields on submit', async () => {
    const user = userEvent.setup();
    renderWithProviders();
    await openCreateModal();

    // Submit empty form
    const submitBtn = screen.getByText('form.create');
    await user.click(submitBtn);

    // Should show validation error messages
    await waitFor(() => {
      const errorMessages = screen.getAllByText(/required|is required/i);
      expect(errorMessages.length).toBeGreaterThan(0);
    });
  });

  it('validates postal code format (4 digits)', async () => {
    const user = userEvent.setup();
    renderWithProviders();
    await openCreateModal();

    // Fill address, city, canton, building type, construction year — but bad postal code
    const inputs = screen.getAllByRole('textbox');
    // address is the first textbox
    await user.type(inputs[0], 'Test Street 1');
    // city
    await user.type(inputs[1], 'Bern');
    // postal_code
    await user.type(inputs[2], '12'); // too short

    const submitBtn = screen.getByText('form.create');
    await user.click(submitBtn);

    await waitFor(() => {
      // Should show postal code error
      const errors = document.querySelectorAll('.text-red-600');
      expect(errors.length).toBeGreaterThan(0);
    });
  });

  it('validates construction year range (1800-current)', async () => {
    const user = userEvent.setup();
    renderWithProviders();
    await openCreateModal();

    // Fill the construction year with an invalid value
    const numberInputs = screen.getAllByRole('spinbutton');
    // Construction year is the first number input
    await user.type(numberInputs[0], '1700');

    const submitBtn = screen.getByText('form.create');
    await user.click(submitBtn);

    await waitFor(() => {
      const errors = document.querySelectorAll('.text-red-600');
      expect(errors.length).toBeGreaterThan(0);
    });
  });

  it('shows EGID and EGRID as separate fields in advanced section', async () => {
    const user = userEvent.setup();
    renderWithProviders();
    await openCreateModal();

    // Click advanced options
    const advancedBtn = screen.getByText('form.advanced_options');
    await user.click(advancedBtn);

    // Both EGID and EGRID labels should be present and distinct
    expect(screen.getByText('building.egid')).toBeInTheDocument();
    expect(screen.getByText('building.egrid')).toBeInTheDocument();
    expect(screen.getByText('building.official_id')).toBeInTheDocument();

    // Helper text should distinguish them
    expect(screen.getByText('building.egid_hint')).toBeInTheDocument();
    expect(screen.getByText('building.egrid_hint')).toBeInTheDocument();
    expect(screen.getByText('building.official_id_hint')).toBeInTheDocument();
  });

  it('shows floors_below field in advanced section', async () => {
    const user = userEvent.setup();
    renderWithProviders();
    await openCreateModal();

    const advancedBtn = screen.getByText('form.advanced_options');
    await user.click(advancedBtn);

    expect(screen.getByText('building.floors_above')).toBeInTheDocument();
    expect(screen.getByText('building.floors_below')).toBeInTheDocument();
    expect(screen.getByText('building.surface_area')).toBeInTheDocument();
  });

  it('calls mutateAsync on valid form submission', async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockResolvedValueOnce({ id: 'new-building' });
    renderWithProviders();
    await openCreateModal();

    // Fill required fields within the modal form
    const form = document.querySelector('form')!;
    const formInputs = form.querySelectorAll<HTMLInputElement>('input:not([type="number"])');
    // address, city, postal_code
    await user.type(formInputs[0], 'Test Avenue 1');
    await user.type(formInputs[1], 'Lausanne');
    await user.type(formInputs[2], '1000');

    // Select canton and building type (combobox within form)
    const formSelects = form.querySelectorAll('select');
    await user.selectOptions(formSelects[0], 'VD');
    await user.selectOptions(formSelects[1], 'residential');

    // Construction year
    const formNumberInputs = form.querySelectorAll<HTMLInputElement>('input[type="number"]');
    await user.type(formNumberInputs[0], '1990');

    const submitBtn = screen.getByText('form.create');
    await user.click(submitBtn);

    await waitFor(() => {
      expect(mockMutateAsync).toHaveBeenCalledTimes(1);
    });

    // Verify the call included the right data
    const callData = mockMutateAsync.mock.calls[0][0];
    expect(callData.address).toBe('Test Avenue 1');
    expect(callData.city).toBe('Lausanne');
    expect(callData.postal_code).toBe('1000');
    expect(callData.canton).toBe('VD');
    expect(callData.building_type).toBe('residential');
    expect(callData.construction_year).toBe(1990);
  });

  it('shows error message when API call fails', async () => {
    const user = userEvent.setup();
    mockMutateAsync.mockRejectedValueOnce({
      response: { data: { detail: 'Duplicate EGRID' } },
    });
    renderWithProviders();
    await openCreateModal();

    // Fill required fields within the modal form
    const form = document.querySelector('form')!;
    const formInputs = form.querySelectorAll<HTMLInputElement>('input:not([type="number"])');
    await user.type(formInputs[0], 'Test Avenue 1');
    await user.type(formInputs[1], 'Lausanne');
    await user.type(formInputs[2], '1000');

    const formSelects = form.querySelectorAll('select');
    await user.selectOptions(formSelects[0], 'VD');
    await user.selectOptions(formSelects[1], 'residential');

    const formNumberInputs = form.querySelectorAll<HTMLInputElement>('input[type="number"]');
    await user.type(formNumberInputs[0], '1990');

    const submitBtn = screen.getByText('form.create');
    await user.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Duplicate EGRID')).toBeInTheDocument();
    });
  });

  it('closes modal on cancel', async () => {
    const user = userEvent.setup();
    renderWithProviders();
    await openCreateModal();

    // Modal should be visible
    expect(screen.getByText('form.create')).toBeInTheDocument();

    const cancelBtn = screen.getByText('form.cancel');
    await user.click(cancelBtn);

    // Modal should be closed — form.create button (submit) should not be visible
    await waitFor(() => {
      expect(screen.queryByText('form.cancel')).not.toBeInTheDocument();
    });
  });

  it('shows field groupings with legends', async () => {
    renderWithProviders();
    await openCreateModal();

    // Should have grouped fieldsets
    const legends = document.querySelectorAll('legend');
    expect(legends.length).toBeGreaterThanOrEqual(2);
  });

  it('shows year range hint below construction year', async () => {
    renderWithProviders();
    await openCreateModal();

    expect(screen.getByText('building.year_range_hint')).toBeInTheDocument();
  });
});
