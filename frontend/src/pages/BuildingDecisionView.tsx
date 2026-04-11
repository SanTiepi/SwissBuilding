/**
 * MIGRATION: KEEP BOUNDED
 * This page remains as a specialist view under BuildingDetail (Building Home).
 * It must not own canonical truth — it is a projection.
 * Per ADR-006.
 */
import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { decisionViewApi } from '@/api/decisionView';
import type {
  DecisionView,
  DecisionBlocker,
  DecisionCondition,
  DecisionClearItem,
  AudienceReadiness,
  ProofChainItem,
} from '@/api/decisionView';
import {
  ArrowLeft,
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Shield,
  FileCheck,
  Clock,
  Link as LinkIcon,
  Hash,
  TrendingUp,
  Loader2,
  Building2,
  ChevronRight,
} from 'lucide-react';
import { cn, formatDate } from '@/utils/formatters';

const GRADE_COLORS: Record<string, string> = {
  A: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  B: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  C: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200',
  D: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
  F: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
};

const AUDIENCE_LABELS: Record<string, string> = {
  authority: 'Authority',
  insurer: 'Insurer',
  lender: 'Lender',
  transaction: 'Transaction',
};

function GradeBadge({ grade }: { grade: string }) {
  return (
    <span
      className={cn(
        'inline-flex items-center px-3 py-1 rounded-full text-lg font-bold',
        GRADE_COLORS[grade] || GRADE_COLORS.F,
      )}
    >
      {grade}
    </span>
  );
}

function StatusBadge({ status }: { status: string }) {
  const colors: Record<string, string> = {
    ready: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    acknowledged: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    delivered: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    draft: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
    shared: 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300',
    queued: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300',
    sent: 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300',
    auto_matched: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
    finalized: 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300',
  };
  return (
    <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium', colors[status] || 'bg-gray-100 text-gray-600')}>
      {status}
    </span>
  );
}

function BlockerCard({ item }: { item: DecisionBlocker }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded-lg">
      <AlertTriangle className="w-5 h-5 text-red-600 dark:text-red-400 mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-red-900 dark:text-red-100">{item.title}</p>
        <p className="text-xs text-red-700 dark:text-red-300 mt-0.5">{item.description}</p>
        {item.link_hint && (
          <Link
            to={item.link_hint}
            className="text-xs text-red-600 dark:text-red-400 hover:underline mt-1 inline-flex items-center gap-1"
          >
            View details <ChevronRight className="w-3 h-3" />
          </Link>
        )}
      </div>
    </div>
  );
}

function ConditionCard({ item }: { item: DecisionCondition }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-orange-50 dark:bg-orange-950 border border-orange-200 dark:border-orange-800 rounded-lg">
      <AlertCircle className="w-5 h-5 text-orange-600 dark:text-orange-400 mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-orange-900 dark:text-orange-100">{item.title}</p>
        <p className="text-xs text-orange-700 dark:text-orange-300 mt-0.5">{item.description}</p>
        {item.link_hint && (
          <Link
            to={item.link_hint}
            className="text-xs text-orange-600 dark:text-orange-400 hover:underline mt-1 inline-flex items-center gap-1"
          >
            View details <ChevronRight className="w-3 h-3" />
          </Link>
        )}
      </div>
    </div>
  );
}

function ClearCard({ item }: { item: DecisionClearItem }) {
  return (
    <div className="flex items-start gap-3 p-3 bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded-lg">
      <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-green-900 dark:text-green-100">{item.title}</p>
        <p className="text-xs text-green-700 dark:text-green-300 mt-0.5">{item.description}</p>
      </div>
    </div>
  );
}

function AudienceTab({ ar }: { ar: AudienceReadiness }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {ar.has_pack ? (
            <CheckCircle2 className="w-4 h-4 text-green-600" />
          ) : (
            <AlertCircle className="w-4 h-4 text-gray-400" />
          )}
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">
            {ar.has_pack ? `Pack v${ar.latest_pack_version}` : 'No pack generated'}
          </span>
          {ar.latest_pack_status && <StatusBadge status={ar.latest_pack_status} />}
        </div>
        {ar.latest_pack_generated_at && (
          <span className="text-xs text-gray-500">{formatDate(ar.latest_pack_generated_at)}</span>
        )}
      </div>

      {ar.has_pack && (
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-xs text-gray-500 dark:text-gray-400 mb-1">Included sections</p>
            {ar.included_sections.length > 0 ? (
              <ul className="space-y-0.5">
                {ar.included_sections.map((s) => (
                  <li key={s} className="text-gray-700 dark:text-gray-300 flex items-center gap-1">
                    <CheckCircle2 className="w-3 h-3 text-green-500" /> {s.replace(/_/g, ' ')}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-gray-400 text-xs">None</p>
            )}
          </div>
          <div className="space-y-2">
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Unknowns</span>
              <span className={ar.unknowns_count > 0 ? 'text-orange-600 font-medium' : 'text-green-600'}>
                {ar.unknowns_count}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Contradictions</span>
              <span className={ar.contradictions_count > 0 ? 'text-red-600 font-medium' : 'text-green-600'}>
                {ar.contradictions_count}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Residual risks</span>
              <span className={ar.residual_risks_count > 0 ? 'text-orange-600 font-medium' : 'text-green-600'}>
                {ar.residual_risks_count}
              </span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Trust refs</span>
              <span className="text-gray-700 dark:text-gray-300">{ar.trust_refs_count}</span>
            </div>
            <div className="flex justify-between text-xs">
              <span className="text-gray-500">Proof refs</span>
              <span className="text-gray-700 dark:text-gray-300">{ar.proof_refs_count}</span>
            </div>
          </div>
        </div>
      )}

      {ar.caveats.length > 0 && (
        <div className="mt-2 p-2 bg-yellow-50 dark:bg-yellow-950 rounded text-xs text-yellow-800 dark:text-yellow-200">
          <p className="font-medium mb-1">Caveats:</p>
          <ul className="list-disc ml-4 space-y-0.5">
            {ar.caveats.map((c, i) => (
              <li key={i}>{c}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function ProofChainRow({ item }: { item: ProofChainItem }) {
  return (
    <div className="flex items-center gap-3 p-3 border border-gray-200 dark:border-gray-700 rounded-lg">
      <FileCheck className="w-4 h-4 text-gray-500 flex-shrink-0" />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-gray-900 dark:text-gray-100">{item.label}</span>
          {item.version && <span className="text-xs text-gray-500">v{item.version}</span>}
          {item.status && <StatusBadge status={item.status} />}
        </div>
        <div className="flex items-center gap-3 mt-1 text-xs text-gray-500">
          {item.content_hash && (
            <span className="flex items-center gap-1" title={item.content_hash}>
              <Hash className="w-3 h-3" /> {item.content_hash.slice(0, 8)}...
            </span>
          )}
          {item.occurred_at && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" /> {formatDate(item.occurred_at)}
            </span>
          )}
          {item.custody_chain_length > 0 && (
            <span className="flex items-center gap-1">
              <LinkIcon className="w-3 h-3" /> {item.custody_chain_length} events
            </span>
          )}
        </div>
      </div>
    </div>
  );
}

export default function BuildingDecisionView() {
  const { buildingId } = useParams<{ buildingId: string }>();
  const { t } = useTranslation();
  const [selectedAudience, setSelectedAudience] = useState<string>('authority');

  const { data, isLoading, error } = useQuery<DecisionView>({
    queryKey: ['decision-view', buildingId],
    queryFn: () => decisionViewApi.get(buildingId!),
    enabled: !!buildingId,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-6 text-center text-red-600">
        <AlertTriangle className="w-8 h-8 mx-auto mb-2" />
        <p>{t('common.error') || 'Failed to load decision view'}</p>
      </div>
    );
  }

  const selectedAr = data.audience_readiness.find((ar) => ar.audience === selectedAudience);

  return (
    <div className="max-w-5xl mx-auto px-4 py-6 space-y-8">
      {/* Back link */}
      <Link
        to={`/buildings/${buildingId}`}
        className="inline-flex items-center gap-1 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
      >
        <ArrowLeft className="w-4 h-4" /> Back to building
      </Link>

      {/* === 1. Decision Header === */}
      <section className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="p-3 bg-gray-100 dark:bg-gray-800 rounded-lg">
              <Building2 className="w-6 h-6 text-gray-600 dark:text-gray-300" />
            </div>
            <div>
              <h1 className="text-xl font-bold text-gray-900 dark:text-gray-100">{data.building_name}</h1>
              {data.building_address && (
                <p className="text-sm text-gray-500 dark:text-gray-400">{data.building_address}</p>
              )}
            </div>
          </div>
          <GradeBadge grade={data.passport_grade} />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mt-6">
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Trust</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {(data.overall_trust * 100).toFixed(0)}%
            </p>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Completeness</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {(data.overall_completeness * 100).toFixed(0)}%
            </p>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Readiness</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100 capitalize">
              {data.readiness_status.replace(/_/g, ' ')}
            </p>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Custody</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {data.custody_posture.current_versions}/{data.custody_posture.total_artifact_versions}
            </p>
            <p className="text-xs text-gray-400">{data.custody_posture.total_custody_events} events</p>
          </div>
        </div>

        {data.last_updated && (
          <p className="text-xs text-gray-400 mt-3 text-right">Last updated: {formatDate(data.last_updated)}</p>
        )}
      </section>

      {/* === 2. Blockers & Conditions === */}
      <section className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2 mb-4">
          <Shield className="w-5 h-5" /> Blockers &amp; Conditions
        </h2>

        {data.blockers.length === 0 && data.conditions.length === 0 && data.clear_items.length === 0 && (
          <p className="text-sm text-gray-500 dark:text-gray-400">No items to display.</p>
        )}

        {data.blockers.length > 0 && (
          <div className="space-y-2 mb-4">
            <p className="text-xs font-medium text-red-600 dark:text-red-400 uppercase tracking-wide">
              Blockers ({data.blockers.length})
            </p>
            {data.blockers.map((b) => (
              <BlockerCard key={b.id} item={b} />
            ))}
          </div>
        )}

        {data.conditions.length > 0 && (
          <div className="space-y-2 mb-4">
            <p className="text-xs font-medium text-orange-600 dark:text-orange-400 uppercase tracking-wide">
              Conditions ({data.conditions.length})
            </p>
            {data.conditions.map((c) => (
              <ConditionCard key={c.id} item={c} />
            ))}
          </div>
        )}

        {data.clear_items.length > 0 && (
          <div className="space-y-2">
            <p className="text-xs font-medium text-green-600 dark:text-green-400 uppercase tracking-wide">
              Clear ({data.clear_items.length})
            </p>
            {data.clear_items.map((c) => (
              <ClearCard key={c.id} item={c} />
            ))}
          </div>
        )}
      </section>

      {/* === 3. Audience-specific Readiness === */}
      <section className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Audience Readiness</h2>

        <div className="flex border-b border-gray-200 dark:border-gray-700 mb-4">
          {data.audience_readiness.map((ar) => (
            <button
              key={ar.audience}
              onClick={() => setSelectedAudience(ar.audience)}
              className={cn(
                'px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors',
                selectedAudience === ar.audience
                  ? 'border-red-600 text-red-600 dark:text-red-400'
                  : 'border-transparent text-gray-500 hover:text-gray-700 dark:text-gray-400',
              )}
            >
              {AUDIENCE_LABELS[ar.audience] || ar.audience}
              {ar.has_pack && <CheckCircle2 className="w-3 h-3 inline-block ml-1 text-green-500" />}
            </button>
          ))}
        </div>

        {selectedAr && <AudienceTab ar={selectedAr} />}
      </section>

      {/* === 4. Proof Chain === */}
      <section className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2 mb-4">
          <FileCheck className="w-5 h-5" /> Proof Chain
        </h2>
        {data.proof_chain.length === 0 ? (
          <p className="text-sm text-gray-500 dark:text-gray-400">No proof chain items yet.</p>
        ) : (
          <div className="space-y-2">
            {data.proof_chain.map((item, i) => (
              <ProofChainRow key={`${item.entity_type}-${item.entity_id}-${i}`} item={item} />
            ))}
          </div>
        )}
      </section>

      {/* === 5. ROI Summary === */}
      <section className="bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-700 rounded-xl p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2 mb-4">
          <TrendingUp className="w-5 h-5" /> ROI Summary
        </h2>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Time saved</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {data.roi.time_saved_hours.toFixed(1)}h
            </p>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Rework avoided</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{data.roi.rework_avoided}</p>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Blocker days saved</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">
              {data.roi.blocker_days_saved.toFixed(1)}
            </p>
          </div>
          <div className="text-center p-3 bg-gray-50 dark:bg-gray-800 rounded-lg">
            <p className="text-xs text-gray-500 dark:text-gray-400">Pack reuse</p>
            <p className="text-lg font-bold text-gray-900 dark:text-gray-100">{data.roi.pack_reuse_count}</p>
          </div>
        </div>
        {data.roi.evidence_sources.length > 0 && (
          <p className="text-xs text-gray-400 mt-3">Evidence: {data.roi.evidence_sources.join(', ')}</p>
        )}
      </section>
    </div>
  );
}
