import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  leasesApi,
  type LeaseListData,
  type LeaseCreatePayload,
  type LeaseUpdatePayload,
  type LeaseData,
  type ContactOption,
} from '@/api/leases';
import { Plus, Edit3, Loader2, X, Home, AlertTriangle, Clock, FileText, Search } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  draft: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  terminated: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  expired: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  disputed: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
};

const LEASE_TYPES = ['residential', 'commercial', 'mixed', 'parking', 'storage', 'short_term'] as const;
const STATUSES = ['draft', 'active', 'terminated', 'expired', 'disputed'] as const;

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

interface LeaseFormProps {
  buildingId: string;
  initialData?: LeaseData | null;
  onClose: () => void;
}

function LeaseFormModal({ buildingId, initialData, onClose }: LeaseFormProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const isEdit = !!initialData;

  const [formState, setFormState] = useState({
    lease_type: initialData?.lease_type ?? 'residential',
    reference_code: initialData?.reference_code ?? '',
    tenant_type: initialData?.tenant_type ?? 'contact',
    tenant_id: initialData?.tenant_id ?? '',
    date_start: initialData?.date_start?.slice(0, 10) ?? '',
    date_end: initialData?.date_end?.slice(0, 10) ?? '',
    rent_monthly_chf: initialData?.rent_monthly_chf?.toString() ?? '',
    charges_monthly_chf: initialData?.charges_monthly_chf?.toString() ?? '',
    deposit_chf: initialData?.deposit_chf?.toString() ?? '',
    status: initialData?.status ?? 'draft',
    notes: initialData?.notes ?? '',
  });

  // Contact selector state (create mode only)
  const [contactQuery, setContactQuery] = useState('');
  const [contactResults, setContactResults] = useState<ContactOption[]>([]);
  const [contactLoading, setContactLoading] = useState(false);
  const [showContactDropdown, setShowContactDropdown] = useState(false);
  const [selectedContactName, setSelectedContactName] = useState('');
  const contactDropdownRef = useRef<HTMLDivElement>(null);

  const assignSelectedContact = (contact: ContactOption) => {
    setFormState((s) => ({ ...s, tenant_id: contact.id, tenant_type: 'contact' }));
    setSelectedContactName(contact.name);
    setContactQuery('');
    setContactResults([]);
    setShowContactDropdown(false);
  };

  // Debounced contact search
  useEffect(() => {
    if (isEdit) return;
    if (contactQuery.length < 1) {
      setContactResults([]);
      return;
    }
    const timer = setTimeout(async () => {
      setContactLoading(true);
      try {
        const results = await leasesApi.lookupContacts(buildingId, contactQuery);
        setContactResults(results);
        if (results.length === 1) {
          assignSelectedContact(results[0]);
        } else {
          setShowContactDropdown(true);
        }
      } catch {
        setContactResults([]);
      } finally {
        setContactLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [buildingId, contactQuery, isEdit]);

  // Close dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (contactDropdownRef.current && !contactDropdownRef.current.contains(e.target as Node)) {
        setShowContactDropdown(false);
      }
    };
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  const handleSelectContact = (contact: ContactOption) => {
    assignSelectedContact(contact);
  };

  const createMutation = useMutation({
    mutationFn: (data: LeaseCreatePayload) => leasesApi.create(buildingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-leases', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['lease-summary', buildingId] });
      onClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: LeaseUpdatePayload) => leasesApi.update(initialData!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-leases', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['lease-summary', buildingId] });
      onClose();
    },
  });

  const isPending = createMutation.isPending || updateMutation.isPending;
  const error = createMutation.error || updateMutation.error;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const numOrNull = (v: string) => (v ? Number(v) : null);

    if (isEdit) {
      const payload: LeaseUpdatePayload = {
        lease_type: formState.lease_type,
        reference_code: formState.reference_code,
        date_end: formState.date_end || null,
        rent_monthly_chf: numOrNull(formState.rent_monthly_chf),
        charges_monthly_chf: numOrNull(formState.charges_monthly_chf),
        deposit_chf: numOrNull(formState.deposit_chf),
        status: formState.status,
        notes: formState.notes || null,
      };
      updateMutation.mutate(payload);
    } else {
      const payload: LeaseCreatePayload = {
        lease_type: formState.lease_type,
        reference_code: formState.reference_code,
        tenant_type: formState.tenant_type,
        tenant_id: formState.tenant_id,
        date_start: formState.date_start,
        date_end: formState.date_end || null,
        rent_monthly_chf: numOrNull(formState.rent_monthly_chf),
        charges_monthly_chf: numOrNull(formState.charges_monthly_chf),
        deposit_chf: numOrNull(formState.deposit_chf),
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
      <div
        data-testid="lease-form-modal"
        className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4 p-6"
      >
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">
            {isEdit ? t('lease.edit') || 'Edit Lease' : t('lease.create') || 'Create Lease'}
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
            {/* Lease type */}
            <div>
              <label className={labelCls}>{t('lease.lease_type') || 'Lease Type'} *</label>
              <select
                value={formState.lease_type}
                onChange={set('lease_type')}
                className={inputCls}
                data-testid="lease-form-type"
              >
                {LEASE_TYPES.map((lt) => (
                  <option key={lt} value={lt}>
                    {t(`lease.type.${lt}`) || lt}
                  </option>
                ))}
              </select>
            </div>

            {/* Reference code */}
            <div>
              <label className={labelCls}>{t('lease.reference_code') || 'Reference'} *</label>
              <input
                type="text"
                value={formState.reference_code}
                onChange={set('reference_code')}
                required
                data-testid="lease-form-reference-code"
                className={inputCls}
              />
            </div>

            {/* Tenant selector — only on create */}
            {!isEdit && (
              <div className="sm:col-span-2" ref={contactDropdownRef}>
                <label className={labelCls}>{t('lease.tenant') || 'Tenant'} *</label>
                {selectedContactName ? (
                  <div className="flex items-center gap-2">
                    <span data-testid="contact-selected-name" className={cn(inputCls, 'flex-1 flex items-center')}>
                      {selectedContactName}
                    </span>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedContactName('');
                        setFormState((s) => ({ ...s, tenant_id: '', tenant_type: 'contact' }));
                        setContactResults([]);
                        setShowContactDropdown(false);
                      }}
                      className="p-2 text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                      aria-label={t('form.clear') || 'Clear'}
                    >
                      <X className="w-4 h-4" />
                    </button>
                  </div>
                ) : (
                  <div className="relative">
                    <div className="relative">
                      <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                      <input
                        type="text"
                        value={contactQuery}
                        onChange={(e) => setContactQuery(e.target.value)}
                        onFocus={() => contactResults.length > 0 && setShowContactDropdown(true)}
                        className={cn(inputCls, 'pl-9')}
                        placeholder={t('lease.search_tenant') || 'Search contacts...'}
                        data-testid="contact-search-input"
                        aria-label={t('lease.tenant') || 'Tenant'}
                      />
                      {contactLoading && (
                        <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-gray-400" />
                      )}
                    </div>
                    {showContactDropdown && (
                      <div className="absolute z-10 w-full mt-1 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                        {contactResults.length === 0 ? (
                          <div className="px-3 py-2 text-sm text-gray-500 dark:text-slate-400">
                            {t('lease.no_contacts_found') || 'No contacts found'}
                          </div>
                        ) : (
                          contactResults.map((contact) => (
                            <button
                              key={contact.id}
                              type="button"
                              onClick={() => handleSelectContact(contact)}
                              data-testid="contact-search-result"
                              className="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-slate-600 flex items-center justify-between"
                            >
                              <span className="font-medium text-gray-900 dark:text-white">{contact.name}</span>
                              {contact.email && (
                                <span className="text-xs text-gray-400 dark:text-slate-500 ml-2">{contact.email}</span>
                              )}
                            </button>
                          ))
                        )}
                      </div>
                    )}
                  </div>
                )}
                {/* Hidden required input for form validation */}
                <input type="hidden" value={formState.tenant_id} required />
              </div>
            )}

            {/* Date start */}
            <div>
              <label className={labelCls}>{t('lease.date_start') || 'Start Date'} *</label>
              <input
                type="date"
                value={formState.date_start}
                onChange={set('date_start')}
                required={!isEdit}
                disabled={isEdit}
                data-testid="lease-form-date-start"
                className={cn(inputCls, isEdit && 'opacity-60 cursor-not-allowed')}
              />
            </div>

            {/* Date end */}
            <div>
              <label className={labelCls}>{t('lease.date_end') || 'End Date'}</label>
              <input
                type="date"
                value={formState.date_end}
                onChange={set('date_end')}
                className={inputCls}
                data-testid="lease-form-date-end"
              />
            </div>

            {/* Rent */}
            <div>
              <label className={labelCls}>{t('lease.rent_monthly') || 'Rent (CHF/mo)'}</label>
              <input
                type="number"
                step="1"
                min="0"
                value={formState.rent_monthly_chf}
                onChange={set('rent_monthly_chf')}
                data-testid="lease-form-rent"
                className={inputCls}
              />
            </div>

            {/* Charges */}
            <div>
              <label className={labelCls}>{t('lease.charges_monthly') || 'Charges (CHF/mo)'}</label>
              <input
                type="number"
                step="1"
                min="0"
                value={formState.charges_monthly_chf}
                onChange={set('charges_monthly_chf')}
                data-testid="lease-form-charges"
                className={inputCls}
              />
            </div>

            {/* Deposit */}
            <div>
              <label className={labelCls}>{t('lease.deposit') || 'Deposit (CHF)'}</label>
              <input
                type="number"
                step="1"
                min="0"
                value={formState.deposit_chf}
                onChange={set('deposit_chf')}
                data-testid="lease-form-deposit"
                className={inputCls}
              />
            </div>

            {/* Status */}
            <div>
              <label className={labelCls}>{t('lease.status') || 'Status'}</label>
              <select
                value={formState.status}
                onChange={set('status')}
                className={inputCls}
                data-testid="lease-form-status"
              >
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {t(`lease.status.${s}`) || s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className={labelCls}>{t('lease.notes') || 'Notes'}</label>
            <textarea
              value={formState.notes}
              onChange={set('notes')}
              rows={3}
              className={inputCls}
              data-testid="lease-form-notes"
            />
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
              data-testid="lease-form-submit"
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

interface LeasesTabProps {
  buildingId: string;
}

export default function LeasesTab({ buildingId }: LeasesTabProps) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingLease, setEditingLease] = useState<LeaseData | null>(null);

  // Leases list
  const {
    data: leasesPage,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-leases', buildingId, page],
    queryFn: () => leasesApi.listByBuilding(buildingId, { page, size: 20 }),
    enabled: !!buildingId,
  });

  // Summary
  const { data: summary } = useQuery({
    queryKey: ['lease-summary', buildingId],
    queryFn: () => leasesApi.getSummary(buildingId),
    enabled: !!buildingId,
  });

  // Fetch full lease data for editing
  const handleEdit = async (lease: LeaseListData) => {
    try {
      const full = await leasesApi.get(buildingId, lease.id);
      setEditingLease(full);
    } catch {
      setEditingLease({
        ...lease,
        unit_id: null,
        zone_id: null,
        notice_period_months: null,
        charges_monthly_chf: null,
        deposit_chf: null,
        surface_m2: null,
        rooms: null,
        notes: null,
        source_type: null,
        confidence: null,
        source_ref: null,
        created_by: null,
        created_at: '',
        updated_at: '',
        tenant_display_name: lease.tenant_display_name ?? null,
        unit_label: lease.unit_label ?? null,
        zone_name: lease.zone_name ?? null,
      });
    }
  };

  const leases = leasesPage?.items ?? [];
  const totalPages = leasesPage?.pages ?? 1;

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          <SummaryCard
            icon={<FileText className="w-4 h-4" />}
            label={t('lease.total') || 'Total'}
            value={String(summary.total_leases)}
          />
          <SummaryCard
            icon={<Home className="w-4 h-4" />}
            label={t('lease.active') || 'Active'}
            value={String(summary.active_leases)}
            highlight="green"
          />
          <SummaryCard
            icon={<FileText className="w-4 h-4" />}
            label={t('lease.rent') || 'Rent'}
            value={formatCurrency(summary.monthly_rent_chf) + '/mo'}
          />
          <SummaryCard
            icon={<FileText className="w-4 h-4" />}
            label={t('lease.charges') || 'Charges'}
            value={formatCurrency(summary.monthly_charges_chf) + '/mo'}
          />
          <SummaryCard
            icon={<Clock className="w-4 h-4" />}
            label={t('lease.expiring_90d') || 'Expiring 90d'}
            value={String(summary.expiring_90d)}
            highlight={summary.expiring_90d > 0 ? 'orange' : undefined}
          />
          <SummaryCard
            icon={<AlertTriangle className="w-4 h-4" />}
            label={t('lease.disputed') || 'Disputed'}
            value={String(summary.disputed_count)}
            highlight={summary.disputed_count > 0 ? 'red' : undefined}
          />
        </div>
      )}

      {/* Actions bar */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{t('lease.list_title') || 'Leases'}</h3>
        <button
          onClick={() => setShowCreateModal(true)}
          data-testid="leases-create-button"
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
        >
          <Plus className="w-4 h-4" />
          {t('lease.create') || 'Create Lease'}
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
          {t('lease.load_error') || 'Failed to load leases.'}
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && (
        <>
          {leases.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-slate-400">
              <Home className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p className="text-sm">{t('lease.empty') || 'No leases found for this building.'}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-slate-700 text-left">
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('lease.reference_code') || 'Reference'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('lease.lease_type') || 'Type'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('lease.tenant') || 'Tenant'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">{t('lease.unit') || 'Unit'}</th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">{t('lease.zone') || 'Zone'}</th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('lease.date_start') || 'Start'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('lease.date_end') || 'End'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400 text-right">
                      {t('lease.rent_monthly') || 'Rent/mo'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('lease.status') || 'Status'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                  {leases.map((lease) => (
                    <tr key={lease.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50">
                      <td className="py-3 font-medium text-gray-900 dark:text-white">{lease.reference_code}</td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">
                        {t(`lease.type.${lease.lease_type}`) || lease.lease_type}
                      </td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">
                        {lease.tenant_display_name || lease.tenant_id.slice(0, 8) + '...'}
                      </td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">{lease.unit_label || '-'}</td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">{lease.zone_name || '-'}</td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">
                        {lease.date_start?.slice(0, 10) ?? '-'}
                      </td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">{lease.date_end?.slice(0, 10) ?? '-'}</td>
                      <td className="py-3 text-gray-900 dark:text-white text-right">
                        {formatCurrency(lease.rent_monthly_chf)}
                      </td>
                      <td className="py-3">
                        <StatusBadge status={lease.status} />
                      </td>
                      <td className="py-3">
                        <button
                          onClick={() => handleEdit(lease)}
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
                {t('lease.page') || 'Page'} {page} / {totalPages} ({leasesPage?.total ?? 0}{' '}
                {t('lease.total_items') || 'items'})
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
      {showCreateModal && <LeaseFormModal buildingId={buildingId} onClose={() => setShowCreateModal(false)} />}

      {/* Edit modal */}
      {editingLease && (
        <LeaseFormModal buildingId={buildingId} initialData={editingLease} onClose={() => setEditingLease(null)} />
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
