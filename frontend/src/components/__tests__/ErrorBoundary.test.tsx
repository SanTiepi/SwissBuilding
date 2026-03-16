import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ErrorBoundary, PageErrorBoundary } from '../ErrorBoundary';

// Suppress React error boundary console.error noise in tests
const originalConsoleError = console.error;
const suppressExpectedWindowError = (event: Event) => {
  const errorEvent = event as ErrorEvent;
  if (errorEvent.error instanceof Error && errorEvent.error.message === 'Something went wrong!') {
    event.preventDefault();
  }
};

beforeEach(() => {
  console.error = vi.fn();
  window.addEventListener('error', suppressExpectedWindowError);
});

afterEach(() => {
  console.error = originalConsoleError;
  window.removeEventListener('error', suppressExpectedWindowError);
});

function GoodChild() {
  return <div>Everything is fine</div>;
}

function BadChild(): JSX.Element {
  throw new Error('Something went wrong!');
}

describe('ErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <ErrorBoundary>
        <GoodChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Everything is fine')).toBeInTheDocument();
  });

  it('renders error fallback when a child throws', () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('displays the error message in the fallback', () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText('Something went wrong!')).toBeInTheDocument();
  });

  it('renders a reload button in the fallback', () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );

    const button = screen.getByTestId('error-boundary-reload');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Reload');
  });

  it('does not show error fallback when children render successfully', () => {
    render(
      <ErrorBoundary>
        <GoodChild />
      </ErrorBoundary>,
    );

    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
  });

  it('renders a Go to Dashboard link', () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );

    const link = screen.getByTestId('error-boundary-home');
    expect(link).toBeInTheDocument();
    expect(link).toHaveTextContent('Dashboard');
    expect(link).toHaveAttribute('href', '/dashboard');
  });

  it('renders a Copy error button', () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );

    const button = screen.getByTestId('error-boundary-copy');
    expect(button).toBeInTheDocument();
    expect(button).toHaveTextContent('Copy error');
  });

  it('displays error timestamp', () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );

    // Timestamp is an ISO string, check it contains a date-like pattern
    const boundary = screen.getByTestId('error-boundary');
    expect(boundary.textContent).toMatch(/\d{4}-\d{2}-\d{2}/);
  });

  it('toggles error details on click', () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );

    const toggleButton = screen.getByTestId('error-boundary-toggle-details');
    expect(toggleButton).toHaveTextContent('Show details');
    expect(screen.queryByTestId('error-boundary-details')).not.toBeInTheDocument();

    fireEvent.click(toggleButton);

    expect(toggleButton).toHaveTextContent('Hide details');
    expect(screen.getByTestId('error-boundary-details')).toBeInTheDocument();

    fireEvent.click(toggleButton);

    expect(toggleButton).toHaveTextContent('Show details');
    expect(screen.queryByTestId('error-boundary-details')).not.toBeInTheDocument();
  });

  it('has data-testid on the boundary container', () => {
    render(
      <ErrorBoundary>
        <BadChild />
      </ErrorBoundary>,
    );

    expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
  });
});

describe('PageErrorBoundary', () => {
  it('renders children when there is no error', () => {
    render(
      <PageErrorBoundary pageName="Test Page">
        <GoodChild />
      </PageErrorBoundary>,
    );

    expect(screen.getByText('Everything is fine')).toBeInTheDocument();
  });

  it('renders error fallback with page name when a child throws', () => {
    render(
      <PageErrorBoundary pageName="Test Page">
        <BadChild />
      </PageErrorBoundary>,
    );

    expect(screen.getByText('Error loading Test Page')).toBeInTheDocument();
  });

  it('renders fallback without page name', () => {
    render(
      <PageErrorBoundary>
        <BadChild />
      </PageErrorBoundary>,
    );

    expect(screen.getByText('An error occurred / Une erreur est survenue')).toBeInTheDocument();
  });

  it('displays the error message', () => {
    render(
      <PageErrorBoundary pageName="Test Page">
        <BadChild />
      </PageErrorBoundary>,
    );

    expect(screen.getByText('Something went wrong!')).toBeInTheDocument();
  });

  it('has a retry button that resets error state', () => {
    let shouldThrow = true;
    function MaybeBadChild(): JSX.Element {
      if (shouldThrow) {
        throw new Error('Something went wrong!');
      }
      return <div>Recovered</div>;
    }

    render(
      <PageErrorBoundary pageName="Test Page">
        <MaybeBadChild />
      </PageErrorBoundary>,
    );

    expect(screen.getByText('Error loading Test Page')).toBeInTheDocument();

    // Stop throwing before retry
    shouldThrow = false;
    const retryButton = screen.getByTestId('page-error-retry');
    fireEvent.click(retryButton);

    expect(screen.getByText('Recovered')).toBeInTheDocument();
  });

  it('shows retry count after retrying', () => {
    function AlwaysBadChild(): JSX.Element {
      throw new Error('Something went wrong!');
    }

    render(
      <PageErrorBoundary pageName="Test Page">
        <AlwaysBadChild />
      </PageErrorBoundary>,
    );

    // Initially no retry count
    expect(screen.queryByTestId('page-error-retry-count')).not.toBeInTheDocument();

    // Click retry — component will throw again
    fireEvent.click(screen.getByTestId('page-error-retry'));

    // Now retry count should show
    const retryCountEl = screen.getByTestId('page-error-retry-count');
    expect(retryCountEl).toBeInTheDocument();
    expect(retryCountEl).toHaveTextContent('Retried 1 time');

    // Retry again
    fireEvent.click(screen.getByTestId('page-error-retry'));
    expect(screen.getByTestId('page-error-retry-count')).toHaveTextContent('Retried 2 times');
  });

  it('has a Go back button', () => {
    render(
      <PageErrorBoundary pageName="Test Page">
        <BadChild />
      </PageErrorBoundary>,
    );

    const backButton = screen.getByTestId('page-error-back');
    expect(backButton).toBeInTheDocument();
    expect(backButton).toHaveTextContent('Go back');
  });

  it('calls window.history.back when Go back is clicked', () => {
    const backSpy = vi.spyOn(window.history, 'back').mockImplementation(() => {});

    render(
      <PageErrorBoundary pageName="Test Page">
        <BadChild />
      </PageErrorBoundary>,
    );

    fireEvent.click(screen.getByTestId('page-error-back'));
    expect(backSpy).toHaveBeenCalledOnce();

    backSpy.mockRestore();
  });

  it('has a Copy button', () => {
    render(
      <PageErrorBoundary pageName="Test Page">
        <BadChild />
      </PageErrorBoundary>,
    );

    const copyButton = screen.getByTestId('page-error-copy');
    expect(copyButton).toBeInTheDocument();
    expect(copyButton).toHaveTextContent('Copy');
  });

  it('toggles error details', () => {
    render(
      <PageErrorBoundary pageName="Test Page">
        <BadChild />
      </PageErrorBoundary>,
    );

    const toggleButton = screen.getByTestId('page-error-toggle-details');
    expect(toggleButton).toHaveTextContent('Show details');
    expect(screen.queryByTestId('page-error-details')).not.toBeInTheDocument();

    fireEvent.click(toggleButton);

    expect(toggleButton).toHaveTextContent('Hide details');
    expect(screen.getByTestId('page-error-details')).toBeInTheDocument();

    fireEvent.click(toggleButton);

    expect(screen.queryByTestId('page-error-details')).not.toBeInTheDocument();
  });

  it('has dark mode classes on the container', () => {
    render(
      <PageErrorBoundary pageName="Test Page">
        <BadChild />
      </PageErrorBoundary>,
    );

    const boundary = screen.getByTestId('page-error-boundary');
    const card = boundary.firstElementChild;
    expect(card?.className).toContain('dark:bg-slate-800');
    expect(card?.className).toContain('dark:border-slate-700');
  });

  it('displays error timestamp', () => {
    render(
      <PageErrorBoundary pageName="Test Page">
        <BadChild />
      </PageErrorBoundary>,
    );

    const boundary = screen.getByTestId('page-error-boundary');
    expect(boundary.textContent).toMatch(/\d{4}-\d{2}-\d{2}/);
  });

  it('has data-testid on the boundary container', () => {
    render(
      <PageErrorBoundary pageName="Test Page">
        <BadChild />
      </PageErrorBoundary>,
    );

    expect(screen.getByTestId('page-error-boundary')).toBeInTheDocument();
  });
});
