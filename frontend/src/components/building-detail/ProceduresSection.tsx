import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { permitProceduresApi } from '@/api/permitProcedures';
import type { Procedure } from '@/api/permitProcedures';
import ProcedureCard from './ProcedureCard';
import { Loader2, AlertTriangle, ClipboardList } from 'lucide-react';

interface ProceduresSectionProps {
  buildingId: string;
}

export default function ProceduresSection({ buildingId }: ProceduresSectionProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const {
    data: procedures = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-procedures', buildingId],
    queryFn: () => permitProceduresApi.getProcedures(buildingId),
    enabled: !!buildingId,
  });

  const { data: blockers = [] } = useQuery({
    queryKey: ['building-procedural-blockers', buildingId],
    queryFn: () => permitProceduresApi.getProceduralBlockers(buildingId),
    enabled: !!buildingId,
  });

  const submitMutation = useMutation({
    mutationFn: (id: string) => permitProceduresApi.submitProcedure(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-procedures', buildingId] });
    },
  });

  const respondMutation = useMutation({
    mutationFn: ({ requestId, text }: { requestId: string; text: string }) =>
      permitProceduresApi.respondToRequest(requestId, { response_text: text }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-procedures', buildingId] });
    },
  });

  const handleSubmit = (id: string) => submitMutation.mutate(id);
  const handleRespond = (requestId: string, text: string) => respondMutation.mutate({ requestId, text });

  // Sort: complement_requested first, then submitted, then under_review, then rest
  const statusPriority: Record<string, number> = {
    complement_requested: 0,
    submitted: 1,
    under_review: 2,
    draft: 3,
    approved: 4,
    rejected: 5,
    expired: 6,
    withdrawn: 7,
  };

  const sorted = [...procedures].sort(
    (a, b) => (statusPriority[a.status] ?? 9) - (statusPriority[b.status] ?? 9),
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-700 dark:text-red-300 flex items-center gap-2">
        <AlertTriangle className="w-4 h-4 flex-shrink-0" />
        {t('procedure.load_error') || 'Failed to load procedures.'}
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="procedures-section">
      {/* Blocker banner */}
      {blockers.length > 0 && (
        <div
          className="p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
          data-testid="procedural-blockers-banner"
        >
          <div className="flex items-center gap-2 text-sm font-medium text-red-700 dark:text-red-300 mb-1">
            <AlertTriangle className="w-4 h-4" />
            {t('procedure.blockers_title') || 'Procedural blockers'}
          </div>
          <ul className="text-xs text-red-600 dark:text-red-400 space-y-0.5 ml-6 list-disc">
            {blockers.map((b) => (
              <li key={b.procedure_id}>
                {b.procedure_title} — {b.authority_name} ({b.status.replace(/_/g, ' ')})
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Heading */}
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('procedure.title') || 'Procedures'}
        </h3>
      </div>

      {/* List */}
      {sorted.length === 0 ? (
        <div className="text-center py-8 text-gray-500 dark:text-slate-400">
          <ClipboardList className="w-10 h-10 mx-auto mb-3 opacity-40" />
          <p className="text-sm">{t('procedure.empty') || 'No procedures for this building.'}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {sorted.map((proc: Procedure) => (
            <ProcedureCard
              key={proc.id}
              procedure={proc}
              onSubmit={handleSubmit}
              onRespondToRequest={handleRespond}
            />
          ))}
        </div>
      )}
    </div>
  );
}
