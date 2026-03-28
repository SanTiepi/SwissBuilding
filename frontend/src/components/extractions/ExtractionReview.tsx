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
import {
  ArrowLeft,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Plus,
  Shield,
  FileText,
  Beaker,
  Scale,
  ClipboardList,
} from 'lucide-react';
import { ConfidenceIndicator } from '@/components/ConfidenceIndicator';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------


function statusBadge(status: string): { className: string; label: string } {
  switch (status) {
    case 'draft':
      return {
        className: 'bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300',
        label: 'Brouillon',
      };
    case 'reviewed':
      return {
        className: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300',
        label: 'Revu',
      };
    case 'applied':
      return {
        className: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300',
        label: 'Applique',
      };
    case 'rejected':
      return {
        className: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300',
        label: 'Rejete',
      };
    default:
      return {
        className: 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300',
        label: status,
      };
  }
}

function resultBadge(result: string): { className: string; label: string } {
  switch (result) {
    case 'positive':
      return { className: 'bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300', label: 'Positif' };
    case 'negative':
      return { className: 'bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300', label: 'Negatif' };
    case 'trace':
      return { className: 'bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300', label: 'Trace' };
    default:
      return { className: 'bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300', label: 'Non teste' };
  }
}

const REPORT_TYPES = [
  { value: 'asbestos', label: 'Amiante' },
  { value: 'pcb', label: 'PCB' },
  { value: 'lead', label: 'Plomb' },
  { value: 'hap', label: 'HAP' },
  { value: 'radon', label: 'Radon' },
  { value: 'pfas', label: 'PFAS' },
  { value: 'multi', label: 'Multi-polluants' },
  { value: 'unknown', label: 'Inconnu' },
];

const OVERALL_RESULTS = [
  { value: 'presence', label: 'Presence' },
  { value: 'absence', label: 'Absence' },
  { value: 'partial', label: 'Partiel' },
];

const RISK_LEVELS = [
  { value: 'low', label: 'Faible' },
  { value: 'medium', label: 'Moyen' },
  { value: 'high', label: 'Eleve' },
  { value: 'critical', label: 'Critique' },
  { value: 'unknown', label: 'Inconnu' },
];

const WORK_CATEGORIES = [
  { value: '', label: 'Non defini' },
  { value: 'minor', label: 'Mineurs' },
  { value: 'medium', label: 'Moyens' },
  { value: 'major', label: 'Majeurs' },
];

const SAMPLE_RESULTS = [
  { value: 'positive', label: 'Positif' },
  { value: 'negative', label: 'Negatif' },
  { value: 'trace', label: 'Trace' },
  { value: 'not_tested', label: 'Non teste' },
];

// ---------------------------------------------------------------------------
// Editable field components
// ---------------------------------------------------------------------------

interface EditableTextProps {
  value: string | null;
  originalValue: string | null;
  onChange: (v: string) => void;
  placeholder?: string;
  className?: string;
}

function EditableText({ value, originalValue, onChange, placeholder, className }: EditableTextProps) {
  const isModified = value !== originalValue;
  return (
    <div className="relative">
      <input
        type="text"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className={cn(
          'w-full px-3 py-2 text-sm rounded-lg border transition-colors',
          'bg-white dark:bg-slate-900 border-gray-200 dark:border-slate-600',
          'focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none',
          isModified && 'border-amber-400 dark:border-amber-500 ring-1 ring-amber-200 dark:ring-amber-800',
          className,
        )}
      />
      {isModified && originalValue != null && (
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5 line-through">{originalValue}</p>
      )}
    </div>
  );
}

interface EditableSelectProps {
  value: string | null;
  originalValue: string | null;
  options: { value: string; label: string }[];
  onChange: (v: string) => void;
  className?: string;
}

function EditableSelect({ value, originalValue, options, onChange, className }: EditableSelectProps) {
  const isModified = value !== originalValue;
  return (
    <div className="relative">
      <select
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          'w-full px-3 py-2 text-sm rounded-lg border transition-colors',
          'bg-white dark:bg-slate-900 border-gray-200 dark:border-slate-600',
          'focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none',
          isModified && 'border-amber-400 dark:border-amber-500 ring-1 ring-amber-200 dark:ring-amber-800',
          className,
        )}
      >
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {isModified && originalValue != null && (
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5 line-through">
          {options.find((o) => o.value === originalValue)?.label ?? originalValue}
        </p>
      )}
    </div>
  );
}

interface EditableDateProps {
  value: string | null;
  originalValue: string | null;
  onChange: (v: string) => void;
  className?: string;
}

function EditableDate({ value, originalValue, onChange, className }: EditableDateProps) {
  const isModified = value !== originalValue;
  return (
    <div className="relative">
      <input
        type="date"
        value={value ?? ''}
        onChange={(e) => onChange(e.target.value)}
        className={cn(
          'w-full px-3 py-2 text-sm rounded-lg border transition-colors',
          'bg-white dark:bg-slate-900 border-gray-200 dark:border-slate-600',
          'focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none',
          isModified && 'border-amber-400 dark:border-amber-500 ring-1 ring-amber-200 dark:ring-amber-800',
          className,
        )}
      />
      {isModified && originalValue != null && (
        <p className="text-xs text-gray-400 dark:text-slate-500 mt-0.5 line-through">{originalValue}</p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Section components
// ---------------------------------------------------------------------------

function SectionHeader({ icon: Icon, title }: { icon: React.ElementType; title: string }) {
  return (
    <h3 className="flex items-center gap-2 text-base font-semibold text-gray-800 dark:text-slate-100 mb-4">
      <Icon className="w-5 h-5 text-red-500" />
      {title}
    </h3>
  );
}

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

  const addScopeItem = useCallback(
    (field: 'zones_covered' | 'zones_excluded') => {
      setLocalData((prev) => {
        if (!prev) return prev;
        const copy = structuredClone(prev);
        copy.scope[field].push('');
        return copy;
      });
    },
    [],
  );

  const removeScopeItem = useCallback(
    (field: 'zones_covered' | 'zones_excluded', index: number) => {
      setLocalData((prev) => {
        if (!prev) return prev;
        const copy = structuredClone(prev);
        copy.scope[field].splice(index, 1);
        return copy;
      });
    },
    [],
  );

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
                {t('extraction.review_title') || 'Revue de l\'extraction'}
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
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <SectionHeader icon={FileText} title={t('extraction.section_metadata') || 'Metadonnees du rapport'} />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              Type de rapport
            </label>
            <EditableSelect
              value={localData.report_type}
              originalValue={originalData?.report_type ?? null}
              options={REPORT_TYPES}
              onChange={(v) => handleFieldChange('report_type', v)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Laboratoire</label>
            <EditableText
              value={localData.lab_name}
              originalValue={originalData?.lab_name ?? null}
              onChange={(v) => handleFieldChange('lab_name', v)}
              placeholder="Nom du laboratoire"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Reference</label>
            <EditableText
              value={localData.lab_reference}
              originalValue={originalData?.lab_reference ?? null}
              onChange={(v) => handleFieldChange('lab_reference', v)}
              placeholder="Numero de reference"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              Date du rapport
            </label>
            <EditableDate
              value={localData.report_date}
              originalValue={originalData?.report_date ?? null}
              onChange={(v) => handleFieldChange('report_date', v)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              Date de validite
            </label>
            <EditableDate
              value={localData.validity_date}
              originalValue={originalData?.validity_date ?? null}
              onChange={(v) => handleFieldChange('validity_date', v)}
            />
          </div>
        </div>
      </div>

      {/* Section 2: Scope */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <SectionHeader icon={ClipboardList} title={t('extraction.section_scope') || 'Perimetre'} />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
          {/* Zones covered */}
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">
              Zones couvertes
            </label>
            <div className="space-y-2">
              {localData.scope.zones_covered.map((zone, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={zone}
                    onChange={(e) => handleScopeListChange('zones_covered', i, e.target.value)}
                    className="flex-1 px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 focus:ring-2 focus:ring-red-500 outline-none"
                  />
                  <button
                    onClick={() => removeScopeItem('zones_covered', i)}
                    className="text-gray-400 hover:text-red-500 dark:text-slate-500 dark:hover:text-red-400"
                  >
                    <XCircle className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button
                onClick={() => addScopeItem('zones_covered')}
                className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:underline"
              >
                <Plus className="w-3 h-3" /> Ajouter
              </button>
            </div>
          </div>

          {/* Zones excluded */}
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-2">Zones exclues</label>
            <div className="space-y-2">
              {localData.scope.zones_excluded.map((zone, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={zone}
                    onChange={(e) => handleScopeListChange('zones_excluded', i, e.target.value)}
                    className="flex-1 px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 focus:ring-2 focus:ring-red-500 outline-none"
                  />
                  <button
                    onClick={() => removeScopeItem('zones_excluded', i)}
                    className="text-gray-400 hover:text-red-500 dark:text-slate-500 dark:hover:text-red-400"
                  >
                    <XCircle className="w-4 h-4" />
                  </button>
                </div>
              ))}
              <button
                onClick={() => addScopeItem('zones_excluded')}
                className="flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:underline"
              >
                <Plus className="w-3 h-3" /> Ajouter
              </button>
            </div>
          </div>

          {/* Counts */}
          <div className="flex gap-6">
            <div>
              <span className="text-xs text-gray-500 dark:text-slate-400">Elements echantillonnes</span>
              <p className="text-lg font-semibold text-gray-900 dark:text-white">
                {localData.scope.elements_sampled}
              </p>
            </div>
            <div>
              <span className="text-xs text-gray-500 dark:text-slate-400">Elements positifs</span>
              <p className="text-lg font-semibold text-red-600 dark:text-red-400">
                {localData.scope.elements_positive}
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Section 3: Samples */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <SectionHeader icon={Beaker} title={t('extraction.section_samples') || 'Echantillons'} />
        {localData.samples.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-slate-700">
                  <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">ID</th>
                  <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                    Localisation
                  </th>
                  <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                    Materiau
                  </th>
                  <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                    Resultat
                  </th>
                  <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                    Concentration
                  </th>
                  <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">Unite</th>
                  <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                    Seuil depasse
                  </th>
                  <th className="text-center py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                    Confiance
                  </th>
                </tr>
              </thead>
              <tbody>
                {localData.samples.map((sample, idx) => {
                  const rb = resultBadge(sample.result);
                  return (
                    <tr
                      key={idx}
                      className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-gray-50 dark:hover:bg-slate-700/30"
                    >
                      <td className="py-2 px-2">
                        <input
                          type="text"
                          value={sample.sample_id}
                          onChange={(e) => handleSampleChange(idx, 'sample_id', e.target.value)}
                          className="w-24 px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                        />
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="text"
                          value={sample.location ?? ''}
                          onChange={(e) => handleSampleChange(idx, 'location', e.target.value || null)}
                          className="w-32 px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                          placeholder="-"
                        />
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="text"
                          value={sample.material_type ?? ''}
                          onChange={(e) => handleSampleChange(idx, 'material_type', e.target.value || null)}
                          className="w-32 px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                          placeholder="-"
                        />
                      </td>
                      <td className="py-2 px-2">
                        <select
                          value={sample.result}
                          onChange={(e) => handleSampleChange(idx, 'result', e.target.value)}
                          className={cn(
                            'px-2 py-1 text-xs rounded font-medium border-0 outline-none focus:ring-1 focus:ring-red-500',
                            rb.className,
                          )}
                        >
                          {SAMPLE_RESULTS.map((r) => (
                            <option key={r.value} value={r.value}>
                              {r.label}
                            </option>
                          ))}
                        </select>
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="number"
                          step="any"
                          value={sample.concentration ?? ''}
                          onChange={(e) =>
                            handleSampleChange(
                              idx,
                              'concentration',
                              e.target.value ? parseFloat(e.target.value) : null,
                            )
                          }
                          className="w-24 px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                          placeholder="-"
                        />
                      </td>
                      <td className="py-2 px-2">
                        <input
                          type="text"
                          value={sample.unit ?? ''}
                          onChange={(e) => handleSampleChange(idx, 'unit', e.target.value || null)}
                          className="w-20 px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                          placeholder="-"
                        />
                      </td>
                      <td className="py-2 px-2 text-center">
                        <select
                          value={sample.threshold_exceeded === null ? '' : sample.threshold_exceeded ? 'true' : 'false'}
                          onChange={(e) =>
                            handleSampleChange(
                              idx,
                              'threshold_exceeded',
                              e.target.value === '' ? null : e.target.value === 'true',
                            )
                          }
                          className="px-2 py-1 text-xs rounded border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-900 outline-none focus:ring-1 focus:ring-red-500"
                        >
                          <option value="">-</option>
                          <option value="true">Oui</option>
                          <option value="false">Non</option>
                        </select>
                      </td>
                      <td className="py-2 px-2 text-center">
                        <div className="flex items-center justify-center">
                          <ConfidenceIndicator value={sample.confidence} size="sm" showValue />
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-gray-500 dark:text-slate-400 text-center py-4">Aucun echantillon extrait</p>
        )}
        {canEdit && (
          <button
            onClick={addSample}
            className="mt-3 flex items-center gap-1 text-sm text-red-600 dark:text-red-400 hover:underline"
          >
            <Plus className="w-4 h-4" /> Ajouter un echantillon
          </button>
        )}
      </div>

      {/* Section 4: Conclusions */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <SectionHeader icon={CheckCircle2} title={t('extraction.section_conclusions') || 'Conclusions'} />
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              Resultat global
            </label>
            <EditableSelect
              value={localData.conclusions.overall_result}
              originalValue={originalData?.conclusions.overall_result ?? null}
              options={OVERALL_RESULTS}
              onChange={(v) => handleFieldChange('conclusions.overall_result', v)}
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              Niveau de risque
            </label>
            <EditableSelect
              value={localData.conclusions.risk_level}
              originalValue={originalData?.conclusions.risk_level ?? null}
              options={RISK_LEVELS}
              onChange={(v) => handleFieldChange('conclusions.risk_level', v)}
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              Recommandations
            </label>
            <textarea
              value={localData.conclusions.recommendations.join('\n')}
              onChange={(e) =>
                handleFieldChange(
                  'conclusions.recommendations',
                  e.target.value.split('\n').filter((l) => l.trim()),
                )
              }
              rows={3}
              className={cn(
                'w-full px-3 py-2 text-sm rounded-lg border transition-colors',
                'bg-white dark:bg-slate-900 border-gray-200 dark:border-slate-600',
                'focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none',
              )}
              placeholder="Une recommandation par ligne"
            />
          </div>
        </div>
      </div>

      {/* Section 5: Regulatory context */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        <SectionHeader icon={Scale} title={t('extraction.section_regulatory') || 'Contexte reglementaire'} />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              Reference reglementaire
            </label>
            <EditableText
              value={localData.regulatory_context.regulation_ref}
              originalValue={originalData?.regulatory_context.regulation_ref ?? null}
              onChange={(v) => handleFieldChange('regulatory_context.regulation_ref', v)}
              placeholder="Ex: OTConst Art. 60a"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">Seuil applique</label>
            <EditableText
              value={localData.regulatory_context.threshold_applied}
              originalValue={originalData?.regulatory_context.threshold_applied ?? null}
              onChange={(v) => handleFieldChange('regulatory_context.threshold_applied', v)}
              placeholder="Ex: 50.0 mg/kg"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-500 dark:text-slate-400 mb-1">
              Categorie de travaux
            </label>
            <EditableSelect
              value={localData.regulatory_context.work_category ?? ''}
              originalValue={originalData?.regulatory_context.work_category ?? ''}
              options={WORK_CATEGORIES}
              onChange={(v) => handleFieldChange('regulatory_context.work_category', v || null)}
            />
          </div>
        </div>
      </div>

      {/* Footer: Actions + Provenance */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 shadow-sm">
        {/* Provenance info */}
        <div className="flex flex-wrap items-center gap-3 mb-6 text-xs text-gray-500 dark:text-slate-400">
          <span className="flex items-center gap-1">
            <Shield className="w-3.5 h-3.5" />
            Methode: rule_based_v1
          </span>
          <span>
            Extraction: {formatDate(extraction.created_at)}
          </span>
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
