import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { usersApi } from '@/api/users';
import { invitationsApi } from '@/api/invitations';
import { organizationsApi } from '@/api/organizations';
import { cn } from '@/utils/formatters';
import type { User, UserRole, Invitation, Organization } from '@/types';
import {
  Plus,
  Search,
  Loader2,
  AlertTriangle,
  Users,
  X,
  Pencil,
  UserX,
  UserCheck,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Mail,
  KeyRound,
  Send,
  RotateCcw,
  Ban,
  Clock,
  CheckCircle2,
  XCircle,
  Shield,
  ArrowUpDown,
  UserPlus,
} from 'lucide-react';

const ROLES: UserRole[] = ['admin', 'owner', 'diagnostician', 'architect', 'authority', 'contractor'];

const roleColors: Record<string, string> = {
  admin: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  owner: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  diagnostician: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  architect: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  authority: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  contractor: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

const invitationStatusColors: Record<string, string> = {
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  accepted: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  expired: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
  revoked: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

interface CreateUserForm {
  email: string;
  first_name: string;
  last_name: string;
  role: UserRole;
  organization_id: string;
  password: string;
}

interface InviteForm {
  email: string;
  role: UserRole;
  organization_id: string;
  message: string;
}

type SortField = 'name' | 'role' | 'last_login';
type SortDir = 'asc' | 'desc';
type ActiveTab = 'users' | 'invitations';

const emptyForm: CreateUserForm = {
  email: '',
  first_name: '',
  last_name: '',
  role: 'diagnostician',
  organization_id: '',
  password: '',
};

const emptyInviteForm: InviteForm = {
  email: '',
  role: 'diagnostician',
  organization_id: '',
  message: '',
};

/* ------------------------------------------------------------------ */
/*  Confirmation Dialog                                                */
/* ------------------------------------------------------------------ */
function ConfirmDialog({
  open,
  title,
  message,
  onConfirm,
  onCancel,
  loading,
  variant = 'danger',
}: {
  open: boolean;
  title: string;
  message: string;
  onConfirm: () => void;
  onCancel: () => void;
  loading?: boolean;
  variant?: 'danger' | 'primary';
}) {
  const { t } = useTranslation();
  if (!open) return null;
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-6">
        <h3 className="text-lg font-bold text-gray-900 dark:text-white mb-2">{title}</h3>
        <p className="text-sm text-gray-600 dark:text-slate-300 mb-6">{message}</p>
        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
          >
            {t('form.cancel')}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            className={cn(
              'inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white rounded-lg disabled:opacity-50',
              variant === 'danger' ? 'bg-red-600 hover:bg-red-700' : 'bg-blue-600 hover:bg-blue-700',
            )}
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {t('form.confirm')}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Summary Card                                                       */
/* ------------------------------------------------------------------ */
function SummaryCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
      <div className="flex items-center gap-3">
        <div className={cn('p-2.5 rounded-lg', color)}>
          <Icon className="w-5 h-5" />
        </div>
        <div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
          <p className="text-xs text-gray-500 dark:text-slate-400">{label}</p>
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */
export default function AdminUsers() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  // --- tab ---
  const [activeTab, setActiveTab] = useState<ActiveTab>('users');

  // --- users list state ---
  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [orgFilter, setOrgFilter] = useState('');
  const [sortField, setSortField] = useState<SortField>('name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  // --- modals ---
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showInviteModal, setShowInviteModal] = useState(false);
  const [formData, setFormData] = useState<CreateUserForm>(emptyForm);
  const [inviteFormData, setInviteFormData] = useState<InviteForm>(emptyInviteForm);

  // --- expanded user detail ---
  const [expandedUserId, setExpandedUserId] = useState<string | null>(null);

  // --- confirmation dialogs ---
  const [confirmState, setConfirmState] = useState<{
    open: boolean;
    title: string;
    message: string;
    action: (() => void) | null;
    variant: 'danger' | 'primary';
  }>({ open: false, title: '', message: '', action: null, variant: 'danger' });

  // --- role editing ---
  const [editingUser, setEditingUser] = useState<User | null>(null);
  const [editRole, setEditRole] = useState<UserRole>('diagnostician');

  // --- invitations state ---
  const [invPage, setInvPage] = useState(1);
  const [invStatusFilter, setInvStatusFilter] = useState('');

  /* ---------------------------------------------------------------- */
  /*  Queries                                                          */
  /* ---------------------------------------------------------------- */
  const {
    data: usersData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['admin-users', page, pageSize, search, roleFilter, statusFilter, orgFilter],
    queryFn: () =>
      usersApi.list({
        page,
        size: pageSize,
        search: search || undefined,
        role: roleFilter || undefined,
        is_active: statusFilter ? (statusFilter === 'active' ? 'true' : 'false') : undefined,
      }),
  });

  const { data: orgsData } = useQuery({
    queryKey: ['admin-organizations-all'],
    queryFn: () => organizationsApi.list({ page: 1, size: 200 }),
  });

  const { data: invitationsData, isLoading: invLoading } = useQuery({
    queryKey: ['admin-invitations', invPage, invStatusFilter],
    queryFn: () =>
      invitationsApi.list({
        page: invPage,
        size: 20,
        status: invStatusFilter || undefined,
      }),
  });

  const organizations: Organization[] = useMemo(() => orgsData?.items ?? [], [orgsData]);
  const orgMap = useMemo(() => {
    const m = new Map<string, Organization>();
    organizations.forEach((o) => m.set(o.id, o));
    return m;
  }, [organizations]);

  // --- sorted + filtered users ---
  const rawUsers = useMemo(() => usersData?.items ?? [], [usersData]);
  const users = useMemo(() => {
    let filtered = rawUsers;
    // org filter (client-side since API doesn't support it)
    if (orgFilter) {
      filtered = filtered.filter((u) =>
        orgFilter === '__none__' ? !u.organization_id : u.organization_id === orgFilter,
      );
    }
    // sort
    const sorted = [...filtered].sort((a, b) => {
      let cmp = 0;
      if (sortField === 'name') {
        cmp = `${a.first_name} ${a.last_name}`.localeCompare(`${b.first_name} ${b.last_name}`);
      } else if (sortField === 'role') {
        cmp = a.role.localeCompare(b.role);
      } else if (sortField === 'last_login') {
        cmp = a.updated_at.localeCompare(b.updated_at);
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [rawUsers, orgFilter, sortField, sortDir]);

  const totalPages = usersData?.pages ?? 1;
  const invitations = useMemo(() => invitationsData?.items ?? [], [invitationsData]);
  const invTotalPages = invitationsData?.pages ?? 1;

  // --- summary stats ---
  const totalUsers = usersData?.total ?? 0;
  const activeUsers = useMemo(() => rawUsers.filter((u) => u.is_active).length, [rawUsers]);
  const pendingInvitations = useMemo(() => invitations.filter((i) => i.status === 'pending').length, [invitations]);
  const rolesDistribution = useMemo(() => {
    const dist: Record<string, number> = {};
    rawUsers.forEach((u) => {
      dist[u.role] = (dist[u.role] || 0) + 1;
    });
    return dist;
  }, [rawUsers]);

  /* ---------------------------------------------------------------- */
  /*  Mutations                                                        */
  /* ---------------------------------------------------------------- */
  const createMutation = useMutation({
    mutationFn: (data: CreateUserForm) => usersApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setShowCreateModal(false);
      setFormData(emptyForm);
    },
  });

  const updateRoleMutation = useMutation({
    mutationFn: ({ id, role }: { id: string; role: UserRole }) => usersApi.update(id, { role }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setEditingUser(null);
    },
  });

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) => usersApi.update(id, { is_active }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      setConfirmState((s) => ({ ...s, open: false }));
    },
  });

  const inviteCreateMutation = useMutation({
    mutationFn: (data: { email: string; role: string; organization_id?: string }) => invitationsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-invitations'] });
      setShowInviteModal(false);
      setInviteFormData(emptyInviteForm);
    },
  });

  const inviteRevokeMutation = useMutation({
    mutationFn: (id: string) => invitationsApi.revoke(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-invitations'] });
      setConfirmState((s) => ({ ...s, open: false }));
    },
  });

  /* ---------------------------------------------------------------- */
  /*  Handlers                                                         */
  /* ---------------------------------------------------------------- */
  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const handleEditRole = (u: User) => {
    setEditingUser(u);
    setEditRole(u.role);
  };

  const handleSaveRole = () => {
    if (!editingUser || editRole === editingUser.role) {
      setEditingUser(null);
      return;
    }
    const name = `${editingUser.first_name} ${editingUser.last_name}`;
    const fromLabel = t(`role.${editingUser.role}`) || editingUser.role;
    const toLabel = t(`role.${editRole}`) || editRole;
    setConfirmState({
      open: true,
      title: t('admin.change_role_confirm') || 'Confirm role change',
      message: (t('admin.change_role_message') || "Change {name}'s role from {from} to {to}?")
        .replace('{name}', name)
        .replace('{from}', fromLabel)
        .replace('{to}', toLabel),
      action: () => {
        if (editingUser) {
          updateRoleMutation.mutate({ id: editingUser.id, role: editRole });
        }
        setConfirmState((s) => ({ ...s, open: false }));
      },
      variant: 'primary',
    });
  };

  const handleToggleActive = useCallback(
    (u: User) => {
      const name = `${u.first_name} ${u.last_name}`;
      if (u.is_active) {
        setConfirmState({
          open: true,
          title: t('admin.deactivate_confirm') || 'Confirm deactivation',
          message: (t('admin.deactivate_message') || "Deactivate {name}'s account?").replace('{name}', name),
          action: () => toggleActiveMutation.mutate({ id: u.id, is_active: false }),
          variant: 'danger',
        });
      } else {
        setConfirmState({
          open: true,
          title: t('admin.activate_confirm') || 'Confirm reactivation',
          message: (t('admin.activate_message') || "Reactivate {name}'s account?").replace('{name}', name),
          action: () => toggleActiveMutation.mutate({ id: u.id, is_active: true }),
          variant: 'primary',
        });
      }
    },
    [t, toggleActiveMutation],
  );

  const handleInvite = (e: React.FormEvent) => {
    e.preventDefault();
    inviteCreateMutation.mutate({
      email: inviteFormData.email,
      role: inviteFormData.role,
      organization_id: inviteFormData.organization_id || undefined,
    });
  };

  const handleRevokeInvitation = useCallback(
    (inv: Invitation) => {
      setConfirmState({
        open: true,
        title: t('admin.revoke') || 'Revoke',
        message: t('admin.revoke_confirm') || 'Revoke this invitation?',
        action: () => inviteRevokeMutation.mutate(inv.id),
        variant: 'danger',
      });
    },
    [t, inviteRevokeMutation],
  );

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  const formatDate = (dateStr: string | null | undefined) => {
    if (!dateStr) return t('admin.never_logged_in') || 'Never';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const formatDateTime = (dateStr: string | null | undefined) => {
    if (!dateStr) return '-';
    try {
      return new Date(dateStr).toLocaleDateString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) return <ArrowUpDown className="w-3.5 h-3.5 opacity-40" />;
    return sortDir === 'asc' ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />;
  };

  /* ---------------------------------------------------------------- */
  /*  Access guard                                                     */
  /* ---------------------------------------------------------------- */
  if (user?.role !== 'admin') {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-500 dark:text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('admin.access_denied') || 'Access denied'}</p>
      </div>
    );
  }

  /* ---------------------------------------------------------------- */
  /*  Render                                                           */
  /* ---------------------------------------------------------------- */
  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          label={t('admin.total_users') || 'Total users'}
          value={totalUsers}
          icon={Users}
          color="bg-blue-100 text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
        />
        <SummaryCard
          label={t('admin.active_users') || 'Active users'}
          value={activeUsers}
          icon={UserCheck}
          color="bg-green-100 text-green-600 dark:bg-green-900/30 dark:text-green-400"
        />
        <SummaryCard
          label={t('admin.pending_invitations') || 'Pending invitations'}
          value={pendingInvitations}
          icon={Mail}
          color="bg-yellow-100 text-yellow-600 dark:bg-yellow-900/30 dark:text-yellow-400"
        />
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2.5 rounded-lg bg-purple-100 text-purple-600 dark:bg-purple-900/30 dark:text-purple-400">
              <Shield className="w-5 h-5" />
            </div>
            <p className="text-xs text-gray-500 dark:text-slate-400">
              {t('admin.roles_distribution') || 'Roles distribution'}
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {ROLES.map((r) => (
              <span key={r} className={cn('px-1.5 py-0.5 text-[10px] font-medium rounded-full', roleColors[r])}>
                {t(`role.${r}`) || r}: {rolesDistribution[r] || 0}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Header with tabs */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex gap-1 bg-gray-100 dark:bg-slate-700 rounded-lg p-1">
          <button
            onClick={() => setActiveTab('users')}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-md transition-colors',
              activeTab === 'users'
                ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200',
            )}
          >
            <Users className="w-4 h-4 inline mr-1.5 -mt-0.5" />
            {t('admin.tab_users') || 'Users'} ({totalUsers})
          </button>
          <button
            onClick={() => setActiveTab('invitations')}
            className={cn(
              'px-4 py-2 text-sm font-medium rounded-md transition-colors',
              activeTab === 'invitations'
                ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200',
            )}
          >
            <Mail className="w-4 h-4 inline mr-1.5 -mt-0.5" />
            {t('admin.tab_invitations') || 'Invitations'} ({invitationsData?.total ?? 0})
          </button>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => setShowInviteModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            <UserPlus className="w-4 h-4" />
            {t('admin.invite_user') || 'Invite user'}
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            {t('admin.create_user') || 'Create user'}
          </button>
        </div>
      </div>

      {/* ============================================================ */}
      {/*  USERS TAB                                                    */}
      {/* ============================================================ */}
      {activeTab === 'users' && (
        <>
          {/* Filters */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-3 sm:p-4 shadow-sm overflow-hidden">
            <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-2 sm:gap-3">
              <div className="relative w-full sm:flex-1 sm:min-w-[200px]">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-slate-500" />
                <input
                  type="text"
                  value={search}
                  onChange={(e) => {
                    setSearch(e.target.value);
                    setPage(1);
                  }}
                  placeholder={t('admin.search_users') || 'Search by name or email...'}
                  aria-label={t('admin.search_users') || 'Search users'}
                  className="w-full pl-9 pr-4 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                />
              </div>
              <select
                value={roleFilter}
                onChange={(e) => {
                  setRoleFilter(e.target.value);
                  setPage(1);
                }}
                aria-label={t('admin.filter_role') || 'Filter by role'}
                className="w-full sm:w-auto sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0"
              >
                <option value="">{t('admin.all_roles') || 'All roles'}</option>
                {ROLES.map((r) => (
                  <option key={r} value={r}>
                    {t(`role.${r}`) || r}
                  </option>
                ))}
              </select>
              <select
                value={orgFilter}
                onChange={(e) => {
                  setOrgFilter(e.target.value);
                  setPage(1);
                }}
                aria-label={t('admin.filter_org') || 'Filter by organization'}
                className="w-full sm:w-auto sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0"
              >
                <option value="">{t('admin.all_organizations') || 'All organizations'}</option>
                <option value="__none__">{t('admin.no_organization') || 'No organization'}</option>
                {organizations.map((o) => (
                  <option key={o.id} value={o.id}>
                    {o.name}
                  </option>
                ))}
              </select>
              <select
                value={statusFilter}
                onChange={(e) => {
                  setStatusFilter(e.target.value);
                  setPage(1);
                }}
                aria-label={t('admin.filter_status') || 'Filter by status'}
                className="w-full sm:w-auto sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0"
              >
                <option value="">{t('admin.all_statuses') || 'All statuses'}</option>
                <option value="active">{t('admin.active') || 'Active'}</option>
                <option value="inactive">{t('admin.inactive') || 'Inactive'}</option>
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
          ) : users.length === 0 ? (
            <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-12 text-center">
              <Users className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-slate-400 text-sm">{t('admin.no_users') || 'No users found'}</p>
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
                      <th
                        className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400 cursor-pointer select-none hover:text-gray-700 dark:hover:text-slate-200"
                        onClick={() => handleSort('name')}
                      >
                        <span className="inline-flex items-center gap-1">
                          {t('admin.name') || 'Name'}
                          {renderSortIcon('name')}
                        </span>
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('admin.email') || 'Email'}
                      </th>
                      <th
                        className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400 cursor-pointer select-none hover:text-gray-700 dark:hover:text-slate-200"
                        onClick={() => handleSort('role')}
                      >
                        <span className="inline-flex items-center gap-1">
                          {t('admin.role') || 'Role'}
                          {renderSortIcon('role')}
                        </span>
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('admin.organization') || 'Organization'}
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('admin.status') || 'Status'}
                      </th>
                      <th
                        className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400 cursor-pointer select-none hover:text-gray-700 dark:hover:text-slate-200"
                        onClick={() => handleSort('last_login')}
                      >
                        <span className="inline-flex items-center gap-1">
                          {t('admin.last_login') || 'Last login'}
                          {renderSortIcon('last_login')}
                        </span>
                      </th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('admin.actions') || 'Actions'}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                    {users.map((u) => {
                      const isExpanded = expandedUserId === u.id;
                      const org = u.organization_id ? orgMap.get(u.organization_id) : null;
                      return (
                        <UserRow
                          key={u.id}
                          u={u}
                          org={org ?? null}
                          isExpanded={isExpanded}
                          onToggleExpand={() => setExpandedUserId(isExpanded ? null : u.id)}
                          onEditRole={() => handleEditRole(u)}
                          onToggleActive={() => handleToggleActive(u)}
                          togglePending={toggleActiveMutation.isPending}
                          formatDate={formatDate}
                          t={t}
                        />
                      );
                    })}
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
        </>
      )}

      {/* ============================================================ */}
      {/*  INVITATIONS TAB                                              */}
      {/* ============================================================ */}
      {activeTab === 'invitations' && (
        <>
          {/* Invitation filters */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-3 sm:p-4 shadow-sm overflow-hidden">
            <div className="flex flex-wrap items-center gap-2 sm:gap-3">
              <select
                value={invStatusFilter}
                onChange={(e) => {
                  setInvStatusFilter(e.target.value);
                  setInvPage(1);
                }}
                aria-label={t('admin.filter_status') || 'Filter by status'}
                className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
              >
                <option value="">{t('admin.all_statuses') || 'All statuses'}</option>
                <option value="pending">{t('admin.invitation_status.pending') || 'Pending'}</option>
                <option value="accepted">{t('admin.invitation_status.accepted') || 'Accepted'}</option>
                <option value="expired">{t('admin.invitation_status.expired') || 'Expired'}</option>
                <option value="revoked">{t('admin.invitation_status.revoked') || 'Revoked'}</option>
              </select>
            </div>
          </div>

          {/* Invitations list */}
          {invLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-red-600" />
            </div>
          ) : invitations.length === 0 ? (
            <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-12 text-center">
              <Mail className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-slate-400 text-sm">
                {t('admin.no_invitations') || 'No invitations'}
              </p>
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
                      <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('admin.email') || 'Email'}
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('admin.role') || 'Role'}
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('admin.status') || 'Status'}
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('invitation.expires_at') || 'Expires'}
                      </th>
                      <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('invitation.created_at') || 'Created'}
                      </th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('admin.actions') || 'Actions'}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                    {invitations.map((inv) => {
                      const invOrg = inv.organization_id ? orgMap.get(inv.organization_id) : null;
                      return (
                        <tr key={inv.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors">
                          <td className="px-4 py-3 text-gray-900 dark:text-white font-medium whitespace-nowrap">
                            <div>{inv.email}</div>
                            {invOrg && <div className="text-xs text-gray-400 dark:text-slate-500">{invOrg.name}</div>}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span
                              className={cn(
                                'px-2 py-0.5 text-xs font-medium rounded-full',
                                roleColors[inv.role] ||
                                  'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
                              )}
                            >
                              {t(`role.${inv.role}`) || inv.role}
                            </span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span
                              className={cn(
                                'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full',
                                invitationStatusColors[inv.status] || '',
                              )}
                            >
                              {inv.status === 'pending' && <Clock className="w-3 h-3" />}
                              {inv.status === 'accepted' && <CheckCircle2 className="w-3 h-3" />}
                              {inv.status === 'expired' && <XCircle className="w-3 h-3" />}
                              {inv.status === 'revoked' && <Ban className="w-3 h-3" />}
                              {t(`admin.invitation_status.${inv.status}`) || inv.status}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-500 dark:text-slate-400 whitespace-nowrap">
                            {formatDateTime(inv.expires_at)}
                          </td>
                          <td className="px-4 py-3 text-gray-500 dark:text-slate-400 whitespace-nowrap">
                            {formatDate(inv.created_at)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <div className="flex items-center justify-end gap-1">
                              {inv.status === 'pending' && (
                                <>
                                  <button
                                    onClick={() =>
                                      inviteCreateMutation.mutate({
                                        email: inv.email,
                                        role: inv.role,
                                        organization_id: inv.organization_id || undefined,
                                      })
                                    }
                                    title={t('admin.resend') || 'Resend'}
                                    className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
                                  >
                                    <RotateCcw className="w-4 h-4" />
                                  </button>
                                  <button
                                    onClick={() => handleRevokeInvitation(inv)}
                                    title={t('admin.revoke') || 'Revoke'}
                                    className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                  >
                                    <Ban className="w-4 h-4" />
                                  </button>
                                </>
                              )}
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Inv pagination */}
          {invTotalPages > 1 && (
            <div className="flex items-center justify-center gap-2">
              <button
                onClick={() => setInvPage((p) => Math.max(1, p - 1))}
                disabled={invPage === 1}
                aria-label={t('pagination.previous')}
                className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg border border-gray-300 dark:border-slate-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors dark:text-slate-200"
              >
                <ChevronLeft className="w-4 h-4" />
              </button>
              <span className="text-sm text-gray-600 dark:text-slate-300">
                {t('pagination.page', { page: invPage, pages: invTotalPages })}
              </span>
              <button
                onClick={() => setInvPage((p) => Math.min(invTotalPages, p + 1))}
                disabled={invPage === invTotalPages}
                aria-label={t('pagination.next')}
                className="p-2 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg border border-gray-300 dark:border-slate-600 disabled:opacity-40 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors dark:text-slate-200"
              >
                <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          )}
        </>
      )}

      {/* ============================================================ */}
      {/*  CREATE USER MODAL                                            */}
      {/* ============================================================ */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                {t('admin.create_user') || 'Create user'}
              </h2>
              <button
                onClick={() => {
                  setShowCreateModal(false);
                  setFormData(emptyForm);
                }}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                aria-label={t('form.close')}
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>

            <form onSubmit={handleCreate} className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('admin.email') || 'Email'} *
                  </label>
                  <input
                    type="email"
                    required
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('admin.first_name') || 'First name'} *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('admin.last_name') || 'Last name'} *
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('admin.role') || 'Role'} *
                  </label>
                  <select
                    required
                    value={formData.role}
                    onChange={(e) => setFormData({ ...formData, role: e.target.value as UserRole })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {t(`role.${r}`) || r}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('admin.organization') || 'Organization'}
                  </label>
                  <select
                    value={formData.organization_id}
                    onChange={(e) => setFormData({ ...formData, organization_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    <option value="">{t('admin.org_id_placeholder') || 'Select an organization'}</option>
                    {organizations.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.name}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="sm:col-span-2">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('admin.password') || 'Password'} *
                  </label>
                  <input
                    type="password"
                    required
                    minLength={6}
                    value={formData.password}
                    onChange={(e) => setFormData({ ...formData, password: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                </div>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                <button
                  type="button"
                  onClick={() => {
                    setShowCreateModal(false);
                    setFormData(emptyForm);
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
                >
                  {t('form.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={createMutation.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
                >
                  {createMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  {t('form.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/*  INVITE USER MODAL                                            */}
      {/* ============================================================ */}
      {showInviteModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">
                {t('admin.invite_user') || 'Invite user'}
              </h2>
              <button
                onClick={() => {
                  setShowInviteModal(false);
                  setInviteFormData(emptyInviteForm);
                }}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                aria-label={t('form.close')}
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>

            <form onSubmit={handleInvite} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('admin.invite_email') || 'Email address'} *
                </label>
                <input
                  type="email"
                  required
                  value={inviteFormData.email}
                  onChange={(e) => setInviteFormData({ ...inviteFormData, email: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('admin.invite_role') || 'Role'} *
                  </label>
                  <select
                    required
                    value={inviteFormData.role}
                    onChange={(e) =>
                      setInviteFormData({
                        ...inviteFormData,
                        role: e.target.value as UserRole,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {ROLES.map((r) => (
                      <option key={r} value={r}>
                        {t(`role.${r}`) || r}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    {t('admin.invite_organization') || 'Organization'}
                  </label>
                  <select
                    value={inviteFormData.organization_id}
                    onChange={(e) =>
                      setInviteFormData({
                        ...inviteFormData,
                        organization_id: e.target.value,
                      })
                    }
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    <option value="">{t('admin.org_id_placeholder') || 'Select an organization'}</option>
                    {organizations.map((o) => (
                      <option key={o.id} value={o.id}>
                        {o.name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('admin.invite_message') || 'Message (optional)'}
                </label>
                <textarea
                  value={inviteFormData.message}
                  onChange={(e) => setInviteFormData({ ...inviteFormData, message: e.target.value })}
                  rows={3}
                  placeholder={t('admin.invite_message_placeholder') || 'Add a personal message...'}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                />
              </div>

              {/* Permissions preview for selected role */}
              <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3">
                <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                  {t('admin.permissions_summary') || 'Permissions summary'}
                </p>
                <p className="text-xs text-gray-600 dark:text-slate-300">
                  {t(`admin.role_permissions.${inviteFormData.role}`) || '-'}
                </p>
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                <button
                  type="button"
                  onClick={() => {
                    setShowInviteModal(false);
                    setInviteFormData(emptyInviteForm);
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
                >
                  {t('form.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={inviteCreateMutation.isPending}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:bg-blue-400"
                >
                  {inviteCreateMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  <Send className="w-4 h-4" />
                  {t('admin.invite_send') || 'Send invitation'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ============================================================ */}
      {/*  EDIT ROLE MODAL                                              */}
      {/* ============================================================ */}
      {editingUser && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('admin.edit_role') || 'Edit role'}</h2>
              <button
                onClick={() => setEditingUser(null)}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                aria-label={t('form.close')}
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>

            <p className="text-sm text-gray-600 dark:text-slate-300 mb-4">
              {editingUser.first_name} {editingUser.last_name} ({editingUser.email})
            </p>

            <select
              value={editRole}
              onChange={(e) => setEditRole(e.target.value as UserRole)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500 mb-4"
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {t(`role.${r}`) || r}
                </option>
              ))}
            </select>

            {/* Permissions preview */}
            <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3 mb-6">
              <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
                {t('admin.permissions_summary') || 'Permissions summary'}
              </p>
              <p className="text-xs text-gray-600 dark:text-slate-300">
                {t(`admin.role_permissions.${editRole}`) || '-'}
              </p>
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => setEditingUser(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                {t('form.cancel')}
              </button>
              <button
                onClick={handleSaveRole}
                disabled={updateRoleMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
              >
                {updateRoleMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                {t('form.save') || 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Confirmation dialog */}
      <ConfirmDialog
        open={confirmState.open}
        title={confirmState.title}
        message={confirmState.message}
        onConfirm={() => confirmState.action?.()}
        onCancel={() => setConfirmState((s) => ({ ...s, open: false }))}
        loading={toggleActiveMutation.isPending || inviteRevokeMutation.isPending || updateRoleMutation.isPending}
        variant={confirmState.variant}
      />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  User Row with expandable detail                                    */
/* ------------------------------------------------------------------ */
function UserRow({
  u,
  org,
  isExpanded,
  onToggleExpand,
  onEditRole,
  onToggleActive,
  togglePending,
  formatDate,
  t,
}: {
  u: User;
  org: Organization | null;
  isExpanded: boolean;
  onToggleExpand: () => void;
  onEditRole: () => void;
  onToggleActive: () => void;
  togglePending: boolean;
  formatDate: (d: string | null | undefined) => string;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  return (
    <>
      <tr
        className={cn(
          'hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer',
          isExpanded && 'bg-gray-50 dark:bg-slate-700/50',
        )}
        onClick={onToggleExpand}
      >
        <td className="px-4 py-3 text-gray-900 dark:text-white font-medium whitespace-nowrap">
          <div className="flex items-center gap-2">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400 flex-shrink-0" />
            )}
            {u.first_name} {u.last_name}
          </div>
        </td>
        <td className="px-4 py-3 text-gray-600 dark:text-slate-300 whitespace-nowrap">{u.email}</td>
        <td className="px-4 py-3 whitespace-nowrap">
          <span
            className={cn(
              'px-2 py-0.5 text-xs font-medium rounded-full',
              roleColors[u.role] || 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
            )}
          >
            {t(`role.${u.role}`) || u.role}
          </span>
        </td>
        <td className="px-4 py-3 text-gray-600 dark:text-slate-300 whitespace-nowrap text-xs">
          {org ? org.name : <span className="text-gray-400 dark:text-slate-500">-</span>}
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          <span
            className={cn(
              'px-2 py-0.5 text-xs font-medium rounded-full',
              u.is_active
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
            )}
          >
            {u.is_active ? t('admin.active') || 'Active' : t('admin.inactive') || 'Inactive'}
          </span>
        </td>
        <td className="px-4 py-3 text-gray-500 dark:text-slate-400 whitespace-nowrap text-xs">
          {formatDate(u.updated_at)}
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          <div className="flex items-center justify-end gap-1" onClick={(e) => e.stopPropagation()}>
            <button
              onClick={onEditRole}
              title={t('admin.edit_role') || 'Edit role'}
              className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
            >
              <Pencil className="w-4 h-4" />
            </button>
            <button
              onClick={onToggleActive}
              disabled={togglePending}
              title={u.is_active ? t('admin.deactivate') || 'Deactivate' : t('admin.activate') || 'Activate'}
              className={cn(
                'p-1.5 rounded-lg transition-colors',
                u.is_active
                  ? 'text-gray-400 dark:text-slate-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20'
                  : 'text-gray-400 dark:text-slate-500 hover:text-green-600 dark:hover:text-green-400 hover:bg-green-50 dark:hover:bg-green-900/20',
              )}
            >
              {u.is_active ? <UserX className="w-4 h-4" /> : <UserCheck className="w-4 h-4" />}
            </button>
            <button
              onClick={() => {
                /* reset password - placeholder since no backend endpoint */
              }}
              title={t('admin.reset_password') || 'Reset password'}
              className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-amber-600 dark:hover:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
            >
              <KeyRound className="w-4 h-4" />
            </button>
          </div>
        </td>
      </tr>
      {/* Expanded detail panel */}
      {isExpanded && (
        <tr className="bg-gray-50/80 dark:bg-slate-700/30">
          <td colSpan={7} className="px-4 py-4">
            <div className="ml-6 grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* User info */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                  {t('admin.user_detail') || 'User detail'}
                </h4>
                <div className="text-sm text-gray-700 dark:text-slate-200 space-y-1">
                  <p>
                    <span className="text-gray-500 dark:text-slate-400">{t('admin.email') || 'Email'}:</span> {u.email}
                  </p>
                  <p>
                    <span className="text-gray-500 dark:text-slate-400">
                      {t('admin.organization') || 'Organization'}:
                    </span>{' '}
                    {org ? org.name : '-'}
                  </p>
                  <p>
                    <span className="text-gray-500 dark:text-slate-400">{t('admin.created') || 'Created'}:</span>{' '}
                    {formatDate(u.created_at)}
                  </p>
                  <p>
                    <span className="text-gray-500 dark:text-slate-400">{t('admin.last_login') || 'Last login'}:</span>{' '}
                    {formatDate(u.updated_at)}
                  </p>
                </div>
              </div>
              {/* Current role + permissions */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                  {t('admin.role') || 'Role'}
                </h4>
                <span className={cn('inline-block px-2.5 py-1 text-xs font-medium rounded-full', roleColors[u.role])}>
                  {t(`role.${u.role}`) || u.role}
                </span>
                <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
                  {t(`admin.role_permissions.${u.role}`) || '-'}
                </p>
              </div>
              {/* Activity summary */}
              <div className="space-y-2">
                <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                  {t('admin.status') || 'Status'}
                </h4>
                <div className="flex items-center gap-2">
                  <span className={cn('w-2.5 h-2.5 rounded-full', u.is_active ? 'bg-green-500' : 'bg-gray-400')} />
                  <span className="text-sm text-gray-700 dark:text-slate-200">
                    {u.is_active ? t('admin.active') || 'Active' : t('admin.inactive') || 'Inactive'}
                  </span>
                </div>
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  ID: <span className="font-mono">{u.id.slice(0, 8)}...</span>
                </p>
              </div>
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
