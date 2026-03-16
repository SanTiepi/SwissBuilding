import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { unknownsApi } from '@/api/unknowns';
import type { UnknownIssueUpdatePayload } from '@/api/unknowns';
import { useTranslation } from '@/i18n';
import { useAuth } from '@/hooks/useAuth';
import { cn, formatDate } from '@/utils/formatters';
import { toast } from '@/store/toastStore';
import type { UnknownIssue, UnknownType, UnknownSeverity, UnknownStatus } from '@/types';
import {
  HelpCircle,
  AlertTriangle,
  CheckCircle2,
  Eye,
  XCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  Filter,
  ArrowUpDown,
  BarChart3,
  ShieldAlert,
  Bot,
  User,
  X,
} from 'lucide-react';

/* ---------- Constants ---------- */

const UNKNOWN_TYPES: UnknownType[] = [
  'uninspected_zone',
  'missing_plan',
  'unconfirmed_material',
  'undocumented_intervention',
  'incomplete_diagnostic',
  'missing_sample',
  'unverified_source',
  'accessibility_unknown',
  'missing_diagnostic',
  'missing_pollutant_evaluation',
  'missing_lab_results',
];

const SEVERITY_ORDER: Record<UnknownSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
};

const SEVERITY_COLORS: Record<string, { bg: string; text: string; dot: string }> = {
  critical: {
    bg: 'bg-red-100 dark:bg-red-900/30',
    text: 'text-red-700 dark:text-red-400',
    dot: 'bg-red-500',
  },
  high: {
    bg: 'bg-orange-100 dark:bg-orange-900/30',
    text: 'text-orange-700 dark:text-orange-400',
    dot: 'bg-orange-500',
  },
  medium: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/30',
    text: 'text-yellow-700 dark:text-yellow-400',
    dot: 'bg-yellow-500',
  },
  low: {
    bg: 'bg-green-100 dark:bg-green-900/30',
    text: 'text-green-700 dark:text-green-400',
    dot: 'bg-green-500',
  },
};

const STATUS_COLORS: Record<string, { bg: string; text: string }> = {
  open: { bg: 'bg-blue-100 dark:bg-blue-900/30', text: 'text-blue-700 dark:text-blue-400' },
  acknowledged: { bg: 'bg-amber-100 dark:bg-amber-900/30', text: 'text-amber-700 dark:text-amber-400' },
  resolved: { bg: 'bg-green-100 dark:bg-green-900/30', text: 'text-green-700 dark:text-green-400' },
  accepted_risk: { bg: 'bg-purple-100 dark:bg-purple-900/30', text: 'text-purple-700 dark:text-purple-400' },
};

const CATEGORY_COLORS: Record<string, string> = {
  uninspected_zone: 'bg-violet-500',
  missing_plan: 'bg-blue-500',
  unconfirmed_material: 'bg-amber-500',
  undocumented_intervention: 'bg-rose-500',
  incomplete_diagnostic: 'bg-orange-500',
  missing_sample: 'bg-cyan-500',
  unverified_source: 'bg-slate-500',
  accessibility_unknown: 'bg-teal-500',
  missing_diagnostic: 'bg-red-500',
  missing_pollutant_evaluation: 'bg-pink-500',
  missing_lab_results: 'bg-indigo-500',
};

type SortField = 'severity' | 'created_at' | 'unknown_type';
type SortDir = 'asc' | 'desc';

/* ---------- Sub-components ---------- */

function SummaryCard({
  label,
  value,
  icon,
  className,
}: {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        'flex items-center gap-3 rounded-xl p-4 bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700',
        className,
      )}
    >
      <div className="flex-shrink-0">{icon}</div>
      <div>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
        <p className="text-xs text-gray-500 dark:text-slate-400">{label}</p>
      </div>
    </div>
  );
}

function CategoryBar({ type, count, total }: { type: string; count: number; total: number }) {
  const { t } = useTranslation();
  const pct = total > 0 ? (count / total) * 100 : 0;
  return (
    <div className="flex items-center gap-2 text-xs">
      <span className={cn('w-2.5 h-2.5 rounded-full flex-shrink-0', CATEGORY_COLORS[type] ?? 'bg-gray-400')} />
      <span className="flex-1 text-gray-700 dark:text-slate-300 truncate">
        {t(`unknown_issue.type_${type}`) || type.replace(/_/g, ' ')}
      </span>
      <div className="w-24 bg-gray-200 dark:bg-slate-700 rounded-full h-2">
        <div className={cn('h-2 rounded-full', CATEGORY_COLORS[type] ?? 'bg-gray-400')} style={{ width: `${pct}%` }} />
      </div>
      <span className="w-6 text-right text-gray-500 dark:text-slate-400">{count}</span>
    </div>
  );
}

function IssueRow({
  issue,
  isExpanded,
  isSelected,
  onToggle,
  onSelect,
  onAcknowledge,
  onResolve,
  onDismiss,
  isMutating,
}: {
  issue: UnknownIssue;
  isExpanded: boolean;
  isSelected: boolean;
  onToggle: () => void;
  onSelect: (checked: boolean) => void;
  onAcknowledge: () => void;
  onResolve: (notes: string) => void;
  onDismiss: (reason: string) => void;
  isMutating: boolean;
}) {
  const { t } = useTranslation();
  const [resolveNotes, setResolveNotes] = useState('');
  const [dismissReason, setDismissReason] = useState('');
  const [showResolveForm, setShowResolveForm] = useState(false);
  const [showDismissForm, setShowDismissForm] = useState(false);

  const sevColor = SEVERITY_COLORS[issue.severity] ?? SEVERITY_COLORS.medium;
  const statusColor = STATUS_COLORS[issue.status] ?? STATUS_COLORS.open;
  const isAutoResolved = issue.detected_by === 'system' && issue.status === 'resolved';
  const isTerminal = issue.status === 'resolved' || issue.status === 'accepted_risk';

  return (
    <div
      className={cn(
        'border rounded-lg transition-colors',
        isExpanded
          ? 'border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-800'
          : 'border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800',
      )}
    >
      {/* Row header */}
      <div className="flex items-center gap-3 px-4 py-3 cursor-pointer" onClick={onToggle}>
        {!isTerminal && (
          <input
            type="checkbox"
            checked={isSelected}
            onChange={(e) => {
              e.stopPropagation();
              onSelect(e.target.checked);
            }}
            onClick={(e) => e.stopPropagation()}
            className="w-4 h-4 rounded border-gray-300 dark:border-slate-600 text-red-600 focus:ring-red-500"
          />
        )}
        {isTerminal && <div className="w-4" />}

        {/* Severity dot */}
        <span className={cn('w-2.5 h-2.5 rounded-full flex-shrink-0', sevColor.dot)} />

        {/* Category badge */}
        <span
          className={cn(
            'px-2 py-0.5 text-xs font-medium rounded-full flex-shrink-0',
            'bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300',
          )}
        >
          {t(`unknown_issue.type_${issue.unknown_type}`) || issue.unknown_type.replace(/_/g, ' ')}
        </span>

        {/* Title */}
        <span className="flex-1 text-sm text-gray-800 dark:text-slate-200 truncate">{issue.title}</span>

        {/* Auto-resolve indicator */}
        {isAutoResolved && (
          <span className="flex items-center gap-1 px-1.5 py-0.5 text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 rounded">
            <Bot className="w-3 h-3" />
            {t('unknown_issue.auto_resolved')}
          </span>
        )}
        {issue.status === 'resolved' && !isAutoResolved && (
          <span className="flex items-center gap-1 px-1.5 py-0.5 text-xs bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400 rounded">
            <User className="w-3 h-3" />
            {t('unknown_issue.manually_resolved')}
          </span>
        )}

        {/* Status badge */}
        <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', statusColor.bg, statusColor.text)}>
          {t(`unknown_issue.status_${issue.status}`) || issue.status}
        </span>

        {/* Severity badge */}
        <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', sevColor.bg, sevColor.text)}>
          {t(`unknown_issue.severity_${issue.severity}`) || issue.severity}
        </span>

        {/* Blocks readiness */}
        {issue.blocks_readiness && (
          <span title={t('unknown_issue.blocks_readiness_label')}>
            <AlertTriangle className="w-4 h-4 text-red-500 flex-shrink-0" />
          </span>
        )}

        {/* Expand arrow */}
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400 flex-shrink-0" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400 flex-shrink-0" />
        )}
      </div>

      {/* Expanded detail */}
      {isExpanded && (
        <div className="px-4 pb-4 border-t border-gray-100 dark:border-slate-700">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
            {/* Description */}
            <div>
              <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase mb-1">
                {t('unknown_issue.description')}
              </h4>
              <p className="text-sm text-gray-700 dark:text-slate-300">
                {issue.description || t('unknown_issue.no_description')}
              </p>
            </div>

            {/* Affected entity */}
            <div>
              <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase mb-1">
                {t('unknown_issue.affected_entity')}
              </h4>
              <p className="text-sm text-gray-700 dark:text-slate-300">
                {issue.entity_type
                  ? `${issue.entity_type}${issue.entity_id ? ` (${issue.entity_id.slice(0, 8)}...)` : ''}`
                  : t('unknown_issue.no_entity')}
              </p>
            </div>

            {/* Dates */}
            <div>
              <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase mb-1">
                {t('unknown_issue.detected_date')}
              </h4>
              <p className="text-sm text-gray-700 dark:text-slate-300">{formatDate(issue.created_at)}</p>
            </div>

            {/* Detected by */}
            <div>
              <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase mb-1">
                {t('unknown_issue.detected_by')}
              </h4>
              <p className="text-sm text-gray-700 dark:text-slate-300 flex items-center gap-1">
                {issue.detected_by === 'system' ? (
                  <>
                    <Bot className="w-3.5 h-3.5" /> {t('unknown_issue.system')}
                  </>
                ) : (
                  <>
                    <User className="w-3.5 h-3.5" /> {issue.detected_by || t('unknown_issue.manual')}
                  </>
                )}
              </p>
            </div>

            {/* Readiness impact */}
            {issue.blocks_readiness && (
              <div className="md:col-span-2">
                <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase mb-1">
                  {t('unknown_issue.readiness_impact')}
                </h4>
                <div className="flex items-center gap-2 px-3 py-2 bg-red-50 dark:bg-red-900/20 rounded-lg">
                  <AlertTriangle className="w-4 h-4 text-red-500" />
                  <span className="text-sm text-red-600 dark:text-red-400">
                    {issue.readiness_types_affected || t('unknown_issue.blocks_readiness_label')}
                  </span>
                </div>
              </div>
            )}

            {/* Resolution info */}
            {(issue.status === 'resolved' || issue.status === 'accepted_risk') && issue.resolution_notes && (
              <div className="md:col-span-2">
                <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase mb-1">
                  {t('unknown_issue.resolution_notes')}
                </h4>
                <p className="text-sm text-gray-700 dark:text-slate-300 bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2">
                  {issue.resolution_notes}
                </p>
                {issue.resolved_at && (
                  <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
                    {t('unknown_issue.resolved_on')} {formatDate(issue.resolved_at)}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Action buttons */}
          {!isTerminal && (
            <div className="flex flex-wrap gap-2 mt-4 pt-3 border-t border-gray-100 dark:border-slate-700">
              {issue.status === 'open' && (
                <button
                  onClick={onAcknowledge}
                  disabled={isMutating}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:hover:bg-amber-900/50 transition-colors disabled:opacity-50"
                >
                  <Eye className="w-3.5 h-3.5" />
                  {t('unknown_issue.acknowledge')}
                </button>
              )}

              {(issue.status === 'open' || issue.status === 'acknowledged') && (
                <>
                  {!showResolveForm ? (
                    <button
                      onClick={() => {
                        setShowResolveForm(true);
                        setShowDismissForm(false);
                      }}
                      disabled={isMutating}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50 transition-colors disabled:opacity-50"
                    >
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      {t('unknown_issue.resolve')}
                    </button>
                  ) : (
                    <div className="flex items-end gap-2 w-full">
                      <div className="flex-1">
                        <label className="text-xs text-gray-500 dark:text-slate-400 mb-1 block">
                          {t('unknown_issue.resolution_notes')}
                        </label>
                        <input
                          type="text"
                          value={resolveNotes}
                          onChange={(e) => setResolveNotes(e.target.value)}
                          placeholder={t('unknown_issue.resolution_notes_placeholder')}
                          className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                        />
                      </div>
                      <button
                        onClick={() => {
                          onResolve(resolveNotes);
                          setResolveNotes('');
                          setShowResolveForm(false);
                        }}
                        disabled={isMutating}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 transition-colors disabled:opacity-50"
                      >
                        {t('common.confirm')}
                      </button>
                      <button
                        onClick={() => setShowResolveForm(false)}
                        className="px-2 py-1.5 text-xs text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}

                  {!showDismissForm ? (
                    <button
                      onClick={() => {
                        setShowDismissForm(true);
                        setShowResolveForm(false);
                      }}
                      disabled={isMutating}
                      className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-slate-700 dark:text-slate-400 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
                    >
                      <XCircle className="w-3.5 h-3.5" />
                      {t('unknown_issue.dismiss')}
                    </button>
                  ) : (
                    <div className="flex items-end gap-2 w-full">
                      <div className="flex-1">
                        <label className="text-xs text-gray-500 dark:text-slate-400 mb-1 block">
                          {t('unknown_issue.dismiss_reason')}
                        </label>
                        <input
                          type="text"
                          value={dismissReason}
                          onChange={(e) => setDismissReason(e.target.value)}
                          placeholder={t('unknown_issue.dismiss_reason_placeholder')}
                          className="w-full px-3 py-1.5 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                        />
                      </div>
                      <button
                        onClick={() => {
                          onDismiss(dismissReason);
                          setDismissReason('');
                          setShowDismissForm(false);
                        }}
                        disabled={isMutating || !dismissReason.trim()}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-purple-600 text-white hover:bg-purple-700 transition-colors disabled:opacity-50"
                      >
                        {t('common.confirm')}
                      </button>
                      <button
                        onClick={() => setShowDismissForm(false)}
                        className="px-2 py-1.5 text-xs text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  )}
                </>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ---------- Main Panel ---------- */

interface UnknownIssuesPanelProps {
  buildingId: string;
  onClose?: () => void;
}

export function UnknownIssuesPanel({ buildingId, onClose }: UnknownIssuesPanelProps) {
  const { t } = useTranslation();
  const { user } = useAuth();
  const queryClient = useQueryClient();

  // Filters
  const [filterStatus, setFilterStatus] = useState<UnknownStatus | ''>('');
  const [filterSeverity, setFilterSeverity] = useState<UnknownSeverity | ''>('');
  const [filterCategory, setFilterCategory] = useState<UnknownType | ''>('');
  const [showFilters, setShowFilters] = useState(false);

  // Sort
  const [sortField, setSortField] = useState<SortField>('severity');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  // Expansion & selection
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Fetch all issues (no server-side filter for full stats)
  const {
    data: allData,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-unknowns-all', buildingId],
    queryFn: () => unknownsApi.list(buildingId, { size: 100 }),
    enabled: !!buildingId,
  });

  const allIssues = allData?.items ?? [];

  // Mutation
  const updateMutation = useMutation({
    mutationFn: ({ issueId, data }: { issueId: string; data: UnknownIssueUpdatePayload }) =>
      unknownsApi.update(buildingId, issueId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-unknowns-all', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['building-unknowns', buildingId] });
      toast(t('unknown_issue.update_success'), 'success');
    },
    onError: () => {
      toast(t('unknown_issue.update_error'), 'error');
    },
  });

  // Stats
  const stats = useMemo(() => {
    const total = allIssues.length;
    const byStatus: Record<string, number> = {};
    const bySeverity: Record<string, number> = {};
    const byCategory: Record<string, number> = {};
    let resolvedCount = 0;
    let autoResolvedCount = 0;
    let manualResolvedCount = 0;

    for (const issue of allIssues) {
      byStatus[issue.status] = (byStatus[issue.status] || 0) + 1;
      bySeverity[issue.severity] = (bySeverity[issue.severity] || 0) + 1;
      byCategory[issue.unknown_type] = (byCategory[issue.unknown_type] || 0) + 1;
      if (issue.status === 'resolved' || issue.status === 'accepted_risk') {
        resolvedCount++;
        if (issue.detected_by === 'system' && issue.status === 'resolved') {
          autoResolvedCount++;
        } else {
          manualResolvedCount++;
        }
      }
    }

    const resolutionRate = total > 0 ? Math.round((resolvedCount / total) * 100) : 0;

    return {
      total,
      byStatus,
      bySeverity,
      byCategory,
      resolvedCount,
      autoResolvedCount,
      manualResolvedCount,
      resolutionRate,
    };
  }, [allIssues]);

  // Filter + sort
  const filteredIssues = useMemo(() => {
    let result = [...allIssues];

    if (filterStatus) result = result.filter((i) => i.status === filterStatus);
    if (filterSeverity) result = result.filter((i) => i.severity === filterSeverity);
    if (filterCategory) result = result.filter((i) => i.unknown_type === filterCategory);

    result.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'severity':
          cmp = (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9);
          break;
        case 'created_at':
          cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
          break;
        case 'unknown_type':
          cmp = a.unknown_type.localeCompare(b.unknown_type);
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });

    return result;
  }, [allIssues, filterStatus, filterSeverity, filterCategory, sortField, sortDir]);

  // Handlers
  const handleAcknowledge = useCallback(
    (issueId: string) => {
      updateMutation.mutate({ issueId, data: { status: 'acknowledged' } });
    },
    [updateMutation],
  );

  const handleResolve = useCallback(
    (issueId: string, notes: string) => {
      updateMutation.mutate({
        issueId,
        data: {
          status: 'resolved',
          resolution_notes: notes || undefined,
          resolved_by: user?.id,
          resolved_at: new Date().toISOString(),
        },
      });
    },
    [updateMutation, user],
  );

  const handleDismiss = useCallback(
    (issueId: string, reason: string) => {
      updateMutation.mutate({
        issueId,
        data: {
          status: 'accepted_risk',
          resolution_notes: reason,
          resolved_by: user?.id,
          resolved_at: new Date().toISOString(),
        },
      });
    },
    [updateMutation, user],
  );

  const handleBulkAcknowledge = useCallback(() => {
    const openIds = [...selectedIds].filter((id) => {
      const issue = allIssues.find((i) => i.id === id);
      return issue && issue.status === 'open';
    });
    for (const id of openIds) {
      updateMutation.mutate({ issueId: id, data: { status: 'acknowledged' } });
    }
    setSelectedIds(new Set());
  }, [selectedIds, allIssues, updateMutation]);

  const handleBulkResolve = useCallback(() => {
    const actionableIds = [...selectedIds].filter((id) => {
      const issue = allIssues.find((i) => i.id === id);
      return issue && (issue.status === 'open' || issue.status === 'acknowledged');
    });
    for (const id of actionableIds) {
      updateMutation.mutate({
        issueId: id,
        data: {
          status: 'resolved',
          resolved_by: user?.id,
          resolved_at: new Date().toISOString(),
        },
      });
    }
    setSelectedIds(new Set());
  }, [selectedIds, allIssues, updateMutation, user]);

  const toggleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortField(field);
        setSortDir('asc');
      }
    },
    [sortField],
  );

  const toggleSelect = useCallback((id: string, checked: boolean) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (checked) next.add(id);
      else next.delete(id);
      return next;
    });
  }, []);

  // Active categories for the chart
  const activeCategories = useMemo(() => {
    return UNKNOWN_TYPES.filter((t) => (stats.byCategory[t] ?? 0) > 0).sort(
      (a, b) => (stats.byCategory[b] ?? 0) - (stats.byCategory[a] ?? 0),
    );
  }, [stats.byCategory]);

  const openCount = (stats.byStatus['open'] ?? 0) + (stats.byStatus['acknowledged'] ?? 0);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-12">
        <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center justify-center p-12 text-red-500">
        <AlertTriangle className="w-5 h-5 mr-2" />
        {t('error.unknown')}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <HelpCircle className="w-6 h-6 text-gray-500 dark:text-slate-400" />
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">{t('unknown_issue.panel_title')}</h2>
          <span className="px-2 py-0.5 text-xs font-medium bg-yellow-100 dark:bg-yellow-900/30 text-yellow-700 dark:text-yellow-300 rounded-full">
            {openCount} {t('unknown_issue.open_label')}
          </span>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-slate-400"
          >
            <X className="w-5 h-5" />
          </button>
        )}
      </div>

      {/* Summary cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <SummaryCard
          label={t('unknown_issue.total_issues')}
          value={stats.total}
          icon={<HelpCircle className="w-5 h-5 text-gray-500 dark:text-slate-400" />}
        />
        <SummaryCard
          label={t('unknown_issue.open_issues')}
          value={openCount}
          icon={<ShieldAlert className="w-5 h-5 text-blue-500" />}
        />
        <SummaryCard
          label={t('unknown_issue.critical_high')}
          value={(stats.bySeverity['critical'] ?? 0) + (stats.bySeverity['high'] ?? 0)}
          icon={<AlertTriangle className="w-5 h-5 text-red-500" />}
        />
        <SummaryCard
          label={t('unknown_issue.resolution_rate')}
          value={`${stats.resolutionRate}%`}
          icon={<CheckCircle2 className="w-5 h-5 text-green-500" />}
        />
      </div>

      {/* Category breakdown + severity chart */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Category breakdown */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4">
          <div className="flex items-center gap-2 mb-3">
            <BarChart3 className="w-4 h-4 text-gray-500 dark:text-slate-400" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              {t('unknown_issue.category_breakdown')}
            </h3>
          </div>
          <div className="space-y-2">
            {activeCategories.map((cat) => (
              <CategoryBar key={cat} type={cat} count={stats.byCategory[cat] ?? 0} total={stats.total} />
            ))}
            {activeCategories.length === 0 && (
              <p className="text-sm text-gray-500 dark:text-slate-400">{t('unknown_issue.none')}</p>
            )}
          </div>
        </div>

        {/* Resolution info */}
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4">
          <div className="flex items-center gap-2 mb-3">
            <CheckCircle2 className="w-4 h-4 text-gray-500 dark:text-slate-400" />
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
              {t('unknown_issue.resolution_overview')}
            </h3>
          </div>
          <div className="space-y-3">
            {/* Resolution progress bar */}
            <div>
              <div className="flex justify-between text-xs text-gray-500 dark:text-slate-400 mb-1">
                <span>
                  {t('unknown_issue.resolved_count')}: {stats.resolvedCount}/{stats.total}
                </span>
                <span>{stats.resolutionRate}%</span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-3">
                <div
                  className="bg-green-500 h-3 rounded-full transition-all"
                  style={{ width: `${stats.resolutionRate}%` }}
                />
              </div>
            </div>

            {/* Auto vs manual */}
            <div className="flex gap-4 mt-3">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-blue-500" />
                <div>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">{stats.autoResolvedCount}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">{t('unknown_issue.auto_resolved')}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <User className="w-4 h-4 text-green-500" />
                <div>
                  <p className="text-lg font-bold text-gray-900 dark:text-white">{stats.manualResolvedCount}</p>
                  <p className="text-xs text-gray-500 dark:text-slate-400">{t('unknown_issue.manually_resolved')}</p>
                </div>
              </div>
            </div>

            {/* Severity mini-bars */}
            <div className="mt-3 space-y-1.5">
              {(['critical', 'high', 'medium', 'low'] as UnknownSeverity[]).map((sev) => {
                const count = stats.bySeverity[sev] ?? 0;
                if (count === 0) return null;
                const color = SEVERITY_COLORS[sev];
                return (
                  <div key={sev} className="flex items-center gap-2 text-xs">
                    <span className={cn('w-2 h-2 rounded-full', color.dot)} />
                    <span className="w-16 text-gray-600 dark:text-slate-400 capitalize">
                      {t(`unknown_issue.severity_${sev}`) || sev}
                    </span>
                    <div className="flex-1 bg-gray-200 dark:bg-slate-700 rounded-full h-1.5">
                      <div
                        className={cn('h-1.5 rounded-full', color.dot)}
                        style={{ width: `${stats.total > 0 ? (count / stats.total) * 100 : 0}%` }}
                      />
                    </div>
                    <span className="w-4 text-right text-gray-500 dark:text-slate-400">{count}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* Filter & sort bar */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={cn(
            'inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors',
            showFilters
              ? 'bg-red-50 border-red-200 text-red-700 dark:bg-red-900/20 dark:border-red-800 dark:text-red-400'
              : 'bg-white border-gray-200 text-gray-600 hover:bg-gray-50 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-300 dark:hover:bg-slate-700',
          )}
        >
          <Filter className="w-3.5 h-3.5" />
          {t('unknown_issue.filters')}
        </button>

        {/* Sort buttons */}
        {(['severity', 'created_at', 'unknown_type'] as SortField[]).map((field) => (
          <button
            key={field}
            onClick={() => toggleSort(field)}
            className={cn(
              'inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors',
              sortField === field
                ? 'bg-gray-200 border-gray-300 text-gray-800 dark:bg-slate-600 dark:border-slate-500 dark:text-white'
                : 'bg-white border-gray-200 text-gray-500 hover:bg-gray-50 dark:bg-slate-800 dark:border-slate-700 dark:text-slate-400 dark:hover:bg-slate-700',
            )}
          >
            <ArrowUpDown className="w-3 h-3" />
            {t(`unknown_issue.sort_${field}`)}
            {sortField === field && <span className="text-[10px]">{sortDir === 'asc' ? '\u2191' : '\u2193'}</span>}
          </button>
        ))}

        {/* Bulk actions */}
        {selectedIds.size > 0 && (
          <div className="flex items-center gap-2 ml-auto">
            <span className="text-xs text-gray-500 dark:text-slate-400">
              {selectedIds.size} {t('unknown_issue.selected')}
            </span>
            <button
              onClick={handleBulkAcknowledge}
              disabled={updateMutation.isPending}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-400 transition-colors disabled:opacity-50"
            >
              <Eye className="w-3 h-3" />
              {t('unknown_issue.bulk_acknowledge')}
            </button>
            <button
              onClick={handleBulkResolve}
              disabled={updateMutation.isPending}
              className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium rounded-lg bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 transition-colors disabled:opacity-50"
            >
              <CheckCircle2 className="w-3 h-3" />
              {t('unknown_issue.bulk_resolve')}
            </button>
          </div>
        )}
      </div>

      {/* Filter dropdowns */}
      {showFilters && (
        <div className="flex flex-wrap gap-3 p-3 bg-gray-50 dark:bg-slate-800/50 rounded-lg border border-gray-200 dark:border-slate-700">
          <div>
            <label className="text-xs text-gray-500 dark:text-slate-400 mb-1 block">
              {t('unknown_issue.filter_status')}
            </label>
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as UnknownStatus | '')}
              className="px-2 py-1 text-xs border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            >
              <option value="">{t('common.all')}</option>
              {(['open', 'acknowledged', 'resolved', 'accepted_risk'] as UnknownStatus[]).map((s) => (
                <option key={s} value={s}>
                  {t(`unknown_issue.status_${s}`) || s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 dark:text-slate-400 mb-1 block">
              {t('unknown_issue.filter_severity')}
            </label>
            <select
              value={filterSeverity}
              onChange={(e) => setFilterSeverity(e.target.value as UnknownSeverity | '')}
              className="px-2 py-1 text-xs border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            >
              <option value="">{t('common.all')}</option>
              {(['critical', 'high', 'medium', 'low'] as UnknownSeverity[]).map((s) => (
                <option key={s} value={s}>
                  {t(`unknown_issue.severity_${s}`) || s}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-xs text-gray-500 dark:text-slate-400 mb-1 block">
              {t('unknown_issue.filter_category')}
            </label>
            <select
              value={filterCategory}
              onChange={(e) => setFilterCategory(e.target.value as UnknownType | '')}
              className="px-2 py-1 text-xs border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            >
              <option value="">{t('common.all')}</option>
              {UNKNOWN_TYPES.map((cat) => (
                <option key={cat} value={cat}>
                  {t(`unknown_issue.type_${cat}`) || cat.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
          </div>
          {(filterStatus || filterSeverity || filterCategory) && (
            <button
              onClick={() => {
                setFilterStatus('');
                setFilterSeverity('');
                setFilterCategory('');
              }}
              className="self-end px-2 py-1 text-xs text-red-600 hover:text-red-700 dark:text-red-400"
            >
              {t('unknown_issue.clear_filters')}
            </button>
          )}
        </div>
      )}

      {/* Issues list */}
      <div className="space-y-2">
        {filteredIssues.length === 0 ? (
          <div className="text-center py-8 text-gray-500 dark:text-slate-400">
            <HelpCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">
              {filterStatus || filterSeverity || filterCategory
                ? t('unknown_issue.no_matches')
                : t('unknown_issue.none')}
            </p>
          </div>
        ) : (
          filteredIssues.map((issue) => (
            <IssueRow
              key={issue.id}
              issue={issue}
              isExpanded={expandedId === issue.id}
              isSelected={selectedIds.has(issue.id)}
              onToggle={() => setExpandedId(expandedId === issue.id ? null : issue.id)}
              onSelect={(checked) => toggleSelect(issue.id, checked)}
              onAcknowledge={() => handleAcknowledge(issue.id)}
              onResolve={(notes) => handleResolve(issue.id, notes)}
              onDismiss={(reason) => handleDismiss(issue.id, reason)}
              isMutating={updateMutation.isPending}
            />
          ))
        )}
      </div>

      {/* Footer count */}
      {filteredIssues.length > 0 && (
        <p className="text-xs text-gray-500 dark:text-slate-400 text-center">
          {t('unknown_issue.showing_count', { count: String(filteredIssues.length), total: String(stats.total) }) ||
            `${filteredIssues.length} / ${stats.total} issues`}
        </p>
      )}
    </div>
  );
}
