import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { artifactCustodyApi, type ArchivePosture as ArchivePostureData } from '@/api/artifactCustody';
import { formatDate } from '@/utils/formatters';
import { Archive, CheckCircle2, Clock, FileCheck, Layers, ShieldCheck } from 'lucide-react';

interface ArchivePostureProps {
  buildingId: string;
}

export function ArchivePosture({ buildingId }: ArchivePostureProps) {
  const { t } = useTranslation();
  const { data, isLoading, isError } = useQuery<ArchivePostureData>({
    queryKey: ['archive-posture', buildingId],
    queryFn: () => artifactCustodyApi.getArchivePosture(buildingId),
    retry: false,
    staleTime: 60_000,
  });

  if (isLoading) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4 animate-pulse">
        <div className="h-4 bg-gray-200 dark:bg-slate-700 rounded w-1/3 mb-3" />
        <div className="h-3 bg-gray-200 dark:bg-slate-700 rounded w-2/3" />
      </div>
    );
  }

  if (isError || !data) return null;

  const allTraceable = data.total_artifacts > 0 && data.withdrawn_count === 0;

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Archive className="w-4 h-4 text-gray-500 dark:text-slate-400" />
        <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
          {t('artifact_custody.archive_posture') || 'Archive Posture'}
        </h3>
        {allTraceable && (
          <span className="ml-auto inline-flex items-center gap-1 text-xs font-medium text-green-700 dark:text-green-400 bg-green-100 dark:bg-green-900/30 px-2 py-0.5 rounded-full">
            <ShieldCheck className="w-3 h-3" />
            {t('artifact_custody.all_traceable') || 'All traceable'}
          </span>
        )}
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-center">
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-2">
          <Layers className="w-4 h-4 mx-auto mb-1 text-blue-500" />
          <p className="text-lg font-bold text-gray-900 dark:text-white">{data.total_artifacts}</p>
          <p className="text-[10px] text-gray-500 dark:text-slate-400">
            {t('artifact_custody.artifacts') || 'Artifacts'}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-2">
          <FileCheck className="w-4 h-4 mx-auto mb-1 text-green-500" />
          <p className="text-lg font-bold text-gray-900 dark:text-white">{data.current_count}</p>
          <p className="text-[10px] text-gray-500 dark:text-slate-400">{t('artifact_custody.current') || 'Current'}</p>
        </div>
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-2">
          <CheckCircle2 className="w-4 h-4 mx-auto mb-1 text-gray-400" />
          <p className="text-lg font-bold text-gray-900 dark:text-white">{data.superseded_count}</p>
          <p className="text-[10px] text-gray-500 dark:text-slate-400">
            {t('artifact_custody.superseded') || 'Superseded'}
          </p>
        </div>
        <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-2">
          <Archive className="w-4 h-4 mx-auto mb-1 text-amber-500" />
          <p className="text-lg font-bold text-gray-900 dark:text-white">{data.archived_count}</p>
          <p className="text-[10px] text-gray-500 dark:text-slate-400">
            {t('artifact_custody.archived') || 'Archived'}
          </p>
        </div>
      </div>

      {data.last_custody_event && (
        <div className="mt-3 flex items-center gap-1 text-xs text-gray-500 dark:text-slate-400">
          <Clock className="w-3 h-3" />
          <span>
            {t('artifact_custody.last_event') || 'Last event'}: {data.last_custody_event.event_type} &mdash;{' '}
            {formatDate(data.last_custody_event.occurred_at)}
          </span>
        </div>
      )}
    </div>
  );
}

export default ArchivePosture;
