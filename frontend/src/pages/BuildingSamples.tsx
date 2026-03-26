import { useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { useDiagnostics, useCreateSample } from '@/hooks/useDiagnostics';
import { diagnosticsApi } from '@/api/diagnostics';
import { buildingsApi } from '@/api/buildings';
import { formatDate, cn } from '@/utils/formatters';
import { formatSampleUnit, SAMPLE_UNIT_OPTIONS } from '@/utils/sampleUnits';
import { POLLUTANT_COLORS, RISK_COLORS } from '@/utils/constants';
import { PollutantBadge } from '@/components/PollutantBadge';
import { BuildingSubNav } from '@/components/BuildingSubNav';
import { RoleGate } from '@/components/RoleGate';
import { toast } from '@/store/toastStore';
import { SAMPLE_UNIT_VALUES, type Sample, type PollutantType, type RiskLevel, type Diagnostic } from '@/types';
import {
  ArrowLeft,
  Plus,
  Loader2,
  X,
  FlaskConical,
  ChevronDown,
  ChevronUp,
  BarChart3,
  Filter,
  AlertCircle,
  Beaker,
  Scale,
  FileText,
  MapPin,
  Hash,
} from 'lucide-react';

// --- Swiss regulatory thresholds ---
const SWISS_THRESHOLDS: Record<
  string,
  { value: number; unit: string; label: string; regulation: string; regulation_detail: string }
> = {
  asbestos: {
    value: 1,
    unit: 'percent_weight',
    label: '>1% poids',
    regulation: 'OTConst Art. 60a / CFST 6503',
    regulation_detail: 'sample.threshold_detail_asbestos',
  },
  pcb: {
    value: 50,
    unit: 'mg_per_kg',
    label: '>50 mg/kg',
    regulation: 'ORRChim Annexe 2.15',
    regulation_detail: 'sample.threshold_detail_pcb',
  },
  lead: {
    value: 5000,
    unit: 'mg_per_kg',
    label: '>5000 mg/kg',
    regulation: 'ORRChim Annexe 2.18',
    regulation_detail: 'sample.threshold_detail_lead',
  },
  hap: {
    value: 200,
    unit: 'mg_per_kg',
    label: '>200 mg/kg',
    regulation: 'OLED',
    regulation_detail: 'sample.threshold_detail_hap',
  },
  radon: {
    value: 300,
    unit: 'bq_per_m3',
    label: '>300 Bq/m3',
    regulation: 'ORaP Art. 110',
    regulation_detail: 'sample.threshold_detail_radon',
  },
};

// --- Risk helpers ---
const RISK_ORDER: Record<string, number> = { critical: 4, high: 3, medium: 2, low: 1, unknown: 0 };

function riskBadgeClasses(level: string): string {
  switch (level) {
    case 'critical':
      return 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400';
    case 'high':
      return 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400';
    case 'medium':
      return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400';
    case 'low':
      return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
    default:
      return 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300';
  }
}

function autoCalculateRiskLevel(pollutant: string, concentration: number): RiskLevel {
  const threshold = SWISS_THRESHOLDS[pollutant];
  if (!threshold) return 'unknown';
  if (concentration <= 0) return 'low';
  const ratio = concentration / threshold.value;
  if (ratio >= 2) return 'critical';
  if (ratio >= 1) return 'high';
  if (ratio >= 0.5) return 'medium';
  return 'low';
}

// --- Sample form schema ---
const sampleSchema = z.object({
  sample_number: z.string().min(1, 'Sample number is required'),
  diagnostic_id: z.string().min(1, 'Diagnostic is required'),
  location_floor: z.string().optional(),
  location_room: z.string().optional(),
  location_detail: z.string().min(1, 'Location detail is required'),
  material_category: z.string().min(1, 'Material category is required'),
  material_description: z.string().optional(),
  material_state: z.string().optional(),
  pollutant_type: z.string().min(1, 'Pollutant type is required'),
  pollutant_subtype: z.string().optional(),
  concentration: z.coerce.number().min(0, 'Concentration must be positive'),
  unit: z.enum(SAMPLE_UNIT_VALUES, { message: 'Unit is required' }),
  notes: z.string().optional(),
});

type SampleFormData = z.infer<typeof sampleSchema>;

// --- Extended sample with diagnostic info ---
interface SampleWithDiagnostic extends Sample {
  diagnostic_type?: string;
  diagnostic_status?: string;
  diagnostic_date?: string;
}

// --- Sort types ---
type SortKey = 'sample_number' | 'pollutant_type' | 'risk_level' | 'concentration' | 'created_at';
type SortDir = 'asc' | 'desc';

export default function BuildingSamples() {
  const { buildingId } = useParams<{ buildingId: string }>();
  const { t, locale } = useTranslation();
  useAuth();

  const [showCreateModal, setShowCreateModal] = useState(false);
  const [expandedSamples, setExpandedSamples] = useState<Set<string>>(new Set());
  const [pollutantFilter, setPollutantFilter] = useState<string>('');
  const [riskFilter, setRiskFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [diagnosticFilter, setDiagnosticFilter] = useState<string>('');
  const [sortKey, setSortKey] = useState<SortKey>('created_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [showFilters, setShowFilters] = useState(false);

  const createSample = useCreateSample();

  // Fetch building
  const { data: building } = useQuery({
    queryKey: ['buildings', buildingId],
    queryFn: () => buildingsApi.get(buildingId!),
    enabled: !!buildingId,
  });

  // Fetch diagnostics for this building
  const { data: diagnosticsData, isLoading: diagLoading } = useDiagnostics(buildingId!);
  const diagnostics: Diagnostic[] = useMemo(
    () => (Array.isArray(diagnosticsData) ? diagnosticsData : []),
    [diagnosticsData],
  );

  // Fetch samples for each diagnostic
  const { data: allSamplesData, isLoading: samplesLoading } = useQuery({
    queryKey: ['building-samples', buildingId, diagnostics.map((d) => d.id).join(',')],
    queryFn: async () => {
      const results: SampleWithDiagnostic[] = [];
      for (const diag of diagnostics) {
        try {
          const samples = await diagnosticsApi.listSamples(diag.id);
          for (const s of samples) {
            results.push({
              ...s,
              diagnostic_type: diag.diagnostic_type,
              diagnostic_status: diag.status,
              diagnostic_date: diag.date_inspection,
            });
          }
        } catch {
          // skip failed diagnostic
        }
      }
      return results;
    },
    enabled: diagnostics.length > 0,
  });

  const allSamples: SampleWithDiagnostic[] = useMemo(
    () => (Array.isArray(allSamplesData) ? allSamplesData : []),
    [allSamplesData],
  );

  const isLoading = diagLoading || samplesLoading;

  // --- Filtering ---
  const filteredSamples = useMemo(() => {
    let result = allSamples;
    if (pollutantFilter) {
      result = result.filter((s) => s.pollutant_type === pollutantFilter);
    }
    if (riskFilter) {
      result = result.filter((s) => (s.risk_level || 'unknown') === riskFilter);
    }
    if (statusFilter) {
      result = result.filter((s) => s.diagnostic_status === statusFilter);
    }
    if (diagnosticFilter) {
      result = result.filter((s) => s.diagnostic_id === diagnosticFilter);
    }
    return result;
  }, [allSamples, pollutantFilter, riskFilter, statusFilter, diagnosticFilter]);

  // --- Sorting ---
  const sortedSamples = useMemo(() => {
    const sorted = [...filteredSamples];
    sorted.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case 'sample_number':
          cmp = (a.sample_number || '').localeCompare(b.sample_number || '');
          break;
        case 'pollutant_type':
          cmp = (a.pollutant_type || '').localeCompare(b.pollutant_type || '');
          break;
        case 'risk_level':
          cmp = (RISK_ORDER[a.risk_level || 'unknown'] || 0) - (RISK_ORDER[b.risk_level || 'unknown'] || 0);
          break;
        case 'concentration':
          cmp = (a.concentration || 0) - (b.concentration || 0);
          break;
        case 'created_at':
          cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [filteredSamples, sortKey, sortDir]);

  // --- Analytics ---
  const analytics = useMemo(() => {
    const pollutantCounts: Record<string, number> = {};
    const riskCounts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, unknown: 0 };
    let exceededCount = 0;
    let highestRisk: RiskLevel = 'unknown';

    for (const s of allSamples) {
      const rl = s.risk_level || 'unknown';
      riskCounts[rl] = (riskCounts[rl] || 0) + 1;
      pollutantCounts[s.pollutant_type] = (pollutantCounts[s.pollutant_type] || 0) + 1;
      if (s.threshold_exceeded) exceededCount++;
      if ((RISK_ORDER[rl] || 0) > (RISK_ORDER[highestRisk] || 0)) {
        highestRisk = rl as RiskLevel;
      }
    }

    return { pollutantCounts, riskCounts, exceededCount, highestRisk, total: allSamples.length };
  }, [allSamples]);

  // --- Grouped by diagnostic ---
  const groupedByDiagnostic = useMemo(() => {
    const groups: Record<string, { diagnostic: Diagnostic; samples: SampleWithDiagnostic[] }> = {};
    for (const s of sortedSamples) {
      if (!groups[s.diagnostic_id]) {
        const diag = diagnostics.find((d) => d.id === s.diagnostic_id);
        if (diag) {
          groups[s.diagnostic_id] = { diagnostic: diag, samples: [] };
        }
      }
      groups[s.diagnostic_id]?.samples.push(s);
    }
    return Object.values(groups);
  }, [sortedSamples, diagnostics]);

  const toggleExpand = (id: string) => {
    setExpandedSamples((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((prev) => (prev === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortKey(key);
      setSortDir('asc');
    }
  };

  const {
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<SampleFormData>({
    resolver: zodResolver(sampleSchema),
  });

  // eslint-disable-next-line react-hooks/incompatible-library -- react-hook-form watch() is intentionally reactive
  const watchedPollutant = watch('pollutant_type');
  const watchedConcentration = watch('concentration');

  const calculatedRisk = useMemo(() => {
    if (!watchedPollutant || watchedConcentration == null || isNaN(watchedConcentration)) return null;
    return autoCalculateRiskLevel(watchedPollutant, watchedConcentration);
  }, [watchedPollutant, watchedConcentration]);

  const onCreateSubmit = async (data: SampleFormData) => {
    const { diagnostic_id, ...sampleData } = data;
    try {
      await createSample.mutateAsync({
        diagnosticId: diagnostic_id,
        data: sampleData as unknown as Partial<Sample>,
      });
      setShowCreateModal(false);
      reset();
      toast(t('sample.created_success'), 'success');
    } catch {
      // error handled by hook
    }
  };

  // --- Sort header component ---
  function SortHeader({ label, sortKeyProp }: { label: string; sortKeyProp: SortKey }) {
    const isActive = sortKey === sortKeyProp;
    return (
      <button
        onClick={() => handleSort(sortKeyProp)}
        className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider hover:text-slate-700 dark:hover:text-slate-200"
      >
        {label}
        {isActive ? (
          sortDir === 'asc' ? (
            <ChevronUp className="w-3 h-3" />
          ) : (
            <ChevronDown className="w-3 h-3" />
          )
        ) : (
          <ChevronDown className="w-3 h-3 opacity-30" />
        )}
      </button>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back link + header */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <Link
          to={buildingId ? `/buildings/${buildingId}` : '/buildings'}
          className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
        >
          <ArrowLeft className="w-4 h-4" />
          {building?.address || t('sample.back_to_building')}
        </Link>
      </div>

      {/* Sub-navigation */}
      {buildingId && <BuildingSubNav buildingId={buildingId} />}

      {/* Page title */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <FlaskConical className="w-6 h-6" />
            {t('sample.page_title')}
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('sample.page_subtitle')}</p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowFilters(!showFilters)}
            className={cn(
              'inline-flex items-center gap-2 px-3 py-2 text-sm font-medium rounded-lg border transition-colors',
              showFilters
                ? 'bg-red-50 text-red-700 border-red-200 dark:bg-red-900/20 dark:text-red-400 dark:border-red-800'
                : 'text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-700 border-gray-200 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600',
            )}
          >
            <Filter className="w-4 h-4" />
            {t('sample.filters')}
          </button>
          <RoleGate allowedRoles={['admin', 'diagnostician']}>
            <button
              onClick={() => setShowCreateModal(true)}
              disabled={diagnostics.length === 0}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed"
              title={diagnostics.length === 0 ? t('sample.no_diagnostics_hint') : ''}
            >
              <Plus className="w-4 h-4" />
              {t('sample.add')}
            </button>
          </RoleGate>
        </div>
      </div>

      {/* Filters panel */}
      {showFilters && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                {t('sample.filter_pollutant')}
              </label>
              <select
                value={pollutantFilter}
                onChange={(e) => setPollutantFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                <option value="">{t('sample.all_pollutants')}</option>
                {(['asbestos', 'pcb', 'lead', 'hap', 'radon'] as const).map((p) => (
                  <option key={p} value={p}>
                    {t(`pollutant.short.${p}`)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                {t('sample.filter_risk')}
              </label>
              <select
                value={riskFilter}
                onChange={(e) => setRiskFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                <option value="">{t('sample.all_risks')}</option>
                {(['critical', 'high', 'medium', 'low', 'unknown'] as const).map((r) => (
                  <option key={r} value={r}>
                    {t(`risk.${r}`)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                {t('sample.filter_diagnostic_status')}
              </label>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                <option value="">{t('sample.all_statuses')}</option>
                {(['draft', 'in_progress', 'completed', 'validated'] as const).map((s) => (
                  <option key={s} value={s}>
                    {t(`diagnostic_status.${s}`)}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                {t('sample.filter_diagnostic')}
              </label>
              <select
                value={diagnosticFilter}
                onChange={(e) => setDiagnosticFilter(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
              >
                <option value="">{t('sample.all_diagnostics')}</option>
                {diagnostics.map((d) => (
                  <option key={d.id} value={d.id}>
                    {t(`pollutant.short.${d.diagnostic_type}`)} - {formatDate(d.date_inspection, 'dd.MM.yyyy', locale)}
                  </option>
                ))}
              </select>
            </div>
          </div>
          {(pollutantFilter || riskFilter || statusFilter || diagnosticFilter) && (
            <div className="mt-3 flex items-center gap-2">
              <span className="text-xs text-gray-500 dark:text-slate-400">
                {sortedSamples.length} / {allSamples.length} {t('sample.samples_shown')}
              </span>
              <button
                onClick={() => {
                  setPollutantFilter('');
                  setRiskFilter('');
                  setStatusFilter('');
                  setDiagnosticFilter('');
                }}
                className="text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
              >
                {t('sample.clear_filters')}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      )}

      {/* Content */}
      {!isLoading && (
        <>
          {/* Summary cards */}
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            {/* Total samples */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm text-center">
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{analytics.total}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{t('sample.total_samples')}</p>
            </div>

            {/* By pollutant - top pollutants */}
            {(['asbestos', 'pcb', 'lead', 'hap', 'radon'] as const)
              .filter((p) => (analytics.pollutantCounts[p] || 0) > 0)
              .slice(0, 3)
              .map((p) => (
                <div
                  key={p}
                  className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm text-center"
                >
                  <p className="text-2xl font-bold" style={{ color: POLLUTANT_COLORS[p] }}>
                    {analytics.pollutantCounts[p] || 0}
                  </p>
                  <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{t(`pollutant.short.${p}`)}</p>
                </div>
              ))}

            {/* Exceeded */}
            <div className="bg-red-50 dark:bg-red-900/20 rounded-xl border border-red-200 dark:border-red-800 p-4 shadow-sm text-center">
              <p className="text-2xl font-bold text-red-700 dark:text-red-400">{analytics.exceededCount}</p>
              <p className="text-xs text-red-600 dark:text-red-400 mt-1">{t('sample.threshold_exceedances')}</p>
            </div>

            {/* Diagnostics count */}
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm text-center">
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{diagnostics.length}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{t('sample.diagnostics_count')}</p>
            </div>
          </div>

          {/* Risk distribution bar */}
          {analytics.total > 0 && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300 flex items-center gap-2">
                  <BarChart3 className="w-4 h-4" />
                  {t('sample.risk_distribution')}
                </h3>
                <span
                  className={cn(
                    'px-2 py-0.5 text-xs font-medium rounded-full',
                    riskBadgeClasses(analytics.highestRisk),
                  )}
                >
                  {t('sample.highest_risk')}: {t(`risk.${analytics.highestRisk}`)}
                </span>
              </div>
              <div className="flex gap-1 h-4 rounded-full overflow-hidden bg-gray-100 dark:bg-slate-700">
                {(['critical', 'high', 'medium', 'low', 'unknown'] as const).map((level) => {
                  const count = analytics.riskCounts[level] || 0;
                  if (count === 0) return null;
                  const pct = (count / analytics.total) * 100;
                  return (
                    <div
                      key={level}
                      className="h-full transition-all"
                      style={{
                        width: `${pct}%`,
                        minWidth: '8px',
                        backgroundColor: RISK_COLORS[level],
                      }}
                      title={`${t(`risk.${level}`)}: ${count}`}
                    />
                  );
                })}
              </div>
              <div className="flex flex-wrap gap-4 mt-2 text-xs">
                {(['critical', 'high', 'medium', 'low', 'unknown'] as const).map((level) => {
                  const count = analytics.riskCounts[level] || 0;
                  if (count === 0) return null;
                  return (
                    <span key={level} className="flex items-center gap-1.5">
                      <span className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: RISK_COLORS[level] }} />
                      <span className="text-gray-600 dark:text-slate-400">
                        {t(`risk.${level}`)}: {count}
                      </span>
                    </span>
                  );
                })}
              </div>
            </div>
          )}

          {/* Samples table / list */}
          {analytics.total === 0 ? (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-12 text-center shadow-sm">
              <FlaskConical className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-lg font-medium text-gray-700 dark:text-slate-300">{t('sample.no_samples')}</p>
              <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('sample.no_samples_hint')}</p>
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
              <div className="p-4 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between">
                <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                  <Beaker className="w-5 h-5" />
                  {t('sample.all_samples')} ({sortedSamples.length})
                </h2>
              </div>

              {/* Desktop table */}
              <div className="hidden lg:block overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700/50">
                      <th className="px-4 py-3 text-left">
                        <SortHeader label={t('sample.number')} sortKeyProp="sample_number" />
                      </th>
                      <th className="px-4 py-3 text-left">
                        <SortHeader label={t('sample.pollutant_type')} sortKeyProp="pollutant_type" />
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        {t('sample.material_category')}
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        {t('sample.location_detail')}
                      </th>
                      <th className="px-4 py-3 text-left">
                        <SortHeader label={t('sample.concentration')} sortKeyProp="concentration" />
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        {t('sample.threshold_exceeded')}
                      </th>
                      <th className="px-4 py-3 text-left">
                        <SortHeader label={t('sample.risk_level')} sortKeyProp="risk_level" />
                      </th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                        {t('sample.linked_diagnostic')}
                      </th>
                      <th className="px-4 py-3 text-left w-10" />
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                    {sortedSamples.map((s) => {
                      const expanded = expandedSamples.has(s.id);
                      return (
                        <SampleRow
                          key={s.id}
                          sample={s}
                          expanded={expanded}
                          onToggle={() => toggleExpand(s.id)}
                          t={t}
                          locale={locale}
                        />
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Mobile cards */}
              <div className="lg:hidden divide-y divide-gray-100 dark:divide-slate-700">
                {sortedSamples.map((s) => {
                  const expanded = expandedSamples.has(s.id);
                  return (
                    <div key={s.id} className="p-4">
                      <button onClick={() => toggleExpand(s.id)} className="w-full text-left">
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-semibold text-gray-900 dark:text-white">
                              {s.sample_number}
                            </span>
                            <PollutantBadge type={s.pollutant_type as PollutantType} size="sm" />
                          </div>
                          <div className="flex items-center gap-2">
                            <span
                              className={cn(
                                'px-2 py-0.5 text-xs font-medium rounded-full',
                                riskBadgeClasses(s.risk_level || 'unknown'),
                              )}
                            >
                              {s.risk_level ? t(`risk.${s.risk_level}`) : '-'}
                            </span>
                            {expanded ? (
                              <ChevronUp className="w-4 h-4 text-gray-400" />
                            ) : (
                              <ChevronDown className="w-4 h-4 text-gray-400" />
                            )}
                          </div>
                        </div>
                        <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400">
                          <MapPin className="w-3 h-3" />
                          {[s.location_floor, s.location_room, s.location_detail].filter(Boolean).join(' - ') || '-'}
                        </div>
                        <div className="flex items-center justify-between mt-1 text-sm">
                          <span className="font-mono text-gray-900 dark:text-white">
                            {s.concentration} {formatSampleUnit(s.unit)}
                          </span>
                          <span
                            className={cn(
                              'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full',
                              s.threshold_exceeded
                                ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
                            )}
                          >
                            {s.threshold_exceeded ? t('sample.above') : t('sample.below')}
                          </span>
                        </div>
                      </button>
                      {expanded && <SampleExpandedDetail sample={s} t={t} locale={locale} />}
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Bulk view: grouped by diagnostic */}
          {groupedByDiagnostic.length > 1 && (
            <div className="space-y-4">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <FileText className="w-5 h-5" />
                {t('sample.grouped_by_diagnostic')}
              </h2>
              {groupedByDiagnostic.map(({ diagnostic: diag, samples }) => (
                <div
                  key={diag.id}
                  className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden"
                >
                  <div className="p-4 border-b border-gray-100 dark:border-slate-700 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <PollutantBadge type={diag.diagnostic_type as PollutantType} size="sm" />
                      <div>
                        <Link
                          to={`/diagnostics/${diag.id}`}
                          className="text-sm font-medium text-gray-900 dark:text-white hover:text-red-600 dark:hover:text-red-400"
                        >
                          {t(`pollutant.short.${diag.diagnostic_type}`)} -{' '}
                          {formatDate(diag.date_inspection, 'dd.MM.yyyy', locale)}
                        </Link>
                        <p className="text-xs text-gray-500 dark:text-slate-400">
                          {t(`diagnostic_status.${diag.status}`)} - {samples.length} {t('sample.samples_count')}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="p-4">
                    <div className="space-y-2">
                      {samples.map((s) => (
                        <div
                          key={s.id}
                          className="flex items-center gap-3 text-sm p-2 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700/50"
                        >
                          <span className="font-mono text-gray-900 dark:text-white w-20 flex-shrink-0">
                            {s.sample_number}
                          </span>
                          <span className="text-gray-600 dark:text-slate-400 flex-1 truncate">
                            {[s.location_floor, s.location_room, s.location_detail].filter(Boolean).join(' - ') || '-'}
                          </span>
                          <span className="font-mono text-gray-900 dark:text-white">
                            {s.concentration} {formatSampleUnit(s.unit)}
                          </span>
                          <span
                            className={cn(
                              'px-2 py-0.5 text-xs font-medium rounded-full flex-shrink-0',
                              riskBadgeClasses(s.risk_level || 'unknown'),
                            )}
                          >
                            {s.risk_level ? t(`risk.${s.risk_level}`) : '-'}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Regulatory reference section */}
          {analytics.total > 0 && (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
              <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-3 flex items-center gap-2">
                <Scale className="w-4 h-4" />
                {t('sample.regulatory_references')}
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                {Object.entries(SWISS_THRESHOLDS)
                  .filter(([p]) => analytics.pollutantCounts[p])
                  .map(([pollutant, info]) => (
                    <div
                      key={pollutant}
                      className="flex items-start gap-3 bg-slate-50 dark:bg-slate-700/30 rounded-lg px-4 py-3"
                    >
                      <span
                        className="w-3 h-3 rounded-full flex-shrink-0 mt-0.5"
                        style={{ backgroundColor: POLLUTANT_COLORS[pollutant] || '#6b7280' }}
                      />
                      <div>
                        <p className="text-sm font-medium text-gray-900 dark:text-white">
                          {t(`pollutant.short.${pollutant}`)}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-slate-400">
                          {t('sample.limit')}: {info.label}
                        </p>
                        <p className="text-xs text-gray-500 dark:text-slate-400">{info.regulation}</p>
                        <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5">{t(info.regulation_detail)}</p>
                      </div>
                    </div>
                  ))}
              </div>
            </div>
          )}
        </>
      )}

      {/* Create Sample Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('sample.add')}</h2>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  reset();
                }}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg"
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>
            <form onSubmit={handleSubmit(onCreateSubmit)} className="space-y-4">
              {/* Diagnostic selector */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  {t('sample.select_diagnostic')} *
                </label>
                <select
                  {...register('diagnostic_id')}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  <option value="">{t('form.select')}</option>
                  {diagnostics.map((d) => (
                    <option key={d.id} value={d.id}>
                      {t(`pollutant.short.${d.diagnostic_type}`)} -{' '}
                      {formatDate(d.date_inspection, 'dd.MM.yyyy', locale)} ({t(`diagnostic_status.${d.status}`)})
                    </option>
                  ))}
                </select>
                {errors.diagnostic_id && <p className="text-xs text-red-600 mt-1">{errors.diagnostic_id.message}</p>}
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.number')} *
                  </label>
                  <input
                    {...register('sample_number')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                  {errors.sample_number && <p className="text-xs text-red-600 mt-1">{errors.sample_number.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.pollutant_type')} *
                  </label>
                  <select
                    {...register('pollutant_type')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    <option value="">{t('diagnostic.selectPollutant')}</option>
                    {(['asbestos', 'pcb', 'lead', 'hap', 'radon'] as const).map((p) => (
                      <option key={p} value={p}>
                        {t(`pollutant.${p}`)}
                      </option>
                    ))}
                  </select>
                  {errors.pollutant_type && (
                    <p className="text-xs text-red-600 mt-1">{errors.pollutant_type.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.location_floor')}
                  </label>
                  <input
                    {...register('location_floor')}
                    placeholder="e.g. 2e etage"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.location_room')}
                  </label>
                  <input
                    {...register('location_room')}
                    placeholder="e.g. Cuisine"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.location_detail')} *
                  </label>
                  <input
                    {...register('location_detail')}
                    placeholder="e.g. Joint de fenetre"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                  {errors.location_detail && (
                    <p className="text-xs text-red-600 mt-1">{errors.location_detail.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.material_category')} *
                  </label>
                  <input
                    {...register('material_category')}
                    placeholder="e.g. Joint, Colle, Revetement"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                  {errors.material_category && (
                    <p className="text-xs text-red-600 mt-1">{errors.material_category.message}</p>
                  )}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.material_description')}
                  </label>
                  <input
                    {...register('material_description')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.material_state')}
                  </label>
                  <input
                    {...register('material_state')}
                    placeholder="e.g. Bon, Degrade, Friable"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.concentration')} *
                  </label>
                  <input
                    type="number"
                    step="any"
                    {...register('concentration')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                  {errors.concentration && <p className="text-xs text-red-600 mt-1">{errors.concentration.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.unit')} *
                  </label>
                  <select
                    {...register('unit')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    <option value="">{t('form.select')}</option>
                    {SAMPLE_UNIT_OPTIONS.map((unit) => (
                      <option key={unit.value} value={unit.value}>
                        {unit.label}
                      </option>
                    ))}
                  </select>
                  {errors.unit && <p className="text-xs text-red-600 mt-1">{errors.unit.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.pollutant_subtype')}
                  </label>
                  <input
                    {...register('pollutant_subtype')}
                    placeholder="e.g. Chrysotile, Amosite"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    {t('sample.notes')}
                  </label>
                  <input
                    {...register('notes')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
              </div>

              {/* Auto-calculated risk preview */}
              {calculatedRisk && (
                <div className="bg-slate-50 dark:bg-slate-700/30 rounded-lg p-3">
                  <div className="flex items-center gap-2 text-sm">
                    <AlertCircle className="w-4 h-4 text-gray-400" />
                    <span className="text-gray-600 dark:text-slate-400">{t('sample.auto_risk')}:</span>
                    <span
                      className={cn('px-2 py-0.5 text-xs font-medium rounded-full', riskBadgeClasses(calculatedRisk))}
                    >
                      {t(`risk.${calculatedRisk}`)}
                    </span>
                    {watchedPollutant && SWISS_THRESHOLDS[watchedPollutant] && (
                      <span className="text-xs text-gray-400 dark:text-slate-500">
                        ({t('sample.limit')}: {SWISS_THRESHOLDS[watchedPollutant].label})
                      </span>
                    )}
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    reset();
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-600"
                >
                  {t('form.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={createSample.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
                >
                  {createSample.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  {t('form.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Sample table row ---
function SampleRow({
  sample,
  expanded,
  onToggle,
  t,
  locale,
}: {
  sample: SampleWithDiagnostic;
  expanded: boolean;
  onToggle: () => void;
  t: (key: string) => string;
  locale: string;
}) {
  const s = sample;
  return (
    <>
      <tr onClick={onToggle} className="cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors">
        <td className="px-4 py-3 text-sm font-mono text-gray-900 dark:text-white">{s.sample_number}</td>
        <td className="px-4 py-3">
          <PollutantBadge type={s.pollutant_type as PollutantType} size="sm" />
        </td>
        <td className="px-4 py-3 text-sm text-gray-700 dark:text-slate-300">{s.material_category || '-'}</td>
        <td className="px-4 py-3 text-sm text-gray-700 dark:text-slate-300">
          {[s.location_floor, s.location_room, s.location_detail].filter(Boolean).join(' - ') || '-'}
        </td>
        <td className="px-4 py-3 text-sm font-mono text-gray-900 dark:text-white">
          {s.concentration} {formatSampleUnit(s.unit)}
        </td>
        <td className="px-4 py-3">
          <span
            className={cn(
              'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full',
              s.threshold_exceeded
                ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
            )}
          >
            {s.threshold_exceeded ? t('sample.above') : t('sample.below')}
          </span>
        </td>
        <td className="px-4 py-3">
          <span
            className={cn('px-2 py-0.5 text-xs font-medium rounded-full', riskBadgeClasses(s.risk_level || 'unknown'))}
          >
            {s.risk_level ? t(`risk.${s.risk_level}`) : '-'}
          </span>
        </td>
        <td className="px-4 py-3">
          <Link
            to={`/diagnostics/${s.diagnostic_id}`}
            onClick={(e) => e.stopPropagation()}
            className="text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300"
          >
            {s.diagnostic_type ? t(`pollutant.short.${s.diagnostic_type}`) : '-'}
            {s.diagnostic_date && ` - ${formatDate(s.diagnostic_date, 'dd.MM.yy', locale)}`}
          </Link>
        </td>
        <td className="px-4 py-3">
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={9} className="px-4 pb-4 pt-0">
            <SampleExpandedDetail sample={s} t={t} locale={locale} />
          </td>
        </tr>
      )}
    </>
  );
}

// --- Expanded detail panel ---
function SampleExpandedDetail({
  sample,
  t,
  locale: _locale,
}: {
  sample: SampleWithDiagnostic;
  t: (key: string) => string;
  locale: string;
}) {
  const s = sample;
  const threshold = SWISS_THRESHOLDS[s.pollutant_type];

  return (
    <div className="mt-3 bg-slate-50 dark:bg-slate-700/30 rounded-lg p-4 space-y-4">
      {/* Lab results / details */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 text-sm">
        <div>
          <span className="text-gray-500 dark:text-slate-400">{t('sample.material_category')}:</span>{' '}
          <span className="text-gray-900 dark:text-white">{s.material_category || '-'}</span>
        </div>
        <div>
          <span className="text-gray-500 dark:text-slate-400">{t('sample.material_description')}:</span>{' '}
          <span className="text-gray-900 dark:text-white">{s.material_description || '-'}</span>
        </div>
        {s.material_state && (
          <div>
            <span className="text-gray-500 dark:text-slate-400">{t('sample.material_state')}:</span>{' '}
            <span className="text-gray-900 dark:text-white">{s.material_state}</span>
          </div>
        )}
        {s.pollutant_subtype && (
          <div>
            <span className="text-gray-500 dark:text-slate-400">{t('sample.pollutant_subtype')}:</span>{' '}
            <span className="text-gray-900 dark:text-white">{s.pollutant_subtype}</span>
          </div>
        )}
        {s.cfst_work_category && (
          <div>
            <span className="text-gray-500 dark:text-slate-400">{t('sample.cfst_work_category')}:</span>{' '}
            <span className="text-gray-900 dark:text-white">{s.cfst_work_category}</span>
          </div>
        )}
        {s.waste_disposal_type && (
          <div>
            <span className="text-gray-500 dark:text-slate-400">{t('sample.waste_disposal_type')}:</span>{' '}
            <span className="text-gray-900 dark:text-white">{s.waste_disposal_type}</span>
          </div>
        )}
        {s.action_required && (
          <div className="sm:col-span-2">
            <span className="text-gray-500 dark:text-slate-400">{t('sample.action_required')}:</span>{' '}
            <span className="text-orange-700 dark:text-orange-400 font-medium">{s.action_required}</span>
          </div>
        )}
        {s.notes && (
          <div className="sm:col-span-2 lg:col-span-3">
            <span className="text-gray-500 dark:text-slate-400">{t('sample.notes')}:</span>{' '}
            <span className="text-gray-900 dark:text-white">{s.notes}</span>
          </div>
        )}
      </div>

      {/* Threshold comparison bar */}
      {threshold && s.concentration != null && (
        <div>
          <h4 className="text-xs font-semibold text-gray-600 dark:text-slate-400 mb-2 flex items-center gap-1.5">
            <Scale className="w-3.5 h-3.5" />
            {t('sample.threshold_comparison')}
          </h4>
          <ThresholdComparisonBar sample={s} threshold={threshold} t={t} />
        </div>
      )}

      {/* Regulatory reference */}
      {threshold && (
        <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-600 px-4 py-3">
          <div className="flex items-start gap-2">
            <Hash className="w-4 h-4 text-gray-400 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-xs font-medium text-gray-700 dark:text-slate-300">{t('sample.regulatory_ref')}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">{threshold.regulation}</p>
              <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5">{t(threshold.regulation_detail)}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// --- Threshold comparison bar (standalone for expanded detail) ---
function ThresholdComparisonBar({
  sample,
  threshold,
  t,
}: {
  sample: Sample;
  threshold: { value: number; unit: string; label: string };
  t: (key: string) => string;
}) {
  if (sample.concentration == null) return null;

  const ratio = sample.concentration / threshold.value;
  const barPct = Math.min(ratio * 100, 200);
  const displayPct = Math.min(barPct, 100);
  const isExceeded = ratio >= 1;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-xs">
        <span className="text-gray-500 dark:text-slate-400">
          {sample.concentration} {formatSampleUnit(sample.unit)} / {threshold.value} {formatSampleUnit(threshold.unit)}
        </span>
        <span
          className={cn(
            'font-medium',
            isExceeded ? 'text-red-600 dark:text-red-400' : 'text-green-600 dark:text-green-400',
          )}
        >
          {(ratio * 100).toFixed(0)}%
        </span>
      </div>
      <div className="relative h-3 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
        <div className="absolute left-1/2 top-0 bottom-0 w-0.5 bg-gray-400 dark:bg-slate-500 z-10" />
        <div
          className={cn(
            'h-full rounded-full transition-all',
            isExceeded ? 'bg-red-500 dark:bg-red-600' : 'bg-green-500 dark:bg-green-600',
          )}
          style={{ width: `${displayPct / 2}%` }}
        />
      </div>
      <div className="flex justify-between text-[10px] text-gray-400 dark:text-slate-500">
        <span>0</span>
        <span>{t('sample.swiss_limit')}</span>
        <span>2x</span>
      </div>
    </div>
  );
}
