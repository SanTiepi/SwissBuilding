import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockDashboard = vi.fn();

vi.mock('@/api/completeness', () => ({
  completenessApi: {
    getDashboard: (...args: unknown[]) => mockDashboard(...args),
    getMissingItems: vi.fn().mockResolvedValue({ building_id: '1', items: [], total: 0 }),
    getRecommendedActions: vi.fn().mockResolvedValue({ building_id: '1', actions: [], total: 0 }),
  },
}));

vi.mock('@/store/toastStore', () => ({
  toast: vi.fn(),
}));

const { CompletenessCard } = await import('@/components/buildings/CompletenessCard');
const { CompletenessBreakdown } = await import('@/components/buildings/CompletenessBreakdown');
const { MissingItemsChecklist } = await import('@/components/buildings/MissingItemsChecklist');

function wrapper({ children }: { children: React.ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 }, mutations: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

const MOCK_DASHBOARD = {
  building_id: 'test-id',
  overall_score: 75.3,
  overall_color: 'yellow',
  dimensions: [
    { key: 'building_metadata', label: 'Building metadata', score: 90, max_weight: 20, color: 'green', missing_items: [], required_actions: [] },
    { key: 'energy_data', label: 'Energy data', score: 33, max_weight: 15, color: 'red', missing_items: [{ field: 'cecb_label', importance: 'critical' }], required_actions: [] },
    { key: 'hazardous_materials', label: 'Hazardous materials', score: 100, max_weight: 20, color: 'green', missing_items: [], required_actions: [] },
    { key: 'structural_health', label: 'Structural health', score: 0, max_weight: 15, color: 'red', missing_items: [{ field: 'sinistralite_score', importance: 'important' }], required_actions: [] },
    { key: 'environmental_exposure', label: 'Environmental exposure', score: 50, max_weight: 15, color: 'orange', missing_items: [], required_actions: [] },
    { key: 'regulatory_compliance', label: 'Regulatory compliance', score: 100, max_weight: 20, color: 'green', missing_items: [], required_actions: [] },
    { key: 'materials_inventory', label: 'Materials inventory', score: 80, max_weight: 15, color: 'yellow', missing_items: [], required_actions: [] },
    { key: 'repair_history', label: 'Repair history', score: 100, max_weight: 10, color: 'green', missing_items: [], required_actions: [] },
    { key: 'owner_occupant', label: 'Owner/occupant', score: 33, max_weight: 10, color: 'red', missing_items: [], required_actions: [] },
    { key: 'legal_documents', label: 'Legal documents', score: 0, max_weight: 15, color: 'red', missing_items: [], required_actions: [] },
    { key: 'photos_evidence', label: 'Photos/evidence', score: 60, max_weight: 10, color: 'orange', missing_items: [], required_actions: [] },
    { key: 'field_observations', label: 'Field observations', score: 0, max_weight: 10, color: 'red', missing_items: [], required_actions: [] },
    { key: 'third_party_inspections', label: 'Third-party', score: 100, max_weight: 10, color: 'green', missing_items: [], required_actions: [] },
    { key: 'remediation_plan', label: 'Remediation plan', score: 50, max_weight: 10, color: 'orange', missing_items: [], required_actions: [] },
    { key: 'post_works', label: 'Post-works', score: 50, max_weight: 10, color: 'orange', missing_items: [], required_actions: [] },
    { key: 'maintenance_manual', label: 'Maintenance manual', score: 0, max_weight: 5, color: 'red', missing_items: [], required_actions: [] },
  ],
  missing_items_count: 5,
  urgent_actions: 2,
  recommended_actions: 3,
  trend: 'improving' as const,
  evaluated_at: '2026-04-02T10:00:00Z',
};

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe('CompletenessCard', () => {
  it('renders loading state initially', () => {
    mockDashboard.mockReturnValue(new Promise(() => {})); // never resolves
    render(<CompletenessCard buildingId="test-id" />, { wrapper });
    // Should show loading spinner (Loader2 via animate-spin)
    expect(document.querySelector('.animate-spin')).toBeTruthy();
  });

  it('renders overall score when data loads', async () => {
    mockDashboard.mockResolvedValue(MOCK_DASHBOARD);
    render(<CompletenessCard buildingId="test-id" />, { wrapper });
    expect(await screen.findByText('75%')).toBeTruthy();
  });

  it('renders 16 dimension circles', async () => {
    mockDashboard.mockResolvedValue(MOCK_DASHBOARD);
    render(<CompletenessCard buildingId="test-id" />, { wrapper });
    await screen.findByText('75%');
    // 16 circles with aria-labels
    const circles = document.querySelectorAll('[aria-label]');
    expect(circles.length).toBe(16);
  });

  it('shows urgent actions badge', async () => {
    mockDashboard.mockResolvedValue(MOCK_DASHBOARD);
    render(<CompletenessCard buildingId="test-id" />, { wrapper });
    expect(await screen.findByText(/2/)).toBeTruthy();
  });

  it('calls onClick when clicked', async () => {
    mockDashboard.mockResolvedValue(MOCK_DASHBOARD);
    const onClick = vi.fn();
    render(<CompletenessCard buildingId="test-id" onClick={onClick} />, { wrapper });
    await screen.findByText('75%');
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).toHaveBeenCalledOnce();
  });

  it('handles null data gracefully', async () => {
    mockDashboard.mockResolvedValue(null);
    const { container } = render(<CompletenessCard buildingId="test-id" />, { wrapper });
    // Wait for query to settle
    await new Promise((r) => setTimeout(r, 50));
    // Should render nothing (null return)
    expect(container.textContent).toBe('');
  });
});

describe('CompletenessBreakdown', () => {
  it('renders all 16 dimensions', async () => {
    mockDashboard.mockResolvedValue(MOCK_DASHBOARD);
    render(<CompletenessBreakdown buildingId="test-id" />, { wrapper });
    expect(await screen.findByText('Building metadata')).toBeTruthy();
    expect(screen.getByText('Energy data')).toBeTruthy();
    expect(screen.getByText('Hazardous materials')).toBeTruthy();
  });

  it('shows percentage for each dimension', async () => {
    mockDashboard.mockResolvedValue(MOCK_DASHBOARD);
    render(<CompletenessBreakdown buildingId="test-id" />, { wrapper });
    expect(await screen.findByText('90%')).toBeTruthy();
    expect(screen.getAllByText('33%').length).toBeGreaterThan(0);
    expect(screen.getAllByText('100%').length).toBeGreaterThan(0);
  });
});

describe('MissingItemsChecklist', () => {
  it('shows all-complete message when no items', async () => {
    render(<MissingItemsChecklist buildingId="test-id" />, { wrapper });
    expect(await screen.findByText('completeness.all_complete')).toBeTruthy();
  });
});
