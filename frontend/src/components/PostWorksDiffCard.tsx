import { useState } from 'react';
import { useQuery, useQueryClient, useMutation } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { postWorksApi } from '@/api/postWorks';
import type { PostWorksState, PostWorksSummary, BeforeAfterComparison } from '@/api/postWorks';
import { interventionsApi } from '@/api/interventions';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { cn, formatDate, formatCHF } from '@/utils/formatters';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import type { Intervention } from '@/types';
import {
  ArrowRight,
  ShieldCheck,
  CheckCircle2,
  Clock,
  XCircle,
  AlertTriangle,
  Wrench,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  TrendingUp,
  TrendingDown,
  Minus,
} from 'lucide-react';

// ---- Constants ----

const POLLUTANT_COLORS: Record<string, string> = {
  asbestos: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
  pcb: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-300',
  lead: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
  hap: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  radon: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
  unknown: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
};

const STATE_COLORS: Record<string, string> = {
  removed: 'bg-green-500',
  treated: 'bg-yellow-500',
  encapsulated: 'bg-blue-500',
  remaining: 'bg-red-500',
  recheck_needed: 'bg-orange-500',
  unknown_after_intervention: 'bg-gray-400',
};

const DIFF_COLORS = {
  improved: 'text-green-600 dark:text-green-400',
  degraded: 'text-red-600 dark:text-red-400',
  unchanged: 'text-gray-400 dark:text-gray-500',
} as const;

const VERIFICATION_STATUS_STYLES: Record<string, string> = {
  verified: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-300',
  failed: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
};

type StateKey = 'removed' | 'encapsulated' | 'treated' | 'remaining' | 'recheck_needed' | 'unknown_after_intervention';

const STATE_KEYS: StateKey[] = [
  'removed',
  'encapsulated',
  'treated',
  'remaining',
  'recheck_needed',
  'unknown_after_intervention',
];

const VERIFIABLE_ROLES = ['admin', 'diagnostician', 'authority'];

// ---- Sub-components ----

function DiffIndicator({ before, after }: { before: number; after: number }) {
  if (after < before)
    return (
      <span className={cn('inline-flex items-center gap-0.5 text-xs font-medium', DIFF_COLORS.improved)}>
        <TrendingDown className="w-3 h-3" />
        {before - after}
      </span>
    );
  if (after > before)
    return (
      <span className={cn('inline-flex items-center gap-0.5 text-xs font-medium', DIFF_COLORS.degraded)}>
        <TrendingUp className="w-3 h-3" />+{after - before}
      </span>
    );
  return (
    <span className={cn('inline-flex items-center gap-0.5 text-xs font-medium', DIFF_COLORS.unchanged)}>
      <Minus className="w-3 h-3" />
    </span>
  );
}

function RateBadge({ rate, label }: { rate: number; label: string }) {
  const pct = Math.round(rate * 100);
  const color =
    pct >= 80
      ? 'text-green-600 dark:text-green-400'
      : pct >= 50
        ? 'text-yellow-600 dark:text-yellow-400'
        : 'text-red-600 dark:text-red-400';
  return (
    <div>
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-500 dark:text-slate-400">{label}</span>
        <span className={cn('text-xs font-semibold', color)}>{pct}%</span>
      </div>
      <div className="w-full h-2 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
        <div
          className={cn(
            'h-full rounded-full transition-all',
            pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-yellow-500' : 'bg-red-500',
          )}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function SummaryHeader({
  summary,
  comparison,
}: {
  summary: PostWorksSummary | undefined;
  comparison: BeforeAfterComparison | undefined;
}) {
  const { t } = useTranslation();
  if (!summary) return null;

  const remediationPct = comparison ? Math.round(comparison.summary.remediation_rate * 100) : 0;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-5">
      <div className="bg-white dark:bg-slate-800 rounded-lg p-3 border border-gray-200 dark:border-slate-600">
        <p className="text-xs text-gray-500 dark:text-slate-400">{t('post_works.total_states') || 'Total states'}</p>
        <p className="text-xl font-bold text-gray-900 dark:text-white">{summary.total_states}</p>
      </div>
      <div className="bg-white dark:bg-slate-800 rounded-lg p-3 border border-gray-200 dark:border-slate-600">
        <p className="text-xs text-gray-500 dark:text-slate-400">
          {t('post_works.interventions_covered') || 'Interventions'}
        </p>
        <p className="text-xl font-bold text-gray-900 dark:text-white">{summary.interventions_covered}</p>
      </div>
      <div className="bg-white dark:bg-slate-800 rounded-lg p-3 border border-gray-200 dark:border-slate-600">
        <p className="text-xs text-gray-500 dark:text-slate-400">
          {t('post_works.verification_rate') || 'Verification rate'}
        </p>
        <p className="text-xl font-bold text-gray-900 dark:text-white">
          {Math.round(summary.verification_progress.rate * 100)}%
        </p>
      </div>
      <div className="bg-white dark:bg-slate-800 rounded-lg p-3 border border-gray-200 dark:border-slate-600">
        <p className="text-xs text-gray-500 dark:text-slate-400">{t('post_works.improvement') || 'Improvement'}</p>
        <p
          className={cn(
            'text-xl font-bold',
            remediationPct >= 50 ? 'text-green-600 dark:text-green-400' : 'text-orange-600 dark:text-orange-400',
          )}
        >
          {remediationPct}%
        </p>
      </div>
    </div>
  );
}

function BeforeAfterSection({ data }: { data: BeforeAfterComparison }) {
  const { t } = useTranslation();

  const stateLabels: Record<StateKey, string> = {
    removed: t('post_works.removed') || 'Removed',
    encapsulated: t('post_works.encapsulated') || 'Encapsulated',
    treated: t('post_works.treated') || 'Treated',
    remaining: t('post_works.remaining') || 'Remaining',
    recheck_needed: t('post_works.recheck_needed') || 'Recheck needed',
    unknown_after_intervention: '\u2014',
  };

  const totalAfterPositive = data.after.remaining + data.after.recheck_needed + data.after.unknown_after_intervention;
  const totalAfterResolved = data.after.removed + data.after.treated + data.after.encapsulated;

  return (
    <div className="mb-5">
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
        <ShieldCheck className="w-4 h-4 text-gray-500 dark:text-slate-400" />
        {t('post_works.diff_title') || 'Before / After Intervention'}
      </h4>

      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto_1fr] gap-4 items-start">
        {/* Before */}
        <div className="bg-red-50/50 dark:bg-red-900/10 rounded-lg p-4 border border-red-100 dark:border-red-900/30">
          <h5 className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-2">
            {t('post_works.before') || 'Before works'}
          </h5>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            {data.before.total_positive_samples}
            <span className="text-sm font-normal text-gray-500 dark:text-slate-400 ml-1">
              {t('post_works.positive_samples') || 'Positive samples'}
            </span>
          </p>
          <div className="flex flex-wrap gap-1.5">
            {Object.entries(data.before.by_pollutant).map(([pollutant, count]) => (
              <span
                key={pollutant}
                className={cn(
                  'px-2 py-0.5 text-xs font-medium rounded-full',
                  POLLUTANT_COLORS[pollutant] ?? POLLUTANT_COLORS.unknown,
                )}
              >
                {pollutant}: {count}
              </span>
            ))}
          </div>
        </div>

        {/* Arrow separator */}
        <div className="hidden md:flex items-center justify-center pt-8">
          <ArrowRight className="w-5 h-5 text-gray-300 dark:text-slate-500" />
        </div>

        {/* After */}
        <div className="bg-green-50/50 dark:bg-green-900/10 rounded-lg p-4 border border-green-100 dark:border-green-900/30">
          <h5 className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-2">
            {t('post_works.after') || 'After works'}
          </h5>
          <div className="space-y-1.5">
            {STATE_KEYS.map((key) => {
              const count = data.after[key];
              if (count === 0) return null;
              return (
                <div key={key} className="flex items-center gap-2 text-sm">
                  <span className={cn('w-2.5 h-2.5 rounded-full flex-shrink-0', STATE_COLORS[key])} />
                  <span className="text-gray-700 dark:text-slate-200">{stateLabels[key]}</span>
                  <span className="font-semibold text-gray-900 dark:text-white">{count}</span>
                </div>
              );
            })}
          </div>
          <div className="mt-3 pt-2 border-t border-green-200 dark:border-green-900/30 flex items-center gap-3 text-xs">
            <span className="text-gray-500 dark:text-slate-400">
              {t('post_works.resolved') || 'Resolved'}:{' '}
              <strong className="text-green-600 dark:text-green-400">{totalAfterResolved}</strong>
            </span>
            <span className="text-gray-500 dark:text-slate-400">
              {t('post_works.unresolved') || 'Unresolved'}:{' '}
              <strong className="text-red-600 dark:text-red-400">{totalAfterPositive}</strong>
            </span>
            <DiffIndicator before={data.before.total_positive_samples} after={totalAfterPositive} />
          </div>
        </div>
      </div>

      {/* Per-pollutant diff */}
      {Object.keys(data.after.by_pollutant).length > 0 && (
        <div className="mt-4">
          <h5 className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-2">
            {t('post_works.pollutant_breakdown') || 'Per pollutant'}
          </h5>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
            {Object.entries(data.after.by_pollutant).map(([pollutant, states]) => {
              const beforeCount = data.before.by_pollutant[pollutant] ?? 0;
              const remainingCount =
                (states.remaining ?? 0) + (states.recheck_needed ?? 0) + (states.unknown_after_intervention ?? 0);
              return (
                <div
                  key={pollutant}
                  className="flex items-center justify-between bg-white dark:bg-slate-800 rounded-lg px-3 py-2 border border-gray-200 dark:border-slate-600"
                >
                  <span
                    className={cn(
                      'px-2 py-0.5 text-xs font-medium rounded-full',
                      POLLUTANT_COLORS[pollutant] ?? POLLUTANT_COLORS.unknown,
                    )}
                  >
                    {pollutant}
                  </span>
                  <div className="flex items-center gap-2 text-xs">
                    <span className="text-gray-500 dark:text-slate-400">{beforeCount}</span>
                    <ArrowRight className="w-3 h-3 text-gray-300 dark:text-slate-500" />
                    <span className="font-semibold text-gray-900 dark:text-white">{remainingCount}</span>
                    <DiffIndicator before={beforeCount} after={remainingCount} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Rate bars */}
      <div className="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-4">
        <RateBadge
          rate={data.summary.remediation_rate}
          label={t('post_works.remediation_rate') || 'Remediation rate'}
        />
        <RateBadge
          rate={data.summary.verification_rate}
          label={t('post_works.verification_rate') || 'Verification rate'}
        />
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500 dark:text-slate-400">
            {t('post_works.residual_risk') || 'Residual risk'}
          </span>
          <span
            className={cn(
              'px-2 py-0.5 text-xs font-bold rounded-full',
              data.summary.residual_risk_count > 0
                ? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300'
                : 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
            )}
          >
            {data.summary.residual_risk_count}
          </span>
        </div>
      </div>
    </div>
  );
}

function InterventionLinkage({ buildingId, states }: { buildingId: string; states: PostWorksState[] }) {
  const { t } = useTranslation();
  const interventionIds = [...new Set(states.map((s) => s.intervention_id).filter(Boolean))] as string[];

  const { data: interventions } = useQuery({
    queryKey: ['interventions', buildingId],
    queryFn: () => interventionsApi.list(buildingId, { size: 50 }),
    enabled: interventionIds.length > 0,
  });

  const linked = interventions?.items?.filter((iv: Intervention) => interventionIds.includes(iv.id)) ?? [];

  if (linked.length === 0) return null;

  return (
    <div className="mb-5">
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
        <Wrench className="w-4 h-4 text-gray-500 dark:text-slate-400" />
        {t('post_works.linked_interventions') || 'Linked interventions'}
      </h4>
      <div className="space-y-2">
        {linked.map((iv: Intervention) => {
          const stateCount = states.filter((s) => s.intervention_id === iv.id).length;
          return (
            <Link
              key={iv.id}
              to={`/buildings/${buildingId}/interventions`}
              className="flex items-center justify-between bg-white dark:bg-slate-800 rounded-lg px-4 py-3 border border-gray-200 dark:border-slate-600 hover:border-blue-300 dark:hover:border-blue-600 transition-colors group"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-white truncate">{iv.title}</span>
                  <span className="text-xs px-1.5 py-0.5 rounded bg-gray-100 dark:bg-slate-700 text-gray-600 dark:text-slate-300">
                    {t(`intervention_type.${iv.intervention_type}`) || iv.intervention_type}
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-1 text-xs text-gray-500 dark:text-slate-400">
                  {iv.date_start && <span>{formatDate(iv.date_start)}</span>}
                  {iv.cost_chf != null && <span>{formatCHF(iv.cost_chf)}</span>}
                  <span>
                    {stateCount} {t('post_works.states_count') || 'states'}
                  </span>
                </div>
              </div>
              <ExternalLink className="w-4 h-4 text-gray-400 group-hover:text-blue-500 transition-colors flex-shrink-0 ml-2" />
            </Link>
          );
        })}
      </div>
    </div>
  );
}

function VerificationSection({ buildingId, states }: { buildingId: string; states: PostWorksState[] }) {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();
  const canVerify = user && VERIFIABLE_ROLES.includes(user.role);

  const verifyMutation = useMutation({
    mutationFn: ({ stateId }: { stateId: string }) => postWorksApi.verify(buildingId, stateId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['post-works'] });
      queryClient.invalidateQueries({ queryKey: ['post-works-list', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['post-works-summary', buildingId] });
    },
  });

  const verified = states.filter((s) => s.verified);
  const pending = states.filter((s) => !s.verified);

  if (states.length === 0) return null;

  return (
    <div className="mb-5">
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
        <CheckCircle2 className="w-4 h-4 text-gray-500 dark:text-slate-400" />
        {t('post_works.verification') || 'Verification'}
        <span className="text-xs font-normal text-gray-500 dark:text-slate-400">
          ({verified.length}/{states.length})
        </span>
      </h4>

      {/* Pending verification */}
      {pending.length > 0 && (
        <div className="space-y-2 mb-3">
          {pending.slice(0, 5).map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between bg-yellow-50/50 dark:bg-yellow-900/10 rounded-lg px-3 py-2 border border-yellow-200 dark:border-yellow-900/30"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <Clock className="w-3.5 h-3.5 text-yellow-500 flex-shrink-0" />
                  <span className="text-sm text-gray-900 dark:text-white truncate">{s.title}</span>
                </div>
                {s.pollutant_type && (
                  <span
                    className={cn(
                      'inline-block mt-1 px-2 py-0.5 text-xs rounded-full',
                      POLLUTANT_COLORS[s.pollutant_type] ?? POLLUTANT_COLORS.unknown,
                    )}
                  >
                    {s.pollutant_type}
                  </span>
                )}
              </div>
              <span className={cn('px-2 py-0.5 text-xs font-medium rounded-full', VERIFICATION_STATUS_STYLES.pending)}>
                {t('post_works.verification_pending') || 'Pending'}
              </span>
              {canVerify && (
                <button
                  onClick={() => verifyMutation.mutate({ stateId: s.id })}
                  disabled={verifyMutation.isPending}
                  className="ml-2 px-2.5 py-1 text-xs font-medium text-white bg-green-600 hover:bg-green-700 rounded-md transition-colors disabled:opacity-50"
                >
                  {t('post_works.verify_action') || 'Verify'}
                </button>
              )}
            </div>
          ))}
          {pending.length > 5 && (
            <p className="text-xs text-gray-500 dark:text-slate-400 italic pl-1">
              +{pending.length - 5} {t('post_works.more_pending') || 'more pending'}
            </p>
          )}
        </div>
      )}

      {/* Verified */}
      {verified.length > 0 && (
        <div className="space-y-2">
          {verified.slice(0, 3).map((s) => (
            <div
              key={s.id}
              className="flex items-center justify-between bg-green-50/50 dark:bg-green-900/10 rounded-lg px-3 py-2 border border-green-200 dark:border-green-900/30"
            >
              <div className="flex items-center gap-2 flex-1 min-w-0">
                <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                <span className="text-sm text-gray-900 dark:text-white truncate">{s.title}</span>
              </div>
              <div className="flex items-center gap-2 flex-shrink-0">
                {s.verified_at && (
                  <span className="text-xs text-gray-500 dark:text-slate-400">{formatDate(s.verified_at)}</span>
                )}
                <span
                  className={cn('px-2 py-0.5 text-xs font-medium rounded-full', VERIFICATION_STATUS_STYLES.verified)}
                >
                  {t('post_works.verified') || 'Verified'}
                </span>
              </div>
            </div>
          ))}
          {verified.length > 3 && (
            <p className="text-xs text-gray-500 dark:text-slate-400 italic pl-1">
              +{verified.length - 3} {t('post_works.more_verified') || 'more verified'}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function TimelineSection({ states }: { states: PostWorksState[] }) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const sorted = [...states].sort((a, b) => new Date(b.recorded_at).getTime() - new Date(a.recorded_at).getTime());
  const displayed = expanded ? sorted : sorted.slice(0, 5);

  if (sorted.length === 0) return null;

  const stateIcon = (s: PostWorksState) => {
    if (s.verified) return <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />;
    if (s.state_type === 'remaining' || s.state_type === 'recheck_needed')
      return <AlertTriangle className="w-3.5 h-3.5 text-orange-500" />;
    if (s.state_type === 'removed') return <XCircle className="w-3.5 h-3.5 text-green-600" />;
    return <Clock className="w-3.5 h-3.5 text-gray-400" />;
  };

  const stateColor = (s: PostWorksState) => {
    if (s.state_type === 'removed' || s.state_type === 'treated' || s.state_type === 'encapsulated')
      return 'border-green-300 dark:border-green-700';
    if (s.state_type === 'remaining') return 'border-red-300 dark:border-red-700';
    if (s.state_type === 'recheck_needed') return 'border-orange-300 dark:border-orange-700';
    return 'border-gray-300 dark:border-slate-600';
  };

  return (
    <div className="mb-4">
      <h4 className="text-sm font-semibold text-gray-900 dark:text-white mb-3 flex items-center gap-2">
        <Clock className="w-4 h-4 text-gray-500 dark:text-slate-400" />
        {t('post_works.timeline') || 'Timeline'}
        <span className="text-xs font-normal text-gray-500 dark:text-slate-400">({sorted.length})</span>
      </h4>

      <div className="relative">
        {/* Vertical line */}
        <div className="absolute left-[11px] top-2 bottom-2 w-px bg-gray-200 dark:bg-slate-600" />

        <div className="space-y-3">
          {displayed.map((s) => (
            <div key={s.id} className="flex items-start gap-3 relative">
              <div className="z-10 mt-0.5 bg-gray-50 dark:bg-slate-700/50">{stateIcon(s)}</div>
              <div className={cn('flex-1 bg-white dark:bg-slate-800 rounded-lg px-3 py-2 border-l-2', stateColor(s))}>
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm text-gray-900 dark:text-white font-medium truncate">{s.title}</span>
                  <span className="text-xs text-gray-400 dark:text-slate-500 flex-shrink-0">
                    {formatDate(s.recorded_at)}
                  </span>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span
                    className={cn('w-2 h-2 rounded-full flex-shrink-0', STATE_COLORS[s.state_type] ?? 'bg-gray-400')}
                  />
                  <span className="text-xs text-gray-500 dark:text-slate-400">{s.state_type.replace(/_/g, ' ')}</span>
                  {s.pollutant_type && (
                    <span
                      className={cn(
                        'px-1.5 py-0.5 text-[10px] rounded-full',
                        POLLUTANT_COLORS[s.pollutant_type] ?? POLLUTANT_COLORS.unknown,
                      )}
                    >
                      {s.pollutant_type}
                    </span>
                  )}
                  {s.verified && (
                    <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300">
                      {t('post_works.verified') || 'Verified'}
                    </span>
                  )}
                </div>
                {s.notes && <p className="text-xs text-gray-500 dark:text-slate-400 mt-1 italic truncate">{s.notes}</p>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {sorted.length > 5 && (
        <button
          onClick={() => setExpanded((prev) => !prev)}
          className="mt-3 flex items-center gap-1 text-xs text-blue-600 dark:text-blue-400 hover:text-blue-700 dark:hover:text-blue-300 transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="w-3 h-3" />
              {t('post_works.show_less') || 'Show less'}
            </>
          ) : (
            <>
              <ChevronDown className="w-3 h-3" />
              {t('post_works.show_all') || `Show all (${sorted.length})`}
            </>
          )}
        </button>
      )}
    </div>
  );
}

// ---- Main Component ----

export function PostWorksDiffCard({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();

  const {
    data: comparison,
    isLoading: compLoading,
    isError: compError,
  } = useQuery({
    queryKey: ['post-works', 'compare', buildingId],
    queryFn: () => postWorksApi.compare(buildingId),
    enabled: !!buildingId,
  });

  const { data: summary } = useQuery({
    queryKey: ['post-works-summary', buildingId],
    queryFn: () => postWorksApi.summary(buildingId),
    enabled: !!buildingId,
  });

  const { data: statesList } = useQuery({
    queryKey: ['post-works-list', buildingId],
    queryFn: () => postWorksApi.list(buildingId),
    enabled: !!buildingId,
  });

  const states = statesList?.items ?? [];
  const isEmpty = !comparison || comparison.before.total_positive_samples === 0;

  return (
    <AsyncStateWrapper
      isLoading={compLoading}
      isError={compError}
      data={comparison}
      isEmpty={isEmpty}
      icon={<ShieldCheck className="w-5 h-5" />}
      title={t('post_works.diff_title') || 'Before / After Intervention'}
      emptyMessage={t('post_works.no_data') || 'No post-works data'}
      errorMessage={t('app.loading_error') || 'Unable to load this comparison right now.'}
    >
      {comparison && !isEmpty && (
        <>
          {/* Summary header */}
          <SummaryHeader summary={summary} comparison={comparison} />

          {/* Before/After comparison */}
          <BeforeAfterSection data={comparison} />

          {/* Intervention linkage */}
          <InterventionLinkage buildingId={buildingId} states={states} />

          {/* Verification section */}
          <VerificationSection buildingId={buildingId} states={states} />

          {/* Timeline */}
          <TimelineSection states={states} />

          {/* Disclaimer */}
          <p className="mt-3 text-[11px] text-gray-400 dark:text-slate-500 italic">
            {t('disclaimer.post_works') ||
              'Post-works assessment based on available data. Professional verification required.'}
          </p>
        </>
      )}
    </AsyncStateWrapper>
  );
}
