/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under BuildingDetail (Building Home).
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useMemo, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  useDiagnostic,
  useSamples,
  useCreateSample,
  useUploadReport,
  useValidateDiagnostic,
} from '@/hooks/useDiagnostics';
import { useAuth } from '@/hooks/useAuth';
import { useTranslation } from '@/i18n';
import { formatDate, cn } from '@/utils/formatters';
import { formatSampleUnit, SAMPLE_UNIT_OPTIONS } from '@/utils/sampleUnits';
import { POLLUTANT_COLORS, RISK_COLORS } from '@/utils/constants';
import { diagnosticsApi } from '@/api/diagnostics';
import { toast } from '@/store/toastStore';
import { DiagnosticViewSkeleton } from '@/components/Skeleton';
import { CostEstimationModal } from '@/components/CostEstimationModal';
import { DataTable } from '@/components/DataTable';
import { PollutantBadge } from '@/components/PollutantBadge';
import { FileUpload } from '@/components/FileUpload';
import { RoleGate } from '@/components/RoleGate';
import {
  SAMPLE_UNIT_VALUES,
  type Sample,
  type PollutantType,
  type RiskLevel,
  type ParseReportResponse,
  type ParsedSampleData,
} from '@/types';
import {
  ArrowLeft,
  Plus,
  Loader2,
  CheckCircle2,
  Clock,
  AlertTriangle,
  FileText,
  X,
  Shield,
  Bell,
  User,
  FlaskConical,
  Hash,
  Building2,
  Download,
  ChevronDown,
  ChevronUp,
  Activity,
  BarChart3,
  BookOpen,
  MapPin,
  AlertCircle,
  Calculator,
} from 'lucide-react';

const sampleSchema = z.object({
  sample_number: z.string().min(1, 'Sample number is required'),
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

// --- Risk level helpers ---
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

// --- Threshold references per pollutant ---
const THRESHOLD_REFS: Record<string, string> = {
  asbestos: 'diagnostic.threshold_asbestos',
  pcb: 'diagnostic.threshold_pcb',
  lead: 'diagnostic.threshold_lead',
  hap: 'diagnostic.threshold_hap',
  radon: 'diagnostic.threshold_radon',
};

export default function DiagnosticView() {
  const { t, locale } = useTranslation();
  const { id } = useParams<{ id: string }>();
  useAuth();

  const { data: diagnostic, isLoading, isError } = useDiagnostic(id!);
  const { data: samplesData } = useSamples(id!);
  const createSample = useCreateSample();
  const uploadReport = useUploadReport();
  const validateDiagnostic = useValidateDiagnostic();

  const samples: Sample[] = useMemo(() => (Array.isArray(samplesData) ? samplesData : []), [samplesData]);

  const [showSampleModal, setShowSampleModal] = useState(false);
  const [parseResult, setParseResult] = useState<ParseReportResponse | null>(null);
  const [isParsing, setIsParsing] = useState(false);
  const [isApplying, setIsApplying] = useState(false);
  const [editedSamples, setEditedSamples] = useState<ParsedSampleData[]>([]);
  const [expandedSamples, setExpandedSamples] = useState<Set<string>>(new Set());
  const [showCostModal, setShowCostModal] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<SampleFormData>({
    resolver: zodResolver(sampleSchema),
  });

  // --- Derived sample analytics ---
  const sampleAnalytics = useMemo(() => {
    const riskCounts: Record<string, number> = { critical: 0, high: 0, medium: 0, low: 0, unknown: 0 };
    const pollutantRisks: Record<string, RiskLevel> = {};
    const pollutantCounts: Record<string, number> = {};
    let exceededCount = 0;
    let highestRisk: RiskLevel = 'unknown';

    for (const s of samples) {
      const rl = s.risk_level || 'unknown';
      riskCounts[rl] = (riskCounts[rl] || 0) + 1;
      if ((RISK_ORDER[rl] || 0) > (RISK_ORDER[highestRisk] || 0)) {
        highestRisk = rl as RiskLevel;
      }
      if (s.threshold_exceeded) exceededCount++;

      const pt = s.pollutant_type;
      pollutantCounts[pt] = (pollutantCounts[pt] || 0) + 1;
      const existing = pollutantRisks[pt] || 'unknown';
      if ((RISK_ORDER[rl] || 0) > (RISK_ORDER[existing] || 0)) {
        pollutantRisks[pt] = rl as RiskLevel;
      }
    }

    return { riskCounts, pollutantRisks, pollutantCounts, exceededCount, highestRisk };
  }, [samples]);

  // --- Timeline events derived from diagnostic + samples ---
  const timelineEvents = useMemo(() => {
    const events: { date: string; type: string; label: string; detail?: string }[] = [];
    if (!diagnostic) return events;

    events.push({
      date: diagnostic.created_at,
      type: 'created',
      label: t('diagnostic.statusChange'),
      detail: t('diagnostic_status.draft'),
    });

    if (diagnostic.date_inspection) {
      events.push({
        date: diagnostic.date_inspection,
        type: 'inspection',
        label: t('diagnostic.inspectionDate'),
      });
    }

    if (diagnostic.status === 'in_progress' || diagnostic.status === 'completed' || diagnostic.status === 'validated') {
      // approximate: no separate timestamp for in_progress, use updated_at
      if (diagnostic.updated_at !== diagnostic.created_at) {
        events.push({
          date: diagnostic.updated_at,
          type: 'status',
          label: t('diagnostic.statusChange'),
          detail: t(`diagnostic_status.${diagnostic.status}`),
        });
      }
    }

    if (diagnostic.date_report) {
      events.push({
        date: diagnostic.date_report,
        type: 'report',
        label: t('diagnostic.reportDate'),
      });
    }

    for (const s of samples) {
      events.push({
        date: s.created_at,
        type: 'sample',
        label: t('diagnostic.sampleAdded'),
        detail: `${s.sample_number} - ${t(`pollutant.short.${s.pollutant_type}`)}`,
      });
    }

    events.sort((a, b) => new Date(b.date).getTime() - new Date(a.date).getTime());
    return events;
  }, [diagnostic, samples, t]);

  const toggleSampleExpand = (sampleId: string) => {
    setExpandedSamples((prev) => {
      const next = new Set(prev);
      if (next.has(sampleId)) next.delete(sampleId);
      else next.add(sampleId);
      return next;
    });
  };

  const onSampleSubmit = async (data: SampleFormData) => {
    try {
      await createSample.mutateAsync({ diagnosticId: id!, data: data as unknown as Partial<Sample> });
      setShowSampleModal(false);
      reset();
    } catch {}
  };

  const onValidate = async () => {
    if (!id) return;
    try {
      const result = await validateDiagnostic.mutateAsync(id);
      const count = (result as any)?.generated_actions_count;
      if (count && count > 0) {
        toast(t('action.generated_count').replace('{count}', String(count)), 'success');
      }
    } catch {
      // error handled by hook
    }
  };

  const onReportUpload = async (file: File) => {
    try {
      await uploadReport.mutateAsync({ id: id!, file });
    } catch {}
  };

  const onParseReport = async (file: File) => {
    setIsParsing(true);
    try {
      const result = await diagnosticsApi.parseReport(id!, file);
      setParseResult(result);
      setEditedSamples(result.samples);
    } catch {
      // fallback to direct upload if parse endpoint not available
      await onReportUpload(file);
    } finally {
      setIsParsing(false);
    }
  };

  const onApplyReport = async () => {
    if (!parseResult) return;
    setIsApplying(true);
    try {
      await diagnosticsApi.applyReport(id!, { samples: editedSamples });
      setParseResult(null);
      setEditedSamples([]);
    } catch {
      // silent
    } finally {
      setIsApplying(false);
    }
  };

  const statusConfig: Record<string, { color: string; icon: React.ElementType; bg: string }> = {
    draft: { color: 'text-gray-600 dark:text-slate-300', icon: Clock, bg: 'bg-gray-100 dark:bg-slate-700' },
    in_progress: {
      color: 'text-blue-600 dark:text-blue-400',
      icon: FlaskConical,
      bg: 'bg-blue-100 dark:bg-blue-900/30',
    },
    completed: {
      color: 'text-green-600 dark:text-green-400',
      icon: CheckCircle2,
      bg: 'bg-green-100 dark:bg-green-900/30',
    },
    validated: {
      color: 'text-emerald-600 dark:text-emerald-400',
      icon: Shield,
      bg: 'bg-emerald-100 dark:bg-emerald-900/30',
    },
  };

  const sampleColumns = [
    { key: 'sample_number', header: t('sample.number'), sortable: true },
    {
      key: 'location_detail',
      header: t('sample.location_detail'),
      sortable: true,
      render: (row: Sample) => (
        <span className="text-sm">
          {[row.location_floor, row.location_room, row.location_detail].filter(Boolean).join(' - ') || '-'}
        </span>
      ),
    },
    {
      key: 'material_description',
      header: t('sample.material_description'),
      sortable: true,
      render: (row: Sample) => <span className="text-sm">{row.material_description || '-'}</span>,
    },
    {
      key: 'pollutant_type',
      header: t('sample.pollutant_type'),
      render: (row: Sample) => <PollutantBadge type={row.pollutant_type as PollutantType} />,
    },
    {
      key: 'concentration',
      header: t('sample.concentration'),
      sortable: true,
      render: (row: Sample) => {
        return (
          <span className="font-mono text-sm">
            {row.concentration} {formatSampleUnit(row.unit)}
          </span>
        );
      },
    },
    {
      key: 'threshold_exceeded',
      header: t('sample.threshold_exceeded'),
      render: (row: Sample) => (
        <span
          className={cn(
            'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full',
            row.threshold_exceeded ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700',
          )}
        >
          {row.threshold_exceeded ? t('form.yes') : t('form.no')}
        </span>
      ),
    },
    {
      key: 'risk_level',
      header: t('sample.risk_level'),
      render: (row: Sample) => {
        const val = row.risk_level;
        return (
          <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', riskBadgeClasses(val || 'unknown'))}>
            {val ? t(`risk.${val}`) || val : '-'}
          </span>
        );
      },
    },
    {
      key: 'cfst_work_category',
      header: t('sample.cfst_work_category'),
      render: (row: Sample) => <span className="text-sm">{row.cfst_work_category || '-'}</span>,
    },
    {
      key: 'action_required',
      header: t('sample.action_required'),
      render: (row: Sample) =>
        row.action_required ? (
          <span className="text-sm text-orange-700 font-medium">{row.action_required}</span>
        ) : (
          <span className="text-sm text-gray-500">-</span>
        ),
    },
  ];

  if (isLoading) {
    return <DiagnosticViewSkeleton />;
  }

  if (isError || !diagnostic) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('diagnostic.notFound')}</p>
      </div>
    );
  }

  const d = diagnostic;
  const status = statusConfig[d.status] || statusConfig.draft;
  const StatusIcon = status.icon;

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        to={d.building_id ? `/buildings/${d.building_id}` : '/buildings'}
        className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
      >
        <ArrowLeft className="w-4 h-4" />
        {t('diagnostic.backToBuilding')}
      </Link>

      {/* ===== 1. STATUS HEADER ===== */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="space-y-3">
            <div className="flex items-center gap-3 flex-wrap">
              <PollutantBadge type={d.diagnostic_type as PollutantType} />
              {d.diagnostic_type === 'full' && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400">
                  {t('diagnostic_type.full') || 'Full'}
                </span>
              )}
              <div
                className={cn(
                  'inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium',
                  status.bg,
                  status.color,
                )}
              >
                <StatusIcon className="w-4 h-4" />
                {t(`diagnostic_status.${d.status}`) || d.status}
              </div>
              {d.diagnostic_context && (
                <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300">
                  {t(`diagnostic_context.${d.diagnostic_context}`) || d.diagnostic_context}
                </span>
              )}
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-slate-400">
              {d.date_inspection && (
                <span className="flex items-center gap-1">
                  <Clock className="w-4 h-4" />
                  {t('diagnostic.inspectionDate')}: {formatDate(d.date_inspection, 'dd.MM.yyyy', locale)}
                </span>
              )}
              {d.date_report && (
                <span className="flex items-center gap-1">
                  <CheckCircle2 className="w-4 h-4" />
                  {t('diagnostic.reportDate')}: {formatDate(d.date_report, 'dd.MM.yyyy', locale)}
                </span>
              )}
              {d.created_at && (
                <span className="flex items-center gap-1">
                  <FileText className="w-4 h-4" />
                  {t('diagnostic.createdOn')} {formatDate(d.created_at, 'dd.MM.yyyy', locale)}
                </span>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {d.building_id && (
              <Link
                to={`/buildings/${d.building_id}`}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-600"
              >
                <Building2 className="w-4 h-4" />
                {t('diagnostic.viewBuilding')}
              </Link>
            )}
            <RoleGate allowedRoles={['admin', 'diagnostician']}>
              <button
                onClick={() => setShowSampleModal(true)}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
              >
                <Plus className="w-4 h-4" />
                {t('sample.add')}
              </button>
            </RoleGate>
            <RoleGate allowedRoles={['admin', 'authority']}>
              {d.status === 'completed' && (
                <button
                  onClick={onValidate}
                  disabled={validateDiagnostic.isPending}
                  className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/30 border border-green-200 dark:border-green-800 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/50 disabled:opacity-50"
                >
                  {validateDiagnostic.isPending ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                  ) : (
                    <Shield className="w-4 h-4" />
                  )}
                  {t('diagnostic.validate')}
                </button>
              )}
            </RoleGate>
            <button
              onClick={() => setShowCostModal(true)}
              className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/50"
            >
              <Calculator className="w-4 h-4" />
              {t('cost_prediction.title') || 'Estimation des couts'}
            </button>
            <button className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-600">
              <Download className="w-4 h-4" />
              {t('diagnostic.exportReport')}
            </button>
          </div>
        </div>
      </div>

      {/* Info Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 mb-1">
            <User className="w-4 h-4" />
            {t('diagnostic.diagnostician')}
          </div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{d.diagnostician_id || '-'}</p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 mb-1">
            <FlaskConical className="w-4 h-4" />
            {t('diagnostic.laboratory')}
          </div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{d.laboratory || '-'}</p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 mb-1">
            <FileText className="w-4 h-4" />
            {t('diagnostic.methodology')}
          </div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{d.methodology || '-'}</p>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 mb-1">
            <Hash className="w-4 h-4" />
            {t('diagnostic.reportNumber')}
          </div>
          <p className="text-sm font-medium text-gray-900 dark:text-white">{d.laboratory_report_number || '-'}</p>
        </div>
      </div>

      {/* Summary/Conclusion */}
      {(d.summary || d.conclusion) && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm space-y-4">
          {d.summary && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1 flex items-center gap-2">
                <BookOpen className="w-4 h-4" />
                {t('diagnostic.summary_label')}
              </h3>
              <p className="text-sm text-gray-600 dark:text-slate-400">{d.summary}</p>
            </div>
          )}
          {d.conclusion && (
            <div>
              <h3 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-1 flex items-center gap-2">
                <CheckCircle2 className="w-4 h-4" />
                {t('diagnostic.conclusion_label')}
              </h3>
              <p className="text-sm text-gray-600 dark:text-slate-400">{d.conclusion}</p>
            </div>
          )}
        </div>
      )}

      {/* SUVA Notification */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Bell className="w-5 h-5 text-gray-400 dark:text-slate-500" />
            <div>
              <p className="text-sm font-medium text-gray-900 dark:text-white">{t('diagnostic.suvaNotification')}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">{t('diagnostic.suvaDescription')}</p>
            </div>
          </div>
          <span
            className={cn(
              'px-3 py-1 text-xs font-medium rounded-full',
              d.suva_notification_required
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
            )}
          >
            {d.suva_notification_required ? t('diagnostic.notified') : t('diagnostic.notNotified')}
          </span>
        </div>
      </div>

      {/* ===== 4. RISK SUMMARY ===== */}
      {samples.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-gray-100 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <BarChart3 className="w-5 h-5" />
              {t('diagnostic.riskSummary')}
            </h2>
          </div>
          <div className="p-6 space-y-6">
            {/* Overall risk card */}
            <div className="flex flex-col sm:flex-row gap-4">
              <div
                className={cn(
                  'flex-1 rounded-xl p-5 border-2',
                  sampleAnalytics.highestRisk === 'critical'
                    ? 'border-red-300 bg-red-50 dark:border-red-800 dark:bg-red-900/20'
                    : sampleAnalytics.highestRisk === 'high'
                      ? 'border-orange-300 bg-orange-50 dark:border-orange-800 dark:bg-orange-900/20'
                      : sampleAnalytics.highestRisk === 'medium'
                        ? 'border-yellow-300 bg-yellow-50 dark:border-yellow-800 dark:bg-yellow-900/20'
                        : 'border-green-300 bg-green-50 dark:border-green-800 dark:bg-green-900/20',
                )}
              >
                <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1 uppercase tracking-wider">
                  {t('diagnostic.overallRisk')}
                </p>
                <div className="flex items-center gap-3">
                  <AlertCircle
                    className="w-8 h-8"
                    style={{ color: RISK_COLORS[sampleAnalytics.highestRisk] || RISK_COLORS.unknown }}
                  />
                  <div>
                    <p
                      className="text-2xl font-bold"
                      style={{ color: RISK_COLORS[sampleAnalytics.highestRisk] || RISK_COLORS.unknown }}
                    >
                      {t(`risk.${sampleAnalytics.highestRisk}`) || sampleAnalytics.highestRisk}
                    </p>
                    <p className="text-xs text-gray-500 dark:text-slate-400">{t('diagnostic.highestRiskFound')}</p>
                  </div>
                </div>
              </div>

              {/* Sample stats */}
              <div className="flex-1 grid grid-cols-3 gap-3">
                <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-gray-900 dark:text-white">{samples.length}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">{t('diagnostic.samplesTotal')}</p>
                </div>
                <div className="bg-red-50 dark:bg-red-900/20 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-red-700 dark:text-red-400">{sampleAnalytics.exceededCount}</p>
                  <p className="text-xs text-red-600 dark:text-red-400">{t('diagnostic.samplesExceeded')}</p>
                </div>
                <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3 text-center">
                  <p className="text-2xl font-bold text-green-700 dark:text-green-400">
                    {samples.length - sampleAnalytics.exceededCount}
                  </p>
                  <p className="text-xs text-green-600 dark:text-green-400">{t('diagnostic.samplesClean')}</p>
                </div>
              </div>
            </div>

            {/* Risk distribution bar */}
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                {t('diagnostic.riskDistribution')}
              </p>
              <div className="flex gap-2 mb-2">
                {(['critical', 'high', 'medium', 'low'] as const).map((level) => {
                  const count = sampleAnalytics.riskCounts[level] || 0;
                  if (count === 0) return null;
                  const pct = (count / samples.length) * 100;
                  return (
                    <div
                      key={level}
                      className="h-3 rounded-full"
                      style={{
                        width: `${pct}%`,
                        minWidth: count > 0 ? '12px' : '0',
                        backgroundColor: RISK_COLORS[level],
                      }}
                      title={`${t(`risk.${level}`)}: ${count}`}
                    />
                  );
                })}
              </div>
              <div className="flex flex-wrap gap-4 text-xs">
                {(['critical', 'high', 'medium', 'low'] as const).map((level) => {
                  const count = sampleAnalytics.riskCounts[level] || 0;
                  const key = `diagnostic.${level}Count` as const;
                  return (
                    <span key={level} className="flex items-center gap-1.5">
                      <span
                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ backgroundColor: RISK_COLORS[level] }}
                      />
                      <span className="text-gray-600 dark:text-slate-400">
                        {t(key)}: {count}
                      </span>
                    </span>
                  );
                })}
              </div>
            </div>

            {/* Risk by pollutant badge grid */}
            {Object.keys(sampleAnalytics.pollutantRisks).length > 0 && (
              <div>
                <p className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                  {t('diagnostic.riskByPollutant')}
                </p>
                <div className="flex flex-wrap gap-3">
                  {Object.entries(sampleAnalytics.pollutantRisks).map(([pollutant, riskLevel]) => (
                    <div
                      key={pollutant}
                      className="flex items-center gap-2 bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2"
                    >
                      <span
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: POLLUTANT_COLORS[pollutant] || '#6b7280' }}
                      />
                      <span className="text-sm font-medium text-gray-900 dark:text-white">
                        {t(`pollutant.short.${pollutant}`) || pollutant}
                      </span>
                      <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', riskBadgeClasses(riskLevel))}>
                        {t(`risk.${riskLevel}`) || riskLevel}
                      </span>
                      <span className="text-xs text-gray-500 dark:text-slate-400">
                        ({sampleAnalytics.pollutantCounts[pollutant]} {t('diagnostic.samples').toLowerCase()})
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Threshold references */}
            <div>
              <p className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">
                {t('diagnostic.thresholdRef')}
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {Object.entries(sampleAnalytics.pollutantRisks).map(([pollutant]) => {
                  const refKey = THRESHOLD_REFS[pollutant];
                  if (!refKey) return null;
                  return (
                    <div
                      key={pollutant}
                      className="flex items-center gap-2 text-xs text-gray-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-700/30 rounded px-3 py-2"
                    >
                      <span
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: POLLUTANT_COLORS[pollutant] || '#6b7280' }}
                      />
                      <span className="font-medium">{t(`pollutant.short.${pollutant}`) || pollutant}:</span>
                      <span>{t(refKey)}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ===== 2. FINDINGS SECTION (from samples with exceeded thresholds) ===== */}
      {samples.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="p-6 border-b border-gray-100 dark:border-slate-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <AlertTriangle className="w-5 h-5" />
              {t('diagnostic.findings')}
            </h2>
          </div>
          <div className="p-6">
            {sampleAnalytics.exceededCount > 0 ? (
              <div className="space-y-3">
                {samples
                  .filter((s) => s.threshold_exceeded)
                  .sort(
                    (a, b) =>
                      (RISK_ORDER[b.risk_level || 'unknown'] || 0) - (RISK_ORDER[a.risk_level || 'unknown'] || 0),
                  )
                  .map((s) => {
                    const expanded = expandedSamples.has(s.id);
                    return (
                      <div
                        key={s.id}
                        className="border border-gray-200 dark:border-slate-700 rounded-lg overflow-hidden"
                      >
                        <button
                          onClick={() => toggleSampleExpand(s.id)}
                          className="w-full flex items-center gap-3 p-4 text-left hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
                        >
                          <PollutantBadge type={s.pollutant_type as PollutantType} size="sm" />
                          <span
                            className={cn(
                              'px-2 py-0.5 text-xs font-medium rounded-full',
                              riskBadgeClasses(s.risk_level || 'unknown'),
                            )}
                          >
                            {t(`risk.${s.risk_level || 'unknown'}`) || s.risk_level}
                          </span>
                          <span className="flex-1 text-sm text-gray-900 dark:text-white font-medium">
                            {[s.location_floor, s.location_room, s.location_detail].filter(Boolean).join(' - ')}
                          </span>
                          <span className="text-sm font-mono text-gray-600 dark:text-slate-400">
                            {s.concentration} {formatSampleUnit(s.unit)}
                          </span>
                          {expanded ? (
                            <ChevronUp className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          )}
                        </button>
                        {expanded && (
                          <div className="px-4 pb-4 pt-0 border-t border-gray-100 dark:border-slate-700">
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-3 text-sm">
                              <div>
                                <span className="text-gray-500 dark:text-slate-400">
                                  {t('sample.material_category')}:
                                </span>{' '}
                                <span className="text-gray-900 dark:text-white">{s.material_category || '-'}</span>
                              </div>
                              <div>
                                <span className="text-gray-500 dark:text-slate-400">
                                  {t('sample.material_description')}:
                                </span>{' '}
                                <span className="text-gray-900 dark:text-white">{s.material_description || '-'}</span>
                              </div>
                              {s.material_state && (
                                <div>
                                  <span className="text-gray-500 dark:text-slate-400">
                                    {t('sample.material_state')}:
                                  </span>{' '}
                                  <span className="text-gray-900 dark:text-white">{s.material_state}</span>
                                </div>
                              )}
                              {s.cfst_work_category && (
                                <div>
                                  <span className="text-gray-500 dark:text-slate-400">
                                    {t('diagnostic.workCategory')}:
                                  </span>{' '}
                                  <span className="text-gray-900 dark:text-white">{s.cfst_work_category}</span>
                                </div>
                              )}
                              {s.waste_disposal_type && (
                                <div>
                                  <span className="text-gray-500 dark:text-slate-400">
                                    {t('diagnostic.wasteDisposal')}:
                                  </span>{' '}
                                  <span className="text-gray-900 dark:text-white">{s.waste_disposal_type}</span>
                                </div>
                              )}
                              {s.action_required && (
                                <div className="sm:col-span-2">
                                  <span className="text-gray-500 dark:text-slate-400">
                                    {t('sample.action_required')}:
                                  </span>{' '}
                                  <span className="text-orange-700 dark:text-orange-400 font-medium">
                                    {s.action_required}
                                  </span>
                                </div>
                              )}
                              {s.notes && (
                                <div className="sm:col-span-2">
                                  <span className="text-gray-500 dark:text-slate-400">{t('sample.notes')}:</span>{' '}
                                  <span className="text-gray-900 dark:text-white">{s.notes}</span>
                                </div>
                              )}
                              {THRESHOLD_REFS[s.pollutant_type] && (
                                <div className="sm:col-span-2 bg-slate-50 dark:bg-slate-700/30 rounded px-3 py-2">
                                  <span className="text-gray-500 dark:text-slate-400">
                                    {t('diagnostic.thresholdRef')}:
                                  </span>{' '}
                                  <span className="text-gray-700 dark:text-slate-300 text-xs">
                                    {t(THRESHOLD_REFS[s.pollutant_type])}
                                  </span>
                                </div>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    );
                  })}
              </div>
            ) : (
              <div className="text-center py-6">
                <CheckCircle2 className="w-8 h-8 text-green-400 mx-auto mb-2" />
                <p className="text-sm text-gray-500 dark:text-slate-400">{t('diagnostic.noSamplesExceeded')}</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* ===== 3. SAMPLES PANEL ===== */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-100 dark:border-slate-700">
          <div className="flex items-center justify-between">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <FlaskConical className="w-5 h-5" />
              {t('diagnostic.samples')} ({samples.length})
            </h2>
          </div>
        </div>
        <div className="p-6">
          {samples.length > 0 ? (
            <>
              {/* Sample cards for small screen, DataTable for larger */}
              <div className="hidden lg:block">
                <DataTable columns={sampleColumns} data={samples} />
              </div>
              <div className="lg:hidden space-y-3">
                {samples.map((s) => (
                  <div key={s.id} className="border border-gray-200 dark:border-slate-700 rounded-lg p-4 space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-gray-900 dark:text-white">{s.sample_number}</span>
                        <PollutantBadge type={s.pollutant_type as PollutantType} size="sm" />
                      </div>
                      <span
                        className={cn(
                          'px-2 py-0.5 text-xs font-medium rounded-full',
                          riskBadgeClasses(s.risk_level || 'unknown'),
                        )}
                      >
                        {s.risk_level ? t(`risk.${s.risk_level}`) || s.risk_level : '-'}
                      </span>
                    </div>
                    <div className="flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400">
                      <MapPin className="w-3 h-3" />
                      {[s.location_floor, s.location_room, s.location_detail].filter(Boolean).join(' - ') || '-'}
                    </div>
                    <div className="flex items-center justify-between text-sm">
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
                        {s.threshold_exceeded ? t('diagnostic.aboveThreshold') : t('diagnostic.belowThreshold')}
                      </span>
                    </div>
                    {s.material_description && (
                      <p className="text-xs text-gray-500 dark:text-slate-400">{s.material_description}</p>
                    )}
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="text-center py-8">
              <FlaskConical className="w-10 h-10 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500">{t('diagnostic.noSamples')}</p>
            </div>
          )}
        </div>
      </div>

      {/* ===== 5. TIMELINE / ACTIVITY ===== */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="p-6 border-b border-gray-100 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Activity className="w-5 h-5" />
            {t('diagnostic.timeline_section')}
          </h2>
        </div>
        <div className="p-6">
          {timelineEvents.length > 0 ? (
            <div className="relative">
              <div className="absolute left-[11px] top-3 bottom-3 w-0.5 bg-gray-200 dark:bg-slate-700" />
              <div className="space-y-4">
                {timelineEvents.map((evt, i) => (
                  <div key={i} className="relative flex gap-4">
                    <div className="relative z-10 flex-shrink-0 mt-1.5">
                      <div
                        className={cn(
                          'w-[10px] h-[10px] rounded-full ring-4 ring-white dark:ring-slate-800',
                          evt.type === 'sample'
                            ? 'bg-blue-500'
                            : evt.type === 'report'
                              ? 'bg-green-500'
                              : evt.type === 'inspection'
                                ? 'bg-purple-500'
                                : 'bg-gray-400',
                        )}
                        style={{ marginLeft: '6px' }}
                      />
                    </div>
                    <div className="flex-1 pb-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm font-medium text-gray-900 dark:text-white">{evt.label}</span>
                        {evt.detail && (
                          <span className="text-xs text-gray-500 dark:text-slate-400 bg-gray-100 dark:bg-slate-700 px-2 py-0.5 rounded">
                            {evt.detail}
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                        {formatDate(evt.date, 'dd.MM.yyyy HH:mm', locale)}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-6">
              <Activity className="w-8 h-8 text-gray-300 mx-auto mb-2" />
              <p className="text-sm text-gray-500 dark:text-slate-400">{t('diagnostic.noTimeline')}</p>
            </div>
          )}
        </div>
      </div>

      {/* ===== 6. UPLOAD & PARSE REPORT ===== */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{t('diagnostic.uploadReport')}</h2>

        {!parseResult ? (
          <>
            <FileUpload onUpload={onParseReport} accept=".pdf" />
            {isParsing && (
              <div className="mt-3 flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400">
                <Loader2 className="w-4 h-4 animate-spin" />
                {t('report.parsing')}
              </div>
            )}
            {d.report_file_path && (
              <div className="mt-3 flex items-center gap-2 text-sm text-green-700 dark:text-green-400">
                <CheckCircle2 className="w-4 h-4" />
                {t('diagnostic.reportUploaded')}
              </div>
            )}
          </>
        ) : (
          <div className="space-y-4">
            {/* Parse result header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
                <CheckCircle2 className="w-4 h-4" />
                {t('report.samples_found').replace('{count}', String(editedSamples.length))}
              </div>
              <button
                onClick={() => {
                  setParseResult(null);
                  setEditedSamples([]);
                }}
                className="text-sm text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200"
              >
                {t('form.cancel')}
              </button>
            </div>

            {/* Warnings */}
            {parseResult.warnings.length > 0 && (
              <div className="bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3">
                <p className="text-sm font-medium text-yellow-800 dark:text-yellow-300 mb-1">{t('report.warnings')}</p>
                <ul className="text-xs text-yellow-700 dark:text-yellow-400 space-y-0.5">
                  {parseResult.warnings.map((w, i) => (
                    <li key={i}>- {w}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Editable samples table */}
            {editedSamples.length > 0 ? (
              <div className="overflow-x-auto">
                <p className="text-xs text-gray-500 dark:text-slate-400 mb-2">{t('report.edit_before_apply')}</p>
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-slate-700">
                      <th className="text-left py-2 px-2 text-gray-500 dark:text-slate-400 font-medium">
                        {t('sample.number')}
                      </th>
                      <th className="text-left py-2 px-2 text-gray-500 dark:text-slate-400 font-medium">
                        {t('sample.location_detail')}
                      </th>
                      <th className="text-left py-2 px-2 text-gray-500 dark:text-slate-400 font-medium">
                        {t('sample.material_description')}
                      </th>
                      <th className="text-left py-2 px-2 text-gray-500 dark:text-slate-400 font-medium">
                        {t('sample.pollutant_type')}
                      </th>
                      <th className="text-left py-2 px-2 text-gray-500 dark:text-slate-400 font-medium">
                        {t('sample.concentration')}
                      </th>
                      <th className="text-left py-2 px-2 text-gray-500 dark:text-slate-400 font-medium">
                        {t('sample.unit')}
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {editedSamples.map((s, i) => (
                      <tr key={i} className="border-b border-gray-100 dark:border-slate-700/50">
                        <td className="py-1.5 px-2 text-gray-900 dark:text-white">{s.sample_number || '-'}</td>
                        <td className="py-1.5 px-2 text-gray-900 dark:text-white">{s.location || '-'}</td>
                        <td className="py-1.5 px-2 text-gray-900 dark:text-white">{s.material || '-'}</td>
                        <td className="py-1.5 px-2">
                          {s.pollutant_type ? <PollutantBadge type={s.pollutant_type as PollutantType} /> : '-'}
                        </td>
                        <td className="py-1.5 px-2 font-mono text-gray-900 dark:text-white">
                          {s.concentration ?? '-'}
                        </td>
                        <td className="py-1.5 px-2 text-gray-900 dark:text-white">{s.unit || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-slate-400">{t('report.no_samples')}</p>
            )}

            {/* Apply button */}
            <div className="flex justify-end">
              <button
                onClick={onApplyReport}
                disabled={isApplying || editedSamples.length === 0}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
              >
                {isApplying && <Loader2 className="w-4 h-4 animate-spin" />}
                {isApplying ? t('report.applying') : t('report.confirm_apply')}
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Add Sample Modal */}
      {showSampleModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('sample.add')}</h2>
              <button
                onClick={() => {
                  setShowSampleModal(false);
                  reset();
                }}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-700 rounded-lg"
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>
            <form onSubmit={handleSubmit(onSampleSubmit)} className="space-y-4">
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
                    {t('sample.pollutant_type')} *
                  </label>
                  <select
                    {...register('pollutant_type')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    <option value="">{t('diagnostic.selectPollutant')}</option>
                    {['asbestos', 'pcb', 'lead', 'hap', 'radon'].map((p) => (
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
                    {t('sample.pollutant_subtype')}
                  </label>
                  <input
                    {...register('pollutant_subtype')}
                    placeholder="e.g. Chrysotile, Amosite"
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
              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                <button
                  type="button"
                  onClick={() => {
                    setShowSampleModal(false);
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

      {/* Cost Estimation Modal */}
      <CostEstimationModal
        open={showCostModal}
        onClose={() => setShowCostModal(false)}
        defaultPollutant={d.diagnostic_type !== 'full' ? d.diagnostic_type : undefined}
      />
    </div>
  );
}
