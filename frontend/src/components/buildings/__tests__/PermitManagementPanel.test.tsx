import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClientProvider, QueryClient } from '@tanstack/react-query';
import { PermitManagementPanel } from '../PermitManagementPanel';
import * as permitsApi from '@/api/permits';

vi.mock('@/api/permits');

const queryClient = new QueryClient();

const mockPermits = [
  {
    id: 'permit-1',
    building_id: 'building-1',
    permit_type: 'renovation',
    status: 'approved',
    issued_date: '2024-01-01',
    expiry_date: '2025-12-31',
    notes: 'Permit for renovation',
  },
];

const mockAlerts = [
  {
    permit_id: 'permit-1',
    message: 'Permit expiring soon',
    action: 'Renew permit',
    severity: 'warning' as const,
  },
];

const renderComponent = () => {
  return render(
    <QueryClientProvider client={queryClient}>
      <PermitManagementPanel buildingId="building-1" />
    </QueryClientProvider>
  );
};

describe('PermitManagementPanel', () => {
  it('renders the panel with title', async () => {
    vi.mocked(permitsApi.permitsApi.list).mockResolvedValue(mockPermits);
    vi.mocked(permitsApi.permitsApi.getAlerts).mockResolvedValue(mockAlerts);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/Permis & Deadlines/i)).toBeInTheDocument();
    });
  });

  it('displays permits list', async () => {
    vi.mocked(permitsApi.permitsApi.list).mockResolvedValue(mockPermits);
    vi.mocked(permitsApi.permitsApi.getAlerts).mockResolvedValue([]);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/renovation/i)).toBeInTheDocument();
    });
  });

  it('displays alerts when present', async () => {
    vi.mocked(permitsApi.permitsApi.list).mockResolvedValue(mockPermits);
    vi.mocked(permitsApi.permitsApi.getAlerts).mockResolvedValue(mockAlerts);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/Permit expiring soon/i)).toBeInTheDocument();
    });
  });

  it('shows add permit button', async () => {
    vi.mocked(permitsApi.permitsApi.list).mockResolvedValue([]);
    vi.mocked(permitsApi.permitsApi.getAlerts).mockResolvedValue([]);

    renderComponent();

    await waitFor(() => {
      const addButton = screen.getByText(/Ajouter permis/i);
      expect(addButton).toBeInTheDocument();
    });
  });

  it('opens add permit form when button clicked', async () => {
    vi.mocked(permitsApi.permitsApi.list).mockResolvedValue([]);
    vi.mocked(permitsApi.permitsApi.getAlerts).mockResolvedValue([]);

    renderComponent();

    const addButton = await screen.findByText(/Ajouter permis/i);
    fireEvent.click(addButton);

    await waitFor(() => {
      expect(screen.getByText(/Nouveau permis/i)).toBeInTheDocument();
    });
  });
});
