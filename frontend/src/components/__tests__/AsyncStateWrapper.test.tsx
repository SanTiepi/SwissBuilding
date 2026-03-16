import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AsyncStateWrapper } from '../AsyncStateWrapper';

vi.mock('@/i18n', () => ({
  useTranslation: () => ({
    t: (key: string) => key,
    locale: 'fr',
    setLocale: vi.fn(),
  }),
}));

describe('AsyncStateWrapper', () => {
  it('renders loading spinner by default', () => {
    const { container } = render(
      <AsyncStateWrapper isLoading isError={false} data={null}>
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    expect(container.querySelector('.animate-spin')).toBeTruthy();
    expect(screen.queryByText('Content')).toBeNull();
  });

  it('renders loading skeleton when loadingType is skeleton', () => {
    const { container } = render(
      <AsyncStateWrapper isLoading isError={false} data={null} loadingType="skeleton">
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    expect(container.querySelector('.animate-pulse')).toBeTruthy();
    expect(screen.queryByText('Content')).toBeNull();
  });

  it('sets aria-busy and role=status on loading container', () => {
    const { container } = render(
      <AsyncStateWrapper isLoading isError={false} data={null}>
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.getAttribute('role')).toBe('status');
    expect(wrapper.getAttribute('aria-busy')).toBe('true');
  });

  it('provides sr-only loading text for spinner', () => {
    render(
      <AsyncStateWrapper isLoading isError={false} data={null}>
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    const srText = document.querySelector('.sr-only');
    expect(srText).toBeTruthy();
    expect(srText?.textContent).toContain('Loading');
  });

  it('provides sr-only loading text for skeleton', () => {
    render(
      <AsyncStateWrapper isLoading isError={false} data={null} loadingType="skeleton">
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    const srText = document.querySelector('.sr-only');
    expect(srText).toBeTruthy();
    expect(srText?.textContent).toContain('Loading');
  });

  it('renders error state with role=alert', () => {
    const { container } = render(
      <AsyncStateWrapper isLoading={false} isError data={null}>
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.getAttribute('role')).toBe('alert');
    expect(screen.getByText('app.loading_error')).toBeTruthy();
    expect(screen.queryByText('Content')).toBeNull();
  });

  it('renders error state with custom message', () => {
    render(
      <AsyncStateWrapper isLoading={false} isError data={null} errorMessage="Custom error">
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    expect(screen.getByText('Custom error')).toBeTruthy();
  });

  it('renders empty state for null data', () => {
    render(
      <AsyncStateWrapper isLoading={false} isError={false} data={null}>
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    expect(screen.getByText('app.no_data')).toBeTruthy();
    expect(screen.queryByText('Content')).toBeNull();
  });

  it('renders empty state for empty array', () => {
    render(
      <AsyncStateWrapper isLoading={false} isError={false} data={[]}>
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    expect(screen.getByText('app.no_data')).toBeTruthy();
    expect(screen.queryByText('Content')).toBeNull();
  });

  it('renders children when data is present', () => {
    render(
      <AsyncStateWrapper isLoading={false} isError={false} data={{ id: 1 }}>
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    expect(screen.getByText('Content')).toBeTruthy();
  });

  it('respects isEmpty override', () => {
    render(
      <AsyncStateWrapper isLoading={false} isError={false} data={{ id: 1 }} isEmpty>
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    expect(screen.getByText('app.no_data')).toBeTruthy();
    expect(screen.queryByText('Content')).toBeNull();
  });

  it('renders title and icon in error state', () => {
    render(
      <AsyncStateWrapper isLoading={false} isError data={null} title="My Section">
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    expect(screen.getByText('My Section')).toBeTruthy();
    expect(screen.getByText('app.loading_error')).toBeTruthy();
  });

  it('applies variant classes', () => {
    const { container } = render(
      <AsyncStateWrapper isLoading={false} isError={false} data={{ id: 1 }} variant="inline">
        <p>Content</p>
      </AsyncStateWrapper>,
    );
    const wrapper = container.firstElementChild as HTMLElement;
    expect(wrapper.classList.contains('p-2')).toBe(true);
  });
});
