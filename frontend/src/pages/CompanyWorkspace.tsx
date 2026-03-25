import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { remediationApi } from '@/api/remediation';
import type { CompanyWorkspaceSummary } from '@/api/remediation';
import { FileText, Award, ClipboardCheck, Star, Shield, Mail } from 'lucide-react';
import { cn } from '@/utils/formatters';

function StatCard({ label, value, icon: Icon, color }: { label: string; value: number; icon: React.ElementType; color: string }) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-4 flex items-center gap-3">
      <div className={cn('p-2 rounded-lg', color)}>
        <Icon className="w-5 h-5 text-white" />
      </div>
      <div>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{value}</p>
        <p className="text-sm text-gray-500 dark:text-slate-400">{label}</p>
      </div>
    </div>
  );
}

export default function CompanyWorkspace() {
  const { t } = useTranslation();
  // For now, use a placeholder profile ID — real integration would come from route params or auth context
  const profileId = new URLSearchParams(window.location.search).get('profileId') || '';

  const { data, isLoading, error } = useQuery<CompanyWorkspaceSummary>({
    queryKey: ['company-workspace', profileId],
    queryFn: () => remediationApi.getCompanyWorkspace(profileId),
    enabled: !!profileId,
  });

  if (!profileId) {
    return (
      <div className="p-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white mb-4">
          {t('workspace.company_title') || 'Company Workspace'}
        </h1>
        <p className="text-gray-500 dark:text-slate-400">
          {t('workspace.no_profile_selected') || 'No company profile selected. Use ?profileId= in the URL.'}
        </p>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-1/3" />
          <div className="grid grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5, 6].map((i) => (
              <div key={i} className="h-24 bg-gray-200 dark:bg-slate-700 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <p className="text-red-600 dark:text-red-400">
          {t('workspace.load_error') || 'Failed to load workspace data.'}
        </p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">{data.company_name}</h1>
          <div className="flex items-center gap-2 mt-1">
            {data.is_verified && (
              <span className="inline-flex items-center gap-1 text-xs font-medium text-green-700 bg-green-100 dark:text-green-300 dark:bg-green-900/30 px-2 py-0.5 rounded-full">
                <Shield className="w-3 h-3" />
                {t('workspace.verified') || 'Verified'}
              </span>
            )}
            {data.subscription_status && (
              <span className={cn(
                'text-xs font-medium px-2 py-0.5 rounded-full',
                data.subscription_status === 'active'
                  ? 'text-blue-700 bg-blue-100 dark:text-blue-300 dark:bg-blue-900/30'
                  : 'text-gray-700 bg-gray-100 dark:text-gray-300 dark:bg-gray-700',
              )}>
                {data.subscription_plan} - {data.subscription_status}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <StatCard
          label={t('workspace.pending_invitations') || 'Pending Invitations'}
          value={data.pending_invitations}
          icon={Mail}
          color="bg-amber-500"
        />
        <StatCard
          label={t('workspace.active_rfqs') || 'Active RFQs'}
          value={data.active_rfqs}
          icon={FileText}
          color="bg-blue-500"
        />
        <StatCard
          label={t('workspace.draft_quotes') || 'Draft Quotes'}
          value={data.draft_quotes}
          icon={FileText}
          color="bg-purple-500"
        />
        <StatCard
          label={t('workspace.awards_won') || 'Awards Won'}
          value={data.awards_won}
          icon={Award}
          color="bg-green-500"
        />
        <StatCard
          label={t('workspace.completions_pending') || 'Completions Pending'}
          value={data.completions_pending}
          icon={ClipboardCheck}
          color="bg-orange-500"
        />
        <StatCard
          label={t('workspace.reviews_published') || 'Reviews Published'}
          value={data.reviews_published}
          icon={Star}
          color="bg-indigo-500"
        />
      </div>
    </div>
  );
}
