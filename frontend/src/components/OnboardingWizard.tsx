import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  X,
  Search,
  CheckCircle2,
  Circle,
  ChevronRight,
  ChevronLeft,
  Loader2,
  Building2,
  MapPin,
  Calendar,
  Layers,
  Ruler,
  AlertCircle,
  Sparkles,
  ArrowRight,
} from 'lucide-react';
import { cn } from '@/utils/formatters';
import { FileUpload } from '@/components/FileUpload';
import { onboardingApi, type EgidLookupResult, type OnboardingCreateRequest } from '@/api/onboarding';
import { documentsApi } from '@/api/documents';
import { completenessApi } from '@/api/completeness';
import { readinessApi } from '@/api/readiness';
import type { CompletenessResult, ReadinessAssessment } from '@/types';

interface OnboardingWizardProps {
  open: boolean;
  onClose: () => void;
}

const STEPS = [
  { key: 'identify', label: 'Identifier' },
  { key: 'enrich', label: 'Enrichissement' },
  { key: 'documents', label: 'Documents' },
  { key: 'evaluate', label: 'Evaluation' },
] as const;

// Step keys derived from STEPS constant

interface UploadedFile {
  name: string;
  category: string;
}

const DOC_CATEGORIES = [
  { key: 'diagnostic_asbestos', label: 'Diagnostic amiante (PDF)', type: 'diagnostic_report' },
  { key: 'diagnostic_pcb', label: 'Diagnostic PCB (PDF)', type: 'diagnostic_report' },
  { key: 'diagnostic_lead', label: 'Diagnostic plomb (PDF)', type: 'diagnostic_report' },
  { key: 'waste_plan', label: 'Plan de gestion des dechets', type: 'waste_management_plan' },
  { key: 'suva_notification', label: 'Notification SUVA', type: 'notification' },
  { key: 'other', label: 'Autres documents', type: 'other' },
] as const;

export function OnboardingWizard({ open, onClose }: OnboardingWizardProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const [step, setStep] = useState(0);
  const [egidInput, setEgidInput] = useState('');
  const [lookupLoading, setLookupLoading] = useState(false);
  const [lookupError, setLookupError] = useState<string | null>(null);
  const [lookupResult, setLookupResult] = useState<EgidLookupResult | null>(null);

  const [createdBuildingId, setCreatedBuildingId] = useState<string | null>(null);
  const [createLoading, setCreateLoading] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [uploadingCategory, setUploadingCategory] = useState<string | null>(null);

  const [evalLoading, setEvalLoading] = useState(false);
  const [completeness, setCompleteness] = useState<CompletenessResult | null>(null);
  const [readiness, setReadiness] = useState<ReadinessAssessment[] | null>(null);
  const [evalDone, setEvalDone] = useState(false);

  const currentStep = STEPS[step];

  const resetWizard = useCallback(() => {
    setStep(0);
    setEgidInput('');
    setLookupLoading(false);
    setLookupError(null);
    setLookupResult(null);
    setCreatedBuildingId(null);
    setCreateLoading(false);
    setCreateError(null);
    setUploadedFiles([]);
    setUploadingCategory(null);
    setEvalLoading(false);
    setCompleteness(null);
    setReadiness(null);
    setEvalDone(false);
  }, []);

  const handleClose = useCallback(() => {
    resetWizard();
    onClose();
  }, [onClose, resetWizard]);

  // Step 1: EGID lookup
  const handleLookup = useCallback(async () => {
    const egid = parseInt(egidInput, 10);
    if (isNaN(egid) || egid <= 0) {
      setLookupError('Veuillez entrer un numero EGID valide (ex: 1234567)');
      return;
    }
    setLookupLoading(true);
    setLookupError(null);
    setLookupResult(null);

    try {
      const result = await onboardingApi.lookupEgid(egid);
      if (!result.found) {
        setLookupError(`Aucun batiment trouve pour EGID ${egid}. Verifiez le numero et reessayez.`);
      } else {
        setLookupResult(result);
      }
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setLookupError(e?.response?.data?.detail || e?.message || 'Erreur lors de la recherche');
    } finally {
      setLookupLoading(false);
    }
  }, [egidInput]);

  // Step 2 -> Step 3: Create building
  const handleCreateBuilding = useCallback(async () => {
    if (!lookupResult || !lookupResult.found) return;
    setCreateLoading(true);
    setCreateError(null);

    try {
      const payload: OnboardingCreateRequest = {
        egid: lookupResult.egid,
        address: lookupResult.address || `EGID ${lookupResult.egid}`,
        postal_code: lookupResult.postal_code || '0000',
        city: lookupResult.city || 'Inconnu',
        canton: lookupResult.canton || 'VD',
        municipality_ofs: lookupResult.municipality_ofs,
        latitude: lookupResult.latitude,
        longitude: lookupResult.longitude,
        construction_year: lookupResult.construction_year,
        building_type: lookupResult.building_type || 'mixed',
        floors_above: lookupResult.floors_above,
        surface_area_m2: lookupResult.surface_area_m2,
        source_metadata: lookupResult.source_metadata,
      };

      const result = await onboardingApi.createBuilding(payload);
      setCreatedBuildingId(result.id);
      queryClient.invalidateQueries({ queryKey: ['buildings'] });
      setStep(2);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } }; message?: string };
      setCreateError(e?.response?.data?.detail || e?.message || 'Erreur lors de la creation');
    } finally {
      setCreateLoading(false);
    }
  }, [lookupResult, queryClient]);

  // Step 3: Upload document
  const handleUploadFile = useCallback(
    async (file: File, category: string, docType: string) => {
      if (!createdBuildingId) return;
      setUploadingCategory(category);
      try {
        await documentsApi.upload(createdBuildingId, file, docType);
        setUploadedFiles((prev) => [...prev, { name: file.name, category }]);
      } catch {
        // Silent fail — user can retry
      } finally {
        setUploadingCategory(null);
      }
    },
    [createdBuildingId],
  );

  // Step 4: Run evaluation
  const handleEvaluate = useCallback(async () => {
    if (!createdBuildingId) return;
    setEvalLoading(true);

    try {
      const [comp, read] = await Promise.allSettled([
        completenessApi.evaluate(createdBuildingId),
        readinessApi.evaluateAll(createdBuildingId),
      ]);

      if (comp.status === 'fulfilled') setCompleteness(comp.value);
      if (read.status === 'fulfilled') setReadiness(read.value);
    } catch {
      // Non-blocking
    } finally {
      setEvalLoading(false);
      setEvalDone(true);
    }
  }, [createdBuildingId]);

  // Navigation to building detail
  const handleViewDossier = useCallback(() => {
    if (!createdBuildingId) return;
    // Mark onboarding as completed for this building so OverviewTab banner doesn't show
    try {
      localStorage.setItem(`baticonnect-onboarding-dismissed-${createdBuildingId}`, '1');
    } catch {
      // silent
    }
    queryClient.invalidateQueries({ queryKey: ['buildings'] });
    handleClose();
    navigate(`/buildings/${createdBuildingId}`);
  }, [createdBuildingId, navigate, queryClient, handleClose]);

  if (!open) return null;

  const completenessPct = completeness ? Math.round(completeness.overall_score) : 0;
  const completenessTotal = completeness ? completeness.checks.length : 0;
  const completenessCompleted = completeness ? completeness.checks.filter((c) => c.status === 'complete').length : 0;
  const completenessMissing = completeness ? completeness.missing_items.length : 0;

  const readinessVerdict =
    readiness && readiness.length > 0
      ? readiness.some((r) => r.status === 'blocked')
        ? 'blocked'
        : readiness.some((r) => r.status === 'not_ready' || r.status === 'conditionally_ready')
          ? 'conditionally_ready'
          : 'ready'
      : null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="relative w-full max-w-2xl mx-4 bg-white dark:bg-slate-900 rounded-2xl shadow-2xl overflow-hidden max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl bg-red-100 dark:bg-red-900/40 flex items-center justify-center">
              <Building2 className="w-5 h-5 text-red-600 dark:text-red-400" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">Ajouter un batiment</h2>
              <p className="text-xs text-gray-500 dark:text-slate-400">Assistant de configuration guidee</p>
            </div>
          </div>
          <button
            onClick={handleClose}
            className="p-2 text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-300 rounded-lg transition-colors"
            aria-label="Fermer"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Progress Steps */}
        <div className="px-6 py-3 border-b border-gray-100 dark:border-slate-800">
          <div className="flex items-center justify-between">
            {STEPS.map((s, i) => (
              <div key={s.key} className="flex items-center gap-2">
                <div
                  className={cn(
                    'w-7 h-7 rounded-full flex items-center justify-center text-xs font-semibold transition-all',
                    i < step
                      ? 'bg-green-500 text-white'
                      : i === step
                        ? 'bg-red-600 text-white'
                        : 'bg-gray-200 dark:bg-slate-700 text-gray-500 dark:text-slate-400',
                  )}
                >
                  {i < step ? <CheckCircle2 className="w-4 h-4" /> : i + 1}
                </div>
                <span
                  className={cn(
                    'text-xs font-medium hidden sm:block',
                    i <= step ? 'text-gray-900 dark:text-white' : 'text-gray-400 dark:text-slate-500',
                  )}
                >
                  {s.label}
                </span>
                {i < STEPS.length - 1 && (
                  <div
                    className={cn(
                      'w-8 lg:w-12 h-0.5 mx-1',
                      i < step ? 'bg-green-500' : 'bg-gray-200 dark:bg-slate-700',
                    )}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {/* Step 1: Identify */}
          {currentStep.key === 'identify' && (
            <div className="space-y-5">
              <div>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">Identifier le batiment</h3>
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  Entrez le numero EGID (ex: 1234567) pour retrouver automatiquement les informations du batiment.
                </p>
              </div>

              <div className="flex gap-3">
                <div className="flex-1">
                  <label
                    htmlFor="egid-input"
                    className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1"
                  >
                    Numero EGID
                  </label>
                  <input
                    id="egid-input"
                    type="text"
                    value={egidInput}
                    onChange={(e) => {
                      setEgidInput(e.target.value.replace(/\D/g, ''));
                      setLookupError(null);
                    }}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') handleLookup();
                    }}
                    placeholder="Ex: 1234567"
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-800 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none transition-all"
                    data-testid="onboarding-egid-input"
                  />
                </div>
                <div className="flex items-end">
                  <button
                    onClick={handleLookup}
                    disabled={lookupLoading || !egidInput}
                    className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                    data-testid="onboarding-search-btn"
                  >
                    {lookupLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                    Rechercher
                  </button>
                </div>
              </div>

              {lookupError && (
                <div className="flex items-start gap-2 px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-red-700 dark:text-red-300">{lookupError}</p>
                </div>
              )}

              {lookupResult && lookupResult.found && (
                <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-xl p-4 space-y-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
                    <span className="text-sm font-semibold text-green-800 dark:text-green-300">Batiment trouve</span>
                  </div>
                  <div className="grid grid-cols-2 gap-3 text-sm">
                    {lookupResult.address && (
                      <div className="flex items-center gap-2">
                        <MapPin className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-700 dark:text-slate-300">{lookupResult.address}</span>
                      </div>
                    )}
                    {lookupResult.city && (
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-700 dark:text-slate-300">
                          {lookupResult.postal_code} {lookupResult.city}
                        </span>
                      </div>
                    )}
                    {lookupResult.construction_year && (
                      <div className="flex items-center gap-2">
                        <Calendar className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-700 dark:text-slate-300">
                          Construit en {lookupResult.construction_year}
                        </span>
                      </div>
                    )}
                    {lookupResult.canton && (
                      <div className="flex items-center gap-2">
                        <Layers className="w-4 h-4 text-gray-400" />
                        <span className="text-gray-700 dark:text-slate-300">Canton {lookupResult.canton}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 2: Enrichment */}
          {currentStep.key === 'enrich' && lookupResult && (
            <div className="space-y-5">
              <div>
                <div className="flex items-center gap-2 mb-1">
                  <Sparkles className="w-5 h-5 text-amber-500" />
                  <h3 className="text-base font-semibold text-gray-900 dark:text-white">Enrichissement automatique</h3>
                </div>
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  Voici les donnees que nous avons automatiquement retrouvees dans les sources publiques suisses.
                </p>
              </div>

              {/* Data checklist */}
              <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl divide-y divide-gray-100 dark:divide-slate-700">
                <ChecklistRow
                  label="Adresse"
                  value={lookupResult.address}
                  found={lookupResult.has_address}
                  icon={<MapPin className="w-4 h-4" />}
                />
                <ChecklistRow
                  label="Coordonnees GPS"
                  value={
                    lookupResult.has_coordinates && lookupResult.latitude && lookupResult.longitude
                      ? `${lookupResult.latitude.toFixed(4)}, ${lookupResult.longitude.toFixed(4)}`
                      : null
                  }
                  found={lookupResult.has_coordinates}
                  icon={<MapPin className="w-4 h-4" />}
                />
                <ChecklistRow
                  label="Annee de construction"
                  value={lookupResult.construction_year?.toString()}
                  found={lookupResult.has_construction_year}
                  icon={<Calendar className="w-4 h-4" />}
                />
                <ChecklistRow
                  label="Type de batiment"
                  value={lookupResult.building_type}
                  found={lookupResult.has_building_type}
                  icon={<Building2 className="w-4 h-4" />}
                />
                <ChecklistRow
                  label="Nombre d'etages"
                  value={lookupResult.floors_above?.toString()}
                  found={lookupResult.has_floors}
                  icon={<Layers className="w-4 h-4" />}
                />
                <ChecklistRow
                  label="Surface"
                  value={lookupResult.surface_area_m2 ? `${lookupResult.surface_area_m2} m2` : null}
                  found={lookupResult.has_surface_area}
                  icon={<Ruler className="w-4 h-4" />}
                />
              </div>

              {createError && (
                <div className="flex items-start gap-2 px-4 py-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg">
                  <AlertCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                  <p className="text-sm text-red-700 dark:text-red-300">{createError}</p>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Documents */}
          {currentStep.key === 'documents' && (
            <div className="space-y-5">
              <div>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">Importer vos documents</h3>
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  Importez vos diagnostics et documents existants. Cette etape est optionnelle — vous pourrez ajouter
                  des documents plus tard.
                </p>
              </div>

              <div className="space-y-3">
                {DOC_CATEGORIES.map((cat) => {
                  const uploaded = uploadedFiles.filter((f) => f.category === cat.key);
                  const isUploading = uploadingCategory === cat.key;

                  return (
                    <div
                      key={cat.key}
                      className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-4"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-gray-700 dark:text-slate-300">{cat.label}</span>
                        {uploaded.length > 0 && (
                          <span className="inline-flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            {uploaded.length} fichier{uploaded.length > 1 ? 's' : ''}
                          </span>
                        )}
                      </div>
                      <FileUpload
                        onUpload={(file) => handleUploadFile(file, cat.key, cat.type)}
                        accept=".pdf,.jpg,.jpeg,.png"
                        maxSizeMB={50}
                        isLoading={isUploading}
                      />
                    </div>
                  );
                })}
              </div>

              {uploadedFiles.length > 0 && (
                <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg px-4 py-3">
                  <p className="text-sm text-blue-700 dark:text-blue-300">
                    {uploadedFiles.length} document{uploadedFiles.length > 1 ? 's' : ''} importe
                    {uploadedFiles.length > 1 ? 's' : ''} avec succes.
                  </p>
                </div>
              )}
            </div>
          )}

          {/* Step 4: Evaluation */}
          {currentStep.key === 'evaluate' && (
            <div className="space-y-5">
              <div>
                <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-1">Premiere evaluation</h3>
                <p className="text-sm text-gray-500 dark:text-slate-400">
                  BatiConnect analyse automatiquement la completude et l'etat de preparation de votre dossier.
                </p>
              </div>

              {!evalDone && !evalLoading && (
                <button
                  onClick={handleEvaluate}
                  className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
                  data-testid="onboarding-evaluate-btn"
                >
                  <Sparkles className="w-4 h-4" />
                  Lancer l'evaluation
                </button>
              )}

              {evalLoading && (
                <div className="flex flex-col items-center justify-center py-8 gap-3">
                  <Loader2 className="w-8 h-8 text-red-500 animate-spin" />
                  <p className="text-sm text-gray-500 dark:text-slate-400">Analyse en cours...</p>
                </div>
              )}

              {evalDone && (
                <div className="space-y-4">
                  {/* Completeness */}
                  <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-3">
                      <span className="text-sm font-semibold text-gray-900 dark:text-white">Completude du dossier</span>
                      <span
                        className={cn(
                          'text-lg font-bold',
                          completenessPct >= 80
                            ? 'text-green-600'
                            : completenessPct >= 40
                              ? 'text-amber-600'
                              : 'text-red-600',
                        )}
                      >
                        {completeness ? `${completenessPct}%` : '--'}
                      </span>
                    </div>
                    {completeness && (
                      <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-2">
                        <div
                          className={cn(
                            'h-2 rounded-full transition-all duration-500',
                            completenessPct >= 80
                              ? 'bg-green-500'
                              : completenessPct >= 40
                                ? 'bg-amber-500'
                                : 'bg-red-500',
                          )}
                          style={{ width: `${completenessPct}%` }}
                        />
                      </div>
                    )}
                    {completeness && (
                      <p className="text-xs text-gray-500 dark:text-slate-400 mt-2">
                        {completenessCompleted} / {completenessTotal} criteres satisfaits
                        {completenessMissing > 0 &&
                          ` — ${completenessMissing} element${completenessMissing > 1 ? 's' : ''} manquant${completenessMissing > 1 ? 's' : ''}`}
                      </p>
                    )}
                  </div>

                  {/* Readiness */}
                  <div className="bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-700 rounded-xl p-4">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-gray-900 dark:text-white">Etat de preparation</span>
                      {readinessVerdict && (
                        <span
                          className={cn(
                            'inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full',
                            readinessVerdict === 'ready'
                              ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-300'
                              : readinessVerdict === 'conditionally_ready'
                                ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
                                : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
                          )}
                        >
                          {readinessVerdict === 'ready'
                            ? 'Pret'
                            : readinessVerdict === 'conditionally_ready'
                              ? 'Attention requise'
                              : 'Elements bloquants'}
                        </span>
                      )}
                    </div>
                    {readiness && readiness.length > 0 ? (
                      <p className="text-xs text-gray-500 dark:text-slate-400">
                        {readiness.filter((r) => r.status === 'blocked').length} blocage
                        {readiness.filter((r) => r.status === 'blocked').length !== 1 ? 's' : ''},{' '}
                        {readiness.filter((r) => r.status === 'ready').length} critere
                        {readiness.filter((r) => r.status === 'ready').length !== 1 ? 's' : ''} satisfait
                        {readiness.filter((r) => r.status === 'ready').length !== 1 ? 's' : ''}
                      </p>
                    ) : (
                      <p className="text-xs text-gray-500 dark:text-slate-400">
                        Evaluation non disponible pour le moment.
                      </p>
                    )}
                  </div>

                  {/* CTA */}
                  <button
                    onClick={handleViewDossier}
                    className="w-full flex items-center justify-center gap-2 px-4 py-3 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
                    data-testid="onboarding-view-dossier-btn"
                  >
                    Voir le dossier complet
                    <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer navigation */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
          <div>
            {step > 0 && currentStep.key !== 'evaluate' && (
              <button
                onClick={() => setStep((s) => s - 1)}
                className="inline-flex items-center gap-1 px-3 py-2 text-sm text-gray-600 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white transition-colors"
              >
                <ChevronLeft className="w-4 h-4" />
                Retour
              </button>
            )}
          </div>
          <div>
            {currentStep.key === 'identify' && lookupResult && lookupResult.found && (
              <button
                onClick={() => setStep(1)}
                className="inline-flex items-center gap-1 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
                data-testid="onboarding-next-btn"
              >
                Continuer
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
            {currentStep.key === 'enrich' && (
              <button
                onClick={handleCreateBuilding}
                disabled={createLoading}
                className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                data-testid="onboarding-create-btn"
              >
                {createLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle2 className="w-4 h-4" />}
                Creer le batiment
              </button>
            )}
            {currentStep.key === 'documents' && (
              <button
                onClick={() => setStep(3)}
                className="inline-flex items-center gap-1 px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 transition-colors"
              >
                {uploadedFiles.length > 0 ? 'Continuer' : 'Passer cette etape'}
                <ChevronRight className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

// Checklist row for step 2
function ChecklistRow({
  label,
  value,
  found,
  icon,
}: {
  label: string;
  value: string | null | undefined;
  found: boolean;
  icon: React.ReactNode;
}) {
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className={cn('flex-shrink-0', found ? 'text-green-500' : 'text-gray-300 dark:text-slate-600')}>
        {found ? <CheckCircle2 className="w-4 h-4" /> : <Circle className="w-4 h-4" />}
      </div>
      <div className="flex-shrink-0 text-gray-400 dark:text-slate-500">{icon}</div>
      <div className="flex-1 min-w-0">
        <span className="text-sm text-gray-700 dark:text-slate-300">{label}</span>
      </div>
      <div className="text-sm text-gray-900 dark:text-white font-medium truncate max-w-[200px]">
        {found && value ? value : <span className="text-gray-400 dark:text-slate-500 text-xs">Non disponible</span>}
      </div>
    </div>
  );
}
