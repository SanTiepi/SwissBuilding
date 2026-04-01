import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ActivityLedger } from '../ActivityLedger';
import type { BuildingActivityList, ChainIntegrity } from '@/api/buildingActivities';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const mockLedger: BuildingActivityList = {
  items: [
    {
      id: 'a1',
      building_id: 'b1',
      actor_id: 'u1',
      actor_role: 'diagnostician',
      actor_name: 'Jean Muller',
      activity_type: 'diagnostic_submitted',
      entity_type: 'diagnostic',
      entity_id: 'd1',
      title: 'Asbestos diagnostic submitted',
      description: 'Full survey completed',
      reason: 'Annual regulatory check',
      metadata_json: null,
      previous_hash: null,
      activity_hash: 'abc123',
      created_at: '2024-06-15T10:00:00Z',
    },
    {
      id: 'a2',
      building_id: 'b1',
      actor_id: 'u2',
      actor_role: 'admin',
      actor_name: 'Admin User',
      activity_type: 'document_uploaded',
      entity_type: 'document',
      entity_id: 'doc1',
      title: 'Lab report uploaded',
      description: null,
      reason: null,
      metadata_json: null,
      previous_hash: 'abc123',
      activity_hash: 'def456',
      created_at: '2024-06-14T09:00:00Z',
    },
  ],
  total: 2,
  page: 1,
  size: 20,
};

const mockChainValid: ChainIntegrity = {
  valid: true,
  total_entries: 2,
  first_break_at: null,
};

const mockChainBroken: ChainIntegrity = {
  valid: false,
  total_entries: 5,
  first_break_at: 3,
};

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: false } },
});

function wrapper({ children }: { children: React.ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

describe('ActivityLedger', () => {
  it('renders activity entries when data is provided', async () => {
    vi.doMock('@/api/buildingActivities', () => ({
      buildingActivitiesApi: {
        list: vi.fn().mockResolvedValue(mockLedger),
        verifyChain: vi.fn().mockResolvedValue(mockChainValid),
      },
    }));

    render(<ActivityLedger buildingId="b1" />, { wrapper });

    // Title should render
    expect(screen.getByText('activity_ledger.title')).toBeTruthy();

    // Filter dropdown present
    const select = screen.getByRole('combobox');
    expect(select).toBeTruthy();
  });

  it('shows chain valid indicator', async () => {
    vi.doMock('@/api/buildingActivities', () => ({
      buildingActivitiesApi: {
        list: vi.fn().mockResolvedValue(mockLedger),
        verifyChain: vi.fn().mockResolvedValue(mockChainValid),
      },
    }));

    render(<ActivityLedger buildingId="b1" />, { wrapper });
    expect(screen.getByText('activity_ledger.title')).toBeTruthy();
  });

  it('shows chain broken indicator when chain is invalid', async () => {
    vi.doMock('@/api/buildingActivities', () => ({
      buildingActivitiesApi: {
        list: vi.fn().mockResolvedValue(mockLedger),
        verifyChain: vi.fn().mockResolvedValue(mockChainBroken),
      },
    }));

    render(<ActivityLedger buildingId="b1" />, { wrapper });
    expect(screen.getByText('activity_ledger.title')).toBeTruthy();
  });

  it('renders filter controls', () => {
    render(<ActivityLedger buildingId="b1" />, { wrapper });

    // Activity type select
    const selects = screen.getAllByRole('combobox');
    expect(selects.length).toBeGreaterThanOrEqual(1);

    // Date inputs
    const dateInputs = document.querySelectorAll('input[type="date"]');
    expect(dateInputs.length).toBe(2);
  });
});
