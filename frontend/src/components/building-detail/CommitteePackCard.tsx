import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn, formatDate } from '@/utils/formatters';
import { publicSectorApi, type CommitteePackData, type DecisionTraceData } from '@/api/publicSector';
import { Users, Plus, Loader2, ChevronDown, ChevronUp, Gavel, Clock, FileCheck2 } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  submitted: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  under_review: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  decided: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  archived: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
};

const DECISION_COLORS: Record<string, string> = {
  approved: 'text-green-700 dark:text-green-400',
  rejected: 'text-red-700 dark:text-red-400',
  deferred: 'text-yellow-700 dark:text-yellow-400',
  modified: 'text-blue-700 dark:text-blue-400',
  abstained: 'text-gray-500 dark:text-slate-400',
};

const DECISIONS = ['approved', 'rejected', 'deferred', 'modified', 'abstained'] as const;

interface CommitteePackCardProps {
  buildingId: string;
}

export function CommitteePackCard({ buildingId }: CommitteePackCardProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [expandedClausePack, setExpandedClausePack] = useState<string | null>(null);
  const [showDecisionForm, setShowDecisionForm] = useState<string | null>(null);
  const [decisionForm, setDecisionForm] = useState({
    reviewer_name: '',
    decision: 'approved' as string,
    conditions: '',
    notes: '',
  });

  const {
    data: packs = [],
    isLoading,
    isError,
  } = useQuery<CommitteePackData[]>({
    queryKey: ['committee-packs', buildingId],
    queryFn: () => publicSectorApi.listCommitteePacks(buildingId),
    enabled: !!buildingId,
    retry: false,
  });

  const generateMutation = useMutation({
    mutationFn: () =>
      publicSectorApi.generateCommitteePack(buildingId, {
        committee_name: 'Building Committee',
        committee_type: 'building_committee',
      }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['committee-packs', buildingId] }),
  });

  const decideMutation = useMutation({
    mutationFn: (packId: string) =>
      publicSectorApi.recordDecision(packId, {
        ...decisionForm,
        decided_at: new Date().toISOString(),
        conditions: decisionForm.conditions || undefined,
        notes: decisionForm.notes || undefined,
      }),
    onSuccess: (_, packId) => {
      setShowDecisionForm(null);
      setDecisionForm({ reviewer_name: '', decision: 'approved', conditions: '', notes: '' });
      queryClient.invalidateQueries({ queryKey: ['committee-packs', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['decision-traces', 'committee', packId] });
    },
  });

  if (isError) return null;

  return (
    <div
      className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5"
      data-testid="committee-pack-card"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Users className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t('public_sector.committee_packs_title')}
          </h3>
        </div>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          data-testid="generate-committee-pack-button"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
        >
          {generateMutation.isPending ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Plus className="w-3.5 h-3.5" />
          )}
          {t('public_sector.generate_committee_pack')}
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-gray-500 dark:text-slate-400 py-4">
          <Loader2 className="w-4 h-4 animate-spin" />
          {t('app.loading')}
        </div>
      )}

      {!isLoading && packs.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-slate-400" data-testid="committee-pack-empty">
          {t('public_sector.no_committee_packs')}
        </p>
      )}

      {packs.length > 0 && (
        <div className="space-y-4">
          {packs.map((pack) => (
            <div
              key={pack.id}
              className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3"
              data-testid="committee-pack-item"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-white" data-testid="committee-name">
                    {pack.committee_name}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-slate-400">
                    ({t(`public_sector.committee_type.${pack.committee_type}`) || pack.committee_type})
                  </span>
                  <span
                    className={cn(
                      'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
                      STATUS_COLORS[pack.status] || STATUS_COLORS.draft,
                    )}
                    data-testid="committee-pack-status"
                  >
                    {t(`public_sector.status.${pack.status}`) || pack.status}
                  </span>
                </div>
              </div>

              <div className="flex flex-wrap gap-3 text-xs text-gray-500 dark:text-slate-400 mb-2">
                {pack.decision_deadline && (
                  <span className="flex items-center gap-1" data-testid="committee-deadline">
                    <Clock className="w-3 h-3" />
                    {t('public_sector.decision_deadline')}: {pack.decision_deadline}
                  </span>
                )}
              </div>

              {/* Procurement clauses (collapsible) */}
              {pack.procurement_clauses && pack.procurement_clauses.length > 0 && (
                <div className="mt-2">
                  <button
                    onClick={() => setExpandedClausePack(expandedClausePack === pack.id ? null : pack.id)}
                    className="flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-slate-300 hover:text-gray-800 dark:hover:text-slate-100"
                    data-testid="toggle-clauses"
                  >
                    <FileCheck2 className="w-3 h-3" />
                    {t('public_sector.procurement_clauses')} ({pack.procurement_clauses.length})
                    {expandedClausePack === pack.id ? (
                      <ChevronUp className="w-3 h-3" />
                    ) : (
                      <ChevronDown className="w-3 h-3" />
                    )}
                  </button>
                  {expandedClausePack === pack.id && (
                    <ul className="mt-1 space-y-1 ml-4" data-testid="clauses-list">
                      {pack.procurement_clauses.map((c, i) => (
                        <li key={i} className="text-xs text-gray-600 dark:text-slate-300">
                          {c.clause || JSON.stringify(c)}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

              {/* Record Decision button */}
              <div className="mt-3 flex items-center gap-2">
                <button
                  onClick={() => setShowDecisionForm(showDecisionForm === pack.id ? null : pack.id)}
                  className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded"
                  data-testid="record-decision-button"
                >
                  <Gavel className="w-3 h-3" />
                  {t('public_sector.record_decision')}
                </button>
              </div>

              {/* Inline Decision Form */}
              {showDecisionForm === pack.id && (
                <div
                  className="mt-3 p-3 bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-600 space-y-2"
                  data-testid="decision-form"
                >
                  <input
                    type="text"
                    placeholder={t('public_sector.reviewer_name')}
                    value={decisionForm.reviewer_name}
                    onChange={(e) => setDecisionForm({ ...decisionForm, reviewer_name: e.target.value })}
                    data-testid="decision-reviewer-name"
                    className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 dark:text-white"
                  />
                  <select
                    value={decisionForm.decision}
                    onChange={(e) => setDecisionForm({ ...decisionForm, decision: e.target.value })}
                    data-testid="decision-select"
                    className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 dark:text-white"
                  >
                    {DECISIONS.map((d) => (
                      <option key={d} value={d}>
                        {t(`public_sector.decision.${d}`) || d}
                      </option>
                    ))}
                  </select>
                  <input
                    type="text"
                    placeholder={t('public_sector.conditions')}
                    value={decisionForm.conditions}
                    onChange={(e) => setDecisionForm({ ...decisionForm, conditions: e.target.value })}
                    data-testid="decision-conditions"
                    className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 dark:text-white"
                  />
                  <textarea
                    placeholder={t('public_sector.notes')}
                    value={decisionForm.notes}
                    onChange={(e) => setDecisionForm({ ...decisionForm, notes: e.target.value })}
                    data-testid="decision-notes"
                    className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-slate-600 rounded bg-white dark:bg-slate-700 dark:text-white"
                    rows={2}
                  />
                  <div className="flex justify-end gap-2">
                    <button
                      onClick={() => setShowDecisionForm(null)}
                      className="px-2 py-1 text-xs text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-700 rounded"
                    >
                      {t('form.cancel')}
                    </button>
                    <button
                      onClick={() => decideMutation.mutate(pack.id)}
                      disabled={decideMutation.isPending || !decisionForm.reviewer_name}
                      data-testid="submit-decision-button"
                      className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-white bg-red-600 rounded hover:bg-red-700 disabled:bg-red-400"
                    >
                      {decideMutation.isPending && <Loader2 className="w-3 h-3 animate-spin" />}
                      {t('form.save')}
                    </button>
                  </div>
                </div>
              )}

              {/* Decision Traces */}
              <DecisionTracesList packId={pack.id} />
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function DecisionTracesList({ packId }: { packId: string }) {
  const { t } = useTranslation();

  const { data: traces = [] } = useQuery<DecisionTraceData[]>({
    queryKey: ['decision-traces', 'committee', packId],
    queryFn: () => publicSectorApi.listDecisionTraces('committee', packId),
    enabled: !!packId,
    retry: false,
  });

  if (traces.length === 0) return null;

  return (
    <div className="mt-3 border-t border-gray-200 dark:border-slate-600 pt-2" data-testid="decision-traces-list">
      <span className="text-xs font-medium text-gray-600 dark:text-slate-300 block mb-1">
        {t('public_sector.decision_traces')}
      </span>
      <div className="space-y-1">
        {traces.map((trace) => (
          <div key={trace.id} className="flex items-center gap-2 text-xs" data-testid="decision-trace-item">
            <Gavel className="w-3 h-3 text-gray-400" />
            <span className="font-medium text-gray-700 dark:text-slate-200">{trace.reviewer_name}</span>
            <span className={cn('font-medium', DECISION_COLORS[trace.decision] || DECISION_COLORS.abstained)}>
              {t(`public_sector.decision.${trace.decision}`) || trace.decision}
            </span>
            <span className="text-gray-400 dark:text-slate-500">{formatDate(trace.decided_at)}</span>
            {trace.conditions && (
              <span className="text-gray-500 dark:text-slate-400 truncate max-w-[200px]" title={trace.conditions}>
                ({trace.conditions})
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

export default CommitteePackCard;
