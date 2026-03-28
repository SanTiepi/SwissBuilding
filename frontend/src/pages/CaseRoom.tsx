/**
 * CaseRoom — canonical execution workspace for a single BuildingCase.
 * Action-first: every tab shows what to DO, not just what EXISTS.
 */
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cn } from '@/utils/formatters';
import { buildingCasesApi } from '@/api/buildingCases';
import type { BuildingCaseRead, CaseContext, CaseTimelineEvent } from '@/api/buildingCases';
import { buildingsApi } from '@/api/buildings';
import { toast } from '@/store/toastStore';
import {
  ArrowLeft,
  Loader2,
  ChevronDown,
  Building2,
  Calendar,
  CheckCircle2,
  Circle,
  Clock,
  AlertTriangle,
  Play,
  Pause,
  Eye,
  Target,
  FileText,
  Zap,
  DollarSign,
  HelpCircle,
  ArrowRight,
  Shield,
  Search,
  Package,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CASE_STATES = [
  'draft',
  'in_preparation',
  'ready',
  'in_progress',
  'blocked',
  'completed',
  'cancelled',
  'closed',
] as const;

const STATE_TRANSITIONS: Record<string, string[]> = {
  draft: ['in_preparation', 'ready', 'cancelled'],
  in_preparation: ['ready', 'blocked', 'cancelled'],
  ready: ['in_progress', 'blocked', 'cancelled'],
  in_progress: ['blocked', 'completed', 'cancelled'],
  blocked: ['in_preparation', 'ready', 'in_progress', 'cancelled'],
  completed: ['closed'],
  cancelled: [],
  closed: [],
};

const STATE_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  in_preparation: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  ready: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  in_progress: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  blocked: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  cancelled: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500',
  closed: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
};

const STATE_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  in_preparation: 'En preparation',
  ready: 'Pret',
  in_progress: 'En cours',
  blocked: 'Bloque',
  completed: 'Termine',
  cancelled: 'Annule',
  closed: 'Clos',
};

const TYPE_COLORS: Record<string, string> = {
  works: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  permit: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  authority_submission: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  tender: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  insurance_claim: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
  incident: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  maintenance: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  funding: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  transaction: 'bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400',
  due_diligence: 'bg-lime-100 text-lime-700 dark:bg-lime-900/30 dark:text-lime-400',
  transfer: 'bg-sky-100 text-sky-700 dark:bg-sky-900/30 dark:text-sky-400',
  handoff: 'bg-fuchsia-100 text-fuchsia-700 dark:bg-fuchsia-900/30 dark:text-fuchsia-400',
  control: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-400',
  other: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
};

const PRIORITY_COLORS: Record<string, string> = {
  low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const PRIORITY_LABELS: Record<string, string> = {
  low: 'Faible',
  medium: 'Moyen',
  high: 'Haute',
  critical: 'Critique',
};

const POLLUTANT_LABELS: Record<string, string> = {
  asbestos: 'Amiante',
  pcb: 'PCB',
  lead: 'Plomb',
  hap: 'HAP',
  radon: 'Radon',
  pfas: 'PFAS',
};

type TabKey = 'overview' | 'scope' | 'truth' | 'actions' | 'forms' | 'finance' | 'questions';

const TABS: { key: TabKey; label: string; icon: React.ElementType }[] = [
  { key: 'overview', label: "Vue d'ensemble", icon: Eye },
  { key: 'scope', label: 'Perimetre', icon: Target },
  { key: 'truth', label: 'Verite & Manques', icon: Search },
  { key: 'actions', label: 'Actions & Rituels', icon: Zap },
  { key: 'forms', label: 'Formulaires & Packs', icon: FileText },
  { key: 'finance', label: 'Finance', icon: DollarSign },
  { key: 'questions', label: 'Questions', icon: HelpCircle },
];

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatDate(d: string | null | undefined): string {
  if (!d) return '-';
  try {
    return new Date(d).toLocaleDateString('fr-CH');
  } catch {
    return '-';
  }
}

function daysBetween(start: string | null | undefined, end: string | null | undefined): number | null {
  if (!start) return null;
  const s = new Date(start).getTime();
  const e = end ? new Date(end).getTime() : Date.now();
  return Math.max(0, Math.round((e - s) / 86400000));
}

// ---------------------------------------------------------------------------
// State progress dots
// ---------------------------------------------------------------------------

function StateProgressDots({ currentState }: { currentState: string }) {
  const mainStates = CASE_STATES.filter((s) => s !== 'cancelled' && s !== 'blocked');
  const currentIdx = mainStates.indexOf(currentState as (typeof mainStates)[number]);
  const isCancelled = currentState === 'cancelled';
  const isBlocked = currentState === 'blocked';

  return (
    <div className="flex items-center gap-1">
      {mainStates.map((state, idx) => {
        const isActive = state === currentState;
        const isPast = !isCancelled && !isBlocked && currentIdx >= 0 && idx < currentIdx;
        const isFuture = !isActive && !isPast;

        return (
          <div key={state} className="flex items-center gap-1">
            <div className="flex flex-col items-center">
              <div
                className={cn(
                  'w-3 h-3 rounded-full border-2 transition-colors',
                  isActive && 'border-blue-500 bg-blue-500',
                  isPast && 'border-green-500 bg-green-500',
                  isFuture && 'border-gray-300 dark:border-gray-600 bg-transparent',
                  isCancelled && isActive && 'border-gray-400 bg-gray-400',
                  isBlocked && isActive && 'border-red-500 bg-red-500',
                )}
              />
              <span className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5 whitespace-nowrap">
                {STATE_LABELS[state] || state}
              </span>
            </div>
            {idx < mainStates.length - 1 && (
              <div className={cn('w-6 h-0.5 mb-4', isPast ? 'bg-green-400' : 'bg-gray-200 dark:bg-gray-700')} />
            )}
          </div>
        );
      })}
      {(isCancelled || isBlocked) && (
        <div className="ml-2 flex flex-col items-center">
          <div className={cn('w-3 h-3 rounded-full', isCancelled ? 'bg-gray-400' : 'bg-red-500')} />
          <span className="text-[10px] text-gray-400 dark:text-gray-500 mt-0.5">{STATE_LABELS[currentState]}</span>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Advance dropdown
// ---------------------------------------------------------------------------

function AdvanceDropdown({
  currentState,
  onAdvance,
  isAdvancing,
}: {
  currentState: string;
  onAdvance: (newState: string) => void;
  isAdvancing: boolean;
}) {
  const [open, setOpen] = useState(false);
  const transitions = STATE_TRANSITIONS[currentState] || [];

  if (transitions.length === 0) return null;

  return (
    <div className="relative">
      <button
        onClick={() => setOpen(!open)}
        disabled={isAdvancing}
        className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 transition-colors text-sm font-medium"
      >
        {isAdvancing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
        Avancer
        <ChevronDown className="w-4 h-4" />
      </button>
      {open && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setOpen(false)} />
          <div className="absolute right-0 mt-1 z-20 w-48 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-1">
            {transitions.map((state) => (
              <button
                key={state}
                onClick={() => {
                  onAdvance(state);
                  setOpen(false);
                }}
                className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 flex items-center gap-2"
              >
                <span
                  className={cn(
                    'inline-block w-2 h-2 rounded-full',
                    STATE_COLORS[state]?.includes('bg-') ? STATE_COLORS[state].split(' ')[0] : 'bg-gray-300',
                  )}
                />
                {STATE_LABELS[state] || state}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Vue d'ensemble (Overview)
// ---------------------------------------------------------------------------

function OverviewTab({
  caseData,
  context: _context,
  timeline,
}: {
  caseData: BuildingCaseRead;
  context: CaseContext | undefined;
  timeline: CaseTimelineEvent[] | undefined;
}) {
  void _context; // reserved for future scope-scoped data
  const steps = (caseData.steps || []) as { name?: string; status?: string }[];
  const completedSteps = steps.filter((s) => s.status === 'completed').length;
  const daysActive = daysBetween(caseData.actual_start || caseData.created_at, caseData.actual_end);

  return (
    <div className="space-y-6">
      {/* Progress */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Progression
        </h3>
        <StateProgressDots currentState={caseData.state} />
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <MetricCard label="Jours actifs" value={daysActive !== null ? String(daysActive) : '-'} icon={Clock} />
        <MetricCard label="Etapes terminees" value={`${completedSteps}/${steps.length}`} icon={CheckCircle2} />
        <MetricCard label="Zones concernees" value={String(caseData.spatial_scope_ids?.length ?? 0)} icon={Target} />
        <MetricCard label="Polluants" value={String(caseData.pollutant_scope?.length ?? 0)} icon={AlertTriangle} />
      </div>

      {/* Steps detail */}
      {steps.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
            Etapes du dossier
          </h3>
          <div className="space-y-2">
            {steps.map((step, idx) => (
              <div key={idx} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50">
                {step.status === 'completed' ? (
                  <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
                ) : step.status === 'in_progress' ? (
                  <Clock className="w-5 h-5 text-blue-500 flex-shrink-0" />
                ) : (
                  <Circle className="w-5 h-5 text-gray-300 dark:text-gray-600 flex-shrink-0" />
                )}
                <span className="text-sm text-gray-700 dark:text-gray-300 flex-1">
                  {step.name || `Etape ${idx + 1}`}
                </span>
                <span
                  className={cn(
                    'text-xs px-2 py-0.5 rounded-full',
                    step.status === 'completed'
                      ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                      : step.status === 'in_progress'
                        ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                        : 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500',
                  )}
                >
                  {step.status || 'pending'}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Linked entities */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {caseData.intervention_id && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-1">
              <Shield className="w-4 h-4" />
              Intervention liee
            </div>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">{caseData.intervention_id}</p>
          </div>
        )}
        {caseData.tender_id && (
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 mb-1">
              <Package className="w-4 h-4" />
              Appel d'offres lie
            </div>
            <p className="text-sm font-medium text-gray-700 dark:text-gray-300 truncate">{caseData.tender_id}</p>
          </div>
        )}
      </div>

      {/* Timeline */}
      {timeline && timeline.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
            Chronologie
          </h3>
          <div className="space-y-3">
            {timeline.map((ev, idx) => (
              <div key={idx} className="flex items-start gap-3">
                <div className="w-2 h-2 rounded-full bg-blue-400 mt-1.5 flex-shrink-0" />
                <div className="flex-1">
                  <p className="text-sm text-gray-700 dark:text-gray-300">{ev.label}</p>
                  <p className="text-xs text-gray-400 dark:text-gray-500">{formatDate(ev.timestamp)}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function MetricCard({ label, value, icon: Icon }: { label: string; value: string; icon: React.ElementType }) {
  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-4">
      <div className="flex items-center gap-2 text-gray-400 dark:text-gray-500 mb-2">
        <Icon className="w-4 h-4" />
        <span className="text-xs font-medium uppercase tracking-wider">{label}</span>
      </div>
      <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Perimetre (Scope)
// ---------------------------------------------------------------------------

function ScopeTab({ caseData }: { caseData: BuildingCaseRead }) {
  const zones = caseData.spatial_scope_ids || [];
  const pollutants = caseData.pollutant_scope || [];

  return (
    <div className="space-y-6">
      {/* Spatial scope */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Perimetre spatial
        </h3>
        {zones.length === 0 ? (
          <div className="text-center py-8 text-gray-400 dark:text-gray-500">
            <Target className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Aucune zone definie pour ce dossier</p>
            <p className="text-xs mt-1">Definissez les zones concernees pour cadrer le perimetre</p>
          </div>
        ) : (
          <div className="space-y-2">
            {zones.map((zoneId) => (
              <div key={zoneId} className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50">
                <div className="w-2 h-2 rounded-full bg-blue-400" />
                <span className="text-sm text-gray-700 dark:text-gray-300 font-mono">{zoneId}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pollutant scope */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Polluants concernes
        </h3>
        {pollutants.length === 0 ? (
          <div className="text-center py-8 text-gray-400 dark:text-gray-500">
            <AlertTriangle className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Aucun polluant specifie</p>
          </div>
        ) : (
          <div className="flex flex-wrap gap-2">
            {pollutants.map((p) => (
              <span
                key={p}
                className="inline-flex items-center px-3 py-1.5 rounded-full text-sm font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400"
              >
                {POLLUTANT_LABELS[p] || p}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Scope health */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Sante du perimetre
        </h3>
        <div className="space-y-3">
          <ScopeCheckItem
            ok={zones.length > 0}
            label="Zones definies"
            hint={zones.length > 0 ? `${zones.length} zone(s)` : 'A definir'}
          />
          <ScopeCheckItem
            ok={pollutants.length > 0}
            label="Polluants specifies"
            hint={pollutants.length > 0 ? pollutants.map((p) => POLLUTANT_LABELS[p] || p).join(', ') : 'A specifier'}
          />
          <ScopeCheckItem
            ok={!!caseData.planned_start && !!caseData.planned_end}
            label="Dates planifiees"
            hint={
              caseData.planned_start && caseData.planned_end
                ? `${formatDate(caseData.planned_start)} - ${formatDate(caseData.planned_end)}`
                : 'A planifier'
            }
          />
        </div>
      </div>
    </div>
  );
}

function ScopeCheckItem({ ok, label, hint }: { ok: boolean; label: string; hint: string }) {
  return (
    <div className="flex items-center gap-3 p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50">
      {ok ? (
        <CheckCircle2 className="w-5 h-5 text-green-500 flex-shrink-0" />
      ) : (
        <AlertTriangle className="w-5 h-5 text-amber-500 flex-shrink-0" />
      )}
      <div className="flex-1">
        <p className="text-sm font-medium text-gray-700 dark:text-gray-300">{label}</p>
        <p className="text-xs text-gray-400 dark:text-gray-500">{hint}</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Verite & Manques (Truth & Missing)
// ---------------------------------------------------------------------------

function TruthTab({ caseData: _caseData }: { caseData: BuildingCaseRead }) {
  void _caseData;
  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Preuves & Evidences
        </h3>
        <div className="text-center py-8 text-gray-400 dark:text-gray-500">
          <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Analyse de verite scopee au dossier</p>
          <p className="text-xs mt-1">Les claims, evidences, manques et contradictions de ce perimetre</p>
        </div>
      </div>

      {/* Action prompt */}
      <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-4">
        <div className="flex items-start gap-3">
          <Zap className="w-5 h-5 text-blue-500 mt-0.5 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-blue-700 dark:text-blue-300">Prochaine action</p>
            <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
              Lancez une analyse de completude scopee pour identifier les manques dans ce dossier.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Actions & Rituels
// ---------------------------------------------------------------------------

function ActionsTab({ caseData }: { caseData: BuildingCaseRead }) {
  const steps = (caseData.steps || []) as { name?: string; status?: string }[];
  const pendingSteps = steps.filter((s) => s.status !== 'completed');

  return (
    <div className="space-y-6">
      {/* Ritual buttons */}
      <div className="flex flex-wrap gap-3">
        <button
          className="inline-flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors text-sm font-medium"
          onClick={() => toast('Rituel de validation lance', 'success')}
        >
          <CheckCircle2 className="w-4 h-4" />
          Valider
        </button>
        <button
          className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors text-sm font-medium"
          onClick={() => toast('Rituel de gel lance', 'success')}
        >
          <Pause className="w-4 h-4" />
          Geler
        </button>
        <button
          className="inline-flex items-center gap-2 px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700 transition-colors text-sm font-medium"
          onClick={() => toast('Rituel de publication lance', 'success')}
        >
          <ArrowRight className="w-4 h-4" />
          Publier
        </button>
      </div>

      {/* Pending steps as actions */}
      {pendingSteps.length > 0 && (
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
          <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
            Etapes en attente
          </h3>
          <div className="space-y-2">
            {pendingSteps.map((step, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50"
              >
                <div className="flex items-center gap-3">
                  <Circle className="w-5 h-5 text-gray-300 dark:text-gray-600" />
                  <span className="text-sm text-gray-700 dark:text-gray-300">{step.name || `Etape ${idx + 1}`}</span>
                </div>
                <span className="text-xs text-gray-400">{step.status || 'pending'}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Action queue placeholder */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          File d'actions
        </h3>
        <div className="text-center py-8 text-gray-400 dark:text-gray-500">
          <Zap className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Actions filtrees pour ce dossier</p>
          <p className="text-xs mt-1">Les actions generees seront scopees au perimetre du dossier</p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Formulaires & Packs
// ---------------------------------------------------------------------------

function FormsTab({ caseData: _caseData }: { caseData: BuildingCaseRead }) {
  void _caseData;
  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Formulaires applicables
        </h3>
        <div className="text-center py-8 text-gray-400 dark:text-gray-500">
          <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Formulaires de ce dossier</p>
          <p className="text-xs mt-1">Les formulaires reglementaires applicables au type et perimetre du dossier</p>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Packs generes
        </h3>
        <div className="text-center py-8 text-gray-400 dark:text-gray-500">
          <Package className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Packs autorite et soumissions</p>
          <p className="text-xs mt-1">Les packs de documents compiles pour ce dossier</p>
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Finance
// ---------------------------------------------------------------------------

function FinanceTab({ caseData }: { caseData: BuildingCaseRead }) {
  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Resume financier
        </h3>
        <div className="text-center py-8 text-gray-400 dark:text-gray-500">
          <DollarSign className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Entrees financieres liees a ce dossier</p>
          <p className="text-xs mt-1">Devis, couts, factures et budgets pour ce dossier</p>
        </div>
      </div>

      {caseData.tender_id && (
        <div className="bg-cyan-50 dark:bg-cyan-900/20 border border-cyan-200 dark:border-cyan-800 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <Package className="w-5 h-5 text-cyan-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-cyan-700 dark:text-cyan-300">Appel d'offres lie</p>
              <p className="text-xs text-cyan-600 dark:text-cyan-400 mt-1">
                Les devis de l'appel d'offres sont disponibles dans l'onglet Tender du batiment.
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tab: Questions
// ---------------------------------------------------------------------------

function QuestionsTab({ caseData: _caseData }: { caseData: BuildingCaseRead }) {
  void _caseData;
  return (
    <div className="space-y-6">
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Verdicts SafeToX
        </h3>
        <div className="text-center py-8 text-gray-400 dark:text-gray-500">
          <HelpCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
          <p className="text-sm">Verdicts scopes a ce dossier</p>
          <p className="text-xs mt-1">Peut-on demarrer ? Peut-on lancer l'appel d'offres ? Peut-on publier ?</p>
        </div>
      </div>

      {/* Intent queries */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <h3 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-4">
          Requetes d'intention
        </h3>
        <div className="space-y-2">
          {['safe_to_start', 'safe_to_tender', 'safe_to_publish'].map((intent) => (
            <div
              key={intent}
              className="flex items-center justify-between p-3 rounded-lg bg-gray-50 dark:bg-gray-900/50 cursor-pointer hover:bg-gray-100 dark:hover:bg-gray-800"
            >
              <span className="text-sm text-gray-700 dark:text-gray-300">
                {intent.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
              </span>
              <ArrowRight className="w-4 h-4 text-gray-400" />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

export default function CaseRoom() {
  const { caseId } = useParams<{ caseId: string }>();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<TabKey>('overview');

  // Fetch case detail
  const {
    data: caseData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['case-detail', caseId],
    queryFn: () => buildingCasesApi.getDetail(caseId!),
    enabled: !!caseId,
  });

  // Fetch context
  const { data: context } = useQuery({
    queryKey: ['case-context', caseId],
    queryFn: () => buildingCasesApi.getContext(caseId!),
    enabled: !!caseId,
  });

  // Fetch timeline
  const { data: timeline } = useQuery({
    queryKey: ['case-timeline', caseId],
    queryFn: () => buildingCasesApi.getTimeline(caseId!),
    enabled: !!caseId,
  });

  // Fetch building info
  const { data: building } = useQuery({
    queryKey: ['building-mini', caseData?.building_id],
    queryFn: () => buildingsApi.get(caseData!.building_id),
    enabled: !!caseData?.building_id,
  });

  // Advance mutation
  const advanceMutation = useMutation({
    mutationFn: (newState: string) => buildingCasesApi.advance(caseId!, newState),
    onSuccess: (updated) => {
      queryClient.setQueryData(['case-detail', caseId], updated);
      queryClient.invalidateQueries({ queryKey: ['case-context', caseId] });
      queryClient.invalidateQueries({ queryKey: ['case-timeline', caseId] });
      queryClient.invalidateQueries({ queryKey: ['org-cases'] });
      toast(`Dossier avance: ${STATE_LABELS[updated.state] || updated.state}`, 'success');
    },
    onError: (err: unknown) => {
      const msg = err instanceof Error ? err.message : 'Erreur lors de la transition';
      toast(msg, 'error');
    },
  });

  // Loading
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  // Error / not found
  if (error || !caseData) {
    return (
      <div className="space-y-4">
        <Link
          to="/cases"
          className="inline-flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour aux dossiers
        </Link>
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
          <AlertTriangle className="w-10 h-10 text-red-400 mx-auto mb-3" />
          <h3 className="text-lg font-semibold text-red-700 dark:text-red-300">Dossier introuvable</h3>
          <p className="text-sm text-red-600 dark:text-red-400 mt-2">
            {error instanceof Error ? error.message : "Ce dossier n'existe pas ou n'est plus accessible."}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Back link */}
      <Link
        to="/cases"
        className="inline-flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
      >
        <ArrowLeft className="w-4 h-4" />
        Retour aux dossiers
      </Link>

      {/* Header */}
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
          <div className="space-y-2">
            {/* Title */}
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">{caseData.title}</h1>

            {/* Badges */}
            <div className="flex flex-wrap items-center gap-2">
              <span
                className={cn(
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                  TYPE_COLORS[caseData.case_type] || TYPE_COLORS.other,
                )}
              >
                {caseData.case_type.replace(/_/g, ' ')}
              </span>
              <span
                className={cn(
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                  STATE_COLORS[caseData.state] || STATE_COLORS.draft,
                )}
              >
                {STATE_LABELS[caseData.state] || caseData.state}
              </span>
              <span
                className={cn(
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                  PRIORITY_COLORS[caseData.priority ?? 'medium'] || PRIORITY_COLORS.medium,
                )}
              >
                {PRIORITY_LABELS[caseData.priority ?? 'medium'] || caseData.priority}
              </span>
            </div>

            {/* Building link */}
            {building && (
              <Link
                to={`/buildings/${caseData.building_id}`}
                className="inline-flex items-center gap-2 text-sm text-blue-600 dark:text-blue-400 hover:underline"
              >
                <Building2 className="w-4 h-4" />
                {building.address || building.city || 'Batiment'}
              </Link>
            )}

            {/* Dates */}
            <div className="flex flex-wrap items-center gap-4 text-xs text-gray-500 dark:text-gray-400">
              {(caseData.planned_start || caseData.planned_end) && (
                <span className="inline-flex items-center gap-1">
                  <Calendar className="w-3.5 h-3.5" />
                  Prevu: {formatDate(caseData.planned_start)} - {formatDate(caseData.planned_end)}
                </span>
              )}
              {(caseData.actual_start || caseData.actual_end) && (
                <span className="inline-flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5" />
                  Effectif: {formatDate(caseData.actual_start)} - {formatDate(caseData.actual_end)}
                </span>
              )}
            </div>
          </div>

          {/* Advance button */}
          <div className="flex-shrink-0">
            <AdvanceDropdown
              currentState={caseData.state}
              onAdvance={(s) => advanceMutation.mutate(s)}
              isAdvancing={advanceMutation.isPending}
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="border-b border-gray-200 dark:border-gray-700 overflow-x-auto">
        <nav className="flex gap-1 -mb-px min-w-max">
          {TABS.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.key;
            return (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={cn(
                  'inline-flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap',
                  isActive
                    ? 'border-red-600 text-red-600 dark:text-red-400 dark:border-red-400'
                    : 'border-transparent text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300 hover:border-gray-300 dark:hover:border-gray-600',
                )}
              >
                <Icon className="w-4 h-4" />
                {tab.label}
              </button>
            );
          })}
        </nav>
      </div>

      {/* Tab content */}
      <div>
        {activeTab === 'overview' && <OverviewTab caseData={caseData} context={context} timeline={timeline} />}
        {activeTab === 'scope' && <ScopeTab caseData={caseData} />}
        {activeTab === 'truth' && <TruthTab caseData={caseData} />}
        {activeTab === 'actions' && <ActionsTab caseData={caseData} />}
        {activeTab === 'forms' && <FormsTab caseData={caseData} />}
        {activeTab === 'finance' && <FinanceTab caseData={caseData} />}
        {activeTab === 'questions' && <QuestionsTab caseData={caseData} />}
      </div>
    </div>
  );
}
