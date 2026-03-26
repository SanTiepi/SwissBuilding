import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { marketplaceRfqApi } from '@/api/marketplaceRfq';
import type { ClientRequest } from '@/api/marketplaceRfq';
import { useTranslation } from '@/i18n';
import { cn, formatDateTime } from '@/utils/formatters';
import {
  FileText,
  Plus,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  Award,
  Loader2,
  AlertTriangle,
  ArrowLeft,
  Send,
} from 'lucide-react';

const STATUS_CONFIG: Record<string, { icon: typeof Clock; color: string; bg: string; label: string }> = {
  draft: { icon: FileText, color: 'text-gray-500', bg: 'bg-gray-100 dark:bg-slate-700', label: 'Draft' },
  published: { icon: Send, color: 'text-blue-500', bg: 'bg-blue-100 dark:bg-blue-900/30', label: 'Published' },
  awarded: { icon: Award, color: 'text-green-500', bg: 'bg-green-100 dark:bg-green-900/30', label: 'Awarded' },
  closed: { icon: CheckCircle2, color: 'text-purple-500', bg: 'bg-purple-100 dark:bg-purple-900/30', label: 'Closed' },
  cancelled: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-100 dark:bg-red-900/30', label: 'Cancelled' },
};

function StatusBadge({ status }: { status: string }) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft;
  const Icon = config.icon;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
        config.bg,
        config.color,
      )}
    >
      <Icon className="w-3 h-3" />
      {config.label}
    </span>
  );
}

function RequestCard({ request, onClick }: { request: ClientRequest; onClick: () => void }) {
  const { t } = useTranslation();
  return (
    <button
      onClick={onClick}
      className="w-full text-left bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-4 hover:shadow-md transition-shadow"
    >
      <div className="flex items-start justify-between">
        <div className="flex-1 min-w-0">
          <h3 className="font-semibold text-gray-900 dark:text-white truncate">{request.title}</h3>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {t(`marketplace.work_category.${request.work_category}`) || request.work_category}
            {request.estimated_area_m2 ? ` - ${request.estimated_area_m2} m2` : ''}
          </p>
        </div>
        <div className="flex items-center gap-2 ml-2">
          <StatusBadge status={request.status} />
          <ChevronRight className="w-4 h-4 text-gray-400" />
        </div>
      </div>
      {request.deadline && (
        <p className="mt-2 text-xs text-gray-400 dark:text-slate-500">
          {t('marketplace.deadline') || 'Deadline'}: {request.deadline}
        </p>
      )}
      <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
        {t('common.created_at') || 'Created'}: {formatDateTime(request.created_at)}
      </p>
    </button>
  );
}

function RequestDetail({ request, onBack }: { request: ClientRequest; onBack: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data: quotes, isLoading: quotesLoading } = useQuery({
    queryKey: ['marketplace-quotes', request.id],
    queryFn: () => marketplaceRfqApi.listQuotes(request.id),
  });

  const awardMutation = useMutation({
    mutationFn: (data: { quote_id: string; conditions?: string }) => marketplaceRfqApi.awardQuote(request.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplace-requests'] });
      queryClient.invalidateQueries({ queryKey: ['marketplace-quotes', request.id] });
    },
  });

  const handleAward = (quoteId: string) => {
    if (window.confirm(t('marketplace.confirm_award') || 'Confirm award to this company?')) {
      awardMutation.mutate({ quote_id: quoteId });
    }
  };

  return (
    <div className="space-y-4">
      <button
        onClick={onBack}
        className="flex items-center gap-1 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300"
      >
        <ArrowLeft className="w-4 h-4" />
        {t('common.back') || 'Back'}
      </button>

      <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-xl font-bold text-gray-900 dark:text-white">{request.title}</h2>
            <StatusBadge status={request.status} />
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 text-sm mb-4">
          <div>
            <span className="text-gray-500 dark:text-slate-400">
              {t('marketplace.work_category_label') || 'Work Category'}:
            </span>
            <span className="ml-2 text-gray-900 dark:text-white">
              {t(`marketplace.work_category.${request.work_category}`) || request.work_category}
            </span>
          </div>
          {request.estimated_area_m2 && (
            <div>
              <span className="text-gray-500 dark:text-slate-400">{t('marketplace.area') || 'Area'}:</span>
              <span className="ml-2 text-gray-900 dark:text-white">{request.estimated_area_m2} m2</span>
            </div>
          )}
          {request.budget_indication && (
            <div>
              <span className="text-gray-500 dark:text-slate-400">{t('marketplace.budget') || 'Budget'}:</span>
              <span className="ml-2 text-gray-900 dark:text-white">{request.budget_indication.replace(/_/g, ' ')}</span>
            </div>
          )}
          {request.deadline && (
            <div>
              <span className="text-gray-500 dark:text-slate-400">{t('marketplace.deadline') || 'Deadline'}:</span>
              <span className="ml-2 text-gray-900 dark:text-white">{request.deadline}</span>
            </div>
          )}
        </div>

        {request.description && <p className="text-sm text-gray-600 dark:text-slate-300 mb-4">{request.description}</p>}

        {request.pollutant_types && request.pollutant_types.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-4">
            {request.pollutant_types.map((p) => (
              <span
                key={p}
                className="px-2 py-0.5 text-xs rounded-full bg-red-50 dark:bg-red-900/30 text-red-700 dark:text-red-300"
              >
                {p}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Quotes */}
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-6">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          {t('marketplace.quotes') || 'Quotes'} ({quotes?.length ?? 0})
        </h3>

        {quotesLoading && (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
          </div>
        )}

        {awardMutation.isError && (
          <div className="mb-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-300">
            <AlertTriangle className="w-4 h-4 inline mr-1" />
            {String((awardMutation.error as Error)?.message || 'Award failed')}
          </div>
        )}

        <div className="space-y-3">
          {(quotes ?? []).map((quote) => (
            <div key={quote.id} className="border border-gray-100 dark:border-slate-600 rounded-lg p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900 dark:text-white">
                    CHF {Number(quote.amount_chf).toLocaleString('fr-CH', { minimumFractionDigits: 2 })}
                  </p>
                  {quote.timeline_weeks && (
                    <p className="text-sm text-gray-500 dark:text-slate-400">
                      {quote.timeline_weeks} {t('marketplace.weeks') || 'weeks'}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-2">
                  <StatusBadge status={quote.status} />
                  {request.status === 'published' && quote.status === 'submitted' && (
                    <button
                      onClick={() => handleAward(quote.id)}
                      disabled={awardMutation.isPending}
                      className="px-3 py-1.5 text-xs font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
                    >
                      <Award className="w-3.5 h-3.5 inline mr-1" />
                      {t('marketplace.award') || 'Award'}
                    </button>
                  )}
                </div>
              </div>
              {quote.description && (
                <p className="mt-2 text-sm text-gray-600 dark:text-slate-300">{quote.description}</p>
              )}
              {quote.includes && quote.includes.length > 0 && (
                <p className="mt-1 text-xs text-gray-400 dark:text-slate-500">
                  {t('marketplace.includes') || 'Includes'}: {quote.includes.join(', ')}
                </p>
              )}
            </div>
          ))}
          {!quotesLoading && (quotes ?? []).length === 0 && (
            <p className="text-center py-4 text-gray-400 dark:text-slate-500">
              {t('marketplace.no_quotes') || 'No quotes yet'}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}

function CreateRequestForm({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const { t } = useTranslation();
  const [title, setTitle] = useState('');
  const [workCategory, setWorkCategory] = useState('minor');
  const [description, setDescription] = useState('');
  const [buildingId, setBuildingId] = useState('');

  const createMutation = useMutation({
    mutationFn: () =>
      marketplaceRfqApi.createRequest({
        building_id: buildingId,
        title,
        work_category: workCategory,
        description: description || undefined,
      }),
    onSuccess: () => onCreated(),
  });

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-6">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
        {t('marketplace.create_rfq') || 'Create RFQ'}
      </h3>
      <div className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            {t('marketplace.building_id') || 'Building ID'}
          </label>
          <input
            value={buildingId}
            onChange={(e) => setBuildingId(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            {t('marketplace.title') || 'Title'}
          </label>
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            {t('marketplace.work_category_label') || 'Work Category'}
          </label>
          <select
            value={workCategory}
            onChange={(e) => setWorkCategory(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm"
          >
            <option value="minor">Minor</option>
            <option value="medium">Medium</option>
            <option value="major">Major</option>
          </select>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            {t('common.description') || 'Description'}
          </label>
          <textarea
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm"
          />
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => createMutation.mutate()}
            disabled={!title || !buildingId || createMutation.isPending}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
          >
            {createMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin inline mr-1" />
            ) : (
              <Plus className="w-4 h-4 inline mr-1" />
            )}
            {t('common.create') || 'Create'}
          </button>
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg border border-gray-200 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700"
          >
            {t('common.cancel') || 'Cancel'}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MarketplaceRFQ() {
  const { t } = useTranslation();
  const [selectedRequest, setSelectedRequest] = useState<ClientRequest | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ['marketplace-requests'],
    queryFn: () => marketplaceRfqApi.listRequests({ size: 50 }),
  });

  const requests = data?.items ?? [];

  if (selectedRequest) {
    return (
      <div className="space-y-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <FileText className="w-6 h-6 text-red-600" />
          {t('marketplace.rfq_title') || 'RFQ Workspace'}
        </h1>
        <RequestDetail request={selectedRequest} onBack={() => setSelectedRequest(null)} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
            <FileText className="w-6 h-6 text-red-600" />
            {t('marketplace.rfq_title') || 'RFQ Workspace'}
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {t('marketplace.rfq_subtitle') || 'Manage remediation requests for quotes'}
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-red-600 text-white hover:bg-red-700"
        >
          <Plus className="w-4 h-4 inline mr-1" />
          {t('marketplace.new_rfq') || 'New RFQ'}
        </button>
      </div>

      {showCreate && (
        <CreateRequestForm
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false);
            queryClient.invalidateQueries({ queryKey: ['marketplace-requests'] });
          }}
        />
      )}

      {isLoading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600" />
        </div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-700 dark:text-red-300">
          {t('common.error') || 'An error occurred'}
        </div>
      )}

      <div className="space-y-3">
        {requests.map((req) => (
          <RequestCard key={req.id} request={req} onClick={() => setSelectedRequest(req)} />
        ))}
        {!isLoading && requests.length === 0 && !showCreate && (
          <div className="text-center py-12 text-gray-400 dark:text-slate-500">
            {t('marketplace.no_requests') || 'No RFQs yet'}
          </div>
        )}
      </div>
    </div>
  );
}
