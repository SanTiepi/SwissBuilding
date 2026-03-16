import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from 'lucide-react';

interface ReadinessBadgeProps {
  status: string | null;
  blockedCount?: number;
  size?: 'sm' | 'md';
}

const STATUS_CONFIG: Record<string, { icon: typeof CheckCircle2; color: string; bgColor: string; labelKey: string }> = {
  ready: {
    icon: CheckCircle2,
    color: 'text-green-700 dark:text-green-300',
    bgColor: 'bg-green-100 dark:bg-green-900/40',
    labelKey: 'readiness.ready',
  },
  partially_ready: {
    icon: AlertTriangle,
    color: 'text-yellow-700 dark:text-yellow-300',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900/40',
    labelKey: 'readiness.partially_ready',
  },
  conditionally_ready: {
    icon: AlertTriangle,
    color: 'text-yellow-700 dark:text-yellow-300',
    bgColor: 'bg-yellow-100 dark:bg-yellow-900/40',
    labelKey: 'readiness.partially_ready',
  },
  not_ready: {
    icon: XCircle,
    color: 'text-red-700 dark:text-red-300',
    bgColor: 'bg-red-100 dark:bg-red-900/40',
    labelKey: 'readiness.not_ready',
  },
  blocked: {
    icon: XCircle,
    color: 'text-red-700 dark:text-red-300',
    bgColor: 'bg-red-100 dark:bg-red-900/40',
    labelKey: 'readiness.not_ready',
  },
};

export function ReadinessBadge({ status, blockedCount, size = 'sm' }: ReadinessBadgeProps) {
  const { t } = useTranslation();

  if (!status) {
    return (
      <span
        className={cn(
          'inline-flex items-center gap-1 rounded-full font-medium',
          'bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400',
          size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
        )}
        title={t('readiness.unknown')}
      >
        <HelpCircle className={cn('flex-shrink-0', size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5')} />
        --
      </span>
    );
  }

  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.not_ready;
  const Icon = config.icon;

  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 rounded-full font-medium',
        config.bgColor,
        config.color,
        size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-sm',
      )}
      title={t(config.labelKey)}
    >
      <Icon className={cn('flex-shrink-0', size === 'sm' ? 'w-3 h-3' : 'w-3.5 h-3.5')} />
      {t(config.labelKey)}
      {blockedCount != null && blockedCount > 0 && (
        <span
          className={cn(
            'inline-flex items-center justify-center rounded-full bg-red-500 text-white font-bold',
            size === 'sm' ? 'w-4 h-4 text-[10px]' : 'w-5 h-5 text-xs',
          )}
        >
          {blockedCount}
        </span>
      )}
    </span>
  );
}
