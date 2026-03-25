import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import {
  audiencePacksApi,
  type AudiencePackData,
  type AudiencePackListItem,
  type PackComparisonData,
} from '@/api/audiencePacks';
import { CaveatSummary } from './CaveatSummary';
import { PackComparisonView } from '@/components/PackComparisonView';
import {
  CheckCircle2,
  Lock,
  AlertTriangle,
  AlertOctagon,
  Shield,
  FileCheck,
  Hash,
  Loader2,
  Plus,
  Share2,
  GitCompare,
  Package,
} from 'lucide-react';

const AUDIENCE_TYPES = ['insurer', 'fiduciary', 'transaction', 'lender'] as const;
type AudienceType = (typeof AUDIENCE_TYPES)[number];

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  ready: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  shared: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  acknowledged: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
};

interface AudiencePackPreviewProps {
  buildingId: string;
}

export function AudiencePackPreview({ buildingId }: AudiencePackPreviewProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [selectedAudience, setSelectedAudience] = useState<AudienceType>('insurer');
  const [selectedPackId, setSelectedPackId] = useState<string | null>(null);
  const [comparePackIds, setComparePackIds] = useState<[string, string] | null>(null);

  // List packs for this building + audience
  const {
    data: packs = [],
    isLoading: packsLoading,
    isError: packsError,
  } = useQuery<AudiencePackListItem[]>({
    queryKey: ['audience-packs', buildingId, selectedAudience],
    queryFn: () => audiencePacksApi.listByBuilding(buildingId, selectedAudience),
    enabled: !!buildingId,
    retry: false,
  });

  // Get detail for selected pack
  const { data: packDetail, isLoading: detailLoading } = useQuery<AudiencePackData>({
    queryKey: ['audience-pack-detail', selectedPackId],
    queryFn: () => audiencePacksApi.get(selectedPackId!),
    enabled: !!selectedPackId,
    retry: false,
  });

  // Comparison data
  const { data: comparisonData, isLoading: comparisonLoading } = useQuery<PackComparisonData>({
    queryKey: ['audience-pack-compare', comparePackIds?.[0], comparePackIds?.[1]],
    queryFn: () => audiencePacksApi.compare(comparePackIds![0], comparePackIds![1]),
    enabled: !!comparePackIds,
    retry: false,
  });

  // Generate mutation
  const generateMutation = useMutation({
    mutationFn: () => audiencePacksApi.generate(buildingId, selectedAudience),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['audience-packs', buildingId, selectedAudience] });
      setSelectedPackId(data.id);
    },
  });

  // Share mutation
  const shareMutation = useMutation({
    mutationFn: (packId: string) => audiencePacksApi.share(packId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['audience-packs', buildingId, selectedAudience] });
      if (selectedPackId) {
        queryClient.invalidateQueries({ queryKey: ['audience-pack-detail', selectedPackId] });
      }
    },
  });

  // Auto-select first pack when list loads
  if (packs.length > 0 && !selectedPackId && !packs.find((p) => p.id === selectedPackId)) {
    setSelectedPackId(packs[0].id);
  }

  // Handle compare toggle
  const handleCompareToggle = (packId: string) => {
    if (!comparePackIds) {
      // Start comparison: use selected + this pack
      if (selectedPackId && selectedPackId !== packId) {
        setComparePackIds([selectedPackId, packId]);
      }
    } else {
      setComparePackIds(null);
    }
  };

  if (packsError) return null;

  const sections = packDetail?.sections ? Object.entries(packDetail.sections) : [];
  const includedSections = sections.filter(([, s]) => s.included && !s.blocked);
  const blockedSections = sections.filter(([, s]) => s.blocked);

  return (
    <div
      className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5"
      data-testid="audience-pack-preview"
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Package className="w-5 h-5 text-red-600" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t('audience_pack.title')}
          </h3>
        </div>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          data-testid="generate-pack-button"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
        >
          {generateMutation.isPending ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Plus className="w-3.5 h-3.5" />
          )}
          {t('audience_pack.generate')}
        </button>
      </div>

      {/* Audience type tabs */}
      <div className="flex gap-1 mb-4 bg-gray-100 dark:bg-slate-700 rounded-lg p-1" data-testid="audience-tabs">
        {AUDIENCE_TYPES.map((type) => (
          <button
            key={type}
            onClick={() => {
              setSelectedAudience(type);
              setSelectedPackId(null);
              setComparePackIds(null);
            }}
            className={cn(
              'flex-1 px-3 py-1.5 text-xs font-medium rounded-md transition-colors',
              selectedAudience === type
                ? 'bg-white dark:bg-slate-600 text-gray-900 dark:text-white shadow-sm'
                : 'text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-300',
            )}
            data-testid={`audience-tab-${type}`}
          >
            {t(`audience_pack.type.${type}`) || type}
          </button>
        ))}
      </div>

      {/* Loading */}
      {packsLoading && (
        <div className="flex items-center gap-2 text-gray-500 dark:text-slate-400 py-4">
          <Loader2 className="w-4 h-4 animate-spin" />
          {t('app.loading')}
        </div>
      )}

      {/* Empty state */}
      {!packsLoading && packs.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-slate-400 py-4" data-testid="pack-empty">
          {t('audience_pack.no_packs')}
        </p>
      )}

      {/* Pack list (compact) */}
      {packs.length > 0 && (
        <div className="space-y-2 mb-4">
          {packs.map((pack) => (
            <button
              key={pack.id}
              onClick={() => {
                setSelectedPackId(pack.id);
                setComparePackIds(null);
              }}
              className={cn(
                'w-full flex items-center justify-between px-3 py-2 rounded-lg text-left transition-colors',
                selectedPackId === pack.id
                  ? 'bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800'
                  : 'bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700',
              )}
              data-testid="pack-list-item"
            >
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-gray-900 dark:text-white">v{pack.pack_version}</span>
                <span
                  className={cn(
                    'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
                    STATUS_COLORS[pack.status] || STATUS_COLORS.draft,
                  )}
                  data-testid="pack-status"
                >
                  {t(`audience_pack.status.${pack.status}`) || pack.status}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-gray-500 dark:text-slate-400">
                  {new Date(pack.generated_at).toLocaleDateString()}
                </span>
                {packs.length >= 2 && selectedPackId && selectedPackId !== pack.id && (
                  <span
                    role="button"
                    tabIndex={0}
                    onClick={(e) => {
                      e.stopPropagation();
                      handleCompareToggle(pack.id);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.stopPropagation();
                        handleCompareToggle(pack.id);
                      }
                    }}
                    className="p-1 text-gray-400 hover:text-indigo-600 dark:text-slate-500 dark:hover:text-indigo-400 cursor-pointer"
                    title={t('audience_pack.compare')}
                    data-testid="compare-button"
                  >
                    <GitCompare className="w-3.5 h-3.5" />
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Pack detail */}
      {selectedPackId && detailLoading && (
        <div className="flex items-center gap-2 text-gray-500 dark:text-slate-400 py-4">
          <Loader2 className="w-4 h-4 animate-spin" />
          {t('app.loading')}
        </div>
      )}

      {packDetail && !comparePackIds && (
        <div className="space-y-4 border-t border-gray-200 dark:border-slate-700 pt-4" data-testid="pack-detail">
          {/* Included sections */}
          {includedSections.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('audience_pack.included_sections')}
              </p>
              <div className="space-y-1">
                {includedSections.map(([name]) => (
                  <div key={name} className="flex items-center gap-2 text-xs" data-testid="included-section">
                    <CheckCircle2 className="w-3.5 h-3.5 text-green-500" />
                    <span className="text-gray-700 dark:text-slate-300">{name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Blocked/redacted sections */}
          {blockedSections.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('audience_pack.blocked_sections')}
              </p>
              <div className="space-y-1">
                {blockedSections.map(([name]) => (
                  <div key={name} className="flex items-center gap-2 text-xs" data-testid="blocked-section">
                    <Lock className="w-3.5 h-3.5 text-gray-400 dark:text-slate-500" />
                    <span className="text-gray-400 dark:text-slate-500">{name}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Unknowns */}
          {packDetail.unknowns_summary && packDetail.unknowns_summary.length > 0 && (
            <div>
              <p className="text-xs font-medium text-amber-600 dark:text-amber-400 mb-1">
                {t('audience_pack.unknowns')} ({packDetail.unknowns_summary.length})
              </p>
              <div className="space-y-1">
                {packDetail.unknowns_summary.map((u, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs" data-testid="unknown-item">
                    <AlertTriangle className="w-3.5 h-3.5 text-amber-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700 dark:text-slate-300">{u.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Contradictions */}
          {packDetail.contradictions_summary && packDetail.contradictions_summary.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-600 dark:text-red-400 mb-1">
                {t('audience_pack.contradictions')} ({packDetail.contradictions_summary.length})
              </p>
              <div className="space-y-1">
                {packDetail.contradictions_summary.map((c, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs" data-testid="contradiction-item">
                    <AlertOctagon className="w-3.5 h-3.5 text-red-500 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700 dark:text-slate-300">{c.description}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Residual risks */}
          {packDetail.residual_risk_summary && packDetail.residual_risk_summary.length > 0 && (
            <div>
              <p className="text-xs font-medium text-amber-700 dark:text-amber-300 mb-1">
                {t('audience_pack.residual_risks')} ({packDetail.residual_risk_summary.length})
              </p>
              <div className="space-y-1">
                {packDetail.residual_risk_summary.map((r, i) => (
                  <div key={i} className="flex items-start gap-2 text-xs" data-testid="risk-item">
                    <Shield className="w-3.5 h-3.5 text-amber-600 flex-shrink-0 mt-0.5" />
                    <span className="text-gray-700 dark:text-slate-300">
                      <span className="font-medium">[{r.level}]</span> {r.description}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Trust refs */}
          {packDetail.trust_refs && packDetail.trust_refs.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('audience_pack.trust_refs')}
              </p>
              <div className="flex flex-wrap gap-1">
                {packDetail.trust_refs.map((tr, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-400 rounded"
                    data-testid="trust-ref"
                  >
                    {tr.source}
                    <span className="text-blue-500 dark:text-blue-300">
                      {Math.round(tr.confidence * 100)}%
                    </span>
                    <span className="text-blue-400 dark:text-blue-500">{tr.freshness}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Proof refs */}
          {packDetail.proof_refs && packDetail.proof_refs.length > 0 && (
            <div>
              <p className="text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">
                {t('audience_pack.proof_refs')}
              </p>
              <div className="flex flex-wrap gap-1">
                {packDetail.proof_refs.map((pr, i) => (
                  <span
                    key={i}
                    className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-green-50 dark:bg-green-900/20 text-green-700 dark:text-green-400 rounded"
                    data-testid="proof-ref"
                  >
                    <FileCheck className="w-3 h-3" />
                    {pr.title} v{pr.version}
                    <span className="text-green-500 dark:text-green-300">{pr.freshness}</span>
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* Content hash + version */}
          <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-slate-400">
            <span className="flex items-center gap-1" data-testid="content-hash">
              <Hash className="w-3 h-3" />
              {packDetail.content_hash.slice(0, 12)}...
            </span>
            <span>v{packDetail.pack_version}</span>
          </div>

          {/* Caveats */}
          <div>
            <p className="text-xs font-medium text-gray-700 dark:text-slate-300 mb-1">
              {t('audience_pack.caveats')}
            </p>
            <CaveatSummary buildingId={buildingId} audienceType={selectedAudience} />
          </div>

          {/* Actions: Share */}
          {(packDetail.status === 'draft' || packDetail.status === 'ready') && (
            <div className="flex gap-2 pt-2">
              <button
                onClick={() => shareMutation.mutate(packDetail.id)}
                disabled={shareMutation.isPending}
                data-testid="share-button"
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:bg-green-400"
              >
                {shareMutation.isPending ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <Share2 className="w-3.5 h-3.5" />
                )}
                {t('audience_pack.share')}
              </button>
            </div>
          )}
        </div>
      )}

      {/* Comparison view */}
      {comparePackIds && comparisonLoading && (
        <div className="flex items-center gap-2 text-gray-500 dark:text-slate-400 py-4">
          <Loader2 className="w-4 h-4 animate-spin" />
          {t('app.loading')}
        </div>
      )}
      {comparePackIds && comparisonData && (
        <PackComparisonView comparison={comparisonData} onClose={() => setComparePackIds(null)} />
      )}
    </div>
  );
}

export default AudiencePackPreview;
