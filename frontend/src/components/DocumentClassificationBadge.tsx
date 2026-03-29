import { useState } from 'react';
import { cn } from '@/utils/formatters';
import { useTranslation } from '@/i18n';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface DocumentClassificationBadgeProps {
  documentType: string;
  confidence: number;
  method?: 'filename' | 'content' | 'hybrid';
  aiGenerated?: boolean;
  onCorrect?: (correctedType: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Confidence color helpers                                           */
/* ------------------------------------------------------------------ */

function confidenceColor(confidence: number): {
  dot: string;
  bg: string;
  text: string;
  border: string;
} {
  if (confidence >= 0.8) {
    return {
      dot: 'bg-green-500 dark:bg-green-400',
      bg: 'bg-green-50 dark:bg-green-900/20',
      text: 'text-green-700 dark:text-green-300',
      border: 'border-green-200 dark:border-green-800',
    };
  }
  if (confidence >= 0.6) {
    return {
      dot: 'bg-amber-500 dark:bg-amber-400',
      bg: 'bg-amber-50 dark:bg-amber-900/20',
      text: 'text-amber-700 dark:text-amber-300',
      border: 'border-amber-200 dark:border-amber-800',
    };
  }
  return {
    dot: 'bg-red-500 dark:bg-red-400',
    bg: 'bg-red-50 dark:bg-red-900/20',
    text: 'text-red-700 dark:text-red-300',
    border: 'border-red-200 dark:border-red-800',
  };
}

/* ------------------------------------------------------------------ */
/*  Document type keys for correction dropdown                         */
/* ------------------------------------------------------------------ */

const DOCUMENT_TYPE_KEYS = [
  'asbestos_report',
  'lead_report',
  'pcb_report',
  'cfc_estimate',
  'contractor_invoice',
  'cecb_certificate',
  'building_permit',
  'site_report',
  'insurance_policy',
  'management_report',
] as const;

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function DocumentClassificationBadge({
  documentType,
  confidence,
  method,
  aiGenerated,
  onCorrect,
}: DocumentClassificationBadgeProps) {
  const { t } = useTranslation();
  const [showCorrection, setShowCorrection] = useState(false);

  const colors = confidenceColor(confidence);
  const typeLabel = t(`doc_classifier.type.${documentType}`) || documentType;
  const confidencePct = Math.round(confidence * 100);

  return (
    <div className="inline-flex items-center gap-2" data-testid="doc-classification-badge">
      {/* Badge */}
      <span
        className={cn(
          'inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium',
          colors.bg,
          colors.text,
          colors.border,
        )}
        title={`${t('doc_classifier.confidence')}: ${confidencePct}%${method ? ` (${method})` : ''}${aiGenerated ? ' — AI' : ''}`}
      >
        <span className={cn('inline-block h-2 w-2 rounded-full shrink-0', colors.dot)} />
        {typeLabel}
        <span className="opacity-60">{confidencePct}%</span>
      </span>

      {/* Correct button */}
      {onCorrect && (
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowCorrection(!showCorrection)}
            className="text-xs text-gray-500 hover:text-gray-700 dark:text-slate-400 dark:hover:text-slate-200 underline"
            data-testid="doc-classification-correct-btn"
          >
            {t('doc_classifier.correct')}
          </button>

          {showCorrection && (
            <div
              className="absolute top-6 left-0 z-10 w-48 rounded border border-gray-200 bg-white shadow-lg dark:border-slate-700 dark:bg-slate-800"
              data-testid="doc-classification-correction-dropdown"
            >
              {DOCUMENT_TYPE_KEYS.map((key) => (
                <button
                  key={key}
                  type="button"
                  className="block w-full px-3 py-1.5 text-left text-xs hover:bg-gray-100 dark:hover:bg-slate-700"
                  onClick={() => {
                    onCorrect(key);
                    setShowCorrection(false);
                  }}
                >
                  {t(`doc_classifier.type.${key}`) || key}
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default DocumentClassificationBadge;
