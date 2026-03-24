import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  contractsApi,
  type ContractListData,
  type ContractCreatePayload,
  type ContractUpdatePayload,
  type ContractData,
} from '@/api/contracts';
import { Plus, Edit3, Loader2, X, FileText, AlertTriangle, Clock, RefreshCw } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  draft: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  suspended: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  terminated: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  expired: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
};

const CONTRACT_TYPES = [
  'maintenance',
  'management_mandate',
  'concierge',
  'cleaning',
  'elevator',
  'heating',
  'insurance',
  'security',
  'energy',
  'other',
] as const;
const STATUSES = ['draft', 'active', 'suspended', 'terminated', 'expired'] as const;
const PAYMENT_FREQUENCIES = ['monthly', 'quarterly', 'semi_annual', 'annual'] as const;

function formatCurrency(value: number | null): string {
  return `CHF ${(value ?? 0).toLocaleString('fr-CH', { minimumFractionDigits: 0 })}`;
}

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
        STATUS_COLORS[status] || STATUS_COLORS.draft,
      )}
    >
      {status}
    </span>
  );
}

interface ContractFormProps {
  buildingId: string;
  initialData?: ContractData | null;
  onClose: () => void;
}

function ContractFormModal({ buildingId, initialData, onClose }: ContractFormProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const isEdit = !!initialData;

  const [formState, setFormState] = useState({
    contract_type: initialData?.contract_type ?? 'maintenance',
    reference_code: initialData?.reference_code ?? '',
    title: initialData?.title ?? '',
    counterparty_type: initialData?.counterparty_type ?? 'contact',
    counterparty_id: initialData?.counterparty_id ?? '',
    date_start: initialData?.date_start?.slice(0, 10) ?? '',
    date_end: initialData?.date_end?.slice(0, 10) ?? '',
    annual_cost_chf: initialData?.annual_cost_chf?.toString() ?? '',
    payment_frequency: initialData?.payment_frequency ?? '',
    auto_renewal: initialData?.auto_renewal ?? false,
    notice_period_months: initialData?.notice_period_months?.toString() ?? '',
    status: initialData?.status ?? 'draft',
    notes: initialData?.notes ?? '',
  });

  const createMutation = useMutation({
    mutationFn: (data: ContractCreatePayload) => contractsApi.create(buildingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-contracts', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['contract-summary', buildingId] });
      onClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: ContractUpdatePayload) => contractsApi.update(initialData!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-contracts', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['contract-summary', buildingId] });
      onClose();
    },
  });

  const isPending = createMutation.isPending || updateMutation.isPending;
  const error = createMutation.error || updateMutation.error;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const numOrNull = (v: string) => (v ? Number(v) : null);

    if (isEdit) {
      const payload: ContractUpdatePayload = {
        contract_type: formState.contract_type,
        reference_code: formState.reference_code,
        title: formState.title,
        date_end: formState.date_end || null,
        annual_cost_chf: numOrNull(formState.annual_cost_chf),
        payment_frequency: formState.payment_frequency || null,
        auto_renewal: formState.auto_renewal,
        notice_period_months: numOrNull(formState.notice_period_months),
        status: formState.status,
        notes: formState.notes || null,
      };
      updateMutation.mutate(payload);
    } else {
      const payload: ContractCreatePayload = {
        contract_type: formState.contract_type,
        reference_code: formState.reference_code,
        title: formState.title,
        counterparty_type: formState.counterparty_type,
        counterparty_id: formState.counterparty_id,
        date_start: formState.date_start,
        date_end: formState.date_end || null,
        annual_cost_chf: numOrNull(formState.annual_cost_chf),
        payment_frequency: formState.payment_frequency || null,
        auto_renewal: formState.auto_renewal,
        notice_period_months: numOrNull(formState.notice_period_months),
        status: formState.status,
        notes: formState.notes || null,
      };
      createMutation.mutate(payload);
    }
  };

  const set = (field: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement>) =>
    setFormState((s) => ({ ...s, [field]: e.target.value }));

  const inputCls =
    'w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500';
  const labelCls = 'block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4 p-6">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">
            {isEdit ? t('contract.edit') || 'Edit Contract' : t('contract.create') || 'Create Contract'}
          </h2>
          <button
            onClick={onClose}
            className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
            aria-label="Close"
          >
            <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-sm text-red-700 dark:text-red-300">
            {(error as Error).message || t('app.error') || 'An error occurred'}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {/* Contract type */}
            <div>
              <label className={labelCls}>{t('contract.contract_type') || 'Contract Type'} *</label>
              <select value={formState.contract_type} onChange={set('contract_type')} className={inputCls}>
                {CONTRACT_TYPES.map((ct) => (
                  <option key={ct} value={ct}>
                    {t(`contract.type.${ct}`) || ct}
                  </option>
                ))}
              </select>
            </div>

            {/* Reference code */}
            <div>
              <label className={labelCls}>{t('contract.reference_code') || 'Reference'} *</label>
              <input
                type="text"
                value={formState.reference_code}
                onChange={set('reference_code')}
                required
                className={inputCls}
              />
            </div>

            {/* Title */}
            <div className="sm:col-span-2">
              <label className={labelCls}>{t('contract.title') || 'Title'} *</label>
              <input type="text" value={formState.title} onChange={set('title')} required className={inputCls} />
            </div>

            {/* Counterparty ID — only on create */}
            {!isEdit && (
              <div className="sm:col-span-2">
                <label className={labelCls}>{t('contract.counterparty') || 'Counterparty ID'} *</label>
                <input
                  type="text"
                  value={formState.counterparty_id}
                  onChange={set('counterparty_id')}
                  required
                  className={inputCls}
                  placeholder={t('contract.counterparty_placeholder') || 'UUID of contact, user, or organization'}
                />
              </div>
            )}

            {/* Date start */}
            <div>
              <label className={labelCls}>{t('contract.date_start') || 'Start Date'} *</label>
              <input
                type="date"
                value={formState.date_start}
                onChange={set('date_start')}
                required={!isEdit}
                disabled={isEdit}
                className={cn(inputCls, isEdit && 'opacity-60 cursor-not-allowed')}
              />
            </div>

            {/* Date end */}
            <div>
              <label className={labelCls}>{t('contract.date_end') || 'End Date'}</label>
              <input type="date" value={formState.date_end} onChange={set('date_end')} className={inputCls} />
            </div>

            {/* Annual cost */}
            <div>
              <label className={labelCls}>{t('contract.annual_cost') || 'Annual Cost (CHF)'}</label>
              <input
                type="number"
                step="1"
                min="0"
                value={formState.annual_cost_chf}
                onChange={set('annual_cost_chf')}
                className={inputCls}
              />
            </div>

            {/* Payment frequency */}
            <div>
              <label className={labelCls}>{t('contract.payment_frequency') || 'Payment Frequency'}</label>
              <select value={formState.payment_frequency} onChange={set('payment_frequency')} className={inputCls}>
                <option value="">{t('contract.no_frequency') || '-- None --'}</option>
                {PAYMENT_FREQUENCIES.map((pf) => (
                  <option key={pf} value={pf}>
                    {t(`contract.frequency.${pf}`) || pf}
                  </option>
                ))}
              </select>
            </div>

            {/* Auto renewal */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={formState.auto_renewal}
                onChange={(e) => setFormState((s) => ({ ...s, auto_renewal: e.target.checked }))}
                className="w-4 h-4 text-red-600 border-gray-300 dark:border-slate-600 rounded focus:ring-red-500"
              />
              <label className="text-sm font-medium text-gray-700 dark:text-slate-200">
                {t('contract.auto_renewal') || 'Auto Renewal'}
              </label>
            </div>

            {/* Notice period */}
            <div>
              <label className={labelCls}>{t('contract.notice_period') || 'Notice Period (months)'}</label>
              <input
                type="number"
                step="1"
                min="0"
                value={formState.notice_period_months}
                onChange={set('notice_period_months')}
                className={inputCls}
              />
            </div>

            {/* Status */}
            <div>
              <label className={labelCls}>{t('contract.status') || 'Status'}</label>
              <select value={formState.status} onChange={set('status')} className={inputCls}>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {t(`contract.status.${s}`) || s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className={labelCls}>{t('contract.notes') || 'Notes'}</label>
            <textarea value={formState.notes} onChange={set('notes')} rows={3} className={inputCls} />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
            >
              {t('form.cancel') || 'Cancel'}
            </button>
            <button
              type="submit"
              disabled={isPending}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
            >
              {isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              {isEdit ? t('form.save') || 'Save' : t('form.create') || 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

interface ContractsTabProps {
  buildingId: string;
}

export default function ContractsTab({ buildingId }: ContractsTabProps) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingContract, setEditingContract] = useState<ContractData | null>(null);

  // Contracts list
  const {
    data: contractsPage,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-contracts', buildingId, page],
    queryFn: () => contractsApi.listByBuilding(buildingId, { page, size: 20 }),
    enabled: !!buildingId,
  });

  // Summary
  const { data: summary } = useQuery({
    queryKey: ['contract-summary', buildingId],
    queryFn: () => contractsApi.getSummary(buildingId),
    enabled: !!buildingId,
  });

  // Fetch full contract data for editing
  const handleEdit = async (contract: ContractListData) => {
    try {
      const full = await contractsApi.get(buildingId, contract.id);
      setEditingContract(full);
    } catch {
      setEditingContract({
        ...contract,
        counterparty_id: '',
        payment_frequency: null,
        auto_renewal: false,
        notice_period_months: null,
        notes: null,
        source_type: null,
        confidence: null,
        source_ref: null,
        created_by: null,
        created_at: '',
        updated_at: '',
      });
    }
  };

  const contracts = contractsPage?.items ?? [];
  const totalPages = contractsPage?.pages ?? 1;

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <SummaryCard
            icon={<FileText className="w-4 h-4" />}
            label={t('contract.total') || 'Total'}
            value={String(summary.total_contracts)}
          />
          <SummaryCard
            icon={<FileText className="w-4 h-4" />}
            label={t('contract.active') || 'Active'}
            value={String(summary.active_contracts)}
            highlight="green"
          />
          <SummaryCard
            icon={<FileText className="w-4 h-4" />}
            label={t('contract.annual_cost') || 'Annual Cost'}
            value={formatCurrency(summary.annual_cost_chf) + '/yr'}
          />
          <SummaryCard
            icon={<Clock className="w-4 h-4" />}
            label={t('contract.expiring_90d') || 'Expiring 90d'}
            value={String(summary.expiring_90d)}
            highlight={summary.expiring_90d > 0 ? 'orange' : undefined}
          />
          <SummaryCard
            icon={<RefreshCw className="w-4 h-4" />}
            label={t('contract.auto_renewal') || 'Auto Renewal'}
            value={String(summary.auto_renewal_count)}
          />
        </div>
      )}

      {/* Actions bar */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('contract.list_title') || 'Contracts'}
        </h3>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
        >
          <Plus className="w-4 h-4" />
          {t('contract.create') || 'Create Contract'}
        </button>
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-700 dark:text-red-300 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 flex-shrink-0" />
          {t('contract.load_error') || 'Failed to load contracts.'}
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && (
        <>
          {contracts.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-slate-400">
              <FileText className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p className="text-sm">{t('contract.empty') || 'No contracts found for this building.'}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-slate-700 text-left">
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('contract.reference_code') || 'Reference'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('contract.contract_type') || 'Type'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('contract.title') || 'Title'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('contract.counterparty') || 'Counterparty'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('contract.date_start') || 'Start'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('contract.date_end') || 'End'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400 text-right">
                      {t('contract.annual_cost') || 'Annual Cost'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('contract.status') || 'Status'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                  {contracts.map((contract) => (
                    <tr key={contract.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50">
                      <td className="py-3 font-medium text-gray-900 dark:text-white">{contract.reference_code}</td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">
                        {t(`contract.type.${contract.contract_type}`) || contract.contract_type}
                      </td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">{contract.title}</td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">
                        {contract.counterparty_display_name || '-'}
                      </td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">
                        {contract.date_start?.slice(0, 10) ?? '-'}
                      </td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">
                        {contract.date_end?.slice(0, 10) ?? '-'}
                      </td>
                      <td className="py-3 text-gray-900 dark:text-white text-right">
                        {formatCurrency(contract.annual_cost_chf)}
                      </td>
                      <td className="py-3">
                        <StatusBadge status={contract.status} />
                      </td>
                      <td className="py-3">
                        <button
                          onClick={() => handleEdit(contract)}
                          className="p-1.5 text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                          aria-label={t('form.edit') || 'Edit'}
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-gray-200 dark:border-slate-700">
              <p className="text-sm text-gray-500 dark:text-slate-400">
                {t('contract.page') || 'Page'} {page} / {totalPages} ({contractsPage?.total ?? 0}{' '}
                {t('contract.total_items') || 'items'})
              </p>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {t('pagination.previous') || 'Previous'}
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="px-3 py-1.5 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {t('pagination.next') || 'Next'}
                </button>
              </div>
            </div>
          )}
        </>
      )}

      {/* Create modal */}
      {showCreateModal && <ContractFormModal buildingId={buildingId} onClose={() => setShowCreateModal(false)} />}

      {/* Edit modal */}
      {editingContract && (
        <ContractFormModal
          buildingId={buildingId}
          initialData={editingContract}
          onClose={() => setEditingContract(null)}
        />
      )}
    </div>
  );
}

/* ---- Summary card sub-component ---- */

function SummaryCard({
  icon,
  label,
  value,
  highlight,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  highlight?: 'green' | 'orange' | 'red';
}) {
  const highlightCls = highlight
    ? {
        green: 'text-green-700 dark:text-green-400',
        orange: 'text-orange-700 dark:text-orange-400',
        red: 'text-red-700 dark:text-red-400',
      }[highlight]
    : 'text-gray-900 dark:text-white';

  return (
    <div className="bg-gray-50 dark:bg-slate-700 rounded-lg p-3">
      <div className="flex items-center gap-1.5 text-gray-500 dark:text-slate-400 mb-1">
        {icon}
        <span className="text-xs">{label}</span>
      </div>
      <p className={cn('text-sm font-semibold', highlightCls)}>{value}</p>
    </div>
  );
}
