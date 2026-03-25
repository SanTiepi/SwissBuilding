import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { marketplaceRfqApi } from '@/api/marketplaceRfq';
import type { ReviewData } from '@/api/marketplaceRfq';
import { useTranslation } from '@/i18n';
import { cn, formatDateTime } from '@/utils/formatters';
import { Star, CheckCircle2, XCircle, AlertTriangle, Loader2, ClipboardCheck } from 'lucide-react';

function StarDisplay({ rating }: { rating: number }) {
  return (
    <span className="flex items-center gap-0.5">
      {[1, 2, 3, 4, 5].map((s) => (
        <Star
          key={s}
          className={cn(
            'w-4 h-4',
            s <= rating ? 'text-amber-400 fill-amber-400' : 'text-gray-200 dark:text-slate-600',
          )}
        />
      ))}
    </span>
  );
}

function ReviewCard({
  review,
  onApprove,
  onReject,
  isActing,
}: {
  review: ReviewData;
  onApprove: () => void;
  onReject: () => void;
  isActing: boolean;
}) {
  const { t } = useTranslation();

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-4">
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <StarDisplay rating={review.rating} />
            <span className="text-sm font-medium text-gray-900 dark:text-white">
              {review.rating}/5
            </span>
          </div>
          <p className="text-xs text-gray-500 dark:text-slate-400">
            {t('marketplace.reviewer_type') || 'From'}: {review.reviewer_type}
            {' | '}
            {t('marketplace.submitted') || 'Submitted'}: {review.submitted_at ? formatDateTime(review.submitted_at) : '--'}
          </p>
        </div>
        <span
          className={cn(
            'px-2 py-0.5 rounded-full text-xs font-medium',
            review.status === 'submitted'
              ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300'
              : 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
          )}
        >
          {review.status}
        </span>
      </div>

      {review.comment && (
        <p className="text-sm text-gray-600 dark:text-slate-300 mb-3">{review.comment}</p>
      )}

      <div className="flex flex-wrap gap-3 text-xs text-gray-500 dark:text-slate-400 mb-3">
        {review.quality_score && (
          <span>
            {t('marketplace.quality') || 'Quality'}: {review.quality_score}/5
          </span>
        )}
        {review.timeliness_score && (
          <span>
            {t('marketplace.timeliness') || 'Timeliness'}: {review.timeliness_score}/5
          </span>
        )}
        {review.communication_score && (
          <span>
            {t('marketplace.communication') || 'Communication'}: {review.communication_score}/5
          </span>
        )}
      </div>

      <div className="flex gap-2 pt-2 border-t border-gray-100 dark:border-slate-700">
        <button
          onClick={onApprove}
          disabled={isActing}
          className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
        >
          {isActing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <CheckCircle2 className="w-3.5 h-3.5" />}
          {t('marketplace.approve') || 'Approve'}
        </button>
        <button
          onClick={onReject}
          disabled={isActing}
          className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-50"
        >
          {isActing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <XCircle className="w-3.5 h-3.5" />}
          {t('marketplace.reject') || 'Reject'}
        </button>
      </div>
    </div>
  );
}

export default function MarketplaceReviews() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data: reviews, isLoading, error } = useQuery({
    queryKey: ['marketplace-pending-reviews'],
    queryFn: () => marketplaceRfqApi.getPendingReviews(),
  });

  const moderateMutation = useMutation({
    mutationFn: ({ reviewId, decision, notes }: { reviewId: string; decision: string; notes?: string }) =>
      marketplaceRfqApi.moderateReview(reviewId, { decision, notes }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['marketplace-pending-reviews'] });
    },
  });

  const handleApprove = (reviewId: string) => {
    moderateMutation.mutate({ reviewId, decision: 'approve' });
  };

  const handleReject = (reviewId: string) => {
    const reason = window.prompt(t('marketplace.rejection_reason_prompt') || 'Reason for rejection:');
    if (reason !== null) {
      moderateMutation.mutate({ reviewId, decision: 'reject', notes: reason });
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-2">
          <ClipboardCheck className="w-6 h-6 text-red-600" />
          {t('marketplace.review_moderation_title') || 'Review Moderation'}
        </h1>
        <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
          {t('marketplace.review_moderation_subtitle') || 'Approve or reject pending marketplace reviews'}
        </p>
      </div>

      {isLoading && (
        <div className="flex items-center justify-center h-32">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-red-600" />
        </div>
      )}

      {error && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 text-sm text-red-700 dark:text-red-300">
          <AlertTriangle className="w-4 h-4 inline mr-1" />
          {t('common.error') || 'An error occurred'}
        </div>
      )}

      {moderateMutation.isError && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3 text-sm text-red-700 dark:text-red-300">
          {String((moderateMutation.error as Error)?.message || 'Moderation failed')}
        </div>
      )}

      <div className="space-y-4">
        {(reviews ?? []).map((review) => (
          <ReviewCard
            key={review.id}
            review={review}
            onApprove={() => handleApprove(review.id)}
            onReject={() => handleReject(review.id)}
            isActing={moderateMutation.isPending}
          />
        ))}
        {!isLoading && (reviews ?? []).length === 0 && (
          <div className="text-center py-12">
            <CheckCircle2 className="w-12 h-12 text-green-300 dark:text-green-800 mx-auto mb-3" />
            <p className="text-gray-400 dark:text-slate-500">
              {t('marketplace.no_pending_reviews') || 'No reviews pending moderation'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
