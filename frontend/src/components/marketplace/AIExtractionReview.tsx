import { useState } from 'react';
import { useTranslation } from '@/i18n';
import { remediationApi } from '@/api/remediation';
import type { AIExtractionLog } from '@/api/remediation';
import { cn } from '@/utils/formatters';
import { Check, X, Edit3, AlertTriangle, HelpCircle, Loader2 } from 'lucide-react';

function FieldConfidence({ field, value }: { field: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? 'text-green-600' : pct >= 60 ? 'text-amber-600' : 'text-red-600';
  return (
    <span className={cn('text-xs font-mono', color)}>
      {field}: {pct}%
    </span>
  );
}

interface Props {
  extraction: AIExtractionLog;
  onUpdate?: (updated: AIExtractionLog) => void;
}

export function AIExtractionReview({ extraction, onUpdate }: Props) {
  const { t } = useTranslation();
  const [isEditing, setIsEditing] = useState(false);
  const [correctedJson, setCorrectedJson] = useState(JSON.stringify(extraction.output_data, null, 2));
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(false);

  const isDraft = extraction.status === 'draft';
  const outputData = extraction.output_data || {};
  const confidencePerField = (outputData.confidence_per_field || {}) as Record<string, number>;

  const handleConfirm = async () => {
    setLoading(true);
    try {
      const updated = await remediationApi.confirmExtraction(extraction.id);
      onUpdate?.(updated);
    } finally {
      setLoading(false);
    }
  };

  const handleCorrect = async () => {
    setLoading(true);
    try {
      const parsed = JSON.parse(correctedJson);
      const updated = await remediationApi.correctExtraction(extraction.id, {
        corrected_data: parsed,
        notes: notes || undefined,
      });
      onUpdate?.(updated);
      setIsEditing(false);
    } catch {
      // JSON parse error — stay in edit mode
    } finally {
      setLoading(false);
    }
  };

  const handleReject = async () => {
    setLoading(true);
    try {
      const updated = await remediationApi.rejectExtraction(extraction.id, {
        reason: notes || 'Rejected by user',
      });
      onUpdate?.(updated);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-5 space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('extraction.review_title') || 'AI Extraction Review'}
          </h3>
          <p className="text-sm text-gray-500 dark:text-slate-400">
            {extraction.extraction_type} &mdash; {extraction.ai_model || 'unknown model'}
          </p>
        </div>
        <span
          className={cn(
            'text-xs font-medium px-2.5 py-1 rounded-full',
            extraction.status === 'draft' && 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
            extraction.status === 'confirmed' && 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
            extraction.status === 'corrected' && 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
            extraction.status === 'rejected' && 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
          )}
        >
          {extraction.status}
        </span>
      </div>

      {/* Overall confidence */}
      {extraction.confidence_score !== null && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-600 dark:text-slate-300">
            {t('extraction.overall_confidence') || 'Overall confidence'}:
          </span>
          <span className="text-sm font-semibold">
            {Math.round((extraction.confidence_score ?? 0) * 100)}%
          </span>
        </div>
      )}

      {/* Per-field confidence */}
      {Object.keys(confidencePerField).length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-gray-500 dark:text-slate-400 uppercase">
            {t('extraction.field_confidence') || 'Field Confidence'}
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(confidencePerField).map(([field, value]) => (
              <FieldConfidence key={field} field={field} value={value as number} />
            ))}
          </div>
        </div>
      )}

      {/* Ambiguous fields */}
      {extraction.ambiguous_fields && extraction.ambiguous_fields.length > 0 && (
        <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-lg p-3">
          <div className="flex items-center gap-1 text-amber-700 dark:text-amber-300 text-sm font-medium mb-1">
            <AlertTriangle className="w-4 h-4" />
            {t('extraction.ambiguous_fields') || 'Ambiguous Fields'}
          </div>
          <ul className="text-xs text-amber-600 dark:text-amber-400 space-y-1">
            {extraction.ambiguous_fields.map((af, i) => (
              <li key={i}>
                <strong>{String((af as Record<string, unknown>).field || 'unknown')}</strong>: {String((af as Record<string, unknown>).reason || '')}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Unknown fields */}
      {extraction.unknown_fields && extraction.unknown_fields.length > 0 && (
        <div className="bg-gray-50 dark:bg-slate-700/30 border border-gray-200 dark:border-slate-600 rounded-lg p-3">
          <div className="flex items-center gap-1 text-gray-600 dark:text-slate-300 text-sm font-medium mb-1">
            <HelpCircle className="w-4 h-4" />
            {t('extraction.unknown_fields') || 'Unknown Fields'}
          </div>
          <ul className="text-xs text-gray-500 dark:text-slate-400 space-y-1">
            {extraction.unknown_fields.map((uf, i) => (
              <li key={i}>{String((uf as Record<string, unknown>).field || 'unknown')}</li>
            ))}
          </ul>
        </div>
      )}

      {/* Output data / correction editor */}
      {isEditing ? (
        <div className="space-y-2">
          <textarea
            className="w-full h-48 font-mono text-xs border border-gray-300 dark:border-slate-600 rounded-lg p-2 bg-white dark:bg-slate-900 text-gray-900 dark:text-white"
            value={correctedJson}
            onChange={(e) => setCorrectedJson(e.target.value)}
          />
          <input
            type="text"
            placeholder={t('extraction.correction_notes') || 'Correction notes (optional)'}
            className="w-full border border-gray-300 dark:border-slate-600 rounded-lg px-3 py-2 text-sm bg-white dark:bg-slate-900 text-gray-900 dark:text-white"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
        </div>
      ) : (
        <pre className="text-xs bg-gray-50 dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg p-3 overflow-x-auto text-gray-800 dark:text-slate-200 max-h-48">
          {JSON.stringify(extraction.output_data, null, 2)}
        </pre>
      )}

      {/* Actions */}
      {isDraft && (
        <div className="flex items-center gap-2 pt-2 border-t border-gray-200 dark:border-slate-700">
          {!isEditing ? (
            <>
              <button
                onClick={handleConfirm}
                disabled={loading}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-green-600 hover:bg-green-700 rounded-lg disabled:opacity-50"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                {t('extraction.confirm') || 'Confirm'}
              </button>
              <button
                onClick={() => setIsEditing(true)}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-blue-700 bg-blue-100 hover:bg-blue-200 dark:text-blue-300 dark:bg-blue-900/30 dark:hover:bg-blue-900/50 rounded-lg"
              >
                <Edit3 className="w-4 h-4" />
                {t('extraction.correct') || 'Correct'}
              </button>
              <button
                onClick={handleReject}
                disabled={loading}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-red-700 bg-red-100 hover:bg-red-200 dark:text-red-300 dark:bg-red-900/30 dark:hover:bg-red-900/50 rounded-lg disabled:opacity-50"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <X className="w-4 h-4" />}
                {t('extraction.reject') || 'Reject'}
              </button>
            </>
          ) : (
            <>
              <button
                onClick={handleCorrect}
                disabled={loading}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 rounded-lg disabled:opacity-50"
              >
                {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Check className="w-4 h-4" />}
                {t('extraction.save_correction') || 'Save Correction'}
              </button>
              <button
                onClick={() => setIsEditing(false)}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-gray-700 bg-gray-100 hover:bg-gray-200 dark:text-gray-300 dark:bg-gray-700 dark:hover:bg-gray-600 rounded-lg"
              >
                <X className="w-4 h-4" />
                {t('common.cancel') || 'Cancel'}
              </button>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default AIExtractionReview;
