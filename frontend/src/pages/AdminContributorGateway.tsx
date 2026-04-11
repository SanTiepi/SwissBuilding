/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under Admin.
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { exchangeHardeningApi } from '@/api/exchangeHardening';
import { cn, formatDate } from '@/utils/formatters';
import { Users, CheckCircle, XCircle, Clock, Link2, FileText } from 'lucide-react';

const STATUS_STYLE: Record<string, string> = {
  open: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
  fulfilled: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400',
  expired: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
  cancelled: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
  pending_review: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400',
  accepted: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
};

export default function AdminContributorGateway() {
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState<'requests' | 'submissions'>('submissions');

  const { data: requests, isLoading: loadingRequests } = useQuery({
    queryKey: ['contributor-requests'],
    queryFn: () => exchangeHardeningApi.listContributorRequests(),
    staleTime: 30_000,
  });

  const { data: pendingSubmissions, isLoading: loadingSubmissions } = useQuery({
    queryKey: ['contributor-submissions-pending'],
    queryFn: () => exchangeHardeningApi.listPendingSubmissions(),
    staleTime: 15_000,
  });

  const acceptMutation = useMutation({
    mutationFn: (id: string) => exchangeHardeningApi.acceptSubmission(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contributor-submissions-pending'] });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: (id: string) => exchangeHardeningApi.rejectSubmission(id, 'Rejected by reviewer'),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['contributor-submissions-pending'] });
    },
  });

  const tabs = [
    { key: 'submissions' as const, label: 'Pending Submissions', count: pendingSubmissions?.length ?? 0 },
    { key: 'requests' as const, label: 'Gateway Requests', count: requests?.length ?? 0 },
  ];

  return (
    <div className="space-y-6" data-testid="admin-contributor-gateway">
      <div className="flex items-center gap-3">
        <Users className="w-6 h-6 text-indigo-500" />
        <h1 className="text-xl font-bold text-gray-900 dark:text-white">{'Contributor Gateway'}</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-gray-100 dark:bg-gray-800 rounded-lg p-1" data-testid="gateway-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={cn(
              'px-4 py-2 rounded-md text-sm font-medium transition-colors',
              activeTab === tab.key
                ? 'bg-white dark:bg-gray-700 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300',
            )}
            data-testid={`tab-${tab.key}`}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      {/* Pending Submissions Tab */}
      {activeTab === 'submissions' && (
        <div className="space-y-3" data-testid="submissions-list">
          {loadingSubmissions ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map((i) => (
                <div key={i} className="h-16 bg-gray-200 dark:bg-gray-700 rounded-lg" />
              ))}
            </div>
          ) : (pendingSubmissions?.length ?? 0) === 0 ? (
            <div className="text-center py-12 text-gray-400" data-testid="no-submissions">
              <FileText className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">{'No pending submissions'}</p>
            </div>
          ) : (
            pendingSubmissions?.map((sub) => (
              <div
                key={sub.id}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4"
                data-testid={`submission-${sub.id}`}
              >
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {sub.submission_type.replace(/_/g, ' ')}
                    </span>
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded text-xs font-medium',
                        STATUS_STYLE[sub.status] ?? 'bg-gray-100 text-gray-600',
                      )}
                    >
                      {sub.status}
                    </span>
                  </div>
                  <span className="text-xs text-gray-400">{formatDate(sub.created_at)}</span>
                </div>

                {sub.contributor_name && (
                  <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">
                    {'From:'} {sub.contributor_name}
                  </p>
                )}
                {sub.notes && <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">{sub.notes}</p>}

                <div className="flex gap-2 pt-2 border-t border-gray-100 dark:border-gray-700">
                  <button
                    onClick={() => acceptMutation.mutate(sub.id)}
                    disabled={acceptMutation.isPending}
                    className="flex items-center gap-1 px-3 py-1.5 bg-green-600 text-white rounded text-xs font-medium hover:bg-green-700 disabled:opacity-50"
                    data-testid={`accept-${sub.id}`}
                  >
                    <CheckCircle className="w-3 h-3" />
                    {'Accept'}
                  </button>
                  <button
                    onClick={() => rejectMutation.mutate(sub.id)}
                    disabled={rejectMutation.isPending}
                    className="flex items-center gap-1 px-3 py-1.5 bg-red-600 text-white rounded text-xs font-medium hover:bg-red-700 disabled:opacity-50"
                    data-testid={`reject-${sub.id}`}
                  >
                    <XCircle className="w-3 h-3" />
                    {'Reject'}
                  </button>
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Gateway Requests Tab */}
      {activeTab === 'requests' && (
        <div className="space-y-3" data-testid="requests-list">
          {loadingRequests ? (
            <div className="animate-pulse space-y-2">
              {[1, 2].map((i) => (
                <div key={i} className="h-14 bg-gray-200 dark:bg-gray-700 rounded-lg" />
              ))}
            </div>
          ) : (requests?.length ?? 0) === 0 ? (
            <div className="text-center py-12 text-gray-400" data-testid="no-requests">
              <Link2 className="w-8 h-8 mx-auto mb-2 opacity-50" />
              <p className="text-sm">{'No contributor requests'}</p>
            </div>
          ) : (
            requests?.map((req) => (
              <div
                key={req.id}
                className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 flex items-center justify-between"
                data-testid={`request-${req.id}`}
              >
                <div>
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-sm font-medium text-gray-900 dark:text-white">{req.contributor_type}</span>
                    <span
                      className={cn(
                        'px-2 py-0.5 rounded text-xs font-medium',
                        STATUS_STYLE[req.status] ?? 'bg-gray-100 text-gray-600',
                      )}
                    >
                      {req.status}
                    </span>
                  </div>
                  {req.scope_description && (
                    <p className="text-xs text-gray-500 dark:text-gray-400">{req.scope_description}</p>
                  )}
                </div>
                <div className="text-right">
                  <p className="text-xs text-gray-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {'Expires:'} {formatDate(req.expires_at)}
                  </p>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
