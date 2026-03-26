import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { intelligenceApi } from '@/api/intelligence';
import type { MemoryTransfer } from '@/api/intelligence';
import {
  Loader2,
  CheckCircle2,
  XCircle,
  ArrowRightLeft,
  ShieldCheck,
  FileText,
  Users,
  Clock,
  Plus,
  X,
} from 'lucide-react';
import { formatDate } from '@/utils/formatters';

interface MemoryTransferViewProps {
  buildingId: string;
}

const TRANSFER_TYPES = [
  { value: 'sale', labelKey: 'memory_transfer.type_sale' },
  { value: 'refinancing', labelKey: 'memory_transfer.type_refinancing' },
  { value: 'management_change', labelKey: 'memory_transfer.type_management_change' },
  { value: 'new_works_cycle', labelKey: 'memory_transfer.type_new_works_cycle' },
];

function ContinuityGauge({ score, label }: { score: number; label: string }) {
  const pct = Math.round(Math.min(100, Math.max(0, score)));
  const getColor = (v: number) => {
    if (v >= 80) return 'text-emerald-500';
    if (v >= 50) return 'text-yellow-500';
    return 'text-red-500';
  };

  return (
    <div className="flex flex-col items-center gap-2">
      <div className="relative w-28 h-28">
        <svg className="w-28 h-28 -rotate-90" viewBox="0 0 100 100">
          <circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            className="text-slate-200 dark:text-slate-700"
          />
          <circle
            cx="50"
            cy="50"
            r="42"
            fill="none"
            stroke="currentColor"
            strokeWidth="8"
            strokeDasharray={`${pct * 2.64} ${264 - pct * 2.64}`}
            strokeLinecap="round"
            className={getColor(pct)}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className={cn('text-2xl font-black', getColor(pct))}>{pct}</span>
        </div>
      </div>
      <span className="text-xs font-medium text-slate-600 dark:text-slate-400 text-center">{label}</span>
    </div>
  );
}

function TransferTimelineItem({ transfer }: { transfer: MemoryTransfer }) {
  const { t } = useTranslation();
  const isCompleted = transfer.status === 'completed';
  const isPending = transfer.status === 'pending' || transfer.status === 'in_progress';

  return (
    <div className="flex gap-3" data-testid={`transfer-${transfer.id}`}>
      {/* Timeline dot + line */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            'w-3 h-3 rounded-full border-2 shrink-0',
            isCompleted
              ? 'bg-emerald-500 border-emerald-500'
              : isPending
                ? 'bg-yellow-500 border-yellow-500'
                : 'bg-slate-300 dark:bg-slate-600 border-slate-300 dark:border-slate-600',
          )}
        />
        <div className="w-0.5 flex-1 bg-slate-200 dark:bg-slate-700 min-h-[24px]" />
      </div>

      {/* Content */}
      <div className="pb-4 flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-semibold text-slate-900 dark:text-white">{transfer.transfer_label}</span>
          <span
            className={cn(
              'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold',
              isCompleted
                ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400'
                : isPending
                  ? 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
                  : 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-400',
            )}
          >
            {transfer.status}
          </span>
        </div>

        <p className="text-[11px] text-slate-500 dark:text-slate-400 mt-0.5">
          {formatDate(transfer.initiated_at)}
          {transfer.completed_at && ` \u2192 ${formatDate(transfer.completed_at)}`}
        </p>

        {/* Stats row */}
        <div className="flex flex-wrap gap-3 mt-2">
          <div className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
            <FileText className="w-3 h-3" />
            {transfer.sections_count} {t('memory_transfer.sections') || 'sections'}
          </div>
          <div className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
            <FileText className="w-3 h-3" />
            {transfer.documents_count} {t('memory_transfer.documents') || 'documents'}
          </div>
          <div className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
            <Users className="w-3 h-3" />
            {transfer.engagements_count} {t('memory_transfer.engagements') || 'engagements'}
          </div>
          <div className="flex items-center gap-1 text-[11px] text-slate-500 dark:text-slate-400">
            <Clock className="w-3 h-3" />
            {transfer.timeline_events_count} {t('memory_transfer.events') || 'evenements'}
          </div>
        </div>

        {/* Integrity badge */}
        <div className="mt-1.5">
          {transfer.integrity_verified ? (
            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-emerald-700 dark:text-emerald-400">
              <ShieldCheck className="w-3 h-3" /> SHA-256 {t('memory_transfer.verified') || 'verifie'}
            </span>
          ) : (
            <span className="inline-flex items-center gap-1 text-[10px] font-medium text-amber-700 dark:text-amber-400">
              <XCircle className="w-3 h-3" /> {t('memory_transfer.not_verified') || 'Non verifie'}
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function MemoryTransferView({ buildingId }: MemoryTransferViewProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [showInitiate, setShowInitiate] = useState(false);
  const [transferType, setTransferType] = useState('sale');
  const [toOrgId, setToOrgId] = useState('');

  const { data: continuity, isLoading: continuityLoading } = useQuery({
    queryKey: ['continuity-score', buildingId],
    queryFn: () => intelligenceApi.getContinuityScore(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const { data: readiness, isLoading: readinessLoading } = useQuery({
    queryKey: ['transfer-readiness', buildingId],
    queryFn: () => intelligenceApi.getTransferReadiness(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const {
    data: transfers,
    isLoading: transfersLoading,
    isError: transfersError,
  } = useQuery({
    queryKey: ['transfer-history', buildingId],
    queryFn: () => intelligenceApi.getTransferHistory(buildingId),
    retry: false,
    staleTime: 5 * 60 * 1000,
  });

  const initiateMutation = useMutation({
    mutationFn: (data: { transfer_type: string; to_org_id?: string }) =>
      intelligenceApi.initiateTransfer(buildingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['transfer-history', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['continuity-score', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['transfer-readiness', buildingId] });
      setShowInitiate(false);
      setTransferType('sale');
      setToOrgId('');
    },
  });

  const isLoading = continuityLoading || readinessLoading || transfersLoading;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 animate-spin text-red-600" />
      </div>
    );
  }

  if (transfersError) return null;

  const yearsOfMemory = continuity
    ? Math.floor(continuity.transfers_completed > 0 ? (continuity.coverage_pct / 100) * 10 : 0)
    : 0;

  return (
    <div className="space-y-5" data-testid="memory-transfer-view">
      {/* Section header */}
      <div className="flex items-center gap-2">
        <ArrowRightLeft className="w-5 h-5 text-red-600" />
        <h2 className="text-lg font-bold text-slate-900 dark:text-white flex-1">
          {t('memory_transfer.title') || 'Memoire transferable'}
        </h2>
        <button
          onClick={() => setShowInitiate(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors border border-red-200 dark:border-red-800"
        >
          <Plus className="w-3.5 h-3.5" />
          {t('memory_transfer.initiate_button') || 'Initier un transfert'}
        </button>
      </div>

      {/* Continuity score + readiness */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Continuity gauge */}
        {continuity && (
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 flex flex-col items-center space-y-3">
            <ContinuityGauge
              score={continuity.score}
              label={t('memory_transfer.continuity_score') || 'Score de continuite'}
            />
            <div className="grid grid-cols-2 gap-4 w-full mt-2">
              <div className="text-center">
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  {t('memory_transfer.coverage') || 'Couverture'}
                </p>
                <p className="text-lg font-bold text-slate-800 dark:text-slate-200">
                  {Math.round(continuity.coverage_pct)}%
                </p>
              </div>
              <div className="text-center">
                <p className="text-[11px] text-slate-500 dark:text-slate-400">
                  {t('memory_transfer.integrity') || 'Integrite'}
                </p>
                <p className="text-lg font-bold text-slate-800 dark:text-slate-200">
                  {Math.round(continuity.integrity_pct)}%
                </p>
              </div>
            </div>
            {continuity.transfers_completed > 0 && (
              <p className="text-xs text-slate-600 dark:text-slate-400 text-center">
                {t('memory_transfer.years_message') || 'Ce batiment possede'} {yearsOfMemory}{' '}
                {t('memory_transfer.years_suffix') || 'ans de memoire continue'}
              </p>
            )}
            {continuity.gaps > 0 && (
              <p className="text-[11px] text-amber-600 dark:text-amber-400">
                {continuity.gaps} {t('memory_transfer.gaps') || 'lacunes detectees'}
              </p>
            )}
          </div>
        )}

        {/* Transfer readiness checklist */}
        {readiness && (
          <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5 space-y-3">
            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">
              {t('memory_transfer.readiness_title') || 'Pret au transfert'}
            </h3>
            <div className="flex items-center gap-2 mb-2">
              {readiness.ready ? (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {t('memory_transfer.ready') || 'Pret'}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 border border-red-200 dark:border-red-800">
                  <XCircle className="w-3.5 h-3.5" />
                  {t('memory_transfer.not_ready') || 'Non pret'}
                </span>
              )}
            </div>

            <ul className="space-y-2">
              {(readiness.missing_sections || []).length === 0 ? (
                <li className="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400">
                  <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                  {t('memory_transfer.all_sections_complete') || 'Toutes les sections completes'}
                </li>
              ) : (
                (readiness.missing_sections || []).map((section, i) => (
                  <li key={i} className="flex items-center gap-2 text-xs text-red-700 dark:text-red-400">
                    <XCircle className="w-3.5 h-3.5 shrink-0" />
                    {section}
                  </li>
                ))
              )}

              {readiness.open_gates > 0 && (
                <li className="flex items-center gap-2 text-xs text-red-700 dark:text-red-400">
                  <XCircle className="w-3.5 h-3.5 shrink-0" />
                  {readiness.open_gates} {t('memory_transfer.open_gates') || 'portes non liberees'}
                </li>
              )}

              {(readiness.incomplete_engagements || []).length > 0 && (
                <li className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400">
                  <XCircle className="w-3.5 h-3.5 shrink-0" />
                  {readiness.incomplete_engagements.length}{' '}
                  {t('memory_transfer.incomplete_engagements') || 'engagements incomplets'}
                </li>
              )}

              {readiness.documents_without_hash > 0 && (
                <li className="flex items-center gap-2 text-xs text-amber-700 dark:text-amber-400">
                  <XCircle className="w-3.5 h-3.5 shrink-0" />
                  {readiness.documents_without_hash} {t('memory_transfer.docs_without_hash') || 'documents sans hash'}
                </li>
              )}

              {readiness.documents_without_hash === 0 &&
                readiness.open_gates === 0 &&
                readiness.incomplete_engagements.length === 0 &&
                readiness.missing_sections.length === 0 && (
                  <li className="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400">
                    <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                    {t('memory_transfer.all_checks_passed') || 'Tous les controles passes'}
                  </li>
                )}
            </ul>
          </div>
        )}
      </div>

      {/* Transfer history timeline */}
      {transfers && transfers.length > 0 && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-5">
          <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">
            {t('memory_transfer.history_title') || 'Historique des transferts'}
          </h3>
          <div className="space-y-0">
            {transfers.map((transfer) => (
              <TransferTimelineItem key={transfer.id} transfer={transfer} />
            ))}
          </div>
        </div>
      )}

      {transfers && transfers.length === 0 && (
        <div className="rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 p-8 text-center">
          <ArrowRightLeft className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-2" />
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('memory_transfer.no_transfers') || 'Aucun transfert de memoire enregistre'}
          </p>
        </div>
      )}

      {/* Initiate transfer modal */}
      {showInitiate && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
          onClick={() => setShowInitiate(false)}
        >
          <div
            className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-700 shadow-xl p-6 w-full max-w-md mx-4 space-y-4"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-slate-900 dark:text-white">
                {t('memory_transfer.initiate_title') || 'Initier un transfert de memoire'}
              </h3>
              <button
                onClick={() => setShowInitiate(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('memory_transfer.transfer_type_label') || 'Type de transfert'}
                </label>
                <select
                  value={transferType}
                  onChange={(e) => setTransferType(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white"
                >
                  {TRANSFER_TYPES.map((tt) => (
                    <option key={tt.value} value={tt.value}>
                      {t(tt.labelKey) || tt.value}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-700 dark:text-slate-300 mb-1">
                  {t('memory_transfer.to_org_label') || 'Organisation destinataire (optionnel)'}
                </label>
                <input
                  type="text"
                  value={toOrgId}
                  onChange={(e) => setToOrgId(e.target.value)}
                  placeholder={t('memory_transfer.to_org_placeholder') || 'ID organisation...'}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-800 text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500"
                />
              </div>
            </div>

            <div className="flex gap-2 pt-2">
              <button
                onClick={() => {
                  initiateMutation.mutate({
                    transfer_type: transferType,
                    to_org_id: toOrgId.trim() || undefined,
                  });
                }}
                disabled={initiateMutation.isPending}
                className="flex-1 flex items-center justify-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 disabled:opacity-50 rounded-lg transition-colors"
              >
                {initiateMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : null}
                {t('memory_transfer.confirm_initiate') || 'Lancer le transfert'}
              </button>
              <button
                onClick={() => setShowInitiate(false)}
                className="px-4 py-2 text-sm font-medium text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
              >
                {t('form.cancel') || 'Annuler'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
