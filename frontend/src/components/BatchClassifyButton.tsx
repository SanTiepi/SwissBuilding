import { useState } from 'react';
import { cn } from '@/utils/formatters';
import { useTranslation } from '@/i18n';
import { documentClassifierApi, type BatchClassificationResult } from '@/api/documentClassifier';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface BatchClassifyButtonProps {
  buildingId: string;
  onComplete?: (result: BatchClassificationResult) => void;
  className?: string;
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function BatchClassifyButton({ buildingId, onComplete, className }: BatchClassifyButtonProps) {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BatchClassificationResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleClick = async () => {
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await documentClassifierApi.batchClassify(buildingId);
      setResult(res);
      onComplete?.(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Classification failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={cn('inline-flex flex-col gap-2', className)} data-testid="batch-classify-container">
      <button
        type="button"
        onClick={handleClick}
        disabled={loading}
        className={cn(
          'inline-flex items-center gap-2 rounded-md px-3 py-1.5 text-sm font-medium',
          'bg-blue-600 text-white hover:bg-blue-700',
          'dark:bg-blue-500 dark:hover:bg-blue-600',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          'transition-colors',
        )}
        data-testid="batch-classify-btn"
      >
        {loading ? (
          <>
            <span className="inline-block h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
            {t('doc_classifier.classifying')}
          </>
        ) : (
          t('doc_classifier.batch_classify')
        )}
      </button>

      {/* Results summary */}
      {result && (
        <div
          className="rounded border border-gray-200 bg-gray-50 px-3 py-2 text-xs dark:border-slate-700 dark:bg-slate-800"
          data-testid="batch-classify-result"
        >
          <p className="font-medium text-gray-700 dark:text-slate-300">
            {t('doc_classifier.batch_classify')} — {result.total_processed}{' '}
            {result.total_processed === 1 ? 'document' : 'documents'}
          </p>
          <p className="text-green-600 dark:text-green-400">
            {result.classified_count} {t('doc_classifier.classified')}
          </p>
          {result.unclassified_count > 0 && (
            <p className="text-amber-600 dark:text-amber-400">
              {result.unclassified_count} {t('doc_classifier.unclassified')}
            </p>
          )}
        </div>
      )}

      {/* Error */}
      {error && (
        <p className="text-xs text-red-600 dark:text-red-400" data-testid="batch-classify-error">
          {error}
        </p>
      )}
    </div>
  );
}

export default BatchClassifyButton;
