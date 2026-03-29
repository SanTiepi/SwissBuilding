import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { documentExtractionApi, type ExtractionField, type ExtractionResult } from '@/api/documentExtraction';

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface DocumentExtractionPreviewProps {
  documentId: string;
  onConfirm?: (field: ExtractionField) => void;
  onReject?: (field: ExtractionField) => void;
}

/* ------------------------------------------------------------------ */
/*  Field type config                                                  */
/* ------------------------------------------------------------------ */

const FIELD_ICONS: Record<string, string> = {
  dates: '\uD83D\uDCC5',
  amounts: '\uD83D\uDCB0',
  addresses: '\uD83C\uDFE0',
  parcels: '\uD83D\uDDFA\uFE0F',
  cfc_codes: '\uD83D\uDD22',
  parties: '\uD83D\uDC64',
  references: '\uD83D\uDD17',
  pollutant_results: '\u2697\uFE0F',
  energy_class: '\u26A1',
  building_year: '\uD83C\uDFD7\uFE0F',
};

/* ------------------------------------------------------------------ */
/*  Confidence badge                                                   */
/* ------------------------------------------------------------------ */

function ConfidenceDot({ confidence }: { confidence: number }) {
  const color =
    confidence >= 0.85
      ? 'bg-green-500 dark:bg-green-400'
      : confidence >= 0.7
        ? 'bg-amber-500 dark:bg-amber-400'
        : 'bg-red-500 dark:bg-red-400';

  return (
    <span
      className={cn('inline-block w-2 h-2 rounded-full shrink-0', color)}
      title={`${Math.round(confidence * 100)}%`}
    />
  );
}

/* ------------------------------------------------------------------ */
/*  Field row                                                          */
/* ------------------------------------------------------------------ */

function FieldRow({
  field,
  onConfirm,
  onReject,
  t,
}: {
  field: ExtractionField;
  onConfirm?: (f: ExtractionField) => void;
  onReject?: (f: ExtractionField) => void;
  t: (k: string) => string;
}) {
  return (
    <div className="flex items-center gap-3 py-1.5 px-2 rounded hover:bg-gray-50 dark:hover:bg-slate-700/50 text-sm">
      <ConfidenceDot confidence={field.confidence} />
      <span className="font-medium text-gray-900 dark:text-gray-100 min-w-[120px]">{field.value}</span>
      <span className="text-gray-500 dark:text-gray-400 text-xs truncate flex-1" title={field.raw_match}>
        {field.raw_match}
      </span>
      <span className="text-gray-400 dark:text-gray-500 text-xs">{Math.round(field.confidence * 100)}%</span>
      {onConfirm && (
        <button
          onClick={() => onConfirm(field)}
          className="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50"
          data-testid="confirm-field"
        >
          {t('doc_extraction.confirm')}
        </button>
      )}
      {onReject && (
        <button
          onClick={() => onReject(field)}
          className="text-xs px-2 py-0.5 rounded bg-red-100 text-red-700 hover:bg-red-200 dark:bg-red-900/30 dark:text-red-400 dark:hover:bg-red-900/50"
          data-testid="reject-field"
        >
          {t('doc_extraction.reject')}
        </button>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main component                                                     */
/* ------------------------------------------------------------------ */

export function DocumentExtractionPreview({ documentId, onConfirm, onReject }: DocumentExtractionPreviewProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [hasExtracted, setHasExtracted] = useState(false);

  const { data, isLoading: isLoadingExisting } = useQuery({
    queryKey: ['document-extractions', documentId],
    queryFn: () => documentExtractionApi.getExtractions(documentId),
    enabled: !!documentId,
  });

  const extractMutation = useMutation({
    mutationFn: () => documentExtractionApi.extract(documentId),
    onSuccess: () => {
      setHasExtracted(true);
      queryClient.invalidateQueries({ queryKey: ['document-extractions', documentId] });
    },
  });

  const result: ExtractionResult | null | undefined = hasExtracted ? extractMutation.data : data;

  const fieldTypeLabel = (type: string): string => {
    const key = `doc_extraction.${type}`;
    return t(key) || type;
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-4">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-gray-900 dark:text-gray-100">
          {t('doc_extraction.title') || 'Extraction de donnees'}
        </h3>
        {!result && (
          <button
            onClick={() => extractMutation.mutate()}
            disabled={extractMutation.isPending}
            className="text-xs px-3 py-1.5 rounded-md bg-blue-600 text-white hover:bg-blue-700 disabled:opacity-50"
            data-testid="extract-btn"
          >
            {extractMutation.isPending
              ? (t('doc_extraction.extracting') || 'Extraction...')
              : (t('doc_extraction.extract') || 'Extraire')}
          </button>
        )}
      </div>

      {(isLoadingExisting || extractMutation.isPending) && (
        <p className="text-sm text-gray-500 dark:text-gray-400">{t('app.loading') || 'Chargement...'}</p>
      )}

      {result && (
        <div className="space-y-4">
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {result.total_fields} {t('doc_extraction.fields_found') || 'champs trouves'}
          </p>
          {Object.entries(result.extractions).map(([fieldType, fields]) => {
            if (!fields || fields.length === 0) return null;
            return (
              <div key={fieldType}>
                <h4 className="text-xs font-medium text-gray-600 dark:text-gray-300 mb-1 flex items-center gap-1.5">
                  <span>{FIELD_ICONS[fieldType] || ''}</span>
                  {fieldTypeLabel(fieldType)} ({fields.length})
                </h4>
                <div className="space-y-0.5">
                  {fields.map((field, idx) => (
                    <FieldRow key={`${fieldType}-${idx}`} field={field} onConfirm={onConfirm} onReject={onReject} t={t} />
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {result && result.total_fields === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          {t('doc_extraction.no_fields') || 'Aucun champ extrait'}
        </p>
      )}
    </div>
  );
}

export default DocumentExtractionPreview;
