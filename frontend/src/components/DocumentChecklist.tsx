import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { documentChecklistApi, type ChecklistItem } from '@/api/documentChecklist';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface DocumentChecklistProps {
  buildingId: string;
  onUpload?: (documentType: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Status config                                                      */
/* ------------------------------------------------------------------ */

const STATUS_CONFIG: Record<string, { icon: string; textClass: string; bgClass: string }> = {
  present: {
    icon: '\u2705',
    textClass: 'text-green-700 dark:text-green-400',
    bgClass: 'bg-green-50 dark:bg-green-900/20',
  },
  missing: {
    icon: '\u274C',
    textClass: 'text-red-700 dark:text-red-400',
    bgClass: 'bg-red-50 dark:bg-red-900/20',
  },
  expired: {
    icon: '\u26A0\uFE0F',
    textClass: 'text-amber-700 dark:text-amber-400',
    bgClass: 'bg-amber-50 dark:bg-amber-900/20',
  },
  not_applicable: {
    icon: '\u2796',
    textClass: 'text-gray-500 dark:text-gray-500',
    bgClass: 'bg-gray-50 dark:bg-slate-700/30',
  },
};

const IMPORTANCE_BADGE: Record<string, { label: string; className: string }> = {
  critical: {
    label: 'Critique',
    className: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  },
  high: {
    label: 'Eleve',
    className: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  },
  medium: {
    label: 'Moyen',
    className: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  },
  low: {
    label: 'Faible',
    className: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-gray-400',
  },
};

/* ------------------------------------------------------------------ */
/*  Progress bar                                                       */
/* ------------------------------------------------------------------ */

function ProgressBar({ pct }: { pct: number }) {
  const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div className="w-full h-2 bg-gray-200 dark:bg-slate-700 rounded-full overflow-hidden">
      <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${Math.min(pct, 100)}%` }} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Checklist item row                                                 */
/* ------------------------------------------------------------------ */

function ChecklistRow({
  item,
  onUpload,
  t,
}: {
  item: ChecklistItem;
  onUpload?: (type: string) => void;
  t: (k: string) => string;
}) {
  const status = STATUS_CONFIG[item.status] || STATUS_CONFIG.not_applicable;
  const importance = IMPORTANCE_BADGE[item.importance] || IMPORTANCE_BADGE.low;

  return (
    <div
      className={cn(
        'flex items-center gap-3 py-2.5 px-3 rounded-lg border border-gray-100 dark:border-slate-700',
        status.bgClass,
      )}
      data-testid={`checklist-item-${item.document_type}`}
    >
      <span className="text-base shrink-0">{status.icon}</span>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className={cn('text-sm font-medium', status.textClass)}>{item.label}</span>
          <span className={cn('text-[10px] px-1.5 py-0.5 rounded-full font-medium', importance.className)}>
            {importance.label}
          </span>
        </div>
        {item.legal_basis && (
          <span className="text-[11px] text-gray-500 dark:text-gray-400">{item.legal_basis}</span>
        )}
        {item.recommendation && (
          <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-0.5">{item.recommendation}</p>
        )}
      </div>
      {item.status === 'missing' && onUpload && (
        <button
          onClick={() => onUpload(item.document_type)}
          className="text-xs px-2.5 py-1 rounded-md bg-blue-600 text-white hover:bg-blue-700 shrink-0"
          data-testid={`upload-${item.document_type}`}
        >
          {t('doc_checklist.upload') || 'Telecharger'}
        </button>
      )}
      {item.status === 'present' && item.uploaded_at && (
        <span className="text-[11px] text-gray-400 dark:text-gray-500 shrink-0">
          {new Date(item.uploaded_at).toLocaleDateString('fr-CH')}
        </span>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export function DocumentChecklist({ buildingId, onUpload }: DocumentChecklistProps) {
  const { t } = useTranslation();

  const { data, isLoading, error } = useQuery({
    queryKey: ['document-checklist', buildingId],
    queryFn: () => documentChecklistApi.getChecklist(buildingId),
    enabled: !!buildingId,
  });

  if (isLoading) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">{t('app.loading') || 'Chargement...'}</p>;
  }

  if (error || !data) {
    return <p className="text-sm text-red-500">{t('app.error') || 'Erreur'}</p>;
  }

  const criticalMissing = data.items.filter((i) => i.importance === 'critical' && i.status === 'missing');
  const applicableItems = data.items.filter((i) => i.status !== 'not_applicable');
  const naItems = data.items.filter((i) => i.status === 'not_applicable');

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-4 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          {t('doc_checklist.title') || 'Checklist documentaire'}
        </h3>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          {data.total_present}/{data.total_required}{' '}
          {t('doc_checklist.complete') || 'complets'}
        </span>
      </div>

      {/* Progress */}
      <div>
        <ProgressBar pct={data.completion_pct} />
        <p className="text-[11px] text-gray-500 dark:text-gray-400 mt-1">{data.completion_pct}% {t('doc_checklist.completion') || 'completude'}</p>
      </div>

      {/* Critical missing alert */}
      {criticalMissing.length > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
          <p className="text-xs font-semibold text-red-700 dark:text-red-400 mb-1">
            {t('doc_checklist.critical_missing') || 'Documents critiques manquants'}
          </p>
          <ul className="text-xs text-red-600 dark:text-red-300 space-y-0.5">
            {criticalMissing.map((item) => (
              <li key={item.document_type}>- {item.label}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Applicable items */}
      <div className="space-y-1.5">
        {applicableItems.map((item) => (
          <ChecklistRow key={item.document_type} item={item} onUpload={onUpload} t={t} />
        ))}
      </div>

      {/* Non-applicable items (collapsed) */}
      {naItems.length > 0 && (
        <details className="text-xs text-gray-400 dark:text-gray-500">
          <summary className="cursor-pointer">
            {naItems.length} {t('doc_checklist.not_applicable') || 'non applicables'}
          </summary>
          <div className="mt-1 space-y-1">
            {naItems.map((item) => (
              <ChecklistRow key={item.document_type} item={item} t={t} />
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

export default DocumentChecklist;
