import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { passportEnvelopeDiffApi, type EnvelopeDiffResult, type EnvelopeDiffChange } from '@/api/passportEnvelopeDiff';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { ArrowRight, Plus, Minus, Edit3, TrendingUp, TrendingDown, ChevronDown, ChevronUp } from 'lucide-react';

interface PassportDiffViewProps {
  envelopeIdA: string;
  envelopeIdB: string;
  versionA?: number;
  versionB?: number;
  onClose?: () => void;
}

const CHANGE_TYPE_STYLES: Record<string, { bg: string; text: string; icon: typeof Plus }> = {
  added: {
    bg: 'bg-emerald-50 dark:bg-emerald-900/20',
    text: 'text-emerald-700 dark:text-emerald-300',
    icon: Plus,
  },
  removed: {
    bg: 'bg-red-50 dark:bg-red-900/20',
    text: 'text-red-700 dark:text-red-300',
    icon: Minus,
  },
  modified: {
    bg: 'bg-amber-50 dark:bg-amber-900/20',
    text: 'text-amber-700 dark:text-amber-300',
    icon: Edit3,
  },
};

const GRADE_COLORS: Record<string, string> = {
  A: 'text-emerald-600 dark:text-emerald-400',
  B: 'text-green-600 dark:text-green-400',
  C: 'text-yellow-600 dark:text-yellow-400',
  D: 'text-orange-600 dark:text-orange-400',
  F: 'text-red-600 dark:text-red-400',
};

function DeltaArrow({ value }: { value: number | null }) {
  if (value == null || value === 0) return <span className="text-gray-400">--</span>;
  if (value > 0) return <TrendingUp className="w-4 h-4 text-emerald-500 inline" />;
  return <TrendingDown className="w-4 h-4 text-red-500 inline" />;
}

function formatPct(v: number | null): string {
  if (v == null) return '--';
  return `${(v * 100).toFixed(1)}%`;
}

function ChangeRow({ change }: { change: EnvelopeDiffChange }) {
  const style = CHANGE_TYPE_STYLES[change.change_type] || CHANGE_TYPE_STYLES.modified;
  const Icon = style.icon;

  return (
    <div className={cn('flex items-start gap-3 px-3 py-2 rounded-lg text-sm', style.bg)}>
      <Icon className={cn('w-4 h-4 mt-0.5 shrink-0', style.text)} />
      <div className="flex-1 min-w-0">
        <div className="font-medium text-gray-800 dark:text-slate-200">
          <span className="text-gray-500 dark:text-slate-400">{change.section}</span>
          {change.field !== change.section && (
            <>
              <span className="mx-1 text-gray-400">/</span>
              <span>{change.field}</span>
            </>
          )}
        </div>
        <div className="flex items-center gap-2 mt-1 text-xs">
          {change.old_value != null && (
            <span className="text-red-600 dark:text-red-400 line-through truncate max-w-[200px]">
              {change.old_value}
            </span>
          )}
          {change.old_value != null && change.new_value != null && (
            <ArrowRight className="w-3 h-3 text-gray-400 shrink-0" />
          )}
          {change.new_value != null && (
            <span className="text-emerald-600 dark:text-emerald-400 truncate max-w-[200px]">{change.new_value}</span>
          )}
        </div>
      </div>
      <span
        className={cn(
          'text-xs px-2 py-0.5 rounded-full font-medium shrink-0',
          style.text,
          change.change_type === 'added' && 'bg-emerald-100 dark:bg-emerald-800/40',
          change.change_type === 'removed' && 'bg-red-100 dark:bg-red-800/40',
          change.change_type === 'modified' && 'bg-amber-100 dark:bg-amber-800/40',
        )}
      >
        {change.change_type}
      </span>
    </div>
  );
}

export function PassportDiffView({ envelopeIdA, envelopeIdB, versionA, versionB, onClose }: PassportDiffViewProps) {
  const { t } = useTranslation();
  const [expandedSections, setExpandedSections] = useState<Set<string>>(new Set());

  const { data, isLoading, error } = useQuery<EnvelopeDiffResult>({
    queryKey: ['passport-envelope-diff', envelopeIdA, envelopeIdB],
    queryFn: () => passportEnvelopeDiffApi.diffEnvelopes(envelopeIdA, envelopeIdB),
    enabled: Boolean(envelopeIdA && envelopeIdB),
  });

  const toggleSection = (section: string) => {
    setExpandedSections((prev) => {
      const next = new Set(prev);
      if (next.has(section)) next.delete(section);
      else next.add(section);
      return next;
    });
  };

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6">
        <div className="animate-pulse space-y-3">
          <div className="h-5 bg-gray-200 dark:bg-slate-600 rounded w-1/3" />
          <div className="h-4 bg-gray-200 dark:bg-slate-600 rounded w-2/3" />
          <div className="h-4 bg-gray-200 dark:bg-slate-600 rounded w-1/2" />
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-red-200 dark:border-red-800 p-6">
        <p className="text-red-600 dark:text-red-400 text-sm">
          {t('passport_diff.error') || 'Failed to load diff.'}
        </p>
      </div>
    );
  }

  const { summary, changes, trust_delta, completeness_delta, grade_delta } = data;
  const hasChanges = summary.total_changes > 0;

  // Group changes by section
  const changesBySection: Record<string, EnvelopeDiffChange[]> = {};
  for (const change of changes) {
    if (!changesBySection[change.section]) changesBySection[change.section] = [];
    changesBySection[change.section].push(change);
  }

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="px-5 py-4 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between">
        <div>
          <h3 className="text-base font-semibold text-gray-900 dark:text-white">
            {t('passport_diff.title') || 'Passport Version Diff'}
          </h3>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">
            v{versionA ?? data.envelope_a_version} <ArrowRight className="w-3 h-3 inline mx-1" /> v
            {versionB ?? data.envelope_b_version}
          </p>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 p-1 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700"
          >
            <span className="sr-only">{t('form.close') || 'Close'}</span>
            <Minus className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Delta summary cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 px-5 py-4 border-b border-gray-100 dark:border-slate-700">
        {/* Grade */}
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">
            {t('passport_diff.grade') || 'Grade'}
          </div>
          <div className="flex items-center justify-center gap-2">
            <span className={cn('text-xl font-bold', GRADE_COLORS[grade_delta.old_grade || ''] || 'text-gray-400')}>
              {grade_delta.old_grade || '--'}
            </span>
            <ArrowRight className="w-4 h-4 text-gray-400" />
            <span className={cn('text-xl font-bold', GRADE_COLORS[grade_delta.new_grade || ''] || 'text-gray-400')}>
              {grade_delta.new_grade || '--'}
            </span>
          </div>
        </div>

        {/* Trust */}
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">
            {t('passport_diff.trust') || 'Trust'}
          </div>
          <div className="flex items-center justify-center gap-1">
            <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
              {formatPct(trust_delta.old_trust)}
            </span>
            <ArrowRight className="w-3 h-3 text-gray-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
              {formatPct(trust_delta.new_trust)}
            </span>
            <DeltaArrow value={trust_delta.trust_change} />
          </div>
        </div>

        {/* Completeness */}
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">
            {t('passport_diff.completeness') || 'Completeness'}
          </div>
          <div className="flex items-center justify-center gap-1">
            <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
              {completeness_delta.old_pct != null ? `${completeness_delta.old_pct.toFixed(0)}%` : '--'}
            </span>
            <ArrowRight className="w-3 h-3 text-gray-400" />
            <span className="text-sm font-medium text-gray-700 dark:text-slate-300">
              {completeness_delta.new_pct != null ? `${completeness_delta.new_pct.toFixed(0)}%` : '--'}
            </span>
          </div>
        </div>

        {/* Changes count */}
        <div className="text-center">
          <div className="text-xs text-gray-500 dark:text-slate-400 mb-1">
            {t('passport_diff.changes') || 'Changes'}
          </div>
          <div className="text-xl font-bold text-gray-900 dark:text-white">{summary.total_changes}</div>
        </div>
      </div>

      {/* Section summary */}
      {(summary.sections_added.length > 0 || summary.sections_removed.length > 0) && (
        <div className="px-5 py-3 border-b border-gray-100 dark:border-slate-700 flex flex-wrap gap-2 text-xs">
          {summary.sections_added.map((s) => (
            <span
              key={`added-${s}`}
              className="px-2 py-0.5 rounded-full bg-emerald-100 dark:bg-emerald-900/30 text-emerald-700 dark:text-emerald-300"
            >
              + {s}
            </span>
          ))}
          {summary.sections_removed.map((s) => (
            <span
              key={`removed-${s}`}
              className="px-2 py-0.5 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300"
            >
              - {s}
            </span>
          ))}
        </div>
      )}

      {/* Changes list grouped by section */}
      <div className="px-5 py-4 space-y-2">
        {!hasChanges && (
          <p className="text-sm text-gray-500 dark:text-slate-400 text-center py-4">
            {t('passport_diff.no_changes') || 'No differences found between these versions.'}
          </p>
        )}

        {Object.entries(changesBySection).map(([section, sectionChanges]) => {
          const isExpanded = expandedSections.has(section);
          return (
            <div
              key={section}
              className="border border-gray-200 dark:border-slate-600 rounded-lg overflow-hidden"
            >
              <button
                onClick={() => toggleSection(section)}
                className="w-full flex items-center justify-between px-4 py-2.5 text-sm font-medium text-gray-800 dark:text-slate-200 bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700"
              >
                <span>
                  {section}{' '}
                  <span className="text-gray-400 dark:text-slate-500 font-normal">
                    ({sectionChanges.length} {sectionChanges.length === 1 ? 'change' : 'changes'})
                  </span>
                </span>
                {isExpanded ? (
                  <ChevronUp className="w-4 h-4 text-gray-400" />
                ) : (
                  <ChevronDown className="w-4 h-4 text-gray-400" />
                )}
              </button>
              {isExpanded && (
                <div className="p-3 space-y-1.5">
                  {sectionChanges.map((change, idx) => (
                    <ChangeRow key={`${change.section}-${change.field}-${idx}`} change={change} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

export default PassportDiffView;
