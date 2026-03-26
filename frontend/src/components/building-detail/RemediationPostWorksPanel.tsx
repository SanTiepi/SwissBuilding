import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { remediationPostWorksApi, type PostWorksLinkData } from '@/api/remediationPostWorks';
import { Loader2, AlertTriangle, CheckCircle2, Clock, Shield, TrendingUp, ArrowRight } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  drafted: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  review_required: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  finalized: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
        STATUS_COLORS[status] || STATUS_COLORS.pending,
      )}
    >
      {status.replace('_', ' ')}
    </span>
  );
}

function DeltaDisplay({
  label,
  delta,
  unit,
}: {
  label: string;
  delta: { before: unknown; after: unknown; change: unknown } | null;
  unit?: string;
}) {
  if (!delta) return null;
  const suffix = unit ? ` ${unit}` : '';
  return (
    <div className="bg-gray-50 dark:bg-slate-700 rounded-lg p-3">
      <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">{label}</p>
      <div className="flex items-center gap-2 text-sm">
        <span className="font-medium text-gray-900 dark:text-white">
          {String(delta.before)}
          {suffix}
        </span>
        <ArrowRight className="w-3 h-3 text-gray-400" />
        <span className="font-bold text-green-600 dark:text-green-400">
          {String(delta.after)}
          {suffix}
        </span>
        <span className="text-xs text-gray-500 dark:text-slate-400">({String(delta.change) || '0'})</span>
      </div>
    </div>
  );
}

function OutcomeCard({ outcome }: { outcome: PostWorksLinkData }) {
  const { t } = useTranslation();
  return (
    <div
      className="border border-gray-200 dark:border-slate-700 rounded-xl p-4 space-y-4"
      data-testid="remediation-outcome-card"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Shield className="w-5 h-5 text-red-600 dark:text-red-400" />
          <span className="text-sm font-medium text-gray-900 dark:text-white">
            {t('post_works.outcome') || 'Remediation Outcome'}
          </span>
        </div>
        <StatusBadge status={outcome.status} />
      </div>

      {/* Deltas */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <DeltaDisplay label={t('post_works.grade') || 'Grade'} delta={outcome.grade_delta} />
        <DeltaDisplay label={t('post_works.trust') || 'Trust'} delta={outcome.trust_delta} />
        <DeltaDisplay label={t('post_works.completeness') || 'Completeness'} delta={outcome.completeness_delta} />
      </div>

      {/* Residual risks */}
      {outcome.residual_risks && outcome.residual_risks.length > 0 && (
        <div>
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">
            {t('post_works.residual_risks') || 'Residual Risks'} ({outcome.residual_risks.length})
          </p>
          <div className="space-y-1">
            {outcome.residual_risks.slice(0, 5).map((risk, i) => (
              <div key={i} className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300">
                <AlertTriangle className="w-3 h-3 text-orange-500 flex-shrink-0" />
                <span>{risk.description}</span>
                <span className="text-xs text-gray-400">[{risk.severity}]</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Timestamps */}
      <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-slate-400">
        {outcome.drafted_at && (
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Drafted: {new Date(outcome.drafted_at).toLocaleDateString('fr-CH')}
          </span>
        )}
        {outcome.finalized_at && (
          <span className="flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3 text-green-500" />
            Finalized: {new Date(outcome.finalized_at).toLocaleDateString('fr-CH')}
          </span>
        )}
      </div>
    </div>
  );
}

export default function RemediationPostWorksPanel({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();

  const {
    data: outcomes = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['remediation-outcomes', buildingId],
    queryFn: () => remediationPostWorksApi.getBuildingOutcomes(buildingId),
    enabled: !!buildingId,
    retry: false,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="w-6 h-6 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-slate-400">
        <AlertTriangle className="w-6 h-6 mx-auto mb-2 text-orange-500" />
        <p>{t('app.error') || 'Error loading data'}</p>
      </div>
    );
  }

  if (outcomes.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500 dark:text-slate-400" data-testid="no-outcomes">
        <TrendingUp className="w-8 h-8 mx-auto mb-2 text-gray-300 dark:text-slate-600" />
        <p>{t('post_works.no_outcomes') || 'No remediation outcomes yet'}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="remediation-post-works-panel">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
        {t('post_works.remediation_outcomes') || 'Remediation Outcomes'}
      </h3>
      {outcomes.map((outcome) => (
        <OutcomeCard key={outcome.id} outcome={outcome} />
      ))}
    </div>
  );
}
