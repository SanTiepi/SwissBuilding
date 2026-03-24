import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { obligationsApi, type Obligation, type ObligationCreatePayload } from '@/api/obligations';
import { Plus, X, Loader2, CheckCircle2, XCircle, ClipboardList, AlertTriangle, Clock } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  in_progress: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  completed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  cancelled: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
  overdue: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const PRIORITY_COLORS: Record<string, string> = {
  low: 'bg-green-500',
  medium: 'bg-yellow-500',
  high: 'bg-orange-500',
  critical: 'bg-red-500',
};

const OBLIGATION_TYPES = ['regulatory', 'contractual', 'maintenance', 'safety', 'environmental', 'other'] as const;
const PRIORITIES = ['low', 'medium', 'high', 'critical'] as const;

function StatusBadge({ status }: { status: string }) {
  const { t } = useTranslation();
  return (
    <span
      className={cn(
        'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
        STATUS_COLORS[status] || STATUS_COLORS.pending,
      )}
      data-testid="obligation-status-badge"
    >
      {t(`obligation.status.${status}`) || status}
    </span>
  );
}

function TypeBadge({ type }: { type: string }) {
  const { t } = useTranslation();
  return (
    <span
      className="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300"
      data-testid="obligation-type-badge"
    >
      {t(`obligation.type.${type}`) || type}
    </span>
  );
}

function isOverdue(dueDate: string | null): boolean {
  if (!dueDate) return false;
  return new Date(dueDate) < new Date();
}

function isDueSoon(dueDate: string | null, days = 30): boolean {
  if (!dueDate) return false;
  const due = new Date(dueDate);
  const now = new Date();
  const diff = (due.getTime() - now.getTime()) / (1000 * 60 * 60 * 24);
  return diff >= 0 && diff <= days;
}

interface Props {
  buildingId: string;
}

export default function ObligationsCard({ buildingId }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [formTitle, setFormTitle] = useState('');
  const [formDescription, setFormDescription] = useState('');
  const [formType, setFormType] = useState<string>(OBLIGATION_TYPES[0]);
  const [formPriority, setFormPriority] = useState<string>(PRIORITIES[1]);
  const [formDueDate, setFormDueDate] = useState('');

  const {
    data: obligations = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['obligations', buildingId],
    queryFn: () => obligationsApi.listByBuilding(buildingId),
    enabled: !!buildingId,
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: (data: ObligationCreatePayload) => obligationsApi.create(buildingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['obligations', buildingId] });
      resetForm();
    },
  });

  const completeMutation = useMutation({
    mutationFn: (obligationId: string) => obligationsApi.complete(buildingId, obligationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['obligations', buildingId] }),
  });

  const cancelMutation = useMutation({
    mutationFn: (obligationId: string) => obligationsApi.cancel(buildingId, obligationId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['obligations', buildingId] }),
  });

  const resetForm = () => {
    setShowForm(false);
    setFormTitle('');
    setFormDescription('');
    setFormType(OBLIGATION_TYPES[0]);
    setFormPriority(PRIORITIES[1]);
    setFormDueDate('');
  };

  const handleSubmit = () => {
    createMutation.mutate({
      title: formTitle,
      description: formDescription || null,
      obligation_type: formType,
      priority: formPriority,
      due_date: formDueDate || null,
    });
  };

  const { overdueItems, dueSoonItems, otherItems } = useMemo(() => {
    const active = obligations.filter(
      (o: Obligation) => o.status !== 'completed' && o.status !== 'cancelled',
    );
    const overdue = active.filter((o: Obligation) => isOverdue(o.due_date));
    const dueSoon = active.filter((o: Obligation) => !isOverdue(o.due_date) && isDueSoon(o.due_date));
    const other = active.filter((o: Obligation) => !isOverdue(o.due_date) && !isDueSoon(o.due_date));
    return { overdueItems: overdue, dueSoonItems: dueSoon, otherItems: other };
  }, [obligations]);

  const completedItems = obligations.filter(
    (o: Obligation) => o.status === 'completed' || o.status === 'cancelled',
  );

  const renderItem = (item: Obligation) => (
    <div
      key={item.id}
      className="p-3 rounded-lg border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50"
      data-testid="obligation-item"
    >
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span
              className={cn('w-2 h-2 rounded-full flex-shrink-0', PRIORITY_COLORS[item.priority] || 'bg-gray-400')}
              title={item.priority}
            />
            <span className="text-sm font-medium text-gray-900 dark:text-white truncate">{item.title}</span>
            <TypeBadge type={item.obligation_type} />
            <StatusBadge status={item.status} />
          </div>
          {item.description && (
            <p className="text-xs text-gray-500 dark:text-slate-400 mt-1 line-clamp-2">{item.description}</p>
          )}
          {item.due_date && (
            <p className="text-xs text-gray-400 dark:text-slate-500 mt-1">
              {t('obligation.due') || 'Due'}: {new Date(item.due_date).toLocaleDateString('fr-CH')}
            </p>
          )}
        </div>
        {item.status !== 'completed' && item.status !== 'cancelled' && (
          <div className="flex items-center gap-1 flex-shrink-0">
            <button
              onClick={() => completeMutation.mutate(item.id)}
              disabled={completeMutation.isPending}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded text-green-600 dark:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20 transition-colors"
              data-testid="obligation-complete-btn"
              title={t('obligation.action.complete') || 'Complete'}
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => cancelMutation.mutate(item.id)}
              disabled={cancelMutation.isPending}
              className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
              data-testid="obligation-cancel-btn"
              title={t('obligation.action.cancel') || 'Cancel'}
            >
              <XCircle className="w-3.5 h-3.5" />
            </button>
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4 sm:p-6" data-testid="obligations-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <ClipboardList className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('obligation.title') || 'Obligations'}
          </h3>
          {overdueItems.length > 0 && (
            <span
              className="px-1.5 py-0.5 text-xs font-medium rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-400"
              data-testid="obligation-overdue-count"
            >
              {overdueItems.length} {t('obligation.overdue') || 'overdue'}
            </span>
          )}
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition-colors"
            data-testid="obligation-add-btn"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">{t('obligation.add') || 'Add obligation'}</span>
          </button>
        )}
      </div>

      {/* Create form */}
      {showForm && (
        <div
          className="mb-4 p-4 border border-blue-200 dark:border-blue-800 rounded-lg bg-blue-50 dark:bg-blue-900/20"
          data-testid="obligation-add-form"
        >
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('obligation.field.title') || 'Title'}
              </label>
              <input
                type="text"
                value={formTitle}
                onChange={(e) => setFormTitle(e.target.value)}
                className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder={t('obligation.field.title_placeholder') || 'Obligation title'}
                data-testid="obligation-title-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('obligation.field.description') || 'Description'}
              </label>
              <textarea
                value={formDescription}
                onChange={(e) => setFormDescription(e.target.value)}
                rows={2}
                className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                data-testid="obligation-description-input"
              />
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  {t('obligation.field.type') || 'Type'}
                </label>
                <select
                  value={formType}
                  onChange={(e) => setFormType(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="obligation-type-select"
                >
                  {OBLIGATION_TYPES.map((ot) => (
                    <option key={ot} value={ot}>
                      {t(`obligation.type.${ot}`) || ot}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  {t('obligation.field.priority') || 'Priority'}
                </label>
                <select
                  value={formPriority}
                  onChange={(e) => setFormPriority(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="obligation-priority-select"
                >
                  {PRIORITIES.map((p) => (
                    <option key={p} value={p}>
                      {t(`obligation.priority.${p}`) || p}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  {t('obligation.field.due_date') || 'Due date'}
                </label>
                <input
                  type="date"
                  value={formDueDate}
                  onChange={(e) => setFormDueDate(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="obligation-due-date-input"
                />
              </div>
            </div>
            <div className="flex items-center gap-2 justify-end">
              <button
                onClick={resetForm}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
                data-testid="obligation-cancel-btn"
              >
                <X className="w-4 h-4" />
                {t('common.cancel') || 'Cancel'}
              </button>
              <button
                onClick={handleSubmit}
                disabled={createMutation.isPending || !formTitle}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="obligation-submit-btn"
              >
                {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                {t('obligation.add') || 'Add obligation'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-8" data-testid="obligation-loading">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="text-center py-8 text-red-600 dark:text-red-400" data-testid="obligation-error">
          <p className="text-sm">{t('app.error') || 'An error occurred'}</p>
        </div>
      )}

      {/* Empty */}
      {!isLoading && !isError && obligations.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-slate-400" data-testid="obligation-empty">
          <ClipboardList className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">{t('obligation.empty') || 'No obligations'}</p>
        </div>
      )}

      {/* Overdue section */}
      {overdueItems.length > 0 && (
        <div className="mb-4" data-testid="obligation-overdue-section">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle className="w-4 h-4 text-red-500" />
            <h4 className="text-sm font-semibold text-red-700 dark:text-red-400">
              {t('obligation.section.overdue') || 'Overdue'}
            </h4>
          </div>
          <div className="space-y-2">{overdueItems.map(renderItem)}</div>
        </div>
      )}

      {/* Due soon section */}
      {dueSoonItems.length > 0 && (
        <div className="mb-4" data-testid="obligation-due-soon-section">
          <div className="flex items-center gap-2 mb-2">
            <Clock className="w-4 h-4 text-yellow-500" />
            <h4 className="text-sm font-semibold text-yellow-700 dark:text-yellow-400">
              {t('obligation.section.due_soon') || 'Due soon'}
            </h4>
          </div>
          <div className="space-y-2">{dueSoonItems.map(renderItem)}</div>
        </div>
      )}

      {/* Other active */}
      {otherItems.length > 0 && (
        <div className="mb-4" data-testid="obligation-active-section">
          <div className="space-y-2">{otherItems.map(renderItem)}</div>
        </div>
      )}

      {/* Completed / cancelled (collapsed) */}
      {completedItems.length > 0 && (
        <div data-testid="obligation-completed-section">
          <p className="text-xs text-gray-400 dark:text-slate-500 mb-2">
            {completedItems.length} {t('obligation.completed_count') || 'completed/cancelled'}
          </p>
        </div>
      )}
    </div>
  );
}
