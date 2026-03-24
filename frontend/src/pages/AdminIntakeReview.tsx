import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { intakeApi, type IntakeRequest } from '@/api/intake';
import { cn } from '@/utils/formatters';
import {
  Loader2,
  Inbox,
  CheckCircle2,
  XCircle,
  ArrowRightCircle,
  Mail,
  Phone,
  Building2,
  MapPin,
  Clock,
  Filter,
} from 'lucide-react';

const STATUS_FILTERS = ['all', 'new', 'qualified', 'converted', 'rejected'] as const;

const statusColors: Record<string, string> = {
  new: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  qualified: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  converted: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const urgencyColors: Record<string, string> = {
  standard: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  urgent: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  emergency: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

export default function AdminIntakeReview() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const { data, isLoading } = useQuery({
    queryKey: ['admin-intake', statusFilter],
    queryFn: () => intakeApi.list({ status: statusFilter === 'all' ? undefined : statusFilter }),
  });

  const qualifyMutation = useMutation({
    mutationFn: (id: string) => intakeApi.updateStatus(id, 'qualified'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-intake'] }),
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => intakeApi.updateStatus(id, 'rejected'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-intake'] }),
  });

  const convertMutation = useMutation({
    mutationFn: (id: string) => intakeApi.convert(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-intake'] }),
  });

  if (user?.role !== 'admin') {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-slate-500 dark:text-slate-400">{t('admin.access_denied') || 'Access denied'}</p>
      </div>
    );
  }

  const formatDate = (dateStr: string) => {
    try {
      return new Date(dateStr).toLocaleDateString('fr-CH', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 dark:text-white" data-testid="intake-review-title">
            {t('intake.review_title')}
          </h1>
          <p className="text-slate-500 dark:text-slate-400 mt-1">{t('intake.review_subtitle')}</p>
        </div>
        <div className="flex items-center gap-1 text-sm text-slate-500 dark:text-slate-400">
          <Inbox className="w-4 h-4" />
          <span>{data?.total ?? 0} {t('intake.total_requests')}</span>
        </div>
      </div>

      {/* Status filter */}
      <div className="flex flex-wrap gap-2" data-testid="intake-status-filter">
        <Filter className="w-4 h-4 text-slate-400 self-center" />
        {STATUS_FILTERS.map((status) => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            data-testid={`intake-filter-${status}`}
            className={cn(
              'px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              statusFilter === status
                ? 'bg-red-600 text-white'
                : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600',
            )}
          >
            {status === 'all' ? t('intake.filter_all') : t(`intake.status.${status}`)}
          </button>
        ))}
      </div>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center h-48">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      )}

      {/* Empty state */}
      {!isLoading && (!data?.items || data.items.length === 0) && (
        <div className="text-center py-12" data-testid="intake-empty">
          <Inbox className="w-12 h-12 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-slate-500 dark:text-slate-400">{t('intake.no_requests')}</p>
        </div>
      )}

      {/* Request cards */}
      <div className="space-y-4" data-testid="intake-list">
        {data?.items?.map((req: IntakeRequest) => (
          <div
            key={req.id}
            className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 shadow-sm"
            data-testid={`intake-card-${req.id}`}
          >
            <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3">
              {/* Left: info */}
              <div className="space-y-2 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <h3 className="font-semibold text-slate-900 dark:text-white">{req.name}</h3>
                  <span
                    className={cn('px-2 py-0.5 rounded-full text-xs font-medium', statusColors[req.status])}
                    data-testid={`intake-status-${req.id}`}
                  >
                    {t(`intake.status.${req.status}`)}
                  </span>
                  <span
                    className={cn('px-2 py-0.5 rounded-full text-xs font-medium', urgencyColors[req.urgency])}
                    data-testid={`intake-urgency-${req.id}`}
                  >
                    {t(`intake.urgency.${req.urgency}`)}
                  </span>
                  <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                    {t(`intake.request_type.${req.request_type}`)}
                  </span>
                </div>

                <div className="flex flex-wrap gap-4 text-sm text-slate-600 dark:text-slate-400">
                  <span className="flex items-center gap-1">
                    <Mail className="w-3.5 h-3.5" /> {req.email}
                  </span>
                  {req.phone && (
                    <span className="flex items-center gap-1">
                      <Phone className="w-3.5 h-3.5" /> {req.phone}
                    </span>
                  )}
                  {req.company && (
                    <span className="flex items-center gap-1">
                      <Building2 className="w-3.5 h-3.5" /> {req.company}
                    </span>
                  )}
                </div>

                <div className="flex flex-wrap gap-4 text-sm text-slate-600 dark:text-slate-400">
                  <span className="flex items-center gap-1">
                    <MapPin className="w-3.5 h-3.5" />
                    {req.building_address}
                    {req.city && `, ${req.city}`}
                    {req.postal_code && ` ${req.postal_code}`}
                  </span>
                  {req.egid && <span className="text-xs font-mono">EGID: {req.egid}</span>}
                </div>

                {req.description && (
                  <p className="text-sm text-slate-500 dark:text-slate-400 mt-1 line-clamp-2">{req.description}</p>
                )}

                <div className="flex items-center gap-1 text-xs text-slate-400">
                  <Clock className="w-3 h-3" />
                  {formatDate(req.created_at)}
                </div>
              </div>

              {/* Right: actions */}
              <div className="flex sm:flex-col gap-2">
                {req.status === 'new' && (
                  <button
                    onClick={() => qualifyMutation.mutate(req.id)}
                    disabled={qualifyMutation.isPending}
                    data-testid={`intake-qualify-${req.id}`}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg bg-yellow-50 dark:bg-yellow-900/20 text-yellow-700 dark:text-yellow-400 hover:bg-yellow-100 dark:hover:bg-yellow-900/30 transition-colors"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    {t('intake.action_qualify')}
                  </button>
                )}
                {(req.status === 'new' || req.status === 'qualified') && (
                  <button
                    onClick={() => convertMutation.mutate(req.id)}
                    disabled={convertMutation.isPending}
                    data-testid={`intake-convert-${req.id}`}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 hover:bg-green-100 dark:hover:bg-green-900/30 transition-colors"
                  >
                    <ArrowRightCircle className="w-4 h-4" />
                    {t('intake.action_convert')}
                  </button>
                )}
                {req.status !== 'rejected' && req.status !== 'converted' && (
                  <button
                    onClick={() => rejectMutation.mutate(req.id)}
                    disabled={rejectMutation.isPending}
                    data-testid={`intake-reject-${req.id}`}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm font-medium rounded-lg bg-red-50 dark:bg-red-900/20 text-red-700 dark:text-red-400 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
                  >
                    <XCircle className="w-4 h-4" />
                    {t('intake.action_reject')}
                  </button>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
