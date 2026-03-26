import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn, formatDate } from '@/utils/formatters';
import { publicSectorApi, type ReviewPackData } from '@/api/publicSector';
import { FileText, Plus, Send, Loader2, Clock, Users } from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  ready: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  circulating: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  reviewed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  archived: 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-400',
};

interface ReviewPackCardProps {
  buildingId: string;
}

export function ReviewPackCard({ buildingId }: ReviewPackCardProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [circulatingPackId, setCirculatingPackId] = useState<string | null>(null);

  const {
    data: packs = [],
    isLoading,
    isError,
  } = useQuery<ReviewPackData[]>({
    queryKey: ['review-packs', buildingId],
    queryFn: () => publicSectorApi.listReviewPacks(buildingId),
    enabled: !!buildingId,
    retry: false,
  });

  const generateMutation = useMutation({
    mutationFn: () => publicSectorApi.generateReviewPack(buildingId, {}),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['review-packs', buildingId] }),
  });

  const circulateMutation = useMutation({
    mutationFn: (packId: string) =>
      publicSectorApi.circulateReviewPack(packId, {
        recipients: [{ org_name: 'Default', role: 'reviewer', sent_at: new Date().toISOString() }],
      }),
    onSuccess: () => {
      setCirculatingPackId(null);
      queryClient.invalidateQueries({ queryKey: ['review-packs', buildingId] });
    },
  });

  // Don't render if API returned error (feature not available)
  if (isError) return null;

  return (
    <div
      className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-5"
      data-testid="review-pack-card"
    >
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <FileText className="w-5 h-5 text-gray-500 dark:text-slate-400" />
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            {t('public_sector.review_packs_title')}
          </h3>
        </div>
        <button
          onClick={() => generateMutation.mutate()}
          disabled={generateMutation.isPending}
          data-testid="generate-review-pack-button"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:bg-red-400"
        >
          {generateMutation.isPending ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Plus className="w-3.5 h-3.5" />
          )}
          {t('public_sector.generate_review_pack')}
        </button>
      </div>

      {isLoading && (
        <div className="flex items-center gap-2 text-gray-500 dark:text-slate-400 py-4">
          <Loader2 className="w-4 h-4 animate-spin" />
          {t('app.loading')}
        </div>
      )}

      {!isLoading && packs.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-slate-400" data-testid="review-pack-empty">
          {t('public_sector.no_review_packs')}
        </p>
      )}

      {packs.length > 0 && (
        <div className="space-y-3">
          {packs.map((pack) => (
            <div
              key={pack.id}
              className="bg-gray-50 dark:bg-slate-700/50 rounded-lg p-3"
              data-testid="review-pack-item"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-sm font-medium text-gray-900 dark:text-white">v{pack.pack_version}</span>
                  <span
                    className={cn(
                      'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
                      STATUS_COLORS[pack.status] || STATUS_COLORS.draft,
                    )}
                    data-testid="review-pack-status"
                  >
                    {t(`public_sector.status.${pack.status}`) || pack.status}
                  </span>
                </div>
                {(pack.status === 'draft' || pack.status === 'ready') && (
                  <button
                    onClick={() => {
                      setCirculatingPackId(pack.id);
                      circulateMutation.mutate(pack.id);
                    }}
                    disabled={circulateMutation.isPending && circulatingPackId === pack.id}
                    data-testid="circulate-button"
                    className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded"
                  >
                    {circulateMutation.isPending && circulatingPackId === pack.id ? (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    ) : (
                      <Send className="w-3 h-3" />
                    )}
                    {t('public_sector.circulate')}
                  </button>
                )}
              </div>

              <div className="flex flex-wrap gap-3 text-xs text-gray-500 dark:text-slate-400">
                {pack.generated_at && (
                  <span className="flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {formatDate(pack.generated_at)}
                  </span>
                )}
                {pack.review_deadline && (
                  <span className="flex items-center gap-1" data-testid="review-deadline">
                    <Clock className="w-3 h-3" />
                    {t('public_sector.deadline')}: {pack.review_deadline}
                  </span>
                )}
              </div>

              {pack.circulated_to && pack.circulated_to.length > 0 && (
                <div className="mt-2" data-testid="circulated-to-list">
                  <span className="text-xs text-gray-500 dark:text-slate-400 flex items-center gap-1 mb-1">
                    <Users className="w-3 h-3" />
                    {t('public_sector.circulated_to')}:
                  </span>
                  <div className="flex flex-wrap gap-1">
                    {pack.circulated_to.map((r, i) => (
                      <span
                        key={i}
                        className="inline-block px-2 py-0.5 text-xs bg-gray-100 dark:bg-slate-600 text-gray-700 dark:text-slate-300 rounded"
                      >
                        {r.org_name || r.role || 'Reviewer'}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default ReviewPackCard;
