import { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { useTranslation } from '@/i18n';
import { apiClient } from '@/api/client';
import PostWorkItemCard from '@/components/PostWorkItemCard';

interface PostWorkItem {
  id: string;
  building_id: string;
  work_item_id: string | null;
  building_element_id: string | null;
  completion_status: 'pending' | 'in_progress' | 'completed' | 'verified';
  completion_date: string | null;
  contractor_id: string;
  photo_uris: string[] | null;
  before_after_pairs: Record<string, string>[] | null;
  notes: string | null;
  verification_score: number;
  flagged_for_review: boolean;
  ai_generated: boolean;
  created_at: string;
  updated_at: string;
}

interface CompletionStatus {
  building_id: string;
  total_items: number;
  completed_items: number;
  verified_items: number;
  completion_percentage: number;
  items_by_status: Record<string, number>;
  last_updated: string | null;
}

export default function PostWorksTracker() {
  const { buildingId } = useParams<{ buildingId: string }>();
  const { t } = useTranslation();
  const [items, setItems] = useState<PostWorkItem[]>([]);
  const [completionStatus, setCompletionStatus] = useState<CompletionStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [generatingCert, setGeneratingCert] = useState(false);

  const fetchData = useCallback(async () => {
    if (!buildingId) return;
    setLoading(true);
    setError(null);
    try {
      const params: Record<string, string> = {};
      if (statusFilter) params.status = statusFilter;

      const [itemsRes, statusRes] = await Promise.all([
        apiClient.get(`/buildings/${buildingId}/post-work-items`, { params }),
        apiClient.get(`/buildings/${buildingId}/completion-status`),
      ]);
      setItems(itemsRes.data.items || []);
      setCompletionStatus(statusRes.data);
    } catch (err) {
      setError(t('post_works_tracker.load_error') || 'Failed to load post-work items');
    } finally {
      setLoading(false);
    }
  }, [buildingId, statusFilter, t]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleComplete = async (itemId: string, photoUris: string[], notes: string) => {
    if (!buildingId) return;
    try {
      await apiClient.post(`/buildings/${buildingId}/post-work-items/${itemId}/complete`, {
        photo_uris: photoUris,
        notes,
      });
      await fetchData();
    } catch {
      setError(t('post_works_tracker.complete_error') || 'Failed to complete item');
    }
  };

  const handleGenerateCertificate = async () => {
    if (!buildingId) return;
    setGeneratingCert(true);
    try {
      const res = await apiClient.get(`/buildings/${buildingId}/completion-certificate`);
      if (res.data?.pdf_uri) {
        window.open(res.data.pdf_uri, '_blank');
      }
    } catch {
      setError(t('post_works_tracker.certificate_error') || 'Cannot generate certificate yet');
    } finally {
      setGeneratingCert(false);
    }
  };

  const pct = completionStatus?.completion_percentage ?? 0;

  return (
    <div className="max-w-3xl mx-auto px-4 py-6" data-testid="post-works-tracker">
      {/* Header */}
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
          {t('post_works_tracker.title') || 'Post-Works Tracker'}
        </h1>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          {t('post_works_tracker.subtitle') || 'Track and verify completion of work items'}
        </p>
      </div>

      {/* Progress bar */}
      <div className="mb-6 bg-white dark:bg-gray-800 rounded-lg p-4 shadow-sm border border-gray-200 dark:border-gray-700">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
            {t('post_works_tracker.completion') || 'Completion'}
          </span>
          <span className="text-sm font-semibold text-gray-900 dark:text-white" data-testid="completion-pct">
            {pct.toFixed(1)}%
          </span>
        </div>
        <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3" data-testid="progress-bar">
          <div
            className={`h-3 rounded-full transition-all duration-500 ${
              pct >= 100
                ? 'bg-green-500'
                : pct >= 50
                  ? 'bg-blue-500'
                  : 'bg-amber-500'
            }`}
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>
        <div className="mt-2 flex gap-4 text-xs text-gray-500 dark:text-gray-400">
          <span data-testid="total-items">
            {t('post_works_tracker.total') || 'Total'}: {completionStatus?.total_items ?? 0}
          </span>
          <span data-testid="completed-items">
            {t('post_works_tracker.completed') || 'Completed'}: {completionStatus?.completed_items ?? 0}
          </span>
          <span data-testid="verified-items">
            {t('post_works_tracker.verified') || 'Verified'}: {completionStatus?.verified_items ?? 0}
          </span>
        </div>

        {pct >= 100 && (
          <button
            onClick={handleGenerateCertificate}
            disabled={generatingCert}
            className="mt-3 w-full px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
            data-testid="generate-certificate-btn"
          >
            {generatingCert
              ? (t('post_works_tracker.generating') || 'Generating...')
              : (t('post_works_tracker.generate_certificate') || 'Generate Completion Certificate')}
          </button>
        )}
      </div>

      {/* Filter */}
      <div className="mb-4 flex gap-2">
        {['', 'pending', 'in_progress', 'completed', 'verified'].map((s) => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            data-testid={`filter-${s || 'all'}`}
            className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${
              statusFilter === s
                ? 'bg-blue-600 text-white border-blue-600'
                : 'bg-white dark:bg-gray-800 text-gray-600 dark:text-gray-300 border-gray-300 dark:border-gray-600 hover:border-blue-400'
            }`}
          >
            {s === '' ? (t('post_works_tracker.all') || 'All') : s.replace('_', ' ')}
          </button>
        ))}
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-400 text-sm" data-testid="error-message">
          {error}
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="flex justify-center py-12" data-testid="loading-spinner">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
        </div>
      )}

      {/* Items list */}
      {!loading && items.length === 0 && (
        <div className="text-center py-12 text-gray-500 dark:text-gray-400" data-testid="empty-state">
          {t('post_works_tracker.no_items') || 'No work items found'}
        </div>
      )}

      <div className="space-y-3">
        {items.map((item) => (
          <PostWorkItemCard
            key={item.id}
            item={item}
            onComplete={handleComplete}
          />
        ))}
      </div>
    </div>
  );
}
