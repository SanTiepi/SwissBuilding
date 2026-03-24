import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import MissionOrderCard, {
  type DiagnosticMissionOrder,
} from '../building-detail/MissionOrderCard';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

const MOCK_ORDERS: DiagnosticMissionOrder[] = [
  {
    id: 'mo-1',
    building_id: 'b-1',
    mission_type: 'asbestos_full',
    status: 'acknowledged',
    external_mission_id: 'EXT-42',
    context_notes: 'Urgent inspection needed before renovation',
    last_error: null,
    created_at: '2026-03-20T10:00:00Z',
  },
  {
    id: 'mo-2',
    building_id: 'b-1',
    mission_type: 'pcb',
    status: 'failed',
    external_mission_id: null,
    context_notes: null,
    last_error: 'Connection timeout to lab API',
    created_at: '2026-03-19T14:00:00Z',
  },
  {
    id: 'mo-3',
    building_id: 'b-1',
    mission_type: 'lead',
    status: 'draft',
    external_mission_id: null,
    context_notes: 'A'.repeat(200),
    last_error: null,
    created_at: '2026-03-18T09:00:00Z',
  },
];

describe('MissionOrderCard', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders empty state when no orders', () => {
    render(<MissionOrderCard orders={[]} />);
    expect(screen.getByTestId('mission-empty-state')).toBeInTheDocument();
  });

  it('renders order list with status badges', () => {
    render(<MissionOrderCard orders={MOCK_ORDERS} />);
    const items = screen.getAllByTestId('mission-order-item');
    expect(items).toHaveLength(3);
    const badges = screen.getAllByTestId('mission-status-badge');
    expect(badges).toHaveLength(3);
  });

  it('shows external mission ID when present', () => {
    render(<MissionOrderCard orders={MOCK_ORDERS} />);
    expect(screen.getByTestId('mission-external-id')).toHaveTextContent('EXT-42');
  });

  it('shows error message for failed orders', () => {
    render(<MissionOrderCard orders={MOCK_ORDERS} />);
    expect(screen.getByTestId('mission-error')).toHaveTextContent('Connection timeout to lab API');
  });

  it('truncates long context notes with expand toggle', () => {
    render(<MissionOrderCard orders={MOCK_ORDERS} />);
    const toggle = screen.getByTestId('toggle-notes');
    expect(toggle).toBeInTheDocument();
    // Click to expand
    fireEvent.click(toggle);
    // Full text should be visible (200 chars of 'A')
    expect(screen.getByText('A'.repeat(200))).toBeInTheDocument();
  });

  it('shows create button when onSubmit is provided', () => {
    render(<MissionOrderCard orders={[]} onSubmit={vi.fn()} />);
    expect(screen.getByTestId('create-mission-btn')).toBeInTheDocument();
  });

  it('does not show create button when onSubmit is not provided', () => {
    render(<MissionOrderCard orders={[]} />);
    expect(screen.queryByTestId('create-mission-btn')).not.toBeInTheDocument();
  });

  it('opens and closes create form', () => {
    render(<MissionOrderCard orders={[]} onSubmit={vi.fn()} />);
    fireEvent.click(screen.getByTestId('create-mission-btn'));
    expect(screen.getByTestId('mission-create-form')).toBeInTheDocument();

    fireEvent.click(screen.getByTestId('mission-cancel-btn'));
    expect(screen.queryByTestId('mission-create-form')).not.toBeInTheDocument();
  });

  it('submits form with selected values', () => {
    const onSubmit = vi.fn();
    render(<MissionOrderCard orders={[]} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByTestId('create-mission-btn'));

    // Change mission type
    fireEvent.change(screen.getByTestId('mission-type-select'), {
      target: { value: 'pcb' },
    });

    // Enter context notes
    fireEvent.change(screen.getByTestId('mission-context-textarea'), {
      target: { value: 'Test notes' },
    });

    fireEvent.click(screen.getByTestId('mission-submit-btn'));

    expect(onSubmit).toHaveBeenCalledWith({
      mission_type: 'pcb',
      context_notes: 'Test notes',
    });
  });

  it('resets form after submission', () => {
    const onSubmit = vi.fn();
    render(<MissionOrderCard orders={[]} onSubmit={onSubmit} />);
    fireEvent.click(screen.getByTestId('create-mission-btn'));

    fireEvent.change(screen.getByTestId('mission-context-textarea'), {
      target: { value: 'Some notes' },
    });
    fireEvent.click(screen.getByTestId('mission-submit-btn'));

    // Form should be closed
    expect(screen.queryByTestId('mission-create-form')).not.toBeInTheDocument();
  });

  it('renders mission type labels via i18n keys', () => {
    render(<MissionOrderCard orders={MOCK_ORDERS} />);
    // With mocked t() returning the key, we should see the i18n keys
    expect(screen.getByText('mission_order.type.asbestos_full')).toBeInTheDocument();
    expect(screen.getByText('mission_order.type.pcb')).toBeInTheDocument();
  });

  it('disables submit button when isSubmitting', () => {
    render(<MissionOrderCard orders={[]} onSubmit={vi.fn()} isSubmitting />);
    fireEvent.click(screen.getByTestId('create-mission-btn'));
    expect(screen.getByTestId('mission-submit-btn')).toBeDisabled();
  });
});
