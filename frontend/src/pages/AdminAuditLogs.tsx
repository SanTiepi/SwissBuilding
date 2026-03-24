import { useState, useMemo, useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { auditLogsApi } from '@/api/auditLogs';
import { usersApi } from '@/api/users';
import { cn } from '@/utils/formatters';
import type { AuditLog, User } from '@/types';
import {
  Loader2,
  AlertTriangle,
  FileSearch,
  ChevronLeft,
  ChevronRight,
  ChevronDown,
  ChevronUp,
  Download,
  Search,
  X,
  Table2,
  Clock,
  Building2,
  Stethoscope,
  FileText,
  Users,
  Settings,
  Shield,
  BarChart3,
  Activity,
} from 'lucide-react';

const ENTITY_TYPES = ['building', 'diagnostic', 'sample', 'document', 'user', 'system'];
const ACTIONS = ['create', 'update', 'delete', 'read', 'login', 'logout', 'validate', 'export'];

const actionColors: Record<string, string> = {
  create: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  update: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  delete: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  read: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  login: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  logout: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  validate: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  export: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
};

const actionDotColors: Record<string, string> = {
  create: 'bg-green-500',
  update: 'bg-blue-500',
  delete: 'bg-red-500',
  read: 'bg-gray-400',
  login: 'bg-purple-500',
  logout: 'bg-gray-400',
  validate: 'bg-amber-500',
  export: 'bg-cyan-500',
};

type DatePreset = 'today' | '7days' | '30days' | 'custom';
type ViewMode = 'table' | 'timeline';

function getEntityIcon(entityType: string | null) {
  switch (entityType) {
    case 'building':
      return <Building2 className="w-4 h-4" />;
    case 'diagnostic':
      return <Stethoscope className="w-4 h-4" />;
    case 'document':
      return <FileText className="w-4 h-4" />;
    case 'user':
      return <Users className="w-4 h-4" />;
    case 'sample':
      return <Activity className="w-4 h-4" />;
    case 'system':
      return <Settings className="w-4 h-4" />;
    default:
      return <Shield className="w-4 h-4" />;
  }
}

function getDateRange(preset: DatePreset): { from: string; to: string } | null {
  const now = new Date();
  const to = now.toISOString().split('T')[0];
  switch (preset) {
    case 'today':
      return { from: to, to };
    case '7days': {
      const d = new Date(now);
      d.setDate(d.getDate() - 7);
      return { from: d.toISOString().split('T')[0], to };
    }
    case '30days': {
      const d = new Date(now);
      d.setDate(d.getDate() - 30);
      return { from: d.toISOString().split('T')[0], to };
    }
    default:
      return null;
  }
}

function formatDateTimeLocal(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleString();
  } catch {
    return dateStr;
  }
}

function formatTimeOnly(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return dateStr;
  }
}

function formatDateOnly(dateStr: string) {
  try {
    return new Date(dateStr).toLocaleDateString();
  } catch {
    return dateStr;
  }
}

function exportToCsv(logs: AuditLog[], t: (key: string) => string) {
  const headers = [
    t('audit.date'),
    t('audit.user'),
    t('audit.action'),
    t('audit.entity_type'),
    t('audit.entity_id'),
    t('audit.ip_address'),
    t('audit.details'),
  ];
  const rows = logs.map((log) => [
    log.timestamp,
    log.user_name || log.user_email || t('audit.system'),
    log.action,
    log.entity_type || '',
    log.entity_id || '',
    log.ip_address || '',
    log.details ? JSON.stringify(log.details) : '',
  ]);
  const csvContent = [headers, ...rows]
    .map((row) => row.map((c) => `"${String(c).replace(/"/g, '""')}"`).join(','))
    .join('\n');
  downloadFile(csvContent, 'audit-logs.csv', 'text/csv;charset=utf-8;');
}

function exportToJson(logs: AuditLog[]) {
  const jsonContent = JSON.stringify(logs, null, 2);
  downloadFile(jsonContent, 'audit-logs.json', 'application/json');
}

function downloadFile(content: string, filename: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

export default function AdminAuditLogs() {
  const { t } = useTranslation();
  const { user } = useAuthStore();

  const [page, setPage] = useState(1);
  const pageSize = 20;
  const [entityTypeFilter, setEntityTypeFilter] = useState('');
  const [actionFilter, setActionFilter] = useState('');
  const [userFilter, setUserFilter] = useState('');
  const [datePreset, setDatePreset] = useState<DatePreset | ''>('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [searchText, setSearchText] = useState('');
  const [expandedRow, setExpandedRow] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>('table');
  const [showExportMenu, setShowExportMenu] = useState(false);

  // Compute effective date range
  const effectiveDateFrom = datePreset && datePreset !== 'custom' ? getDateRange(datePreset)?.from : dateFrom;
  const effectiveDateTo = datePreset && datePreset !== 'custom' ? getDateRange(datePreset)?.to : dateTo;

  // Fetch users for dropdown
  const { data: usersData } = useQuery({
    queryKey: ['admin-users-list'],
    queryFn: () => usersApi.list({ size: 200 }),
  });
  const usersList = useMemo(() => usersData?.items ?? [], [usersData]);

  const {
    data: logsData,
    isLoading,
    error,
  } = useQuery({
    queryKey: [
      'admin-audit-logs',
      page,
      pageSize,
      entityTypeFilter,
      actionFilter,
      userFilter,
      effectiveDateFrom,
      effectiveDateTo,
    ],
    queryFn: () =>
      auditLogsApi.list({
        page,
        size: pageSize,
        entity_type: entityTypeFilter || undefined,
        action: actionFilter || undefined,
        user_id: userFilter || undefined,
        date_from: effectiveDateFrom || undefined,
        date_to: effectiveDateTo || undefined,
      }),
  });

  const logs = useMemo(() => logsData?.items ?? [], [logsData]);
  const totalPages = logsData?.pages ?? 1;

  // Client-side text search filter
  const filteredLogs = useMemo(() => {
    if (!searchText.trim()) return logs;
    const q = searchText.toLowerCase();
    return logs.filter(
      (log: AuditLog) =>
        (log.entity_id && log.entity_id.toLowerCase().includes(q)) ||
        (log.details && JSON.stringify(log.details).toLowerCase().includes(q)) ||
        (log.user_name && log.user_name.toLowerCase().includes(q)) ||
        (log.user_email && log.user_email.toLowerCase().includes(q)),
    );
  }, [logs, searchText]);

  // Summary stats computed from current page data
  const summaryStats = useMemo(() => {
    const allLogs = filteredLogs;
    const today = new Date().toDateString();

    const actionsToday = allLogs.filter((l: AuditLog) => new Date(l.timestamp).toDateString() === today).length;

    const userCounts: Record<string, number> = {};
    const entityCounts: Record<string, number> = {};
    const actionCounts: Record<string, number> = {};

    allLogs.forEach((l: AuditLog) => {
      const name = l.user_name || l.user_email || 'System';
      userCounts[name] = (userCounts[name] || 0) + 1;
      if (l.entity_type) entityCounts[l.entity_type] = (entityCounts[l.entity_type] || 0) + 1;
      actionCounts[l.action] = (actionCounts[l.action] || 0) + 1;
    });

    const topUsers = Object.entries(userCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3);
    const topEntities = Object.entries(entityCounts)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 3);

    return { actionsToday, topUsers, topEntities, actionCounts };
  }, [filteredLogs]);

  const toggleExpand = useCallback((id: string) => {
    setExpandedRow((prev) => (prev === id ? null : id));
  }, []);

  const clearFilters = useCallback(() => {
    setEntityTypeFilter('');
    setActionFilter('');
    setUserFilter('');
    setDatePreset('');
    setDateFrom('');
    setDateTo('');
    setSearchText('');
    setPage(1);
  }, []);

  const hasActiveFilters =
    entityTypeFilter || actionFilter || userFilter || datePreset || dateFrom || dateTo || searchText;

  const handleDatePreset = useCallback(
    (preset: DatePreset) => {
      if (datePreset === preset) {
        setDatePreset('');
      } else {
        setDatePreset(preset);
        if (preset !== 'custom') {
          setDateFrom('');
          setDateTo('');
        }
      }
      setPage(1);
    },
    [datePreset],
  );

  // Group logs by date for timeline view
  const timelineGroups = useMemo(() => {
    const groups: Record<string, AuditLog[]> = {};
    filteredLogs.forEach((log: AuditLog) => {
      const date = formatDateOnly(log.timestamp);
      if (!groups[date]) groups[date] = [];
      groups[date].push(log);
    });
    return Object.entries(groups);
  }, [filteredLogs]);

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
      <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('audit.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {logsData?.total ?? 0} {t('audit.total_entries')}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {/* View mode toggle */}
          <div className="flex items-center bg-gray-100 dark:bg-slate-700 rounded-lg p-0.5">
            <button
              onClick={() => setViewMode('table')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                viewMode === 'table'
                  ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200',
              )}
            >
              <Table2 className="w-4 h-4" />
              {t('audit.view_table')}
            </button>
            <button
              onClick={() => setViewMode('timeline')}
              className={cn(
                'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors',
                viewMode === 'timeline'
                  ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-white shadow-sm'
                  : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200',
              )}
            >
              <Clock className="w-4 h-4" />
              {t('audit.view_timeline')}
            </button>
          </div>

          {/* Export button */}
          <div className="relative">
            <button
              onClick={() => setShowExportMenu(!showExportMenu)}
              className="flex items-center gap-1.5 px-3 py-2 bg-white dark:bg-slate-700 border border-gray-300 dark:border-slate-600 rounded-lg text-sm font-medium text-gray-700 dark:text-slate-200 hover:bg-gray-50 dark:hover:bg-slate-600 transition-colors"
            >
              <Download className="w-4 h-4" />
              {t('audit.export')}
            </button>
            {showExportMenu && (
              <div className="absolute right-0 mt-1 w-40 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-lg shadow-lg z-10">
                <button
                  onClick={() => {
                    exportToCsv(filteredLogs, t);
                    setShowExportMenu(false);
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-slate-200 hover:bg-gray-50 dark:hover:bg-slate-700 rounded-t-lg"
                >
                  {t('audit.export_csv')}
                </button>
                <button
                  onClick={() => {
                    exportToJson(filteredLogs);
                    setShowExportMenu(false);
                  }}
                  className="w-full text-left px-4 py-2 text-sm text-gray-700 dark:text-slate-200 hover:bg-gray-50 dark:hover:bg-slate-700 rounded-b-lg"
                >
                  {t('audit.export_json')}
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <BarChart3 className="w-4 h-4 text-gray-400 dark:text-slate-500" />
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {t('audit.actions_today')}
            </p>
          </div>
          <p className="text-2xl font-bold text-gray-900 dark:text-white">{summaryStats.actionsToday}</p>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <Users className="w-4 h-4 text-gray-400 dark:text-slate-500" />
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {t('audit.top_users')}
            </p>
          </div>
          <div className="space-y-1">
            {summaryStats.topUsers.length === 0 ? (
              <p className="text-sm text-gray-400 dark:text-slate-500">-</p>
            ) : (
              summaryStats.topUsers.map(([name, count]) => (
                <div key={name} className="flex items-center justify-between text-sm">
                  <span className="text-gray-700 dark:text-slate-300 truncate mr-2">{name}</span>
                  <span className="text-gray-500 dark:text-slate-400 font-mono">{count}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <Building2 className="w-4 h-4 text-gray-400 dark:text-slate-500" />
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {t('audit.most_active_entities')}
            </p>
          </div>
          <div className="space-y-1">
            {summaryStats.topEntities.length === 0 ? (
              <p className="text-sm text-gray-400 dark:text-slate-500">-</p>
            ) : (
              summaryStats.topEntities.map(([entity, count]) => (
                <div key={entity} className="flex items-center justify-between text-sm">
                  <span className="flex items-center gap-1.5 text-gray-700 dark:text-slate-300">
                    {getEntityIcon(entity)}
                    {entity}
                  </span>
                  <span className="text-gray-500 dark:text-slate-400 font-mono">{count}</span>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-1">
            <Activity className="w-4 h-4 text-gray-400 dark:text-slate-500" />
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
              {t('audit.action_distribution')}
            </p>
          </div>
          <div className="flex flex-wrap gap-1.5 mt-1">
            {Object.entries(summaryStats.actionCounts).map(([action, count]) => (
              <span
                key={action}
                className={cn(
                  'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full',
                  actionColors[action] || 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
                )}
              >
                {action}
                <span className="opacity-70">{count}</span>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-3 sm:p-4 shadow-sm space-y-2 sm:space-y-3 overflow-hidden">
        {/* Row 1: dropdowns */}
        <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-2 sm:gap-3">
          <select
            value={userFilter}
            onChange={(e) => {
              setUserFilter(e.target.value);
              setPage(1);
            }}
            aria-label={t('audit.filter_user')}
            className="w-full sm:w-auto sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0"
          >
            <option value="">{t('audit.all_users')}</option>
            {usersList.map((u: User) => (
              <option key={u.id} value={u.id}>
                {u.first_name} {u.last_name} ({u.email})
              </option>
            ))}
          </select>

          <select
            value={entityTypeFilter}
            onChange={(e) => {
              setEntityTypeFilter(e.target.value);
              setPage(1);
            }}
            aria-label={t('audit.filter_entity_type')}
            className="w-full sm:w-auto sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0"
          >
            <option value="">{t('audit.all_entity_types')}</option>
            {ENTITY_TYPES.map((et) => (
              <option key={et} value={et}>
                {et}
              </option>
            ))}
          </select>

          <select
            value={actionFilter}
            onChange={(e) => {
              setActionFilter(e.target.value);
              setPage(1);
            }}
            aria-label={t('audit.filter_action')}
            className="w-full sm:w-auto sm:flex-none px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0"
          >
            <option value="">{t('audit.all_actions')}</option>
            {ACTIONS.map((a) => (
              <option key={a} value={a}>
                {a}
              </option>
            ))}
          </select>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="flex items-center gap-1 px-3 py-2 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 transition-colors"
            >
              <X className="w-4 h-4" />
              {t('audit.clear_filters')}
            </button>
          )}
        </div>

        {/* Row 2: date presets + date inputs + search */}
        <div className="flex flex-col sm:flex-row sm:flex-wrap sm:items-center gap-2 sm:gap-3">
          <div className="flex items-center gap-1 bg-gray-100 dark:bg-slate-700 rounded-lg p-0.5 overflow-x-auto">
            {(['today', '7days', '30days', 'custom'] as DatePreset[]).map((preset) => (
              <button
                key={preset}
                onClick={() => handleDatePreset(preset)}
                className={cn(
                  'px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
                  datePreset === preset
                    ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-white shadow-sm'
                    : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200',
                )}
              >
                {t(`audit.date_preset_${preset}`)}
              </button>
            ))}
          </div>

          {datePreset === 'custom' && (
            <>
              <input
                type="date"
                value={dateFrom}
                onChange={(e) => {
                  setDateFrom(e.target.value);
                  setPage(1);
                }}
                aria-label={t('audit.filter_date_from')}
                className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
              />
              <input
                type="date"
                value={dateTo}
                onChange={(e) => {
                  setDateTo(e.target.value);
                  setPage(1);
                }}
                aria-label={t('audit.filter_date_to')}
                className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
              />
            </>
          )}

          <div className="relative w-full sm:flex-1 sm:min-w-[200px]">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 dark:text-slate-500" />
            <input
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              placeholder={t('audit.search_placeholder')}
              className="w-full pl-9 pr-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-slate-500"
            />
          </div>
        </div>
      </div>

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      ) : error ? (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
          <AlertTriangle className="w-8 h-8 text-red-500 dark:text-red-400 mx-auto mb-2" />
          <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
        </div>
      ) : filteredLogs.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-12 text-center">
          <FileSearch className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400 text-sm">{t('audit.empty')}</p>
        </div>
      ) : viewMode === 'table' ? (
        /* Table View */
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400 w-8" />
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('audit.date')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('audit.user')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('audit.action')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('audit.entity_type')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('audit.entity_id')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('audit.ip_address')}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                {filteredLogs.map((log: AuditLog) => (
                  <AuditLogRow
                    key={log.id}
                    log={log}
                    expanded={expandedRow === log.id}
                    onToggle={() => toggleExpand(log.id)}
                    t={t}
                  />
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        /* Timeline View */
        <div className="space-y-6">
          {timelineGroups.length === 0 ? (
            <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-12 text-center">
              <Clock className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
              <p className="text-gray-500 dark:text-slate-400 text-sm">{t('audit.timeline_empty')}</p>
            </div>
          ) : (
            timelineGroups.map(([date, groupLogs]) => (
              <div key={date}>
                <h3 className="text-sm font-semibold text-gray-500 dark:text-slate-400 mb-3 sticky top-0 bg-gray-50 dark:bg-slate-900 py-1 z-10">
                  {date}
                </h3>
                <div className="relative ml-4 border-l-2 border-gray-200 dark:border-slate-700 pl-6 space-y-4">
                  {groupLogs.map((log: AuditLog) => (
                    <TimelineItem
                      key={log.id}
                      log={log}
                      expanded={expandedRow === log.id}
                      onToggle={() => toggleExpand(log.id)}
                      t={t}
                    />
                  ))}
                </div>
              </div>
            ))
          )}
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
    </div>
  );
}

/* ─────────────────────────────── Table Row ─────────────────────────────── */

function AuditLogRow({
  log,
  expanded,
  onToggle,
  t,
}: {
  log: AuditLog;
  expanded: boolean;
  onToggle: () => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  return (
    <>
      <tr
        className={cn('hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors cursor-pointer')}
        onClick={onToggle}
      >
        <td className="px-4 py-3">
          {expanded ? (
            <ChevronUp className="w-4 h-4 text-gray-400" />
          ) : (
            <ChevronDown className="w-4 h-4 text-gray-400" />
          )}
        </td>
        <td className="px-4 py-3 text-gray-600 dark:text-slate-300 whitespace-nowrap">
          {formatDateTimeLocal(log.timestamp)}
        </td>
        <td className="px-4 py-3 text-gray-900 dark:text-white whitespace-nowrap">
          {log.user_name || log.user_email || t('audit.system')}
        </td>
        <td className="px-4 py-3 whitespace-nowrap">
          <span
            className={cn(
              'px-2 py-0.5 text-xs font-medium rounded-full',
              actionColors[log.action] || 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
            )}
          >
            {log.action}
          </span>
        </td>
        <td className="px-4 py-3 text-gray-600 dark:text-slate-300 whitespace-nowrap">
          <span className="inline-flex items-center gap-1.5">
            {getEntityIcon(log.entity_type)}
            {log.entity_type || '-'}
          </span>
        </td>
        <td className="px-4 py-3 text-gray-500 dark:text-slate-400 whitespace-nowrap font-mono text-xs">
          {log.entity_id ? log.entity_id.slice(0, 8) + '...' : '-'}
        </td>
        <td className="px-4 py-3 text-gray-500 dark:text-slate-400 whitespace-nowrap font-mono text-xs">
          {log.ip_address || '-'}
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={7} className="px-8 py-4 bg-gray-50 dark:bg-slate-800/80">
            <ExpandedDetails log={log} t={t} />
          </td>
        </tr>
      )}
    </>
  );
}

/* ─────────────────────────── Expanded Details ─────────────────────────── */

function ExpandedDetails({
  log,
  t,
}: {
  log: AuditLog;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  const details = log.details || {};
  const payload = details.request_payload || details.payload || details.changes || null;
  const responseStatus = details.response_status || details.status_code || null;
  const userAgent = details.user_agent || null;
  const duration = details.duration_ms || details.duration || null;

  const hasAnyDetail = payload || responseStatus || userAgent || duration || Object.keys(details).length > 0;

  if (!hasAnyDetail) {
    return <p className="text-xs text-gray-400 dark:text-slate-500 italic">{t('audit.no_details')}</p>;
  }

  return (
    <div className="space-y-3">
      {/* Structured detail fields */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {responseStatus && (
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-0.5">{t('audit.response_status')}</p>
            <p className="text-sm text-gray-700 dark:text-slate-300 font-mono">{String(responseStatus)}</p>
          </div>
        )}
        {userAgent && (
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-0.5">{t('audit.user_agent')}</p>
            <p className="text-sm text-gray-700 dark:text-slate-300 truncate" title={String(userAgent)}>
              {String(userAgent)}
            </p>
          </div>
        )}
        {duration && (
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-0.5">{t('audit.duration')}</p>
            <p className="text-sm text-gray-700 dark:text-slate-300 font-mono">
              {t('audit.duration_ms', { value: String(duration) })}
            </p>
          </div>
        )}
        {log.ip_address && (
          <div>
            <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-0.5">{t('audit.ip_address')}</p>
            <p className="text-sm text-gray-700 dark:text-slate-300 font-mono">{log.ip_address}</p>
          </div>
        )}
      </div>

      {/* Request payload */}
      {payload && (
        <div>
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">{t('audit.request_payload')}</p>
          <pre className="text-xs text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-900 rounded-lg p-3 overflow-x-auto border border-gray-200 dark:border-slate-700 max-h-48">
            {typeof payload === 'object' ? JSON.stringify(payload, null, 2) : String(payload)}
          </pre>
        </div>
      )}

      {/* Full details JSON (fallback) */}
      {!payload && Object.keys(details).length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">{t('audit.details')}</p>
          <pre className="text-xs text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-900 rounded-lg p-3 overflow-x-auto border border-gray-200 dark:border-slate-700 max-h-48">
            {JSON.stringify(details, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

/* ─────────────────────────── Timeline Item ─────────────────────────── */

function TimelineItem({
  log,
  expanded,
  onToggle,
  t,
}: {
  log: AuditLog;
  expanded: boolean;
  onToggle: () => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}) {
  return (
    <div>
      {/* Dot on the timeline line */}
      <div
        className={cn(
          'absolute -left-[5px] w-2.5 h-2.5 rounded-full border-2 border-white dark:border-slate-900 mt-1.5',
          actionDotColors[log.action] || 'bg-gray-400',
        )}
        style={{ marginLeft: '-4px' }}
      />

      <div
        className={cn(
          'bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-3 cursor-pointer hover:border-gray-300 dark:hover:border-slate-600 transition-colors',
          expanded && 'ring-1 ring-red-200 dark:ring-red-800 border-red-200 dark:border-red-800',
        )}
        onClick={onToggle}
      >
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-center gap-2 flex-1 min-w-0">
            <span className="text-gray-400 dark:text-slate-500 flex-shrink-0">{getEntityIcon(log.entity_type)}</span>
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span
                  className={cn(
                    'px-2 py-0.5 text-xs font-medium rounded-full',
                    actionColors[log.action] || 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300',
                  )}
                >
                  {log.action}
                </span>
                <span className="text-sm text-gray-600 dark:text-slate-300">{log.entity_type || '-'}</span>
                {log.entity_id && (
                  <span className="text-xs text-gray-400 dark:text-slate-500 font-mono">
                    {log.entity_id.slice(0, 8)}...
                  </span>
                )}
              </div>
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">
                {log.user_name || log.user_email || t('audit.system')}
              </p>
            </div>
          </div>
          <span className="text-xs text-gray-400 dark:text-slate-500 whitespace-nowrap flex-shrink-0">
            {formatTimeOnly(log.timestamp)}
          </span>
        </div>

        {expanded && (
          <div className="mt-3 pt-3 border-t border-gray-100 dark:border-slate-700">
            <ExpandedDetails log={log} t={t} />
          </div>
        )}
      </div>
    </div>
  );
}
