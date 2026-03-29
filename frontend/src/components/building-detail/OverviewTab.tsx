import { lazy, Suspense, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { RiskGauge } from '@/components/RiskGauge';
import { PollutantBadge } from '@/components/PollutantBadge';
import { NextAction } from '@/components/NextAction';
import { DataQualityScore } from '@/components/DataQualityScore';
import { DossierStatusPanel } from '@/components/DossierStatusPanel';
import { ReadinessSummary } from '@/components/ReadinessSummary';
import { TrustScoreCard } from '@/components/TrustScoreCard';
import { UnknownIssuesList } from '@/components/UnknownIssuesList';
import { ChangeSignalsFeed } from '@/components/ChangeSignalsFeed';
import { ContradictionCard } from '@/components/ContradictionCard';
import { PostWorksDiffCard } from '@/components/PostWorksDiffCard';
import { ROICard } from '@/components/building-detail/ROICard';
import { TimeMachinePanel } from '@/components/TimeMachinePanel';
import { PassportCard } from '@/components/PassportCard';
import { SharedLinksPanel } from '@/components/SharedLinksPanel';
import { PreworkDiagnosticTriggerCard } from '@/components/PreworkDiagnosticTriggerCard';
import { PredictiveAlertsBuilding } from '@/components/PredictiveAlerts';
import InstantCardView from '@/components/building-detail/InstantCardView';
import { DossierJourney } from '@/components/building-detail/DossierJourney';
import { ActionQueue } from '@/components/building-detail/ActionQueue';
import { PilotScorecardPanel } from '@/components/building-detail/PilotScorecardPanel';

// Below-the-fold intelligence views — lazy-loaded to reduce OverviewTab chunk
const LazyFormsWorkspace = lazy(() => import('@/components/building-detail/FormsWorkspace'));
const EvidenceByRoleView = lazy(() => import('@/components/building-detail/EvidenceByRoleView'));
const IndispensabilityView = lazy(() => import('@/components/building-detail/IndispensabilityView'));
const EcosystemEngagementsView = lazy(() => import('@/components/building-detail/EcosystemEngagementsView'));
const OperationalGatesView = lazy(() => import('@/components/building-detail/OperationalGatesView'));
const MemoryTransferView = lazy(() => import('@/components/building-detail/MemoryTransferView'));
const AuthorityPackPanel = lazy(() => import('@/components/building-detail/AuthorityPackPanel'));
const RenovationReadinessPanel = lazy(() => import('@/components/building-detail/RenovationReadinessPanel'));
const PackBuilderPanel = lazy(() => import('@/components/building-detail/PackBuilderPanel'));
const ProjectWizard = lazy(() => import('@/components/building-detail/ProjectWizard'));
const DossierWorkflowPanel = lazy(() => import('@/components/building-detail/DossierWorkflowPanel'));
const TransactionReadinessPanel = lazy(() => import('@/components/building-detail/TransactionReadinessPanel'));
const InsuranceReadinessPanel = lazy(() => import('@/components/building-detail/InsuranceReadinessPanel'));
import WorkspaceMembersCard from '@/components/building-detail/WorkspaceMembersCard';
import DocumentInboxCard from '@/components/building-detail/DocumentInboxCard';
import ObligationsCard from '@/components/building-detail/ObligationsCard';
import ProofDeliveryHistory from '@/components/building-detail/ProofDeliveryHistory';
import SwissRulesWatchPanel from '@/components/building-detail/SwissRulesWatchPanel';

const LazyGeoContextPanel = lazy(() => import('@/components/building-detail/GeoContextPanel'));
const LazySpatialEnrichmentCard = lazy(() => import('@/components/building-detail/SpatialEnrichmentCard'));
const LazyIdentityChainPanel = lazy(() => import('@/components/building-detail/IdentityChainPanel'));
import ExchangeHistoryPanel from '@/components/building-detail/ExchangeHistoryPanel';
import { PackagePresetPreview } from '@/components/building-detail/PackagePresetPreview';
import { PublicOwnerModePanel } from '@/components/building-detail/PublicOwnerModePanel';
import { ReviewPackCard } from '@/components/building-detail/ReviewPackCard';
import { CommitteePackCard } from '@/components/building-detail/CommitteePackCard';
import { AudiencePackPreview } from '@/components/building-detail/AudiencePackPreview';
import { ArchivePosture } from '@/components/building-detail/ArchivePosture';
import { CustodyChainPanel } from '@/components/building-detail/CustodyChainPanel';
import { useAuthStore } from '@/store/authStore';
import { intelligenceApi } from '@/api/intelligence';
import type { BuildingDashboard } from '@/api/buildingDashboard';
import type { Building, Diagnostic, PollutantType, BuildingRiskScore, ActionItem } from '@/types';
import {
  AlertTriangle,
  ClipboardList,
  BarChart3,
  CheckCircle2,
  Circle,
  Layers,
  Wrench,
  FileImage,
  Clock,
  ShieldCheck,
  Beaker,
  ChevronRight,
  X,
  Stethoscope,
  FileUp,
  Gauge,
  Hammer,
} from 'lucide-react';
import { formatDate } from '@/utils/formatters';

interface OverviewTabProps {
  buildingId: string;
  building: Building;
  diagnostics: Diagnostic[];
  risk: BuildingRiskScore | undefined;
  pollutantProbabilities: Partial<Record<PollutantType, number>>;
  dashboard: BuildingDashboard | undefined;
  actions: ActionItem[];
  openActions: ActionItem[];
  actionsError: boolean;
  completenessItems: { key: string; done: boolean }[];
  completenessCount: number;
  completenessTotal: number;
  completenessPct: number;
  onNavigateTab?: (tab: string) => void;
}

export function OverviewTab({
  buildingId,
  building,
  diagnostics,
  risk,
  pollutantProbabilities,
  dashboard,
  actions,
  openActions,
  actionsError,
  completenessItems,
  completenessCount,
  completenessTotal,
  completenessPct,
  onNavigateTab,
}: OverviewTabProps) {
  const { t } = useTranslation();
  const currentUser = useAuthStore((s) => s.user);
  const [projectWizardOpen, setProjectWizardOpen] = useState(false);

  // --- Onboarding banner logic ---
  const dismissKey = `baticonnect-onboarding-dismissed-${buildingId}`;
  const [bannerDismissed, setBannerDismissed] = useState(() => {
    try {
      return localStorage.getItem(dismissKey) === '1';
    } catch {
      return false;
    }
  });

  const noDiagnostics = diagnostics.length === 0;
  const noDocuments = dashboard ? dashboard.activity.total_documents === 0 : false;
  const lowCompleteness = completenessPct < 20;
  const showOnboarding = !bannerDismissed && (noDiagnostics || noDocuments || lowCompleteness);

  const dismissOnboarding = () => {
    setBannerDismissed(true);
    try {
      localStorage.setItem(dismissKey, '1');
    } catch {
      // silent
    }
  };

  const { data: instantCard } = useQuery({
    queryKey: ['instant-card', buildingId],
    queryFn: () => intelligenceApi.getInstantCard(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  /** Map action source_type to the most relevant building detail tab */
  const actionSourceToTab = (sourceType: string): string | null => {
    if (sourceType === 'diagnostic' || sourceType === 'risk') return 'diagnostics';
    if (sourceType === 'document') return 'documents';
    if (sourceType === 'compliance') return 'procedures';
    return null;
  };

  return (
    <div className="space-y-6">
      {/* Onboarding Banner — shown when building has little data */}
      {showOnboarding && (
        <div className="relative bg-white dark:bg-slate-800 rounded-xl border border-blue-200 dark:border-blue-700 p-5">
          <button
            onClick={dismissOnboarding}
            className="absolute top-3 right-3 p-1 text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-300 rounded transition-colors"
            aria-label="Fermer"
          >
            <X className="w-4 h-4" />
          </button>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
            Bienvenue dans le dossier de ce batiment
          </h3>
          <p className="text-xs text-gray-500 dark:text-slate-400 mb-4">
            Trois etapes pour demarrer l&apos;evaluation de votre batiment.
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {/* Step 1 */}
            <button
              onClick={() => onNavigateTab?.('diagnostics')}
              className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors text-left"
            >
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
                <Stethoscope className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-gray-900 dark:text-white">1. Importez vos diagnostics</p>
                <p className="text-[11px] text-gray-500 dark:text-slate-400 mt-0.5">
                  Amiante, PCB, plomb, HAP, radon, PFAS
                </p>
              </div>
            </button>
            {/* Step 2 */}
            <button
              onClick={() => onNavigateTab?.('documents')}
              className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors text-left"
            >
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
                <FileUp className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-gray-900 dark:text-white">2. Ajoutez vos documents</p>
                <p className="text-[11px] text-gray-500 dark:text-slate-400 mt-0.5">Plans, rapports, photos, permis</p>
              </div>
            </button>
            {/* Step 3 */}
            <button
              onClick={() => onNavigateTab?.('overview')}
              className="flex items-start gap-3 p-3 rounded-lg bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors text-left"
            >
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/40 flex items-center justify-center">
                <Gauge className="w-4 h-4 text-blue-600 dark:text-blue-400" />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold text-gray-900 dark:text-white">3. Evaluez la readiness</p>
                <p className="text-[11px] text-gray-500 dark:text-slate-400 mt-0.5">
                  Score de completude et pret-a-demarrer
                </p>
              </div>
            </button>
          </div>
        </div>
      )}

      {/* Instant Card — full intelligence overview */}
      {instantCard && <InstantCardView data={instantCard} />}

      {/* Below-the-fold intelligence views — lazy-loaded */}
      <Suspense fallback={null}>
        <EvidenceByRoleView buildingId={buildingId} instantCard={instantCard} />
      </Suspense>

      <Suspense fallback={null}>
        <IndispensabilityView buildingId={buildingId} />
      </Suspense>

      <Suspense fallback={null}>
        <EcosystemEngagementsView buildingId={buildingId} />
      </Suspense>

      <Suspense fallback={null}>
        <OperationalGatesView buildingId={buildingId} />
      </Suspense>

      <Suspense fallback={null}>
        <MemoryTransferView buildingId={buildingId} />
      </Suspense>

      {/* === HERO: Readiness verdict (DossierStatusPanel) === */}
      <div
        className={cn(
          'rounded-xl border-2 p-6',
          dashboard?.readiness.overall_status === 'ready'
            ? 'border-green-400 bg-green-50 dark:border-green-600 dark:bg-green-900/20'
            : dashboard?.readiness.overall_status === 'partially_ready'
              ? 'border-amber-400 bg-amber-50 dark:border-amber-600 dark:bg-amber-900/20'
              : dashboard?.readiness.overall_status === 'not_ready'
                ? 'border-red-400 bg-red-50 dark:border-red-600 dark:bg-red-900/20'
                : 'border-gray-200 bg-gray-50 dark:border-slate-600 dark:bg-slate-700/50',
        )}
      >
        {dashboard && (
          <div className="flex items-center gap-3 mb-4">
            <ShieldCheck
              className={cn(
                'w-7 h-7',
                dashboard.readiness.overall_status === 'ready'
                  ? 'text-green-600 dark:text-green-400'
                  : dashboard.readiness.overall_status === 'partially_ready'
                    ? 'text-amber-600 dark:text-amber-400'
                    : dashboard.readiness.overall_status === 'not_ready'
                      ? 'text-red-600 dark:text-red-400'
                      : 'text-gray-400 dark:text-slate-500',
              )}
            />
            <div>
              <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                {t('readiness.title') || 'Readiness'}
              </p>
              <p
                className={cn(
                  'text-xl font-bold',
                  dashboard.readiness.overall_status === 'ready'
                    ? 'text-green-700 dark:text-green-300'
                    : dashboard.readiness.overall_status === 'partially_ready'
                      ? 'text-amber-700 dark:text-amber-300'
                      : dashboard.readiness.overall_status === 'not_ready'
                        ? 'text-red-700 dark:text-red-300'
                        : 'text-gray-500 dark:text-slate-400',
                )}
              >
                {dashboard.readiness.overall_status === 'ready'
                  ? t('readiness.status.ready') || 'Ready'
                  : dashboard.readiness.overall_status === 'partially_ready'
                    ? t('readiness.status.conditionally_ready') || 'Partiellement prêt'
                    : dashboard.readiness.overall_status === 'not_ready'
                      ? t('readiness.status.not_ready') || 'Non prêt'
                      : '\u2014'}
              </p>
            </div>
            {dashboard.readiness.blocked_count > 0 && (
              <span className="ml-auto inline-flex items-center gap-1 rounded-full bg-red-100 dark:bg-red-900/30 px-3 py-1 text-xs font-semibold text-red-700 dark:text-red-300">
                <AlertTriangle className="w-3 h-3" />
                {dashboard.readiness.blocked_count} {t('readiness.blocked') || 'blockers'}
              </span>
            )}
          </div>
        )}
        <DossierStatusPanel buildingId={buildingId} onNavigateTab={onNavigateTab} />
      </div>

      {/* === DOSSIER WORKFLOW: Full pre-works dossier lifecycle === */}
      <Suspense fallback={null}>
        <DossierWorkflowPanel buildingId={buildingId} onNavigateTab={onNavigateTab} />
      </Suspense>

      {/* === TRANSACTION READINESS: Prepare building for sale/transaction === */}
      <Suspense fallback={null}>
        <TransactionReadinessPanel buildingId={buildingId} />
      </Suspense>

      {/* === INSURANCE READINESS: Assess building for insurance === */}
      <Suspense fallback={null}>
        <InsuranceReadinessPanel buildingId={buildingId} />
      </Suspense>

      {/* === AUTHORITY PACK: Generate authority-ready dossier === */}
      <Suspense fallback={null}>
        <AuthorityPackPanel buildingId={buildingId} />
      </Suspense>

      {/* === RENOVATION READINESS: Assess and prepare renovation === */}
      <Suspense fallback={null}>
        <RenovationReadinessPanel buildingId={buildingId} />
      </Suspense>

      {/* === PACK BUILDER: Multi-audience pack generation === */}
      <Suspense fallback={null}>
        <PackBuilderPanel buildingId={buildingId} />
      </Suspense>

      {/* === PROJECT WIZARD: Launch a work project === */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-600 p-5">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
              <Hammer className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
            </div>
            <div>
              <p className="text-sm font-semibold text-gray-900 dark:text-white">Lancer un projet de travaux</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">
                Creez un projet pre-rempli a partir du dossier existant
              </p>
            </div>
          </div>
          <button
            onClick={() => setProjectWizardOpen(true)}
            className="px-4 py-2 text-sm font-semibold text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg transition-colors flex items-center gap-1.5"
          >
            <Hammer className="w-4 h-4" />
            Demarrer
          </button>
        </div>
      </div>
      <Suspense fallback={null}>
        <ProjectWizard
          open={projectWizardOpen}
          onClose={() => setProjectWizardOpen(false)}
          buildingId={buildingId}
          buildingName={building?.address}
        />
      </Suspense>

      {/* === SECONDARY: Completeness + Trust === */}
      {dashboard && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Completeness */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-600 p-5">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              {t('building.completeness') || 'Completeness'}
            </p>
            <div className="flex items-baseline gap-2">
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {dashboard.completeness.overall_score != null
                  ? `${Math.round(dashboard.completeness.overall_score * 100)}%`
                  : '\u2014'}
              </p>
              {dashboard.completeness.missing_count > 0 && (
                <p className="text-sm text-amber-600 dark:text-amber-400">
                  {dashboard.completeness.missing_count} {t('common.missing') || 'manquants'}
                </p>
              )}
            </div>
          </div>
          {/* Trust */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-600 p-5">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-2">
              {t('trust.title') || 'Trust'}
            </p>
            <div className="flex items-baseline gap-2">
              <p className="text-3xl font-bold text-gray-900 dark:text-white">
                {dashboard.trust.score != null ? `${Math.round(dashboard.trust.score * 100)}%` : '\u2014'}
              </p>
              {dashboard.trust.trend && (
                <p className="text-sm text-gray-500 dark:text-slate-400">{dashboard.trust.trend}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* === TERTIARY: Passport grade, Diagnostics, Alerts === */}
      {dashboard && (
        <div className="grid grid-cols-3 gap-3">
          {/* Passport Grade */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2 flex items-center gap-2">
            <span
              className={cn(
                'text-lg font-bold',
                dashboard.passport_grade === 'A'
                  ? 'text-green-600'
                  : dashboard.passport_grade === 'B'
                    ? 'text-lime-600'
                    : dashboard.passport_grade === 'C'
                      ? 'text-yellow-600'
                      : dashboard.passport_grade === 'D'
                        ? 'text-orange-600'
                        : dashboard.passport_grade === 'E' || dashboard.passport_grade === 'F'
                          ? 'text-red-600'
                          : 'text-gray-400 dark:text-slate-500',
              )}
            >
              {dashboard.passport_grade || '\u2014'}
            </span>
            <span className="text-xs text-gray-500 dark:text-slate-400">{t('passport.grade') || 'Passport'}</span>
          </div>
          {/* Diagnostics */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2 flex items-center gap-2">
            <span className="text-lg font-bold text-gray-900 dark:text-white">
              {dashboard.activity.completed_diagnostics}/{dashboard.activity.total_diagnostics}
            </span>
            <span className="text-xs text-gray-500 dark:text-slate-400">{t('diagnostic.title') || 'Diagnostics'}</span>
          </div>
          {/* Alerts */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2 flex items-center gap-2">
            <span
              className={cn(
                'text-lg font-bold',
                dashboard.alerts.constraint_blockers > 0 || dashboard.alerts.quality_issues > 0
                  ? 'text-amber-600'
                  : 'text-green-600',
              )}
            >
              {dashboard.alerts.weak_signals +
                dashboard.alerts.constraint_blockers +
                dashboard.alerts.quality_issues +
                dashboard.alerts.open_unknowns}
            </span>
            <span className="text-xs text-gray-500 dark:text-slate-400">{t('alert.title') || 'Alertes'}</span>
            {dashboard.alerts.constraint_blockers > 0 && (
              <span className="text-[10px] text-red-600 dark:text-red-400">
                ({dashboard.alerts.constraint_blockers} {t('alert.blockers') || 'blockers'})
              </span>
            )}
          </div>
        </div>
      )}

      {/* Dossier Journey — unified narrative flow */}
      <DossierJourney
        buildingId={buildingId}
        building={building}
        dashboard={dashboard}
        completenessItems={completenessItems}
        completenessPct={completenessPct}
        openActions={openActions}
        diagnostics={diagnostics}
        onNavigateTab={onNavigateTab}
      />

      {/* Action Queue — operator daily driver */}
      <ActionQueue buildingId={buildingId} onNavigateTab={onNavigateTab} />

      {/* Pilot Scorecard — per-building conversion metrics */}
      <PilotScorecardPanel buildingId={buildingId} />

      {/* Risk Overview */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{t('building.riskOverview')}</h2>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="flex flex-col items-center justify-center gap-3">
            <RiskGauge level={risk?.overall_risk_level || 'unknown'} />
            {risk && (
              <div className="text-center space-y-1">
                {risk.confidence != null && (
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {t('risk.confidence')}: {Math.round(risk.confidence * 100)}%
                  </p>
                )}
                {risk.data_source && (
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {t('risk.source')}: {risk.data_source}
                  </p>
                )}
                {risk.last_updated && (
                  <p className="text-xs text-gray-500 dark:text-slate-400">{formatDate(risk.last_updated)}</p>
                )}
              </div>
            )}
          </div>
          <div className="lg:col-span-2 space-y-3">
            <h3 className="text-sm font-medium text-gray-700 dark:text-slate-200">
              {t('building.pollutantProbabilities')}
            </h3>
            {Object.entries(pollutantProbabilities).length > 0 ? (
              Object.entries(pollutantProbabilities).map(([pollutant, probability]) => {
                const pct = typeof probability === 'number' ? probability * 100 : parseFloat(probability) || 0;
                return (
                  <div key={pollutant} className="flex items-center gap-3">
                    <PollutantBadge type={pollutant as PollutantType} />
                    <div className="flex-1">
                      <div className="h-3 bg-gray-100 dark:bg-slate-700 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            'h-full rounded-full transition-all',
                            pct > 75
                              ? 'bg-red-500'
                              : pct > 50
                                ? 'bg-orange-500'
                                : pct > 25
                                  ? 'bg-yellow-500'
                                  : 'bg-green-500',
                          )}
                          style={{ width: `${Math.min(100, pct)}%` }}
                        />
                      </div>
                    </div>
                    <span className="text-sm font-medium text-gray-700 dark:text-slate-200 w-14 text-right">
                      {pct.toFixed(0)}%
                    </span>
                  </div>
                );
              })
            ) : (
              <div className="flex flex-col items-center justify-center py-6 text-center">
                <AlertTriangle className="w-8 h-8 text-gray-300 dark:text-slate-600 mb-2" />
                <p className="text-sm text-gray-500 dark:text-slate-400">{t('building.noRiskData')}</p>
                <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
                  {t('next_action.create_diagnostic_desc')}
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Next Recommended Action */}
      <NextAction building={building} diagnostics={diagnostics} />

      {/* Completeness + Open Actions row */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Completeness */}
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <ClipboardList className="w-5 h-5 text-gray-500 dark:text-slate-400" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t('building.completeness')}</h3>
          </div>
          <p className="text-xs text-gray-500 dark:text-slate-400 mb-3">{t('building.completeness_desc')}</p>
          {/* Progress bar */}
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-slate-400 mb-1">
              <span>
                {completenessCount}/{completenessTotal}
              </span>
              <span>{completenessPct}%</span>
            </div>
            <div className="h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
              <div
                className={cn(
                  'h-full rounded-full transition-all',
                  completenessPct === 100 ? 'bg-green-500' : completenessPct >= 50 ? 'bg-yellow-500' : 'bg-red-500',
                )}
                style={{ width: `${completenessPct}%` }}
              />
            </div>
          </div>
          {/* Checklist */}
          <ul className="space-y-2">
            {completenessItems.map((item) => (
              <li key={item.key} className="flex items-center gap-2 text-sm">
                {item.done ? (
                  <CheckCircle2 className="w-4 h-4 text-green-500 flex-shrink-0" />
                ) : (
                  <Circle className="w-4 h-4 text-gray-300 dark:text-slate-500 flex-shrink-0" />
                )}
                <span
                  className={cn(item.done ? 'text-gray-700 dark:text-slate-200' : 'text-gray-400 dark:text-slate-500')}
                >
                  {item.key === 'diagnostic' && (t('diagnostic.title') || 'Diagnostic')}
                  {item.key === 'validated_diagnostic' && (t('diagnostic_status.validated') || 'Validated diagnostic')}
                  {item.key === 'documents' && (t('document.title') || 'Documents')}
                  {item.key === 'risk_score' && (t('building.risk_score') || 'Risk score')}
                </span>
              </li>
            ))}
          </ul>
        </div>

        {/* Open Actions */}
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-5">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-5 h-5 text-gray-500 dark:text-slate-400" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">{t('action.title') || 'Actions'}</h3>
          </div>
          <div className="flex items-baseline gap-2 mb-2">
            <span className="text-3xl font-bold text-gray-900 dark:text-white">{openActions.length}</span>
            <span className="text-sm text-gray-500 dark:text-slate-400">/ {actions.length} total</span>
          </div>
          {actionsError ? (
            <p className="text-sm text-red-600 dark:text-red-400 mt-2">{t('app.error')}</p>
          ) : openActions.length > 0 ? (
            <ul className="space-y-2 mt-3">
              {openActions.slice(0, 3).map((action: ActionItem) => {
                const targetTab = actionSourceToTab(action.source_type);
                const isUrgent = action.priority === 'critical' || action.priority === 'high';
                return (
                  <li key={action.id} className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-200">
                    <span
                      className={cn(
                        'w-2 h-2 rounded-full flex-shrink-0',
                        action.priority === 'critical'
                          ? 'bg-red-500'
                          : action.priority === 'high'
                            ? 'bg-orange-500'
                            : action.priority === 'medium'
                              ? 'bg-yellow-500'
                              : 'bg-green-500',
                      )}
                    />
                    <span className="truncate flex-1">{action.title}</span>
                    {onNavigateTab && targetTab && isUrgent && (
                      <button
                        onClick={() => onNavigateTab(targetTab)}
                        className="flex-shrink-0 inline-flex items-center gap-0.5 text-[10px] font-medium text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 transition-colors"
                      >
                        {t('action.resolve') || 'Résoudre'}
                        <ChevronRight className="w-3 h-3" />
                      </button>
                    )}
                  </li>
                );
              })}
              {openActions.length > 3 && (
                <li className="text-xs text-gray-500 dark:text-slate-400">
                  +{openActions.length - 3} {t('common.more') || 'more'}
                </li>
              )}
            </ul>
          ) : (
            <p className="text-sm text-gray-500 dark:text-slate-400 mt-2">{t('action.no_actions') || 'No actions'}</p>
          )}
        </div>
      </div>

      {/* Data Quality Score */}
      <DataQualityScore buildingId={buildingId} />

      {/* Passport Summary */}
      <PassportCard buildingId={buildingId} />

      {/* ROI Summary */}
      <ROICard buildingId={buildingId} />

      {/* Shared Links for this building */}
      <SharedLinksPanel buildingId={buildingId} />

      {/* Prework Diagnostic Triggers */}
      <PreworkDiagnosticTriggerCard buildingId={buildingId} />

      {/* Predictive Readiness Alerts */}
      <PredictiveAlertsBuilding buildingId={buildingId} />

      {/* Intelligence Surfaces */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ReadinessSummary buildingId={buildingId} onNavigateTab={onNavigateTab} />
        <TrustScoreCard buildingId={buildingId} />
        <UnknownIssuesList buildingId={buildingId} />
        <ChangeSignalsFeed buildingId={buildingId} />
        <ContradictionCard buildingId={buildingId} />
      </div>

      {/* Geo Context Overlays (geo.admin) */}
      <Suspense fallback={<div className="h-24 animate-pulse bg-gray-100 dark:bg-gray-800 rounded-xl" />}>
        <LazyGeoContextPanel buildingId={buildingId} />
      </Suspense>

      {/* swissBUILDINGS3D Spatial Enrichment */}
      <Suspense fallback={<div className="h-24 animate-pulse bg-gray-100 dark:bg-gray-800 rounded-xl" />}>
        <LazySpatialEnrichmentCard buildingId={buildingId} />
      </Suspense>

      {/* Identity Chain: Address -> EGID -> EGRID -> RDPPF */}
      <Suspense fallback={<div className="h-24 animate-pulse bg-gray-100 dark:bg-gray-800 rounded-xl" />}>
        <LazyIdentityChainPanel buildingId={buildingId} />
      </Suspense>

      {/* Regulatory Forms Workspace */}
      <Suspense fallback={<div className="h-24 animate-pulse bg-gray-100 dark:bg-gray-800 rounded-xl" />}>
        <LazyFormsWorkspace buildingId={buildingId} />
      </Suspense>

      {/* Post-Works Before/After */}
      <PostWorksDiffCard buildingId={buildingId} />

      {/* Time Machine */}
      <TimeMachinePanel buildingId={buildingId} />

      {/* Workspace, Inbox & Obligations */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <WorkspaceMembersCard buildingId={buildingId} />
        <DocumentInboxCard buildingId={buildingId} />
      </div>
      <ObligationsCard buildingId={buildingId} />

      {/* Quick Access Links */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Link
          to={`/buildings/${buildingId}/explorer`}
          className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-slate-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors group"
        >
          <Layers className="w-8 h-8 text-red-600 group-hover:scale-110 transition-transform" />
          <div>
            <p className="font-medium text-gray-900 dark:text-white">{t('building.tab.explorer')}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('explorer.title')}</p>
          </div>
        </Link>
        <Link
          to={`/buildings/${buildingId}/interventions`}
          className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-slate-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors group"
        >
          <Wrench className="w-8 h-8 text-red-600 group-hover:scale-110 transition-transform" />
          <div>
            <p className="font-medium text-gray-900 dark:text-white">{t('building.tab.interventions')}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('intervention.title')}</p>
          </div>
        </Link>
        <Link
          to={`/buildings/${buildingId}/plans`}
          className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-slate-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors group"
        >
          <FileImage className="w-8 h-8 text-red-600 group-hover:scale-110 transition-transform" />
          <div>
            <p className="font-medium text-gray-900 dark:text-white">{t('building.tab.plans')}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('plan.title')}</p>
          </div>
        </Link>
        <Link
          to={`/buildings/${buildingId}/timeline`}
          className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-slate-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors group"
        >
          <Clock className="w-8 h-8 text-red-600 group-hover:scale-110 transition-transform" />
          <div>
            <p className="font-medium text-gray-900 dark:text-white">{t('timeline.title')}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('timeline.description')}</p>
          </div>
        </Link>
        <Link
          to={`/buildings/${buildingId}/readiness`}
          className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-slate-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors group"
        >
          <ShieldCheck className="w-8 h-8 text-red-600 group-hover:scale-110 transition-transform" />
          <div>
            <p className="font-medium text-gray-900 dark:text-white">
              {t('readiness.wallet_title') || 'Readiness Wallet'}
            </p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('readiness.title')}</p>
          </div>
        </Link>
        <Link
          to={`/buildings/${buildingId}/safe-to-x`}
          className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-slate-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors group"
        >
          <BarChart3 className="w-8 h-8 text-red-600 group-hover:scale-110 transition-transform" />
          <div>
            <p className="font-medium text-gray-900 dark:text-white">{t('safe_to.title') || 'Transaction Readiness'}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              {t('safe_to.subtitle') || 'Safe to sell, insure, finance, lease'}
            </p>
          </div>
        </Link>
        <Link
          to={`/buildings/${buildingId}/simulator`}
          className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-slate-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors group"
        >
          <Beaker className="w-8 h-8 text-red-600 group-hover:scale-110 transition-transform" />
          <div>
            <p className="font-medium text-gray-900 dark:text-white">
              {t('simulator.title') || 'Intervention Simulator'}
            </p>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              {t('simulator.subtitle') || 'Simulate intervention impacts'}
            </p>
          </div>
        </Link>
        <Link
          to={`/buildings/${buildingId}/field-observations`}
          className="flex items-center gap-3 p-4 bg-gray-50 dark:bg-slate-700/50 rounded-xl hover:bg-gray-100 dark:hover:bg-slate-700 transition-colors group"
        >
          <ClipboardList className="w-8 h-8 text-red-600 group-hover:scale-110 transition-transform" />
          <div>
            <p className="font-medium text-gray-900 dark:text-white">{t('field_observations.title')}</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{t('building.quick_access.field_observations')}</p>
          </div>
        </Link>
      </div>

      {/* Audience Pack Preview */}
      <AudiencePackPreview buildingId={buildingId} />

      {/* Package Preset Preview */}
      <PackagePresetPreview buildingId={buildingId} />

      {/* Swiss Rules Watch + Exchange History */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SwissRulesWatchPanel buildingId={buildingId} />
        <ExchangeHistoryPanel buildingId={buildingId} />
      </div>

      {/* Artifact Archive Posture + Custody Chain */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ArchivePosture buildingId={buildingId} />
        <CustodyChainPanel buildingId={buildingId} />
      </div>

      {/* Proof Delivery History */}
      <ProofDeliveryHistory buildingId={buildingId} />

      {/* Public Sector Panels */}
      {currentUser?.organization_id && <PublicOwnerModePanel orgId={currentUser.organization_id} />}
      <ReviewPackCard buildingId={buildingId} />
      <CommitteePackCard buildingId={buildingId} />

      {/* Dossier Export (handled by DossierStatusPanel above) */}
    </div>
  );
}

export default OverviewTab;
