import { useTranslation } from '@/i18n';
import type { Nudge } from '@/api/nudges';

interface NudgeCardProps {
  nudge: Nudge;
  onDismiss?: (id: string) => void;
  onAction?: (nudge: Nudge) => void;
}

const severityStyles: Record<string, { bg: string; border: string; icon: string }> = {
  critical: {
    bg: 'bg-red-50 dark:bg-red-950/30',
    border: 'border-red-300 dark:border-red-700',
    icon: '🔴',
  },
  warning: {
    bg: 'bg-amber-50 dark:bg-amber-950/30',
    border: 'border-amber-300 dark:border-amber-700',
    icon: '🟠',
  },
  info: {
    bg: 'bg-blue-50 dark:bg-blue-950/30',
    border: 'border-blue-300 dark:border-blue-700',
    icon: '🔵',
  },
};

export function NudgeCard({ nudge, onDismiss, onAction }: NudgeCardProps) {
  const { t } = useTranslation();
  const style = severityStyles[nudge.severity] ?? severityStyles.info;

  const formatChf = (min: number, max: number): string => {
    if (min === max) return `CHF ${min.toLocaleString('de-CH')}`;
    return `CHF ${min.toLocaleString('de-CH')} – ${max.toLocaleString('de-CH')}`;
  };

  return (
    <div
      data-testid={`nudge-card-${nudge.id}`}
      className={`rounded-lg border ${style.border} ${style.bg} p-4 transition-all hover:shadow-md`}
    >
      {/* Severity banner */}
      <div className="mb-2 flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          {style.icon} {nudge.nudge_type.replace(/_/g, ' ')}
        </span>
        {onDismiss && (
          <button
            onClick={() => onDismiss(nudge.id)}
            className="text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            title={t('nudge.dismiss')}
            data-testid={`nudge-dismiss-${nudge.id}`}
          >
            &times;
          </button>
        )}
      </div>

      {/* Headline (loss framing) */}
      <h3 className="mb-1 text-base font-bold text-gray-900 dark:text-gray-100">{nudge.headline}</h3>

      <p className="mb-3 text-sm text-gray-700 dark:text-gray-300">{nudge.loss_framing}</p>

      {/* Cost of inaction */}
      {nudge.cost_of_inaction && (
        <div className="mb-3 rounded bg-white/60 p-2 dark:bg-gray-800/60">
          <div className="text-xs font-medium text-gray-500 dark:text-gray-400">
            {t('nudge.cost_of_inaction')}
          </div>
          <div className="text-lg font-bold text-red-700 dark:text-red-400">
            {formatChf(nudge.cost_of_inaction.estimated_chf_min, nudge.cost_of_inaction.estimated_chf_max)}
          </div>
          <div className="text-xs text-gray-500 dark:text-gray-400">
            {nudge.cost_of_inaction.description}
          </div>
        </div>
      )}

      {/* Deadline countdown */}
      {nudge.deadline_pressure !== null && nudge.deadline_pressure !== undefined && (
        <div className="mb-2 text-sm font-semibold text-red-600 dark:text-red-400">
          {t('nudge.deadline')}: {nudge.deadline_pressure} {nudge.deadline_pressure === 1 ? 'day' : 'days'}
        </div>
      )}

      {/* Social proof */}
      {nudge.social_proof && (
        <p className="mb-3 text-xs italic text-gray-500 dark:text-gray-400">{nudge.social_proof}</p>
      )}

      {/* CTA button */}
      <button
        onClick={() => onAction?.(nudge)}
        className="w-full rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
        data-testid={`nudge-cta-${nudge.id}`}
      >
        {nudge.call_to_action}
      </button>
    </div>
  );
}
