import { useQuery } from '@tanstack/react-query';
import { cn } from '@/utils/formatters';
import { readinessApi } from '@/api/readiness';
import type { Building, ActionItem, ReadinessAssessment, ReadinessStatus } from '@/types';
import type { BuildingDashboard } from '@/api/buildingDashboard';
import {
  CheckCircle2,
  XCircle,
  AlertTriangle,
  ChevronRight,
  Shield,
  ArrowDown,
  Circle,
} from 'lucide-react';
import { ConfidenceBadge } from '@/components/ConfidenceBadge';

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface DossierJourneyProps {
  buildingId: string;
  building: Building;
  dashboard: BuildingDashboard | undefined;
  completenessItems: { key: string; done: boolean }[];
  completenessPct: number;
  openActions: ActionItem[];
  diagnostics: { diagnostic_type: string }[];
  onNavigateTab?: (tab: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const GRADE_COLORS: Record<string, { bg: string; text: string; ring: string }> = {
  A: { bg: 'bg-emerald-100 dark:bg-emerald-900/40', text: 'text-emerald-700 dark:text-emerald-300', ring: 'ring-emerald-500' },
  B: { bg: 'bg-green-100 dark:bg-green-900/40', text: 'text-green-700 dark:text-green-300', ring: 'ring-green-500' },
  C: { bg: 'bg-yellow-100 dark:bg-yellow-900/40', text: 'text-yellow-700 dark:text-yellow-300', ring: 'ring-yellow-500' },
  D: { bg: 'bg-orange-100 dark:bg-orange-900/40', text: 'text-orange-700 dark:text-orange-300', ring: 'ring-orange-500' },
  E: { bg: 'bg-red-100 dark:bg-red-900/40', text: 'text-red-700 dark:text-red-300', ring: 'ring-red-500' },
  F: { bg: 'bg-red-100 dark:bg-red-900/40', text: 'text-red-700 dark:text-red-300', ring: 'ring-red-500' },
};

const READINESS_LABELS: Record<string, string> = {
  safe_to_start: 'Pret a demarrer',
  safe_to_tender: 'Pret a soumissionner',
  safe_to_reopen: 'Pret a rouvrir',
  safe_to_requalify: 'Pret a requalifier',
};

const STATUS_LABEL: Record<string, string> = {
  ready: 'Passe',
  conditionally_ready: 'Conditionnel',
  not_ready: 'Non passe',
  blocked: 'Bloque',
};

const STATUS_STYLES: Record<string, { text: string; icon: typeof CheckCircle2 }> = {
  ready: { text: 'text-green-600 dark:text-green-400', icon: CheckCircle2 },
  conditionally_ready: { text: 'text-amber-600 dark:text-amber-400', icon: AlertTriangle },
  not_ready: { text: 'text-red-600 dark:text-red-400', icon: XCircle },
  blocked: { text: 'text-red-700 dark:text-red-500', icon: XCircle },
};

const PRIORITY_BADGE: Record<string, string> = {
  critical: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
  high: 'bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300',
  medium: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
  low: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300',
};

/** Map completeness item key to a building detail tab */
function itemToTab(key: string): string | null {
  if (key === 'diagnostic' || key === 'validated_diagnostic') return 'diagnostics';
  if (key === 'documents') return 'documents';
  if (key === 'risk_score') return 'overview';
  return null;
}

/** Map action source_type to a building detail tab */
function actionToTab(sourceType: string): string | null {
  if (sourceType === 'diagnostic' || sourceType === 'risk') return 'diagnostics';
  if (sourceType === 'document') return 'documents';
  if (sourceType === 'compliance') return 'procedures';
  return null;
}

/** Map blocker label to a building detail tab */
function blockerToTab(label: string): string | null {
  const lower = label.toLowerCase();
  if (lower.includes('diagnostic') || lower.includes('sample') || lower.includes('pollutant')) return 'diagnostics';
  if (lower.includes('document') || lower.includes('evidence') || lower.includes('report') || lower.includes('proof')) return 'documents';
  if (lower.includes('ownership') || lower.includes('owner')) return 'ownership';
  if (lower.includes('lease') || lower.includes('tenant')) return 'leases';
  if (lower.includes('contract')) return 'contracts';
  if (lower.includes('procedure') || lower.includes('compliance') || lower.includes('regulatory')) return 'procedures';
  return null;
}

const ITEM_LABELS: Record<string, string> = {
  diagnostic: 'Diagnostic',
  validated_diagnostic: 'Diagnostic valide',
  documents: 'Documents',
  risk_score: 'Score de risque',
};

/* ------------------------------------------------------------------ */
/*  Section connector                                                  */
/* ------------------------------------------------------------------ */

function SectionConnector({ step, total }: { step: number; total: number }) {
  if (step >= total) return null;
  return (
    <div className="flex justify-center py-1">
      <div className="flex flex-col items-center">
        <div className="w-px h-4 bg-gray-300 dark:bg-slate-600" />
        <ArrowDown className="w-4 h-4 text-gray-300 dark:text-slate-600" />
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Step header                                                        */
/* ------------------------------------------------------------------ */

function StepHeader({
  step,
  title,
  variant,
}: {
  step: number;
  title: string;
  variant: 'neutral' | 'success' | 'warning' | 'danger';
}) {
  const colors: Record<string, string> = {
    neutral: 'bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-slate-200',
    success: 'bg-green-100 dark:bg-green-900/40 text-green-700 dark:text-green-300',
    warning: 'bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300',
    danger: 'bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300',
  };

  return (
    <div className="flex items-center gap-2.5 mb-3">
      <span
        className={cn(
          'inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-bold',
          colors[variant],
        )}
      >
        {step}
      </span>
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{title}</h4>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export function DossierJourney({
  buildingId,
  building,
  dashboard,
  completenessItems,
  completenessPct,
  openActions,
  diagnostics,
  onNavigateTab,
}: DossierJourneyProps) {
  // Fetch readiness assessments (React Query will deduplicate with ReadinessSummary)
  const { data: readinessData } = useQuery({
    queryKey: ['building-readiness', buildingId],
    queryFn: () => readinessApi.list(buildingId),
    enabled: !!buildingId,
  });

  // Derive readiness gates (latest per type)
  const latestByType = new Map<string, ReadinessAssessment>();
  for (const a of readinessData?.items ?? []) {
    const existing = latestByType.get(a.readiness_type);
    if (!existing || a.assessed_at > existing.assessed_at) {
      latestByType.set(a.readiness_type, a);
    }
  }

  // Guard: if no dashboard data yet, render nothing
  if (!dashboard) return null;

  const grade = dashboard.passport_grade;
  const gradeColors = grade ? (GRADE_COLORS[grade] ?? GRADE_COLORS.F) : null;

  // Detected pollutants from diagnostics
  const pollutantTypes = [...new Set(diagnostics.map((d) => d.diagnostic_type).filter((t) => t !== 'full'))];

  // Completeness split
  const documented = completenessItems.filter((i) => i.done);
  const missing = completenessItems.filter((i) => !i.done);

  // Overall readiness verdict
  const readinessStatus = dashboard.readiness.overall_status;
  const readinessVerdict =
    readinessStatus === 'ready'
      ? { label: 'Pret', color: 'text-green-700 dark:text-green-300', bg: 'bg-green-100 dark:bg-green-900/30' }
      : readinessStatus === 'partially_ready'
        ? { label: 'Partiellement pret', color: 'text-amber-700 dark:text-amber-300', bg: 'bg-amber-100 dark:bg-amber-900/30' }
        : readinessStatus === 'not_ready'
          ? { label: 'Non pret', color: 'text-red-700 dark:text-red-300', bg: 'bg-red-100 dark:bg-red-900/30' }
          : { label: '\u2014', color: 'text-gray-500 dark:text-slate-400', bg: 'bg-gray-100 dark:bg-slate-700' };

  // Section variant helpers
  const completenessVariant: 'success' | 'warning' | 'danger' =
    completenessPct >= 80 ? 'success' : completenessPct >= 50 ? 'warning' : 'danger';

  const readinessVariant: 'success' | 'warning' | 'danger' =
    readinessStatus === 'ready' ? 'success' : readinessStatus === 'partially_ready' ? 'warning' : 'danger';

  const actionsVariant: 'success' | 'warning' | 'danger' | 'neutral' =
    openActions.length === 0 ? 'success' : openActions.some((a) => a.priority === 'critical') ? 'danger' : 'warning';

  // Completeness bar color
  const barColor =
    completenessPct >= 80
      ? 'bg-green-500'
      : completenessPct >= 50
        ? 'bg-amber-500'
        : completenessPct >= 20
          ? 'bg-orange-500'
          : 'bg-red-500';

  // Top actions (max 5)
  const topActions = openActions.slice(0, 5);

  // Readiness gate types
  const gateTypes = ['safe_to_start', 'safe_to_tender', 'safe_to_reopen', 'safe_to_requalify'] as const;

  return (
    <div
      className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5 shadow-sm"
      data-testid="dossier-journey"
    >
      {/* Title */}
      <div className="flex items-center gap-2 mb-5">
        <Shield className="w-5 h-5 text-red-600 dark:text-red-400" />
        <h3 className="text-base font-semibold text-gray-900 dark:text-white">
          Parcours du dossier
        </h3>
      </div>

      {/* ============ SECTION 1: Etat du batiment ============ */}
      <div className="rounded-lg bg-gray-50 dark:bg-slate-700/50 p-4">
        <StepHeader step={1} title="Etat du batiment" variant="neutral" />
        <div className="flex items-center gap-4">
          {/* Grade badge */}
          {gradeColors && grade ? (
            <div
              className={cn(
                'flex items-center justify-center w-12 h-12 rounded-full ring-2 text-xl font-bold shrink-0',
                gradeColors.bg,
                gradeColors.text,
                gradeColors.ring,
              )}
            >
              {grade}
            </div>
          ) : (
            <div className="flex items-center justify-center w-12 h-12 rounded-full ring-2 ring-gray-300 dark:ring-slate-600 bg-gray-100 dark:bg-slate-700 text-gray-400 dark:text-slate-500 text-xl font-bold shrink-0">
              ?
            </div>
          )}

          <div className="min-w-0 flex-1">
            {/* Address */}
            <p className="text-sm font-medium text-gray-900 dark:text-white truncate">
              {building.address}, {building.postal_code} {building.city}
            </p>
            {/* One-line summary */}
            <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
              {building.construction_year
                ? `Batiment de ${building.construction_year}`
                : 'Annee de construction inconnue'}
              {pollutantTypes.length > 0
                ? `, ${pollutantTypes.length} polluant${pollutantTypes.length > 1 ? 's' : ''} documente${pollutantTypes.length > 1 ? 's' : ''}`
                : ''}
              {grade ? `, grade ${grade}` : ''}
            </p>
            {/* Pollutant badges */}
            {pollutantTypes.length > 0 && (
              <div className="flex flex-wrap gap-1.5 mt-2">
                {pollutantTypes.map((p) => (
                  <span
                    key={p}
                    className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium uppercase bg-gray-200 dark:bg-slate-600 text-gray-700 dark:text-slate-200"
                  >
                    {p}
                  </span>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <SectionConnector step={1} total={4} />

      {/* ============ SECTION 2: Completude du dossier ============ */}
      <div className="rounded-lg bg-gray-50 dark:bg-slate-700/50 p-4">
        <StepHeader step={2} title="Completude du dossier" variant={completenessVariant} />

        {/* Progress bar */}
        <div className="mb-3">
          <div className="flex items-center justify-between text-xs text-gray-500 dark:text-slate-400 mb-1">
            <span>{completenessPct}%</span>
            {completenessPct < 20 && (
              <span className="text-red-600 dark:text-red-400 font-medium flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Critique
              </span>
            )}
            {completenessPct >= 20 && completenessPct < 50 && (
              <span className="text-amber-600 dark:text-amber-400 font-medium flex items-center gap-1">
                <AlertTriangle className="w-3 h-3" />
                Incomplet
              </span>
            )}
          </div>
          <div className="h-2.5 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
            <div
              className={cn('h-full rounded-full transition-all duration-500', barColor)}
              style={{ width: `${completenessPct}%` }}
            />
          </div>
        </div>

        {/* Two columns: documented / missing */}
        <div className="grid grid-cols-2 gap-4 mt-3">
          {/* Documented */}
          <div>
            <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
              Documente
            </p>
            {documented.length > 0 ? (
              <ul className="space-y-1">
                {documented.map((item) => (
                  <li key={item.key} className="flex items-center gap-1.5 text-xs text-gray-700 dark:text-slate-200">
                    <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                    <span className="flex-1">{ITEM_LABELS[item.key] || item.key}</span>
                    <ConfidenceBadge level="validated" size="sm" />
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-xs text-gray-400 dark:text-slate-500 italic">Aucun element documente</p>
            )}
          </div>

          {/* Missing */}
          <div>
            <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
              Manquant
            </p>
            {missing.length > 0 ? (
              <ul className="space-y-1">
                {missing.map((item) => {
                  const tab = itemToTab(item.key);
                  return (
                    <li key={item.key} className="flex items-center gap-1.5 text-xs">
                      <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                      {onNavigateTab && tab ? (
                        <button
                          onClick={() => onNavigateTab(tab)}
                          className="text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 underline underline-offset-2 transition-colors text-left"
                        >
                          {ITEM_LABELS[item.key] || item.key}
                        </button>
                      ) : (
                        <span className="text-gray-500 dark:text-slate-400">
                          {ITEM_LABELS[item.key] || item.key}
                        </span>
                      )}
                    </li>
                  );
                })}
              </ul>
            ) : (
              <p className="text-xs text-green-600 dark:text-green-400 flex items-center gap-1">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Tout est documente
              </p>
            )}
          </div>
        </div>
      </div>

      <SectionConnector step={2} total={4} />

      {/* ============ SECTION 3: Verdict de readiness ============ */}
      <div className="rounded-lg bg-gray-50 dark:bg-slate-700/50 p-4">
        <StepHeader step={3} title="Verdict de readiness" variant={readinessVariant} />

        {/* Large verdict */}
        <div className={cn('inline-flex items-center gap-2 px-4 py-2 rounded-lg text-lg font-bold mb-4', readinessVerdict.bg, readinessVerdict.color)}>
          {readinessStatus === 'ready' && <CheckCircle2 className="w-5 h-5" />}
          {readinessStatus === 'partially_ready' && <AlertTriangle className="w-5 h-5" />}
          {readinessStatus === 'not_ready' && <XCircle className="w-5 h-5" />}
          {!readinessStatus && <Circle className="w-5 h-5" />}
          {readinessVerdict.label}
        </div>

        {/* Gates */}
        <div className="space-y-2">
          {gateTypes.map((type) => {
            const assessment = latestByType.get(type);
            const status = assessment?.status as ReadinessStatus | undefined;
            const styles = status ? (STATUS_STYLES[status] ?? STATUS_STYLES.not_ready) : null;
            const Icon = styles?.icon ?? Circle;
            const blockers = assessment?.blockers_json ?? [];

            return (
              <div key={type} className="rounded-lg bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 px-3 py-2">
                <div className="flex items-center gap-2">
                  <Icon className={cn('w-4 h-4 flex-shrink-0', styles?.text ?? 'text-gray-300 dark:text-slate-500')} />
                  <span className="text-xs font-medium text-gray-700 dark:text-slate-200 flex-1">
                    {READINESS_LABELS[type] || type.replace(/_/g, ' ')}
                  </span>
                  <span className={cn('text-[10px] font-medium', styles?.text ?? 'text-gray-400 dark:text-slate-500')}>
                    {status ? (STATUS_LABEL[status] || status) : 'Non evalue'}
                  </span>
                </div>

                {/* Blockers for this gate */}
                {blockers.length > 0 && (
                  <ul className="mt-1.5 ml-6 space-y-1">
                    {blockers.slice(0, 3).map((blocker, i) => {
                      const tab = blockerToTab(blocker.label);
                      return (
                        <li key={i} className="flex items-center gap-1.5 text-[11px]">
                          <span className="text-gray-500 dark:text-slate-400 flex-1">{blocker.label}</span>
                          {onNavigateTab && tab && (
                            <button
                              onClick={() => onNavigateTab(tab)}
                              className="flex-shrink-0 inline-flex items-center gap-0.5 text-[10px] font-medium text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 transition-colors"
                            >
                              Resoudre
                              <ChevronRight className="w-3 h-3" />
                            </button>
                          )}
                        </li>
                      );
                    })}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      </div>

      <SectionConnector step={3} total={4} />

      {/* ============ SECTION 4: Prochaines actions ============ */}
      <div className="rounded-lg bg-gray-50 dark:bg-slate-700/50 p-4">
        <StepHeader step={4} title="Prochaines actions" variant={actionsVariant} />

        {topActions.length > 0 ? (
          <ul className="space-y-2">
            {topActions.map((action) => {
              const tab = actionToTab(action.source_type);
              return (
                <li
                  key={action.id}
                  className="flex items-center gap-2 rounded-lg bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 px-3 py-2"
                >
                  <span
                    className={cn(
                      'w-2 h-2 rounded-full flex-shrink-0',
                      action.priority === 'critical'
                        ? 'bg-red-500'
                        : action.priority === 'high'
                          ? 'bg-orange-500'
                          : action.priority === 'medium'
                            ? 'bg-amber-500'
                            : 'bg-green-500',
                    )}
                  />
                  <span className="text-xs text-gray-700 dark:text-slate-200 flex-1 truncate">
                    {action.title}
                  </span>
                  <span
                    className={cn(
                      'text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0',
                      PRIORITY_BADGE[action.priority] || PRIORITY_BADGE.low,
                    )}
                  >
                    {action.priority}
                  </span>
                  {onNavigateTab && tab && (
                    <button
                      onClick={() => onNavigateTab(tab)}
                      className="flex-shrink-0 inline-flex items-center gap-0.5 text-[10px] font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
                    >
                      Resoudre
                      <ChevronRight className="w-3 h-3" />
                    </button>
                  )}
                </li>
              );
            })}
            {openActions.length > 5 && (
              <p className="text-xs text-gray-400 dark:text-slate-500 pl-1">
                +{openActions.length - 5} autres actions
              </p>
            )}
          </ul>
        ) : (
          <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
            <CheckCircle2 className="w-4 h-4" />
            Aucune action bloquante
          </div>
        )}
      </div>
    </div>
  );
}

export default DossierJourney;
