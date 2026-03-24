import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { workspaceApi, type WorkspaceMember } from '@/api/workspace';
import { Plus, X, Loader2, Users, Trash2, Shield } from 'lucide-react';

const ROLE_COLORS: Record<string, string> = {
  owner: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  manager: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  editor: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  viewer: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  diagnostician: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  contractor: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
};

const ROLES = ['owner', 'manager', 'editor', 'viewer', 'diagnostician', 'contractor'] as const;
const ACCESS_SCOPES = ['full', 'read_only', 'diagnostics_only', 'documents_only'] as const;

function RoleBadge({ role }: { role: string }) {
  const { t } = useTranslation();
  return (
    <span
      className={cn(
        'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
        ROLE_COLORS[role] || ROLE_COLORS.viewer,
      )}
      data-testid="member-role-badge"
    >
      {t(`workspace.role.${role}`) || role}
    </span>
  );
}

function ScopeBadge({ scope }: { scope: string }) {
  const { t } = useTranslation();
  return (
    <span
      className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-400"
      data-testid="member-scope-badge"
    >
      <Shield className="w-2.5 h-2.5" />
      {t(`workspace.scope.${scope}`) || scope}
    </span>
  );
}

interface Props {
  buildingId: string;
}

export default function WorkspaceMembersCard({ buildingId }: Props) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [formRole, setFormRole] = useState<string>(ROLES[3]);
  const [formScope, setFormScope] = useState<string>(ACCESS_SCOPES[0]);
  const [formUserId, setFormUserId] = useState('');
  const [formOrgId, setFormOrgId] = useState('');

  const {
    data: members = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['workspace-members', buildingId],
    queryFn: () => workspaceApi.listMembers(buildingId),
    enabled: !!buildingId,
    retry: false,
  });

  const addMutation = useMutation({
    mutationFn: (data: { user_id?: string | null; organization_id?: string | null; role: string; access_scope: string }) =>
      workspaceApi.addMember(buildingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members', buildingId] });
      resetForm();
    },
  });

  const removeMutation = useMutation({
    mutationFn: (memberId: string) => workspaceApi.removeMember(buildingId, memberId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['workspace-members', buildingId] });
    },
  });

  const resetForm = () => {
    setShowForm(false);
    setFormRole(ROLES[3]);
    setFormScope(ACCESS_SCOPES[0]);
    setFormUserId('');
    setFormOrgId('');
  };

  const handleSubmit = () => {
    addMutation.mutate({
      user_id: formUserId || null,
      organization_id: formOrgId || null,
      role: formRole,
      access_scope: formScope,
    });
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg shadow p-4 sm:p-6" data-testid="workspace-members-card">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('workspace.title') || 'Workspace Members'}
          </h3>
          {members.length > 0 && (
            <span className="px-1.5 py-0.5 text-xs font-medium rounded-full bg-gray-100 dark:bg-slate-700 text-gray-500 dark:text-slate-400">
              {members.length}
            </span>
          )}
        </div>
        {!showForm && (
          <button
            onClick={() => setShowForm(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 transition-colors"
            data-testid="workspace-add-member-btn"
          >
            <Plus className="w-4 h-4" />
            <span className="hidden sm:inline">{t('workspace.add_member') || 'Add member'}</span>
          </button>
        )}
      </div>

      {/* Add form */}
      {showForm && (
        <div
          className="mb-4 p-4 border border-blue-200 dark:border-blue-800 rounded-lg bg-blue-50 dark:bg-blue-900/20"
          data-testid="workspace-add-form"
        >
          <div className="space-y-3">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('workspace.field.user_id') || 'User ID'}
              </label>
              <input
                type="text"
                value={formUserId}
                onChange={(e) => setFormUserId(e.target.value)}
                className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder={t('workspace.field.user_id_placeholder') || 'Enter user ID or email'}
                data-testid="workspace-user-id-input"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('workspace.field.org_id') || 'Organization ID'}
              </label>
              <input
                type="text"
                value={formOrgId}
                onChange={(e) => setFormOrgId(e.target.value)}
                className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                placeholder={t('workspace.field.org_id_placeholder') || 'Enter organization ID'}
                data-testid="workspace-org-id-input"
              />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  {t('workspace.field.role') || 'Role'}
                </label>
                <select
                  value={formRole}
                  onChange={(e) => setFormRole(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="workspace-role-select"
                >
                  {ROLES.map((r) => (
                    <option key={r} value={r}>
                      {t(`workspace.role.${r}`) || r}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                  {t('workspace.field.scope') || 'Access scope'}
                </label>
                <select
                  value={formScope}
                  onChange={(e) => setFormScope(e.target.value)}
                  className="w-full rounded-md border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white px-3 py-2 text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  data-testid="workspace-scope-select"
                >
                  {ACCESS_SCOPES.map((s) => (
                    <option key={s} value={s}>
                      {t(`workspace.scope.${s}`) || s}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <div className="flex items-center gap-2 justify-end">
              <button
                onClick={resetForm}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
                data-testid="workspace-cancel-btn"
              >
                <X className="w-4 h-4" />
                {t('common.cancel') || 'Cancel'}
              </button>
              <button
                onClick={handleSubmit}
                disabled={addMutation.isPending || (!formUserId && !formOrgId)}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-md bg-blue-600 text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="workspace-submit-btn"
              >
                {addMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
                {t('workspace.add_member') || 'Add member'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-8" data-testid="workspace-loading">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="text-center py-8 text-red-600 dark:text-red-400" data-testid="workspace-error">
          <p className="text-sm">{t('app.error') || 'An error occurred'}</p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && members.length === 0 && (
        <div className="text-center py-8 text-gray-500 dark:text-slate-400" data-testid="workspace-empty">
          <Users className="w-8 h-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">{t('workspace.empty') || 'No workspace members'}</p>
        </div>
      )}

      {/* Member list */}
      {!isLoading && !isError && members.length > 0 && (
        <div className="space-y-3" data-testid="workspace-member-list">
          {members.map((member: WorkspaceMember) => (
            <div
              key={member.id}
              className="p-3 rounded-lg border border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2"
              data-testid="workspace-member-item"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-medium text-gray-900 dark:text-white truncate">
                    {member.user_name || member.user_email || member.org_name || t('workspace.unknown_member') || 'Unknown'}
                  </span>
                  <RoleBadge role={member.role} />
                  <ScopeBadge scope={member.access_scope} />
                </div>
                {member.org_name && member.user_name && (
                  <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">{member.org_name}</p>
                )}
              </div>
              <button
                onClick={() => removeMutation.mutate(member.id)}
                disabled={removeMutation.isPending}
                className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors"
                data-testid="workspace-remove-btn"
                title={t('workspace.remove_member') || 'Remove member'}
              >
                <Trash2 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{t('workspace.remove') || 'Remove'}</span>
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
