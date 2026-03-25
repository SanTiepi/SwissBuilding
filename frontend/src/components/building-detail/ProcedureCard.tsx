import { useState } from 'react';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import type { Procedure, ProcedureStep, ProcedureStatus, StepStatus } from '@/api/permitProcedures';
import { ChevronDown, ChevronUp, AlertTriangle, FileText, CheckCircle2, Clock, XCircle } from 'lucide-react';
import AuthorityRequestCard from './AuthorityRequestCard';

// ─── Status colour maps ──────────────────────────────────────────────

const PROCEDURE_STATUS_COLORS: Record<ProcedureStatus, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
  submitted: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  under_review: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  complement_requested: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  approved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  expired: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-400',
  withdrawn: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-400',
};

const STEP_STATUS_COLORS: Record<StepStatus, string> = {
  pending: 'bg-gray-300 dark:bg-slate-500',
  active: 'bg-blue-500 dark:bg-blue-400',
  completed: 'bg-green-500 dark:bg-green-400',
  skipped: 'bg-gray-300 dark:bg-slate-500',
  blocked: 'bg-red-500 dark:bg-red-400',
};

const STEP_LINE_COLORS: Record<StepStatus, string> = {
  pending: 'bg-gray-200 dark:bg-slate-600',
  active: 'bg-blue-200 dark:bg-blue-900/40',
  completed: 'bg-green-200 dark:bg-green-900/40',
  skipped: 'bg-gray-200 dark:bg-slate-600',
  blocked: 'bg-red-200 dark:bg-red-900/40',
};

// ─── Helpers ─────────────────────────────────────────────────────────

function formatDateShort(d: string | null): string {
  if (!d) return '-';
  return d.slice(0, 10);
}

function isDueSoon(dueDate: string | null): boolean {
  if (!dueDate) return false;
  const diff = new Date(dueDate).getTime() - Date.now();
  return diff > 0 && diff < 7 * 24 * 60 * 60 * 1000;
}

function isOverdue(dueDate: string | null): boolean {
  if (!dueDate) return false;
  return new Date(dueDate).getTime() < Date.now();
}

// ─── Sub-components ──────────────────────────────────────────────────

function StatusBadge({ status, colorMap }: { status: string; colorMap: Record<string, string> }) {
  return (
    <span
      data-testid={`badge-${status}`}
      className={cn('inline-block px-2 py-0.5 text-xs font-medium rounded-full', colorMap[status] || colorMap.draft)}
    >
      {status.replace(/_/g, ' ')}
    </span>
  );
}

function StepTimeline({ steps }: { steps: ProcedureStep[] }) {
  const { t } = useTranslation();
  const sorted = [...steps].sort((a, b) => a.step_order - b.step_order);

  return (
    <div className="space-y-0" data-testid="step-timeline">
      {sorted.map((step, idx) => {
        const isLast = idx === sorted.length - 1;
        const isActive = step.status === 'active';
        const linkedCount = step.linked_document_ids.length;
        const requiredCount = step.required_documents.length;
        const missingDocs = requiredCount - linkedCount;

        return (
          <div key={step.id} className="flex gap-3" data-testid={`step-${step.id}`}>
            {/* Vertical line + dot */}
            <div className="flex flex-col items-center">
              <div className={cn('w-3 h-3 rounded-full flex-shrink-0 mt-1', STEP_STATUS_COLORS[step.status])} />
              {!isLast && <div className={cn('w-0.5 flex-1 min-h-[24px]', STEP_LINE_COLORS[step.status])} />}
            </div>

            {/* Content */}
            <div
              className={cn(
                'flex-1 pb-4',
                isActive && 'bg-blue-50 dark:bg-blue-900/10 -mx-2 px-2 py-2 rounded-lg border border-blue-200 dark:border-blue-800',
              )}
            >
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className={cn(
                    'text-sm font-medium',
                    isActive ? 'text-blue-900 dark:text-blue-200' : 'text-gray-900 dark:text-white',
                  )}
                >
                  {step.name}
                </span>
                <StatusBadge status={step.status} colorMap={STEP_STATUS_COLORS_TEXT} />
                {step.due_date && (
                  <span
                    className={cn(
                      'inline-flex items-center gap-1 text-xs',
                      isOverdue(step.due_date)
                        ? 'text-red-600 dark:text-red-400 font-medium'
                        : isDueSoon(step.due_date)
                          ? 'text-orange-600 dark:text-orange-400'
                          : 'text-gray-500 dark:text-slate-400',
                    )}
                  >
                    <Clock className="w-3 h-3" />
                    {formatDateShort(step.due_date)}
                  </span>
                )}
              </div>

              {/* Required documents */}
              {requiredCount > 0 && (
                <div className="mt-1.5 flex flex-wrap gap-1.5">
                  {step.required_documents.map((doc, di) => {
                    const isLinked = di < linkedCount;
                    return (
                      <span
                        key={di}
                        className={cn(
                          'inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded',
                          isLinked
                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                            : 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
                        )}
                      >
                        {isLinked ? (
                          <CheckCircle2 className="w-3 h-3" />
                        ) : (
                          <FileText className="w-3 h-3" />
                        )}
                        {doc}
                      </span>
                    );
                  })}
                  {missingDocs > 0 && (
                    <span className="text-xs text-orange-600 dark:text-orange-400">
                      {missingDocs} {t('procedure.missing_docs') || 'missing'}
                    </span>
                  )}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}

// Text-based status colours for step badges (different from dot colours)
const STEP_STATUS_COLORS_TEXT: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  active: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  skipped: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
  blocked: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

// ─── Main component ──────────────────────────────────────────────────

interface ProcedureCardProps {
  procedure: Procedure;
  defaultExpanded?: boolean;
  onSubmit?: (id: string) => void;
  onRespondToRequest?: (requestId: string, text: string) => void;
}

export default function ProcedureCard({ procedure, defaultExpanded = false, onSubmit, onRespondToRequest }: ProcedureCardProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(defaultExpanded);

  const openRequests = procedure.authority_requests.filter((r) => r.status === 'open' || r.status === 'overdue');

  return (
    <div
      data-testid={`procedure-card-${procedure.id}`}
      className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden"
    >
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 text-left hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
        data-testid="procedure-card-toggle"
      >
        <div className="flex items-center gap-3 flex-wrap min-w-0">
          <span className="inline-block px-2 py-0.5 text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-600 dark:text-slate-200 rounded">
            {t(`procedure.type.${procedure.procedure_type}`) || procedure.procedure_type.replace(/_/g, ' ')}
          </span>
          <StatusBadge status={procedure.status} colorMap={PROCEDURE_STATUS_COLORS} />
          <span className="text-sm font-semibold text-gray-900 dark:text-white truncate">{procedure.title}</span>
          {procedure.reference_number && (
            <span className="text-xs text-gray-500 dark:text-slate-400">#{procedure.reference_number}</span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0 ml-2">
          {procedure.blocks_activities && (
            <span
              className="inline-flex items-center gap-1 text-xs font-medium text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 px-2 py-0.5 rounded-full"
              data-testid="blocker-badge"
            >
              <AlertTriangle className="w-3 h-3" />
              {t('procedure.blocker') || 'Blocker'}
            </span>
          )}
          {openRequests.length > 0 && (
            <span className="inline-flex items-center gap-1 text-xs font-medium text-orange-700 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20 px-2 py-0.5 rounded-full">
              {openRequests.length} {t('procedure.open_requests') || 'open'}
            </span>
          )}
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </div>
      </button>

      {/* Blocker alert */}
      {expanded && procedure.blocks_activities && (
        <div
          className="mx-4 mb-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-center gap-2 text-sm text-red-700 dark:text-red-300"
          data-testid="blocker-alert"
        >
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {t('procedure.blocker_message') || 'This procedure blocks building activities until resolved.'}
        </div>
      )}

      {/* Expanded content */}
      {expanded && (
        <div className="px-4 pb-4 space-y-4">
          {/* Authority info */}
          <div className="flex items-center gap-4 text-sm text-gray-600 dark:text-slate-300">
            <span>
              <span className="text-gray-500 dark:text-slate-400">{t('procedure.authority') || 'Authority'}:</span>{' '}
              {procedure.authority_name}
            </span>
            {procedure.submitted_at && (
              <span>
                <span className="text-gray-500 dark:text-slate-400">{t('procedure.submitted_at') || 'Submitted'}:</span>{' '}
                {formatDateShort(procedure.submitted_at)}
              </span>
            )}
          </div>

          {/* Step timeline */}
          {procedure.steps.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-3">
                {t('procedure.steps') || 'Steps'}
              </h4>
              <StepTimeline steps={procedure.steps} />
            </div>
          )}

          {/* Authority requests */}
          {procedure.authority_requests.length > 0 && (
            <div>
              <h4 className="text-sm font-medium text-gray-700 dark:text-slate-200 mb-3">
                {t('procedure.authority_requests') || 'Authority Requests'}
              </h4>
              <div className="space-y-3">
                {procedure.authority_requests.map((req) => (
                  <AuthorityRequestCard key={req.id} request={req} onRespond={onRespondToRequest} />
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          {procedure.status === 'draft' && onSubmit && (
            <div className="pt-2 border-t border-gray-100 dark:border-slate-700">
              <button
                onClick={() => onSubmit(procedure.id)}
                data-testid="procedure-submit-button"
                className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
              >
                {t('procedure.submit') || 'Submit Procedure'}
              </button>
            </div>
          )}

          {/* Rejection reason */}
          {procedure.status === 'rejected' && procedure.rejection_reason && (
            <div className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2 text-sm">
              <XCircle className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
              <div>
                <p className="font-medium text-red-700 dark:text-red-300">{t('procedure.rejected_reason') || 'Rejection reason'}</p>
                <p className="text-red-600 dark:text-red-400 mt-0.5">{procedure.rejection_reason}</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
