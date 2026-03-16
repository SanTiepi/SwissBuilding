import { useQuery } from '@tanstack/react-query';
import { Stethoscope, FlaskConical, FileText, Shield } from 'lucide-react';
import { useTranslation } from '@/i18n';
import { evidenceSummaryApi } from '@/api/evidenceSummary';
import { cn } from '@/utils/formatters';

interface SearchEvidencePreviewProps {
  buildingId: string;
}

export function SearchEvidencePreview({ buildingId }: SearchEvidencePreviewProps) {
  const { t } = useTranslation();

  const { data: summary, isLoading } = useQuery({
    queryKey: ['evidence-summary', buildingId],
    queryFn: () => evidenceSummaryApi.get(buildingId),
    staleTime: 30_000,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-4">
        <div className="w-4 h-4 border-2 border-slate-300 dark:border-slate-600 border-t-slate-600 dark:border-t-slate-300 rounded-full animate-spin" />
      </div>
    );
  }

  if (!summary) return null;

  const stats = [
    {
      icon: Stethoscope,
      label: t('search.diagnostics_count', { count: summary.diagnostics_count }),
      value: summary.diagnostics_count,
      color: 'text-blue-600 dark:text-blue-400',
      bg: 'bg-blue-50 dark:bg-blue-900/30',
    },
    {
      icon: FlaskConical,
      label: t('search.samples_count', { count: summary.samples_count }),
      value: summary.samples_count,
      color: 'text-purple-600 dark:text-purple-400',
      bg: 'bg-purple-50 dark:bg-purple-900/30',
    },
    {
      icon: FileText,
      label: t('search.documents_count', { count: summary.documents_count }),
      value: summary.documents_count,
      color: 'text-amber-600 dark:text-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-900/30',
    },
  ];

  const coveragePercent = Math.round(summary.coverage_ratio * 100);

  return (
    <div className="p-3 space-y-2.5">
      <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide">
        {t('search.evidence_preview')}
      </p>

      <div className="space-y-1.5">
        {stats.map((stat) => {
          const Icon = stat.icon;
          return (
            <div key={stat.label} className="flex items-center gap-2">
              <div className={cn('w-5 h-5 rounded flex items-center justify-center flex-shrink-0', stat.bg)}>
                <Icon className={cn('w-3 h-3', stat.color)} />
              </div>
              <span className="text-xs text-slate-700 dark:text-slate-300">{stat.label}</span>
            </div>
          );
        })}
      </div>

      {/* Pollutant coverage bar */}
      <div className="space-y-1">
        <div className="flex items-center gap-1.5">
          <Shield className="w-3 h-3 text-emerald-600 dark:text-emerald-400" />
          <span className="text-xs text-slate-600 dark:text-slate-400">{t('search.pollutant_coverage')}</span>
          <span className="ml-auto text-xs font-medium text-slate-700 dark:text-slate-300">{coveragePercent}%</span>
        </div>
        <div className="h-1.5 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden">
          <div
            className={cn(
              'h-full rounded-full transition-all',
              coveragePercent >= 80 ? 'bg-emerald-500' : coveragePercent >= 50 ? 'bg-amber-500' : 'bg-red-500',
            )}
            style={{ width: `${coveragePercent}%` }}
          />
        </div>
      </div>
    </div>
  );
}
