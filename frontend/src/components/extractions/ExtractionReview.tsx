import { useState, useCallback, useRef } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { toast } from '@/store/toastStore';
import { cn, formatDate } from '@/utils/formatters';
import {
  getExtraction,
  reviewExtraction,
  applyExtraction,
  rejectExtraction,
  recordCorrection,
  type ExtractedData,
  type ExtractedSample,
} from '@/api/extractions';
import { ArrowLeft, CheckCircle2, XCircle, AlertTriangle, Loader2, Shield, FileText } from 'lucide-react';
import { ConfidenceIndicator } from '@/components/ConfidenceIndicator';
import { statusBadge } from './shared';
import { MetadataSection } from './MetadataSection';
import { ScopeSection } from './ScopeSection';
import { SamplesTable } from './SamplesTable';
import { ConclusionsSection } from './ConclusionsSection';
import { RegulatorySection } from './RegulatorySection';

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

export default function ExtractionReview() {
  const { t } = useTranslation();
  const { buildingId, extractionId } = useParams<{ buildingId: string; extractionId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  // Fetch extraction
  const {
    data: extraction,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['extraction', extractionId],
    queryFn: () => getExtraction(extractionId!),
    enabled: !!extractionId,
  });

  // Local working copy of extracted data (user edits this)
  const [localData, setLocalData] = useState<ExtractedData | null>(null);
  // Track original data for showing diffs
  const [originalData, setOriginalData] = useState<ExtractedData | null>(null);

  // Reject modal state
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');

  // Debounce timer ref for corrections
  const correctionTimer = useRef<ReturnType<typeof setTimeout>>();

  // Initialize local data from fetched extraction
  if (extraction?.extracted_data && localData === null) {
    setLocalData(structuredClone(extraction.extracted_data));
    setOriginalData(structuredClone(extraction.extracted_data));
  }

  // Mutations
  const applyMutation = useMutation({
    mutationFn: async () => {
      if (!extractionId || !localData) return;
      // First save any pending edits via review
      await reviewExtraction(extractionId, localData);
      // Then apply
      return applyExtraction(extractionId);
    },
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['extraction', extractionId] });
      toast(t('extraction.applied') || 'Extraction appliquee au dossier');
      if (result?.diagnostic_id && buildingId) {
        navigate(`/buildings/${buildingId}`);
      }
    },
    onError: (err: any) => {
      toast(err?.response?.data?.detail || err?.message || 'Erreur');
    },
  });

  const rejectMutation = useMutation({
    mutationFn: () => rejectExtraction(extractionId!, rejectReason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['extraction', extractionId] });
      setShowRejectModal(false);
      toast(t('extraction.rejected') || 'Extraction rejetee');
      if (buildingId) navigate(`/buildings/${buildingId}`);
    },
    onError: (err: any) => {
      toast(err?.response?.data?.detail || err?.message || 'Erreur');
    },
  });

  // Field change handler — updates local state + fires correction API (debounced)
  const handleFieldChange = useCallback(
    (fieldPath: string, newValue: unknown) => {
      if (!localData || !extractionId) return;

      // Get old value from current local data by walking the dot-path
      const parts = fieldPath.split('.');
      let oldVal: unknown = localData;
      for (const p of parts) {
        if (oldVal && typeof oldVal === 'object') {
          oldVal = (oldVal as Record<string, unknown>)[p];
        } else {
          oldVal = undefined;
        }
      }

      // Apply to local data
      setLocalData((prev) => {
        if (!prev) return prev;
        const copy = structuredClone(prev);
        let target: Record<string, unknown> = copy as unknown as Record<string, unknown>;
        for (let i = 0; i < parts.length - 1; i++) {
          if (target[parts[i]] && typeof target[parts[i]] === 'object') {
            target = target[parts[i]] as Record<string, unknown>;
          }
        }
        target[parts[parts.length - 1]] = newValue;
        return copy as ExtractedData;
      });

      // Debounce correction API call
      if (correctionTimer.current) clearTimeout(correctionTimer.current);
      correctionTimer.current = setTimeout(() => {
        recordCorrection(extractionId, fieldPath, oldVal, newValue).catch(() => {
          // Silent — correction is a feedback signal, not critical
        });
      }, 500);
    },
    [localData, extractionId],
  );

  // Sample-level field change
  const handleSampleChange = useCallback(
    (index: number, field: keyof ExtractedSample, newValue: unknown) => {
      handleFieldChange(`samples.${index}.${field}`, newValue);
    },
    [handleFieldChange],
  );

  // Add a new empty sample
  const addSample = useCallback(() => {
    setLocalData((prev) => {
      if (!prev) return prev;
      const copy = structuredClone(prev);
      copy.samples.push({
        sample_id: `manual_${copy.samples.length + 1}`,
        location: null,
        material_type: null,
        result: 'not_tested',
        concentration: null,
        unit: null,
        threshold_exceeded: null,
        confidence: 1.0, // manual = full confidence
      });
      return copy;
    });
  }, []);

  // Scope list changes
  const handleScopeListChange = useCallback(
    (field: 'zones_covered' | 'zones_excluded', index: number, value: string) => {
      handleFieldChange(`scope.${field}.${index}`, value);
    },
    [handleFieldChange],
  );

  const addScopeItem = useCallback((field: 'zones_covered' | 'zones_excluded') => {
    setLocalData((prev) => {
      if (!prev) return prev;
      const copy = structuredClone(prev);
      copy.scope[field].push('');
      return copy;
    });
  }, []);

  const removeScopeItem = useCallback((field: 'zones_covered' | 'zones_excluded', index: number) => {
    setLocalData((prev) => {
      if (!prev) return prev;
      const copy = structuredClone(prev);
      copy.scope[field].splice(index, 1);
      return copy;
    });
  }, []);

  // Loading / error states
  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  if (isError || !extraction || !localData) {
    return (
      <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-8 text-center">
        <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
        <p className="text-red-700 dark:text-red-300">{t('extraction.not_found') || 'Extraction introuvable'}</p>
        <Link
          to={buildingId ? `/buildings/${buildingId}` : '/buildings'}
          className="text-sm text-red-600 dark:text-red-400 hover:underline mt-2 inline-block"
        >
          Retour
        </Link>
      </div>
    );
  }

  const canEdit = extraction.status === 'draft' || extraction.status === 'reviewed';
  const confidence = extraction.confidence ?? 0;
  const badge = statusBadge(extraction.status);

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      {/* Back link */}
      <Link
        to={buildingId ? `/buildings/${buildingId}` : '/buildings'}
        className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
      >
        <ArrowLeft className="w-4 h-4" />
        {t('building.backToList') || 'Retour'}
      </Link>

      {/* Header card */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold text-gray-900 dark:text-white">
                {t('extraction.review_title') || "Revue de l'extraction"}
              </h1>
              <span className={cn('px-2.5 py-0.5 text-xs font-medium rounded-full', badge.className)}>
                {badge.label}
              </span>
            </div>
            <div className="flex items-center gap-4 text-sm text-gray-500 dark:text-slate-400">
              <span className="flex items-center gap-1">
                <FileText className="w-4 h-4" />
                Doc: {extraction.document_id.slice(0, 8)}...
              </span>
              <span>
                {t('extraction.created_at') || 'Cree le'}: {formatDate(extraction.created_at)}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {/* Confidence gauge */}
            <ConfidenceIndicator value={confidence} size="md" />
          </div>
        </div>
      </div>

      {/* Section 1: Metadata */}
      <MetadataSection extracted={localData} original={originalData} onFieldChange={handleFieldChange} />

      {/* Section 2: Scope */}
      <ScopeSection
        extracted={localData}
        original={originalData}
        onFieldChange={handleFieldChange}
        onScopeListChange={handleScopeListChange}
        onAddScopeItem={addScopeItem}
        onRemoveScopeItem={removeScopeItem}
      />

      {/* Section 3: Samples */}
      <SamplesTable
        extracted={localData}
        onSampleChange={handleSampleChange}
        onAddSample={addSample}
        canEdit={canEdit}
      />

      {/* Section 4: Conclusions */}
      <ConclusionsSection extracted={localData} original={originalData} onFieldChange={handleFieldChange} />

      {/* Section 5: Regulatory context */}
      <RegulatorySection extracted={localData} original={originalData} onFieldChange={handleFieldChange} />

      {/* Footer: Actions + Provenance */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        {/* Provenance info */}
        <div className="flex flex-wrap items-center gap-3 mb-6 text-xs text-gray-500 dark:text-slate-400">
          <span className="flex items-center gap-1">
            <Shield className="w-3.5 h-3.5" />
            Methode: rule_based_v1
          </span>
          <span>Extraction: {formatDate(extraction.created_at)}</span>
          {(extraction.corrections?.length ?? 0) > 0 && (
            <span>{extraction.corrections!.length} correction(s) enregistree(s)</span>
          )}
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 text-xs font-medium">
            <AlertTriangle className="w-3 h-3" />
            Necessite revue humaine
          </span>
        </div>

        {/* Action buttons */}
        {canEdit ? (
          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => applyMutation.mutate()}
              disabled={applyMutation.isPending}
              className={cn(
                'inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg transition-colors',
                'bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed',
              )}
            >
              {applyMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4" />
              )}
              Appliquer au dossier
            </button>
            <button
              onClick={() => setShowRejectModal(true)}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg transition-colors bg-white dark:bg-slate-700 text-red-600 dark:text-red-400 border border-red-300 dark:border-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
            >
              <XCircle className="w-4 h-4" />
              Rejeter
            </button>
            <Link
              to={buildingId ? `/buildings/${buildingId}` : '/buildings'}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg transition-colors bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-200 border border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600"
            >
              Retour
            </Link>
          </div>
        ) : (
          <div className="flex items-center gap-3">
            <Link
              to={buildingId ? `/buildings/${buildingId}` : '/buildings'}
              className="inline-flex items-center gap-2 px-5 py-2.5 text-sm font-medium rounded-lg transition-colors bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-200 border border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600"
            >
              Retour
            </Link>
            <span className="text-sm text-gray-500 dark:text-slate-400">
              {extraction.status === 'applied'
                ? 'Cette extraction a deja ete appliquee.'
                : 'Cette extraction a ete rejetee.'}
            </span>
          </div>
        )}
      </div>

      {/* Reject modal */}
      {showRejectModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-xl w-full max-w-md mx-4">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-3">Rejeter l'extraction</h3>
            <p className="text-sm text-gray-500 dark:text-slate-400 mb-4">
              Indiquez la raison du rejet. Ce retour alimentera le moteur d'apprentissage.
            </p>
            <textarea
              value={rejectReason}
              onChange={(e) => setRejectReason(e.target.value)}
              rows={3}
              className="w-full px-3 py-2 text-sm rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 focus:ring-2 focus:ring-red-500 outline-none mb-4"
              placeholder="Raison du rejet..."
              autoFocus
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowRejectModal(false)}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-white dark:bg-slate-700 text-gray-700 dark:text-slate-200 border border-gray-300 dark:border-slate-600 hover:bg-gray-50 dark:hover:bg-slate-600"
              >
                Annuler
              </button>
              <button
                onClick={() => rejectMutation.mutate()}
                disabled={rejectMutation.isPending}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              >
                {rejectMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                Confirmer le rejet
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
