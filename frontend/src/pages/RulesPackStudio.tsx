/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view (regulatory rules studio).
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { regulatoryPacksApi, type PackWithJurisdiction, type PackDiff } from '@/api/regulatoryPacks';
import { jurisdictionsApi } from '@/api/jurisdictions';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import { cn } from '@/utils/formatters';
import {
  Scale,
  Search,
  ArrowLeftRight,
  AlertTriangle,
  ExternalLink,
  Bell,
  Filter,
  ChevronDown,
  ChevronUp,
  X,
  Monitor,
} from 'lucide-react';

const POLLUTANTS = ['asbestos', 'pcb', 'lead', 'hap', 'radon'] as const;

const pollutantColors: Record<string, string> = {
  asbestos: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  pcb: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  lead: 'bg-gray-200 text-gray-700 dark:bg-gray-700/50 dark:text-gray-300',
  hap: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  radon: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

const pollutantBorderColors: Record<string, string> = {
  asbestos: 'border-l-blue-500',
  pcb: 'border-l-orange-500',
  lead: 'border-l-gray-500',
  hap: 'border-l-purple-500',
  radon: 'border-l-green-500',
};

function PackCard({
  pack,
  isSelected,
  onSelect,
  onToggleCompare,
  isCompareTarget,
  t,
}: {
  pack: PackWithJurisdiction;
  isSelected: boolean;
  onSelect: () => void;
  onToggleCompare: () => void;
  isCompareTarget: boolean;
  t: (key: string) => string;
}) {
  const colorClass = pollutantColors[pack.pollutant_type] || 'bg-gray-100 text-gray-700';
  const borderClass = pollutantBorderColors[pack.pollutant_type] || 'border-l-gray-400';

  return (
    <button
      onClick={onSelect}
      className={cn(
        'w-full text-left border-l-4 px-3 py-2.5 rounded-r-lg transition-colors',
        borderClass,
        isSelected
          ? 'bg-red-50 dark:bg-red-900/20 ring-1 ring-red-200 dark:ring-red-800'
          : 'hover:bg-gray-50 dark:hover:bg-slate-700/50',
        isCompareTarget && 'ring-2 ring-amber-400 dark:ring-amber-500',
      )}
    >
      <div className="flex items-center justify-between gap-2">
        <span className={cn('px-2 py-0.5 text-[11px] font-medium rounded-full', colorClass)}>
          {t(`pollutant.${pack.pollutant_type}`) || pack.pollutant_type}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onToggleCompare();
          }}
          title={t('rules_studio.compare')}
          className={cn(
            'p-1 rounded transition-colors',
            isCompareTarget
              ? 'text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20'
              : 'text-gray-400 dark:text-slate-500 hover:text-gray-600 dark:hover:text-slate-300',
          )}
        >
          <ArrowLeftRight className="w-3.5 h-3.5" />
        </button>
      </div>
      <p className="text-sm font-medium text-gray-900 dark:text-white mt-1 truncate">{pack.jurisdiction_name || '-'}</p>
      <p className="text-xs text-gray-500 dark:text-slate-400">
        v{pack.version} &middot; {pack.threshold_value ?? '-'} {pack.threshold_unit ?? ''}
      </p>
    </button>
  );
}

function PackDetail({ pack, t }: { pack: PackWithJurisdiction; t: (key: string) => string }) {
  const colorClass = pollutantColors[pack.pollutant_type] || 'bg-gray-100 text-gray-700';

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', colorClass)}>
              {t(`pollutant.${pack.pollutant_type}`) || pack.pollutant_type}
            </span>
            <span
              className={cn(
                'px-2 py-0.5 text-[10px] font-medium rounded-full',
                pack.is_active
                  ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                  : 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
              )}
            >
              {pack.is_active ? t('admin.active') || 'Active' : t('admin.inactive') || 'Inactive'}
            </span>
          </div>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">
            {pack.jurisdiction_name} ({pack.jurisdiction_code})
          </h3>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            {t('regulatory_pack.version') || 'Version'}: {pack.version}
          </p>
        </div>
      </div>

      {/* Rules grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        <InfoCell
          label={t('regulatory_pack.threshold') || 'Threshold'}
          value={pack.threshold_value != null ? `${pack.threshold_value} ${pack.threshold_unit ?? ''}` : '-'}
        />
        <InfoCell
          label={t('regulatory_pack.action') || 'Action'}
          value={
            pack.threshold_action ? t(`regulatory_pack.action.${pack.threshold_action}`) || pack.threshold_action : '-'
          }
        />
        <InfoCell
          label={t('regulatory_pack.risk_years') || 'Risk Years'}
          value={
            pack.risk_year_start || pack.risk_year_end
              ? `${pack.risk_year_start ?? '...'} - ${pack.risk_year_end ?? '...'}`
              : '-'
          }
        />
        <InfoCell
          label={t('regulatory_pack.base_probability') || 'Base probability'}
          value={pack.base_probability != null ? `${(pack.base_probability * 100).toFixed(0)}%` : '-'}
        />
        <InfoCell
          label={t('regulatory_pack.legal_reference') || 'Legal ref'}
          value={
            pack.legal_reference ? (
              pack.legal_url ? (
                <a
                  href={pack.legal_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-blue-600 dark:text-blue-400 hover:underline"
                >
                  {pack.legal_reference} <ExternalLink className="w-3 h-3" />
                </a>
              ) : (
                pack.legal_reference
              )
            ) : (
              '-'
            )
          }
        />
        <InfoCell
          label={t('regulatory_pack.notification') || 'Notification'}
          value={
            pack.notification_required ? (
              <span className="inline-flex items-center gap-1 text-amber-600 dark:text-amber-400">
                <Bell className="w-3.5 h-3.5" />
                {pack.notification_authority ?? ''}{' '}
                {pack.notification_delay_days != null ? `(${pack.notification_delay_days}j)` : ''}
              </span>
            ) : (
              '-'
            )
          }
        />
      </div>

      {/* JSON details */}
      {pack.work_categories_json && (
        <JsonBlock label={t('regulatory_pack.work_categories') || 'Work categories'} data={pack.work_categories_json} />
      )}
      {pack.waste_classification_json && (
        <JsonBlock
          label={t('regulatory_pack.waste_classification') || 'Waste classification'}
          data={pack.waste_classification_json}
        />
      )}
      {pack.description_fr && <p className="text-sm text-gray-600 dark:text-slate-300 italic">{pack.description_fr}</p>}
    </div>
  );
}

function InfoCell({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
      <p className="text-[11px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">{label}</p>
      <p className="text-sm font-medium text-gray-900 dark:text-white mt-0.5">{value}</p>
    </div>
  );
}

function JsonBlock({ label, data }: { label: string; data: Record<string, unknown> }) {
  return (
    <div>
      <p className="text-[11px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">{label}</p>
      <pre className="text-xs bg-white dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded p-2 overflow-x-auto">
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

function CompareView({
  packA,
  packB,
  diffs,
  onClose,
  t,
}: {
  packA: PackWithJurisdiction;
  packB: PackWithJurisdiction;
  diffs: PackDiff[];
  onClose: () => void;
  t: (key: string) => string;
}) {
  const changedCount = diffs.filter((d) => d.changed).length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-bold text-gray-900 dark:text-white">
            {t('rules_studio.comparison') || 'Pack Comparison'}
          </h3>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            {changedCount} {t('rules_studio.differences') || 'differences'}
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg transition-colors"
        >
          <X className="w-4 h-4 text-gray-500 dark:text-slate-400" />
        </button>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 dark:border-slate-700">
              <th className="text-left px-3 py-2 font-medium text-gray-500 dark:text-slate-400">
                {t('rules_studio.field') || 'Field'}
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-500 dark:text-slate-400">
                {packA.jurisdiction_name} ({packA.jurisdiction_code})
              </th>
              <th className="text-left px-3 py-2 font-medium text-gray-500 dark:text-slate-400">
                {packB.jurisdiction_name} ({packB.jurisdiction_code})
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
            {diffs.map((d) => (
              <tr key={d.field} className={d.changed ? 'bg-amber-50/50 dark:bg-amber-900/10' : ''}>
                <td className="px-3 py-2 font-medium text-gray-700 dark:text-slate-300">
                  {t(`rules_studio.field_${d.field}`) || d.field}
                </td>
                <td
                  className={cn(
                    'px-3 py-2',
                    d.changed ? 'text-red-600 dark:text-red-400 font-medium' : 'text-gray-600 dark:text-slate-400',
                  )}
                >
                  {formatValue(d.pack_a)}
                </td>
                <td
                  className={cn(
                    'px-3 py-2',
                    d.changed ? 'text-green-600 dark:text-green-400 font-medium' : 'text-gray-600 dark:text-slate-400',
                  )}
                >
                  {formatValue(d.pack_b)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function formatValue(v: string | number | boolean | null): string {
  if (v === null || v === undefined) return '-';
  if (typeof v === 'boolean') return v ? 'Yes' : 'No';
  return String(v);
}

export default function RulesPackStudio() {
  const { t } = useTranslation();
  const { user } = useAuthStore();

  const [searchQuery, setSearchQuery] = useState('');
  const [pollutantFilter, setPollutantFilter] = useState<string>('');
  const [jurisdictionFilter, setJurisdictionFilter] = useState<string>('');
  const [selectedPackId, setSelectedPackId] = useState<string | null>(null);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [showFilters, setShowFilters] = useState(false);

  // Fetch jurisdictions for filter dropdown
  const { data: jurisdictionsData } = useQuery({
    queryKey: ['rules-studio-jurisdictions'],
    queryFn: () => jurisdictionsApi.list({ size: 200 }),
  });

  // Fetch all packs
  const {
    data: allPacks,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['rules-studio-packs'],
    queryFn: () => regulatoryPacksApi.listAll(),
  });

  const jurisdictions = useMemo(() => jurisdictionsData?.items ?? [], [jurisdictionsData]);

  // Filter packs
  const filteredPacks = useMemo(() => {
    if (!allPacks) return [];
    return allPacks.filter((p) => {
      if (pollutantFilter && p.pollutant_type !== pollutantFilter) return false;
      if (jurisdictionFilter && p.jurisdiction_id !== jurisdictionFilter) return false;
      if (searchQuery) {
        const q = searchQuery.toLowerCase();
        return (
          (p.jurisdiction_name ?? '').toLowerCase().includes(q) ||
          p.pollutant_type.toLowerCase().includes(q) ||
          (p.legal_reference ?? '').toLowerCase().includes(q)
        );
      }
      return true;
    });
  }, [allPacks, pollutantFilter, jurisdictionFilter, searchQuery]);

  const selectedPack = useMemo(
    () => filteredPacks.find((p) => p.id === selectedPackId) ?? null,
    [filteredPacks, selectedPackId],
  );

  const toggleCompare = (packId: string) => {
    setCompareIds((prev) => {
      if (prev.includes(packId)) return prev.filter((id) => id !== packId);
      if (prev.length >= 2) return [prev[1], packId];
      return [...prev, packId];
    });
  };

  const comparePackA = useMemo(() => (allPacks ?? []).find((p) => p.id === compareIds[0]), [allPacks, compareIds]);
  const comparePackB = useMemo(() => (allPacks ?? []).find((p) => p.id === compareIds[1]), [allPacks, compareIds]);
  const diffs = useMemo(() => {
    if (!comparePackA || !comparePackB) return null;
    return regulatoryPacksApi.comparePacks(comparePackA, comparePackB);
  }, [comparePackA, comparePackB]);

  if (user?.role !== 'admin') {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-500 dark:text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('admin.access_denied') || 'Access denied'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {t('rules_studio.title') || 'Rules Pack Studio'}
        </h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          {t('rules_studio.description') || 'View, compare, and analyze regulatory packs across jurisdictions'}
        </p>
      </div>

      {/* Mobile disclosure banner */}
      <div
        className="md:hidden flex items-start gap-3 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg px-4 py-3"
        data-testid="mobile-desktop-hint"
      >
        <Monitor className="w-5 h-5 text-blue-500 dark:text-blue-400 shrink-0 mt-0.5" />
        <p className="text-sm text-blue-700 dark:text-blue-300">
          {t('rules_studio.desktop_hint') ||
            'This tool is optimized for desktop use. For the best experience, use a larger screen.'}
        </p>
      </div>

      {/* Search + filter bar */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-slate-500" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder={t('rules_studio.search_placeholder') || 'Search packs...'}
            className="w-full pl-9 pr-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
          />
        </div>
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={cn(
            'inline-flex items-center gap-2 px-4 py-2 border rounded-lg text-sm font-medium transition-colors',
            showFilters
              ? 'border-red-300 dark:border-red-700 text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20'
              : 'border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700',
          )}
        >
          <Filter className="w-4 h-4" />
          {t('rules_studio.filters') || 'Filters'}
          {showFilters ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
        </button>
        {compareIds.length === 2 && (
          <button
            onClick={() => setCompareIds([])}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-amber-700 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors"
          >
            <X className="w-4 h-4" />
            {t('rules_studio.clear_compare') || 'Clear comparison'}
          </button>
        )}
      </div>

      {/* Filters row */}
      {showFilters && (
        <div className="flex flex-wrap gap-3 bg-gray-50 dark:bg-slate-800/50 rounded-xl p-4 border border-gray-200 dark:border-slate-700">
          <div>
            <label className="block text-[11px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              {t('rules_studio.filter_pollutant') || 'Pollutant'}
            </label>
            <select
              value={pollutantFilter}
              onChange={(e) => setPollutantFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              <option value="">{t('rules_studio.all') || 'All'}</option>
              {POLLUTANTS.map((p) => (
                <option key={p} value={p}>
                  {t(`pollutant.${p}`) || p}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-[11px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              {t('rules_studio.filter_jurisdiction') || 'Jurisdiction'}
            </label>
            <select
              value={jurisdictionFilter}
              onChange={(e) => setJurisdictionFilter(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
            >
              <option value="">{t('rules_studio.all') || 'All'}</option>
              {jurisdictions.map((j) => (
                <option key={j.id} value={j.id}>
                  {j.name} ({j.code})
                </option>
              ))}
            </select>
          </div>
        </div>
      )}

      {/* Main content */}
      <AsyncStateWrapper isLoading={isLoading} isError={isError} data={allPacks} variant="page">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left panel - Pack list */}
          <div className="lg:col-span-1">
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
              <div className="px-4 py-3 border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50 flex items-center justify-between">
                <h2 className="text-sm font-medium text-gray-700 dark:text-slate-300">
                  {t('rules_studio.packs') || 'Packs'} ({filteredPacks.length})
                </h2>
                {compareIds.length > 0 && (
                  <span className="text-xs text-amber-600 dark:text-amber-400">
                    {compareIds.length}/2 {t('rules_studio.selected') || 'selected'}
                  </span>
                )}
              </div>
              <div className="p-2 max-h-[60vh] lg:max-h-[calc(100vh-340px)] overflow-y-auto space-y-1">
                {filteredPacks.length === 0 ? (
                  <div className="text-center py-8">
                    <Scale className="w-10 h-10 text-gray-300 dark:text-slate-600 mx-auto mb-2" />
                    <p className="text-sm text-gray-500 dark:text-slate-400">
                      {t('regulatory_pack.empty') || 'No regulatory packs'}
                    </p>
                  </div>
                ) : (
                  filteredPacks.map((pack) => (
                    <PackCard
                      key={pack.id}
                      pack={pack}
                      isSelected={selectedPackId === pack.id}
                      onSelect={() => setSelectedPackId(pack.id)}
                      onToggleCompare={() => toggleCompare(pack.id)}
                      isCompareTarget={compareIds.includes(pack.id)}
                      t={t}
                    />
                  ))
                )}
              </div>
            </div>
          </div>

          {/* Right panel - Detail or Compare */}
          <div className="lg:col-span-2">
            {diffs && comparePackA && comparePackB ? (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-6">
                <CompareView
                  packA={comparePackA}
                  packB={comparePackB}
                  diffs={diffs}
                  onClose={() => setCompareIds([])}
                  t={t}
                />
              </div>
            ) : selectedPack ? (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-6">
                <PackDetail pack={selectedPack} t={t} />
              </div>
            ) : (
              <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm p-12 text-center">
                <Scale className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
                <p className="text-gray-500 dark:text-slate-400 text-sm">
                  {t('rules_studio.select_prompt') || 'Select a pack to view details, or select 2 packs to compare'}
                </p>
              </div>
            )}
          </div>
        </div>
      </AsyncStateWrapper>
    </div>
  );
}
