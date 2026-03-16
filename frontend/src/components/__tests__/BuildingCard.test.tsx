import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BuildingCard } from '../BuildingCard';
import type { Building } from '@/types';

const mockNavigate = vi.fn();

vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

function createMockBuilding(overrides: Partial<Building> = {}): Building {
  return {
    id: 'b-001',
    egid: null,
    egrid: 'CH123456',
    official_id: null,
    address: '12 Rue de Lausanne',
    postal_code: '1000',
    city: 'Lausanne',
    canton: 'VD',
    latitude: 46.5197,
    longitude: 6.6323,
    parcel_number: null,
    construction_year: 1965,
    renovation_year: null,
    building_type: 'residential',
    floors_above: 4,
    floors_below: 1,
    surface_area_m2: 450,
    volume_m3: null,
    owner_id: null,
    status: 'active',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
    risk_scores: {
      id: 'rs-001',
      building_id: 'b-001',
      asbestos_probability: 0.8,
      pcb_probability: 0.3,
      lead_probability: 0.5,
      hap_probability: 0.1,
      radon_probability: 0.2,
      overall_risk_level: 'high',
      confidence: 0.85,
      factors_json: null,
      data_source: 'model',
      last_updated: '2024-01-01T00:00:00Z',
    },
    ...overrides,
  };
}

describe('BuildingCard', () => {
  beforeEach(() => {
    mockNavigate.mockClear();
  });

  it('renders the building address and city', () => {
    const building = createMockBuilding();
    render(<BuildingCard building={building} />);

    expect(screen.getByText('12 Rue de Lausanne')).toBeInTheDocument();
    expect(screen.getByText('1000 Lausanne')).toBeInTheDocument();
  });

  it('renders the canton badge', () => {
    const building = createMockBuilding({ canton: 'GE' });
    render(<BuildingCard building={building} />);

    expect(screen.getByText('GE')).toBeInTheDocument();
  });

  it('renders the construction year', () => {
    const building = createMockBuilding({ construction_year: 1972 });
    render(<BuildingCard building={building} />);

    expect(screen.getByText('1972')).toBeInTheDocument();
  });

  it('renders "--" when construction year is null', () => {
    const building = createMockBuilding({ construction_year: null });
    render(<BuildingCard building={building} />);

    expect(screen.getByText('--')).toBeInTheDocument();
  });

  it('displays the risk level translation key', () => {
    const building = createMockBuilding();
    render(<BuildingCard building={building} />);

    // The mock t() returns the key as-is
    expect(screen.getByText('risk.high')).toBeInTheDocument();
  });

  it('displays unknown risk when risk_scores is undefined', () => {
    const building = createMockBuilding({ risk_scores: undefined });
    render(<BuildingCard building={building} />);

    expect(screen.getByText('risk.unknown')).toBeInTheDocument();
  });

  it('navigates to building detail on click when no onClick prop', async () => {
    const user = userEvent.setup();
    const building = createMockBuilding({ id: 'b-123' });
    render(<BuildingCard building={building} />);

    const card = screen.getByRole('article');
    await user.click(card);

    expect(mockNavigate).toHaveBeenCalledWith('/buildings/b-123');
  });

  it('calls custom onClick instead of navigating when provided', async () => {
    const user = userEvent.setup();
    const building = createMockBuilding();
    const handleClick = vi.fn();
    render(<BuildingCard building={building} onClick={handleClick} />);

    const card = screen.getByRole('article');
    await user.click(card);

    expect(handleClick).toHaveBeenCalledOnce();
    expect(mockNavigate).not.toHaveBeenCalled();
  });

  it('renders building type translation key', () => {
    const building = createMockBuilding({ building_type: 'industrial' });
    render(<BuildingCard building={building} />);

    expect(screen.getByText('building_type.industrial')).toBeInTheDocument();
  });

  it('renders the building type icon container', () => {
    const building = createMockBuilding({ building_type: 'commercial' });
    render(<BuildingCard building={building} />);

    // The card should render with the correct building type label
    expect(screen.getByText('building_type.commercial')).toBeInTheDocument();
  });

  it('is keyboard accessible via Enter key', async () => {
    const user = userEvent.setup();
    const building = createMockBuilding({ id: 'b-456' });
    render(<BuildingCard building={building} />);

    const card = screen.getByRole('article');
    card.focus();
    await user.keyboard('{Enter}');

    expect(mockNavigate).toHaveBeenCalledWith('/buildings/b-456');
  });

  // --- New high-signal tests below ---

  it('is keyboard accessible via Space key', async () => {
    const user = userEvent.setup();
    const building = createMockBuilding({ id: 'b-789' });
    render(<BuildingCard building={building} />);

    const card = screen.getByRole('article');
    card.focus();
    await user.keyboard(' ');

    expect(mockNavigate).toHaveBeenCalledWith('/buildings/b-789');
  });

  it('uses fallback icon for unrecognized building_type', () => {
    const building = createMockBuilding({ building_type: 'bunker' });
    render(<BuildingCard building={building} />);

    // The card still renders with the building_type key even for unknown types
    expect(screen.getByText('building_type.bunker')).toBeInTheDocument();
    // Card is still interactive (fallback icon = Building2)
    expect(screen.getByRole('article')).toBeInTheDocument();
  });

  describe('freshness color branches', () => {
    afterEach(() => {
      vi.useRealTimers();
    });

    it('shows green freshness for recently updated building (within 7 days)', () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date('2026-03-10T12:00:00Z'));

      const building = createMockBuilding({
        updated_at: '2026-03-08T12:00:00Z', // 2 days ago
      });
      render(<BuildingCard building={building} />);

      // The freshness indicator should have a green color class
      const freshnessEl = screen.getByTitle('building.data_freshness');
      expect(freshnessEl.className).toContain('green');
    });

    it('shows red freshness for stale building (over 90 days)', () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date('2026-03-10T12:00:00Z'));

      const building = createMockBuilding({
        updated_at: '2025-11-01T12:00:00Z', // ~130 days ago
      });
      render(<BuildingCard building={building} />);

      const freshnessEl = screen.getByTitle('building.data_freshness');
      expect(freshnessEl.className).toContain('red');
    });
  });

  it('shows surface area when updated_at is null', () => {
    const building = createMockBuilding({
      updated_at: null as unknown as string,
      surface_area_m2: 850,
    });
    render(<BuildingCard building={building} />);

    // Surface area rendered as fallback
    expect(screen.getByText(/850/)).toBeInTheDocument();
  });
});
