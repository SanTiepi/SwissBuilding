import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import PostWorksTracker from '../../pages/Contractor/PostWorksTracker';

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock('@/api/client', () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
  }),
}));

const mockItems = [
  {
    id: 'item-1',
    building_id: 'b-1',
    work_item_id: null,
    building_element_id: null,
    completion_status: 'pending' as const,
    completion_date: null,
    contractor_id: 'c-1',
    photo_uris: null,
    before_after_pairs: null,
    notes: 'Replace insulation',
    verification_score: 0,
    flagged_for_review: false,
    ai_generated: false,
    created_at: '2026-04-01T10:00:00Z',
    updated_at: '2026-04-01T10:00:00Z',
  },
  {
    id: 'item-2',
    building_id: 'b-1',
    work_item_id: null,
    building_element_id: null,
    completion_status: 'completed' as const,
    completion_date: '2026-04-01T12:00:00Z',
    contractor_id: 'c-1',
    photo_uris: ['photo1.jpg'],
    before_after_pairs: [{ before_photo_id: 'a', after_photo_id: 'b' }],
    notes: 'Facade done',
    verification_score: 85,
    flagged_for_review: false,
    ai_generated: false,
    created_at: '2026-04-01T10:00:00Z',
    updated_at: '2026-04-01T12:00:00Z',
  },
];

const mockStatus = {
  building_id: 'b-1',
  total_items: 2,
  completed_items: 1,
  verified_items: 0,
  completion_percentage: 50.0,
  items_by_status: { pending: 1, completed: 1 },
  last_updated: '2026-04-01T12:00:00Z',
};

function setupMock(items: typeof mockItems, status: typeof mockStatus) {
  mockGet.mockImplementation((url: string) =>
    new Promise((resolve) =>
      setTimeout(() => {
        if (url.includes('post-work-items')) {
          resolve({ data: { items, total: items.length, page: 1, size: 20, pages: items.length > 0 ? 1 : 0 } });
        } else if (url.includes('completion-status')) {
          resolve({ data: status });
        } else {
          resolve({ data: {} });
        }
      }, 0),
    ),
  );
}

function renderTracker() {
  return render(
    <MemoryRouter initialEntries={['/contractor/buildings/b-1/post-works']}>
      <Routes>
        <Route
          path="/contractor/buildings/:buildingId/post-works"
          element={<PostWorksTracker />}
        />
      </Routes>
    </MemoryRouter>,
  );
}

describe('PostWorksTracker', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setupMock(mockItems, mockStatus);
  });

  it('renders the tracker page with title', async () => {
    renderTracker();
    await waitFor(() => {
      expect(screen.getByTestId('post-works-tracker')).toBeInTheDocument();
    });
  });

  it('displays completion percentage', async () => {
    renderTracker();
    await waitFor(() => {
      expect(screen.getByTestId('completion-pct')).toHaveTextContent('50.0%');
    });
  });

  it('shows progress bar', async () => {
    renderTracker();
    await waitFor(() => {
      expect(screen.getByTestId('progress-bar')).toBeInTheDocument();
    });
  });

  it('displays total and completed item counts', async () => {
    renderTracker();
    await waitFor(() => {
      expect(screen.getByTestId('total-items')).toHaveTextContent('2');
      expect(screen.getByTestId('completed-items')).toHaveTextContent('1');
    });
  });

  it('renders work items', async () => {
    renderTracker();
    await waitFor(() => {
      expect(screen.getByTestId('post-work-item-item-1')).toBeInTheDocument();
      expect(screen.getByTestId('post-work-item-item-2')).toBeInTheDocument();
    });
  });

  it('calls API with correct building ID', async () => {
    renderTracker();
    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(
        expect.stringContaining('/buildings/b-1/post-work-items'),
        expect.anything(),
      );
      expect(mockGet).toHaveBeenCalledWith(expect.stringContaining('/buildings/b-1/completion-status'));
    });
  });

  it('shows certificate button at 100%', async () => {
    setupMock(mockItems, {
      ...mockStatus,
      completion_percentage: 100,
      completed_items: 2,
      verified_items: 2,
    });

    renderTracker();
    await waitFor(() => {
      expect(screen.getByTestId('generate-certificate-btn')).toBeInTheDocument();
    });
  });

  it('does not show certificate button below 100%', async () => {
    renderTracker();
    await waitFor(() => {
      expect(screen.getByTestId('completion-pct')).toHaveTextContent('50.0%');
    });
    expect(screen.queryByTestId('generate-certificate-btn')).not.toBeInTheDocument();
  });

  it('shows status badges on items', async () => {
    renderTracker();
    await waitFor(() => {
      const statuses = screen.getAllByTestId('item-status');
      expect(statuses.length).toBe(2);
      expect(statuses[0]).toHaveTextContent('pending');
      expect(statuses[1]).toHaveTextContent('completed');
    });
  });

  it('filters by status when filter button clicked', async () => {
    renderTracker();
    await waitFor(() => {
      expect(screen.getByTestId('post-work-item-item-1')).toBeInTheDocument();
    });

    await act(async () => {
      fireEvent.click(screen.getByTestId('filter-pending'));
    });

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(
        expect.stringContaining('post-work-items'),
        expect.objectContaining({ params: { status: 'pending' } }),
      );
    });
  });
});
