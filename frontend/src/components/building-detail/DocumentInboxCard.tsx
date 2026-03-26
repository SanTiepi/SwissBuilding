import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { documentInboxApi, type DocumentInboxItem } from '@/api/documentInbox';
import { Inbox, Loader2, Link2, Tag, XCircle, FileText } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  linked: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  classified: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  return (
    <span
      className={cn(
        'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
        STATUS_COLORS[status] || STATUS_COLORS.pending,
      )}
      data-testid="inbox-status-badge"
    >
      {t(`document_inbox.status.${status}`) || status}
    </span>
  );
}

interface Props {
  buildingId?: string;
}

export default function DocumentInboxCard({ buildingId }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [classifyItemId, setClassifyItemId] = useState<string | null>(null);
  const [classifyType, setClassifyType] = useState('');

  const queryKey = buildingId ? ['document-inbox', buildingId] : ['document-inbox'];

  const {
    data: inbox,
    isLoading,
    isError,
  } = useQuery({
    queryKey,
    queryFn: () => documentInboxApi.list(buildingId),
    retry: false,
  });

  const linkMutation = useMutation({
    mutationFn: ({ itemId, targetBuildingId }: { itemId: string; targetBuildingId: string }) =>
      documentInboxApi.link(itemId, targetBuildingId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  const classifyMutation = useMutation({
    mutationFn: ({ itemId, documentType }: { itemId: string; documentType: string }) =>
      documentInboxApi.classify(itemId, documentType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey });
      setClassifyItemId(null);
      setClassifyType('');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (itemId: string) => documentInboxApi.reject(itemId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey }),
  });

  const pendingCount = inbox?.pending ?? 0;
  const items = inbox?.items ?? [];

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4 sm:p-6" data-testid="document-inbox-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Inbox className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('document_inbox.title') || 'Document Inbox'}
          </h3>
          {pendingCount > 0 && (
            <span
              className="px-1.5 py-0.5 text-xs font-medium rounded-full bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-400"
              data-testid="inbox-pending-count"
            >
              {pendingCount}
            </span>
          )}
        </div>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-8" data-testid="inbox-loading">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="text-center py-8 text-red-600 dark:text-red-400" data-testid="inbox-error">
          <p className="text-sm">{t('app.error') || 'An error occurred'}</p>
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && items.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-slate-400" data-testid="inbox-empty">
          <Inbox className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">{t('document_inbox.empty') || 'No documents in inbox'}</p>
        </div>
      )}

      {/* Item list */}
      {!isLoading && !isError && items.length > 0 && (
        <div className="space-y-3" data-testid="inbox-item-list">
          {items.map((item: DocumentInboxItem) => (
            <div
              key={item.id}
              className="p-3 rounded-lg border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50"
              data-testid="inbox-item"
            >
              <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap min-w-0">
                  <FileText className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />
                  <span
                    className="text-sm font-medium text-gray-900 dark:text-white truncate"
                    data-testid="inbox-filename"
                  >
                    {item.filename}
                  </span>
                  <StatusBadge status={item.status} />
                </div>
                <div className="text-xs text-gray-500 dark:text-slate-400 flex-shrink-0">
                  {item.source && <span data-testid="inbox-source">{item.source}</span>}
                </div>
              </div>

              {/* Actions for pending items */}
              {item.status === 'pending' && (
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {buildingId && (
                    <button
                      onClick={() => linkMutation.mutate({ itemId: item.id, targetBuildingId: buildingId })}
                      disabled={linkMutation.isPending}
                      className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 transition-colors"
                      data-testid="inbox-link-btn"
                    >
                      <Link2 className="w-3.5 h-3.5" />
                      {t('document_inbox.action.link') || 'Link'}
                    </button>
                  )}

                  {classifyItemId === item.id ? (
                    <div className="flex items-center gap-1">
                      <input
                        type="text"
                        value={classifyType}
                        onChange={(e) => setClassifyType(e.target.value)}
                        placeholder={t('document_inbox.field.document_type') || 'Document type'}
                        className="rounded border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-2 py-1 text-xs w-32 focus:ring-1 focus:ring-blue-500"
                        data-testid="inbox-classify-input"
                      />
                      <button
                        onClick={() => classifyMutation.mutate({ itemId: item.id, documentType: classifyType })}
                        disabled={!classifyType || classifyMutation.isPending}
                        className="px-2 py-1 text-xs font-medium rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 transition-colors"
                        data-testid="inbox-classify-confirm-btn"
                      >
                        {t('common.confirm') || 'OK'}
                      </button>
                      <button
                        onClick={() => {
                          setClassifyItemId(null);
                          setClassifyType('');
                        }}
                        className="px-1 py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200"
                        data-testid="inbox-classify-cancel-btn"
                      >
                        <XCircle className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setClassifyItemId(item.id)}
                      className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors"
                      data-testid="inbox-classify-btn"
                    >
                      <Tag className="w-3.5 h-3.5" />
                      {t('document_inbox.action.classify') || 'Classify'}
                    </button>
                  )}

                  <button
                    onClick={() => rejectMutation.mutate(item.id)}
                    disabled={rejectMutation.isPending}
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                    data-testid="inbox-reject-btn"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    {t('document_inbox.action.reject') || 'Reject'}
                  </button>
                </div>
              )}

              <div className="mt-1 text-[10px] text-gray-400 dark:text-slate-500">
                {new Date(item.uploaded_at).toLocaleDateString('fr-CH')}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
