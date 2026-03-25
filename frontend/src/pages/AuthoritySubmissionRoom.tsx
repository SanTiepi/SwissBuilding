import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { permitProceduresApi } from '@/api/permitProcedures';
import type { Procedure, ProcedureStep } from '@/api/permitProcedures';
import ProcedureCard from '@/components/building-detail/ProcedureCard';
import AuthorityRequestCard from '@/components/building-detail/AuthorityRequestCard';
import ProofDeliveryHistory from '@/components/building-detail/ProofDeliveryHistory';
import AuthorityProofSet from '@/components/building-detail/AuthorityProofSet';
import type { ProofRequirement } from '@/components/building-detail/AuthorityProofSet';
import {
  ArrowLeft,
  Loader2,
  AlertTriangle,
  Send,
  FileText,
  ClipboardList,
  ShieldCheck,
} from 'lucide-react';

// ─── Helpers ─────────────────────────────────────────────────────────

function findActiveStep(steps: ProcedureStep[]): ProcedureStep | null {
  return steps.find((s) => s.status === 'active') ?? null;
}

function buildProofRequirements(step: ProcedureStep | null): ProofRequirement[] {
  if (!step) return [];
  return step.required_documents.map((label, idx) => ({
    label,
    document_id: idx < step.linked_document_ids.length ? step.linked_document_ids[idx] : null,
  }));
}

function getNextAction(
  procedure: Procedure,
  activeStep: ProcedureStep | null,
  t: (key: string) => string,
): { label: string; type: 'submit' | 'respond' | 'send_proof' | 'wait' } {
  const openRequests = procedure.authority_requests.filter(
    (r) => r.status === 'open' || r.status === 'overdue',
  );

  if (openRequests.length > 0) {
    return { label: t('authority_room.action_respond_request'), type: 'respond' };
  }

  if (procedure.status === 'draft') {
    return { label: t('authority_room.action_submit'), type: 'submit' };
  }

  if (activeStep) {
    const missing = activeStep.required_documents.length - activeStep.linked_document_ids.length;
    if (missing > 0) {
      return { label: t('authority_room.action_send_proof'), type: 'send_proof' };
    }
  }

  return { label: t('authority_room.action_wait'), type: 'wait' };
}

const ACTION_ICONS: Record<string, React.ElementType> = {
  submit: Send,
  respond: AlertTriangle,
  send_proof: FileText,
  wait: ClipboardList,
};

const ACTION_COLORS: Record<string, string> = {
  submit: 'bg-blue-600 text-white hover:bg-blue-700',
  respond: 'bg-orange-600 text-white hover:bg-orange-700',
  send_proof: 'bg-indigo-600 text-white hover:bg-indigo-700',
  wait: 'bg-gray-200 text-gray-600 dark:bg-slate-700 dark:text-slate-300 cursor-default',
};

// ─── Main component ──────────────────────────────────────────────────

export default function AuthoritySubmissionRoom() {
  const { buildingId, procedureId } = useParams<{ buildingId: string; procedureId: string }>();
  const { t } = useTranslation();

  const {
    data: procedure,
    isLoading,
    error,
  } = useQuery<Procedure>({
    queryKey: ['procedure', procedureId],
    queryFn: () => permitProceduresApi.getProcedure(procedureId!),
    enabled: !!procedureId,
    staleTime: 30_000,
  });

  // ─── Loading state ──────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="authority-room-loading">
        <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
      </div>
    );
  }

  // ─── Error state ────────────────────────────────────────────────
  if (error || !procedure) {
    return (
      <div className="max-w-3xl mx-auto p-6" data-testid="authority-room-error">
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
          <AlertTriangle className="w-8 h-8 text-red-500 mx-auto mb-2" />
          <p className="text-sm text-red-700 dark:text-red-300">{t('authority_room.load_error')}</p>
        </div>
      </div>
    );
  }

  const activeStep = findActiveStep(procedure.steps);
  const proofRequirements = buildProofRequirements(activeStep);
  const nextAction = getNextAction(procedure, activeStep, t);
  const NextActionIcon = ACTION_ICONS[nextAction.type] || ClipboardList;
  const openRequests = procedure.authority_requests.filter(
    (r) => r.status === 'open' || r.status === 'overdue',
  );
  return (
    <div className="max-w-4xl mx-auto px-4 py-6 space-y-6" data-testid="authority-submission-room">
      {/* Back nav */}
      <Link
        to={`/buildings/${buildingId}`}
        className="inline-flex items-center gap-1.5 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
      >
        <ArrowLeft className="w-4 h-4" />
        {t('authority_room.back_to_building')}
      </Link>

      {/* Page header */}
      <div className="flex items-start justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            {t('authority_room.title')}
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{procedure.title}</p>
        </div>
      </div>

      {/* ─── 1. Submission summary ──────────────────────────────── */}
      <section data-testid="submission-summary">
        <ProcedureCard procedure={procedure} defaultExpanded />
      </section>

      {/* ─── 2. Current step ───────────────────────────────────── */}
      {activeStep && (
        <section
          className="bg-blue-50 dark:bg-blue-900/10 border border-blue-200 dark:border-blue-800 rounded-xl p-4"
          data-testid="current-step"
        >
          <h3 className="text-sm font-semibold text-blue-900 dark:text-blue-200 mb-1">
            {t('authority_room.current_step')}
          </h3>
          <p className="text-sm text-blue-800 dark:text-blue-300">{activeStep.name}</p>
          {activeStep.due_date && (
            <p className="text-xs text-blue-600 dark:text-blue-400 mt-1">
              {t('authority_room.due_date')}: {activeStep.due_date.slice(0, 10)}
            </p>
          )}
        </section>
      )}

      {/* ─── 3. Required proof set ─────────────────────────────── */}
      <AuthorityProofSet
        requirements={proofRequirements}
        stepName={activeStep?.name || t('authority_room.no_active_step')}
      />

      {/* ─── 4. Sent & acknowledged items ──────────────────────── */}
      {buildingId && <ProofDeliveryHistory buildingId={buildingId} />}

      {/* ─── 5. Complement loop ────────────────────────────────── */}
      {openRequests.length > 0 && (
        <section data-testid="complement-loop">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-orange-500" />
            {t('authority_room.complement_loop')}
          </h3>
          <div className="space-y-3">
            {openRequests.map((req) => (
              <AuthorityRequestCard key={req.id} request={req} />
            ))}
          </div>
        </section>
      )}

      {/* ─── 6. Next move ──────────────────────────────────────── */}
      <section
        className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-4"
        data-testid="next-move"
      >
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-3">
          {t('authority_room.next_move')}
        </h3>
        <button
          className={cn(
            'inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
            ACTION_COLORS[nextAction.type],
          )}
          disabled={nextAction.type === 'wait'}
          data-testid="next-action-button"
        >
          <NextActionIcon className="w-4 h-4" />
          {nextAction.label}
        </button>
      </section>
    </div>
  );
}
