import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import OperatorWorkspace from '../../pages/OperatorWorkspace';

vi.mock('@/api/remediation', () => ({
  remediationApi: {
    getOperatorQueue: vi.fn().mockResolvedValue({
      active_rfqs: 4,
      quotes_received: 7,
      awards_pending: 2,
      completions_awaiting: 1,
      post_works_open: 3,
    }),
  },
}));

vi.mock('@/i18n', () => ({
  useTranslation: () => ({ t: (k: string) => k, language: 'fr', setLanguage: vi.fn() }),
}));

function renderWithProviders(ui: React.ReactElement) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>);
}

describe('OperatorWorkspace', () => {
  it('renders title', async () => {
    renderWithProviders(<OperatorWorkspace />);
    await waitFor(() => expect(screen.getByText('workspace.operator_title')).toBeTruthy());
  });

  it('renders queue counts', async () => {
    renderWithProviders(<OperatorWorkspace />);
    await waitFor(() => {
      expect(screen.getByText('4')).toBeTruthy();
      expect(screen.getByText('7')).toBeTruthy();
      expect(screen.getByText('2')).toBeTruthy();
      expect(screen.getByText('3')).toBeTruthy();
    });
  });

  it('renders all queue labels', async () => {
    renderWithProviders(<OperatorWorkspace />);
    await waitFor(() => {
      expect(screen.getByText('workspace.active_rfqs')).toBeTruthy();
      expect(screen.getByText('workspace.quotes_received')).toBeTruthy();
      expect(screen.getByText('workspace.awards_pending')).toBeTruthy();
      expect(screen.getByText('workspace.completions_awaiting')).toBeTruthy();
      expect(screen.getByText('workspace.post_works_open')).toBeTruthy();
    });
  });

  it('renders completions awaiting count', async () => {
    renderWithProviders(<OperatorWorkspace />);
    await waitFor(() => expect(screen.getByText('1')).toBeTruthy());
  });

  it('renders description text', async () => {
    renderWithProviders(<OperatorWorkspace />);
    await waitFor(() => expect(screen.getByText('workspace.operator_description')).toBeTruthy());
  });
});
