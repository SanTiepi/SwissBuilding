import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockUser = { organization_id: 'org-1', role: 'admin' };
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn((selector: (s: { user: typeof mockUser }) => unknown) => selector({ user: mockUser })),
}));

const mockGetValueEvents = vi.fn();
vi.mock('@/api/intelligence', () => ({
  intelligenceApi: {
    getValueEvents: (...args: unknown[]) => mockGetValueEvents(...args),
  },
}));

import { ValuePulse } from '../ValuePulse';

function wrap(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('ValuePulse', () => {
  it('renders pulse indicator when events exist', async () => {
    mockGetValueEvents.mockResolvedValue([
      {
        event_type: 'contradiction_resolved',
        building_id: 'b-1',
        delta_description: 'Contradiction resolue sur amiante',
        created_at: '2026-03-01T10:00:00Z',
      },
    ]);
    wrap(<ValuePulse />);

    const status = await screen.findByRole('status');
    expect(status).toBeInTheDocument();
    expect(status).toHaveTextContent('+1 contradiction resolue');
  });

  it('dismisses on close button click', async () => {
    mockGetValueEvents.mockResolvedValue([
      {
        event_type: 'source_unified',
        building_id: 'b-1',
        delta_description: 'Source ajoutee',
        created_at: '2026-03-01T10:00:00Z',
      },
    ]);
    wrap(<ValuePulse />);

    await screen.findByRole('status');
    fireEvent.click(screen.getByLabelText('Dismiss'));
    // After dismiss, status element should be gone or invisible
    expect(screen.queryByRole('status')).toBeNull();
  });
});
