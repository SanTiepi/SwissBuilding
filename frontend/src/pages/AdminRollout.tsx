import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { rolloutApi } from '@/api/rollout';
import type { AccessGrantCreate } from '@/api/rollout';
import { cn, formatDate } from '@/utils/formatters';
import { Loader2, AlertTriangle, ShieldCheck, XCircle, Plus, Clock } from 'lucide-react';

export default function AdminRollout() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState<AccessGrantCreate>({
    building_id: '',
    grantee_email: '',
    grant_type: 'viewer',
    scope: 'read',
  });

  const {
    data: grantsData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['rollout-grants'],
    queryFn: () => rolloutApi.listGrants({ size: 50 }),
  });

  const { data: events = [] } = useQuery({
    queryKey: ['rollout-events'],
    queryFn: () => rolloutApi.listEvents({ limit: 20 }),
  });

  const createMutation = useMutation({
    mutationFn: (data: AccessGrantCreate) => rolloutApi.createGrant(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rollout-grants'] });
      queryClient.invalidateQueries({ queryKey: ['rollout-events'] });
      setShowForm(false);
      setFormData({ building_id: '', grantee_email: '', grant_type: 'viewer', scope: 'read' });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (grantId: string) => rolloutApi.revokeGrant(grantId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['rollout-grants'] });
      queryClient.invalidateQueries({ queryKey: ['rollout-events'] });
    },
  });

  const grants = grantsData?.items ?? [];

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
      </div>
    );
  }

  const grantTypeBadge = (gtype: string) => {
    const colors: Record<string, string> = {
      viewer: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
      collaborator: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
      admin: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300',
    };
    return colors[gtype] || 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300';
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('rollout.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('rollout.description')}</p>
        </div>
        <button
          onClick={() => setShowForm(!showForm)}
          data-testid="rollout-create-button"
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
        >
          <Plus className="w-4 h-4" />
          {t('rollout.create_grant')}
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div
          className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6"
          data-testid="rollout-create-form"
        >
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">{t('rollout.create_grant')}</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('rollout.building_id')}
              </label>
              <input
                type="text"
                value={formData.building_id}
                onChange={(e) => setFormData({ ...formData, building_id: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                data-testid="rollout-building-id"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('rollout.grantee_email')}
              </label>
              <input
                type="email"
                value={formData.grantee_email}
                onChange={(e) => setFormData({ ...formData, grantee_email: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                data-testid="rollout-grantee-email"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('rollout.grant_type')}
              </label>
              <select
                value={formData.grant_type}
                onChange={(e) => setFormData({ ...formData, grant_type: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                data-testid="rollout-grant-type"
              >
                <option value="viewer">Viewer</option>
                <option value="collaborator">Collaborator</option>
                <option value="admin">Admin</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('rollout.scope')}
              </label>
              <select
                value={formData.scope}
                onChange={(e) => setFormData({ ...formData, scope: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                data-testid="rollout-scope"
              >
                <option value="read">Read</option>
                <option value="write">Write</option>
                <option value="full">Full</option>
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('rollout.expires_at')}
              </label>
              <input
                type="date"
                value={formData.expires_at || ''}
                onChange={(e) => setFormData({ ...formData, expires_at: e.target.value || null })}
                className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
                data-testid="rollout-expires-at"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <button
              onClick={() => setShowForm(false)}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-300 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
            >
              {t('form.cancel')}
            </button>
            <button
              onClick={() => createMutation.mutate(formData)}
              disabled={createMutation.isPending || !formData.building_id || !formData.grantee_email}
              className="px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50"
              data-testid="rollout-submit"
            >
              {createMutation.isPending ? t('app.loading') : t('form.save')}
            </button>
          </div>
        </div>
      )}

      {/* Grants Table */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-red-600" />
            {t('rollout.active_grants')}
          </h2>
        </div>
        {grants.length === 0 ? (
          <div className="p-8 text-center text-gray-500 dark:text-slate-400">{t('rollout.empty')}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm" data-testid="rollout-grants-table">
              <thead className="bg-gray-50 dark:bg-slate-700/50">
                <tr>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('rollout.building')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('rollout.grantee')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('rollout.grant_type')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('rollout.scope')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('rollout.expires_at')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('form.actions')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
                {grants.map((grant) => (
                  <tr key={grant.id} data-testid={`grant-row-${grant.id}`}>
                    <td className="px-4 py-3 text-gray-900 dark:text-white">{grant.building_address}</td>
                    <td className="px-4 py-3 text-gray-900 dark:text-white">
                      {grant.grantee_email}
                      {grant.grantee_org_name && (
                        <span className="text-xs text-gray-500 dark:text-slate-400 block">
                          {grant.grantee_org_name}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={cn('px-2 py-0.5 text-xs font-medium rounded-full', grantTypeBadge(grant.grant_type))}
                      >
                        {grant.grant_type}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-700 dark:text-slate-300">{grant.scope}</td>
                    <td className="px-4 py-3 text-gray-700 dark:text-slate-300">
                      {grant.expires_at ? formatDate(grant.expires_at) : '-'}
                    </td>
                    <td className="px-4 py-3">
                      {!grant.revoked_at ? (
                        <button
                          onClick={() => revokeMutation.mutate(grant.id)}
                          disabled={revokeMutation.isPending}
                          className="inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300"
                          data-testid={`revoke-${grant.id}`}
                        >
                          <XCircle className="w-3.5 h-3.5" />
                          {t('rollout.revoke')}
                        </button>
                      ) : (
                        <span className="text-xs text-gray-400 dark:text-slate-500">{t('rollout.revoked')}</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Event Log */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 dark:border-slate-700">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
            <Clock className="w-5 h-5 text-gray-500 dark:text-slate-400" />
            {t('rollout.event_log')}
          </h2>
        </div>
        {events.length === 0 ? (
          <div className="p-6 text-center text-gray-500 dark:text-slate-400">{t('rollout.no_events')}</div>
        ) : (
          <ul className="divide-y divide-gray-200 dark:divide-slate-700" data-testid="rollout-events-list">
            {events.map((ev) => (
              <li key={ev.id} className="px-6 py-3 flex items-center justify-between">
                <div>
                  <span className="text-sm text-gray-900 dark:text-white">{ev.detail}</span>
                  <span className="ml-2 text-xs text-gray-500 dark:text-slate-400">{ev.actor_email}</span>
                </div>
                <span className="text-xs text-gray-400 dark:text-slate-500">{formatDate(ev.created_at)}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
