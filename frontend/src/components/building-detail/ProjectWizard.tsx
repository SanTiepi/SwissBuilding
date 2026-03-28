import { useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  X,
  ChevronRight,
  ChevronLeft,
  Loader2,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Wrench,
  MapPin,
  FileText,
  ClipboardList,
  ShieldCheck,
  Beaker,
  Hammer,
} from 'lucide-react';
import { cn } from '@/utils/formatters';
import { toast } from '@/store/toastStore';
import {
  projectSetupApi,
  type ProjectDraft,
  type ProjectCreateRequest,
} from '@/api/projectSetup';

interface ProjectWizardProps {
  open: boolean;
  onClose: () => void;
  buildingId: string;
  buildingName?: string;
}

const STEPS = [
  { key: 'type', label: 'Type de travaux', icon: Wrench },
  { key: 'scope', label: 'Perimetre', icon: MapPin },
  { key: 'obligations', label: 'Obligations', icon: ShieldCheck },
  { key: 'summary', label: 'Resume', icon: ClipboardList },
] as const;

const INTERVENTION_TYPES = [
  { value: 'asbestos_removal', label: 'Desamiantage', description: 'Retrait de materiaux contenant de l\'amiante', icon: '🔬' },
  { value: 'pcb_removal', label: 'Decontamination PCB', description: 'Retrait des joints et materiaux contenant des PCB', icon: '🧪' },
  { value: 'lead_removal', label: 'Deplombage', description: 'Retrait des peintures et materiaux contenant du plomb', icon: '🎨' },
  { value: 'hap_removal', label: 'Traitement HAP', description: 'Retrait des materiaux contenant des HAP', icon: '⚗' },
  { value: 'radon_mitigation', label: 'Assainissement radon', description: 'Mesures de reduction du radon dans le batiment', icon: '☢' },
  { value: 'pfas_remediation', label: 'Remediation PFAS', description: 'Traitement des contaminations PFAS', icon: '💧' },
  { value: 'renovation', label: 'Renovation', description: 'Travaux de renovation (controle polluants requis)', icon: '🏗' },
  { value: 'maintenance', label: 'Maintenance', description: 'Entretien courant du batiment', icon: '🔧' },
  { value: 'other', label: 'Autre', description: 'Autre type de travaux', icon: '📋' },
] as const;

const RISK_COLORS: Record<string, string> = {
  critical: 'text-red-600 dark:text-red-400 bg-red-50 dark:bg-red-900/20',
  high: 'text-orange-600 dark:text-orange-400 bg-orange-50 dark:bg-orange-900/20',
  medium: 'text-yellow-600 dark:text-yellow-400 bg-yellow-50 dark:bg-yellow-900/20',
  low: 'text-green-600 dark:text-green-400 bg-green-50 dark:bg-green-900/20',
  unknown: 'text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-gray-700/50',
};

export default function ProjectWizard({ open, onClose, buildingId, buildingName }: ProjectWizardProps) {
  const queryClient = useQueryClient();
  const [step, setStep] = useState(0);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const [description, setDescription] = useState('');
  const [draft, setDraft] = useState<ProjectDraft | null>(null);
  const [loading, setLoading] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [customTitle, setCustomTitle] = useState('');

  // Track user-removed zones
  const [removedZoneIds, setRemovedZoneIds] = useState<Set<string>>(new Set());

  const reset = useCallback(() => {
    setStep(0);
    setSelectedType(null);
    setDescription('');
    setDraft(null);
    setLoading(false);
    setCreating(false);
    setError(null);
    setCustomTitle('');
    setRemovedZoneIds(new Set());
  }, []);

  const handleClose = useCallback(() => {
    reset();
    onClose();
  }, [reset, onClose]);

  const handleNext = useCallback(async () => {
    if (step === 0 && selectedType) {
      // Generate draft when moving from type selection to scope
      setLoading(true);
      setError(null);
      try {
        const result = await projectSetupApi.generateDraft(buildingId, selectedType);
        setDraft(result);
        setCustomTitle(result.suggested_title);
        setStep(1);
      } catch (err) {
        setError('Erreur lors de la generation du projet');
        console.error('Project draft generation failed:', err);
      } finally {
        setLoading(false);
      }
    } else if (step < STEPS.length - 1) {
      setStep((s) => s + 1);
    }
  }, [step, selectedType, buildingId]);

  const handleBack = useCallback(() => {
    if (step > 0) {
      setStep((s) => s - 1);
    }
  }, [step]);

  const handleCreate = useCallback(async () => {
    if (!draft || !selectedType) return;
    setCreating(true);
    setError(null);

    const activeZones = draft.scope.zones.filter((z) => !removedZoneIds.has(z.id));
    const missingDocs = draft.document_checklist.filter((d) => d.status === 'missing');

    const createData: ProjectCreateRequest = {
      intervention_type: selectedType,
      title: customTitle || draft.suggested_title,
      description: description || undefined,
      zones_affected: activeZones.map((z) => z.name),
      materials_used: Object.keys(draft.scope.materials_involved),
      gaps: missingDocs.map((d) => ({ label: d.label })),
    };

    try {
      await projectSetupApi.createProject(buildingId, createData);
      toast('Projet cree avec succes', 'success');
      queryClient.invalidateQueries({ queryKey: ['interventions', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['building', buildingId] });
      handleClose();
    } catch (err) {
      setError('Erreur lors de la creation du projet');
      console.error('Project creation failed:', err);
    } finally {
      setCreating(false);
    }
  }, [draft, selectedType, customTitle, description, buildingId, removedZoneIds, queryClient, handleClose]);

  const toggleZone = useCallback((zoneId: string) => {
    setRemovedZoneIds((prev) => {
      const next = new Set(prev);
      if (next.has(zoneId)) {
        next.delete(zoneId);
      } else {
        next.add(zoneId);
      }
      return next;
    });
  }, []);

  if (!open) return null;

  const activeZones = draft?.scope.zones.filter((z) => !removedZoneIds.has(z.id)) ?? [];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
      {/* Overlay */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={handleClose} />

      {/* Modal */}
      <div className="relative bg-white dark:bg-slate-800 rounded-2xl shadow-2xl w-full max-w-3xl max-h-[90vh] flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-slate-700">
          <div>
            <h2 className="text-lg font-bold text-gray-900 dark:text-white">Lancer un projet de travaux</h2>
            {buildingName && (
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">{buildingName}</p>
            )}
          </div>
          <button
            onClick={handleClose}
            className="p-1.5 text-gray-400 hover:text-gray-600 dark:text-slate-500 dark:hover:text-slate-300 rounded-lg transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step indicator */}
        <div className="px-6 py-3 border-b border-gray-100 dark:border-slate-700/50">
          <div className="flex items-center gap-2">
            {STEPS.map((s, i) => {
              const Icon = s.icon;
              const isActive = i === step;
              const isDone = i < step;
              return (
                <div key={s.key} className="flex items-center gap-2 flex-1">
                  <div
                    className={cn(
                      'flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium transition-colors',
                      isActive
                        ? 'bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
                        : isDone
                          ? 'bg-green-50 dark:bg-green-900/20 text-green-600 dark:text-green-400'
                          : 'bg-gray-50 dark:bg-slate-700/50 text-gray-400 dark:text-slate-500',
                    )}
                  >
                    {isDone ? (
                      <CheckCircle2 className="w-3.5 h-3.5" />
                    ) : (
                      <Icon className="w-3.5 h-3.5" />
                    )}
                    <span className="hidden sm:inline">{s.label}</span>
                  </div>
                  {i < STEPS.length - 1 && (
                    <ChevronRight className="w-3 h-3 text-gray-300 dark:text-slate-600 flex-shrink-0" />
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 text-sm text-red-700 dark:text-red-300 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Step 1: Type de travaux */}
          {step === 0 && (
            <div className="space-y-4">
              <p className="text-sm text-gray-600 dark:text-slate-300">
                Selectionnez le type de travaux a realiser sur ce batiment.
              </p>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {INTERVENTION_TYPES.map((t) => (
                  <button
                    key={t.value}
                    onClick={() => setSelectedType(t.value)}
                    className={cn(
                      'flex items-start gap-3 p-3 rounded-lg border-2 text-left transition-all',
                      selectedType === t.value
                        ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 dark:border-blue-400'
                        : 'border-gray-200 dark:border-slate-600 hover:border-gray-300 dark:hover:border-slate-500',
                    )}
                  >
                    <span className="text-xl flex-shrink-0 mt-0.5">{t.icon}</span>
                    <div className="min-w-0">
                      <p className="text-sm font-semibold text-gray-900 dark:text-white">{t.label}</p>
                      <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5">{t.description}</p>
                    </div>
                  </button>
                ))}
              </div>

              {selectedType && (
                <div className="mt-4">
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                    Description (optionnel)
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    rows={3}
                    className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="Decrivez le contexte du projet..."
                  />
                </div>
              )}
            </div>
          )}

          {/* Step 2: Perimetre automatique */}
          {step === 1 && draft && (
            <div className="space-y-5">
              {/* Title */}
              <div>
                <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
                  Titre du projet
                </label>
                <input
                  type="text"
                  value={customTitle}
                  onChange={(e) => setCustomTitle(e.target.value)}
                  className="w-full px-3 py-2 text-sm rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Scope summary */}
              <div className="flex items-center gap-3 p-3 rounded-lg bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800">
                <Beaker className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0" />
                <div className="text-sm text-blue-800 dark:text-blue-200">
                  <strong>{draft.scope.total_positive_samples}</strong> echantillon(s) positif(s) detecte(s)
                  {draft.scope.pollutants_found.length > 0 && (
                    <span> — {draft.scope.pollutants_found.join(', ')}</span>
                  )}
                </div>
              </div>

              {/* Zones */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                  <MapPin className="w-4 h-4" />
                  Zones concernees ({activeZones.length})
                </h3>
                {draft.scope.zones.length > 0 ? (
                  <div className="space-y-1.5">
                    {draft.scope.zones.map((z) => {
                      const isActive = !removedZoneIds.has(z.id);
                      return (
                        <div
                          key={z.id}
                          className={cn(
                            'flex items-center justify-between px-3 py-2 rounded-lg border text-sm transition-all',
                            isActive
                              ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/10'
                              : 'border-gray-200 dark:border-slate-600 bg-gray-50 dark:bg-slate-700/30 opacity-60',
                          )}
                        >
                          <div className="flex items-center gap-2">
                            <span className="font-medium text-gray-900 dark:text-white">{z.name}</span>
                            <span className="text-xs text-gray-500 dark:text-slate-400">
                              {z.zone_type}
                              {z.floor_number != null ? ` — Etage ${z.floor_number}` : ''}
                              {z.surface_area_m2 ? ` — ${z.surface_area_m2} m2` : ''}
                            </span>
                          </div>
                          <button
                            onClick={() => toggleZone(z.id)}
                            className={cn(
                              'text-xs px-2 py-0.5 rounded transition-colors',
                              isActive
                                ? 'text-red-600 hover:bg-red-100 dark:text-red-400 dark:hover:bg-red-900/30'
                                : 'text-green-600 hover:bg-green-100 dark:text-green-400 dark:hover:bg-green-900/30',
                            )}
                          >
                            {isActive ? 'Retirer' : 'Ajouter'}
                          </button>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="text-sm text-gray-500 dark:text-slate-400 italic">
                    Aucune zone identifiee automatiquement. Les zones seront definies manuellement.
                  </p>
                )}
                {draft.scope.affected_floors.length > 0 && (
                  <p className="text-xs text-gray-500 dark:text-slate-400 mt-2">
                    Etages concernes : {draft.scope.affected_floors.join(', ')}
                  </p>
                )}
              </div>

              {/* Elements to treat */}
              {draft.scope.elements_to_treat.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                    <Hammer className="w-4 h-4" />
                    Elements a traiter ({draft.scope.elements_to_treat.length})
                  </h3>
                  <div className="max-h-48 overflow-y-auto border border-gray-200 dark:border-slate-600 rounded-lg">
                    <table className="w-full text-xs">
                      <thead className="bg-gray-50 dark:bg-slate-700/50 sticky top-0">
                        <tr>
                          <th className="text-left px-3 py-1.5 text-gray-500 dark:text-slate-400 font-medium">
                            Echantillon
                          </th>
                          <th className="text-left px-3 py-1.5 text-gray-500 dark:text-slate-400 font-medium">
                            Materiau
                          </th>
                          <th className="text-left px-3 py-1.5 text-gray-500 dark:text-slate-400 font-medium">
                            Localisation
                          </th>
                          <th className="text-left px-3 py-1.5 text-gray-500 dark:text-slate-400 font-medium">
                            Risque
                          </th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100 dark:divide-slate-700">
                        {draft.scope.elements_to_treat.map((el, i) => (
                          <tr key={i} className="hover:bg-gray-50 dark:hover:bg-slate-700/30">
                            <td className="px-3 py-1.5 text-gray-900 dark:text-white font-mono">
                              {el.sample_number}
                            </td>
                            <td className="px-3 py-1.5 text-gray-700 dark:text-slate-200">{el.material}</td>
                            <td className="px-3 py-1.5 text-gray-500 dark:text-slate-400">{el.location || '—'}</td>
                            <td className="px-3 py-1.5">
                              <span
                                className={cn(
                                  'inline-block px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase',
                                  RISK_COLORS[el.risk_level] || RISK_COLORS.unknown,
                                )}
                              >
                                {el.risk_level}
                              </span>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}

              {/* Relevant diagnostics */}
              {draft.relevant_diagnostics.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                    <FileText className="w-4 h-4" />
                    Diagnostics de reference ({draft.relevant_diagnostics.length})
                  </h3>
                  <div className="space-y-1">
                    {draft.relevant_diagnostics.map((d) => (
                      <div
                        key={d.id}
                        className="flex items-center gap-2 px-3 py-1.5 rounded bg-gray-50 dark:bg-slate-700/50 text-xs"
                      >
                        <CheckCircle2 className="w-3.5 h-3.5 text-green-500 flex-shrink-0" />
                        <span className="text-gray-900 dark:text-white font-medium">
                          {d.diagnostic_type || 'Diagnostic'}
                        </span>
                        <span className="text-gray-500 dark:text-slate-400">
                          — {d.status}
                          {d.date_inspection ? ` — ${d.date_inspection}` : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Step 3: Obligations et pieces */}
          {step === 2 && draft && (
            <div className="space-y-5">
              {/* Regulatory requirements */}
              {draft.regulatory_requirements.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                    <ShieldCheck className="w-4 h-4" />
                    Exigences reglementaires
                  </h3>
                  <div className="space-y-1.5">
                    {draft.regulatory_requirements.map((r, i) => (
                      <div
                        key={i}
                        className="flex items-start gap-2 px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 text-sm"
                      >
                        <ShieldCheck className="w-4 h-4 text-amber-600 dark:text-amber-400 flex-shrink-0 mt-0.5" />
                        <div>
                          <p className="text-gray-900 dark:text-white font-medium">{r.label}</p>
                          <p className="text-xs text-gray-500 dark:text-slate-400">{r.ref}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Document checklist */}
              <div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Pieces requises
                </h3>
                <div className="space-y-1.5">
                  {draft.document_checklist.map((doc, i) => (
                    <div
                      key={i}
                      className={cn(
                        'flex items-center gap-2 px-3 py-2 rounded-lg text-sm border',
                        doc.status === 'available'
                          ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/10'
                          : 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/10',
                      )}
                    >
                      {doc.status === 'available' ? (
                        <CheckCircle2 className="w-4 h-4 text-green-600 dark:text-green-400 flex-shrink-0" />
                      ) : (
                        <XCircle className="w-4 h-4 text-red-500 dark:text-red-400 flex-shrink-0" />
                      )}
                      <span
                        className={cn(
                          'font-medium',
                          doc.status === 'available'
                            ? 'text-green-800 dark:text-green-200'
                            : 'text-red-800 dark:text-red-200',
                        )}
                      >
                        {doc.label}
                      </span>
                      <span
                        className={cn(
                          'ml-auto text-xs',
                          doc.status === 'available'
                            ? 'text-green-600 dark:text-green-400'
                            : 'text-red-500 dark:text-red-400',
                        )}
                      >
                        {doc.status === 'available' ? 'Disponible' : 'Manquant'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              {/* Gap analysis verdict */}
              <div
                className={cn(
                  'p-4 rounded-xl border-2',
                  draft.gap_analysis.can_start
                    ? 'border-green-400 bg-green-50 dark:border-green-600 dark:bg-green-900/20'
                    : 'border-amber-400 bg-amber-50 dark:border-amber-600 dark:bg-amber-900/20',
                )}
              >
                <div className="flex items-center gap-3">
                  {draft.gap_analysis.can_start ? (
                    <CheckCircle2 className="w-6 h-6 text-green-600 dark:text-green-400" />
                  ) : (
                    <AlertTriangle className="w-6 h-6 text-amber-600 dark:text-amber-400" />
                  )}
                  <div>
                    <p
                      className={cn(
                        'font-semibold',
                        draft.gap_analysis.can_start
                          ? 'text-green-800 dark:text-green-200'
                          : 'text-amber-800 dark:text-amber-200',
                      )}
                    >
                      {draft.gap_analysis.message}
                    </p>
                    <p className="text-xs text-gray-600 dark:text-slate-400 mt-1">
                      {draft.gap_analysis.available_documents_count}/{draft.gap_analysis.total_required_documents} pieces
                      disponibles — Readiness {Math.round(draft.gap_analysis.readiness_score * 100)}%
                    </p>
                  </div>
                </div>
                {draft.gap_analysis.blockers.length > 0 && (
                  <ul className="mt-3 space-y-1 ml-9">
                    {draft.gap_analysis.blockers.map((b, i) => (
                      <li key={i} className="text-xs text-amber-700 dark:text-amber-300 flex items-center gap-1.5">
                        <XCircle className="w-3 h-3 flex-shrink-0" />
                        {b}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          )}

          {/* Step 4: Resume et creation */}
          {step === 3 && draft && (
            <div className="space-y-4">
              <div className="bg-gray-50 dark:bg-slate-700/50 rounded-xl p-4 space-y-3">
                <div>
                  <p className="text-xs text-gray-500 dark:text-slate-400 uppercase tracking-wider font-medium">Projet</p>
                  <p className="text-lg font-bold text-gray-900 dark:text-white mt-0.5">
                    {customTitle || draft.suggested_title}
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <p className="text-xs text-gray-500 dark:text-slate-400">Type</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {draft.intervention_type_label}
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-slate-400">Zones</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">{activeZones.length} zone(s)</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-slate-400">Elements</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {draft.scope.elements_to_treat.length} a traiter
                    </p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500 dark:text-slate-400">Pieces</p>
                    <p className="text-sm font-medium text-gray-900 dark:text-white">
                      {draft.gap_analysis.available_documents_count}/{draft.gap_analysis.total_required_documents}{' '}
                      disponibles
                    </p>
                  </div>
                </div>

                {description && (
                  <div>
                    <p className="text-xs text-gray-500 dark:text-slate-400">Description</p>
                    <p className="text-sm text-gray-700 dark:text-slate-200 mt-0.5">{description}</p>
                  </div>
                )}

                {/* Readiness badge */}
                <div className="flex items-center gap-2 pt-2 border-t border-gray-200 dark:border-slate-600">
                  {draft.gap_analysis.can_start ? (
                    <>
                      <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
                      <span className="text-sm font-semibold text-green-700 dark:text-green-300">
                        Pret a demarrer
                      </span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle className="w-5 h-5 text-amber-600 dark:text-amber-400" />
                      <span className="text-sm font-semibold text-amber-700 dark:text-amber-300">
                        {draft.gap_analysis.blockers.length} element(s) manquant(s)
                      </span>
                    </>
                  )}
                </div>
              </div>

              {/* Related actions */}
              {draft.related_actions.length > 0 && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-2">
                    Actions associees ({draft.related_actions.length})
                  </h3>
                  <div className="space-y-1">
                    {draft.related_actions.map((a) => (
                      <div
                        key={a.id}
                        className="flex items-center gap-2 px-3 py-1.5 rounded bg-gray-50 dark:bg-slate-700/50 text-xs"
                      >
                        <span
                          className={cn(
                            'w-2 h-2 rounded-full flex-shrink-0',
                            a.priority === 'critical'
                              ? 'bg-red-500'
                              : a.priority === 'high'
                                ? 'bg-orange-500'
                                : a.priority === 'medium'
                                  ? 'bg-yellow-500'
                                  : 'bg-gray-400',
                          )}
                        />
                        <span className="text-gray-900 dark:text-white">{a.title}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              <p className="text-xs text-gray-500 dark:text-slate-400 italic">
                Le projet sera cree avec le statut &laquo; Planifie &raquo;. Les pieces manquantes genereront des actions
                de suivi.
              </p>
            </div>
          )}

          {/* Loading state */}
          {loading && (
            <div className="flex flex-col items-center justify-center py-12">
              <Loader2 className="w-8 h-8 text-blue-500 animate-spin mb-3" />
              <p className="text-sm text-gray-500 dark:text-slate-400">
                Analyse du dossier en cours...
              </p>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-800/50">
          <button
            onClick={step === 0 ? handleClose : handleBack}
            className="flex items-center gap-1 px-4 py-2 text-sm font-medium text-gray-600 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            {step === 0 ? (
              'Annuler'
            ) : (
              <>
                <ChevronLeft className="w-4 h-4" /> Retour
              </>
            )}
          </button>

          {step < STEPS.length - 1 ? (
            <button
              onClick={handleNext}
              disabled={step === 0 && !selectedType || loading}
              className={cn(
                'flex items-center gap-1 px-5 py-2 text-sm font-semibold rounded-lg transition-colors',
                step === 0 && !selectedType || loading
                  ? 'bg-gray-200 dark:bg-slate-600 text-gray-400 dark:text-slate-500 cursor-not-allowed'
                  : 'bg-blue-600 hover:bg-blue-700 text-white',
              )}
            >
              {loading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  Suivant <ChevronRight className="w-4 h-4" />
                </>
              )}
            </button>
          ) : (
            <button
              onClick={handleCreate}
              disabled={creating}
              className={cn(
                'flex items-center gap-1 px-5 py-2 text-sm font-semibold rounded-lg transition-colors',
                creating
                  ? 'bg-gray-200 dark:bg-slate-600 text-gray-400 dark:text-slate-500 cursor-not-allowed'
                  : 'bg-green-600 hover:bg-green-700 text-white',
              )}
            >
              {creating ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <CheckCircle2 className="w-4 h-4" /> Creer le projet
                </>
              )}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
