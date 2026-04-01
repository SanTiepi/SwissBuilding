import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import {
  buildingActivitiesApi,
  type BuildingActivityItem,
  type ActivityListParams,
} from '@/api/buildingActivities';

interface ActivityLedgerProps {
  buildingId: string;
}

const ACTIVITY_TYPE_OPTIONS = [
  'diagnostic_submitted',
  'sample_recorded',
  'document_uploaded',
  'action_created',
  'action_completed',
  'risk_assessed',
  'readiness_evaluated',
  'intervention_started',
  'intervention_completed',
  'note_added',
  'status_changed',
  'remediation_started',
  'authority_notified',
] as const;

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
  diagnostician: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  owner: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  architect: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  authority: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  contractor: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
};

function getInitials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

function formatRelativeTime(dateStr: string): string {
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH}h ago`;
  const diffD = Math.floor(diffH / 24);
  if (diffD < 30) return `${diffD}d ago`;
  return date.toLocaleDateString();
}

export function ActivityLedger({ buildingId }: ActivityLedgerProps) {
  const { t } = useTranslation();
  const [page, setPage] = useState(1);
  const [filterType, setFilterType] = useState<string>('');
  const [filterDateFrom, setFilterDateFrom] = useState<string>('');
  const [filterDateTo, setFilterDateTo] = useState<string>('');
  const size = 20;

  const params: ActivityListParams = {
    page,
    size,
    ...(filterType ? { activity_type: filterType } : {}),
    ...(filterDateFrom ? { date_from: filterDateFrom } : {}),
    ...(filterDateTo ? { date_to: filterDateTo } : {}),
  };

  const {
    data: ledger,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-activities', buildingId, params],
    queryFn: () => buildingActivitiesApi.list(buildingId, params),
  });

  const { data: chainStatus } = useQuery({
    queryKey: ['building-activities-chain', buildingId],
    queryFn: () => buildingActivitiesApi.verifyChain(buildingId),
  });

  const totalPages = ledger ? Math.ceil(ledger.total / size) : 0;

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('activity_ledger.title') || 'Activity Ledger'}
        </h3>
        {chainStatus && (
          <div className="flex items-center gap-2">
            {chainStatus.valid ? (
              <span className="inline-flex items-center gap-1 rounded-full bg-green-100 px-3 py-1 text-sm font-medium text-green-800 dark:bg-green-900 dark:text-green-200">
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                    clipRule="evenodd"
                  />
                </svg>
                {t('activity_ledger.chain_valid') || 'Chain valid'}
              </span>
            ) : (
              <span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-3 py-1 text-sm font-medium text-red-800 dark:bg-red-900 dark:text-red-200">
                <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 20 20">
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                {t('activity_ledger.chain_broken') || 'Chain broken'}
              </span>
            )}
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {chainStatus.total_entries} entries
            </span>
          </div>
        )}
      </div>

      {/* Filters */}
      <div className="flex flex-wrap items-center gap-3 rounded-lg bg-gray-50 p-3 dark:bg-gray-800">
        <select
          value={filterType}
          onChange={(e) => {
            setFilterType(e.target.value);
            setPage(1);
          }}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
        >
          <option value="">{t('activity_ledger.filter_type') || 'All types'}</option>
          {ACTIVITY_TYPE_OPTIONS.map((type) => (
            <option key={type} value={type}>
              {t(`activity_ledger.type_${type}`) || type.replace(/_/g, ' ')}
            </option>
          ))}
        </select>
        <input
          type="date"
          value={filterDateFrom}
          onChange={(e) => {
            setFilterDateFrom(e.target.value);
            setPage(1);
          }}
          placeholder={t('activity_ledger.filter_date') || 'From'}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
        />
        <input
          type="date"
          value={filterDateTo}
          onChange={(e) => {
            setFilterDateTo(e.target.value);
            setPage(1);
          }}
          className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-sm dark:border-gray-600 dark:bg-gray-700 dark:text-white"
        />
      </div>

      {/* Content */}
      {isLoading && <p className="text-gray-500 dark:text-gray-400">Loading...</p>}
      {isError && <p className="text-red-500">Failed to load activities.</p>}
      {ledger && ledger.items.length === 0 && (
        <p className="py-8 text-center text-gray-500 dark:text-gray-400">
          {t('activity_ledger.empty') || 'No activities recorded yet.'}
        </p>
      )}

      {/* Timeline */}
      {ledger && ledger.items.length > 0 && (
        <div className="relative space-y-0">
          <div className="absolute left-5 top-0 h-full w-0.5 bg-gray-200 dark:bg-gray-700" />
          {ledger.items.map((activity) => (
            <ActivityEntry key={activity.id} activity={activity} t={t} />
          ))}
        </div>
      )}

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <button
            onClick={() => setPage((p) => Math.max(1, p - 1))}
            disabled={page === 1}
            className="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-white"
          >
            Previous
          </button>
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {page} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            disabled={page === totalPages}
            className="rounded-md border border-gray-300 px-3 py-1 text-sm disabled:opacity-50 dark:border-gray-600 dark:text-white"
          >
            Next
          </button>
        </div>
      )}
    </div>
  );
}

function ActivityEntry({
  activity,
  t,
}: {
  activity: BuildingActivityItem;
  t: (key: string) => string;
}) {
  const roleClass = ROLE_COLORS[activity.actor_role] || 'bg-gray-100 text-gray-800 dark:bg-gray-700 dark:text-gray-200';

  return (
    <div className="relative flex gap-4 py-3 pl-2">
      {/* Avatar circle */}
      <div className="z-10 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-full bg-blue-500 text-xs font-bold text-white">
        {getInitials(activity.actor_name)}
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-medium text-gray-900 dark:text-white">{activity.actor_name}</span>
          <span className={`inline-block rounded-full px-2 py-0.5 text-xs font-medium ${roleClass}`}>
            {activity.actor_role}
          </span>
          <span className="text-xs text-gray-500 dark:text-gray-400" title={new Date(activity.created_at).toLocaleString()}>
            {formatRelativeTime(activity.created_at)}
          </span>
        </div>
        <p className="mt-0.5 text-sm text-gray-800 dark:text-gray-200">{activity.title}</p>
        {activity.description && (
          <p className="mt-0.5 text-xs text-gray-500 dark:text-gray-400">{activity.description}</p>
        )}
        {activity.reason && (
          <p className="mt-0.5 text-xs italic text-gray-400 dark:text-gray-500">
            Reason: {activity.reason}
          </p>
        )}
        <div className="mt-1 flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
          <span>
            {t(`activity_ledger.type_${activity.activity_type}`) || activity.activity_type.replace(/_/g, ' ')}
          </span>
          <span>·</span>
          <span>{activity.entity_type}</span>
        </div>
      </div>
    </div>
  );
}
