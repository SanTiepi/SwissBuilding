/**
 * MIGRATION: ABSORB INTO Today
 * This page will be absorbed into the Today master workspace as an actions panel.
 * Per ADR-005 and V3 migration plan.
 * New features should target the master workspace directly.
 */
import { useState, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { actionsApi } from '@/api/actions';
import { buildingsApi } from '@/api/buildings';
import { campaignsApi } from '@/api/campaigns';
import type { ActionItem, ActionPriority, ActionStatus, ActionSourceType, Building, Campaign } from '@/types';
import {
  Loader2,
  Plus,
  CheckCircle2,
  XCircle,
  Building2,
  Calendar,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  X,
  Megaphone,
  ArrowUpDown,
  CheckSquare,
  Square,
  Minus,
  Clock,
  Play,
  Ban,
} from 'lucide-react';
import { cn } from '@/utils/formatters';

// ─── Constants ───────────────────────────────────────────────────────────────

const STATUSES: ActionStatus[] = ['open', 'in_progress', 'blocked', 'done', 'dismissed'];
const PRIORITIES: ActionPriority[] = ['low', 'medium', 'high', 'critical'];
const SOURCE_TYPES: ActionSourceType[] = [
  'risk',
  'diagnostic',
  'document',
  'compliance',
  'simulation',
  'manual',
  'system',
];

const PRIORITY_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };
const STATUS_ORDER: Record<string, number> = { open: 0, in_progress: 1, blocked: 2, done: 3, dismissed: 4 };

type SortField = 'created_at' | 'priority' | 'due_date' | 'status';
type SortDir = 'asc' | 'desc';

const priorityColors: Record<string, string> = {
  low: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  medium: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  high: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  critical: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const statusColors: Record<string, string> = {
  open: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  in_progress: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  blocked: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  done: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  dismissed: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
};

const sourceColors: Record<string, string> = {
  risk: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  diagnostic: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  document: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  compliance: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  simulation: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  manual: 'bg-slate-100 text-slate-700 dark:bg-slate-900/30 dark:text-slate-400',
  system: 'bg-gray-100 text-gray-700 dark:bg-gray-900/30 dark:text-gray-400',
};

const statusIconMap: Record<string, React.ElementType> = {
  open: Clock,
  in_progress: Play,
  blocked: Ban,
  done: CheckCircle2,
  dismissed: XCircle,
};

// ─── Helpers ─────────────────────────────────────────────────────────────────

function formatDate(dateStr: string | null): string | null {
  if (!dateStr) return null;
  try {
    return new Date(dateStr).toLocaleDateString();
  } catch {
    return dateStr;
  }
}

function isOverdue(dateStr: string | null): boolean {
  if (!dateStr) return false;
  try {
    return new Date(dateStr) < new Date();
  } catch {
    return false;
  }
}

// ─── Summary Bar ─────────────────────────────────────────────────────────────

function SummaryBar({ actions, t }: { actions: ActionItem[]; t: (k: string) => string }) {
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const s of STATUSES) counts[s] = 0;
    for (const a of actions) counts[a.status] = (counts[a.status] || 0) + 1;
    return counts;
  }, [actions]);

  const priorityCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const p of PRIORITIES) counts[p] = 0;
    for (const a of actions) counts[a.priority] = (counts[a.priority] || 0) + 1;
    return counts;
  }, [actions]);

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
      <h2 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-3">
        {t('action.summary_bar')}
      </h2>
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-9 gap-2">
        {STATUSES.map((s) => {
          const Icon = statusIconMap[s] || Clock;
          return (
            <div
              key={s}
              className={cn('flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium', statusColors[s])}
            >
              <Icon className="w-3.5 h-3.5 flex-shrink-0" />
              <span className="truncate">{t(`action_status.${s}`) || s}</span>
              <span className="ml-auto font-bold">{statusCounts[s]}</span>
            </div>
          );
        })}
        <div className="hidden lg:block w-px bg-gray-200 dark:bg-slate-600" />
        {PRIORITIES.map((p) => (
          <div
            key={p}
            className={cn('flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium', priorityColors[p])}
          >
            <span className="truncate">{t(`action_priority.${p}`) || p}</span>
            <span className="ml-auto font-bold">{priorityCounts[p]}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Create Modal ────────────────────────────────────────────────────────────

interface CreateModalProps {
  open: boolean;
  onClose: () => void;
  buildings: Building[];
  campaigns: Campaign[];
  onSubmit: (data: {
    building_id: string;
    title: string;
    description: string;
    priority: ActionPriority;
    campaign_id?: string;
  }) => void;
  isPending: boolean;
  t: (k: string) => string;
}

function CreateModal({ open, onClose, buildings, campaigns, onSubmit, isPending, t }: CreateModalProps) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [priority, setPriority] = useState<ActionPriority>('medium');
  const [buildingId, setBuildingId] = useState('');
  const [campaignId, setCampaignId] = useState('');

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!buildingId || !title.trim()) return;
    onSubmit({
      building_id: buildingId,
      title: title.trim(),
      description: description.trim(),
      priority,
      campaign_id: campaignId || undefined,
    });
    setTitle('');
    setDescription('');
    setPriority('medium');
    setBuildingId('');
    setCampaignId('');
  };

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-xl w-full max-w-lg mx-4 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 dark:border-slate-700">
          <h2 className="text-base font-semibold text-gray-900 dark:text-white">{t('action.create_manual')}</h2>
          <button
            onClick={onClose}
            aria-label={t('form.close') || 'Close'}
            className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              {t('action.title_label')} *
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              {t('action.description_label')}
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white resize-none"
            />
          </div>

          {/* Building selector */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              {t('action.select_building')} *
            </label>
            <select
              required
              value={buildingId}
              onChange={(e) => setBuildingId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            >
              <option value="">{t('action.select_building')}</option>
              {buildings.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.address}, {b.city}
                </option>
              ))}
            </select>
          </div>

          {/* Priority */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              {t('action.select_priority')}
            </label>
            <select
              value={priority}
              onChange={(e) => setPriority(e.target.value as ActionPriority)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            >
              {PRIORITIES.map((p) => (
                <option key={p} value={p}>
                  {t(`action_priority.${p}`) || p}
                </option>
              ))}
            </select>
          </div>

          {/* Campaign (optional) */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
              {t('action.optional_campaign')}
            </label>
            <select
              value={campaignId}
              onChange={(e) => setCampaignId(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
            >
              <option value="">{t('action.no_campaign')}</option>
              {campaigns.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.title}
                </option>
              ))}
            </select>
          </div>

          {/* Buttons */}
          <div className="flex items-center justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-300 bg-gray-100 dark:bg-slate-700 rounded-lg hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
            >
              {t('action.form_cancel')}
            </button>
            <button
              type="submit"
              disabled={isPending || !buildingId || !title.trim()}
              className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isPending && <Loader2 className="w-4 h-4 animate-spin" />}
              {t('action.form_submit')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ─── Action Row ──────────────────────────────────────────────────────────────

interface ActionRowProps {
  action: ActionItem;
  isSelected: boolean;
  isExpanded: boolean;
  onToggleSelect: () => void;
  onToggleExpand: () => void;
  onStatusChange: (status: ActionStatus) => void;
  onPriorityChange: (priority: ActionPriority) => void;
  buildingMap: Map<string, Building>;
  campaignMap: Map<string, Campaign>;
  isPending: boolean;
  t: (k: string) => string;
}

function ActionRow({
  action,
  isSelected,
  isExpanded,
  onToggleSelect,
  onToggleExpand,
  onStatusChange,
  onPriorityChange,
  buildingMap,
  campaignMap,
  isPending,
  t,
}: ActionRowProps) {
  const building = buildingMap.get(action.building_id);
  const campaign = action.campaign_id ? campaignMap.get(action.campaign_id) : null;
  const overdue = isOverdue(action.due_date) && action.status !== 'done' && action.status !== 'dismissed';
  const isTerminal = action.status === 'done' || action.status === 'dismissed';

  return (
    <div
      className={cn(
        'bg-white dark:bg-slate-800 border rounded-xl shadow-sm transition-all',
        isSelected
          ? 'border-red-300 dark:border-red-700 ring-1 ring-red-200 dark:ring-red-800'
          : 'border-gray-200 dark:border-slate-700',
        isExpanded ? 'shadow-md' : 'hover:shadow-md',
      )}
    >
      {/* Main row */}
      <div className="flex items-start gap-3 p-4">
        {/* Checkbox */}
        <button
          onClick={onToggleSelect}
          className="mt-0.5 flex-shrink-0 text-gray-400 hover:text-red-500 dark:text-slate-500 dark:hover:text-red-400 transition-colors"
          aria-label={isSelected ? t('action.deselect_all') : t('action.select_all')}
        >
          {isSelected ? (
            <CheckSquare className="w-5 h-5 text-red-500 dark:text-red-400" />
          ) : (
            <Square className="w-5 h-5" />
          )}
        </button>

        {/* Content */}
        <div className="flex-1 min-w-0 space-y-2">
          {/* Badges row */}
          <div className="flex flex-wrap items-center gap-1.5">
            <span
              className={cn(
                'px-2 py-0.5 text-xs font-medium rounded-full',
                priorityColors[action.priority] || priorityColors.medium,
              )}
            >
              {t(`action_priority.${action.priority}`) || action.priority}
            </span>
            <span
              className={cn(
                'px-2 py-0.5 text-xs font-medium rounded-full',
                statusColors[action.status] || statusColors.open,
              )}
            >
              {t(`action_status.${action.status}`) || action.status}
            </span>
            <span
              className={cn(
                'px-2 py-0.5 text-xs font-medium rounded-full',
                sourceColors[action.source_type] || sourceColors.system,
              )}
            >
              {t(`action_source.${action.source_type}`) || action.source_type}
            </span>
            {campaign && (
              <Link
                to={`/campaigns`}
                className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400 hover:bg-violet-200 dark:hover:bg-violet-900/50 transition-colors"
              >
                <Megaphone className="w-3 h-3" />
                {campaign.title}
              </Link>
            )}
            {overdue && (
              <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs font-bold rounded-full bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                <AlertTriangle className="w-3 h-3" />
                {t('action.overdue')}
              </span>
            )}
          </div>

          {/* Title */}
          <button onClick={onToggleExpand} className="text-left w-full">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white hover:text-red-600 dark:hover:text-red-400 transition-colors">
              {action.title}
            </h3>
          </button>

          {/* Meta row */}
          <div className="flex flex-wrap items-center gap-3 text-xs text-gray-500 dark:text-slate-400">
            {building ? (
              <Link
                to={`/buildings/${action.building_id}`}
                className="inline-flex items-center gap-1 hover:text-red-600 dark:hover:text-red-400 transition-colors"
              >
                <Building2 className="w-3.5 h-3.5" />
                <span className="truncate max-w-[180px]">
                  {building.address}, {building.city}
                </span>
              </Link>
            ) : action.building_id ? (
              <Link
                to={`/buildings/${action.building_id}`}
                className="inline-flex items-center gap-1 hover:text-red-600 dark:hover:text-red-400 transition-colors"
              >
                <Building2 className="w-3.5 h-3.5" />
                <span>{t('action.source')}</span>
              </Link>
            ) : null}
            {action.due_date && (
              <span
                className={cn(
                  'inline-flex items-center gap-1',
                  overdue ? 'text-red-600 dark:text-red-400 font-medium' : '',
                )}
              >
                <Calendar className="w-3.5 h-3.5" />
                {formatDate(action.due_date)}
              </span>
            )}
            <span className="inline-flex items-center gap-1">
              <Clock className="w-3.5 h-3.5" />
              {formatDate(action.created_at)}
            </span>
          </div>
        </div>

        {/* Right: quick actions */}
        <div className="flex items-center gap-2 flex-shrink-0">
          {!isTerminal && (
            <>
              <button
                onClick={() => onStatusChange('done')}
                disabled={isPending}
                title={t('action.mark_done')}
                aria-label={t('action.mark_done')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/40 transition-colors disabled:opacity-50"
              >
                <CheckCircle2 className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{t('action.mark_done')}</span>
              </button>
              <button
                onClick={() => onStatusChange('dismissed')}
                disabled={isPending}
                title={t('action.dismiss')}
                aria-label={t('action.dismiss')}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-slate-400 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
              >
                <XCircle className="w-3.5 h-3.5" />
                <span className="hidden sm:inline">{t('action.dismiss')}</span>
              </button>
            </>
          )}
          <button
            onClick={onToggleExpand}
            aria-label={isExpanded ? t('form.collapse') || 'Collapse' : t('form.expand') || 'Expand'}
            aria-expanded={isExpanded}
            className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 transition-colors"
          >
            {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Expanded detail panel */}
      {isExpanded && (
        <div className="border-t border-gray-100 dark:border-slate-700 px-4 py-4 bg-gray-50/50 dark:bg-slate-800/50 rounded-b-xl space-y-4">
          {/* Description */}
          {action.description && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                {t('action.description_label')}
              </h4>
              <p className="text-sm text-gray-700 dark:text-slate-300">{action.description}</p>
            </div>
          )}

          {/* Status + Priority editors */}
          <div className="flex flex-wrap gap-4">
            <div>
              <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                {t('action.change_status')}
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {STATUSES.map((s) => (
                  <button
                    key={s}
                    onClick={() => onStatusChange(s)}
                    disabled={isPending || action.status === s}
                    className={cn(
                      'px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors disabled:opacity-40',
                      action.status === s
                        ? 'ring-2 ring-red-300 dark:ring-red-700 border-transparent ' + statusColors[s]
                        : 'border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700',
                    )}
                  >
                    {t(`action_status.${s}`) || s}
                  </button>
                ))}
              </div>
            </div>
            <div>
              <h4 className="text-xs font-semibold text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
                {t('action.change_priority')}
              </h4>
              <div className="flex flex-wrap gap-1.5">
                {PRIORITIES.map((p) => (
                  <button
                    key={p}
                    onClick={() => onPriorityChange(p)}
                    disabled={isPending || action.priority === p}
                    className={cn(
                      'px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors disabled:opacity-40',
                      action.priority === p
                        ? 'ring-2 ring-red-300 dark:ring-red-700 border-transparent ' + priorityColors[p]
                        : 'border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700',
                    )}
                  >
                    {t(`action_priority.${p}`) || p}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────────────────────

export default function Actions() {
  const { t } = useTranslation();
  const { user } = useAuthStore();
  const queryClient = useQueryClient();

  // ── Filters ──
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [priorityFilter, setPriorityFilter] = useState<string>('');
  const [sourceFilter, setSourceFilter] = useState<string>('');
  const [buildingFilter, setBuildingFilter] = useState<string>('');
  const [assignedToMe, setAssignedToMe] = useState(false);

  // ── Sort ──
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  // ── Selection ──
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // ── Expand ──
  const [expandedId, setExpandedId] = useState<string | null>(null);

  // ── Create modal ──
  const [createOpen, setCreateOpen] = useState(false);

  // ── Data queries ──
  const {
    data: actions = [],
    isLoading,
    error,
  } = useQuery({
    queryKey: ['actions', statusFilter, priorityFilter, assignedToMe],
    queryFn: () =>
      actionsApi.list({
        status: statusFilter || undefined,
        priority: priorityFilter || undefined,
        assigned_to: assignedToMe ? user?.id : undefined,
      }),
  });

  const { data: buildingsPage } = useQuery({
    queryKey: ['buildings-all'],
    queryFn: () => buildingsApi.list({ size: 200 }),
    staleTime: 5 * 60 * 1000,
  });
  const buildings = useMemo(() => buildingsPage?.items ?? [], [buildingsPage]);

  const { data: campaignsPage } = useQuery({
    queryKey: ['campaigns-all'],
    queryFn: () => campaignsApi.list({ size: 200 }),
    staleTime: 5 * 60 * 1000,
  });
  const campaigns = useMemo(() => campaignsPage?.items ?? [], [campaignsPage]);

  // ── Maps for fast lookup ──
  const buildingMap = useMemo(() => {
    const m = new Map<string, Building>();
    for (const b of buildings) m.set(b.id, b);
    return m;
  }, [buildings]);

  const campaignMap = useMemo(() => {
    const m = new Map<string, Campaign>();
    for (const c of campaigns) m.set(c.id, c);
    return m;
  }, [campaigns]);

  // ── Derived: unique building IDs that appear in actions ──
  const actionBuildingIds = useMemo(() => {
    const ids = new Set<string>();
    for (const a of actions) {
      if (a.building_id) ids.add(a.building_id);
    }
    return ids;
  }, [actions]);

  // ── Client-side filtering + sorting ──
  const filteredActions = useMemo(() => {
    let list = actions;
    if (sourceFilter) list = list.filter((a) => a.source_type === sourceFilter);
    if (buildingFilter) list = list.filter((a) => a.building_id === buildingFilter);

    // Sort
    list = [...list].sort((a, b) => {
      const cmp = (() => {
        switch (sortField) {
          case 'priority':
            return (PRIORITY_ORDER[a.priority] ?? 99) - (PRIORITY_ORDER[b.priority] ?? 99);
          case 'status':
            return (STATUS_ORDER[a.status] ?? 99) - (STATUS_ORDER[b.status] ?? 99);
          case 'due_date': {
            const da = a.due_date ? new Date(a.due_date).getTime() : Infinity;
            const db = b.due_date ? new Date(b.due_date).getTime() : Infinity;
            return da - db;
          }
          case 'created_at':
          default:
            return new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
        }
      })();
      return sortDir === 'desc' ? -cmp : cmp;
    });
    return list;
  }, [actions, sourceFilter, buildingFilter, sortField, sortDir]);

  // ── Mutations ──
  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: string; data: Partial<ActionItem> }) => actionsApi.update(id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] });
    },
  });

  const createMutation = useMutation({
    mutationFn: (data: {
      building_id: string;
      title: string;
      description: string;
      priority: ActionPriority;
      campaign_id?: string;
    }) => {
      return actionsApi.create(data.building_id, {
        title: data.title,
        description: data.description,
        priority: data.priority,
        source_type: 'manual',
        action_type: 'manual',
        status: 'open',
        campaign_id: data.campaign_id ?? null,
      } as Partial<ActionItem>);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] });
      setCreateOpen(false);
    },
  });

  // ── Bulk mutation ──
  const bulkUpdateMutation = useMutation({
    mutationFn: async ({ ids, data }: { ids: string[]; data: Partial<ActionItem> }) => {
      await Promise.all(ids.map((id) => actionsApi.update(id, data)));
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['actions'] });
      setSelectedIds(new Set());
    },
  });

  // ── Handlers ──
  const handleToggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    const activeIds = filteredActions.filter((a) => a.status !== 'done' && a.status !== 'dismissed').map((a) => a.id);
    setSelectedIds((prev) => {
      if (prev.size === activeIds.length && activeIds.every((id) => prev.has(id))) {
        return new Set();
      }
      return new Set(activeIds);
    });
  }, [filteredActions]);

  const handleBulkAction = useCallback(
    (status: ActionStatus) => {
      const ids = Array.from(selectedIds);
      if (ids.length === 0) return;
      bulkUpdateMutation.mutate({ ids, data: { status } });
    },
    [selectedIds, bulkUpdateMutation],
  );

  const handleToggleSort = useCallback(
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

  const hasActiveFilters = statusFilter || priorityFilter || sourceFilter || buildingFilter || assignedToMe;

  const clearFilters = () => {
    setStatusFilter('');
    setPriorityFilter('');
    setSourceFilter('');
    setBuildingFilter('');
    setAssignedToMe(false);
  };

  const selectCls =
    'px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-red-500 bg-white dark:bg-slate-700 text-gray-900 dark:text-white min-w-0';

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('action.title')}</h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {filteredActions.length} {t('action.title').toLowerCase()}
          </p>
        </div>
        <button
          onClick={() => setCreateOpen(true)}
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
        >
          <Plus className="w-4 h-4" />
          {t('action.create')}
        </button>
      </div>

      {/* Summary Bar */}
      {!isLoading && !error && actions.length > 0 && <SummaryBar actions={actions} t={t} />}

      {/* Filter Bar */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 shadow-sm">
        <div className="flex flex-wrap items-center gap-3">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            aria-label={t('action.filter_status')}
            className={cn(selectCls, 'flex-1 sm:flex-none')}
          >
            <option value="">{t('action.all_statuses')}</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {t(`action_status.${s}`) || s}
              </option>
            ))}
          </select>

          <select
            value={priorityFilter}
            onChange={(e) => setPriorityFilter(e.target.value)}
            aria-label={t('action.filter_priority')}
            className={cn(selectCls, 'flex-1 sm:flex-none')}
          >
            <option value="">{t('action.all_priorities')}</option>
            {PRIORITIES.map((p) => (
              <option key={p} value={p}>
                {t(`action_priority.${p}`) || p}
              </option>
            ))}
          </select>

          <select
            value={sourceFilter}
            onChange={(e) => setSourceFilter(e.target.value)}
            aria-label={t('action.filter_source')}
            className={cn(selectCls, 'flex-1 sm:flex-none')}
          >
            <option value="">{t('action.all_sources')}</option>
            {SOURCE_TYPES.map((s) => (
              <option key={s} value={s}>
                {t(`action_source.${s}`) || s}
              </option>
            ))}
          </select>

          <select
            value={buildingFilter}
            onChange={(e) => setBuildingFilter(e.target.value)}
            aria-label={t('action.filter_building')}
            className={cn(selectCls, 'flex-1 sm:flex-none')}
          >
            <option value="">{t('action.all_buildings')}</option>
            {Array.from(actionBuildingIds).map((bid) => {
              const b = buildingMap.get(bid);
              return (
                <option key={bid} value={bid}>
                  {b ? `${b.address}, ${b.city}` : bid.slice(0, 8)}
                </option>
              );
            })}
          </select>

          <label className="inline-flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={assignedToMe}
              onChange={(e) => setAssignedToMe(e.target.checked)}
              className="w-4 h-4 rounded border-gray-300 dark:border-slate-600 text-red-600 focus:ring-red-500 dark:bg-slate-700"
            />
            {t('action.filter_assigned')}
          </label>

          {hasActiveFilters && (
            <button
              onClick={clearFilters}
              className="inline-flex items-center gap-1 px-3 py-2 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
            >
              <X className="w-3.5 h-3.5" />
              {t('action.clear_filters')}
            </button>
          )}
        </div>

        {/* Sort row */}
        <div className="flex flex-wrap items-center gap-2 mt-3 pt-3 border-t border-gray-100 dark:border-slate-700">
          <span className="text-xs font-medium text-gray-500 dark:text-slate-400 flex items-center gap-1">
            <ArrowUpDown className="w-3.5 h-3.5" />
            {t('action.sort_by')}:
          </span>
          {(
            [
              ['created_at', 'action.sort_created'],
              ['priority', 'action.sort_priority'],
              ['due_date', 'action.sort_due_date'],
              ['status', 'action.sort_status'],
            ] as const
          ).map(([field, labelKey]) => (
            <button
              key={field}
              onClick={() => handleToggleSort(field)}
              className={cn(
                'px-2.5 py-1 text-xs font-medium rounded-lg border transition-colors',
                sortField === field
                  ? 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800 text-red-700 dark:text-red-400'
                  : 'border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-400 hover:bg-gray-100 dark:hover:bg-slate-700',
              )}
            >
              {t(labelKey)} {sortField === field && (sortDir === 'asc' ? '\u2191' : '\u2193')}
            </button>
          ))}
        </div>
      </div>

      {/* Bulk actions bar */}
      {selectedIds.size > 0 && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-3 flex flex-wrap items-center gap-3">
          <span className="text-sm font-medium text-red-700 dark:text-red-400">
            {t('action.selected_count').replace('{count}', String(selectedIds.size))}
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleBulkAction('in_progress')}
              disabled={bulkUpdateMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-yellow-700 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg hover:bg-yellow-100 dark:hover:bg-yellow-900/40 transition-colors disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              {t('action.bulk_in_progress')}
            </button>
            <button
              onClick={() => handleBulkAction('done')}
              disabled={bulkUpdateMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-green-700 dark:text-green-400 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/40 transition-colors disabled:opacity-50"
            >
              <CheckCircle2 className="w-3.5 h-3.5" />
              {t('action.bulk_done')}
            </button>
            <button
              onClick={() => handleBulkAction('dismissed')}
              disabled={bulkUpdateMutation.isPending}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-gray-600 dark:text-slate-400 bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-600 transition-colors disabled:opacity-50"
            >
              <XCircle className="w-3.5 h-3.5" />
              {t('action.bulk_dismiss')}
            </button>
          </div>
          <button
            onClick={() => setSelectedIds(new Set())}
            className="ml-auto text-xs text-red-600 dark:text-red-400 hover:underline"
          >
            {t('action.deselect_all')}
          </button>
        </div>
      )}

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
      ) : filteredActions.length === 0 ? (
        <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-12 text-center">
          <CheckCircle2 className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400 text-sm">
            {hasActiveFilters ? t('action.no_actions') : t('action.all_done')}
          </p>
        </div>
      ) : (
        <>
          {/* Select all toggle */}
          <div className="flex items-center gap-2">
            <button
              onClick={handleSelectAll}
              className="inline-flex items-center gap-1.5 text-xs font-medium text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300 transition-colors"
            >
              {selectedIds.size > 0 &&
              filteredActions
                .filter((a) => a.status !== 'done' && a.status !== 'dismissed')
                .every((a) => selectedIds.has(a.id)) ? (
                <Minus className="w-4 h-4" />
              ) : (
                <CheckSquare className="w-4 h-4" />
              )}
              {selectedIds.size > 0 ? t('action.deselect_all') : t('action.select_all')}
            </button>
          </div>

          {/* Action list */}
          <div className="space-y-3">
            {filteredActions.map((action) => (
              <ActionRow
                key={action.id}
                action={action}
                isSelected={selectedIds.has(action.id)}
                isExpanded={expandedId === action.id}
                onToggleSelect={() => handleToggleSelect(action.id)}
                onToggleExpand={() => setExpandedId(expandedId === action.id ? null : action.id)}
                onStatusChange={(status) => updateMutation.mutate({ id: action.id, data: { status } })}
                onPriorityChange={(priority) => updateMutation.mutate({ id: action.id, data: { priority } })}
                buildingMap={buildingMap}
                campaignMap={campaignMap}
                isPending={updateMutation.isPending}
                t={t}
              />
            ))}
          </div>
        </>
      )}

      {/* Create modal */}
      <CreateModal
        open={createOpen}
        onClose={() => setCreateOpen(false)}
        buildings={buildings}
        campaigns={campaigns}
        onSubmit={(data) => createMutation.mutate(data)}
        isPending={createMutation.isPending}
        t={t}
      />
    </div>
  );
}
