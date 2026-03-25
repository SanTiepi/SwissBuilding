import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import MarketplaceCompanies from '@/pages/MarketplaceCompanies';

// Mock the API
vi.mock('@/api/marketplace', () => ({
  marketplaceApi: {
    listCompanies: vi.fn().mockResolvedValue({
      items: [
        {
          id: '1',
          organization_id: 'org-1',
          company_name: 'SanaCore SA',
          legal_form: 'SA',
          uid_number: 'CHE-123',
          address: 'Rue Test 1',
          city: 'Lausanne',
          postal_code: '1000',
          canton: 'VD',
          contact_email: 'info@sanacore.ch',
          contact_phone: null,
          website: null,
          description: 'Expert desamiantage',
          work_categories: ['asbestos_removal', 'pcb_remediation'],
          certifications: [],
          regions_served: ['VD', 'GE'],
          employee_count: 45,
          years_experience: 20,
          insurance_info: null,
          is_active: true,
          profile_completeness: 0.9,
          created_at: '2026-01-01T00:00:00Z',
          updated_at: '2026-01-01T00:00:00Z',
        },
      ],
      total: 1,
      page: 1,
      size: 50,
      pages: 1,
    }),
    getRatingSummary: vi.fn().mockResolvedValue({
      company_profile_id: '1',
      average_rating: 4.2,
      total_reviews: 5,
      rating_breakdown: { '1': 0, '2': 0, '3': 1, '4': 2, '5': 2 },
      average_quality: 4.0,
      average_timeliness: 4.5,
      average_communication: 4.0,
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k }),
}));

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>{ui}</BrowserRouter>
    </QueryClientProvider>,
  );
}

describe('MarketplaceCompanies', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders the page title', async () => {
    renderWithProviders(<MarketplaceCompanies />);
    expect(screen.getByText('marketplace.companies_title')).toBeInTheDocument();
  });

  it('displays company cards after loading', async () => {
    renderWithProviders(<MarketplaceCompanies />);
    await waitFor(() => {
      expect(screen.getByText('SanaCore SA')).toBeInTheDocument();
    });
  });

  it('displays canton and city info', async () => {
    renderWithProviders(<MarketplaceCompanies />);
    await waitFor(() => {
      expect(screen.getByText('Lausanne, VD')).toBeInTheDocument();
    });
  });

  it('shows work category badges', async () => {
    renderWithProviders(<MarketplaceCompanies />);
    await waitFor(() => {
      expect(screen.getByText('marketplace.work_category.asbestos_removal')).toBeInTheDocument();
    });
  });

  it('has search input', () => {
    renderWithProviders(<MarketplaceCompanies />);
    const searchInput = screen.getByPlaceholderText('marketplace.search_placeholder');
    expect(searchInput).toBeInTheDocument();
  });

  it('has canton filter dropdown', () => {
    renderWithProviders(<MarketplaceCompanies />);
    expect(screen.getByText('marketplace.all_cantons')).toBeInTheDocument();
  });

  it('has work category filter dropdown', () => {
    renderWithProviders(<MarketplaceCompanies />);
    expect(screen.getByText('marketplace.all_categories')).toBeInTheDocument();
  });

  it('displays rating badge when rating summary loads', async () => {
    renderWithProviders(<MarketplaceCompanies />);
    await waitFor(() => {
      expect(screen.getByText('4.2')).toBeInTheDocument();
    });
  });
});
