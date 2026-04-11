import { useState, useRef } from 'react';
import { useTranslation } from '@/i18n';

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

interface Props {
  item: PostWorkItem;
  onComplete: (itemId: string, photoUris: string[], notes: string) => Promise<void>;
}

const STATUS_STYLES: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
  in_progress: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  completed: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  verified: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

export default function PostWorkItemCard({ item, onComplete }: Props) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [notes, setNotes] = useState('');
  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const canComplete = item.completion_status === 'pending' || item.completion_status === 'in_progress';

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      setSelectedFiles(Array.from(e.target.files));
    }
  };

  const handleSubmit = async () => {
    if (selectedFiles.length === 0) return;
    setSubmitting(true);
    try {
      // In production, files would be uploaded to S3 first, returning URIs.
      // For now, use file names as placeholder URIs.
      const photoUris = selectedFiles.map((f) => `uploads/${f.name}`);
      await onComplete(item.id, photoUris, notes);
      setSelectedFiles([]);
      setNotes('');
      setExpanded(false);
    } finally {
      setSubmitting(false);
    }
  };

  const scoreColor =
    item.verification_score >= 80
      ? 'text-green-600 dark:text-green-400'
      : item.verification_score >= 50
        ? 'text-amber-600 dark:text-amber-400'
        : 'text-red-600 dark:text-red-400';

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 shadow-sm overflow-hidden"
      data-testid={`post-work-item-${item.id}`}
    >
      {/* Header row */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-4 flex items-center justify-between text-left hover:bg-gray-50 dark:hover:bg-gray-750 transition-colors"
        data-testid="item-toggle"
      >
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${STATUS_STYLES[item.completion_status] || STATUS_STYLES.pending}`}
              data-testid="item-status"
            >
              {item.completion_status.replace('_', ' ')}
            </span>
            {item.flagged_for_review && (
              <span
                className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
                data-testid="review-flag"
              >
                {t('post_work_item.flagged') || 'Review needed'}
              </span>
            )}
          </div>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-300 truncate">
            {item.notes || (t('post_work_item.no_notes') || 'No description')}
          </p>
        </div>
        <div className="ml-4 flex items-center gap-3">
          {item.completion_status !== 'pending' && (
            <span className={`text-sm font-medium ${scoreColor}`} data-testid="verification-score">
              {item.verification_score.toFixed(0)}%
            </span>
          )}
          <span className="text-gray-400 text-xs">{item.photo_uris?.length ?? 0} photos</span>
          <svg
            className={`w-5 h-5 text-gray-400 transition-transform ${expanded ? 'rotate-180' : ''}`}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4 space-y-4" data-testid="item-detail">
          {/* Existing photos */}
          {item.photo_uris && item.photo_uris.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                {t('post_work_item.photos') || 'Photos'}
              </h4>
              <div className="flex gap-2 flex-wrap">
                {item.photo_uris.map((uri, i) => (
                  <div
                    key={i}
                    className="w-16 h-16 bg-gray-100 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600 flex items-center justify-center text-xs text-gray-400"
                    title={uri}
                  >
                    {i + 1}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Before/after pairs */}
          {item.before_after_pairs && item.before_after_pairs.length > 0 && (
            <div>
              <h4 className="text-xs font-medium text-gray-500 dark:text-gray-400 mb-2">
                {t('post_work_item.before_after') || 'Before / After'}
              </h4>
              <div className="grid grid-cols-2 gap-2">
                {item.before_after_pairs.map((_pair, i) => (
                  <div key={i} className="flex gap-1 text-xs text-gray-500 dark:text-gray-400">
                    <span className="px-2 py-1 bg-red-50 dark:bg-red-900/10 rounded">Before</span>
                    <span className="px-2 py-1 bg-green-50 dark:bg-green-900/10 rounded">After</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Completion form for actionable items */}
          {canComplete && (
            <div className="space-y-3 pt-2 border-t border-gray-100 dark:border-gray-700">
              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {t('post_work_item.upload_photos') || 'Upload photos (required)'}
                </label>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/*"
                  multiple
                  capture="environment"
                  onChange={handleFileChange}
                  className="block w-full text-sm text-gray-500 dark:text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 dark:file:bg-blue-900/20 dark:file:text-blue-400 hover:file:bg-blue-100"
                  data-testid="photo-upload"
                />
                {selectedFiles.length > 0 && (
                  <p className="mt-1 text-xs text-gray-500 dark:text-gray-400" data-testid="selected-count">
                    {selectedFiles.length} file(s) selected
                  </p>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
                  {t('post_work_item.notes') || 'Notes'}
                </label>
                <textarea
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={2}
                  className="w-full px-3 py-2 text-sm border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-900 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder={t('post_work_item.notes_placeholder') || 'Add completion notes...'}
                  data-testid="notes-input"
                />
              </div>

              <button
                onClick={handleSubmit}
                disabled={selectedFiles.length === 0 || submitting}
                className="w-full px-4 py-2.5 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed transition-colors active:scale-[0.98]"
                data-testid="submit-completion"
              >
                {submitting
                  ? (t('post_work_item.submitting') || 'Submitting...')
                  : (t('post_work_item.mark_complete') || 'Mark as Complete')}
              </button>
            </div>
          )}

          {/* Metadata */}
          <div className="text-xs text-gray-400 dark:text-gray-500 flex gap-4">
            <span>Created: {new Date(item.created_at).toLocaleDateString()}</span>
            {item.completion_date && (
              <span>Completed: {new Date(item.completion_date).toLocaleDateString()}</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
