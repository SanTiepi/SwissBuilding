/**
 * MIGRATION: DEPRECATE
 * This page is scheduled for removal. Do not add new features.
 * Its functionality is covered by BuildingDetail assignments tab.
 * Not routed in App.tsx — orphaned page file.
 */
import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { assignmentsApi, type CreateAssignmentData } from '@/api/assignments';
import { usersApi } from '@/api/users';
import { buildingsApi } from '@/api/buildings';
import { cn } from '@/utils/formatters';
import type { Assignment, AssignmentRole, Building, User } from '@/types';
import {
  Plus,
  Loader2,
  AlertTriangle,
  X,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Users,
  Building2,
  ClipboardList,
  CalendarDays,
  Grid3X3,
  ChevronDown,
  ChevronUp,
  BarChart3,
  ListChecks,
} from 'lucide-react';

// ─── Constants ────────────────────────────────────────────────────────────────

const ASSIGNMENT_ROLES: AssignmentRole[] = [
  'responsible',
  'owner_contact',
  'diagnostician',
  'reviewer',
  'contractor_contact',
];

const TARGET_TYPES = ['building', 'diagnostic'] as const;

type SortField = 'created_at' | 'role' | 'target_type';
type SortDir = 'asc' | 'desc';
type ViewMode = 'list' | 'matrix';

const roleColors: Record<string, string> = {
  responsible: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  owner_contact: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  diagnostician: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  reviewer: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  contractor_contact: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

const targetTypeColors: Record<string, string> = {
  building: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  diagnostic: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
};

// ─── Interfaces ───────────────────────────────────────────────────────────────

interface AssignmentFormData {
  target_type: string;
  target_id: string;
  user_id: string;
  role: AssignmentRole;
}

const emptyForm: AssignmentFormData = {
  target_type: 'building',
  target_id: '',
  user_id: '',
  role: 'responsible',
};

// ─── Component ────────────────────────────────────────────────────────────────

export default function Assignments() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  // State
  const [page, setPage] = useState(1);
  const pageSize = 50;
  const [roleFilter, setRoleFilter] = useState('');
  const [targetTypeFilter, setTargetTypeFilter] = useState('');
  const [userFilter, setUserFilter] = useState('');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');
  const [viewMode, setViewMode] = useState<ViewMode>('list');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showBulkModal, setShowBulkModal] = useState(false);
  const [formData, setFormData] = useState<AssignmentFormData>(emptyForm);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [bulkTargetIds, setBulkTargetIds] = useState<string[]>([]);
  const [bulkForm, setBulkForm] = useState<{ user_id: string; role: AssignmentRole; target_type: string }>({
    user_id: '',
    role: 'responsible',
    target_type: 'building',
  });

  // Queries
  const {
    data: assignmentsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['assignments', page, pageSize, roleFilter, targetTypeFilter, userFilter],
    queryFn: () => {
      const params: Record<string, string | number> = { page, size: pageSize };
      if (targetTypeFilter) params.target_type = targetTypeFilter;
      if (userFilter) params.user_id = userFilter;
      if (roleFilter) params.role = roleFilter;
      return assignmentsApi.list(params);
    },
  });

  const { data: usersData } = useQuery({
    queryKey: ['users-all'],
    queryFn: () => usersApi.list({ size: 200 }),
  });

  const { data: buildingsData } = useQuery({
    queryKey: ['buildings-all'],
    queryFn: () => buildingsApi.list({ size: 200 }),
  });

  // All assignments (for matrix view) — get all regardless of filter for matrix
  const { data: allAssignmentsData } = useQuery({
    queryKey: ['assignments-all'],
    queryFn: () => assignmentsApi.list({ size: 200 }),
    enabled: viewMode === 'matrix',
  });

  // Derived data
  const assignments = useMemo(() => assignmentsData?.items ?? [], [assignmentsData]);
  const totalPages = assignmentsData?.pages ?? 1;
  const usersMap = useMemo(() => {
    const map = new Map<string, User>();
    (usersData?.items ?? []).forEach((u) => map.set(u.id, u));
    return map;
  }, [usersData]);
  const buildingsMap = useMemo(() => {
    const map = new Map<string, Building>();
    (buildingsData?.items ?? []).forEach((b) => map.set(b.id, b));
    return map;
  }, [buildingsData]);
  const usersList = useMemo(() => usersData?.items ?? [], [usersData]);
  const buildingsList = useMemo(() => buildingsData?.items ?? [], [buildingsData]);

  // Sorted assignments
  const sortedAssignments = useMemo(() => {
    const sorted = [...assignments];
    sorted.sort((a, b) => {
      let cmp = 0;
      if (sortField === 'created_at') {
        cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      } else if (sortField === 'role') {
        cmp = a.role.localeCompare(b.role);
      } else if (sortField === 'target_type') {
        cmp = a.target_type.localeCompare(b.target_type);
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [assignments, sortField, sortDir]);

  // Summary cards data
  const summaryData = useMemo(() => {
    const allItems = assignmentsData?.items ?? [];
    const total = assignmentsData?.total ?? 0;
    const byRole: Record<string, number> = {};
    ASSIGNMENT_ROLES.forEach((r) => (byRole[r] = 0));
    allItems.forEach((a) => {
      byRole[a.role] = (byRole[a.role] || 0) + 1;
    });

    const now = new Date();
    const startOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
    const thisMonth = allItems.filter((a) => new Date(a.created_at) >= startOfMonth).length;

    const assignedBuildingIds = new Set(allItems.filter((a) => a.target_type === 'building').map((a) => a.target_id));
    const totalBuildings = buildingsData?.total ?? 0;
    const unassigned = Math.max(0, totalBuildings - assignedBuildingIds.size);

    return { total, byRole, thisMonth, unassigned };
  }, [assignmentsData, buildingsData]);

  // Mutations
  const createMutation = useMutation({
    mutationFn: (data: CreateAssignmentData) => assignmentsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
      queryClient.invalidateQueries({ queryKey: ['assignments-all'] });
      setShowCreateModal(false);
      setFormData(emptyForm);
    },
  });

  const bulkCreateMutation = useMutation({
    mutationFn: async (targets: string[]) => {
      const promises = targets.map((targetId) =>
        assignmentsApi.create({
          target_type: bulkForm.target_type,
          target_id: targetId,
          user_id: bulkForm.user_id,
          role: bulkForm.role,
        }),
      );
      return Promise.all(promises);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
      queryClient.invalidateQueries({ queryKey: ['assignments-all'] });
      setShowBulkModal(false);
      setBulkTargetIds([]);
      setBulkForm({ user_id: '', role: 'responsible', target_type: 'building' });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => assignmentsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['assignments'] });
      queryClient.invalidateQueries({ queryKey: ['assignments-all'] });
      setDeleteConfirmId(null);
    },
  });

  // Handlers
  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault();
    createMutation.mutate({
      target_type: formData.target_type,
      target_id: formData.target_id,
      user_id: formData.user_id,
      role: formData.role,
    });
  };

  const handleBulkCreate = (e: React.FormEvent) => {
    e.preventDefault();
    if (bulkTargetIds.length === 0) return;
    bulkCreateMutation.mutate(bulkTargetIds);
  };

  const handleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortField(field);
        setSortDir('desc');
      }
    },
    [sortField],
  );

  const toggleBulkTarget = (id: string) => {
    setBulkTargetIds((prev) => (prev.includes(id) ? prev.filter((i) => i !== id) : [...prev, id]));
  };

  const getUserName = (userId: string) => {
    const u = usersMap.get(userId);
    return u ? `${u.first_name} ${u.last_name}` : userId.slice(0, 8);
  };

  const getTargetLabel = (a: Assignment) => {
    if (a.target_type === 'building') {
      const b = buildingsMap.get(a.target_id);
      return b ? `${b.address}, ${b.city}` : a.target_id.slice(0, 8);
    }
    return a.target_id.slice(0, 8);
  };

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString();
    } catch {
      return dateStr;
    }
  };

  const renderSortIcon = (field: SortField) => {
    if (sortField !== field) return null;
    return sortDir === 'asc' ? (
      <ChevronUp className="w-3 h-3 inline ml-1" />
    ) : (
      <ChevronDown className="w-3 h-3 inline ml-1" />
    );
  };

  // Matrix view data
  const matrixData = useMemo(() => {
    if (viewMode !== 'matrix') return { users: [] as User[], buildings: [] as Building[], grid: new Map() };

    const allAssignments = allAssignmentsData?.items ?? [];
    const buildingAssignments = allAssignments.filter((a) => a.target_type === 'building');

    const involvedUserIds = new Set(buildingAssignments.map((a) => a.user_id));
    const involvedBuildingIds = new Set(buildingAssignments.map((a) => a.target_id));

    const matrixUsers = usersList.filter((u) => involvedUserIds.has(u.id));
    const matrixBuildings = buildingsList.filter((b) => involvedBuildingIds.has(b.id));

    const grid = new Map<string, AssignmentRole[]>();
    buildingAssignments.forEach((a) => {
      const key = `${a.user_id}:${a.target_id}`;
      const existing = grid.get(key) || [];
      existing.push(a.role);
      grid.set(key, existing);
    });

    return { users: matrixUsers, buildings: matrixBuildings, grid };
  }, [viewMode, allAssignmentsData, usersList, buildingsList]);

  // ─── Access control ─────────────────────────────────────────────────

  if (user?.role !== 'admin' && user?.role !== 'owner') {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-500 dark:text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('admin.access_denied') || 'Access denied'}</p>
      </div>
    );
  }

  // ─── Render ─────────────────────────────────────────────────────────

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('assignment.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {assignmentsData?.total ?? 0} {t('assignment.total') || 'total'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View toggle */}
          <div className="flex items-center bg-gray-100 dark:bg-slate-700 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('list')}
              className={cn(
                'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                viewMode === 'list'
                  ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 dark:text-slate-400',
              )}
            >
              <ListChecks className="w-4 h-4" />
            </button>
            <button
              onClick={() => setViewMode('matrix')}
              className={cn(
                'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                viewMode === 'matrix'
                  ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 dark:text-slate-400',
              )}
            >
              <Grid3X3 className="w-4 h-4" />
            </button>
          </div>
          <button
            onClick={() => setShowBulkModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-200 text-sm font-medium rounded-lg border border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors"
          >
            <ClipboardList className="w-4 h-4" />
            {t('assignment.bulk_assign')}
          </button>
          <button
            onClick={() => setShowCreateModal(true)}
            className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
          >
            <Plus className="w-4 h-4" />
            {t('assignment.create')}
          </button>
        </div>
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
              <Users className="w-5 h-5 text-blue-600 dark:text-blue-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{summaryData.total}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">{t('assignment.total_assignments')}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
              <BarChart3 className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">
                {Object.keys(summaryData.byRole).filter((r) => summaryData.byRole[r] > 0).length}
              </p>
              <p className="text-xs text-gray-500 dark:text-slate-400">{t('assignment.active_roles')}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
              <Building2 className="w-5 h-5 text-amber-600 dark:text-amber-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{summaryData.unassigned}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">{t('assignment.unassigned_buildings')}</p>
            </div>
          </div>
        </div>
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 dark:bg-green-900/30 rounded-lg">
              <CalendarDays className="w-5 h-5 text-green-600 dark:text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold text-gray-900 dark:text-white">{summaryData.thisMonth}</p>
              <p className="text-xs text-gray-500 dark:text-slate-400">{t('assignment.this_month')}</p>
            </div>
          </div>
        </div>
      </div>

      {/* Role distribution bar */}
      {summaryData.total > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">
            {t('assignment.role_distribution')}
          </p>
          <div className="flex gap-3 flex-wrap">
            {ASSIGNMENT_ROLES.map((r) => (
              <div key={r} className="flex items-center gap-1.5">
                <span className={cn('w-2.5 h-2.5 rounded-full', roleColors[r]?.split(' ')[0])} />
                <span className="text-xs text-gray-600 dark:text-slate-300">
                  {t(`assignment_role.${r}`)} ({summaryData.byRole[r] || 0})
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={roleFilter}
            onChange={(e) => {
              setRoleFilter(e.target.value);
              setPage(1);
            }}
            aria-label={t('assignment.filter_role')}
            className="flex-1 sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0"
          >
            <option value="">{t('assignment.all_roles')}</option>
            {ASSIGNMENT_ROLES.map((r) => (
              <option key={r} value={r}>
                {t(`assignment_role.${r}`)}
              </option>
            ))}
          </select>
          <select
            value={targetTypeFilter}
            onChange={(e) => {
              setTargetTypeFilter(e.target.value);
              setPage(1);
            }}
            aria-label={t('assignment.filter_target_type')}
            className="flex-1 sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0"
          >
            <option value="">{t('assignment.all_target_types')}</option>
            {TARGET_TYPES.map((tt) => (
              <option key={tt} value={tt}>
                {t(`assignment.target_type_${tt}`)}
              </option>
            ))}
          </select>
          <select
            value={userFilter}
            onChange={(e) => {
              setUserFilter(e.target.value);
              setPage(1);
            }}
            aria-label={t('assignment.filter_user')}
            className="flex-1 sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0"
          >
            <option value="">{t('assignment.all_users')}</option>
            {usersList.map((u) => (
              <option key={u.id} value={u.id}>
                {u.first_name} {u.last_name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Matrix view */}
      {viewMode === 'matrix' && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="p-4 border-b border-gray-200 dark:border-slate-700">
            <h2 className="text-sm font-semibold text-gray-900 dark:text-white">{t('assignment.role_matrix')}</h2>
            <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">{t('assignment.role_matrix_desc')}</p>
          </div>
          {matrixData.users.length === 0 || matrixData.buildings.length === 0 ? (
            <div className="p-8 text-center text-gray-500 dark:text-slate-400 text-sm">
              {t('assignment.no_assignments')}
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
                    <th className="text-left px-3 py-2 font-medium text-gray-500 dark:text-slate-400 sticky left-0 bg-gray-50 dark:bg-slate-800/50 z-10">
                      {t('assignment.user')}
                    </th>
                    {matrixData.buildings.map((b) => (
                      <th
                        key={b.id}
                        className="text-center px-2 py-2 font-medium text-gray-500 dark:text-slate-400 whitespace-nowrap max-w-[120px] truncate"
                        title={`${b.address}, ${b.city}`}
                      >
                        {b.address.length > 18 ? b.address.slice(0, 18) + '...' : b.address}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                  {matrixData.users.map((u) => (
                    <tr key={u.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50">
                      <td className="px-3 py-2 font-medium text-gray-900 dark:text-white whitespace-nowrap sticky left-0 bg-white dark:bg-slate-800 z-10">
                        {u.first_name} {u.last_name}
                      </td>
                      {matrixData.buildings.map((b) => {
                        const roles = matrixData.grid.get(`${u.id}:${b.id}`) || [];
                        return (
                          <td key={b.id} className="px-2 py-2 text-center">
                            {roles.length > 0 ? (
                              <div className="flex flex-wrap justify-center gap-0.5">
                                {roles.map((r: AssignmentRole, i: number) => (
                                  <span
                                    key={i}
                                    className={cn('px-1 py-0.5 text-[10px] font-medium rounded', roleColors[r])}
                                    title={t(`assignment_role.${r}`)}
                                  >
                                    {t(`assignment_role.${r}`).slice(0, 3)}
                                  </span>
                                ))}
                              </div>
                            ) : (
                              <span className="text-gray-300 dark:text-slate-600">-</span>
                            )}
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* List view */}
      {viewMode === 'list' && (
        <>
          {isLoading ? (
            <div className="flex items-center justify-center h-64">
              <Loader2 className="w-8 h-8 animate-spin text-red-600" />
            </div>
          ) : error ? (
            <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
              <AlertTriangle className="w-8 h-8 text-red-500 dark:text-red-400 mx-auto mb-2" />
              <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
            </div>
          ) : sortedAssignments.length === 0 ? (
            <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-12 text-center">
              <Users className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-slate-400 text-sm">{t('assignment.no_assignments')}</p>
            </div>
          ) : (
            <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
                      <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('assignment.user')}
                      </th>
                      <th
                        className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400 cursor-pointer select-none"
                        onClick={() => handleSort('target_type')}
                      >
                        {t('assignment.target')}
                        {renderSortIcon('target_type')}
                      </th>
                      <th
                        className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400 cursor-pointer select-none"
                        onClick={() => handleSort('role')}
                      >
                        {t('assignment.role')}
                        {renderSortIcon('role')}
                      </th>
                      <th
                        className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400 cursor-pointer select-none"
                        onClick={() => handleSort('created_at')}
                      >
                        {t('assignment.date')}
                        {renderSortIcon('created_at')}
                      </th>
                      <th className="text-right px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                        {t('admin.actions')}
                      </th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                    {sortedAssignments.map((a) => {
                      const assignedUser = usersMap.get(a.user_id);
                      const isExpanded = expandedId === a.id;
                      return (
                        <tr key={a.id} className="group">
                          <td className="px-4 py-3">
                            <button
                              onClick={() => setExpandedId(isExpanded ? null : a.id)}
                              className="text-left hover:underline"
                            >
                              <p className="text-gray-900 dark:text-white font-medium">{getUserName(a.user_id)}</p>
                              {assignedUser && (
                                <p className="text-xs text-gray-500 dark:text-slate-400">{assignedUser.email}</p>
                              )}
                            </button>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={cn(
                                'px-2 py-0.5 text-xs font-medium rounded-full mr-2',
                                targetTypeColors[a.target_type] ||
                                  'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
                              )}
                            >
                              {t(`assignment.target_type_${a.target_type}`)}
                            </span>
                            <span className="text-gray-700 dark:text-slate-300 text-xs">{getTargetLabel(a)}</span>
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', roleColors[a.role])}>
                              {t(`assignment_role.${a.role}`)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-gray-500 dark:text-slate-400 whitespace-nowrap text-xs">
                            {formatDate(a.created_at)}
                          </td>
                          <td className="px-4 py-3 whitespace-nowrap">
                            <div className="flex items-center justify-end gap-1">
                              <button
                                onClick={() => setDeleteConfirmId(a.id)}
                                title={t('assignment.delete')}
                                className="p-1.5 text-gray-400 dark:text-slate-500 hover:text-red-600 dark:hover:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors opacity-0 group-hover:opacity-100"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })}

                    {/* Expanded detail rows */}
                    {sortedAssignments.map((a) => {
                      if (expandedId !== a.id) return null;
                      const assignedUser = usersMap.get(a.user_id);
                      const createdByUser = usersMap.get(a.created_by);
                      const building = a.target_type === 'building' ? buildingsMap.get(a.target_id) : null;
                      return (
                        <tr key={`${a.id}-detail`}>
                          <td colSpan={5} className="px-4 py-4 bg-gray-50 dark:bg-slate-800/60">
                            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-xs">
                              {/* User info */}
                              <div className="space-y-1">
                                <p className="font-semibold text-gray-700 dark:text-slate-200">
                                  {t('assignment.user_details')}
                                </p>
                                {assignedUser ? (
                                  <>
                                    <p className="text-gray-600 dark:text-slate-300">
                                      {assignedUser.first_name} {assignedUser.last_name}
                                    </p>
                                    <p className="text-gray-500 dark:text-slate-400">{assignedUser.email}</p>
                                    <p className="text-gray-500 dark:text-slate-400">
                                      {t(`role.${assignedUser.role}`)}
                                    </p>
                                  </>
                                ) : (
                                  <p className="text-gray-400 dark:text-slate-500">ID: {a.user_id}</p>
                                )}
                              </div>
                              {/* Target info */}
                              <div className="space-y-1">
                                <p className="font-semibold text-gray-700 dark:text-slate-200">
                                  {t('assignment.target_details')}
                                </p>
                                <p className="text-gray-600 dark:text-slate-300">
                                  {t(`assignment.target_type_${a.target_type}`)}
                                </p>
                                {building ? (
                                  <>
                                    <p className="text-gray-500 dark:text-slate-400">
                                      {building.address}, {building.postal_code} {building.city}
                                    </p>
                                    <p className="text-gray-500 dark:text-slate-400">
                                      {t('building.canton')}: {building.canton}
                                    </p>
                                  </>
                                ) : (
                                  <p className="text-gray-400 dark:text-slate-500">ID: {a.target_id}</p>
                                )}
                              </div>
                              {/* Assignment meta */}
                              <div className="space-y-1">
                                <p className="font-semibold text-gray-700 dark:text-slate-200">
                                  {t('assignment.assignment_info')}
                                </p>
                                <p className="text-gray-600 dark:text-slate-300">
                                  {t('assignment.role')}: {t(`assignment_role.${a.role}`)}
                                </p>
                                <p className="text-gray-500 dark:text-slate-400">
                                  {t('assignment.created_at')}: {formatDate(a.created_at)}
                                </p>
                                <p className="text-gray-500 dark:text-slate-400">
                                  {t('assignment.created_by')}:{' '}
                                  {createdByUser
                                    ? `${createdByUser.first_name} ${createdByUser.last_name}`
                                    : a.created_by.slice(0, 8)}
                                </p>
                              </div>
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

      {/* Delete Confirmation Modal */}
      {deleteConfirmId && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-sm mx-4 p-6">
            <div className="flex items-center gap-3 mb-4">
              <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400" />
              </div>
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('assignment.delete')}</h2>
            </div>
            <p className="text-sm text-gray-600 dark:text-slate-300 mb-6">{t('assignment.delete_warning')}</p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeleteConfirmId(null)}
                className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
              >
                {t('form.cancel')}
              </button>
              <button
                onClick={() => deleteMutation.mutate(deleteConfirmId)}
                disabled={deleteMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
              >
                {deleteMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                {t('assignment.confirm_delete')}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Create Assignment Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-md max-h-[90vh] overflow-y-auto mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('assignment.create')}</h2>
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
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('assignment.user')} *
                </label>
                <select
                  required
                  value={formData.user_id}
                  onChange={(e) => setFormData({ ...formData, user_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  <option value="">{t('assignment.select_user')}</option>
                  {usersList.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.first_name} {u.last_name} ({u.email})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('assignment.target_type')} *
                </label>
                <select
                  required
                  value={formData.target_type}
                  onChange={(e) => setFormData({ ...formData, target_type: e.target.value, target_id: '' })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  {TARGET_TYPES.map((tt) => (
                    <option key={tt} value={tt}>
                      {t(`assignment.target_type_${tt}`)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('assignment.target')} *
                </label>
                {formData.target_type === 'building' ? (
                  <select
                    required
                    value={formData.target_id}
                    onChange={(e) => setFormData({ ...formData, target_id: e.target.value })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  >
                    <option value="">{t('assignment.select_target')}</option>
                    {buildingsList.map((b) => (
                      <option key={b.id} value={b.id}>
                        {b.address}, {b.city}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    required
                    value={formData.target_id}
                    onChange={(e) => setFormData({ ...formData, target_id: e.target.value })}
                    placeholder={t('assignment.enter_target_id')}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                  />
                )}
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('assignment.role')} *
                </label>
                <select
                  required
                  value={formData.role}
                  onChange={(e) => setFormData({ ...formData, role: e.target.value as AssignmentRole })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  {ASSIGNMENT_ROLES.map((r) => (
                    <option key={r} value={r}>
                      {t(`assignment_role.${r}`)}
                    </option>
                  ))}
                </select>
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
                  {t('assignment.create')}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Bulk Assign Modal */}
      {showBulkModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto mx-4 p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('assignment.bulk_assign')}</h2>
              <button
                onClick={() => {
                  setShowBulkModal(false);
                  setBulkTargetIds([]);
                }}
                className="p-1 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg"
                aria-label={t('form.close')}
              >
                <X className="w-5 h-5 text-gray-500 dark:text-slate-400" />
              </button>
            </div>

            <form onSubmit={handleBulkCreate} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('assignment.user')} *
                </label>
                <select
                  required
                  value={bulkForm.user_id}
                  onChange={(e) => setBulkForm({ ...bulkForm, user_id: e.target.value })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  <option value="">{t('assignment.select_user')}</option>
                  {usersList.map((u) => (
                    <option key={u.id} value={u.id}>
                      {u.first_name} {u.last_name} ({u.email})
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('assignment.role')} *
                </label>
                <select
                  required
                  value={bulkForm.role}
                  onChange={(e) => setBulkForm({ ...bulkForm, role: e.target.value as AssignmentRole })}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  {ASSIGNMENT_ROLES.map((r) => (
                    <option key={r} value={r}>
                      {t(`assignment_role.${r}`)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('assignment.target_type')} *
                </label>
                <select
                  required
                  value={bulkForm.target_type}
                  onChange={(e) => {
                    setBulkForm({ ...bulkForm, target_type: e.target.value });
                    setBulkTargetIds([]);
                  }}
                  className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-red-500"
                >
                  {TARGET_TYPES.map((tt) => (
                    <option key={tt} value={tt}>
                      {t(`assignment.target_type_${tt}`)}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  {t('assignment.select_targets')} ({bulkTargetIds.length} {t('assignment.selected')})
                </label>
                {bulkForm.target_type === 'building' ? (
                  <div className="max-h-48 overflow-y-auto border border-gray-300 dark:border-slate-600 rounded-lg">
                    {buildingsList.map((b) => (
                      <label
                        key={b.id}
                        className="flex items-center gap-2 px-3 py-2 hover:bg-gray-50 dark:hover:bg-slate-700 cursor-pointer text-sm"
                      >
                        <input
                          type="checkbox"
                          checked={bulkTargetIds.includes(b.id)}
                          onChange={() => toggleBulkTarget(b.id)}
                          className="rounded border-gray-300 dark:border-slate-600 text-red-600 focus:ring-red-500"
                        />
                        <span className="text-gray-900 dark:text-white truncate">
                          {b.address}, {b.city}
                        </span>
                      </label>
                    ))}
                  </div>
                ) : (
                  <p className="text-xs text-gray-500 dark:text-slate-400">{t('assignment.bulk_diagnostic_hint')}</p>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-4 border-t border-gray-100 dark:border-slate-700">
                <button
                  type="button"
                  onClick={() => {
                    setShowBulkModal(false);
                    setBulkTargetIds([]);
                  }}
                  className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700"
                >
                  {t('form.cancel')}
                </button>
                <button
                  type="submit"
                  disabled={bulkCreateMutation.isPending || bulkTargetIds.length === 0}
                  className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
                >
                  {bulkCreateMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                  {t('assignment.bulk_assign')} ({bulkTargetIds.length})
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
