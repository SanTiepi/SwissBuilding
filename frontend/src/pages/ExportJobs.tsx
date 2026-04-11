/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a standalone specialist view (cross-cutting utility).
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { exportsApi } from '@/api/exports';
import { backgroundJobsApi } from '@/api/backgroundJobs';
import { useAuth } from '@/hooks/useAuth';
import { useTranslation } from '@/i18n';
import { formatDate, cn } from '@/utils/formatters';
import { toast } from '@/store/toastStore';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import type { ExportJob, ExportJobStatus, BackgroundJob } from '@/types';
import {
  Download,
  Loader2,
  CheckCircle2,
  XCircle,
  Clock,
  Package,
  Ban,
  RotateCcw,
  ChevronDown,
  ChevronUp,
  Timer,
} from 'lucide-react';

const STATUS_CONFIG: Record<ExportJobStatus, { icon: typeof Clock; color: string; bgColor: string }> = {
  queued: { icon: Clock, color: 'text-gray-500', bgColor: 'bg-gray-100 dark:bg-slate-700' },
  processing: {
    icon: Loader2,
    color: 'text-blue-500',
    bgColor: 'bg-blue-100 dark:bg-blue-900/30',
  },
  completed: {
    icon: CheckCircle2,
    color: 'text-green-500',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
  },
  failed: { icon: XCircle, color: 'text-red-500', bgColor: 'bg-red-100 dark:bg-red-900/30' },
};

const STATUS_FILTERS: ExportJobStatus[] = ['queued', 'processing', 'completed', 'failed'];

function formatElapsedTime(createdAt: string): string {
  const created = new Date(createdAt).getTime();
  const now = Date.now();
  const diffMs = Math.max(0, now - created);
  const totalSeconds = Math.floor(diffMs / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes > 0) {
    return `${minutes}m ${seconds}s`;
  }
  return `${seconds}s`;
}

function ProgressBar({ progressPct }: { progressPct: number | undefined }) {
  if (progressPct == null) {
    // Indeterminate progress
    return (
      <div className="w-full h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
        <div className="h-full w-1/3 bg-blue-500 rounded-full animate-[indeterminate_1.5s_ease-in-out_infinite]" />
      </div>
    );
  }
  const pct = Math.min(100, Math.max(0, progressPct));
  return (
    <div className="w-full h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
      <div className="h-full bg-blue-500 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function ExportJobs() {
  const { t } = useTranslation();
  useAuth();
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [page, setPage] = useState(1);
  const [expandedErrors, setExpandedErrors] = useState<Set<string>>(new Set());

  const { data, isLoading, isError } = useQuery({
    queryKey: ['export-jobs', statusFilter, page],
    queryFn: () => exportsApi.list({ status: statusFilter || undefined, page, size: 20 }),
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      const hasActive = items.some((j) => j.status === 'queued' || j.status === 'processing');
      return hasActive ? 5000 : false;
    },
  });

  const jobs = useMemo(() => data?.items ?? [], [data?.items]);
  const totalPages = data?.pages ?? 0;

  // Fetch background jobs for progress tracking on processing exports
  const processingJobIds = useMemo(() => jobs.filter((j) => j.status === 'processing').map((j) => j.id), [jobs]);

  const { data: bgJobs } = useQuery({
    queryKey: ['background-jobs', processingJobIds],
    queryFn: () => backgroundJobsApi.list({ job_type: 'export', status: 'running', limit: 50 }),
    enabled: processingJobIds.length > 0,
    refetchInterval: processingJobIds.length > 0 ? 5000 : false,
  });

  const bgJobMap = useMemo(() => {
    const map = new Map<string, BackgroundJob>();
    if (bgJobs) {
      for (const bj of bgJobs) {
        if (bj.building_id) {
          map.set(bj.building_id, bj);
        }
        map.set(bj.id, bj);
      }
    }
    return map;
  }, [bgJobs]);

  // Summary counts
  const summary = useMemo(() => {
    const counts = { queued: 0, processing: 0, completed: 0, failed: 0 };
    for (const job of jobs) {
      if (job.status in counts) {
        counts[job.status]++;
      }
    }
    return counts;
  }, [jobs]);

  const hasAnySummary = summary.queued + summary.processing + summary.completed + summary.failed > 0;

  // Cancel mutation
  const cancelMutation = useMutation({
    mutationFn: (id: string) => exportsApi.cancel(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['export-jobs'] });
      toast(t('export.cancel_success') || 'Export cancelled successfully', 'success');
    },
    onError: () => {
      toast(t('app.error') || 'Error', 'error');
    },
  });

  // Retry mutation (creates a new export with same params)
  const retryMutation = useMutation({
    mutationFn: (job: ExportJob) =>
      exportsApi.create({
        type: job.type,
        building_id: job.building_id ?? undefined,
        organization_id: job.organization_id ?? undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['export-jobs'] });
      toast(t('export.retry_success') || 'Export retried successfully', 'success');
    },
    onError: () => {
      toast(t('app.error') || 'Error', 'error');
    },
  });

  const handleCancel = useCallback(
    (id: string) => {
      if (window.confirm(t('export.cancel_confirm') || 'Are you sure you want to cancel this export?')) {
        cancelMutation.mutate(id);
      }
    },
    [cancelMutation, t],
  );

  const handleRetry = useCallback(
    (job: ExportJob) => {
      if (window.confirm(t('export.retry_confirm') || 'Are you sure you want to retry this export?')) {
        retryMutation.mutate(job);
      }
    },
    [retryMutation, t],
  );

  const toggleErrorExpanded = useCallback((id: string) => {
    setExpandedErrors((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('export.jobs_title') || 'Export Jobs'}
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {t('export.jobs_description') || 'Track dossier and pack generation progress'}
          </p>
        </div>
        <Package className="w-8 h-8 text-gray-300 dark:text-slate-600" />
      </div>

      {/* Summary bar */}
      {hasAnySummary && (
        <div className="flex flex-wrap gap-3">
          {summary.queued > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-slate-700 text-sm text-gray-600 dark:text-slate-300">
              <Clock className="w-3.5 h-3.5" />
              {t('export.queued_count', { count: summary.queued }) || `${summary.queued} queued`}
            </div>
          )}
          {summary.processing > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-blue-100 dark:bg-blue-900/30 text-sm text-blue-600 dark:text-blue-300">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              {t('export.processing_count', { count: summary.processing }) || `${summary.processing} processing`}
            </div>
          )}
          {summary.completed > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-green-100 dark:bg-green-900/30 text-sm text-green-600 dark:text-green-300">
              <CheckCircle2 className="w-3.5 h-3.5" />
              {t('export.completed_count', { count: summary.completed }) || `${summary.completed} completed`}
            </div>
          )}
          {summary.failed > 0 && (
            <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-100 dark:bg-red-900/30 text-sm text-red-600 dark:text-red-300">
              <XCircle className="w-3.5 h-3.5" />
              {t('export.failed_count', { count: summary.failed }) || `${summary.failed} failed`}
            </div>
          )}
        </div>
      )}

      {/* Status filters */}
      <div className="flex flex-wrap gap-2">
        <button
          onClick={() => {
            setStatusFilter('');
            setPage(1);
          }}
          className={cn(
            'px-3 py-1.5 text-sm rounded-lg border transition-colors',
            !statusFilter
              ? 'bg-red-600 text-white border-red-600'
              : 'bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200 border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700',
          )}
        >
          {t('common.all') || 'All'}
        </button>
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            onClick={() => {
              setStatusFilter(status);
              setPage(1);
            }}
            className={cn(
              'px-3 py-1.5 text-sm rounded-lg border transition-colors',
              statusFilter === status
                ? 'bg-red-600 text-white border-red-600'
                : 'bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200 border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-700',
            )}
          >
            {t(`export.status.${status}`) || status}
          </button>
        ))}
      </div>

      {/* Main content */}
      <AsyncStateWrapper
        isLoading={isLoading}
        isError={isError}
        data={jobs}
        variant="page"
        icon={<Download className="w-12 h-12 text-gray-300 dark:text-slate-600" />}
        emptyMessage={t('export.no_exports') || t('export.no_jobs') || 'No export jobs'}
      >
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900/50">
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('export.column.status') || 'Status'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('export.column.type') || 'Type'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('export.column.progress') || 'Progress'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('export.column.created') || 'Created'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('export.column.completed') || 'Completed'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('export.column.error') || 'Error'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('export.column.actions') || 'Actions'}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
                {jobs.map((job: ExportJob) => {
                  const config = STATUS_CONFIG[job.status];
                  const Icon = config.icon;
                  const isActive = job.status === 'queued' || job.status === 'processing';
                  const bgJob = bgJobMap.get(job.id);
                  const isErrorExpanded = expandedErrors.has(job.id);

                  return (
                    <tr key={job.id} className="hover:bg-gray-50 dark:hover:bg-slate-700/50">
                      {/* Status badge */}
                      <td className="px-4 py-3">
                        <span
                          className={cn(
                            'inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium',
                            config.bgColor,
                            config.color,
                            isActive && 'animate-pulse',
                          )}
                        >
                          <Icon className={cn('w-3 h-3', job.status === 'processing' && 'animate-spin')} />
                          {t(`export.status.${job.status}`) || job.status}
                        </span>
                      </td>

                      {/* Type */}
                      <td className="px-4 py-3 text-gray-700 dark:text-slate-200">
                        {t(`export.type.${job.type}`) || job.type.replace(/_/g, ' ')}
                      </td>

                      {/* Progress */}
                      <td className="px-4 py-3 min-w-[140px]">
                        {job.status === 'processing' ? (
                          <div className="space-y-1">
                            <ProgressBar progressPct={bgJob?.progress_pct} />
                            <div className="flex items-center justify-between text-xs text-gray-500 dark:text-slate-400">
                              <span>{bgJob?.progress_pct != null ? `${bgJob.progress_pct}%` : ''}</span>
                              <span className="flex items-center gap-1">
                                <Timer className="w-3 h-3" />
                                {formatElapsedTime(job.created_at)}
                              </span>
                            </div>
                          </div>
                        ) : job.status === 'queued' ? (
                          <div className="flex items-center gap-1 text-xs text-gray-400 dark:text-slate-500">
                            <Timer className="w-3 h-3" />
                            {formatElapsedTime(job.created_at)}
                          </div>
                        ) : (
                          <span className="text-gray-300 dark:text-slate-600">{'\u2014'}</span>
                        )}
                      </td>

                      {/* Created */}
                      <td className="px-4 py-3 text-gray-500 dark:text-slate-400">{formatDate(job.created_at)}</td>

                      {/* Completed */}
                      <td className="px-4 py-3 text-gray-500 dark:text-slate-400">
                        {job.completed_at ? formatDate(job.completed_at) : '\u2014'}
                      </td>

                      {/* Error */}
                      <td className="px-4 py-3 max-w-[200px]">
                        {job.error_message ? (
                          <div>
                            <button
                              onClick={() => toggleErrorExpanded(job.id)}
                              className="flex items-center gap-1 text-red-500 text-xs hover:text-red-600 dark:hover:text-red-400"
                            >
                              {isErrorExpanded ? (
                                <ChevronUp className="w-3 h-3 flex-shrink-0" />
                              ) : (
                                <ChevronDown className="w-3 h-3 flex-shrink-0" />
                              )}
                              {t('export.error_details') || 'Error details'}
                            </button>
                            {isErrorExpanded && (
                              <div className="mt-1 p-2 rounded bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-xs text-red-600 dark:text-red-300 break-words whitespace-pre-wrap">
                                {job.error_message}
                              </div>
                            )}
                          </div>
                        ) : (
                          <span className="text-gray-300 dark:text-slate-600">{'\u2014'}</span>
                        )}
                      </td>

                      {/* Actions */}
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {job.status === 'queued' && (
                            <button
                              onClick={() => handleCancel(job.id)}
                              disabled={cancelMutation.isPending}
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md border border-gray-300 dark:border-slate-600 text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700 disabled:opacity-50 transition-colors"
                              title={t('export.cancel') || 'Cancel'}
                            >
                              <Ban className="w-3 h-3" />
                              {t('export.cancel') || 'Cancel'}
                            </button>
                          )}
                          {job.status === 'failed' && (
                            <button
                              onClick={() => handleRetry(job)}
                              disabled={retryMutation.isPending}
                              className="inline-flex items-center gap-1 px-2 py-1 text-xs rounded-md border border-blue-300 dark:border-blue-700 text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 disabled:opacity-50 transition-colors"
                              title={t('export.retry') || 'Retry'}
                            >
                              <RotateCcw className="w-3 h-3" />
                              {t('export.retry') || 'Retry'}
                            </button>
                          )}
                          {job.status !== 'queued' && job.status !== 'failed' && (
                            <span className="text-gray-300 dark:text-slate-600">{'\u2014'}</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t border-gray-200 dark:border-slate-700">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page <= 1}
                className="px-3 py-1 text-sm text-gray-500 dark:text-slate-400 disabled:opacity-50"
              >
                {t('pagination.previous') || 'Previous'}
              </button>
              <span className="text-sm text-gray-500 dark:text-slate-400">
                {page} / {totalPages}
              </span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                disabled={page >= totalPages}
                className="px-3 py-1 text-sm text-gray-500 dark:text-slate-400 disabled:opacity-50"
              >
                {t('pagination.next') || 'Next'}
              </button>
            </div>
          )}
        </div>
      </AsyncStateWrapper>
    </div>
  );
}
