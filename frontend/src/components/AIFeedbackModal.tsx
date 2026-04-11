import { useState, useCallback } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { aiFeedbackApi, type AIFeedbackCreate } from '@/api/aiFeedback';
import { AlertTriangle, CheckCircle2, X, Bot } from 'lucide-react';

interface AIFeedbackModalProps {
  isOpen: boolean;
  onClose: () => void;
  diagnosticId: string;
  entityType: string;
  entityId: string;
  fieldName: string;
  originalValue: string;
  modelVersion?: string;
}

export default function AIFeedbackModal({
  isOpen,
  onClose,
  diagnosticId,
  entityType,
  entityId,
  fieldName,
  originalValue,
  modelVersion,
}: AIFeedbackModalProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [correctedValue, setCorrectedValue] = useState(originalValue);
  const [notes, setNotes] = useState('');
  const [submitted, setSubmitted] = useState(false);

  const mutation = useMutation({
    mutationFn: (data: AIFeedbackCreate) => aiFeedbackApi.recordFeedback(diagnosticId, data),
    onSuccess: () => {
      setSubmitted(true);
      queryClient.invalidateQueries({ queryKey: ['ai-metrics'] });
      setTimeout(onClose, 1500);
    },
  });

  const handleSubmit = useCallback(() => {
    mutation.mutate({
      entity_type: entityType,
      entity_id: entityId,
      field_name: fieldName,
      original_value: originalValue,
      corrected_value: correctedValue,
      model_version: modelVersion,
      notes: notes || undefined,
    });
  }, [mutation, entityType, entityId, fieldName, originalValue, correctedValue, modelVersion, notes]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800">
        <div className="mb-4 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot className="h-5 w-5 text-blue-500" />
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              {t('ai_feedback.title') || 'Correct AI Extraction'}
            </h3>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
            <X className="h-5 w-5" />
          </button>
        </div>

        {submitted ? (
          <div className="flex flex-col items-center gap-3 py-6">
            <CheckCircle2 className="h-10 w-10 text-green-500" />
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {t('ai_feedback.thanks') || 'Thank you! Your correction helps improve accuracy.'}
            </p>
          </div>
        ) : (
          <>
            <div className="mb-3">
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">
                {t('ai_feedback.field') || 'Field'}
              </label>
              <p className="text-sm font-mono text-gray-700 dark:text-gray-300">{fieldName}</p>
            </div>

            <div className="mb-3">
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">
                {t('ai_feedback.original') || 'AI extracted value'}
              </label>
              <div className="flex items-center gap-2 rounded bg-orange-50 px-3 py-2 dark:bg-orange-900/20">
                <AlertTriangle className="h-4 w-4 text-orange-500" />
                <span className="text-sm text-gray-800 dark:text-gray-200">{originalValue}</span>
              </div>
            </div>

            <div className="mb-3">
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">
                {t('ai_feedback.corrected') || 'Correct value'}
              </label>
              <input
                type="text"
                value={correctedValue}
                onChange={(e) => setCorrectedValue(e.target.value)}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-white"
              />
            </div>

            <div className="mb-4">
              <label className="mb-1 block text-xs font-medium text-gray-500 dark:text-gray-400">
                {t('ai_feedback.notes') || 'Notes (optional)'}
              </label>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={2}
                className="w-full rounded border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none dark:border-gray-600 dark:bg-gray-700 dark:text-white"
                placeholder={t('ai_feedback.notes_placeholder') || 'Why is this wrong?'}
              />
            </div>

            <div className="flex justify-end gap-2">
              <button
                onClick={onClose}
                className="rounded px-4 py-2 text-sm text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
              >
                {t('common.cancel') || 'Cancel'}
              </button>
              <button
                onClick={handleSubmit}
                disabled={mutation.isPending || !correctedValue}
                className="rounded bg-blue-600 px-4 py-2 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {mutation.isPending
                  ? (t('common.saving') || 'Saving...')
                  : (t('ai_feedback.submit') || 'Submit Correction')}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
