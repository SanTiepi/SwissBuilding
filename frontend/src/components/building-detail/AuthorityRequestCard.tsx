import { useState } from 'react';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import type { AuthorityRequest, RequestStatus } from '@/api/permitProcedures';
import { Clock, Send, FileText, AlertTriangle } from 'lucide-react';

const REQUEST_STATUS_COLORS: Record<RequestStatus, string> = {
  open: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  responded: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  overdue: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  closed: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-400',
};

function formatDateShort(d: string | null): string {
  if (!d) return '-';
  return d.slice(0, 10);
}

function isOverdue(deadline: string | null): boolean {
  if (!deadline) return false;
  return new Date(deadline).getTime() < Date.now();
}

function daysUntil(deadline: string | null): number | null {
  if (!deadline) return null;
  const diff = new Date(deadline).getTime() - Date.now();
  return Math.ceil(diff / (24 * 60 * 60 * 1000));
}

interface AuthorityRequestCardProps {
  request: AuthorityRequest;
  onRespond?: (requestId: string, text: string) => void;
}

export default function AuthorityRequestCard({ request, onRespond }: AuthorityRequestCardProps) {
  const { t } = useTranslation();
  const [responseText, setResponseText] = useState('');
  const [showForm, setShowForm] = useState(false);

  const overdue = isOverdue(request.response_deadline);
  const effectiveStatus: RequestStatus = request.status === 'open' && overdue ? 'overdue' : request.status;
  const remaining = daysUntil(request.response_deadline);

  const handleSubmit = () => {
    if (!responseText.trim() || !onRespond) return;
    onRespond(request.id, responseText.trim());
    setResponseText('');
    setShowForm(false);
  };

  return (
    <div
      data-testid={`authority-request-${request.id}`}
      className="bg-gray-50 dark:bg-slate-700/50 border border-gray-200 dark:border-slate-600 rounded-lg p-3"
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="inline-block px-2 py-0.5 text-xs font-medium bg-slate-100 text-slate-700 dark:bg-slate-600 dark:text-slate-200 rounded">
            {request.request_type.replace(/_/g, ' ')}
          </span>
          <span
            data-testid={`request-status-${effectiveStatus}`}
            className={cn(
              'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
              REQUEST_STATUS_COLORS[effectiveStatus],
            )}
          >
            {t(`procedure.request_status.${effectiveStatus}`) || effectiveStatus}
          </span>
        </div>
        {request.response_deadline && (
          <span
            className={cn(
              'inline-flex items-center gap-1 text-xs flex-shrink-0',
              overdue
                ? 'text-red-600 dark:text-red-400 font-medium'
                : remaining !== null && remaining <= 3
                  ? 'text-orange-600 dark:text-orange-400'
                  : 'text-gray-500 dark:text-slate-400',
            )}
            data-testid="request-deadline"
          >
            {overdue ? <AlertTriangle className="w-3 h-3" /> : <Clock className="w-3 h-3" />}
            {formatDateShort(request.response_deadline)}
            {remaining !== null && !overdue && (
              <span>
                ({remaining}
                {t('procedure.days_short') || 'd'})
              </span>
            )}
            {overdue && <span>({t('procedure.overdue') || 'overdue'})</span>}
          </span>
        )}
      </div>

      {/* Subject + body */}
      <h5 className="text-sm font-medium text-gray-900 dark:text-white mt-2">{request.subject}</h5>
      <p className="text-xs text-gray-600 dark:text-slate-300 mt-1 line-clamp-3">{request.body}</p>

      {/* Linked documents */}
      {request.linked_document_ids.length > 0 && (
        <div className="mt-2 flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400">
          <FileText className="w-3 h-3" />
          {request.linked_document_ids.length} {t('procedure.linked_docs') || 'linked documents'}
        </div>
      )}

      {/* Response (already responded) */}
      {request.response_text && (
        <div className="mt-2 p-2 bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 rounded text-xs text-green-800 dark:text-green-300">
          <p className="font-medium mb-0.5">
            {t('procedure.response') || 'Response'} — {formatDateShort(request.responded_at)}
          </p>
          <p>{request.response_text}</p>
        </div>
      )}

      {/* Response form */}
      {(effectiveStatus === 'open' || effectiveStatus === 'overdue') && onRespond && !request.response_text && (
        <>
          {!showForm ? (
            <button
              onClick={() => setShowForm(true)}
              data-testid="respond-button"
              className="mt-2 inline-flex items-center gap-1.5 text-xs font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300"
            >
              <Send className="w-3 h-3" />
              {t('procedure.respond') || 'Respond'}
            </button>
          ) : (
            <div className="mt-2 space-y-2">
              <textarea
                value={responseText}
                onChange={(e) => setResponseText(e.target.value)}
                rows={3}
                data-testid="response-textarea"
                placeholder={t('procedure.response_placeholder') || 'Type your response...'}
                className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <div className="flex items-center gap-2">
                <button
                  onClick={handleSubmit}
                  disabled={!responseText.trim()}
                  data-testid="submit-response"
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-blue-400"
                >
                  <Send className="w-3 h-3" />
                  {t('procedure.send_response') || 'Send'}
                </button>
                <button
                  onClick={() => {
                    setShowForm(false);
                    setResponseText('');
                  }}
                  className="px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white"
                >
                  {t('form.cancel') || 'Cancel'}
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
