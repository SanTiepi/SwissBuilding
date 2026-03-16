import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { passportApi, type PassportSummary } from '@/api/passport';
import { sharedLinksApi } from '@/api/sharedLinks';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { toast } from '@/store/toastStore';
import { AsyncStateWrapper } from '@/components/AsyncStateWrapper';
import {
  Shield,
  TrendingUp,
  TrendingDown,
  Minus,
  AlertTriangle,
  Eye,
  FileText,
  FlaskConical,
  Stethoscope,
  Wrench,
  Share2,
  X,
  Copy,
  Check,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';

const AUDIENCE_TYPES = ['buyer', 'insurer', 'lender', 'authority', 'contractor', 'tenant'] as const;
const EXPIRATION_OPTIONS = [7, 14, 30, 90] as const;

const GRADE_COLORS: Record<string, { bg: string; text: string; ring: string }> = {
  A: {
    bg: 'bg-emerald-100 dark:bg-emerald-900/40',
    text: 'text-emerald-700 dark:text-emerald-300',
    ring: 'ring-emerald-500',
  },
  B: { bg: 'bg-green-100 dark:bg-green-900/40', text: 'text-green-700 dark:text-green-300', ring: 'ring-green-500' },
  C: {
    bg: 'bg-yellow-100 dark:bg-yellow-900/40',
    text: 'text-yellow-700 dark:text-yellow-300',
    ring: 'ring-yellow-500',
  },
  D: {
    bg: 'bg-orange-100 dark:bg-orange-900/40',
    text: 'text-orange-700 dark:text-orange-300',
    ring: 'ring-orange-500',
  },
  F: { bg: 'bg-red-100 dark:bg-red-900/40', text: 'text-red-700 dark:text-red-300', ring: 'ring-red-500' },
};

const KNOWLEDGE_BAR_SEGMENTS: { key: keyof PassportSummary['knowledge_state']; color: string }[] = [
  { key: 'proven_pct', color: 'bg-green-500' },
  { key: 'inferred_pct', color: 'bg-blue-500' },
  { key: 'declared_pct', color: 'bg-yellow-500' },
  { key: 'obsolete_pct', color: 'bg-orange-500' },
  { key: 'contradictory_pct', color: 'bg-red-500' },
];

const TREND_ICON: Record<string, typeof TrendingUp> = {
  improving: TrendingUp,
  stable: Minus,
  declining: TrendingDown,
};

const TREND_COLOR: Record<string, string> = {
  improving: 'text-green-500',
  stable: 'text-gray-400 dark:text-slate-500',
  declining: 'text-red-500',
};

function GradeBadge({ grade }: { grade: string }) {
  const colors = GRADE_COLORS[grade] ?? GRADE_COLORS['F'];
  return (
    <div
      className={cn(
        'flex items-center justify-center w-14 h-14 rounded-full ring-2 text-2xl font-bold shrink-0',
        colors.bg,
        colors.text,
        colors.ring,
      )}
    >
      {grade}
    </div>
  );
}

function KnowledgeBar({ knowledge }: { knowledge: PassportSummary['knowledge_state'] }) {
  return (
    <div className="flex h-2.5 w-full rounded-full overflow-hidden bg-gray-200 dark:bg-slate-600">
      {KNOWLEDGE_BAR_SEGMENTS.map(({ key, color }) => {
        const value = knowledge[key] as number;
        if (value <= 0) return null;
        return <div key={key} className={cn(color, 'h-full')} style={{ width: `${value * 100}%` }} />;
      })}
    </div>
  );
}

/* ---------- Share Passport Modal ---------- */
function SharePassportModal({ buildingId, onClose }: { buildingId: string; onClose: () => void }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [audience, setAudience] = useState<string>('buyer');
  const [expiresIn, setExpiresIn] = useState<number>(30);
  const [maxViews, setMaxViews] = useState<string>('');
  const [createdLink, setCreatedLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const createMutation = useMutation({
    mutationFn: () =>
      sharedLinksApi.create({
        resource_type: 'building',
        resource_id: buildingId,
        audience_type: audience,
        expires_in_days: expiresIn,
        max_views: maxViews ? parseInt(maxViews, 10) : undefined,
        allowed_sections: ['passport'],
      }),
    onSuccess: (data) => {
      const url = `${window.location.origin}/shared/${data.token}`;
      setCreatedLink(url);
      toast(t('passport.link_created') || 'Link created', 'success');
      queryClient.invalidateQueries({ queryKey: ['shared-links', buildingId] });
    },
    onError: () => {
      toast(t('passport.link_error') || 'Failed to create link', 'error');
    },
  });

  const handleCopy = useCallback(async () => {
    if (!createdLink) return;
    try {
      await navigator.clipboard.writeText(createdLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select text
    }
  }, [createdLink]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-slate-800 rounded-xl shadow-xl w-full max-w-md mx-4 p-6">
        <div className="flex items-center justify-between mb-5">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('passport.share_passport') || 'Share Passport'}
          </h3>
          <button
            onClick={onClose}
            aria-label={t('form.close') || 'Close'}
            className="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {createdLink ? (
          <div className="space-y-4">
            <div className="flex items-center gap-2 p-3 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
              <Check className="w-5 h-5 text-green-600 shrink-0" />
              <span className="text-sm text-green-700 dark:text-green-300">
                {t('passport.link_created') || 'Link created successfully'}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="text"
                readOnly
                value={createdLink}
                className="flex-1 text-sm bg-gray-50 dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg px-3 py-2 text-gray-700 dark:text-slate-200"
              />
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 px-3 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors shrink-0"
              >
                {copied ? <Check className="w-4 h-4" /> : <Copy className="w-4 h-4" />}
                {copied ? t('passport.copied') || 'Copied!' : t('passport.copy_link') || 'Copy'}
              </button>
            </div>
          </div>
        ) : (
          <div className="space-y-4">
            {/* Audience selector */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">
                {t('passport.audience_type') || 'Audience type'}
              </label>
              <div className="grid grid-cols-3 gap-2">
                {AUDIENCE_TYPES.map((a) => (
                  <button
                    key={a}
                    onClick={() => setAudience(a)}
                    className={cn(
                      'px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors',
                      audience === a
                        ? 'bg-red-50 dark:bg-red-900/30 border-red-300 dark:border-red-700 text-red-700 dark:text-red-300'
                        : 'bg-white dark:bg-slate-700 border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-600',
                    )}
                  >
                    {t(`passport.audience_${a}`) || a}
                  </button>
                ))}
              </div>
            </div>

            {/* Expiration */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">
                {t('passport.expires_in') || 'Expires in'}
              </label>
              <div className="flex gap-2">
                {EXPIRATION_OPTIONS.map((d) => (
                  <button
                    key={d}
                    onClick={() => setExpiresIn(d)}
                    className={cn(
                      'px-3 py-1.5 text-xs font-medium rounded-lg border transition-colors',
                      expiresIn === d
                        ? 'bg-red-50 dark:bg-red-900/30 border-red-300 dark:border-red-700 text-red-700 dark:text-red-300'
                        : 'bg-white dark:bg-slate-700 border-gray-200 dark:border-slate-600 text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-600',
                    )}
                  >
                    {d} {t('passport.days') || 'days'}
                  </button>
                ))}
              </div>
            </div>

            {/* Max views */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1.5">
                {t('passport.max_views') || 'Max views'}
              </label>
              <input
                type="number"
                min={1}
                value={maxViews}
                onChange={(e) => setMaxViews(e.target.value)}
                placeholder={t('passport.max_views_placeholder') || 'Unlimited'}
                className="w-full text-sm bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg px-3 py-2 text-gray-700 dark:text-slate-200 placeholder-gray-400 dark:placeholder-slate-500"
              />
            </div>

            {/* Create button */}
            <button
              onClick={() => createMutation.mutate()}
              disabled={createMutation.isPending}
              className="w-full py-2.5 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              {createMutation.isPending
                ? t('passport.creating_link') || 'Creating...'
                : t('passport.create_link') || 'Create Link'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

/* ---------- Expandable Section ---------- */
function ExpandableSection({
  label,
  expanded,
  onToggle,
  children,
}: {
  label: React.ReactNode;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <div>
      <button onClick={onToggle} className="flex items-center gap-1 w-full text-left group" type="button">
        {expanded ? (
          <ChevronDown className="w-3.5 h-3.5 text-gray-400 shrink-0" />
        ) : (
          <ChevronRight className="w-3.5 h-3.5 text-gray-400 shrink-0" />
        )}
        {label}
      </button>
      {expanded && <div className="mt-2 ml-5">{children}</div>}
    </div>
  );
}

/* ---------- Main PassportCard ---------- */
export function PassportCard({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();
  const [showShareModal, setShowShareModal] = useState(false);
  const [expandedBlindSpots, setExpandedBlindSpots] = useState(false);
  const [expandedContradictions, setExpandedContradictions] = useState(false);
  const [expandedEvidence, setExpandedEvidence] = useState(false);

  const {
    data: passport,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['passport', 'summary', buildingId],
    queryFn: () => passportApi.summary(buildingId),
    enabled: !!buildingId,
  });

  const renderContent = () => {
    if (!passport) return null;
    const { knowledge_state, completeness, blind_spots, contradictions, evidence_coverage, passport_grade } = passport;

    const trustPct = Math.round(knowledge_state.overall_trust * 100);
    const completenessPct = Math.round(completeness.overall_score * 100);
    const trend = knowledge_state.trend ?? 'stable';
    const TrendIcon = TREND_ICON[trend] ?? Minus;
    const trendColor = TREND_COLOR[trend] ?? TREND_COLOR['stable'];
    const trendLabel = t(`passport.trend.${trend}`) || trend;

    return (
      <>
        {/* Header: Grade + Title + Knowledge Bar + Share button */}
        <div className="flex items-center gap-4">
          <GradeBadge grade={passport_grade} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-2">
              <Shield className="w-5 h-5 text-red-600 dark:text-red-400" />
              <h3 className="text-base font-semibold text-gray-900 dark:text-white truncate">
                {t('passport.title') || 'Passeport Batiment'}
              </h3>
              <span className="ml-auto text-xs text-gray-400 dark:text-slate-500 tabular-nums shrink-0">
                {knowledge_state.total_data_points} pts
              </span>
              <button
                onClick={() => setShowShareModal(true)}
                className="ml-2 flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800 hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors shrink-0"
                title={t('passport.share_passport') || 'Share Passport'}
                aria-label={t('passport.share_passport') || 'Share Passport'}
              >
                <Share2 className="w-3.5 h-3.5" />
                {t('passport.share') || 'Share'}
              </button>
            </div>
            <KnowledgeBar knowledge={knowledge_state} />
            <div className="flex gap-3 mt-1.5 text-[10px] text-gray-400 dark:text-slate-500">
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-green-500 inline-block" />
                {t('trust_score.proven') || 'Proven'}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-blue-500 inline-block" />
                {t('trust_score.inferred') || 'Inferred'}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-yellow-500 inline-block" />
                {t('trust_score.declared') || 'Declared'}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-orange-500 inline-block" />
                {t('trust_score.obsolete') || 'Obsolete'}
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2 h-2 rounded-full bg-red-500 inline-block" />
                {t('trust_score.contradictory') || 'Contradictory'}
              </span>
            </div>
          </div>
        </div>

        {/* Key metrics row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-5">
          {/* Trust */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2.5">
            <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-0.5">
              {t('passport.trust') || 'Trust'}
            </p>
            <div className="flex items-center gap-1.5">
              <span className="text-lg font-bold text-gray-900 dark:text-white tabular-nums">{trustPct}%</span>
              <TrendIcon className={cn('w-3.5 h-3.5', trendColor)} />
              <span className={cn('text-[10px]', trendColor)}>{trendLabel}</span>
            </div>
          </div>

          {/* Completeness */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2.5">
            <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-0.5">
              {t('passport.completeness') || 'Completeness'}
            </p>
            <span className="text-lg font-bold text-gray-900 dark:text-white tabular-nums">{completenessPct}%</span>
          </div>

          {/* Blind spots - expandable */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2.5">
            <ExpandableSection
              expanded={expandedBlindSpots}
              onToggle={() => setExpandedBlindSpots((v) => !v)}
              label={
                <div className="flex-1">
                  <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-0.5">
                    {t('passport.blind_spots') || 'Blind spots'}
                  </p>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn(
                        'text-lg font-bold tabular-nums',
                        blind_spots.blocking > 0 ? 'text-red-600 dark:text-red-400' : 'text-gray-900 dark:text-white',
                      )}
                    >
                      {blind_spots.total_open}
                    </span>
                    {blind_spots.blocking > 0 && <AlertTriangle className="w-3.5 h-3.5 text-red-500" />}
                  </div>
                </div>
              }
            >
              {Object.keys(blind_spots.by_type).length > 0 ? (
                <ul className="space-y-1">
                  {Object.entries(blind_spots.by_type).map(([type, count]) => (
                    <li
                      key={type}
                      className="flex items-center justify-between text-xs text-gray-600 dark:text-slate-300"
                    >
                      <span className="capitalize">{type.replace(/_/g, ' ')}</span>
                      <span className="tabular-nums font-medium">{count}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-gray-400 dark:text-slate-500">--</p>
              )}
            </ExpandableSection>
          </div>

          {/* Contradictions - expandable */}
          <div className="bg-gray-50 dark:bg-slate-700/50 rounded-lg px-3 py-2.5">
            <ExpandableSection
              expanded={expandedContradictions}
              onToggle={() => setExpandedContradictions((v) => !v)}
              label={
                <div className="flex-1">
                  <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wide mb-0.5">
                    {t('passport.contradictions') || 'Contradictions'}
                  </p>
                  <div className="flex items-center gap-1.5">
                    <span
                      className={cn(
                        'text-lg font-bold tabular-nums',
                        contradictions.unresolved > 0
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-gray-900 dark:text-white',
                      )}
                    >
                      {contradictions.unresolved}
                    </span>
                    {contradictions.unresolved > 0 && <Eye className="w-3.5 h-3.5 text-red-500" />}
                  </div>
                </div>
              }
            >
              {Object.keys(contradictions.by_type).length > 0 ? (
                <ul className="space-y-1">
                  {Object.entries(contradictions.by_type).map(([type, count]) => (
                    <li
                      key={type}
                      className="flex items-center justify-between text-xs text-gray-600 dark:text-slate-300"
                    >
                      <span className="capitalize">{type.replace(/_/g, ' ')}</span>
                      <span className="tabular-nums font-medium">{count}</span>
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-gray-400 dark:text-slate-500">--</p>
              )}
            </ExpandableSection>
          </div>
        </div>

        {/* Evidence coverage - expandable */}
        <div className="mt-4 pt-3 border-t border-gray-100 dark:border-slate-700">
          <ExpandableSection
            expanded={expandedEvidence}
            onToggle={() => setExpandedEvidence((v) => !v)}
            label={
              <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-slate-400 flex-1">
                <span className="text-[10px] font-medium uppercase tracking-wide text-gray-400 dark:text-slate-500">
                  {t('passport.evidence') || 'Evidence'}
                </span>
                <span className="flex items-center gap-1">
                  <Stethoscope className="w-3.5 h-3.5" />
                  {evidence_coverage.diagnostics_count} diag
                </span>
                <span className="flex items-center gap-1">
                  <FlaskConical className="w-3.5 h-3.5" />
                  {evidence_coverage.samples_count} samples
                </span>
                <span className="flex items-center gap-1">
                  <FileText className="w-3.5 h-3.5" />
                  {evidence_coverage.documents_count} docs
                </span>
                {evidence_coverage.interventions_count > 0 && (
                  <span className="flex items-center gap-1">
                    <Wrench className="w-3.5 h-3.5" />
                    {evidence_coverage.interventions_count} interv
                  </span>
                )}
              </div>
            }
          >
            <div className="space-y-2 text-xs text-gray-600 dark:text-slate-300">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <Stethoscope className="w-3.5 h-3.5 text-gray-400" />
                  {t('diagnostic.title') || 'Diagnostics'}
                </span>
                <span className="tabular-nums font-medium">{evidence_coverage.diagnostics_count}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <FlaskConical className="w-3.5 h-3.5 text-gray-400" />
                  Samples
                </span>
                <span className="tabular-nums font-medium">{evidence_coverage.samples_count}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1.5">
                  <FileText className="w-3.5 h-3.5 text-gray-400" />
                  {t('document.title') || 'Documents'}
                </span>
                <span className="tabular-nums font-medium">{evidence_coverage.documents_count}</span>
              </div>
              {evidence_coverage.interventions_count > 0 && (
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Wrench className="w-3.5 h-3.5 text-gray-400" />
                    {t('intervention.title') || 'Interventions'}
                  </span>
                  <span className="tabular-nums font-medium">{evidence_coverage.interventions_count}</span>
                </div>
              )}
              {evidence_coverage.latest_diagnostic_date && (
                <div className="flex items-center justify-between text-[10px] text-gray-400 dark:text-slate-500 pt-1 border-t border-gray-100 dark:border-slate-700">
                  <span>Latest diagnostic</span>
                  <span>{new Date(evidence_coverage.latest_diagnostic_date).toLocaleDateString()}</span>
                </div>
              )}
              {evidence_coverage.latest_document_date && (
                <div className="flex items-center justify-between text-[10px] text-gray-400 dark:text-slate-500">
                  <span>Latest document</span>
                  <span>{new Date(evidence_coverage.latest_document_date).toLocaleDateString()}</span>
                </div>
              )}
            </div>
          </ExpandableSection>
        </div>

        {/* Share modal */}
        {showShareModal && <SharePassportModal buildingId={buildingId} onClose={() => setShowShareModal(false)} />}
      </>
    );
  };

  return (
    <AsyncStateWrapper
      isLoading={isLoading}
      isError={isError}
      data={passport}
      loadingType="skeleton"
      icon={<Shield className="w-5 h-5" />}
      title={t('passport.title') || 'Passeport Batiment'}
      emptyMessage={t('passport.no_data') || 'No passport data'}
      className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm"
    >
      {renderContent()}
    </AsyncStateWrapper>
  );
}
