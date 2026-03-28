import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { reviewQueueApi } from '@/api/reviewQueue';
import type { ReviewTask } from '@/api/reviewQueue';
import { cn } from '@/utils/formatters';
import { ClipboardCheck, Eye } from 'lucide-react';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const PRIORITY_DOT: Record<string, string> = {
  critical: 'bg-red-600',
  high: 'bg-orange-500',
  medium: 'bg-blue-500',
  low: 'bg-slate-400',
};

const TASK_TYPE_LABEL: Record<string, string> = {
  extraction_review: 'Extraction',
  claim_verification: 'Assertion',
  contradiction_resolution: 'Contradiction',
  decision_approval: 'Decision',
  publication_review: 'Publication',
  transfer_approval: 'Transfert',
  pack_review: 'Pack',
  source_validation: 'Source',
  ritual_approval: 'Rituel',
};

const TASK_TYPE_BADGE: Record<string, string> = {
  extraction_review: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  claim_verification: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
  contradiction_resolution: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  decision_approval: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  publication_review: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  transfer_approval: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
  pack_review: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-300',
  source_validation: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-300',
  ritual_approval: 'bg-rose-100 text-rose-700 dark:bg-rose-900/30 dark:text-rose-300',
};

// ---------------------------------------------------------------------------
// Target navigation helper
// ---------------------------------------------------------------------------

function getTargetPath(task: ReviewTask): string {
  const buildingBase = `/buildings/${task.building_id}`;
  switch (task.target_type) {
    case 'extraction':
      return `${buildingBase}/diagnostics`;
    case 'claim':
      return `${buildingBase}`;
    case 'contradiction':
      return `${buildingBase}`;
    case 'decision':
      return `${buildingBase}`;
    case 'pack':
      return `${buildingBase}`;
    case 'passport':
      return `${buildingBase}`;
    default:
      return buildingBase;
  }
}

// ---------------------------------------------------------------------------
// Age helper
// ---------------------------------------------------------------------------

function formatAge(createdAt: string | null): string {
  if (!createdAt) return '';
  const diff = Date.now() - new Date(createdAt).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return '<1h';
  if (hours < 24) return `${hours}h`;
  const days = Math.floor(hours / 24);
  if (days === 1) return '1j';
  return `${days}j`;
}

// ---------------------------------------------------------------------------
// Task row
// ---------------------------------------------------------------------------

function TaskRow({ task, onNavigate }: { task: ReviewTask; onNavigate: (path: string) => void }) {
  const typeBadge = TASK_TYPE_BADGE[task.task_type] || 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
  const typeLabel = TASK_TYPE_LABEL[task.task_type] || task.task_type;

  return (
    <button
      onClick={() => onNavigate(getTargetPath(task))}
      className="w-full text-left px-4 py-3 border-b border-slate-50 dark:border-slate-700/50 hover:bg-slate-50 dark:hover:bg-slate-700/40 transition-colors"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={cn('w-2 h-2 rounded-full flex-shrink-0', PRIORITY_DOT[task.priority] || PRIORITY_DOT.medium)} />
            <span className={cn('text-[10px] font-semibold uppercase px-1.5 py-0.5 rounded', typeBadge)}>
              {typeLabel}
            </span>
          </div>
          <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{task.title}</p>
          {task.description && (
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 truncate">{task.description}</p>
          )}
        </div>
        <div className="flex items-center gap-2 flex-shrink-0">
          <span className="text-[10px] text-slate-400 dark:text-slate-500">{formatAge(task.created_at)}</span>
          <Eye className="w-3.5 h-3.5 text-slate-400" />
        </div>
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ReviewQueuePanel() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const { data: stats } = useQuery({
    queryKey: ['review-queue-stats'],
    queryFn: reviewQueueApi.getStats,
    refetchInterval: 60_000,
  });

  const { data: tasks, isLoading } = useQuery({
    queryKey: ['review-queue'],
    queryFn: () => reviewQueueApi.getQueue({ status: 'pending', limit: 20 }),
    refetchInterval: 60_000,
  });

  const totalPending = stats?.total_pending ?? 0;
  const criticalCount = stats?.critical ?? 0;
  const highCount = stats?.high ?? 0;

  // Don't render at all if no tasks
  if (!isLoading && totalPending === 0) return null;

  return (
    <div className="rounded-xl border bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 flex flex-col">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-100 dark:border-slate-700">
        <ClipboardCheck className="w-4 h-4 text-violet-500" />
        <h2 className="text-sm font-semibold text-slate-900 dark:text-white">
          {t('review_queue.title') || 'Revues en attente'}
        </h2>
        <div className="ml-auto flex items-center gap-1.5">
          {criticalCount > 0 && (
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-600 text-white">
              {criticalCount} {t('review_queue.critical') || 'critique(s)'}
            </span>
          )}
          {highCount > 0 && (
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-orange-500 text-white">
              {highCount} {t('review_queue.high') || 'haute(s)'}
            </span>
          )}
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
            {totalPending}
          </span>
        </div>
      </div>

      {/* Task list */}
      <div className="flex-1 overflow-y-auto max-h-[360px]">
        {isLoading ? (
          <div className="animate-pulse space-y-3 p-4">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-12 rounded bg-slate-200 dark:bg-slate-700" />
            ))}
          </div>
        ) : !tasks || tasks.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-8 text-slate-400 dark:text-slate-500">
            <ClipboardCheck className="w-8 h-8 mb-2" />
            <p className="text-sm">{t('review_queue.empty') || 'Aucune revue en attente'}</p>
          </div>
        ) : (
          tasks.map((task) => <TaskRow key={task.id} task={task} onNavigate={navigate} />)
        )}
      </div>
    </div>
  );
}
