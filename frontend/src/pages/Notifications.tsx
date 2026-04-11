/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view (notification center).
 * Not currently routed in App.tsx but used as component reference.
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient, useInfiniteQuery } from '@tanstack/react-query';
import {
  Bell,
  CheckCheck,
  Info,
  UserPlus,
  Download,
  AlertCircle,
  Mail,
  MailOpen,
  Trash2,
  CheckSquare,
  Square,
  Minus,
  X,
  Filter,
  Loader2,
} from 'lucide-react';
import { formatDistanceToNow, isToday, isYesterday, differenceInDays } from 'date-fns';
import { useTranslation } from '@/i18n';
import { notificationsApi } from '@/api/notifications';
import { cn } from '@/utils/formatters';
import type { Notification, NotificationType } from '@/types';

// ─── Constants ──────────────────────────────────────────────────────────────

const NOTIFICATION_TYPES: NotificationType[] = ['action', 'invitation', 'export', 'system'];
const STATUS_OPTIONS: Array<{ value: string; labelKey: string }> = [
  { value: '', labelKey: 'notification.filter_all_statuses' },
  { value: 'unread', labelKey: 'notification.unread' },
  { value: 'read', labelKey: 'notification.filter_read' },
];

const PAGE_SIZE = 20;

const TYPE_ICONS: Record<NotificationType, typeof Info> = {
  action: AlertCircle,
  invitation: UserPlus,
  export: Download,
  system: Info,
};

const TYPE_COLORS: Record<NotificationType, { bg: string; text: string; dot: string }> = {
  action: {
    bg: 'bg-blue-100 dark:bg-blue-900/30',
    text: 'text-blue-600 dark:text-blue-400',
    dot: 'bg-blue-500',
  },
  invitation: {
    bg: 'bg-purple-100 dark:bg-purple-900/30',
    text: 'text-purple-600 dark:text-purple-400',
    dot: 'bg-purple-500',
  },
  export: {
    bg: 'bg-green-100 dark:bg-green-900/30',
    text: 'text-green-600 dark:text-green-400',
    dot: 'bg-green-500',
  },
  system: {
    bg: 'bg-gray-100 dark:bg-gray-700',
    text: 'text-gray-600 dark:text-gray-400',
    dot: 'bg-gray-500',
  },
};

// ─── Helpers ────────────────────────────────────────────────────────────────

type DateGroup = 'today' | 'yesterday' | 'this_week' | 'older';

function getDateGroup(dateStr: string): DateGroup {
  const date = new Date(dateStr);
  if (isToday(date)) return 'today';
  if (isYesterday(date)) return 'yesterday';
  if (differenceInDays(new Date(), date) <= 7) return 'this_week';
  return 'older';
}

function groupNotifications(notifications: Notification[]): Map<DateGroup, Notification[]> {
  const groups = new Map<DateGroup, Notification[]>();
  for (const n of notifications) {
    const group = getDateGroup(n.created_at);
    if (!groups.has(group)) groups.set(group, []);
    groups.get(group)!.push(n);
  }
  return groups;
}

// ─── Notification Row ───────────────────────────────────────────────────────

interface NotificationRowProps {
  notification: Notification;
  isSelected: boolean;
  onToggleSelect: () => void;
  onMarkRead: () => void;
  onMarkUnread: () => void;
  onDelete: () => void;
  onClick: () => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

function NotificationRow({
  notification,
  isSelected,
  onToggleSelect,
  onMarkRead,
  onMarkUnread,
  onDelete,
  onClick,
  t,
}: NotificationRowProps) {
  const [hovered, setHovered] = useState(false);
  const isUnread = notification.status === 'unread';
  const colors = TYPE_COLORS[notification.type] || TYPE_COLORS.system;
  const Icon = TYPE_ICONS[notification.type] || Info;

  return (
    <div
      className={cn(
        'group flex items-start gap-3 px-4 py-3 transition-colors relative',
        isUnread ? 'bg-slate-50 dark:bg-slate-800/80' : 'bg-white dark:bg-slate-800',
        isSelected && 'bg-red-50/50 dark:bg-red-900/10',
        'hover:bg-slate-100 dark:hover:bg-slate-700/50',
      )}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Checkbox */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onToggleSelect();
        }}
        className="mt-1 flex-shrink-0 text-gray-400 hover:text-red-500 dark:text-slate-500 dark:hover:text-red-400 transition-colors"
        aria-label={isSelected ? t('notification.deselect') : t('notification.select')}
      >
        {isSelected ? (
          <CheckSquare className="w-4 h-4 text-red-500 dark:text-red-400" />
        ) : (
          <Square className="w-4 h-4" />
        )}
      </button>

      {/* Icon */}
      <div className={cn('flex-shrink-0 w-9 h-9 rounded-full flex items-center justify-center mt-0.5', colors.bg)}>
        <Icon className={cn('w-4 h-4', colors.text)} />
      </div>

      {/* Content */}
      <button onClick={onClick} className="flex-1 min-w-0 text-left">
        <div className="flex items-start gap-2">
          <div className="flex-1 min-w-0">
            <p
              className={cn(
                'text-sm leading-tight',
                isUnread
                  ? 'font-semibold text-slate-900 dark:text-white'
                  : 'font-normal text-slate-700 dark:text-slate-300',
              )}
            >
              {notification.title}
            </p>
            {notification.body && (
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-2">{notification.body}</p>
            )}
            <div className="flex items-center gap-2 mt-1">
              <span
                className={cn(
                  'inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded-full',
                  colors.bg,
                  colors.text,
                )}
              >
                {t(`notification_type.${notification.type}`)}
              </span>
              <span className="text-xs text-slate-400 dark:text-slate-500">
                {formatDistanceToNow(new Date(notification.created_at), { addSuffix: true })}
              </span>
            </div>
          </div>
          {isUnread && <div className={cn('flex-shrink-0 w-2 h-2 mt-2 rounded-full', colors.dot)} />}
        </div>
      </button>

      {/* Hover actions */}
      {hovered && (
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-1 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-600 rounded-lg shadow-sm px-1 py-0.5">
          {isUnread ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onMarkRead();
              }}
              className="p-1.5 text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
              title={t('notification.mark_read')}
              aria-label={t('notification.mark_read')}
            >
              <MailOpen className="w-3.5 h-3.5" />
            </button>
          ) : (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onMarkUnread();
              }}
              className="p-1.5 text-slate-500 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
              title={t('notification.mark_unread')}
              aria-label={t('notification.mark_unread')}
            >
              <Mail className="w-3.5 h-3.5" />
            </button>
          )}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onDelete();
            }}
            className="p-1.5 text-slate-500 hover:text-red-600 dark:hover:text-red-400 transition-colors"
            title={t('notification.delete')}
            aria-label={t('notification.delete')}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ──────────────────────────────────────────────────────────────

export default function Notifications() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // ── Filters ──
  const [typeFilter, setTypeFilter] = useState<string>('');
  const [statusFilter, setStatusFilter] = useState<string>('');

  // ── Selection ──
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // ── Unread count ──
  const { data: unreadData } = useQuery({
    queryKey: ['notifications', 'unread-count'],
    queryFn: notificationsApi.getUnreadCount,
    refetchInterval: 30_000,
    staleTime: 10_000,
  });
  const unreadCount = unreadData?.count ?? 0;

  // ── Infinite scroll notifications ──
  const {
    data: pagesData,
    isLoading,
    isError,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['notifications', 'list', typeFilter, statusFilter],
    queryFn: async ({ pageParam = 1 }) => {
      return notificationsApi.list({
        type: typeFilter || undefined,
        status: statusFilter || undefined,
        page: pageParam,
        size: PAGE_SIZE,
      });
    },
    getNextPageParam: (lastPage) => {
      if (lastPage.page < lastPage.pages) return lastPage.page + 1;
      return undefined;
    },
    initialPageParam: 1,
    staleTime: 5_000,
  });

  const allNotifications = useMemo(() => {
    if (!pagesData) return [];
    return pagesData.pages.flatMap((page) => page.items);
  }, [pagesData]);

  const totalCount = pagesData?.pages[0]?.total ?? 0;

  // ── Grouped notifications ──
  const grouped = useMemo(() => groupNotifications(allNotifications), [allNotifications]);

  const groupOrder: DateGroup[] = ['today', 'yesterday', 'this_week', 'older'];
  const groupLabelKeys: Record<DateGroup, string> = {
    today: 'notification.group_today',
    yesterday: 'notification.group_yesterday',
    this_week: 'notification.group_this_week',
    older: 'notification.group_older',
  };

  // ── Mutations ──
  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['notifications'] });
  };

  const markReadMutation = useMutation({
    mutationFn: notificationsApi.markRead,
    onSuccess: invalidateAll,
  });

  const markUnreadMutation = useMutation({
    mutationFn: notificationsApi.markUnread,
    onSuccess: invalidateAll,
  });

  const markAllReadMutation = useMutation({
    mutationFn: notificationsApi.markAllRead,
    onSuccess: invalidateAll,
  });

  const deleteMutation = useMutation({
    mutationFn: notificationsApi.delete,
    onSuccess: invalidateAll,
  });

  const bulkMarkReadMutation = useMutation({
    mutationFn: async (ids: string[]) => {
      await Promise.all(ids.map((id) => notificationsApi.markRead(id)));
    },
    onSuccess: () => {
      invalidateAll();
      setSelectedIds(new Set());
    },
  });

  const bulkDeleteMutation = useMutation({
    mutationFn: notificationsApi.deleteBatch,
    onSuccess: () => {
      invalidateAll();
      setSelectedIds(new Set());
    },
  });

  // ── Handlers ──
  const handleNotificationClick = useCallback(
    (notification: Notification) => {
      if (notification.status === 'unread') {
        markReadMutation.mutate(notification.id);
      }
      if (notification.link) {
        navigate(notification.link);
      }
    },
    [markReadMutation, navigate],
  );

  const handleToggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setSelectedIds((prev) => {
      if (prev.size === allNotifications.length && allNotifications.every((n) => prev.has(n.id))) {
        return new Set();
      }
      return new Set(allNotifications.map((n) => n.id));
    });
  }, [allNotifications]);

  const handleBulkMarkRead = useCallback(() => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    bulkMarkReadMutation.mutate(ids);
  }, [selectedIds, bulkMarkReadMutation]);

  const handleBulkDelete = useCallback(() => {
    const ids = Array.from(selectedIds);
    if (ids.length === 0) return;
    bulkDeleteMutation.mutate(ids);
  }, [selectedIds, bulkDeleteMutation]);

  const hasActiveFilters = typeFilter || statusFilter;

  const clearFilters = () => {
    setTypeFilter('');
    setStatusFilter('');
  };

  const selectCls =
    'px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('notification.title')}</h1>
          {unreadCount > 0 && (
            <span className="inline-flex items-center justify-center min-w-[24px] h-6 px-2 text-xs font-bold text-white bg-red-500 rounded-full">
              {unreadCount > 99 ? '99+' : unreadCount}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {unreadCount > 0 && (
            <button
              onClick={() => markAllReadMutation.mutate()}
              disabled={markAllReadMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors disabled:opacity-50"
            >
              <CheckCheck className="w-4 h-4" />
              {t('notification.mark_all_read')}
            </button>
          )}
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <Filter className="w-4 h-4 text-gray-400 dark:text-slate-500 flex-shrink-0" />

          {/* Type filter */}
          <select
            value={typeFilter}
            onChange={(e) => setTypeFilter(e.target.value)}
            aria-label={t('notification.filter_by_type')}
            className={cn(selectCls, 'flex-1 sm:flex-none')}
          >
            <option value="">{t('notification.filter_all_types')}</option>
            {NOTIFICATION_TYPES.map((type) => (
              <option key={type} value={type}>
                {t(`notification_type.${type}`)}
              </option>
            ))}
          </select>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label={t('notification.filter_by_status')}
            className={cn(selectCls, 'flex-1 sm:flex-none')}
          >
            {STATUS_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {t(opt.labelKey)}
              </option>
            ))}
          </select>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-1 px-3 py-2 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              <X className="w-3.5 h-3.5" />
              {t('notification.clear_filters')}
            </button>
          )}

          <span className="ml-auto text-xs text-gray-500 dark:text-slate-400">
            {t('notification.total_count', { count: totalCount })}
          </span>
        </div>
      </div>

      {/* Bulk actions bar */}
      {selectedIds.size > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-3 flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-red-700 dark:text-red-400">
            {t('notification.selected_count', { count: selectedIds.size })}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={handleBulkMarkRead}
              disabled={bulkMarkReadMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-blue-700 dark:text-blue-400 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/40 transition-colors disabled:opacity-50"
            >
              <MailOpen className="w-3.5 h-3.5" />
              {t('notification.bulk_mark_read')}
            </button>
            <button
              onClick={handleBulkDelete}
              disabled={bulkDeleteMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-700 dark:text-red-400 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40 transition-colors disabled:opacity-50"
            >
              <Trash2 className="w-3.5 h-3.5" />
              {t('notification.bulk_delete')}
            </button>
          </div>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="ml-auto text-xs text-red-600 dark:text-red-400 hover:underline"
          >
            {t('notification.deselect_all')}
          </button>
        </div>
      )}

      {/* Content */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      ) : isError ? (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
          <AlertCircle className="w-8 h-8 text-red-500 dark:text-red-400 mx-auto mb-2" />
          <p className="text-red-700 dark:text-red-300">{t('notification.load_error')}</p>
        </div>
      ) : allNotifications.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-12 text-center">
          <Bell className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400 text-sm">
            {hasActiveFilters ? t('notification.no_match') : t('notification.no_notifications')}
          </p>
          {hasActiveFilters && (
            <button onClick={clearFilters} className="mt-3 text-sm text-red-600 dark:text-red-400 hover:underline">
              {t('notification.clear_filters')}
            </button>
          )}
        </div>
      ) : (
        <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
          {/* Select all toggle */}
          <div className="flex items-center gap-2 px-4 py-2 border-b border-gray-100 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
            <button
              onClick={handleSelectAll}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 transition-colors"
            >
              {selectedIds.size > 0 && allNotifications.every((n) => selectedIds.has(n.id)) ? (
                <Minus className="w-4 h-4" />
              ) : (
                <CheckSquare className="w-4 h-4" />
              )}
              {selectedIds.size > 0 ? t('notification.deselect_all') : t('notification.select_all')}
            </button>
          </div>

          {/* Grouped notification list */}
          {groupOrder.map((group) => {
            const items = grouped.get(group);
            if (!items || items.length === 0) return null;
            return (
              <div key={group}>
                <div className="px-4 py-2 bg-gray-50 dark:bg-slate-700/30 border-b border-gray-100 dark:border-slate-700">
                  <h3 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                    {t(groupLabelKeys[group])}
                  </h3>
                </div>
                <div className="divide-y divide-gray-100 dark:divide-slate-700">
                  {items.map((notification) => (
                    <NotificationRow
                      key={notification.id}
                      notification={notification}
                      isSelected={selectedIds.has(notification.id)}
                      onToggleSelect={() => handleToggleSelect(notification.id)}
                      onMarkRead={() => markReadMutation.mutate(notification.id)}
                      onMarkUnread={() => markUnreadMutation.mutate(notification.id)}
                      onDelete={() => deleteMutation.mutate(notification.id)}
                      onClick={() => handleNotificationClick(notification)}
                      t={t}
                    />
                  ))}
                </div>
              </div>
            );
          })}

          {/* Load more */}
          {hasNextPage && (
            <div className="flex items-center justify-center py-4 border-t border-gray-100 dark:border-slate-700">
              <button
                onClick={() => fetchNextPage()}
                disabled={isFetchingNextPage}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors disabled:opacity-50"
              >
                {isFetchingNextPage && <Loader2 className="w-4 h-4 animate-spin" />}
                {t('notification.load_more')}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
