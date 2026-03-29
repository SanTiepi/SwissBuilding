import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cn } from '@/utils/formatters';
import {
  transactionReadinessApi,
  type TransactionAssessment,
  type TransactionItem,
  type TransactionPackResult,
} from '@/api/transactionReadiness';
import { packExportApi } from '@/api/packExport';
import {
  Banknote,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Package,
  ShieldCheck,
  ShieldAlert,
  Eye,
  FileWarning,
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
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const VERDICT_CONFIG: Record<
  string,
  { label: string; color: string; bg: string; border: string; icon: typeof CheckCircle2 }
> = {
  ready: {
    label: 'Pret pour la vente',
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
  not_ready: {
    label: 'Non pret',
    color: 'text-red-700 dark:text-red-300',
    bg: 'bg-red-100 dark:bg-red-900/30',
    border: 'border-red-300 dark:border-red-700',
    icon: XCircle,
  },
};

const GRADE_COLORS: Record<string, string> = {
  A: 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30',
  B: 'text-lime-600 dark:text-lime-400 bg-lime-100 dark:bg-lime-900/30',
  C: 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30',
  D: 'text-orange-600 dark:text-orange-400 bg-orange-100 dark:bg-orange-900/30',
  E: 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30',
  F: 'text-red-700 dark:text-red-300 bg-red-200 dark:bg-red-900/40',
};

const RISK_RATING_CONFIG: Record<string, { label: string; color: string }> = {
  low: { label: 'Faible', color: 'text-green-600 dark:text-green-400' },
  medium: { label: 'Moyen', color: 'text-amber-600 dark:text-amber-400' },
  high: { label: 'Eleve', color: 'text-red-600 dark:text-red-400' },
  critical: { label: 'Critique', color: 'text-red-700 dark:text-red-300' },
};

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface TransactionReadinessPanelProps {
  buildingId: string;
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

/** Progress bar used for trust and completeness */
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

/** Expandable section wrapper */
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

/** Item list for blockers / conditions / caveats */
function ItemList({
  items,
  emptyText,
  iconColor = 'text-red-500',
}: {
  items: TransactionItem[];
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

/** Chip / badge for buyer summary lists */
function Chip({ text, variant }: { text: string; variant: 'fact' | 'risk' | 'strength' }) {
  const colors = {
    fact: 'bg-gray-100 dark:bg-slate-600 text-gray-700 dark:text-slate-200',
    risk: 'bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-300',
    strength: 'bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-300',
  };
  return (
    <span className={cn('inline-block px-2 py-0.5 rounded text-[10px] font-medium', colors[variant])}>{text}</span>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function TransactionReadinessPanel({ buildingId }: TransactionReadinessPanelProps) {
  const queryClient = useQueryClient();
  const [expanded, setExpanded] = useState(false);
  const [packResult, setPackResult] = useState<TransactionPackResult | null>(null);
  const [redactFinancials, setRedactFinancials] = useState(true);

  // Fetch transaction assessment
  const {
    data: assessment,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['transaction-readiness-panel', buildingId],
    queryFn: () => transactionReadinessApi.assess(buildingId),
    staleTime: 60_000,
    retry: 1,
  });

  // Generate pack mutation
  const generateMutation = useMutation({
    mutationFn: () => transactionReadinessApi.generatePack(buildingId, redactFinancials),
    onSuccess: (data) => {
      setPackResult(data);
      queryClient.invalidateQueries({ queryKey: ['transaction-readiness-panel', buildingId] });
    },
  });

  // Derive collapsed status
  const quickVerdict = assessment?.verdict ?? 'not_ready';
  const verdictCfg = VERDICT_CONFIG[quickVerdict] ?? VERDICT_CONFIG.not_ready;
  const blockerCount =
    (assessment?.safe_to_sell?.blockers?.length ?? 0) + (assessment?.completeness?.critical_missing?.length ?? 0);

  const quickLabel =
    quickVerdict === 'ready' ? 'Pret pour la vente' : quickVerdict === 'conditional' ? 'Sous conditions' : 'Non pret';

  const quickDot =
    quickVerdict === 'ready' ? 'bg-green-500' : quickVerdict === 'conditional' ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div
      className={cn(
        'bg-white dark:bg-slate-800 rounded-xl border-2 overflow-hidden transition-colors',
        assessment ? verdictCfg.border : 'border-gray-200 dark:border-slate-600',
      )}
      data-testid="transaction-readiness-panel"
    >
      {/* Collapsed header -- always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-100 dark:bg-indigo-900/40 flex items-center justify-center">
            <Banknote className="w-5 h-5 text-indigo-600 dark:text-indigo-400" />
          </div>
          <div className="text-left">
            <p className="text-sm font-bold text-gray-900 dark:text-white">Preparation transaction</p>
            <div className="flex items-center gap-2 mt-0.5">
              <p className="text-xs text-gray-500 dark:text-slate-400">{quickLabel}</p>
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
              <span>Impossible de charger l&apos;evaluation de transaction.</span>
            </div>
          )}

          {/* Assessment content */}
          {assessment && !isLoading && (
            <>
              {/* 1. Verdict hero */}
              <div className="pt-4">
                <VerdictHero assessment={assessment} />
              </div>

              {/* 2. Trust & Completeness row */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <ShieldCheck className="w-4 h-4 text-gray-500 dark:text-slate-400" />
                    <span className="text-xs font-medium text-gray-600 dark:text-slate-400">Confiance</span>
                    {assessment.trust.level && (
                      <span
                        className={cn(
                          'text-[10px] font-semibold px-1.5 py-0.5 rounded',
                          assessment.trust.score_pct >= 70
                            ? 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300'
                            : assessment.trust.score_pct >= 40
                              ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
                              : 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
                        )}
                      >
                        {assessment.trust.level}
                      </span>
                    )}
                  </div>
                  <ScoreBar pct={assessment.trust.score_pct} label="Score de confiance" />
                </div>
                <div>
                  <div className="flex items-center gap-2 mb-2">
                    <Eye className="w-4 h-4 text-gray-500 dark:text-slate-400" />
                    <span className="text-xs font-medium text-gray-600 dark:text-slate-400">Completude</span>
                  </div>
                  <ScoreBar pct={assessment.completeness.score_pct} label="Score de completude" />
                </div>
              </div>

              {/* 3. Critical gaps */}
              {(assessment.completeness.critical_missing.length > 0 || assessment.completeness.missing.length > 0) && (
                <ExpandableSection
                  title="Manques critiques"
                  icon={FileWarning}
                  badge={
                    assessment.completeness.critical_missing.length > 0 ? (
                      <span className="text-[10px] font-semibold text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30 px-1.5 py-0.5 rounded">
                        {assessment.completeness.critical_missing.length} critique
                        {assessment.completeness.critical_missing.length > 1 ? 's' : ''}
                      </span>
                    ) : undefined
                  }
                  defaultOpen={assessment.completeness.critical_missing.length > 0}
                >
                  <div className="space-y-3">
                    {assessment.completeness.critical_missing.length > 0 && (
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                          Critiques pour la transaction
                        </p>
                        <ul className="space-y-1">
                          {assessment.completeness.critical_missing.map((item, i) => (
                            <li
                              key={i}
                              className="flex items-center justify-between gap-2 text-[11px] text-red-600 dark:text-red-400"
                            >
                              <span className="flex items-center gap-1.5">
                                <XCircle className="w-3 h-3 flex-shrink-0" />
                                {item}
                              </span>
                              <button className="text-[10px] font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 flex items-center gap-0.5 flex-shrink-0">
                                Resoudre
                                <ArrowRight className="w-3 h-3" />
                              </button>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                    {assessment.completeness.missing.length > 0 && (
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                          Autres manques
                        </p>
                        <ul className="space-y-1">
                          {assessment.completeness.missing.map((item, i) => (
                            <li
                              key={i}
                              className="flex items-center gap-1.5 text-[11px] text-amber-600 dark:text-amber-400"
                            >
                              <AlertTriangle className="w-3 h-3 flex-shrink-0" />
                              {item}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                </ExpandableSection>
              )}

              {/* 4. Contradictions & Caveats */}
              {(assessment.contradictions.count > 0 || assessment.caveats.count > 0) && (
                <ExpandableSection
                  title="Contradictions et reserves"
                  icon={ShieldAlert}
                  badge={
                    <span className="text-[10px] font-semibold text-amber-600 dark:text-amber-400 bg-amber-100 dark:bg-amber-900/30 px-1.5 py-0.5 rounded">
                      {assessment.contradictions.count + assessment.caveats.count}
                    </span>
                  }
                >
                  <div className="space-y-3">
                    {assessment.contradictions.count > 0 && (
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                          Contradictions ({assessment.contradictions.count})
                        </p>
                        <ItemList items={assessment.contradictions.items} iconColor="text-amber-500" />
                      </div>
                    )}
                    {assessment.caveats.seller_caveats.length > 0 && (
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                          Reserves du vendeur
                        </p>
                        <ItemList items={assessment.caveats.seller_caveats} iconColor="text-amber-500" />
                      </div>
                    )}
                    {assessment.caveats.buyer_risks.length > 0 && (
                      <div>
                        <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1.5">
                          Risques acheteur
                        </p>
                        <ItemList items={assessment.caveats.buyer_risks} iconColor="text-red-500" />
                      </div>
                    )}
                  </div>
                </ExpandableSection>
              )}

              {/* 5. Incidents */}
              {(assessment.incidents.unresolved_count > 0 || assessment.incidents.recurring_count > 0) && (
                <ExpandableSection
                  title="Incidents"
                  icon={AlertOctagon}
                  badge={
                    <span
                      className={cn(
                        'text-[10px] font-semibold px-1.5 py-0.5 rounded',
                        RISK_RATING_CONFIG[assessment.incidents.risk_rating]?.color ?? 'text-gray-500',
                        assessment.incidents.risk_rating === 'high' || assessment.incidents.risk_rating === 'critical'
                          ? 'bg-red-100 dark:bg-red-900/30'
                          : 'bg-amber-100 dark:bg-amber-900/30',
                      )}
                    >
                      {RISK_RATING_CONFIG[assessment.incidents.risk_rating]?.label ?? assessment.incidents.risk_rating}
                    </span>
                  }
                >
                  <div className="grid grid-cols-2 gap-3">
                    <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-slate-700/50">
                      <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-0.5">
                        Non resolus
                      </p>
                      <p className="text-lg font-bold text-gray-900 dark:text-white">
                        {assessment.incidents.unresolved_count}
                      </p>
                    </div>
                    <div className="p-2.5 rounded-lg bg-gray-50 dark:bg-slate-700/50">
                      <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-0.5">
                        Recurrents
                      </p>
                      <p className="text-lg font-bold text-gray-900 dark:text-white">
                        {assessment.incidents.recurring_count}
                      </p>
                    </div>
                  </div>
                </ExpandableSection>
              )}

              {/* 6. Buyer summary preview */}
              {assessment.buyer_summary && (
                <ExpandableSection title="Apercu acheteur" icon={Eye}>
                  <BuyerSummaryPreview summary={assessment.buyer_summary} />
                </ExpandableSection>
              )}

              {/* 7. Next actions */}
              {assessment.next_actions.length > 0 && (
                <ExpandableSection title="Prochaines actions" icon={ArrowRight}>
                  <ul className="space-y-1.5">
                    {assessment.next_actions.map((action, i) => (
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

              {/* 8. Pack generation */}
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

function VerdictHero({ assessment }: { assessment: TransactionAssessment }) {
  const cfg = VERDICT_CONFIG[assessment.verdict] ?? VERDICT_CONFIG.not_ready;
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
      {assessment.ownership && (
        <div className="flex items-center gap-2 text-[11px] text-gray-500 dark:text-slate-400">
          {assessment.ownership.documented ? (
            <CheckCircle2 className="w-3 h-3 text-green-500" />
          ) : (
            <XCircle className="w-3 h-3 text-red-500" />
          )}
          Propriete:{' '}
          {assessment.ownership.current_owner
            ? assessment.ownership.current_owner
            : assessment.ownership.documented
              ? 'Documente'
              : 'Non documente'}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Buyer Summary Preview                                              */
/* ------------------------------------------------------------------ */

function BuyerSummaryPreview({ summary }: { summary: TransactionAssessment['buyer_summary'] }) {
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
            {summary.year > 0 ? summary.year : '\u2014'} &middot; {summary.pollutant_status || '\u2014'}
          </p>
        </div>
      </div>

      {/* Key facts */}
      {summary.key_facts.length > 0 && (
        <div>
          <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
            Faits cles
          </p>
          <div className="flex flex-wrap gap-1">
            {summary.key_facts.map((f, i) => (
              <Chip key={i} text={f} variant="fact" />
            ))}
          </div>
        </div>
      )}

      {/* Key risks */}
      {summary.key_risks.length > 0 && (
        <div>
          <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
            <TrendingDown className="w-3 h-3 inline mr-0.5" />
            Risques
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
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Transaction Export Buttons                                         */
/* ------------------------------------------------------------------ */

function TransactionExportButtons({ buildingId, redactFinancials }: { buildingId: string; redactFinancials: boolean }) {
  const [downloading, setDownloading] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [shareExpiry, setShareExpiry] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      const blob = await packExportApi.generateTransactionPdf(buildingId, redactFinancials);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pack-transaction-${buildingId.slice(0, 8)}.pdf`;
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
      const result = await packExportApi.createShareLink(buildingId, 'transaction');
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
  assessment: TransactionAssessment;
  packResult: TransactionPackResult | null;
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
            <span className="text-sm font-medium text-green-700 dark:text-green-300">Pack transaction genere</span>
            <p className="text-[11px] text-green-600 dark:text-green-400">
              {packResult.sections.length} section{packResult.sections.length > 1 ? 's' : ''}
              {packResult.redacted_financials && ' \u00B7 Donnees financieres masquees'}
            </p>
          </div>
        </div>
        <TransactionExportButtons buildingId={buildingId} redactFinancials={redactFinancials} />
      </div>
    );
  }

  // Not ready — disabled button with blockers
  if (!assessment.pack_ready) {
    return (
      <div className="pt-3 border-t border-gray-100 dark:border-slate-700">
        <div className="relative group">
          <button
            disabled
            className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold text-gray-400 dark:text-slate-500 bg-gray-100 dark:bg-slate-700 rounded-lg cursor-not-allowed"
          >
            <Package className="w-4 h-4" />
            Generer le pack transaction
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

  // Ready — show generate button with redaction toggle
  return (
    <div className="pt-3 border-t border-gray-100 dark:border-slate-700 space-y-3">
      {/* Redaction toggle */}
      <label className="flex items-center gap-2 cursor-pointer">
        <input
          type="checkbox"
          checked={redactFinancials}
          onChange={onToggleRedact}
          className="w-4 h-4 rounded border-gray-300 dark:border-slate-500 text-indigo-600 focus:ring-indigo-500 dark:bg-slate-700"
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
          assessment.verdict === 'ready'
            ? 'text-white bg-green-600 hover:bg-green-700 disabled:opacity-50'
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
            Generer le pack transaction
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
