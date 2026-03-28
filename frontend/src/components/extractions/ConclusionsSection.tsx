import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { CheckCircle2 } from 'lucide-react';
import { SectionHeader, EditableSelect, OVERALL_RESULTS, RISK_LEVELS } from './shared';
import type { SectionProps } from './shared';

export function ConclusionsSection({ extracted, original, onFieldChange }: SectionProps) {
  const { t } = useTranslation();

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
      <SectionHeader icon={CheckCircle2} title={t('extraction.section_conclusions') || 'Conclusions'} />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Resultat global</label>
          <EditableSelect
            value={extracted.conclusions.overall_result}
            originalValue={original?.conclusions.overall_result ?? null}
            options={OVERALL_RESULTS}
            onChange={(v) => onFieldChange('conclusions.overall_result', v)}
          />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Niveau de risque</label>
          <EditableSelect
            value={extracted.conclusions.risk_level}
            originalValue={original?.conclusions.risk_level ?? null}
            options={RISK_LEVELS}
            onChange={(v) => onFieldChange('conclusions.risk_level', v)}
          />
        </div>
        <div className="sm:col-span-2">
          <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Recommandations</label>
          <textarea
            value={extracted.conclusions.recommendations.join('\n')}
            onChange={(e) =>
              onFieldChange(
                'conclusions.recommendations',
                e.target.value.split('\n').filter((l) => l.trim()),
              )
            }
            rows={3}
            className={cn(
              'w-full px-3 py-2 text-sm rounded-lg border transition-colors',
              'bg-white dark:bg-slate-900 border-gray-200 dark:border-slate-600',
              'focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none',
            )}
            placeholder="Une recommandation par ligne"
          />
        </div>
      </div>
    </div>
  );
}
