import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { remediationPostWorksApi, type AIFeedbackPayload } from '@/api/remediationPostWorks';
import { toast } from '@/store/toastStore';
import {
  Loader2,
  AlertTriangle,
  CheckCircle2,
  Clock,
  FileCheck,
  Play,
  Eye,
  ThumbsUp,
  ThumbsDown,
  Pencil,
} from 'lucide-react';

const STATUS_COLORS: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  drafted: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  review_required: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  finalized: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

function StatusBadge({ status }: { status: string }) {
  return (
    <span className={cn('inline-block px-2 py-0.5 text-xs font-medium rounded-full', STATUS_COLORS[status] || STATUS_COLORS.pending)}>
      {status.replace('_', ' ')}
    </span>
  );
}

interface CompletionPostWorksProps {
  completionId: string;
  completionStatus: string;
}

export default function CompletionPostWorks({ completionId, completionStatus }: CompletionPostWorksProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const {
    data: postWorks,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['completion-post-works', completionId],
    queryFn: () => remediationPostWorksApi.getPostWorks(completionId),
    enabled: !!completionId,
    retry: false,
  });

  const draftMutation = useMutation({
    mutationFn: () => remediationPostWorksApi.draftPostWorks(completionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['completion-post-works', completionId] });
      toast(t('post_works.drafted_success') || 'Post-works draft created');
    },
    onError: () => toast(t('app.error') || 'Error'),
  });

  const reviewMutation = useMutation({
    mutationFn: () => remediationPostWorksApi.reviewPostWorks(completionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['completion-post-works', completionId] });
      toast(t('post_works.reviewed_success') || 'Post-works reviewed');
    },
    onError: () => toast(t('app.error') || 'Error'),
  });

  const finalizeMutation = useMutation({
    mutationFn: () => remediationPostWorksApi.finalizePostWorks(completionId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['completion-post-works', completionId] });
      toast(t('post_works.finalized_success') || 'Post-works finalized');
    },
    onError: () => toast(t('app.error') || 'Error'),
  });

  const feedbackMutation = useMutation({
    mutationFn: (payload: AIFeedbackPayload) => remediationPostWorksApi.submitFeedback(payload),
    onSuccess: () => toast(t('post_works.feedback_recorded') || 'Feedback recorded'),
    onError: () => toast(t('app.error') || 'Error'),
  });

  const handleFeedback = (type: 'confirm' | 'correct' | 'reject', entityId: string) => {
    feedbackMutation.mutate({
      feedback_type: type,
      entity_type: 'post_works_state',
      entity_id: entityId,
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-6">
        <Loader2 className="w-5 h-5 animate-spin text-red-600" />
      </div>
    );
  }

  // No post-works yet — show draft button if completion is fully confirmed
  if (isError || !postWorks) {
    if (completionStatus !== 'fully_confirmed') {
      return (
        <div className="text-center py-6 text-gray-500 dark:text-slate-400" data-testid="pw-not-ready">
          <Clock className="w-6 h-6 mx-auto mb-2 text-gray-300 dark:text-slate-600" />
          <p className="text-sm">{t('post_works.awaiting_confirmation') || 'Awaiting full confirmation to draft post-works'}</p>
        </div>
      );
    }
    return (
      <div className="text-center py-6" data-testid="pw-draft-action">
        <FileCheck className="w-8 h-8 mx-auto mb-2 text-blue-500" />
        <p className="text-sm text-gray-700 dark:text-slate-300 mb-3">
          {t('post_works.ready_to_draft') || 'Completion confirmed. Ready to draft post-works analysis.'}
        </p>
        <button
          onClick={() => draftMutation.mutate()}
          disabled={draftMutation.isPending}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50"
          data-testid="draft-post-works-btn"
        >
          {draftMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />}
          {t('post_works.draft_action') || 'Draft Post-Works'}
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="completion-post-works">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
          {t('post_works.title') || 'Post-Works Analysis'}
        </h4>
        <StatusBadge status={postWorks.status} />
      </div>

      {/* Intervention link */}
      <div className="bg-gray-50 dark:bg-slate-700 rounded-lg p-3">
        <p className="text-xs text-gray-500 dark:text-slate-400">{t('post_works.intervention') || 'Linked Intervention'}</p>
        <p className="text-sm font-medium text-gray-900 dark:text-white mt-0.5">{postWorks.intervention_id}</p>
      </div>

      {/* Deltas (if finalized) */}
      {postWorks.status === 'finalized' && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          {postWorks.grade_delta && (
            <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-3">
              <p className="text-xs text-green-600 dark:text-green-400">Grade</p>
              <p className="text-sm font-bold text-green-700 dark:text-green-300">
                {postWorks.grade_delta.before} → {postWorks.grade_delta.after}
              </p>
            </div>
          )}
          {postWorks.trust_delta && (
            <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-3">
              <p className="text-xs text-blue-600 dark:text-blue-400">Trust</p>
              <p className="text-sm font-bold text-blue-700 dark:text-blue-300">
                {(postWorks.trust_delta.before * 100).toFixed(0)}% → {(postWorks.trust_delta.after * 100).toFixed(0)}%
              </p>
            </div>
          )}
          {postWorks.completeness_delta && (
            <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3">
              <p className="text-xs text-purple-600 dark:text-purple-400">Completeness</p>
              <p className="text-sm font-bold text-purple-700 dark:text-purple-300">
                {(postWorks.completeness_delta.before * 100).toFixed(0)}% → {(postWorks.completeness_delta.after * 100).toFixed(0)}%
              </p>
            </div>
          )}
        </div>
      )}

      {/* Residual risks */}
      {postWorks.residual_risks && postWorks.residual_risks.length > 0 && (
        <div className="border border-orange-200 dark:border-orange-800 rounded-lg p-3">
          <p className="text-xs font-medium text-orange-600 dark:text-orange-400 mb-2">
            {t('post_works.residual_risks') || 'Residual Risks'} ({postWorks.residual_risks.length})
          </p>
          {postWorks.residual_risks.map((risk, i) => (
            <div key={i} className="flex items-start gap-2 text-sm text-gray-700 dark:text-slate-300 mb-1">
              <AlertTriangle className="w-3 h-3 mt-0.5 text-orange-500 flex-shrink-0" />
              <span>{risk.description}</span>
            </div>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-2 pt-2">
        {postWorks.status === 'drafted' && (
          <button
            onClick={() => reviewMutation.mutate()}
            disabled={reviewMutation.isPending}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-yellow-600 rounded-lg hover:bg-yellow-700 disabled:opacity-50"
            data-testid="review-post-works-btn"
          >
            {reviewMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <Eye className="w-3 h-3" />}
            {t('post_works.review_action') || 'Mark as Reviewed'}
          </button>
        )}
        {postWorks.status === 'review_required' && (
          <button
            onClick={() => finalizeMutation.mutate()}
            disabled={finalizeMutation.isPending}
            className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-green-600 rounded-lg hover:bg-green-700 disabled:opacity-50"
            data-testid="finalize-post-works-btn"
          >
            {finalizeMutation.isPending ? <Loader2 className="w-3 h-3 animate-spin" /> : <CheckCircle2 className="w-3 h-3" />}
            {t('post_works.finalize_action') || 'Finalize'}
          </button>
        )}
        {postWorks.status === 'finalized' && (
          <span className="inline-flex items-center gap-1 text-sm text-green-600 dark:text-green-400">
            <CheckCircle2 className="w-4 h-4" />
            {t('post_works.finalized') || 'Finalized'}
          </span>
        )}
      </div>

      {/* AI Feedback buttons (for drafted items) */}
      {(postWorks.status === 'drafted' || postWorks.status === 'review_required') && (
        <div className="border-t border-gray-200 dark:border-slate-700 pt-3">
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">
            {t('post_works.ai_feedback') || 'AI Output Feedback'}
          </p>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handleFeedback('confirm', postWorks.intervention_id)}
              disabled={feedbackMutation.isPending}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-green-700 bg-green-50 dark:bg-green-900/20 dark:text-green-400 rounded-lg hover:bg-green-100 dark:hover:bg-green-900/40"
              data-testid="feedback-confirm-btn"
            >
              <ThumbsUp className="w-3 h-3" /> {t('post_works.confirm') || 'Confirm'}
            </button>
            <button
              onClick={() => handleFeedback('correct', postWorks.intervention_id)}
              disabled={feedbackMutation.isPending}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-yellow-700 bg-yellow-50 dark:bg-yellow-900/20 dark:text-yellow-400 rounded-lg hover:bg-yellow-100 dark:hover:bg-yellow-900/40"
              data-testid="feedback-correct-btn"
            >
              <Pencil className="w-3 h-3" /> {t('post_works.correct') || 'Correct'}
            </button>
            <button
              onClick={() => handleFeedback('reject', postWorks.intervention_id)}
              disabled={feedbackMutation.isPending}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-red-700 bg-red-50 dark:bg-red-900/20 dark:text-red-400 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/40"
              data-testid="feedback-reject-btn"
            >
              <ThumbsDown className="w-3 h-3" /> {t('post_works.reject') || 'Reject'}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
