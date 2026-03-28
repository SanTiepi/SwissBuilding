import { cn } from '@/utils/formatters';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export type ConfidenceLevel =
  | 'raw'
  | 'enriched'
  | 'validated'
  | 'published'
  | 'inherited'
  | 'contradictory';

export interface ConfidenceBadgeProps {
  level: ConfidenceLevel;
  size?: 'sm' | 'md';
  showLabel?: boolean;
  tooltip?: string;
  source?: string; // for inherited: "Diagnostic 2022"
  date?: string; // for inherited: original date
}

/* ------------------------------------------------------------------ */
/*  Level config                                                       */
/* ------------------------------------------------------------------ */

interface LevelConfig {
  label: string;
  description: string;
  dotClass: string;
  textClass: string;
  bgClass: string;
}

const LEVEL_CONFIG: Record<ConfidenceLevel, LevelConfig> = {
  raw: {
    label: 'Source brute',
    description: 'Document importe, non analyse',
    dotClass: 'bg-gray-400 dark:bg-slate-500',
    textClass: 'text-gray-600 dark:text-slate-400',
    bgClass: 'bg-gray-100 dark:bg-slate-700',
  },
  enriched: {
    label: 'Enrichi',
    description: 'Extrait par IA, non encore valide',
    dotClass: 'bg-amber-400 dark:bg-amber-500',
    textClass: 'text-amber-700 dark:text-amber-300',
    bgClass: 'bg-amber-50 dark:bg-amber-900/20',
  },
  validated: {
    label: 'Valide',
    description: 'Confirme par un expert',
    dotClass: 'bg-green-500 dark:bg-green-400',
    textClass: 'text-green-700 dark:text-green-300',
    bgClass: 'bg-green-50 dark:bg-green-900/20',
  },
  published: {
    label: 'Publie',
    description: 'Publie dans BatiConnect',
    dotClass: 'bg-blue-500 dark:bg-blue-400',
    textClass: 'text-blue-700 dark:text-blue-300',
    bgClass: 'bg-blue-50 dark:bg-blue-900/20',
  },
  inherited: {
    label: 'Herite',
    description: 'Reutilise depuis un cycle precedent',
    dotClass: 'bg-purple-500 dark:bg-purple-400',
    textClass: 'text-purple-700 dark:text-purple-300',
    bgClass: 'bg-purple-50 dark:bg-purple-900/20',
  },
  contradictory: {
    label: 'Contradictoire',
    description: 'Deux sources se contredisent',
    dotClass: 'bg-red-500 dark:bg-red-400',
    textClass: 'text-red-700 dark:text-red-300',
    bgClass: 'bg-red-50 dark:bg-red-900/20',
  },
};

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function ConfidenceBadge({
  level,
  size = 'md',
  showLabel,
  tooltip,
  source,
  date,
}: ConfidenceBadgeProps) {
  const config = LEVEL_CONFIG[level];
  const resolvedShowLabel = showLabel ?? size === 'md';

  // Build tooltip text
  let titleText = tooltip ?? config.description;
  if (level === 'inherited') {
    const parts: string[] = [config.description];
    if (source) parts.push(`Source: ${source}`);
    if (date) parts.push(`Date: ${date}`);
    titleText = tooltip ?? parts.join('\n');
  }

  const dotSize = size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5';

  if (!resolvedShowLabel) {
    // Dot only
    return (
      <span
        className={cn('inline-block rounded-full shrink-0', dotSize, config.dotClass)}
        title={titleText}
        data-testid={`confidence-badge-${level}`}
      />
    );
  }

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-[11px] font-medium shrink-0',
        config.bgClass,
        config.textClass,
      )}
      title={titleText}
      data-testid={`confidence-badge-${level}`}
    >
      <span className={cn('inline-block rounded-full shrink-0', dotSize, config.dotClass)} />
      {config.label}
    </span>
  );
}

export default ConfidenceBadge;
