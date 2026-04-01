import { Component, useState, useEffect, lazy, Suspense } from 'react';
import type { ReactNode, ErrorInfo } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { useQuery } from '@tanstack/react-query';
import { useBuilding, useUpdateBuilding, useDeleteBuilding } from '@/hooks/useBuildings';
import { useDiagnostics, useCreateDiagnostic, useBuildingRisk } from '@/hooks/useDiagnostics';
import { useAuth } from '@/hooks/useAuth';
import { useTranslation } from '@/i18n';
import { formatDate, cn } from '@/utils/formatters';
import { SWISS_CANTONS, BUILDING_TYPES } from '@/utils/constants';
import { documentsApi } from '@/api/documents';
import { buildingsApi } from '@/api/buildings';
import { actionsApi } from '@/api/actions';
import { buildingDashboardApi } from '@/api/buildingDashboard';
import type { BuildingDashboard } from '@/api/buildingDashboard';
import { toast } from '@/store/toastStore';
import { BuildingDetailSkeleton } from '@/components/Skeleton';
import { RoleGate } from '@/components/RoleGate';
import type { Diagnostic, PollutantType, BuildingRiskScore, Document as DocType, ActionItem } from '@/types';
import type { FieldError } from 'react-hook-form';
import { ArrowLeft, Edit3, Trash2, Loader2, MapPin, Calendar, Building2, X, AlertTriangle } from 'lucide-react';
import { InvalidationBadge } from '@/components/InvalidationAlerts';
import { BuildingAlertBadge } from '@/components/BuildingAlertBadge';

const LazyOverviewTab = lazy(() => import('@/components/building-detail/OverviewTab'));
const LazyActivityTab = lazy(() => import('@/components/building-detail/ActivityTab'));
const LazyDiagnosticsTab = lazy(() => import('@/components/building-detail/DiagnosticsTab'));
const LazyDocumentsTab = lazy(() => import('@/components/building-detail/DocumentsTab'));
const LazyLeasesTab = lazy(() => import('@/components/building-detail/LeasesTab'));
const LazyContractsTab = lazy(() => import('@/components/building-detail/ContractsTab'));
const LazyOwnershipTab = lazy(() => import('@/components/building-detail/OwnershipTab'));
const LazyProceduresSection = lazy(() => import('@/components/building-detail/ProceduresSection'));
const LazyTenderTab = lazy(() => import('@/components/building-detail/TenderTab'));
const LazyBuildingLifeTab = lazy(() => import('@/components/building-detail/BuildingLifeTab'));
const LazyUnknownsLedger = lazy(() => import('@/components/building-detail/UnknownsLedger'));
const LazyTransferPackagePanel = lazy(() =>
  import('@/components/TransferPackagePanel').then((m) => ({ default: m.TransferPackagePanel })),
);
const LazyPassportDiffView = lazy(() => import('@/components/building-detail/PassportDiffView'));
const LazyBuildingExplorerEmbed = lazy(() => import('@/pages/BuildingExplorer'));
const LazyBuildingPlansEmbed = lazy(() => import('@/pages/BuildingPlans'));
const LazyBuildingInterventionsEmbed = lazy(() => import('@/pages/BuildingInterventions'));
const LazyIntelligencePanel = lazy(() =>
  import('@/components/IntelligencePanel').then((m) => ({ default: m.IntelligencePanel })),
);
const LazyRecommendationList = lazy(() =>
  import('@/components/RecommendationList').then((m) => ({ default: m.RecommendationList })),
);
const LazyFieldMemoryPanel = lazy(() =>
  import('@/components/FieldMemoryPanel').then((m) => ({ default: m.FieldMemoryPanel })),
);
const LazyDocumentChecklist = lazy(() => import('@/components/DocumentChecklist'));
const LazyActivityLedger = lazy(() =>
  import('@/components/ActivityLedger').then((m) => ({ default: m.ActivityLedger })),
);
const LazyCertificateGenerator = lazy(() =>
  import('@/components/CertificateGenerator').then((m) => ({ default: m.CertificateGenerator })),
);
const LazyProofOfStateExport = lazy(() =>
  import('@/components/ProofOfStateExport').then((m) => ({ default: m.ProofOfStateExport })),
);

// ErrorBoundary to catch crashes in individual tab content
interface TabErrorBoundaryProps {
  children: ReactNode;
  tabKey: string;
}

interface TabErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class TabErrorBoundary extends Component<TabErrorBoundaryProps, TabErrorBoundaryState> {
  constructor(props: TabErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): TabErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error(`[TabErrorBoundary] Tab "${this.props.tabKey}" crashed:`, error, info.componentStack);
  }

  componentDidUpdate(prevProps: TabErrorBoundaryProps) {
    // Reset error state when switching tabs
    if (prevProps.tabKey !== this.props.tabKey && this.state.hasError) {
      this.setState({ hasError: false, error: null });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-red-700 dark:text-red-300 mb-2">
            Something went wrong in this tab
          </h3>
          <p className="text-sm text-red-600 dark:text-red-400 mb-4">
            {this.state.error?.message || 'An unexpected error occurred'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
          >
            Try again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

const editSchema = z.object({
  address: z.string().min(1),
  city: z.string().min(1),
  canton: z.string().min(1),
  postal_code: z.string().min(4),
  construction_year: z.coerce.number().min(1800).max(new Date().getFullYear()),
  building_type: z.string().min(1),
  floors_above: z.coerce.number().optional(),
  surface_area_m2: z.coerce.number().optional(),
  egrid: z.string().optional(),
});

type EditFormData = z.infer<typeof editSchema>;

type TabKey = 'overview' | 'spatial' | 'truth' | 'change' | 'cases' | 'passport' | 'intelligence' | 'questions';

/** Map legacy tab keys (used by onNavigateTab callbacks) to new doctrinal keys */
const LEGACY_TAB_MAP: Record<string, TabKey> = {
  overview: 'overview',
  activity: 'change',
  diagnostics: 'truth',
  documents: 'truth',
  ownership: 'truth',
  leases: 'cases',
  contracts: 'cases',
  procedures: 'cases',
  tenders: 'cases',
  'building-life': 'overview',
  details: 'overview',
  spatial: 'spatial',
  truth: 'truth',
  change: 'change',
  cases: 'cases',
  passport: 'passport',
  intelligence: 'intelligence',
  questions: 'questions',
};

const TabFallback = (
  <div className="flex items-center justify-center py-12">
    <Loader2 className="w-8 h-8 animate-spin text-red-600" />
  </div>
);

/** Envelope version diff selector — embedded in the passport tab */
function PassportDiffSection({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();
  const [selectedA, setSelectedA] = useState('');
  const [selectedB, setSelectedB] = useState('');
  const [showDiff, setShowDiff] = useState(false);

  const { data: history } = useQuery({
    queryKey: ['passport-envelope-history', buildingId],
    queryFn: async () => {
      const { apiClient } = await import('@/api/client');
      const res = await apiClient.get<{
        items: Array<{ id: string; version: number; version_label: string | null; status: string; created_at: string }>;
        count: number;
      }>(`/buildings/${buildingId}/passport-envelope/history`);
      return res.data;
    },
  });

  const items = history?.items ?? [];

  if (items.length < 2) return null;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5">
      <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
        {t('passport_diff.compare_versions') || 'Compare Passport Versions'}
      </h3>
      <div className="flex flex-col sm:flex-row items-start sm:items-end gap-3">
        <div className="flex-1 w-full">
          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1">
            {t('passport_diff.version_a') || 'Version A (older)'}
          </label>
          <select
            value={selectedA}
            onChange={(e) => {
              setSelectedA(e.target.value);
              setShowDiff(false);
            }}
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 dark:text-white"
          >
            <option value="">{t('passport_diff.select') || 'Select...'}</option>
            {items.map((env) => (
              <option key={env.id} value={env.id}>
                v{env.version} - {env.status}
                {env.version_label ? ` (${env.version_label})` : ''}
              </option>
            ))}
          </select>
        </div>
        <div className="flex-1 w-full">
          <label className="block text-xs text-gray-500 dark:text-slate-400 mb-1">
            {t('passport_diff.version_b') || 'Version B (newer)'}
          </label>
          <select
            value={selectedB}
            onChange={(e) => {
              setSelectedB(e.target.value);
              setShowDiff(false);
            }}
            className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 dark:text-white"
          >
            <option value="">{t('passport_diff.select') || 'Select...'}</option>
            {items.map((env) => (
              <option key={env.id} value={env.id}>
                v{env.version} - {env.status}
                {env.version_label ? ` (${env.version_label})` : ''}
              </option>
            ))}
          </select>
        </div>
        <button
          disabled={!selectedA || !selectedB || selectedA === selectedB}
          onClick={() => setShowDiff(true)}
          className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-40 disabled:cursor-not-allowed shrink-0"
        >
          {t('passport_diff.compare') || 'Compare'}
        </button>
      </div>
      {showDiff && selectedA && selectedB && selectedA !== selectedB && (
        <div className="mt-4">
          <Suspense fallback={TabFallback}>
            <LazyPassportDiffView envelopeIdA={selectedA} envelopeIdB={selectedB} onClose={() => setShowDiff(false)} />
          </Suspense>
        </div>
      )}
    </div>
  );
}

export default function BuildingDetail() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  useAuth();

  const { data: building, isLoading, isError } = useBuilding(id!);
  const { data: diagnosticsData } = useDiagnostics(id!);
  const { data: riskData } = useBuildingRisk(id!);
  const updateBuilding = useUpdateBuilding();
  const deleteBuilding = useDeleteBuilding();
  const createDiagnostic = useCreateDiagnostic();

  const diagnostics: Diagnostic[] = Array.isArray(diagnosticsData) ? diagnosticsData : [];

  const [activeTab, setActiveTab] = useState<TabKey>('overview');
  const [showEditModal, setShowEditModal] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);
  const [showDiagnosticForm, setShowDiagnosticForm] = useState(false);
  const [documents, setDocuments] = useState<DocType[]>([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [documentsError, setDocumentsError] = useState(false);

  // Fetch documents for this building
  useEffect(() => {
    if (!id) return;
    documentsApi
      .listByBuilding(id)
      .then((data) => {
        setDocumentsError(false);
        setDocuments(Array.isArray(data) ? data : []);
      })
      .catch(() => {
        setDocumentsError(true);
        setDocuments([]);
        toast(t('app.error'));
      })
      .finally(() => setIsLoadingDocs(false));
  }, [id, t]);

  // Activity query — only fetched when activity tab is active
  const {
    data: activity = [],
    isLoading: activityLoading,
    isError: activityError,
  } = useQuery({
    queryKey: ['building-activity', id],
    queryFn: () => buildingsApi.getActivity(id!),
    enabled: !!id && activeTab === 'change',
    retry: false,
  });

  // Actions query — fetched for overview tab open actions count
  const { data: actions = [], isError: actionsError } = useQuery({
    queryKey: ['building-actions', id],
    queryFn: () => actionsApi.listByBuilding(id!),
    enabled: !!id,
    retry: false,
  });

  // Dashboard aggregate query — used on overview tab to reduce API calls
  const { data: dashboard } = useQuery<BuildingDashboard>({
    queryKey: ['building-dashboard', id],
    queryFn: () => buildingDashboardApi.get(id!),
    enabled: !!id,
    retry: false,
    staleTime: 60_000,
  });

  const openActions = actions.filter((a: ActionItem) => a.status === 'open' || a.status === 'in_progress');

  const tabs: { key: TabKey; label: string; count?: number }[] = [
    { key: 'overview', label: t('building.tab.overview') },
    { key: 'spatial', label: t('building.tab.spatial') || 'Spatial' },
    { key: 'truth', label: t('building.tab.truth') || 'Verite' },
    { key: 'change', label: t('building.tab.change') || 'Changements' },
    { key: 'cases', label: t('building.tab.cases') || 'Dossiers' },
    { key: 'passport', label: t('building.tab.passport') || 'Passeport & Transfert' },
    { key: 'intelligence', label: t('building.tab.intelligence') || 'Intelligence' },
    { key: 'questions', label: t('building.tab.questions') || 'Questions' },
  ];

  const {
    register: editRegister,
    handleSubmit: editHandleSubmit,
    formState: { errors: editErrors },
  } = useForm<EditFormData>({
    resolver: zodResolver(editSchema),
    values: building as EditFormData,
  });

  const onEditSubmit = async (data: EditFormData) => {
    try {
      await updateBuilding.mutateAsync({ id: id!, data });
      setShowEditModal(false);
    } catch {}
  };

  const onDelete = async () => {
    try {
      await deleteBuilding.mutateAsync(id!);
      navigate('/buildings');
    } catch {}
  };

  const onCreateDiagnostic = async (formData: Partial<Diagnostic>) => {
    try {
      await createDiagnostic.mutateAsync({ buildingId: id!, data: formData });
      setShowDiagnosticForm(false);
    } catch {}
  };

  const handleDocumentUpload = async (file: File) => {
    try {
      await documentsApi.upload(id!, file);
      const data = await documentsApi.listByBuilding(id!);
      setDocuments(Array.isArray(data) ? data : []);
    } catch (err: any) {
      toast(err?.response?.data?.detail || err?.message || 'Upload failed');
    }
  };

  if (isLoading) {
    return <BuildingDetailSkeleton />;
  }

  if (isError || !building) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('building.notFound')}</p>
        <Link to="/buildings" className="text-sm text-red-600 dark:text-red-400 hover:underline mt-2 inline-block">
          {t('building.backToList')}
        </Link>
      </div>
    );
  }

  const risk = riskData as BuildingRiskScore | undefined;
  const pollutantProbabilities: Partial<Record<PollutantType, number>> = risk
    ? {
        asbestos: risk.asbestos_probability,
        pcb: risk.pcb_probability,
        lead: risk.lead_probability,
        hap: risk.hap_probability,
        radon: risk.radon_probability,
      }
    : {};

  // Completeness checklist
  const hasDiagnostic = diagnostics.length > 0;
  const hasValidatedDiagnostic = diagnostics.some((d) => d.status === 'validated');
  const hasDocuments = documents.length > 0;
  const hasRiskScore = !!risk;
  const completenessItems = [
    { key: 'diagnostic', done: hasDiagnostic },
    { key: 'validated_diagnostic', done: hasValidatedDiagnostic },
    { key: 'documents', done: hasDocuments },
    { key: 'risk_score', done: hasRiskScore },
  ];
  const completenessCount = completenessItems.filter((c) => c.done).length;
  const completenessTotal = completenessItems.length;
  const completenessPct = Math.round((completenessCount / completenessTotal) * 100);

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        to="/buildings"
        className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
      >
        <ArrowLeft className="w-4 h-4" />
        {t('building.backToList')}
      </Link>

      {/* Header */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <div className="flex flex-col lg:flex-row lg:items-start lg:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{building.address}</h1>
              <span className="px-2 py-0.5 text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 rounded-full">
                {building.canton}
              </span>
              <InvalidationBadge buildingId={id} />
              <BuildingAlertBadge buildingId={id!} />
            </div>
            <div className="flex flex-wrap items-center gap-4 text-sm text-gray-500 dark:text-slate-400">
              <span className="flex items-center gap-1">
                <MapPin className="w-4 h-4" />
                {building.postal_code} {building.city}
              </span>
              <span className="flex items-center gap-1">
                <Calendar className="w-4 h-4" />
                {building.construction_year}
              </span>
              <span className="flex items-center gap-1">
                <Building2 className="w-4 h-4" />
                {t(`building_type.${building.building_type}`) || building.building_type}
              </span>
            </div>
          </div>
          <RoleGate allowedRoles={['admin']}>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setShowEditModal(true)}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                <Edit3 className="w-4 h-4" />
                {t('form.edit')}
              </button>
              <button
                onClick={() => setShowDeleteConfirm(true)}
                className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-red-700 dark:text-red-400 bg-white dark:bg-slate-800 border border-red-300 dark:border-red-700 rounded-lg hover:bg-red-50 dark:hover:bg-red-900/30"
              >
                <Trash2 className="w-4 h-4" />
                {t('form.delete')}
              </button>
            </div>
          </RoleGate>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
        <div className="border-b border-gray-200 dark:border-slate-700">
          <nav className="flex -mb-px overflow-x-auto" role="tablist" aria-label={t('building.tab.overview')}>
            {tabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                role="tab"
                aria-selected={activeTab === tab.key}
                data-testid={`building-tab-${tab.key}`}
                className={cn(
                  'flex items-center gap-2 px-6 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                  activeTab === tab.key
                    ? 'border-red-600 text-red-600'
                    : 'border-transparent text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 hover:border-gray-300 dark:hover:border-slate-600',
                )}
              >
                {tab.label}
                {tab.count != null && (
                  <span
                    className={cn(
                      'ml-1 px-1.5 py-0.5 text-xs font-medium rounded-full',
                      activeTab === tab.key
                        ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                        : 'bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400',
                    )}
                  >
                    {tab.count}
                  </span>
                )}
              </button>
            ))}
          </nav>
        </div>

        <div className="p-6">
          <TabErrorBoundary tabKey={activeTab}>
            {/* Vue d'ensemble — daily operating surface */}
            {activeTab === 'overview' && (
              <Suspense fallback={TabFallback}>
                <LazyOverviewTab
                  buildingId={id!}
                  building={building}
                  diagnostics={diagnostics}
                  risk={risk}
                  pollutantProbabilities={pollutantProbabilities}
                  dashboard={dashboard}
                  actions={actions}
                  openActions={openActions}
                  actionsError={actionsError}
                  completenessItems={completenessItems}
                  completenessCount={completenessCount}
                  completenessTotal={completenessTotal}
                  completenessPct={completenessPct}
                  onNavigateTab={(tab: string) => setActiveTab(LEGACY_TAB_MAP[tab] ?? 'overview')}
                />
                {/* Building Life summary */}
                <div className="mt-6">
                  <Suspense fallback={TabFallback}>
                    <LazyBuildingLifeTab buildingId={id!} />
                  </Suspense>
                </div>
                {/* Building details grid (absorbed from old Details tab) */}
                <div className="mt-6">
                  <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                    {t('building.tab.details')}
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    {[
                      { label: t('building.address'), value: building.address },
                      { label: t('building.city'), value: `${building.postal_code} ${building.city}` },
                      { label: t('building.canton'), value: building.canton },
                      { label: t('building.construction_year'), value: building.construction_year },
                      { label: t('building.renovation_year'), value: building.renovation_year || '-' },
                      {
                        label: t('building.building_type'),
                        value: t(`building_type.${building.building_type}`) || building.building_type,
                      },
                      { label: t('building.floors_above'), value: building.floors_above ?? '-' },
                      { label: t('building.floors_below'), value: building.floors_below ?? '-' },
                      {
                        label: t('building.surface_area'),
                        value: building.surface_area_m2 ? `${building.surface_area_m2} m\u00B2` : '-',
                      },
                      {
                        label: t('building.volume'),
                        value: building.volume_m3 ? `${building.volume_m3} m\u00B3` : '-',
                      },
                      { label: t('building.egrid'), value: building.egrid || '-' },
                      { label: t('building.official_id'), value: building.official_id || '-' },
                      { label: t('building.parcel_number'), value: building.parcel_number || '-' },
                      {
                        label: t('building.latitude'),
                        value: building.latitude != null ? String(building.latitude) : '-',
                      },
                      {
                        label: t('building.longitude'),
                        value: building.longitude != null ? String(building.longitude) : '-',
                      },
                      {
                        label: t('building.last_diagnostic'),
                        value: diagnostics.length > 0 ? formatDate(diagnostics[0].date_inspection) : '-',
                      },
                      { label: t('form.created_at') || 'Created', value: formatDate(building.created_at) },
                      { label: t('form.updated_at') || 'Updated', value: formatDate(building.updated_at) },
                    ].map((item) => (
                      <div key={item.label} className="bg-gray-50 dark:bg-slate-700 rounded-lg p-3">
                        <p className="text-xs text-gray-500 dark:text-slate-400">{item.label}</p>
                        <p className="text-sm font-medium text-gray-900 dark:text-white mt-0.5">{item.value || '-'}</p>
                      </div>
                    ))}
                  </div>
                </div>
              </Suspense>
            )}

            {/* Spatial — zone/element explorer + plans */}
            {activeTab === 'spatial' && (
              <Suspense fallback={TabFallback}>
                <div className="space-y-8">
                  <LazyBuildingExplorerEmbed />
                  <div className="border-t border-gray-200 dark:border-slate-700 pt-6">
                    <LazyBuildingPlansEmbed />
                  </div>
                </div>
              </Suspense>
            )}

            {/* Verite — what is true: diagnostics, documents, ownership */}
            {activeTab === 'truth' && (
              <Suspense fallback={TabFallback}>
                <div className="space-y-8">
                  <section>
                    <Suspense fallback={null}>
                      <LazyDocumentChecklist buildingId={id!} />
                    </Suspense>
                  </section>
                  <section>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      {t('building.tab.diagnostics')}
                    </h3>
                    <LazyDiagnosticsTab
                      buildingId={id!}
                      diagnostics={diagnostics}
                      onCreateClick={() => setShowDiagnosticForm(true)}
                    />
                  </section>
                  <section className="border-t border-gray-200 dark:border-slate-700 pt-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      {t('building.tab.documents')}
                    </h3>
                    <LazyDocumentsTab
                      documents={documents}
                      isLoadingDocs={isLoadingDocs}
                      documentsError={documentsError}
                      buildingId={id!}
                      onUpload={handleDocumentUpload}
                    />
                  </section>
                  <section className="border-t border-gray-200 dark:border-slate-700 pt-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      {t('building.tab.ownership') || 'Ownership'}
                    </h3>
                    <LazyOwnershipTab buildingId={id!} />
                  </section>
                  <section className="border-t border-gray-200 dark:border-slate-700 pt-6">
                    <LazyUnknownsLedger buildingId={id!} />
                  </section>
                </div>
              </Suspense>
            )}

            {/* Changements — what changed: timeline, activity */}
            {activeTab === 'change' && (
              <Suspense fallback={TabFallback}>
                <LazyActivityTab
                  buildingId={id!}
                  activity={activity}
                  activityLoading={activityLoading}
                  activityError={activityError}
                />
                <div className="mt-6">
                  <Suspense fallback={null}>
                    <LazyActivityLedger buildingId={id!} />
                  </Suspense>
                </div>
              </Suspense>
            )}

            {/* Dossiers — active episodes: cases, interventions, tenders, leases, contracts, procedures */}
            {activeTab === 'cases' && (
              <Suspense fallback={TabFallback}>
                <div className="space-y-8">
                  <section>
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      {t('building.tab.leases') || 'Leases'}
                    </h3>
                    <LazyLeasesTab buildingId={id!} />
                  </section>
                  <section className="border-t border-gray-200 dark:border-slate-700 pt-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      {t('building.tab.contracts') || 'Contracts'}
                    </h3>
                    <LazyContractsTab buildingId={id!} />
                  </section>
                  <section className="border-t border-gray-200 dark:border-slate-700 pt-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      {t('building.tab.procedures') || 'Procedures'}
                    </h3>
                    <LazyProceduresSection buildingId={id!} />
                  </section>
                  <section className="border-t border-gray-200 dark:border-slate-700 pt-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      {t('building.tab.tenders') || "Appels d'offres"}
                    </h3>
                    <LazyTenderTab buildingId={id!} />
                  </section>
                  <section className="border-t border-gray-200 dark:border-slate-700 pt-6">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
                      {t('building.tab.interventions') || 'Interventions'}
                    </h3>
                    <LazyBuildingInterventionsEmbed />
                  </section>
                </div>
              </Suspense>
            )}

            {/* Passeport & Transfert — passport envelope, transfer receipts, version diff */}
            {activeTab === 'passport' && (
              <div className="space-y-6">
                <Suspense fallback={TabFallback}>
                  <LazyTransferPackagePanel buildingId={id!} />
                </Suspense>
                <Suspense fallback={TabFallback}>
                  <PassportDiffSection buildingId={id!} />
                </Suspense>
                <Suspense fallback={null}>
                  <LazyCertificateGenerator buildingId={id!} />
                </Suspense>
                <Suspense fallback={null}>
                  <LazyProofOfStateExport buildingId={id!} />
                </Suspense>
              </div>
            )}

            {/* Intelligence — AI recommendations, field memory, insights */}
            {activeTab === 'intelligence' && (
              <Suspense fallback={TabFallback}>
                <div className="space-y-6">
                  <LazyIntelligencePanel buildingId={id!} />
                  <LazyRecommendationList buildingId={id!} />
                  <LazyFieldMemoryPanel buildingId={id!} />
                </div>
              </Suspense>
            )}

            {/* Questions — readiness, intent queries, SafeToX verdicts */}
            {activeTab === 'questions' && (
              <div className="space-y-4">
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  {t('building.tab.questions_description') ||
                    'Readiness verdicts, intent queries and SafeToX evaluations for this building.'}
                </p>
                <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-6 text-center">
                  <p className="text-gray-500 dark:text-slate-400 text-sm">
                    {t('building.tab.questions_coming_soon') || 'Full readiness workspace coming soon.'}
                  </p>
                </div>
              </div>
            )}
          </TabErrorBoundary>
        </div>
      </div>

      {/* Edit Modal */}
      {showEditModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('building.edit')}</h2>
              <button
                onClick={() => setShowEditModal(false)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                aria-label={t('form.close')}
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>
            <form onSubmit={editHandleSubmit(onEditSubmit)} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('building.address')}
                  </label>
                  <input
                    {...editRegister('address')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                  {editErrors.address && <p className="text-xs text-red-600 mt-1">{editErrors.address.message}</p>}
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('building.city')}
                  </label>
                  <input
                    {...editRegister('city')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('building.postal_code')}
                  </label>
                  <input
                    {...editRegister('postal_code')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('building.canton')}
                  </label>
                  <select
                    {...editRegister('canton')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 dark:text-white"
                  >
                    {SWISS_CANTONS.map((c) => (
                      <option key={c} value={c}>
                        {t(`canton.${c}`) || c}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('building.construction_year')}
                  </label>
                  <input
                    type="number"
                    {...editRegister('construction_year')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('building.building_type')}
                  </label>
                  <select
                    {...editRegister('building_type')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 dark:text-white"
                  >
                    {BUILDING_TYPES.map((bt) => (
                      <option key={bt} value={bt}>
                        {t(`building_type.${bt}`) || bt}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('building.floors_above')}
                  </label>
                  <input
                    type="number"
                    {...editRegister('floors_above')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('building.surface_area')}
                  </label>
                  <input
                    type="number"
                    {...editRegister('surface_area_m2')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('building.egrid')}
                  </label>
                  <input
                    {...editRegister('egrid')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
              </div>
              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                <button
                  type="button"
                  onClick={() => setShowEditModal(false)}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
                >
                  {t('form.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={updateBuilding.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
                >
                  {updateBuilding.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  {t('form.save')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {showDeleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-6 text-center">
            <AlertTriangle className="w-12 h-12 text-red-500 mx-auto mb-3" />
            <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">{t('building.deleteTitle')}</h3>
            <p className="text-sm text-gray-500 dark:text-slate-400 mb-6">{t('building.deleteConfirm')}</p>
            <div className="flex justify-center gap-3">
              <button
                onClick={() => setShowDeleteConfirm(false)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                {t('form.cancel')}
              </button>
              <button
                onClick={onDelete}
                disabled={deleteBuilding.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
              >
                {deleteBuilding.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                {t('form.delete')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Diagnostic Form */}
      {showDiagnosticForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div
            data-testid="building-diagnostic-modal"
            className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md mx-4 p-6"
          >
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('diagnostic.create')}</h2>
              <button
                onClick={() => setShowDiagnosticForm(false)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                aria-label={t('form.close')}
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>
            <DiagnosticCreateForm
              onSubmit={onCreateDiagnostic}
              isPending={createDiagnostic.isPending}
              onCancel={() => setShowDiagnosticForm(false)}
            />
          </div>
        </div>
      )}
    </div>
  );
}

// Sub-component for diagnostic creation
function DiagnosticCreateForm({
  onSubmit,
  isPending,
  onCancel,
}: {
  onSubmit: (data: Partial<Diagnostic>) => void;
  isPending: boolean;
  onCancel: () => void;
}) {
  const { t } = useTranslation();
  const schema = z.object({
    diagnostic_type: z.string().min(1),
    diagnostic_context: z.string().min(1),
    date_inspection: z.string().min(1),
    methodology: z.string().optional(),
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm({
    resolver: zodResolver(schema),
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
          {t('diagnostic.diagnosticType')} *
        </label>
        <select
          {...register('diagnostic_type')}
          data-testid="building-diagnostic-type"
          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <option value="">{t('diagnostic.selectType')}</option>
          {['asbestos', 'pcb', 'lead', 'hap', 'radon'].map((p) => (
            <option key={p} value={p}>
              {t(`pollutant.${p}`)}
            </option>
          ))}
        </select>
        {errors.diagnostic_type && (
          <p className="text-xs text-red-600 mt-1">{(errors.diagnostic_type as FieldError)?.message}</p>
        )}
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
          {t('diagnostic.diagnosticContext')} *
        </label>
        <select
          {...register('diagnostic_context')}
          defaultValue="AvT"
          data-testid="building-diagnostic-context"
          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <option value="UN">{t('diagnostic.context_UN')}</option>
          <option value="AvT">{t('diagnostic.context_AvT')}</option>
          <option value="ApT">{t('diagnostic.context_ApT')}</option>
        </select>
        {errors.diagnostic_context && (
          <p className="text-xs text-red-600 mt-1">{(errors.diagnostic_context as FieldError)?.message}</p>
        )}
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
          {t('diagnostic.dateInspection')} *
        </label>
        <input
          type="date"
          {...register('date_inspection')}
          data-testid="building-diagnostic-date"
          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
        />
        {errors.date_inspection && (
          <p className="text-xs text-red-600 mt-1">{(errors.date_inspection as FieldError)?.message}</p>
        )}
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
          {t('diagnostic.methodology')}
        </label>
        <input
          {...register('methodology')}
          data-testid="building-diagnostic-methodology"
          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
        />
      </div>
      <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
        <button
          type="button"
          onClick={onCancel}
          className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
        >
          {t('form.cancel')}
        </button>
        <button
          type="submit"
          disabled={isPending}
          data-testid="building-diagnostic-submit"
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
        >
          {isPending && <Loader2 className="w-4 h-4 animate-spin" />}
          {t('form.create')}
        </button>
      </div>
    </form>
  );
}
