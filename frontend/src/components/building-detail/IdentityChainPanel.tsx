import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { identityChainApi } from '@/api/identityChain';
import type { IdentityChainResponse, RdppfRestriction } from '@/api/identityChain';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Loader2,
  MapPin,
  Hash,
  FileText,
  Shield,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
} from 'lucide-react';

interface IdentityChainPanelProps {
  buildingId: string;
}

type StepStatus = 'resolved' | 'missing' | 'skipped';

function getStepStatus(value: unknown): StepStatus {
  if (value !== null && value !== undefined) return 'resolved';
  return 'missing';
}

function StepIcon({ status }: { status: StepStatus }) {
  if (status === 'resolved') return <CheckCircle2 className="h-5 w-5 text-emerald-500" />;
  if (status === 'skipped') return <XCircle className="h-5 w-5 text-gray-400 dark:text-gray-500" />;
  return <HelpCircle className="h-5 w-5 text-amber-500" />;
}

function StepConnector({ status }: { status: StepStatus }) {
  return (
    <div
      className={cn(
        'h-0.5 w-8 mx-1',
        status === 'resolved' ? 'bg-emerald-400 dark:bg-emerald-600' : 'bg-gray-300 dark:bg-gray-600'
      )}
    />
  );
}

function formatDate(iso: string | null): string {
  if (!iso) return '-';
  try {
    return new Date(iso).toLocaleDateString('fr-CH', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
}

function formatConfidence(confidence: number | null): string {
  if (confidence === null || confidence === undefined) return '-';
  return `${Math.round(confidence * 100)}%`;
}

export default function IdentityChainPanel({ buildingId }: IdentityChainPanelProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [resolving, setResolving] = useState(false);
  const [showRdppf, setShowRdppf] = useState(false);

  const { data, isLoading, error } = useQuery<IdentityChainResponse>({
    queryKey: ['identity-chain', buildingId],
    queryFn: () => identityChainApi.get(buildingId),
    staleTime: 5 * 60 * 1000,
    retry: 1,
  });

  const handleResolve = async () => {
    setResolving(true);
    try {
      await identityChainApi.resolve(buildingId);
      await queryClient.invalidateQueries({ queryKey: ['identity-chain', buildingId] });
    } catch {
      // Error handled by UI state
    } finally {
      setResolving(false);
    }
  };

  if (isLoading) {
    return (
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
        <div className="flex items-center gap-2 text-gray-500 dark:text-gray-400">
          <Loader2 className="h-4 w-4 animate-spin" />
          {t('identity_chain.loading') || 'Chargement de la chaine d\'identite...'}
        </div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 text-red-500 dark:text-red-400">
            <AlertTriangle className="h-4 w-4" />
            {t('identity_chain.error') || 'Chaine d\'identite non disponible'}
          </div>
          <button
            onClick={handleResolve}
            disabled={resolving}
            className="flex items-center gap-1.5 text-sm text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', resolving && 'animate-spin')} />
            {t('identity_chain.resolve') || 'Resoudre'}
          </button>
        </div>
      </div>
    );
  }

  const egidStatus = getStepStatus(data.egid?.value);
  const egridStatus = getStepStatus(data.egrid?.value);
  const rdppfStatus = (data.rdppf?.restrictions?.length ?? 0) > 0 || (data.rdppf?.themes?.length ?? 0) > 0
    ? 'resolved' as StepStatus
    : data.egrid?.value
      ? 'missing' as StepStatus
      : 'skipped' as StepStatus;

  const restrictions: RdppfRestriction[] = data.rdppf?.restrictions ?? [];

  return (
    <div className="rounded-xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 p-6 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-indigo-500 dark:text-indigo-400" />
          <h3 className="text-base font-semibold text-gray-900 dark:text-white">
            {t('identity_chain.title') || 'Chaine d\'identite cadastrale'}
          </h3>
          {data.chain_complete && (
            <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-emerald-100 dark:bg-emerald-900/30 px-2 py-0.5 text-xs font-medium text-emerald-700 dark:text-emerald-400">
              <CheckCircle2 className="h-3 w-3" />
              {t('identity_chain.complete') || 'Complete'}
            </span>
          )}
        </div>
        <button
          onClick={handleResolve}
          disabled={resolving}
          className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-blue-900/20 transition-colors"
        >
          <RefreshCw className={cn('h-3.5 w-3.5', resolving && 'animate-spin')} />
          {t('identity_chain.resolve') || 'Resoudre la chaine'}
        </button>
      </div>

      {/* Chain Diagram */}
      <div className="flex items-center justify-center gap-0 py-3">
        {/* Address */}
        <div className="flex flex-col items-center gap-1">
          <MapPin className="h-5 w-5 text-blue-500 dark:text-blue-400" />
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">
            {t('identity_chain.address') || 'Adresse'}
          </span>
          <CheckCircle2 className="h-4 w-4 text-emerald-500" />
        </div>

        <StepConnector status={egidStatus} />

        {/* EGID */}
        <div className="flex flex-col items-center gap-1">
          <Hash className="h-5 w-5 text-violet-500 dark:text-violet-400" />
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">EGID</span>
          <StepIcon status={egidStatus} />
        </div>

        <StepConnector status={egridStatus} />

        {/* EGRID */}
        <div className="flex flex-col items-center gap-1">
          <FileText className="h-5 w-5 text-orange-500 dark:text-orange-400" />
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">EGRID</span>
          <StepIcon status={egridStatus} />
        </div>

        <StepConnector status={rdppfStatus} />

        {/* RDPPF */}
        <div className="flex flex-col items-center gap-1">
          <Shield className="h-5 w-5 text-red-500 dark:text-red-400" />
          <span className="text-xs font-medium text-gray-700 dark:text-gray-300">RDPPF</span>
          <StepIcon status={rdppfStatus} />
        </div>
      </div>

      {/* Chain Gaps */}
      {data.chain_gaps.length > 0 && (
        <div className="rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 p-3">
          <div className="flex items-start gap-2">
            <AlertTriangle className="h-4 w-4 text-amber-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-amber-800 dark:text-amber-300">
                {t('identity_chain.gaps_title') || 'Elements non resolus'}
              </p>
              <ul className="mt-1 text-xs text-amber-700 dark:text-amber-400 space-y-0.5">
                {data.chain_gaps.map((gap) => (
                  <li key={gap}>- {gap.replace(/_/g, ' ')}</li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      )}

      {/* Details Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* EGID Detail */}
        <div className="rounded-lg bg-gray-50 dark:bg-gray-750 p-3 space-y-1.5">
          <div className="flex items-center gap-1.5">
            <Hash className="h-4 w-4 text-violet-500" />
            <span className="text-sm font-medium text-gray-900 dark:text-white">EGID</span>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400 space-y-0.5">
            <p>
              <span className="text-gray-500 dark:text-gray-500">{t('identity_chain.value') || 'Valeur'}:</span>{' '}
              <span className="font-mono font-medium text-gray-900 dark:text-white">
                {data.egid?.value ?? '-'}
              </span>
            </p>
            <p>
              <span className="text-gray-500 dark:text-gray-500">{t('identity_chain.source') || 'Source'}:</span>{' '}
              {data.egid?.source ?? '-'}
            </p>
            <p>
              <span className="text-gray-500 dark:text-gray-500">{t('identity_chain.confidence') || 'Confiance'}:</span>{' '}
              {formatConfidence(data.egid?.confidence ?? null)}
            </p>
            <p>
              <span className="text-gray-500 dark:text-gray-500">{t('identity_chain.resolved_at') || 'Resolu le'}:</span>{' '}
              {formatDate(data.egid?.resolved_at ?? null)}
            </p>
          </div>
        </div>

        {/* EGRID Detail */}
        <div className="rounded-lg bg-gray-50 dark:bg-gray-750 p-3 space-y-1.5">
          <div className="flex items-center gap-1.5">
            <FileText className="h-4 w-4 text-orange-500" />
            <span className="text-sm font-medium text-gray-900 dark:text-white">EGRID</span>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400 space-y-0.5">
            <p>
              <span className="text-gray-500 dark:text-gray-500">{t('identity_chain.value') || 'Valeur'}:</span>{' '}
              <span className="font-mono font-medium text-gray-900 dark:text-white">
                {data.egrid?.value ?? '-'}
              </span>
            </p>
            <p>
              <span className="text-gray-500 dark:text-gray-500">{t('identity_chain.parcel') || 'Parcelle'}:</span>{' '}
              {data.egrid?.parcel_number ?? '-'}
            </p>
            <p>
              <span className="text-gray-500 dark:text-gray-500">{t('identity_chain.area') || 'Surface'}:</span>{' '}
              {data.egrid?.area_m2 != null ? `${data.egrid.area_m2} m\u00B2` : '-'}
            </p>
            <p>
              <span className="text-gray-500 dark:text-gray-500">{t('identity_chain.resolved_at') || 'Resolu le'}:</span>{' '}
              {formatDate(data.egrid?.resolved_at ?? null)}
            </p>
          </div>
        </div>

        {/* RDPPF Summary */}
        <div className="rounded-lg bg-gray-50 dark:bg-gray-750 p-3 space-y-1.5">
          <div className="flex items-center gap-1.5">
            <Shield className="h-4 w-4 text-red-500" />
            <span className="text-sm font-medium text-gray-900 dark:text-white">RDPPF</span>
          </div>
          <div className="text-sm text-gray-600 dark:text-gray-400 space-y-0.5">
            <p>
              <span className="text-gray-500 dark:text-gray-500">{t('identity_chain.restrictions') || 'Restrictions'}:</span>{' '}
              <span className="font-medium text-gray-900 dark:text-white">{restrictions.length}</span>
            </p>
            <p>
              <span className="text-gray-500 dark:text-gray-500">{t('identity_chain.themes') || 'Themes'}:</span>{' '}
              {(data.rdppf?.themes?.length ?? 0) > 0 ? data.rdppf.themes.join(', ') : '-'}
            </p>
            <p>
              <span className="text-gray-500 dark:text-gray-500">{t('identity_chain.resolved_at') || 'Resolu le'}:</span>{' '}
              {formatDate(data.rdppf?.resolved_at ?? null)}
            </p>
          </div>
        </div>
      </div>

      {/* RDPPF Restrictions Expandable */}
      {restrictions.length > 0 && (
        <div className="border-t border-gray-200 dark:border-gray-700 pt-3">
          <button
            onClick={() => setShowRdppf(!showRdppf)}
            className="flex items-center gap-1.5 text-sm font-medium text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            {showRdppf ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
            {t('identity_chain.rdppf_details') || 'Details des restrictions RDPPF'}{' '}
            <span className="text-gray-400">({restrictions.length})</span>
          </button>
          {showRdppf && (
            <div className="mt-3 space-y-2">
              {restrictions.map((r, idx) => (
                <div
                  key={idx}
                  className="rounded-lg border border-gray-200 dark:border-gray-600 p-3 text-sm"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="font-medium text-gray-900 dark:text-white">{r.description || r.type}</p>
                      <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                        {r.type} {r.authority ? `\u2014 ${r.authority}` : ''}
                      </p>
                    </div>
                    {r.in_force_since && (
                      <span className="text-xs text-gray-400 dark:text-gray-500 whitespace-nowrap">
                        {r.in_force_since}
                      </span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
