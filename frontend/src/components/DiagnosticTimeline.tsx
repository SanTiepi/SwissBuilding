import { Link } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { formatDate } from '@/utils/formatters';
import { PollutantBadge } from '@/components/PollutantBadge';
import { ChevronRight } from 'lucide-react';
import type { Diagnostic, DiagnosticStatus } from '@/types';

interface DiagnosticTimelineProps {
  diagnostics: Diagnostic[];
}

const statusStyles: Record<DiagnosticStatus, { bg: string; text: string; dot: string }> = {
  draft: { bg: 'bg-slate-100', text: 'text-slate-600', dot: 'bg-slate-400' },
  in_progress: { bg: 'bg-blue-50', text: 'text-blue-700', dot: 'bg-blue-500' },
  completed: { bg: 'bg-green-50', text: 'text-green-700', dot: 'bg-green-500' },
  validated: { bg: 'bg-emerald-50', text: 'text-emerald-700', dot: 'bg-emerald-600' },
};

export function DiagnosticTimeline({ diagnostics }: DiagnosticTimelineProps) {
  const { t, locale } = useTranslation();

  // Sort by date, most recent first
  const sorted = [...diagnostics].sort(
    (a, b) => new Date(b.date_inspection).getTime() - new Date(a.date_inspection).getTime(),
  );

  if (sorted.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-slate-500 text-sm">
        {t('diagnostic.no_diagnostics')}
      </div>
    );
  }

  return (
    <div className="relative">
      {/* Vertical connector line */}
      <div className="absolute left-[19px] top-6 bottom-6 w-0.5 bg-slate-200 dark:bg-slate-700" />

      <div className="space-y-0">
        {sorted.map((diag) => {
          const style = statusStyles[diag.status] || statusStyles.draft;

          return (
            <div key={diag.id} className="relative flex gap-4 pb-8 last:pb-0">
              {/* Timeline dot */}
              <div className="relative z-10 flex-shrink-0 mt-1">
                <div
                  className={`w-[10px] h-[10px] rounded-full ring-4 ring-white dark:ring-slate-800 ${style.dot}`}
                  style={{ marginLeft: '14px' }}
                />
              </div>

              {/* Content card - clickable link to diagnostic detail */}
              <Link
                to={`/diagnostics/${diag.id}`}
                className="flex-1 bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4 hover:shadow-md hover:border-slate-300 dark:hover:border-slate-600 transition-all group"
              >
                {/* Header row */}
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-sm font-semibold text-slate-900 dark:text-white">
                      {formatDate(diag.date_inspection, 'dd.MM.yyyy', locale)}
                    </span>
                    <PollutantBadge
                      type={diag.diagnostic_type === 'full' ? 'asbestos' : diag.diagnostic_type}
                      size="sm"
                    />
                    {diag.diagnostic_type === 'full' && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700">
                        {t('diagnostic_type.full')}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${style.bg} ${style.text}`}
                    >
                      {t(`diagnostic_status.${diag.status}`)}
                    </span>
                    <ChevronRight className="w-4 h-4 text-slate-300 dark:text-slate-600 group-hover:text-slate-500 dark:group-hover:text-slate-400 transition-colors" />
                  </div>
                </div>

                {/* Context */}
                <p className="text-xs text-slate-500 dark:text-slate-400 mb-1">
                  {t(`diagnostic_context.${diag.diagnostic_context}`)}
                </p>

                {/* Summary */}
                {diag.summary && (
                  <p className="text-sm text-slate-600 dark:text-slate-300 mt-2 line-clamp-2">{diag.summary}</p>
                )}

                {/* Footer */}
                <div className="flex items-center justify-between mt-3 pt-2 border-t border-slate-100 dark:border-slate-700">
                  <span className="text-xs text-slate-500">{t(`diagnostic_context.${diag.diagnostic_context}`)}</span>
                  {diag.laboratory && <span className="text-xs text-slate-500">{diag.laboratory}</span>}
                </div>
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}
