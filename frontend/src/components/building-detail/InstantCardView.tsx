import { useState } from 'react';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import type {
  InstantCardResult,
  WhatWeKnow,
  WhatIsRisky,
  WhatBlocks,
  WhatToDoNext,
  WhatIsReusable,
  ExecutionSection,
  TrustMeta,
} from '@/api/intelligence';
import {
  ClipboardList,
  AlertTriangle,
  Ban,
  ArrowRight,
  Recycle,
  ChevronDown,
  ChevronRight,
  Shield,
  Clock,
  TrendingUp,
} from 'lucide-react';

interface InstantCardViewProps {
  data: InstantCardResult;
}

// --- Grade badge ---

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-emerald-500 text-white',
  B: 'bg-green-500 text-white',
  C: 'bg-yellow-500 text-white',
  D: 'bg-orange-500 text-white',
  E: 'bg-red-500 text-white',
  F: 'bg-red-700 text-white',
};

function GradeBadge({ grade }: { grade: string }) {
  const g = grade?.toUpperCase() || 'F';
  return (
    <div
      data-testid="grade-badge"
      className={cn(
        'inline-flex items-center justify-center w-14 h-14 rounded-xl text-2xl font-black shadow-lg',
        GRADE_COLORS[g] || GRADE_COLORS.F,
      )}
    >
      {g}
    </div>
  );
}

// --- Collapsible section ---

interface SectionProps {
  title: string;
  icon: React.ReactNode;
  headerColor: string;
  defaultOpen?: boolean;
  badge?: React.ReactNode;
  children: React.ReactNode;
  testId: string;
}

function CardSection({ title, icon, headerColor, defaultOpen = true, badge, children, testId }: SectionProps) {
  const [open, setOpen] = useState(defaultOpen);
  return (
    <div data-testid={testId} className="rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <button
        type="button"
        onClick={() => setOpen(!open)}
        className={cn(
          'w-full flex items-center gap-3 px-5 py-3.5 text-left font-semibold text-sm transition-colors',
          headerColor,
        )}
        data-testid={`${testId}-toggle`}
      >
        {icon}
        <span className="flex-1">{title}</span>
        {badge}
        {open ? <ChevronDown className="w-4 h-4 opacity-60" /> : <ChevronRight className="w-4 h-4 opacity-60" />}
      </button>
      {open && <div className="px-5 py-4 bg-white dark:bg-slate-900 space-y-3">{children}</div>}
    </div>
  );
}

// --- Risk bar ---

function RiskBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? 'bg-red-500' : pct >= 60 ? 'bg-orange-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-green-500';
  return (
    <div className="space-y-1" data-testid="risk-bar">
      <div className="flex justify-between text-xs text-slate-600 dark:text-slate-400">
        <span className="capitalize">{label}</span>
        <span className="font-medium">{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-slate-200 dark:bg-slate-700 overflow-hidden">
        <div className={cn('h-full rounded-full transition-all duration-700', color)} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

// --- Key-value row ---

function KVRow({ label, value }: { label: string; value: string | number | null | undefined }) {
  if (value === null || value === undefined) return null;
  return (
    <div className="flex justify-between py-1.5 border-b border-slate-100 dark:border-slate-800 last:border-0">
      <span className="text-xs text-slate-500 dark:text-slate-400">{label}</span>
      <span className="text-xs font-medium text-slate-800 dark:text-slate-200">{String(value)}</span>
    </div>
  );
}

// --- Priority badge ---

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = {
    high: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    medium: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
    low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  };
  return (
    <span
      className={cn('px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase', colors[priority] || colors.medium)}
    >
      {priority}
    </span>
  );
}

// --- Format CHF ---

function formatCHF(v: number | null | undefined): string {
  if (v === null || v === undefined) return '-';
  return `CHF ${v.toLocaleString('fr-CH', { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;
}

// --- Main component ---

export default function InstantCardView({ data }: InstantCardViewProps) {
  const { t } = useTranslation();

  const what_we_know: Partial<WhatWeKnow> = data?.what_we_know || {};
  const what_is_risky: Partial<WhatIsRisky> = data?.what_is_risky || {};
  const what_blocks: Partial<WhatBlocks> = data?.what_blocks || {};
  const what_to_do_next: Partial<WhatToDoNext> = data?.what_to_do_next || {};
  const what_is_reusable: Partial<WhatIsReusable> = data?.what_is_reusable || {};
  const execution: Partial<ExecutionSection> = data?.execution || {};
  const trust: Partial<TrustMeta> = data?.trust || {};

  // Safely default nested arrays that are accessed with .length / .map
  const proceduralBlockers = what_blocks.procedural_blockers || [];
  const missingProof = what_blocks.missing_proof || [];
  const overdueObligations = what_blocks.overdue_obligations || [];
  const residualMaterials = what_we_know.residual_materials || [];
  const complianceGaps = what_is_risky.compliance_gaps || [];
  const top3Actions = what_to_do_next.top_3_actions || [];
  const diagnosticPublications = what_is_reusable.diagnostic_publications || [];
  const packsGenerated = what_is_reusable.packs_generated || [];
  const proofDeliveries = what_is_reusable.proof_deliveries || [];
  const subsidies = execution.subsidies || [];

  const blockerCount = proceduralBlockers.length + missingProof.length + overdueObligations.length;

  const riskEntries = Object.entries(what_is_risky.pollutant_risk || {}).filter(([, v]) => typeof v === 'number') as [
    string,
    number,
  ][];

  return (
    <div className="space-y-4" data-testid="instant-card-view">
      {/* ===== Section 1: Ce qu'on sait ===== */}
      <CardSection
        testId="section-what-we-know"
        title={t('intelligence.what_we_know') || "Ce qu'on sait"}
        icon={<ClipboardList className="w-5 h-5" />}
        headerColor="bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300"
      >
        {/* Identity */}
        <div>
          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
            {t('intelligence.identity') || 'Identite'}
          </h4>
          <KVRow label="Adresse" value={what_we_know.identity?.address as string} />
          <KVRow label="EGID" value={what_we_know.identity?.egid as number} />
          <KVRow label="EGRID" value={what_we_know.identity?.egrid as string} />
          <KVRow label="Parcelle" value={what_we_know.identity?.parcel as string} />
          <KVRow
            label={t('intelligence.construction_year') || 'Annee'}
            value={what_we_know.identity?.construction_year as number}
          />
        </div>

        {/* Physical */}
        <div>
          <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
            {t('intelligence.physical') || 'Physique'}
          </h4>
          <KVRow label={t('intelligence.floors') || 'Etages'} value={what_we_know.physical?.floors as number} />
          <KVRow
            label={t('intelligence.dwellings') || 'Logements'}
            value={what_we_know.physical?.dwellings as number}
          />
          <KVRow
            label={t('intelligence.surface') || 'Surface'}
            value={what_we_know.physical?.surface_m2 ? `${what_we_know.physical.surface_m2} m2` : null}
          />
          <KVRow
            label={t('intelligence.heating') || 'Chauffage'}
            value={what_we_know.physical?.heating_type as string}
          />
        </div>

        {/* Environment */}
        {Object.keys(what_we_know.environment || {}).length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              {t('intelligence.environment') || 'Environnement'}
            </h4>
            {what_we_know.environment?.radon != null && (
              <KVRow label="Radon" value={String(what_we_know.environment.radon)} />
            )}
            {what_we_know.environment?.noise != null && (
              <KVRow label={t('intelligence.noise') || 'Bruit'} value={String(what_we_know.environment.noise)} />
            )}
          </div>
        )}

        {/* Diagnostics */}
        {Object.keys(what_we_know.diagnostics || {}).length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              {t('intelligence.diagnostics') || 'Diagnostics'}
            </h4>
            <p className="text-xs text-slate-600 dark:text-slate-400">
              {what_we_know.diagnostics?.summary
                ? String(what_we_know.diagnostics.summary)
                : t('intelligence.no_diagnostics') || 'Aucun diagnostic importe'}
            </p>
          </div>
        )}

        {/* Residual materials */}
        {residualMaterials.length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              {t('intelligence.residual_materials') || 'Materiaux residuels'}
            </h4>
            {residualMaterials.map((m, i) => (
              <div key={i} className="flex items-center gap-2 py-1 text-xs">
                <span className="font-medium text-slate-700 dark:text-slate-300 capitalize">{m.material_type}</span>
                {m.location && <span className="text-slate-400">— {m.location}</span>}
                <span
                  className={cn(
                    'px-1.5 py-0.5 rounded text-[10px] font-medium',
                    m.status === 'removed'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
                  )}
                >
                  {m.status}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardSection>

      {/* ===== Section 2: Les risques ===== */}
      <CardSection
        testId="section-what-is-risky"
        title={t('intelligence.what_is_risky') || 'Les risques'}
        icon={<AlertTriangle className="w-5 h-5" />}
        headerColor={
          riskEntries.some(([, v]) => v >= 0.8)
            ? 'bg-red-50 text-red-800 dark:bg-red-900/30 dark:text-red-300'
            : 'bg-orange-50 text-orange-800 dark:bg-orange-900/30 dark:text-orange-300'
        }
        badge={
          riskEntries.length > 0 ? (
            <span className="text-[10px] bg-white/60 dark:bg-slate-800/60 px-2 py-0.5 rounded-full font-medium">
              {riskEntries.length} {t('intelligence.pollutants') || 'polluants'}
            </span>
          ) : undefined
        }
      >
        {/* Pollutant risk bars */}
        {riskEntries.length > 0 ? (
          <div className="space-y-2.5">
            {riskEntries.map(([k, v]) => (
              <RiskBar key={k} label={k.replace(/_/g, ' ')} value={v} />
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t('intelligence.no_pollutant_data') || 'Aucune donnee de risque polluant disponible'}
          </p>
        )}

        {/* Environmental score */}
        {what_is_risky.environmental_risk && Object.keys(what_is_risky.environmental_risk).length > 0 && (
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
            <KVRow
              label={t('intelligence.environmental_risk') || 'Score risque environnemental'}
              value={
                typeof what_is_risky.environmental_risk.score === 'number'
                  ? `${what_is_risky.environmental_risk.score}/10`
                  : null
              }
            />
          </div>
        )}

        {/* Compliance gaps */}
        {complianceGaps.length > 0 && (
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800">
            <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              {t('intelligence.compliance_gaps') || 'Non-conformites'}
            </h4>
            <ul className="space-y-1">
              {complianceGaps.map((g, i) => (
                <li key={i} className="text-xs text-red-600 dark:text-red-400 flex items-start gap-1.5">
                  <span className="w-1 h-1 rounded-full bg-red-500 mt-1.5 shrink-0" />
                  {String(g.description || g.label || JSON.stringify(g))}
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardSection>

      {/* ===== Section 3: Ce qui bloque ===== */}
      <CardSection
        testId="section-what-blocks"
        title={t('intelligence.what_blocks') || 'Ce qui bloque'}
        icon={<Ban className="w-5 h-5" />}
        headerColor={
          blockerCount > 0
            ? 'bg-red-50 text-red-800 dark:bg-red-900/30 dark:text-red-300'
            : 'bg-slate-50 text-slate-600 dark:bg-slate-800 dark:text-slate-400'
        }
        badge={
          blockerCount > 0 ? (
            <span className="bg-red-500 text-white text-[10px] px-2 py-0.5 rounded-full font-bold">{blockerCount}</span>
          ) : (
            <span className="bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 text-[10px] px-2 py-0.5 rounded-full font-medium">
              {t('intelligence.clear') || 'OK'}
            </span>
          )
        }
        defaultOpen={blockerCount > 0}
      >
        {blockerCount === 0 ? (
          <p className="text-xs text-green-600 dark:text-green-400">
            {t('intelligence.no_blockers') || 'Aucun blocage identifie'}
          </p>
        ) : (
          <div className="space-y-3">
            {proceduralBlockers.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-red-600 dark:text-red-400 mb-1">
                  {t('intelligence.procedural_blockers') || 'Blocages proceduraux'}
                </h4>
                {proceduralBlockers.map((b, i) => (
                  <div key={i} className="text-xs text-slate-700 dark:text-slate-300 py-0.5" data-testid="blocker-item">
                    {String(b.description || b.label || JSON.stringify(b))}
                  </div>
                ))}
              </div>
            )}
            {missingProof.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-orange-600 dark:text-orange-400 mb-1">
                  {t('intelligence.missing_proof') || 'Preuves manquantes'}
                </h4>
                {missingProof.map((b, i) => (
                  <div key={i} className="text-xs text-slate-700 dark:text-slate-300 py-0.5" data-testid="blocker-item">
                    {String(b.description || b.label || JSON.stringify(b))}
                  </div>
                ))}
              </div>
            )}
            {overdueObligations.length > 0 && (
              <div>
                <h4 className="text-xs font-semibold text-red-600 dark:text-red-400 mb-1">
                  {t('intelligence.overdue_obligations') || 'Obligations en retard'}
                </h4>
                {overdueObligations.map((b, i) => (
                  <div key={i} className="text-xs text-slate-700 dark:text-slate-300 py-0.5" data-testid="blocker-item">
                    {String(b.description || b.label || JSON.stringify(b))}
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </CardSection>

      {/* ===== Section 4: Quoi faire maintenant ===== */}
      <CardSection
        testId="section-what-to-do"
        title={t('intelligence.what_to_do_next') || 'Quoi faire maintenant'}
        icon={<ArrowRight className="w-5 h-5" />}
        headerColor="bg-blue-50 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300"
      >
        {top3Actions.length > 0 ? (
          <div className="space-y-3">
            {top3Actions.map((a, i) => (
              <div
                key={i}
                className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/60 border border-slate-100 dark:border-slate-700"
                data-testid="action-item"
              >
                <div className="flex items-center justify-center w-6 h-6 rounded-full bg-blue-500 text-white text-xs font-bold shrink-0">
                  {i + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-800 dark:text-slate-200">{a.action}</p>
                  <div className="flex items-center gap-3 mt-1.5">
                    <PriorityBadge priority={a.priority} />
                    {a.estimated_cost !== null && (
                      <span className="text-[11px] text-slate-500 dark:text-slate-400">
                        {formatCHF(a.estimated_cost)}
                      </span>
                    )}
                    {a.evidence_needed && (
                      <span className="text-[11px] text-slate-400 dark:text-slate-500 truncate">
                        {a.evidence_needed}
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t('intelligence.no_actions') || 'Aucune action prioritaire identifiee'}
          </p>
        )}

        {/* Renovation plan summary */}
        {execution.renovation_plan_10y && Object.keys(execution.renovation_plan_10y).length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              {t('intelligence.renovation_plan') || 'Plan de renovation (10 ans)'}
            </h4>
            {execution.renovation_plan_10y.total_net_chf != null && (
              <KVRow
                label={t('intelligence.total_cost') || 'Cout total net'}
                value={formatCHF(execution.renovation_plan_10y.total_net_chf as number)}
              />
            )}
            {subsidies.length > 0 && (
              <KVRow
                label={t('intelligence.subsidies') || 'Subventions'}
                value={formatCHF(subsidies.reduce((s, sub) => s + (sub.amount || 0), 0))}
              />
            )}
          </div>
        )}

        {/* Next concrete step */}
        {execution.next_concrete_step && Object.keys(execution.next_concrete_step).length > 0 && (
          <div className="mt-3 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
            <p className="text-xs font-semibold text-blue-700 dark:text-blue-300 mb-1">
              {t('intelligence.next_step') || 'Prochaine etape concrete'}
            </p>
            <p className="text-xs text-blue-600 dark:text-blue-400">
              {String(
                execution.next_concrete_step.description ||
                  execution.next_concrete_step.action ||
                  JSON.stringify(execution.next_concrete_step),
              )}
            </p>
          </div>
        )}
      </CardSection>

      {/* ===== Section 5: Ce qui sera reutilisable ===== */}
      <CardSection
        testId="section-what-is-reusable"
        title={t('intelligence.what_is_reusable') || 'Ce qui sera reutilisable'}
        icon={<Recycle className="w-5 h-5" />}
        headerColor="bg-emerald-50 text-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300"
        defaultOpen={false}
      >
        <div className="space-y-2">
          {diagnosticPublications.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
                {t('intelligence.diagnostic_publications') || 'Publications diagnostiques'}
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                {diagnosticPublications.length} {t('intelligence.available') || 'disponible(s)'}
              </p>
            </div>
          )}
          {packsGenerated.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
                {t('intelligence.packs') || 'Packs generes'}
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-400">{packsGenerated.length} pack(s)</p>
            </div>
          )}
          {proofDeliveries.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">
                {t('intelligence.proof_deliveries') || 'Livraisons de preuves'}
              </h4>
              <p className="text-xs text-slate-600 dark:text-slate-400">
                {proofDeliveries.length} {t('intelligence.deliveries') || 'livraison(s)'}
              </p>
            </div>
          )}
          {diagnosticPublications.length === 0 && packsGenerated.length === 0 && proofDeliveries.length === 0 && (
            <p className="text-xs text-slate-500 dark:text-slate-400 italic">
              {t('intelligence.reusable_empty') || 'Chaque action enrichit le batiment de maniere permanente'}
            </p>
          )}
        </div>
      </CardSection>

      {/* ===== Bottom bar: Grade + Scores + Trust ===== */}
      <div
        className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5"
        data-testid="instant-card-footer"
      >
        <div className="flex items-center gap-6">
          {/* Grade */}
          <GradeBadge grade={data.passport_grade} />

          {/* Trust info */}
          <div className="flex-1 grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="text-center">
              <Shield className="w-4 h-4 mx-auto text-slate-400 mb-0.5" />
              <p className="text-[11px] text-slate-500 dark:text-slate-400">{t('intelligence.trust') || 'Confiance'}</p>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200">
                {Math.round((trust.overall_trust ?? 0) * 100)}%
              </p>
            </div>
            <div className="text-center">
              <Clock className="w-4 h-4 mx-auto text-slate-400 mb-0.5" />
              <p className="text-[11px] text-slate-500 dark:text-slate-400">
                {t('intelligence.freshness') || 'Fraicheur'}
              </p>
              <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 capitalize">{trust.freshness}</p>
            </div>
            {trust.trend && (
              <div className="text-center">
                <TrendingUp className="w-4 h-4 mx-auto text-slate-400 mb-0.5" />
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  {t('intelligence.trend') || 'Tendance'}
                </p>
                <p className="text-sm font-semibold text-slate-800 dark:text-slate-200 capitalize">{trust.trend}</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
