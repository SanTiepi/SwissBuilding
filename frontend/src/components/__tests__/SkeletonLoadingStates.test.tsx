import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import {
  Skeleton,
  SkeletonLine,
  SkeletonBlock,
  InlineSkeleton,
  CardSkeleton,
  TableSkeleton,
  BuildingDetailSkeleton,
  DiagnosticViewSkeleton,
  DashboardSkeleton,
} from '../Skeleton';

describe('Skeleton primitives', () => {
  describe('Skeleton (base)', () => {
    it('renders with animate-pulse', () => {
      const { container } = render(<Skeleton />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.classList.contains('animate-pulse')).toBe(true);
    });

    it('applies dark mode background class', () => {
      const { container } = render(<Skeleton />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.className).toContain('dark:bg-slate-600');
    });

    it('accepts custom className', () => {
      const { container } = render(<Skeleton className="h-8 w-24" />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.classList.contains('h-8')).toBe(true);
      expect(el.classList.contains('w-24')).toBe(true);
    });
  });

  describe('SkeletonLine', () => {
    it('renders with default full width', () => {
      const { container } = render(<SkeletonLine />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.className).toContain('w-full');
      expect(el.className).toContain('h-4');
    });

    it('accepts custom width', () => {
      const { container } = render(<SkeletonLine width="w-1/2" />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.className).toContain('w-1/2');
    });

    it('has dark mode support', () => {
      const { container } = render(<SkeletonLine />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.className).toContain('dark:bg-slate-600');
    });
  });

  describe('SkeletonBlock', () => {
    it('renders with default dimensions', () => {
      const { container } = render(<SkeletonBlock />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.className).toContain('h-24');
      expect(el.className).toContain('w-full');
      expect(el.className).toContain('rounded-lg');
    });

    it('accepts custom height and width', () => {
      const { container } = render(<SkeletonBlock height="h-48" width="w-64" />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.className).toContain('h-48');
      expect(el.className).toContain('w-64');
    });

    it('has dark mode support', () => {
      const { container } = render(<SkeletonBlock />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.className).toContain('dark:bg-slate-600');
    });
  });

  describe('InlineSkeleton', () => {
    it('has role=status and aria-busy', () => {
      const { container } = render(<InlineSkeleton />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.getAttribute('role')).toBe('status');
      expect(el.getAttribute('aria-busy')).toBe('true');
    });

    it('includes sr-only loading text', () => {
      const { container } = render(<InlineSkeleton />);
      const srOnly = container.querySelector('.sr-only');
      expect(srOnly).toBeTruthy();
      expect(srOnly?.textContent).toContain('Loading');
    });

    it('renders 3 lines by default for card variant', () => {
      const { container } = render(<InlineSkeleton variant="card" />);
      const lines = container.querySelectorAll('.rounded.bg-gray-200');
      expect(lines.length).toBe(3);
    });

    it('renders max 2 lines for inline variant', () => {
      const { container } = render(<InlineSkeleton variant="inline" />);
      const lines = container.querySelectorAll('.rounded.bg-gray-200');
      expect(lines.length).toBe(2);
    });

    it('has dark mode classes on skeleton bars', () => {
      const { container } = render(<InlineSkeleton />);
      const line = container.querySelector('.rounded.bg-gray-200') as HTMLElement;
      expect(line.className).toContain('dark:bg-slate-600');
    });
  });
});

describe('Composite skeletons', () => {
  describe('CardSkeleton', () => {
    it('has role=status and aria-busy', () => {
      const { container } = render(<CardSkeleton />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.getAttribute('role')).toBe('status');
      expect(el.getAttribute('aria-busy')).toBe('true');
    });

    it('includes sr-only loading text', () => {
      const { container } = render(<CardSkeleton />);
      const srOnly = container.querySelector('.sr-only');
      expect(srOnly).toBeTruthy();
    });

    it('has dark mode classes', () => {
      const { container } = render(<CardSkeleton />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.className).toContain('dark:bg-slate-800');
    });

    it('renders animate-pulse children', () => {
      const { container } = render(<CardSkeleton />);
      expect(container.querySelectorAll('.animate-pulse').length).toBeGreaterThan(0);
    });
  });

  describe('TableSkeleton', () => {
    it('has role=status and aria-busy', () => {
      const { container } = render(<TableSkeleton />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.getAttribute('role')).toBe('status');
      expect(el.getAttribute('aria-busy')).toBe('true');
    });

    it('renders correct default row count (5)', () => {
      const { container } = render(<TableSkeleton />);
      // Each row is a flex container with gap-4
      const rows = container.querySelectorAll('.flex.gap-4');
      expect(rows.length).toBe(5);
    });

    it('renders custom rows and cols', () => {
      const { container } = render(<TableSkeleton rows={3} cols={2} />);
      const rows = container.querySelectorAll('.flex.gap-4');
      expect(rows.length).toBe(3);
      // Each row should have 2 skeleton cells
      rows.forEach((row) => {
        expect(row.querySelectorAll('.animate-pulse').length).toBe(2);
      });
    });

    it('includes sr-only loading text', () => {
      const { container } = render(<TableSkeleton />);
      const srOnly = container.querySelector('.sr-only');
      expect(srOnly).toBeTruthy();
    });
  });

  describe('BuildingDetailSkeleton', () => {
    it('has role=status and aria-busy', () => {
      const { container } = render(<BuildingDetailSkeleton />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.getAttribute('role')).toBe('status');
      expect(el.getAttribute('aria-busy')).toBe('true');
    });

    it('includes sr-only loading text', () => {
      const { container } = render(<BuildingDetailSkeleton />);
      const srOnly = container.querySelector('.sr-only');
      expect(srOnly).toBeTruthy();
    });

    it('has dark mode classes throughout', () => {
      const { container } = render(<BuildingDetailSkeleton />);
      const darkElements = container.querySelectorAll('[class*="dark:"]');
      expect(darkElements.length).toBeGreaterThan(5);
    });
  });

  describe('DiagnosticViewSkeleton', () => {
    it('has role=status and aria-busy', () => {
      const { container } = render(<DiagnosticViewSkeleton />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.getAttribute('role')).toBe('status');
      expect(el.getAttribute('aria-busy')).toBe('true');
    });

    it('includes sr-only loading text', () => {
      const { container } = render(<DiagnosticViewSkeleton />);
      const srOnly = container.querySelector('.sr-only');
      expect(srOnly).toBeTruthy();
    });

    it('has dark mode classes throughout', () => {
      const { container } = render(<DiagnosticViewSkeleton />);
      const darkElements = container.querySelectorAll('[class*="dark:"]');
      expect(darkElements.length).toBeGreaterThan(5);
    });
  });

  describe('DashboardSkeleton', () => {
    it('has role=status and aria-busy', () => {
      const { container } = render(<DashboardSkeleton />);
      const el = container.firstElementChild as HTMLElement;
      expect(el.getAttribute('role')).toBe('status');
      expect(el.getAttribute('aria-busy')).toBe('true');
    });

    it('includes sr-only loading text', () => {
      const { container } = render(<DashboardSkeleton />);
      const srOnly = container.querySelector('.sr-only');
      expect(srOnly).toBeTruthy();
    });

    it('has dark mode classes throughout', () => {
      const { container } = render(<DashboardSkeleton />);
      const darkElements = container.querySelectorAll('[class*="dark:"]');
      expect(darkElements.length).toBeGreaterThan(5);
    });

    it('renders KPI card skeletons (4)', () => {
      const { container } = render(<DashboardSkeleton />);
      // 4 KPI cards each with rounded-xl class in the grid
      const kpiGrid = container.querySelector('.grid.grid-cols-1.sm\\:grid-cols-2.lg\\:grid-cols-4');
      expect(kpiGrid).toBeTruthy();
      expect(kpiGrid?.children.length).toBe(4);
    });
  });
});
