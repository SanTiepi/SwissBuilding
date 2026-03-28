import { cn } from '@/utils/formatters';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface ConfidenceIndicatorProps {
  value: number; // 0.0 to 1.0
  size?: 'sm' | 'md';
  showValue?: boolean;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function dotColor(v: number): string {
  if (v >= 0.8) return 'bg-green-500';
  if (v >= 0.5) return 'bg-amber-500';
  return 'bg-red-500';
}

function textColor(v: number): string {
  if (v >= 0.8) return 'text-green-600 dark:text-green-400';
  if (v >= 0.5) return 'text-amber-600 dark:text-amber-400';
  return 'text-red-600 dark:text-red-400';
}

function bgColor(v: number): string {
  if (v >= 0.8) return 'bg-green-50 dark:bg-green-900/20';
  if (v >= 0.5) return 'bg-amber-50 dark:bg-amber-900/20';
  return 'bg-red-50 dark:bg-red-900/20';
}

function label(v: number): string {
  if (v >= 0.8) return 'Haute confiance';
  if (v >= 0.5) return 'Confiance moyenne';
  return 'Faible confiance';
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ConfidenceIndicator({ value, size = 'md', showValue }: ConfidenceIndicatorProps) {
  const clamped = Math.max(0, Math.min(1, value));
  const pct = Math.round(clamped * 100);
  const resolvedShowValue = showValue ?? size === 'md';
  const dotSize = size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5';
  const titleText = `${label(clamped)} (${pct}%)`;

  if (!resolvedShowValue) {
    return (
      <span
        className={cn('inline-block rounded-full shrink-0', dotSize, dotColor(clamped))}
        title={titleText}
        data-testid="confidence-indicator"
      />
    );
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium shrink-0',
        bgColor(clamped),
        textColor(clamped),
      )}
      title={titleText}
      data-testid="confidence-indicator"
    >
      <span className={cn('inline-block rounded-full shrink-0', dotSize, dotColor(clamped))} />
      {pct}%
    </span>
  );
}

export default ConfidenceIndicator;
