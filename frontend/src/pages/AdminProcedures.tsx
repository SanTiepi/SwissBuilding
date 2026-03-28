/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under Admin.
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/utils/formatters';
import { permitProceduresApi } from '@/api/permitProcedures';
import type { ProcedureStatus, ProcedureListItem } from '@/api/permitProcedures';
import { Loader2, AlertTriangle, ClipboardList, Building2, ExternalLink, Filter } from 'lucide-react';

const STATUS_OPTIONS: ProcedureStatus[] = [
  'complement_requested',
  'submitted',
  'under_review',
  'draft',
  'approved',
  'rejected',
  'expired',
  'withdrawn',
];

const STATUS_COLORS: Record<ProcedureStatus, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
  submitted: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  under_review: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  complement_requested: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  approved: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  expired: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-400',
  withdrawn: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-400',
};

export default function AdminProcedures() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const [statusFilter, setStatusFilter] = useState<ProcedureStatus | ''>('');
  const [typeFilter, setTypeFilter] = useState('');
  const [page, setPage] = useState(1);

  const isAdmin = !!user && user.role === 'admin';

  const { data, isLoading, isError } = useQuery({
    queryKey: ['admin-procedures', statusFilter, typeFilter, page],
    queryFn: () =>
      permitProceduresApi.getAdminProcedures({
        status: statusFilter || undefined,
        procedure_type: typeFilter || undefined,
        page,
        size: 25,
      }),
    enabled: isAdmin,
  });

  const items = data?.items ?? [];
  const totalPages = data?.pages ?? 1;

  // Admin guard
  if (!isAdmin) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-slate-400">
        <AlertTriangle className="w-8 h-8 mx-auto mb-3 text-orange-500" />
        <p>{t('admin.access_denied') || 'Admin access required.'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-procedures-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ClipboardList className="w-6 h-6 text-red-600" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('procedure.admin_title') || 'All Procedures'}
          </h1>
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3" data-testid="procedure-filters">
        <Filter className="w-4 h-4 text-gray-400" />
        <select
          value={statusFilter}
          onChange={(e) => {
            setStatusFilter(e.target.value as ProcedureStatus | '');
            setPage(1);
          }}
          data-testid="filter-status"
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
        >
          <option value="">{t('procedure.all_statuses') || 'All statuses'}</option>
          {STATUS_OPTIONS.map((s) => (
            <option key={s} value={s}>
              {t(`procedure.status.${s}`) || s.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
        <input
          type="text"
          value={typeFilter}
          onChange={(e) => {
            setTypeFilter(e.target.value);
            setPage(1);
          }}
          placeholder={t('procedure.filter_type') || 'Filter by type...'}
          data-testid="filter-type"
          className="px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500 w-48"
        />
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
          {t('procedure.load_error') || 'Failed to load procedures.'}
        </div>
      )}

      {/* Table */}
      {!isLoading && !isError && (
        <>
          {items.length === 0 ? (
            <div className="text-center py-12 text-gray-500 dark:text-slate-400">
              <ClipboardList className="w-10 h-10 mx-auto mb-3 opacity-40" />
              <p className="text-sm">{t('procedure.empty') || 'No procedures found.'}</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm" data-testid="procedures-table">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-slate-700 text-left">
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('procedure.building') || 'Building'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('procedure.title_col') || 'Procedure'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('procedure.status_col') || 'Status'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400">
                      {t('procedure.authority') || 'Authority'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400 text-right">
                      {t('procedure.days_pending') || 'Days'}
                    </th>
                    <th className="pb-3 font-medium text-gray-500 dark:text-slate-400 text-right">
                      {t('procedure.requests') || 'Requests'}
                    </th>
                    <th className="pb-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                  {items.map((item: ProcedureListItem) => (
                    <tr
                      key={item.id}
                      className="hover:bg-gray-50 dark:hover:bg-slate-700/50"
                      data-testid={`procedure-row-${item.id}`}
                    >
                      <td className="py-3">
                        <div className="flex items-center gap-1.5">
                          <Building2 className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
                          <span className="text-gray-900 dark:text-white text-sm truncate max-w-[200px]">
                            {item.building_address || item.building_id.slice(0, 8)}
                          </span>
                        </div>
                      </td>
                      <td className="py-3">
                        <div>
                          <span className="font-medium text-gray-900 dark:text-white">{item.title}</span>
                          <span className="ml-2 text-xs text-gray-400">{item.procedure_type.replace(/_/g, ' ')}</span>
                        </div>
                      </td>
                      <td className="py-3">
                        <span
                          className={cn(
                            'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
                            STATUS_COLORS[item.status] || STATUS_COLORS.draft,
                          )}
                        >
                          {t(`procedure.status.${item.status}`) || item.status.replace(/_/g, ' ')}
                        </span>
                        {item.blocks_activities && <AlertTriangle className="w-3 h-3 text-red-500 inline ml-1" />}
                      </td>
                      <td className="py-3 text-gray-600 dark:text-slate-300">{item.authority_name}</td>
                      <td className="py-3 text-right">
                        <span
                          className={cn(
                            'text-sm font-medium',
                            item.days_pending > 30
                              ? 'text-red-600 dark:text-red-400'
                              : item.days_pending > 14
                                ? 'text-orange-600 dark:text-orange-400'
                                : 'text-gray-600 dark:text-slate-300',
                          )}
                        >
                          {item.days_pending}
                        </span>
                      </td>
                      <td className="py-3 text-right">
                        {item.open_requests > 0 ? (
                          <span className="inline-block px-1.5 py-0.5 text-xs font-medium bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400 rounded-full">
                            {item.open_requests}
                          </span>
                        ) : (
                          <span className="text-gray-400">-</span>
                        )}
                      </td>
                      <td className="py-3">
                        <Link
                          to={`/buildings/${item.building_id}`}
                          className="p-1.5 text-gray-400 hover:text-gray-700 dark:hover:text-white hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg inline-flex"
                          title={t('procedure.view_building') || 'View building'}
                        >
                          <ExternalLink className="w-4 h-4" />
                        </Link>
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
                {t('lease.page') || 'Page'} {page} / {totalPages} ({data?.total ?? 0}{' '}
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
    </div>
  );
}
