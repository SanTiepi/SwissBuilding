import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import type { PackComparisonData, AudiencePackData, CaveatEvaluation } from '@/api/audiencePacks';
import { CheckCircle2, Lock, AlertTriangle, ArrowRight, X } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  ready: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  shared: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  acknowledged: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
};

function PackColumn({ pack, label }: { pack: AudiencePackData; label: string }) {
  const { t } = useTranslation();
  const sections = pack.sections || {};
  const sectionEntries = Object.entries(sections);

  return (
    <div className="flex-1 min-w-0">
      <div className="flex items-center gap-2 mb-3">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white truncate">{label}</h4>
        <span
          className={cn(
            'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
            STATUS_COLORS[pack.status] || STATUS_COLORS.draft,
          )}
        >
          {t(`audience_pack.status.${pack.status}`) || pack.status}
        </span>
      </div>
      <p className="text-xs text-gray-500 dark:text-slate-400 mb-2">
        v{pack.pack_version} | {t('audience_pack.type_label')}:{' '}
        {t(`audience_pack.type.${pack.pack_type}`) || pack.pack_type}
      </p>

      {/* Sections */}
      <div className="space-y-1 mb-3">
        <p className="text-xs font-medium text-gray-700 dark:text-slate-300">{t('audience_pack.sections')}</p>
        {sectionEntries.length === 0 ? (
          <p className="text-xs text-gray-400 dark:text-slate-500">{t('audience_pack.no_sections')}</p>
        ) : (
          sectionEntries.map(([name, section]) => (
            <div key={name} className="flex items-center gap-2 text-xs" data-testid="comparison-section">
              {section.blocked ? (
                <Lock className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
              ) : section.included ? (
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
              ) : (
                <X className="w-3.5 h-3.5 text-red-400" />
              )}
              <span
                className={cn(
                  section.blocked
                    ? 'text-gray-400 dark:text-slate-500 line-through'
                    : 'text-gray-700 dark:text-slate-300',
                )}
              >
                {name}
              </span>
            </div>
          ))
        )}
      </div>

      {/* Caveats */}
      {pack.caveats && pack.caveats.length > 0 && (
        <div className="mb-3">
          <p className="text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">{t('audience_pack.caveats')}</p>
          {pack.caveats.map((c: CaveatEvaluation, i: number) => (
            <div
              key={i}
              className="flex items-start gap-1 text-xs text-gray-600 dark:text-slate-400"
              data-testid="comparison-caveat"
            >
              <AlertTriangle className="w-3 h-3 flex-shrink-0 mt-0.5 text-amber-500" />
              <span>{c.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

interface PackComparisonViewProps {
  comparison: PackComparisonData;
  onClose?: () => void;
}

export function PackComparisonView({ comparison, onClose }: PackComparisonViewProps) {
  const { t } = useTranslation();

  const sectionDiff = comparison.section_diff || {};
  const caveatDiff = comparison.caveat_diff || {};
  const hasOnlyIn1 = Object.values(sectionDiff).some((d) => d.only_in_1 && d.only_in_1.length > 0);
  const hasOnlyIn2 = Object.values(sectionDiff).some((d) => d.only_in_2 && d.only_in_2.length > 0);
  const hasChanged = Object.values(sectionDiff).some((d) => d.changed && d.changed.length > 0);
  const hasDiffs = hasOnlyIn1 || hasOnlyIn2 || hasChanged;

  return (
    <div
      className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5"
      data-testid="pack-comparison-view"
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t('audience_pack.comparison_title')}</h3>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-300"
            data-testid="close-comparison"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Side-by-side packs */}
      <div className="flex gap-4 mb-4" data-testid="comparison-columns">
        <PackColumn
          pack={comparison.pack_1}
          label={`${t(`audience_pack.type.${comparison.pack_1.pack_type}`) || comparison.pack_1.pack_type} (v${comparison.pack_1.pack_version})`}
        />
        <div className="flex items-center flex-shrink-0">
          <ArrowRight className="w-4 h-4 text-gray-300 dark:text-slate-600" />
        </div>
        <PackColumn
          pack={comparison.pack_2}
          label={`${t(`audience_pack.type.${comparison.pack_2.pack_type}`) || comparison.pack_2.pack_type} (v${comparison.pack_2.pack_version})`}
        />
      </div>

      {/* Diff summary */}
      {hasDiffs && (
        <div className="border-t border-gray-200 dark:border-slate-700 pt-3" data-testid="diff-summary">
          <p className="text-xs font-medium text-gray-700 dark:text-slate-300 mb-2">
            {t('audience_pack.diff_summary')}
          </p>
          {Object.entries(sectionDiff).map(([section, diff]) => {
            const items: string[] = [];
            if (diff.only_in_1?.length)
              items.push(`${t('audience_pack.only_in')} Pack 1: ${diff.only_in_1.join(', ')}`);
            if (diff.only_in_2?.length)
              items.push(`${t('audience_pack.only_in')} Pack 2: ${diff.only_in_2.join(', ')}`);
            if (diff.changed?.length) items.push(`${t('audience_pack.changed')}: ${diff.changed.join(', ')}`);
            if (items.length === 0) return null;
            return (
              <div key={section} className="mb-2" data-testid="diff-section">
                <p className="text-xs font-medium text-gray-600 dark:text-slate-400">{section}</p>
                {items.map((item, i) => (
                  <p key={i} className="text-xs text-gray-500 dark:text-slate-400 ml-2">
                    {item}
                  </p>
                ))}
              </div>
            );
          })}
        </div>
      )}

      {/* Caveat diff */}
      {(caveatDiff.only_in_1?.length > 0 || caveatDiff.only_in_2?.length > 0) && (
        <div className="border-t border-gray-200 dark:border-slate-700 pt-3 mt-3" data-testid="caveat-diff">
          <p className="text-xs font-medium text-gray-700 dark:text-slate-300 mb-2">
            {t('audience_pack.caveat_diff_title')}
          </p>
          {caveatDiff.only_in_1?.length > 0 && (
            <div className="mb-1">
              <p className="text-xs text-gray-500 dark:text-slate-400">{t('audience_pack.only_in')} Pack 1:</p>
              {caveatDiff.only_in_1.map((c: CaveatEvaluation, i: number) => (
                <p key={i} className="text-xs text-gray-600 dark:text-slate-400 ml-2">
                  {c.message}
                </p>
              ))}
            </div>
          )}
          {caveatDiff.only_in_2?.length > 0 && (
            <div>
              <p className="text-xs text-gray-500 dark:text-slate-400">{t('audience_pack.only_in')} Pack 2:</p>
              {caveatDiff.only_in_2.map((c: CaveatEvaluation, i: number) => (
                <p key={i} className="text-xs text-gray-600 dark:text-slate-400 ml-2">
                  {c.message}
                </p>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default PackComparisonView;
