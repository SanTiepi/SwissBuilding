import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { remediationApi } from '@/api/remediation';
import type { OperatorRemediationQueue } from '@/api/remediation';
import { FileText, MessageSquare, Award, ClipboardCheck, Wrench } from 'lucide-react';
import { cn } from '@/utils/formatters';

function QueueCard({
  label,
  value,
  icon: Icon,
  color,
}: {
  label: string;
  value: number;
  icon: React.ElementType;
  color: string;
}) {
  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-5 flex items-center gap-4">
      <div className={cn('p-3 rounded-xl', color)}>
        <Icon className="w-6 h-6 text-white" />
      </div>
      <div>
        <p className="text-3xl font-bold text-gray-900 dark:text-white">{value}</p>
        <p className="text-sm text-gray-500 dark:text-slate-400">{label}</p>
      </div>
    </div>
  );
}

export default function OperatorWorkspace() {
  const { t } = useTranslation();

  const { data, isLoading, error } = useQuery<OperatorRemediationQueue>({
    queryKey: ['operator-queue'],
    queryFn: () => remediationApi.getOperatorQueue(),
  });

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-8 bg-gray-200 dark:bg-slate-700 rounded w-1/3" />
          <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
            {[1, 2, 3, 4, 5].map((i) => (
              <div key={i} className="h-28 bg-gray-200 dark:bg-slate-700 rounded" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6">
        <p className="text-red-600 dark:text-red-400">{t('workspace.load_error') || 'Failed to load queue data.'}</p>
      </div>
    );
  }

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
        {t('workspace.operator_title') || 'Remediation Queue'}
      </h1>
      <p className="text-gray-500 dark:text-slate-400">
        {t('workspace.operator_description') || 'Overview of your active remediation operations.'}
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        <QueueCard
          label={t('workspace.active_rfqs') || 'Active RFQs'}
          value={data.active_rfqs}
          icon={FileText}
          color="bg-blue-500"
        />
        <QueueCard
          label={t('workspace.quotes_received') || 'Quotes Received'}
          value={data.quotes_received}
          icon={MessageSquare}
          color="bg-purple-500"
        />
        <QueueCard
          label={t('workspace.awards_pending') || 'Awards Pending'}
          value={data.awards_pending}
          icon={Award}
          color="bg-amber-500"
        />
        <QueueCard
          label={t('workspace.completions_awaiting') || 'Completions Awaiting'}
          value={data.completions_awaiting}
          icon={ClipboardCheck}
          color="bg-green-500"
        />
        <QueueCard
          label={t('workspace.post_works_open') || 'Post-Works Open'}
          value={data.post_works_open}
          icon={Wrench}
          color="bg-orange-500"
        />
      </div>
    </div>
  );
}
