import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import RulesPackStudio from '@/pages/RulesPackStudio';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

vi.mock('@/store/authStore', () => ({
  useAuthStore: Object.assign(
    () => ({
      user: { role: 'admin' },
    }),
    {
      getState: () => ({
        user: { role: 'admin' },
      }),
    },
  ),
}));

vi.mock('@/api/regulatoryPacks', () => ({
  regulatoryPacksApi: {
    listAll: vi.fn().mockResolvedValue([]),
    comparePacks: vi.fn().mockReturnValue([]),
  },
}));

vi.mock('@/api/jurisdictions', () => ({
  jurisdictionsApi: {
    list: vi.fn().mockResolvedValue({ items: [], total: 0, page: 1, size: 200, pages: 0 }),
  },
}));

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
};

describe('RulesPackStudio mobile disclosure', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders mobile desktop-hint banner with correct i18n key', () => {
    render(<RulesPackStudio />, { wrapper: createWrapper() });

    const banner = screen.getByTestId('mobile-desktop-hint');
    expect(banner).toBeInTheDocument();
    expect(banner).toHaveTextContent('rules_studio.desktop_hint');
  });

  it('banner has md:hidden class so it only shows on mobile', () => {
    render(<RulesPackStudio />, { wrapper: createWrapper() });

    const banner = screen.getByTestId('mobile-desktop-hint');
    expect(banner.className).toContain('md:hidden');
  });

  it('renders page title for admin users', () => {
    render(<RulesPackStudio />, { wrapper: createWrapper() });

    expect(screen.getByText('rules_studio.title')).toBeInTheDocument();
  });
});
