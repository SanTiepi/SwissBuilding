import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cn } from '@/utils/formatters';
import {
  insuranceReadinessApi,
  type InsuranceAssessment,
  type InsuranceItem,
  type InsurancePackResult,
} from '@/api/insuranceReadiness';
import { packExportApi } from '@/api/packExport';
import {
  Shield,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Package,
  ShieldAlert,
  ShieldCheck,
  AlertOctagon,
  Star,
  TrendingDown,
  ArrowRight,
  Lock,
  Info,
  Download,
  Share2,
  Copy,
  Check,
  Activity,
  Eye,
  Search,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const VERDICT_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string; icon: typeof CheckCircle2 }
> = {
  insurable: {
    label: 'Assurable',
    color: 'text-green-700 dark:text-green-300',
    bg: 'bg-green-100 dark:bg-green-900/30',
    border: 'border-green-300 dark:border-green-700',
    icon: CheckCircle2,
  },
  conditional: {
    label: 'Sous conditions',
    color: 'text-amber-700 dark:text-amber-300',
    bg: 'bg-amber-100 dark:bg-amber-900/30',
    border: 'border-amber-300 dark:border-amber-700',
    icon: AlertTriangle,
  },
  not_insurable: {
    label: 'Non assurable',
    color: 'text-red-700 dark:text-red-300',
    bg: 'bg-red-100 dark:bg-red-900/30',
    border: 'border-red-300 dark:border-red-700',
    icon: XCircle,
  },
};

const RISK_RATING_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  low: {
    label: 'Faible',
    color: 'text-green-700 dark:text-green-300',
    bg: 'bg-green-100 dark:bg-green-900/30',
  },
  medium: {
    label: 'Moyen',
    color: 'text-amber-700 dark:text-amber-300',
    bg: 'bg-amber-100 dark:bg-amber-900/30',
  },
  high: {
    label: 'Eleve',
    color: 'text-red-700 dark:text-red-300',
    bg: 'bg-red-100 dark:bg-red-900/30',
  },
  critical: {
    label: 'Critique',
    color: 'text-red-800 dark:text-red-200',
    bg: 'bg-red-200 dark:bg-red-900/40',
  },
};

const POLLUTANT_STATUS_CONFIG: Record<string, { label: string; color: string; bg: string }> = {
  clear: {
    label: 'Absent',
    color: 'text-green-700 dark:text-green-300',
    bg: 'bg-green-100 dark:bg-green-900/30',
  },
  traces: {
    label: 'Traces',
    color: 'text-amber-700 dark:text-amber-300',
    bg: 'bg-amber-100 dark:bg-amber-900/30',
  },
  present: {
    label: 'Present',
    color: 'text-red-700 dark:text-red-300',
    bg: 'bg-red-100 dark:bg-red-900/30',
  },
  unknown: {
    label: 'Inconnu',
    color: 'text-gray-500 dark:text-slate-400',
    bg: 'bg-gray-100 dark:bg-slate-700',
  },
};

const POLLUTANT_LABELS: Record<string, string> = {
  asbestos: 'Amiante',
  pcb: 'PCB',
  lead: 'Plomb',
  radon: 'Radon',
};

const GRADE_COLORS: Record<string, string> = {
  A: 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30',
  B: 'text-lime-600 dark:text-lime-400 bg-lime-100 dark:bg-lime-900/30',
  C: 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30',
  D: 'text-orange-600 dark:text-orange-400 bg-orange-100 dark:bg-orange-900/30',
  E: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30',
  F: 'text-red-700 dark:text-red-300 bg-red-200 dark:bg-red-900/40',
};

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface InsuranceReadinessPanelProps {
  buildingId: string;
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function ScoreBar({ pct, label }: { pct: number; label: string }) {
  const barColor = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-500';
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-medium text-gray-600 dark:text-slate-400">{label}</span>
        <span className="text-xs font-semibold text-gray-700 dark:text-slate-200">{pct}%</span>
      </div>
      <div className="h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all duration-500', barColor)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

function ExpandableSection({
  title,
  icon: Icon,
  badge,
  children,
  defaultOpen = false,
}: {
  title: string;
  icon: typeof AlertTriangle;
  badge?: React.ReactNode;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div className="border-t border-gray-100 dark:border-slate-700 pt-3">
      <button onClick={() => setOpen(!open)} className="w-full flex items-center justify-between text-left group">
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-gray-500 dark:text-slate-400" />
          <span className="text-xs font-semibold text-gray-700 dark:text-slate-200">{title}</span>
          {badge}
        </div>
        {open ? (
          <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
        )}
      </button>
      {open && <div className="mt-3">{children}</div>}
    </div>
  );
}

function ItemList({
  items,
  emptyText,
  iconColor = 'text-red-500',
}: {
  items: InsuranceItem[];
  emptyText?: string;
  iconColor?: string;
}) {
  if (items.length === 0 && emptyText) {
    return <p className="text-[11px] text-gray-400 dark:text-slate-500 italic">{emptyText}</p>;
  }
  return (
    <ul className="space-y-1.5">
      {items.map((item, i) => (
        <li key={i} className="flex items-start gap-2 text-[11px]">
          <span className={cn('mt-0.5 w-1.5 h-1.5 rounded-full flex-shrink-0', iconColor.replace('text-', 'bg-'))} />
          <div className="min-w-0">
            <span className="text-gray-700 dark:text-slate-300">{item.label}</span>
            {item.details && <p className="text-gray-500 dark:text-slate-400 mt-0.5">{item.details}</p>}
          </div>
        </li>
      ))}
    </ul>
  );
}

function Chip({ text, variant }: { text: string; variant: 'risk' | 'strength' | 'inspection' }) {
  const colors = {
    risk: 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300',
    strength: 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300',
    inspection: 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300',
  };
  return (
    <span className={cn('inline-block px-2 py-0.5 rounded text-[10px] font-medium', colors[variant])}>{text}</span>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function InsuranceReadinessPanel({ buildingId }: InsuranceReadinessPanelProps) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [packResult, setPackResult] = useState<InsurancePackResult | null>(null);
  const [redactFinancials, setRedactFinancials] = useState(false);

  const {
    data: assessment,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['insurance-readiness-panel', buildingId],
    queryFn: () => insuranceReadinessApi.assess(buildingId),
    staleTime: 60_000,
    retry: 1,
  });

  const generateMutation = useMutation({
    mutationFn: () => insuranceReadinessApi.generatePack(buildingId, redactFinancials),
    onSuccess: (data) => {
      setPackResult(data);
      queryClient.invalidateQueries({ queryKey: ['insurance-readiness-panel', buildingId] });
    },
  });

  const quickVerdict = assessment?.verdict ?? 'not_insurable';
  const verdictCfg = VERDICT_CONFIG[quickVerdict] ?? VERDICT_CONFIG.not_insurable;
  const blockerCount =
    (assessment?.safe_to_insure?.blockers?.length ?? 0) + (assessment?.unknowns?.blocking_insurance?.length ?? 0);

  const quickLabel =
    quickVerdict === 'insurable' ? 'Assurable' : quickVerdict === 'conditional' ? 'Sous conditions' : 'Non assurable';

  const quickDot =
    quickVerdict === 'insurable' ? 'bg-green-500' : quickVerdict === 'conditional' ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div
      className={cn(
        'bg-white dark:bg-slate-800 rounded-xl border-2 overflow-hidden transition-colors',
        assessment ? verdictCfg.border : 'border-gray-200 dark:border-slate-600',
      )}
      data-testid="insurance-readiness-panel"
    >
      {/* Collapsed header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-teal-100 dark:bg-teal-900/40 flex items-center justify-center">
            <Shield className="w-5 h-5 text-teal-600 dark:text-teal-400" />
          </div>
          <div className="text-left">
            <p className="text-sm font-bold text-gray-900 dark:text-white">Preparation assurance</p>
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-xs text-gray-500 dark:text-slate-400">{quickLabel}</p>
              {assessment?.risk_profile?.overall_rating && (
                <span
                  className={cn(
                    'text-[10px] font-semibold px-1.5 py-0.5 rounded',
                    RISK_RATING_CONFIG[assessment.risk_profile.overall_rating]?.bg ?? 'bg-gray-100 dark:bg-slate-700',
                    RISK_RATING_CONFIG[assessment.risk_profile.overall_rating]?.color ?? 'text-gray-500',
                  )}
                >
                  Risque{' '}
                  {RISK_RATING_CONFIG[assessment.risk_profile.overall_rating]?.label ??
                    assessment.risk_profile.overall_rating}
                </span>
              )}
              {blockerCount > 0 && (
                <span className="text-[10px] font-medium text-red-600 dark:text-red-400">
                  {blockerCount} blocage{blockerCount > 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn('w-2.5 h-2.5 rounded-full', quickDot)} />
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-gray-100 dark:border-slate-700">
          {/* Loading */}
          {isLoading && (
            <div className="flex items-center justify-center py-8 text-gray-400 dark:text-slate-500">
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
              <span className="text-sm">Evaluation en cours...</span>
            </div>
          )}

          {/* Error */}
          {error && !isLoading && (
            <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-600 dark:text-red-400 mt-4">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>Impossible de charger l&apos;evaluation assurance.</span>
            </div>
          )}

          {/* Assessment content */}
          {assessment && !isLoading && (
            <>
              {/* 1. Verdict hero */}
              <div className="pt-4">
                <VerdictHero assessment={assessment} />
              </div>

              {/* 2. Risk profile section */}
              <RiskProfileSection assessment={assessment} />

              {/* 3. Completeness */}
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <Eye className="w-4 h-4 text-gray-500 dark:text-slate-400" />
                  <span className="text-xs font-medium text-gray-600 dark:text-slate-400">Completude dossier</span>
                </div>
                <ScoreBar pct={assessment.completeness.score_pct} label="Score de completude" />
              </div>

              {/* 4. Pollutant status row */}
              <PollutantStatusRow pollutantStatus={assessment.pollutant_status} />

              {/* 5. Coverage gaps & exclusions */}
              {(assessment.caveats.insurer_exclusions.length > 0 ||
                assessment.caveats.coverage_gaps.length > 0 ||
                assessment.caveats.implied_conditions.length > 0) && (
                <ExpandableSection
                  title="Couverture et exclusions"
                  icon={ShieldAlert}
                  badge={
                    <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/30 px-1.5 py-0.5 rounded">
                      {assessment.caveats.count}
                    </span>
                  }
                >
                  <div className="space-y-3">
                    {assessment.caveats.insurer_exclusions.length > 0 && (
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                          Exclusions assureur
                        </p>
                        <ItemList items={assessment.caveats.insurer_exclusions} iconColor="text-red-500" />
                      </div>
                    )}
                    {assessment.caveats.coverage_gaps.length > 0 && (
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                          Lacunes de couverture
                        </p>
                        <ItemList items={assessment.caveats.coverage_gaps} iconColor="text-amber-500" />
                      </div>
                    )}
                    {assessment.caveats.implied_conditions.length > 0 && (
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                          Conditions implicites
                        </p>
                        <ItemList items={assessment.caveats.implied_conditions} iconColor="text-amber-500" />
                      </div>
                    )}
                  </div>
                </ExpandableSection>
              )}

              {/* 6. Incidents */}
              {(assessment.incidents.unresolved.length > 0 ||
                assessment.incidents.recurring.length > 0 ||
                assessment.incidents.recent.length > 0) && (
                <ExpandableSection
                  title="Incidents"
                  icon={AlertOctagon}
                  badge={
                    <span className="text-[10px] font-semibold text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30 px-1.5 py-0.5 rounded">
                      {assessment.incidents.total}
                    </span>
                  }
                  defaultOpen={assessment.incidents.unresolved.length > 0}
                >
                  <div className="space-y-3">
                    {assessment.incidents.unresolved.length > 0 && (
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                          Non resolus ({assessment.incidents.unresolved.length})
                        </p>
                        <ItemList items={assessment.incidents.unresolved} iconColor="text-red-500" />
                      </div>
                    )}
                    {assessment.incidents.recurring.length > 0 && (
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                          Recurrents ({assessment.incidents.recurring.length})
                        </p>
                        <ItemList items={assessment.incidents.recurring} iconColor="text-amber-500" />
                      </div>
                    )}
                    {assessment.incidents.recent.length > 0 && (
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                          12 derniers mois ({assessment.incidents.recent.length})
                        </p>
                        <ItemList items={assessment.incidents.recent} iconColor="text-gray-500" />
                      </div>
                    )}
                  </div>
                </ExpandableSection>
              )}

              {/* 7. Insurer summary preview */}
              {assessment.insurer_summary && (
                <ExpandableSection title="Apercu assureur" icon={Eye}>
                  <InsurerSummaryPreview summary={assessment.insurer_summary} />
                </ExpandableSection>
              )}

              {/* 8. Next actions */}
              {assessment.next_actions.length > 0 && (
                <ExpandableSection title="Prochaines actions" icon={ArrowRight}>
                  <ul className="space-y-1.5">
                    {assessment.next_actions.slice(0, 5).map((action, i) => (
                      <li key={i} className="flex items-center gap-2 text-[11px]">
                        <span
                          className={cn(
                            'w-1.5 h-1.5 rounded-full flex-shrink-0',
                            action.priority === 'critical' || action.priority === 'high'
                              ? 'bg-red-500'
                              : action.priority === 'medium'
                                ? 'bg-amber-500'
                                : 'bg-green-500',
                          )}
                        />
                        <span className="text-gray-700 dark:text-slate-300">{action.title}</span>
                      </li>
                    ))}
                  </ul>
                </ExpandableSection>
              )}

              {/* 9. Pack generation */}
              <PackGenerationSection
                assessment={assessment}
                packResult={packResult}
                redactFinancials={redactFinancials}
                onToggleRedact={() => setRedactFinancials(!redactFinancials)}
                onGenerate={() => generateMutation.mutate()}
                generating={generateMutation.isPending}
                generateError={generateMutation.isError}
                buildingId={buildingId}
              />
            </>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Verdict Hero                                                       */
/* ------------------------------------------------------------------ */

function VerdictHero({ assessment }: { assessment: InsuranceAssessment }) {
  const cfg = VERDICT_CONFIG[assessment.verdict] ?? VERDICT_CONFIG.not_insurable;
  const Icon = cfg.icon;

  return (
    <div className="space-y-2">
      <div
        className={cn('inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-base font-bold', cfg.bg, cfg.color)}
      >
        <Icon className="w-5 h-5" />
        {cfg.label}
      </div>
      {assessment.verdict_summary && (
        <p className="text-xs text-gray-600 dark:text-slate-400 leading-relaxed">{assessment.verdict_summary}</p>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Risk Profile Section                                               */
/* ------------------------------------------------------------------ */

function RiskProfileSection({ assessment }: { assessment: InsuranceAssessment }) {
  const rp = assessment.risk_profile;
  const ratingCfg = RISK_RATING_CONFIG[rp.overall_rating] ?? RISK_RATING_CONFIG.medium;

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <Activity className="w-4 h-4 text-gray-500 dark:text-slate-400" />
        <span className="text-xs font-semibold text-gray-700 dark:text-slate-200">Profil de risque</span>
        <span className={cn('text-[10px] font-semibold px-1.5 py-0.5 rounded', ratingCfg.bg, ratingCfg.color)}>
          {ratingCfg.label}
        </span>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-slate-700/50">
          <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-0.5">
            Incidents
          </p>
          <p className="text-lg font-bold text-gray-900 dark:text-white">{rp.incident_count}</p>
        </div>
        <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-slate-700/50">
          <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-0.5">
            Non resolus
          </p>
          <p
            className={cn(
              'text-lg font-bold',
              rp.unresolved_incidents > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white',
            )}
          >
            {rp.unresolved_incidents}
          </p>
        </div>
        <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-slate-700/50">
          <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-0.5">
            Recurrents
          </p>
          <p
            className={cn(
              'text-lg font-bold',
              rp.recurring_patterns > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-gray-900 dark:text-white',
            )}
          >
            {rp.recurring_patterns}
          </p>
        </div>
        {rp.total_claim_cost_chf > 0 && (
          <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-slate-700/50">
            <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-0.5">
              Cout total CHF
            </p>
            <p className="text-lg font-bold text-gray-900 dark:text-white">
              {rp.total_claim_cost_chf.toLocaleString('fr-CH')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Pollutant Status Row                                               */
/* ------------------------------------------------------------------ */

function PollutantStatusRow({ pollutantStatus }: { pollutantStatus: InsuranceAssessment['pollutant_status'] }) {
  const pollutants = (['asbestos', 'pcb', 'lead', 'radon'] as const).map((key) => ({
    key,
    label: POLLUTANT_LABELS[key],
    status: pollutantStatus[key],
  }));

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <ShieldCheck className="w-4 h-4 text-gray-500 dark:text-slate-400" />
        <span className="text-xs font-semibold text-gray-700 dark:text-slate-200">Polluants</span>
      </div>
      <div className="flex flex-wrap gap-2">
        {pollutants.map((p) => {
          const cfg = POLLUTANT_STATUS_CONFIG[p.status] ?? POLLUTANT_STATUS_CONFIG.unknown;
          return (
            <span
              key={p.key}
              className={cn(
                'inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-medium',
                cfg.bg,
                cfg.color,
              )}
            >
              {p.label}: {cfg.label}
            </span>
          );
        })}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Insurer Summary Preview                                            */
/* ------------------------------------------------------------------ */

function InsurerSummaryPreview({ summary }: { summary: InsuranceAssessment['insurer_summary'] }) {
  const ratingCfg = RISK_RATING_CONFIG[summary.risk_rating] ?? RISK_RATING_CONFIG.medium;

  return (
    <div className="space-y-3">
      {/* Grade + meta row */}
      <div className="flex items-center gap-3">
        <span
          className={cn(
            'text-lg font-bold w-8 h-8 rounded flex items-center justify-center',
            GRADE_COLORS[summary.building_grade] ?? 'text-gray-500 bg-gray-100 dark:bg-slate-600',
          )}
        >
          {summary.building_grade || '\u2014'}
        </span>
        <div className="text-[11px] text-gray-600 dark:text-slate-400">
          <p>{summary.address || '\u2014'}</p>
          <p>
            {summary.year > 0 ? summary.year : '\u2014'} &middot;{' '}
            <span className={cn('font-medium', ratingCfg.color)}>Risque {ratingCfg.label.toLowerCase()}</span>
          </p>
        </div>
      </div>

      {/* Key risks */}
      {summary.key_risks.length > 0 && (
        <div>
          <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
            <TrendingDown className="w-3 h-3 inline mr-0.5" />
            Risques cles
          </p>
          <div className="flex flex-wrap gap-1">
            {summary.key_risks.map((r, i) => (
              <Chip key={i} text={r} variant="risk" />
            ))}
          </div>
        </div>
      )}

      {/* Key strengths */}
      {summary.key_strengths.length > 0 && (
        <div>
          <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
            <Star className="w-3 h-3 inline mr-0.5" />
            Points forts
          </p>
          <div className="flex flex-wrap gap-1">
            {summary.key_strengths.map((s, i) => (
              <Chip key={i} text={s} variant="strength" />
            ))}
          </div>
        </div>
      )}

      {/* Recommended inspections */}
      {summary.recommended_inspections.length > 0 && (
        <div>
          <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
            <Search className="w-3 h-3 inline mr-0.5" />
            Inspections recommandees
          </p>
          <div className="flex flex-wrap gap-1">
            {summary.recommended_inspections.map((insp, i) => (
              <Chip key={i} text={insp} variant="inspection" />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Insurance Export Buttons                                            */
/* ------------------------------------------------------------------ */

function InsuranceExportButtons({ buildingId, redactFinancials }: { buildingId: string; redactFinancials: boolean }) {
  const [downloading, setDownloading] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [shareExpiry, setShareExpiry] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      const blob = await packExportApi.generatePackPdf(buildingId, 'insurance', redactFinancials);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pack-assurance-${buildingId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silent
    } finally {
      setDownloading(false);
    }
  };

  const handleShare = async () => {
    setSharing(true);
    try {
      const result = await packExportApi.createShareLink(buildingId, 'insurance');
      setShareLink(result.share_url);
      setShareExpiry(result.expires_at);
    } catch {
      // silent
    } finally {
      setSharing(false);
    }
  };

  const handleCopy = async () => {
    if (!shareLink) return;
    try {
      await navigator.clipboard.writeText(shareLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <button
          onClick={handleDownloadPdf}
          disabled={downloading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors"
        >
          {downloading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
          Telecharger PDF
        </button>
        <button
          onClick={handleShare}
          disabled={sharing}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors"
        >
          {sharing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Share2 className="w-3.5 h-3.5" />}
          Partager
        </button>
      </div>
      {shareLink && (
        <div className="flex items-center gap-2 p-2.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <input
            type="text"
            value={shareLink}
            readOnly
            className="flex-1 text-xs text-blue-700 dark:text-blue-300 bg-transparent outline-none truncate font-mono"
          />
          <button
            onClick={handleCopy}
            className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium bg-blue-100 dark:bg-blue-800/50 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
          >
            {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copie' : 'Copier'}
          </button>
          {shareExpiry && (
            <span className="flex-shrink-0 text-[10px] text-blue-500 dark:text-blue-400">
              Expire le {new Date(shareExpiry).toLocaleDateString('fr-CH')}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Pack Generation Section                                            */
/* ------------------------------------------------------------------ */

function PackGenerationSection({
  assessment,
  packResult,
  redactFinancials,
  onToggleRedact,
  onGenerate,
  generating,
  generateError,
  buildingId,
}: {
  assessment: InsuranceAssessment;
  packResult: InsurancePackResult | null;
  redactFinancials: boolean;
  onToggleRedact: () => void;
  onGenerate: () => void;
  generating: boolean;
  generateError: boolean;
  buildingId: string;
}) {
  // Pack already generated
  if (packResult) {
    return (
      <div className="pt-3 border-t border-gray-100 dark:border-slate-700 space-y-2">
        <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg">
          <Package className="w-4 h-4 text-green-600 dark:text-green-400" />
          <div className="flex-1">
            <span className="text-sm font-medium text-green-700 dark:text-green-300">Pack assureur genere</span>
            <p className="text-[11px] text-green-600 dark:text-green-400">
              {packResult.sections.length} section{packResult.sections.length > 1 ? 's' : ''}
              {packResult.redacted_financials && ' \u00B7 Donnees financieres masquees'}
            </p>
          </div>
        </div>
        <InsuranceExportButtons buildingId={buildingId} redactFinancials={redactFinancials} />
      </div>
    );
  }

  // Not ready -- disabled button with blockers
  if (!assessment.pack_ready) {
    return (
      <div className="pt-3 border-t border-gray-100 dark:border-slate-700">
        <div className="relative group">
          <button
            disabled
            className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold text-gray-400 dark:text-slate-500 bg-gray-100 dark:bg-slate-700 rounded-lg cursor-not-allowed"
          >
            <Package className="w-4 h-4" />
            Generer le pack assureur
          </button>
          {assessment.pack_blockers.length > 0 && (
            <div className="mt-2 p-2.5 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
              <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                Conditions non remplies
              </p>
              <ul className="space-y-1">
                {assessment.pack_blockers.map((b, i) => (
                  <li key={i} className="flex items-center gap-1.5 text-[11px] text-red-600 dark:text-red-400">
                    <Lock className="w-3 h-3 flex-shrink-0" />
                    {b}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Ready -- show generate button with redaction toggle
  return (
    <div className="pt-3 border-t border-gray-100 dark:border-slate-700 space-y-3">
      {/* Redaction toggle */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={redactFinancials}
          onChange={onToggleRedact}
          className="w-4 h-4 rounded border-gray-300 dark:border-slate-500 text-teal-600 focus:ring-teal-500 dark:bg-slate-700"
        />
        <span className="text-xs text-gray-600 dark:text-slate-400">Masquer les donnees financieres</span>
        <span title="Les montants et flux financiers seront remplaces par des mentions generiques dans le pack">
          <Info className="w-3 h-3 text-gray-400 dark:text-slate-500" />
        </span>
      </label>

      {/* Generate button */}
      <button
        onClick={onGenerate}
        disabled={generating}
        className={cn(
          'w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold rounded-lg transition-colors',
          assessment.verdict === 'insurable'
            ? 'text-white bg-teal-600 hover:bg-teal-700 disabled:opacity-50'
            : 'text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50',
        )}
      >
        {generating ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            Generation en cours...
          </>
        ) : (
          <>
            <Package className="w-4 h-4" />
            Generer le pack assureur
          </>
        )}
      </button>
      {assessment.verdict === 'conditional' && (
        <p className="text-[11px] text-amber-600 dark:text-amber-400 text-center">Le pack sera genere avec reserves</p>
      )}
      {generateError && (
        <p className="text-xs text-red-600 dark:text-red-400 text-center">Erreur lors de la generation du pack.</p>
      )}
    </div>
  );
}
