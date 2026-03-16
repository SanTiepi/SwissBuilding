import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { Loader2, AlertTriangle, Inbox } from 'lucide-react';
import { InlineSkeleton } from '@/components/Skeleton';

interface AsyncStateWrapperProps {
  isLoading: boolean;
  isError: boolean;
  data: unknown;
  children: React.ReactNode;
  variant?: 'card' | 'inline' | 'page';
  loadingType?: 'spinner' | 'skeleton';
  icon?: React.ReactNode;
  title?: string;
  emptyMessage?: string;
  errorMessage?: string;
  className?: string;
  isEmpty?: boolean;
}

const VARIANT_CLASSES: Record<string, string> = {
  card: 'bg-gray-50 dark:bg-slate-700/50 rounded-xl p-5',
  inline: 'p-2',
  page: 'bg-gray-50 dark:bg-slate-700/50 rounded-xl p-8 min-h-[200px]',
};

function isDataEmpty(data: unknown): boolean {
  if (data == null) return true;
  if (Array.isArray(data)) return data.length === 0;
  return false;
}

export function AsyncStateWrapper({
  isLoading,
  isError,
  data,
  children,
  variant = 'card',
  loadingType = 'spinner',
  icon,
  title,
  emptyMessage,
  errorMessage,
  className,
  isEmpty: isEmptyOverride,
}: AsyncStateWrapperProps) {
  const { t } = useTranslation();
  const wrapperCls = cn(VARIANT_CLASSES[variant], className);

  // Loading state
  if (isLoading) {
    return (
      <div
        className={cn(wrapperCls, variant !== 'inline' && 'flex items-center justify-center')}
        role="status"
        aria-busy="true"
      >
        {loadingType === 'skeleton' ? (
          <InlineSkeleton variant={variant} />
        ) : (
          <>
            <Loader2 className="w-5 h-5 animate-spin text-gray-400" aria-hidden="true" />
            <span className="sr-only">Loading…</span>
          </>
        )}
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className={wrapperCls} role="alert">
        {(icon || title) && (
          <div className="flex items-center gap-2 mb-3">
            {icon && <span className="text-gray-500 dark:text-slate-400">{icon}</span>}
            {title && <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>}
          </div>
        )}
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/40 dark:bg-red-900/20 dark:text-red-300">
          <AlertTriangle className="mt-0.5 h-4 w-4 flex-shrink-0" />
          <span>{errorMessage || t('app.loading_error') || 'Unable to load this section right now.'}</span>
        </div>
      </div>
    );
  }

  // Empty state
  const empty = isEmptyOverride !== undefined ? isEmptyOverride : isDataEmpty(data);
  if (empty) {
    return (
      <div className={wrapperCls}>
        {(icon || title) && (
          <div className="flex items-center gap-2 mb-3">
            {icon && <span className="text-gray-500 dark:text-slate-400">{icon}</span>}
            {title && <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h3>}
          </div>
        )}
        <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400">
          <Inbox className="w-4 h-4 flex-shrink-0" />
          <span>{emptyMessage || t('app.no_data') || 'No data available'}</span>
        </div>
      </div>
    );
  }

  // Success — render children
  return <div className={wrapperCls}>{children}</div>;
}
