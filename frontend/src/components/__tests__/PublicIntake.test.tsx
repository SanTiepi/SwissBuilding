import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import PublicIntake from '@/pages/PublicIntake';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/utils/formatters', () => ({
  cn: (...classes: (string | undefined | false)[]) => classes.filter(Boolean).join(' '),
}));

const mockSubmit = vi.fn();
vi.mock('@/api/intake', () => ({
  intakeApi: {
    submit: (...args: unknown[]) => mockSubmit(...args),
  },
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <PublicIntake />
    </MemoryRouter>,
  );
}

describe('PublicIntake', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });
  afterEach(cleanup);

  it('renders the form with all required fields', () => {
    renderPage();
    expect(screen.getByTestId('intake-name')).toBeInTheDocument();
    expect(screen.getByTestId('intake-email')).toBeInTheDocument();
    expect(screen.getByTestId('intake-address')).toBeInTheDocument();
    expect(screen.getByTestId('intake-submit')).toBeInTheDocument();
  });

  it('renders optional fields', () => {
    renderPage();
    expect(screen.getByTestId('intake-phone')).toBeInTheDocument();
    expect(screen.getByTestId('intake-company')).toBeInTheDocument();
    expect(screen.getByTestId('intake-city')).toBeInTheDocument();
    expect(screen.getByTestId('intake-postal-code')).toBeInTheDocument();
    expect(screen.getByTestId('intake-egid')).toBeInTheDocument();
  });

  it('renders request type and urgency dropdowns', () => {
    renderPage();
    expect(screen.getByTestId('intake-request-type')).toBeInTheDocument();
    expect(screen.getByTestId('intake-urgency')).toBeInTheDocument();
  });

  it('renders description textarea', () => {
    renderPage();
    expect(screen.getByTestId('intake-description')).toBeInTheDocument();
  });

  it('renders urgency badge', () => {
    renderPage();
    expect(screen.getByTestId('intake-urgency-badge')).toBeInTheDocument();
  });

  it('updates form fields on change', () => {
    renderPage();
    const nameInput = screen.getByTestId('intake-name') as HTMLInputElement;
    fireEvent.change(nameInput, { target: { value: 'Jean Dupont', name: 'requester_name' } });
    expect(nameInput.value).toBe('Jean Dupont');
  });

  it('submits the form and shows success', async () => {
    mockSubmit.mockResolvedValueOnce({ id: '1', status: 'new' });
    renderPage();

    fireEvent.change(screen.getByTestId('intake-name'), { target: { value: 'Jean', name: 'requester_name' } });
    fireEvent.change(screen.getByTestId('intake-email'), { target: { value: 'j@test.ch', name: 'requester_email' } });
    fireEvent.change(screen.getByTestId('intake-address'), {
      target: { value: 'Rue Test 1', name: 'building_address' },
    });

    fireEvent.click(screen.getByTestId('intake-submit'));

    await waitFor(() => {
      expect(screen.getByTestId('intake-success')).toBeInTheDocument();
    });
    expect(mockSubmit).toHaveBeenCalledTimes(1);
    expect(mockSubmit).toHaveBeenCalledWith(
      expect.objectContaining({
        requester_name: 'Jean',
        requester_email: 'j@test.ch',
        building_address: 'Rue Test 1',
        request_type: 'asbestos_diagnostic',
        source: 'website',
      }),
    );
  });

  it('shows error on submit failure', async () => {
    mockSubmit.mockRejectedValueOnce(new Error('fail'));
    renderPage();

    fireEvent.change(screen.getByTestId('intake-name'), { target: { value: 'Jean', name: 'requester_name' } });
    fireEvent.change(screen.getByTestId('intake-email'), { target: { value: 'j@test.ch', name: 'requester_email' } });
    fireEvent.change(screen.getByTestId('intake-address'), {
      target: { value: 'Rue Test 1', name: 'building_address' },
    });

    fireEvent.click(screen.getByTestId('intake-submit'));

    await waitFor(() => {
      expect(screen.getByText('intake.submit_error')).toBeInTheDocument();
    });
  });

  it('renders the branded header', () => {
    renderPage();
    expect(screen.getByText('BatiConnect')).toBeInTheDocument();
  });

  it('has no auth requirement (renders without auth store)', () => {
    // If it renders without error, it does not require auth
    renderPage();
    expect(screen.getByTestId('intake-submit')).toBeInTheDocument();
  });
});
