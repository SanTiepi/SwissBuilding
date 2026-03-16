import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act } from '@testing-library/react';
import { PwaStatusIndicator } from '../PwaStatusIndicator';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

describe('PwaStatusIndicator', () => {
  let onLineSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(() => {
    vi.useFakeTimers();
    onLineSpy = vi.spyOn(navigator, 'onLine', 'get');
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  it('renders nothing when online', () => {
    onLineSpy.mockReturnValue(true);
    const { container } = render(<PwaStatusIndicator />);
    expect(container.innerHTML).toBe('');
  });

  it('shows offline banner when navigator.onLine is false', () => {
    onLineSpy.mockReturnValue(false);
    render(<PwaStatusIndicator />);
    expect(screen.getByTestId('pwa-status-indicator')).toBeTruthy();
    expect(screen.getByText('pwa.offline')).toBeTruthy();
  });

  it('shows offline banner on offline event', () => {
    onLineSpy.mockReturnValue(true);
    render(<PwaStatusIndicator />);
    expect(screen.queryByTestId('pwa-status-indicator')).toBeNull();

    act(() => {
      onLineSpy.mockReturnValue(false);
      window.dispatchEvent(new Event('offline'));
    });

    expect(screen.getByTestId('pwa-status-indicator')).toBeTruthy();
    expect(screen.getByText('pwa.offline')).toBeTruthy();
  });

  it('shows back-online message on online event after being offline', () => {
    onLineSpy.mockReturnValue(false);
    render(<PwaStatusIndicator />);
    expect(screen.getByText('pwa.offline')).toBeTruthy();

    act(() => {
      onLineSpy.mockReturnValue(true);
      window.dispatchEvent(new Event('online'));
    });

    expect(screen.getByTestId('pwa-status-indicator')).toBeTruthy();
    expect(screen.getByText('pwa.back_online')).toBeTruthy();
  });

  it('hides completely after back-online timeout', () => {
    onLineSpy.mockReturnValue(false);
    const { container } = render(<PwaStatusIndicator />);

    act(() => {
      onLineSpy.mockReturnValue(true);
      window.dispatchEvent(new Event('online'));
    });

    expect(screen.getByTestId('pwa-status-indicator')).toBeTruthy();

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(container.innerHTML).toBe('');
  });

  it('has correct data-testid', () => {
    onLineSpy.mockReturnValue(false);
    render(<PwaStatusIndicator />);
    expect(screen.getByTestId('pwa-status-indicator')).toBeTruthy();
  });
});
