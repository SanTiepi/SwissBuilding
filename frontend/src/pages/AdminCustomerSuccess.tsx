import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { apiClient } from '@/api/client';
import { cn, formatDate } from '@/utils/formatters';
import { Loader2, AlertTriangle, Trophy, CheckCircle2, Circle, XCircle, RefreshCw } from 'lucide-react';

interface Milestone {
  id: string;
  organization_id: string;
  milestone_type: string;
  status: string;
  achieved_at: string | null;
  evidence_entity_type: string | null;
  evidence_entity_id: string | null;
  evidence_summary: string | null;
  blocker_description: string | null;
  created_at: string;
  updated_at: string;
}

interface NextStep {
  milestone_type: string;
  recommendation: string;
}

interface CustomerSuccessReport {
  organization_id: string;
  milestones: Milestone[];
  next_step: NextStep | null;
}

interface OrgOption {
  id: string;
  name: string;
}

const MILESTONE_TYPES = [
  'first_building_added',
  'first_diagnostic_completed',
  'first_evidence_pack',
  'full_completeness',
  'first_authority_submission',
  'multi_building_portfolio',
];

const customerSuccessApi = {
  getReport: async (orgId: string): Promise<CustomerSuccessReport> => {
    const response = await apiClient.get<CustomerSuccessReport>(`/organizations/${orgId}/customer-success`);
    return response.data;
  },
  listOrgs: async (): Promise<OrgOption[]> => {
    const response = await apiClient.get<OrgOption[] | { items: OrgOption[] }>('/organizations', { params: { limit: 100 } });
    const data = response.data;
    return Array.isArray(data) ? data : Array.isArray((data as any)?.items) ? (data as any).items : [];
  },
};

export default function AdminCustomerSuccess() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [selectedOrgId, setSelectedOrgId] = useState<string>('');

  const { data: orgs = [] } = useQuery({
    queryKey: ['org-list-cs'],
    queryFn: customerSuccessApi.listOrgs,
  });

  const {
    data: report,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['customer-success', selectedOrgId],
    queryFn: () => customerSuccessApi.getReport(selectedOrgId),
    enabled: !!selectedOrgId,
  });

  const checkMutation = useMutation({
    mutationFn: () => customerSuccessApi.getReport(selectedOrgId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['customer-success', selectedOrgId] });
    },
  });

  const statusIcon = (status: string) => {
    if (status === 'achieved')
      return <CheckCircle2 className="w-5 h-5 text-green-500" data-testid="milestone-achieved" />;
    if (status === 'blocked') return <XCircle className="w-5 h-5 text-red-500" data-testid="milestone-blocked" />;
    return <Circle className="w-5 h-5 text-gray-400 dark:text-slate-500" data-testid="milestone-pending" />;
  };

  const statusBg = (status: string) => {
    if (status === 'achieved') return 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20';
    if (status === 'blocked') return 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20';
    return 'border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-700/50';
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{t('customer_success.title')}</h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">{t('customer_success.description')}</p>
      </div>

      {/* Org selector */}
      <div className="flex items-center gap-4">
        <select
          value={selectedOrgId}
          onChange={(e) => setSelectedOrgId(e.target.value)}
          className="px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white"
          data-testid="cs-org-selector"
        >
          <option value="">{t('customer_success.select_org')}</option>
          {orgs.map((org) => (
            <option key={org.id} value={org.id}>
              {org.name}
            </option>
          ))}
        </select>
        {selectedOrgId && (
          <button
            onClick={() => checkMutation.mutate()}
            disabled={checkMutation.isPending}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50"
            data-testid="cs-check-advance"
          >
            <RefreshCw className={cn('w-4 h-4', checkMutation.isPending && 'animate-spin')} />
            {t('customer_success.check_advance')}
          </button>
        )}
      </div>

      {!selectedOrgId && (
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-8 text-center">
          <Trophy className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400">{t('customer_success.select_org_prompt')}</p>
        </div>
      )}

      {selectedOrgId && isLoading && (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      )}

      {selectedOrgId && isError && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-red-700 dark:text-red-300">{t('app.error')}</p>
        </div>
      )}

      {report && (
        <>
          {/* Milestone Tracker */}
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-slate-700">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
                <Trophy className="w-5 h-5 text-yellow-500" />
                {t('customer_success.milestones')}
              </h2>
            </div>
            <div className="p-6 space-y-3" data-testid="cs-milestone-list">
              {MILESTONE_TYPES.map((mType) => {
                const milestone = report.milestones.find((m) => m.milestone_type === mType);
                const status = milestone?.status || 'pending';
                return (
                  <div
                    key={mType}
                    className={cn('rounded-lg border p-4 flex items-start gap-3', statusBg(status))}
                    data-testid={`milestone-${mType}`}
                  >
                    {statusIcon(status)}
                    <div className="flex-1">
                      <p className="font-medium text-gray-900 dark:text-white">
                        {t(`customer_success.milestone_${mType}`) || mType}
                      </p>
                      {milestone?.achieved_at && (
                        <p className="text-xs text-green-600 dark:text-green-400 mt-1">
                          {t('customer_success.achieved_at')}: {formatDate(milestone.achieved_at)}
                        </p>
                      )}
                      {milestone?.evidence_summary && (
                        <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">
                          {t('customer_success.evidence')}: {milestone.evidence_summary}
                        </p>
                      )}
                      {milestone?.blocker_description && (
                        <p className="text-xs text-red-600 dark:text-red-400 mt-1">
                          {t('customer_success.blocker')}: {milestone.blocker_description}
                        </p>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Next Step Recommendation */}
          {report.next_step && (
            <div
              className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-xl p-6"
              data-testid="cs-next-step"
            >
              <h3 className="text-sm font-semibold text-blue-800 dark:text-blue-300 mb-2">
                {t('customer_success.next_step')}
              </h3>
              <p className="text-sm text-blue-700 dark:text-blue-300">
                <span className="font-medium">{report.next_step.milestone_type}</span>:{' '}
                {report.next_step.recommendation}
              </p>
            </div>
          )}
        </>
      )}
    </div>
  );
}
