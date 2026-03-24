import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  ownershipApi,
  type OwnershipListData,
  type OwnershipCreatePayload,
  type OwnershipUpdatePayload,
  type OwnershipData,
} from '@/api/ownership';
import { leasesApi, type ContactOption } from '@/api/leases';
import { Plus, Edit3, Loader2, X, Users, AlertTriangle, FileText, Search, Shield } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  active: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  transferred: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  disputed: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  archived: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
};

const OWNERSHIP_TYPES = ['full', 'co_ownership', 'usufruct', 'bare_ownership', 'ppe_unit'] as const;
const ACQUISITION_TYPES = ['purchase', 'inheritance', 'donation', 'construction', 'exchange'] as const;
const STATUSES = ['active', 'transferred', 'disputed', 'archived'] as const;

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
        STATUS_COLORS[status] || STATUS_COLORS.archived,
      )}
    >
      {status}
    </span>
  );
}

interface OwnershipFormProps {
  buildingId: string;
  initialData?: OwnershipData | null;
  onClose: () => void;
}

function OwnershipFormModal({ buildingId, initialData, onClose }: OwnershipFormProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const isEdit = !!initialData;

  const [formState, setFormState] = useState({
    owner_type: initialData?.owner_type ?? 'contact',
    owner_id: initialData?.owner_id ?? '',
    ownership_type: initialData?.ownership_type ?? 'full',
    share_pct: initialData?.share_pct?.toString() ?? '',
    acquisition_type: initialData?.acquisition_type ?? '',
    acquisition_date: initialData?.acquisition_date?.slice(0, 10) ?? '',
    disposal_date: initialData?.disposal_date?.slice(0, 10) ?? '',
    acquisition_price_chf: initialData?.acquisition_price_chf?.toString() ?? '',
    land_register_ref: initialData?.land_register_ref ?? '',
    status: initialData?.status ?? 'active',
    notes: initialData?.notes ?? '',
  });

  // Contact selector state (create mode only)
  const [contactQuery, setContactQuery] = useState('');
  const [contactResults, setContactResults] = useState<ContactOption[]>([]);
  const [contactLoading, setContactLoading] = useState(false);
  const [showContactDropdown, setShowContactDropdown] = useState(false);
  const [selectedContactName, setSelectedContactName] = useState('');
  const contactDropdownRef = useRef<HTMLDivElement>(null);

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
        setShowContactDropdown(true);
      } catch {
        setContactResults([]);
      } finally {
        setContactLoading(false);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [contactQuery, isEdit]);

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
    setFormState((s) => ({ ...s, owner_id: contact.id, owner_type: contact.contact_type || 'contact' }));
    setSelectedContactName(contact.name);
    setContactQuery('');
    setShowContactDropdown(false);
  };

  const createMutation = useMutation({
    mutationFn: (data: OwnershipCreatePayload) => ownershipApi.create(buildingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-ownership', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['ownership-summary', buildingId] });
      onClose();
    },
  });

  const updateMutation = useMutation({
    mutationFn: (data: OwnershipUpdatePayload) => ownershipApi.update(initialData!.id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-ownership', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['ownership-summary', buildingId] });
      onClose();
    },
  });

  const isPending = createMutation.isPending || updateMutation.isPending;
  const error = createMutation.error || updateMutation.error;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const numOrNull = (v: string) => (v ? Number(v) : null);

    if (isEdit) {
      const payload: OwnershipUpdatePayload = {
        ownership_type: formState.ownership_type,
        share_pct: numOrNull(formState.share_pct),
        acquisition_type: formState.acquisition_type || null,
        acquisition_date: formState.acquisition_date || null,
        disposal_date: formState.disposal_date || null,
        acquisition_price_chf: numOrNull(formState.acquisition_price_chf),
        land_register_ref: formState.land_register_ref || null,
        status: formState.status,
        notes: formState.notes || null,
      };
      updateMutation.mutate(payload);
    } else {
      const payload: OwnershipCreatePayload = {
        owner_type: formState.owner_type,
        owner_id: formState.owner_id,
        ownership_type: formState.ownership_type,
        share_pct: numOrNull(formState.share_pct),
        acquisition_type: formState.acquisition_type || null,
        acquisition_date: formState.acquisition_date || null,
        disposal_date: formState.disposal_date || null,
        acquisition_price_chf: numOrNull(formState.acquisition_price_chf),
        land_register_ref: formState.land_register_ref || null,
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
            {isEdit ? t('ownership.edit') || 'Edit Ownership' : t('ownership.create') || 'Create Ownership Record'}
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
            {/* Owner selector — only on create */}
            {!isEdit && (
              <div className="sm:col-span-2" ref={contactDropdownRef}>
                <label className={labelCls}>{t('ownership.owner') || 'Owner'} *</label>
                {selectedContactName ? (
                  <div className="flex items-center gap-2">
                    <span className={cn(inputCls, 'flex-1 flex items-center')}>{selectedContactName}</span>
                    <button
                      type="button"
                      onClick={() => {
                        setSelectedContactName('');
                        setFormState((s) => ({ ...s, owner_id: '', owner_type: 'contact' }));
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
                        placeholder={t('ownership.search_owner') || 'Search contacts...'}
                        data-testid="contact-search-input"
                      />
                      {contactLoading && (
                        <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-gray-400" />
                      )}
                    </div>
                    {showContactDropdown && (
                      <div className="absolute z-10 w-full mt-1 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                        {contactResults.length === 0 ? (
                          <div className="px-3 py-2 text-sm text-gray-500 dark:text-slate-400">
                            {t('ownership.no_contacts_found') || 'No contacts found'}
                          </div>
                        ) : (
                          contactResults.map((contact) => (
                            <button
                              key={contact.id}
                              type="button"
                              onClick={() => handleSelectContact(contact)}
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
                <input type="hidden" value={formState.owner_id} required />
              </div>
            )}

            {/* Ownership type */}
            <div>
              <label className={labelCls}>{t('ownership.ownership_type') || 'Ownership Type'} *</label>
              <select value={formState.ownership_type} onChange={set('ownership_type')} className={inputCls}>
                {OWNERSHIP_TYPES.map((ot) => (
                  <option key={ot} value={ot}>
                    {t(`ownership.type.${ot}`) || ot}
                  </option>
                ))}
              </select>
            </div>

            {/* Share % */}
            <div>
              <label className={labelCls}>{t('ownership.share_pct') || 'Share %'}</label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="100"
                value={formState.share_pct}
                onChange={set('share_pct')}
                className={inputCls}
              />
            </div>

            {/* Acquisition type */}
            <div>
              <label className={labelCls}>{t('ownership.acquisition_type') || 'Acquisition Type'}</label>
              <select value={formState.acquisition_type} onChange={set('acquisition_type')} className={inputCls}>
                <option value="">{t('form.select') || '-- Select --'}</option>
                {ACQUISITION_TYPES.map((at) => (
                  <option key={at} value={at}>
                    {t(`ownership.acquisition.${at}`) || at}
                  </option>
                ))}
              </select>
            </div>

            {/* Acquisition date */}
            <div>
              <label className={labelCls}>{t('ownership.acquisition_date') || 'Acquisition Date'}</label>
              <input
                type="date"
                value={formState.acquisition_date}
                onChange={set('acquisition_date')}
                className={inputCls}
              />
            </div>

            {/* Disposal date */}
            <div>
              <label className={labelCls}>{t('ownership.disposal_date') || 'Disposal Date'}</label>
              <input type="date" value={formState.disposal_date} onChange={set('disposal_date')} className={inputCls} />
            </div>

            {/* Acquisition price */}
            <div>
              <label className={labelCls}>{t('ownership.acquisition_price') || 'Acquisition Price (CHF)'}</label>
              <input
                type="number"
                step="1"
                min="0"
                value={formState.acquisition_price_chf}
                onChange={set('acquisition_price_chf')}
                className={inputCls}
              />
            </div>

            {/* Land register ref */}
            <div>
              <label className={labelCls}>{t('ownership.land_register_ref') || 'Land Register Ref'}</label>
              <input
                type="text"
                value={formState.land_register_ref}
                onChange={set('land_register_ref')}
                className={inputCls}
              />
            </div>

            {/* Status */}
            <div>
              <label className={labelCls}>{t('ownership.status') || 'Status'}</label>
              <select value={formState.status} onChange={set('status')} className={inputCls}>
                {STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {t(`ownership.status.${s}`) || s}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Notes */}
          <div>
            <label className={labelCls}>{t('ownership.notes') || 'Notes'}</label>
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

interface OwnershipTabProps {
  buildingId: string;
}

export default function OwnershipTab({ buildingId }: OwnershipTabProps) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editingRecord, setEditingRecord] = useState<OwnershipData | null>(null);

  // Ownership list
  const {
    data: ownershipPage,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-ownership', buildingId, page],
    queryFn: () => ownershipApi.listByBuilding(buildingId, { page, size: 20 }),
    enabled: !!buildingId,
  });

  // Summary
  const { data: summary } = useQuery({
    queryKey: ['ownership-summary', buildingId],
    queryFn: () => ownershipApi.getSummary(buildingId),
    enabled: !!buildingId,
  });

  // Fetch full record for editing
  const handleEdit = async (record: OwnershipListData) => {
    try {
      const full = await ownershipApi.get(buildingId, record.id);
      setEditingRecord(full);
    } catch {
      setEditingRecord({
        ...record,
        acquisition_type: null,
        disposal_date: null,
        acquisition_price_chf: null,
        land_register_ref: null,
        document_id: null,
        notes: null,
        source_type: null,
        confidence: null,
        source_ref: null,
        created_by: null,
        created_at: '',
        updated_at: '',
        owner_display_name: record.owner_display_name ?? null,
      });
    }
  };

  const records = ownershipPage?.items ?? [];
  const totalPages = ownershipPage?.pages ?? 1;

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      {summary && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <SummaryCard
            icon={<FileText className="w-4 h-4" />}
            label={t('ownership.total') || 'Total Records'}
            value={String(summary.total_records)}
          />
          <SummaryCard
            icon={<Users className="w-4 h-4" />}
            label={t('ownership.active') || 'Active'}
            value={String(summary.active_records)}
            highlight="green"
          />
          <SummaryCard
            icon={<FileText className="w-4 h-4" />}
            label={t('ownership.total_share') || 'Total Share'}
            value={`${summary.total_share_pct.toFixed(1)}%`}
          />
          <SummaryCard
            icon={<Users className="w-4 h-4" />}
            label={t('ownership.owner_count') || 'Owners'}
            value={String(summary.owner_count)}
          />
          <SummaryCard
            icon={<Shield className="w-4 h-4" />}
            label={t('ownership.co_ownership') || 'Co-ownership'}
            value={summary.co_ownership ? t('common.yes') || 'Yes' : t('common.no') || 'No'}
            highlight={summary.co_ownership ? 'orange' : undefined}
          />
        </div>
      )}

      {/* Actions bar */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('ownership.list_title') || 'Ownership Records'}
        </h3>
        <button
          onClick={() => setShowCreateModal(true)}
          className="inline-flex items-center gap-2 px-3 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
        >
          <Plus className="w-4 h-4" />
          {t('ownership.create') || 'Add Owner'}
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
          {t('ownership.load_error') || 'Failed to load ownership records.'}
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && (
        <>
          {records.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-slate-400">
              <Users className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p className="text-sm">{t('ownership.empty') || 'No ownership records found for this building.'}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-slate-700 text-left">
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('ownership.owner') || 'Owner'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('ownership.ownership_type') || 'Type'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400 text-right">
                      {t('ownership.share_pct') || 'Share %'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('ownership.acquisition_date') || 'Acquisition'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('ownership.status') || 'Status'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                  {records.map((record) => (
                    <tr key={record.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50">
                      <td className="py-3 font-medium text-gray-900 dark:text-white">
                        {record.owner_display_name || record.owner_id.slice(0, 8) + '...'}
                      </td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">
                        <span
                          className={cn(
                            'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
                            'bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
                          )}
                        >
                          {t(`ownership.type.${record.ownership_type}`) || record.ownership_type}
                        </span>
                      </td>
                      <td className="py-3 text-gray-900 dark:text-white text-right">
                        {record.share_pct != null ? `${record.share_pct}%` : '-'}
                      </td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">
                        {record.acquisition_date?.slice(0, 10) ?? '-'}
                      </td>
                      <td className="py-3">
                        <StatusBadge status={record.status} />
                      </td>
                      <td className="py-3">
                        <button
                          onClick={() => handleEdit(record)}
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
                {t('ownership.page') || 'Page'} {page} / {totalPages} ({ownershipPage?.total ?? 0}{' '}
                {t('ownership.total_items') || 'items'})
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
      {showCreateModal && <OwnershipFormModal buildingId={buildingId} onClose={() => setShowCreateModal(false)} />}

      {/* Edit modal */}
      {editingRecord && (
        <OwnershipFormModal
          buildingId={buildingId}
          initialData={editingRecord}
          onClose={() => setEditingRecord(null)}
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
