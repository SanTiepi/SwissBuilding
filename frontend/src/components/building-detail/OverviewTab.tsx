import { Link } from 'react-router-dom';
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
import WorkspaceMembersCard from '@/components/building-detail/WorkspaceMembersCard';
import DocumentInboxCard from '@/components/building-detail/DocumentInboxCard';
import ObligationsCard from '@/components/building-detail/ObligationsCard';
import ProofDeliveryHistory from '@/components/building-detail/ProofDeliveryHistory';
import SwissRulesWatchPanel from '@/components/building-detail/SwissRulesWatchPanel';
import ExchangeHistoryPanel from '@/components/building-detail/ExchangeHistoryPanel';
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
}: OverviewTabProps) {
  const { t } = useTranslation();

  return (
    <div className="space-y-6">
      {/* Dashboard Summary (aggregate endpoint) */}
      {dashboard && (
        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          {/* Passport Grade */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              {t('passport.grade') || 'Passport'}
            </p>
            <p
              className={cn(
                'text-2xl font-bold',
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
            </p>
          </div>
          {/* Trust */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">{t('trust.title') || 'Trust'}</p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {dashboard.trust.score != null ? `${Math.round(dashboard.trust.score * 100)}%` : '\u2014'}
            </p>
            {dashboard.trust.trend && (
              <p className="text-xs text-gray-500 dark:text-slate-400">{dashboard.trust.trend}</p>
            )}
          </div>
          {/* Completeness */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              {t('building.completeness') || 'Completeness'}
            </p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {dashboard.completeness.overall_score != null
                ? `${Math.round(dashboard.completeness.overall_score * 100)}%`
                : '\u2014'}
            </p>
            {dashboard.completeness.missing_count > 0 && (
              <p className="text-xs text-amber-600 dark:text-amber-400">
                {dashboard.completeness.missing_count} {t('common.missing') || 'missing'}
              </p>
            )}
          </div>
          {/* Readiness */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              {t('readiness.title') || 'Readiness'}
            </p>
            <p
              className={cn(
                'text-sm font-semibold',
                dashboard.readiness.overall_status === 'ready'
                  ? 'text-green-600'
                  : dashboard.readiness.overall_status === 'partially_ready'
                    ? 'text-yellow-600'
                    : dashboard.readiness.overall_status === 'not_ready'
                      ? 'text-red-600'
                      : 'text-gray-500 dark:text-slate-400',
              )}
            >
              {dashboard.readiness.overall_status || '\u2014'}
            </p>
            {dashboard.readiness.blocked_count > 0 && (
              <p className="text-xs text-red-600 dark:text-red-400">
                {dashboard.readiness.blocked_count} {t('readiness.blocked') || 'blocked'}
              </p>
            )}
          </div>
          {/* Activity */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              {t('diagnostic.title') || 'Diagnostics'}
            </p>
            <p className="text-2xl font-bold text-gray-900 dark:text-white">
              {dashboard.activity.completed_diagnostics}/{dashboard.activity.total_diagnostics}
            </p>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              {dashboard.activity.open_actions} {t('action.open') || 'open actions'}
            </p>
          </div>
          {/* Alerts */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4 text-center">
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">{t('alert.title') || 'Alerts'}</p>
            <p
              className={cn(
                'text-2xl font-bold',
                dashboard.alerts.constraint_blockers > 0 || dashboard.alerts.quality_issues > 0
                  ? 'text-amber-600'
                  : 'text-green-600',
              )}
            >
              {dashboard.alerts.weak_signals +
                dashboard.alerts.constraint_blockers +
                dashboard.alerts.quality_issues +
                dashboard.alerts.open_unknowns}
            </p>
            {dashboard.alerts.constraint_blockers > 0 && (
              <p className="text-xs text-red-600 dark:text-red-400">
                {dashboard.alerts.constraint_blockers} {t('alert.blockers') || 'blockers'}
              </p>
            )}
          </div>
        </div>
      )}

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
              {openActions.slice(0, 3).map((action: ActionItem) => (
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
                  <span className="truncate">{action.title}</span>
                </li>
              ))}
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

      {/* Dossier Status (unified safe-to-start journey) */}
      <DossierStatusPanel buildingId={buildingId} />

      {/* Passport Summary */}
      <PassportCard buildingId={buildingId} />

      {/* ROI Summary */}
      <ROICard buildingId={buildingId} />

      {/* Shared Links for this building */}
      <SharedLinksPanel buildingId={buildingId} />

      {/* Prework Diagnostic Triggers */}
      <PreworkDiagnosticTriggerCard buildingId={buildingId} />

      {/* Intelligence Surfaces */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <ReadinessSummary buildingId={buildingId} />
        <TrustScoreCard buildingId={buildingId} />
        <UnknownIssuesList buildingId={buildingId} />
        <ChangeSignalsFeed buildingId={buildingId} />
        <ContradictionCard buildingId={buildingId} />
      </div>

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

      {/* Swiss Rules Watch + Exchange History */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <SwissRulesWatchPanel buildingId={buildingId} />
        <ExchangeHistoryPanel buildingId={buildingId} />
      </div>

      {/* Proof Delivery History */}
      <ProofDeliveryHistory buildingId={buildingId} />

      {/* Dossier Export (handled by DossierStatusPanel above) */}
    </div>
  );
}

export default OverviewTab;
