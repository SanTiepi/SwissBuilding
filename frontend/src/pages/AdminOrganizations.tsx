/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under Admin.
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { organizationsApi } from '@/api/organizations';
import { cn } from '@/utils/formatters';
import type { Organization, OrganizationType } from '@/types';
import {
  Plus,
  Loader2,
  AlertTriangle,
  Building2,
  X,
  Pencil,
  Trash2,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  Award,
} from 'lucide-react';

const ORG_TYPES: OrganizationType[] = [
  'diagnostic_lab',
  'architecture_firm',
  'property_management',
  'authority',
  'contractor',
];

const orgTypeColors: Record<string, string> = {
  diagnostic_lab: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  architecture_firm: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  property_management: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  authority: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  contractor: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

interface OrgFormData {
  name: string;
  type: OrganizationType;
  address: string;
  postal_code: string;
  city: string;
  canton: string;
  phone: string;
  email: string;
  suva_recognized: boolean;
  fach_approved: boolean;
}

const emptyForm: OrgFormData = {
  name: '',
  type: 'diagnostic_lab',
  address: '',
  postal_code: '',
  city: '',
  canton: '',
  phone: '',
  email: '',
  suva_recognized: false,
  fach_approved: false,
};

export default function AdminOrganizations() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [typeFilter, setTypeFilter] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [editingOrg, setEditingOrg] = useState<Organization | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<Organization | null>(null);
  const [formData, setFormData] = useState<OrgFormData>(emptyForm);

  const {
    data: orgsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['admin-organizations', page, pageSize, typeFilter],
    queryFn: () => {
      const params: Record<string, string | number> = { page, size: pageSize };
      if (typeFilter) params.type = typeFilter;
      return organizationsApi.list(params);
    },
  });

  const orgs = useMemo(() => orgsData?.items ?? [], [orgsData]);
  const totalPages = orgsData?.pages ?? 1;

  const createMutation = useMutation({
    mutationFn: (data: OrgFormData) => organizationsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-organizations'] });
      closeModal();
    },
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: OrgFormData }) => organizationsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-organizations'] });
      closeModal();
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => organizationsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-organizations'] });
      setDeleteConfirm(null);
    },
  });

  const closeModal = () => {
    setShowModal(false);
    setEditingOrg(null);
    setFormData(emptyForm);
  };

  const openCreate = () => {
    setFormData(emptyForm);
    setEditingOrg(null);
    setShowModal(true);
  };

  const openEdit = (org: Organization) => {
    setEditingOrg(org);
    setFormData({
      name: org.name,
      type: org.type,
      address: org.address || '',
      postal_code: org.postal_code || '',
      city: org.city || '',
      canton: org.canton || '',
      phone: org.phone || '',
      email: org.email || '',
      suva_recognized: org.suva_recognized,
      fach_approved: org.fach_approved,
    });
    setShowModal(true);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (editingOrg) {
      updateMutation.mutate({ id: editingOrg.id, data: formData });
    } else {
      createMutation.mutate(formData);
    }
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  const isSaving = createMutation.isPending || updateMutation.isPending;

  if (user?.role !== 'admin') {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-500 dark:text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('admin.access_denied') || 'Access denied'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('org.title') || 'Organizations'}</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {orgsData?.total ?? 0} {t('org.total') || 'total organizations'}
          </p>
        </div>
        <button
          onClick={openCreate}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t('org.create') || 'Create organization'}
        </button>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(1);
            }}
            aria-label={t('org.filter_type') || 'Filter by type'}
            className="flex-1 sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0"
          >
            <option value="">{t('org.all_types') || 'All types'}</option>
            {ORG_TYPES.map((ot) => (
              <option key={ot} value={ot}>
                {t(`org_type.${ot}`) || ot}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
          <AlertTriangle className="w-8 h-8 text-red-500 dark:text-red-400 mx-auto mb-2" />
          <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
        </div>
      ) : orgs.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-12 text-center">
          <Building2 className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400 text-sm">{t('org.no_orgs') || 'No organizations found'}</p>
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('org.name') || 'Name'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('org.type') || 'Type'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('org.city') || 'City'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('org.canton') || 'Canton'}
                  </th>
                  <th className="text-center px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('org.members') || 'Members'}
                  </th>
                  <th className="text-center px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('org.certifications') || 'Certifications'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('admin.created') || 'Created'}
                  </th>
                  <th className="text-right px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('admin.actions') || 'Actions'}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                {orgs.map((org) => (
                  <tr key={org.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors">
                    <td className="px-4 py-3 text-gray-900 dark:text-white font-medium whitespace-nowrap">
                      {org.name}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={cn(
                          'px-2 py-0.5 text-xs font-medium rounded-full',
                          orgTypeColors[org.type] || 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
                        )}
                      >
                        {t(`org_type.${org.type}`) || org.type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-300 whitespace-nowrap">{org.city || '-'}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-300 whitespace-nowrap">
                      {org.canton || '-'}
                    </td>
                    <td className="px-4 py-3 text-center text-gray-600 dark:text-slate-300">{org.member_count}</td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center justify-center gap-1.5">
                        {org.suva_recognized && (
                          <span
                            title="SUVA"
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400 rounded-full"
                          >
                            <ShieldCheck className="w-3 h-3" />
                            SUVA
                          </span>
                        )}
                        {org.fach_approved && (
                          <span
                            title="FACH"
                            className="inline-flex items-center gap-1 px-1.5 py-0.5 text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400 rounded-full"
                          >
                            <Award className="w-3 h-3" />
                            FACH
                          </span>
                        )}
                        {!org.suva_recognized && !org.fach_approved && (
                          <span className="text-gray-400 dark:text-slate-500 text-xs">-</span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-500 dark:text-slate-400 whitespace-nowrap">
                      {formatDate(org.created_at)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => openEdit(org)}
                          title={t('form.edit') || 'Edit'}
                          className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                        >
                          <Pencil className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setDeleteConfirm(org)}
                          title={t('form.delete') || 'Delete'}
                          className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-center gap-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            aria-label={t('pagination.previous')}
            className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg border border-gray-300 dark:border-slate-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors dark:text-slate-200"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
          <span className="text-sm text-gray-600 dark:text-slate-300">
            {t('pagination.page', { page, pages: totalPages })}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            aria-label={t('pagination.next')}
            className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg border border-gray-300 dark:border-slate-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors dark:text-slate-200"
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Create/Edit Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                {editingOrg ? t('org.edit') || 'Edit organization' : t('org.create') || 'Create organization'}
              </h2>
              <button
                onClick={closeModal}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                aria-label={t('form.close')}
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('org.name') || 'Name'} *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('org.type') || 'Type'} *
                  </label>
                  <select
                    required
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value as OrganizationType })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    {ORG_TYPES.map((ot) => (
                      <option key={ot} value={ot}>
                        {t(`org_type.${ot}`) || ot}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('org.address') || 'Address'}
                  </label>
                  <input
                    type="text"
                    value={formData.address}
                    onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('org.postal_code') || 'Postal code'}
                  </label>
                  <input
                    type="text"
                    value={formData.postal_code}
                    onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('org.city') || 'City'}
                  </label>
                  <input
                    type="text"
                    value={formData.city}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('org.canton') || 'Canton'}
                  </label>
                  <input
                    type="text"
                    value={formData.canton}
                    onChange={(e) => setFormData({ ...formData, canton: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('org.phone') || 'Phone'}
                  </label>
                  <input
                    type="tel"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('org.email') || 'Email'}
                  </label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div className="sm:col-span-2 flex flex-wrap gap-4">
                  <label className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={formData.suva_recognized}
                      onChange={(e) => setFormData({ ...formData, suva_recognized: e.target.checked })}
                      className="w-4 h-4 rounded border-gray-300 dark:border-slate-600 text-red-600 focus:ring-red-500 dark:bg-slate-700"
                    />
                    {t('org.suva_recognized') || 'SUVA recognized'}
                  </label>
                  <label className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300 cursor-pointer select-none">
                    <input
                      type="checkbox"
                      checked={formData.fach_approved}
                      onChange={(e) => setFormData({ ...formData, fach_approved: e.target.checked })}
                      className="w-4 h-4 rounded border-gray-300 dark:border-slate-600 text-red-600 focus:ring-red-500 dark:bg-slate-700"
                    />
                    {t('org.fach_approved') || 'FACH approved'}
                  </label>
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
                >
                  {t('form.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={isSaving}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
                >
                  {isSaving && <Loader2 className="w-4 h-4 animate-spin" />}
                  {editingOrg ? t('form.save') || 'Save' : t('form.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Delete Confirmation */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-6">
            <h2 className="text-lg font-bold text-gray-900 dark:text-white mb-2">
              {t('org.delete_confirm_title') || 'Delete organization'}
            </h2>
            <p className="text-sm text-gray-600 dark:text-slate-300 mb-6">
              {t('org.delete_confirm_body') || 'Are you sure you want to delete'}{' '}
              <span className="font-semibold">{deleteConfirm.name}</span>?
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setDeleteConfirm(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                {t('form.cancel')}
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteConfirm.id)}
                disabled={deleteMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
              >
                {deleteMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                {t('form.delete') || 'Delete'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
