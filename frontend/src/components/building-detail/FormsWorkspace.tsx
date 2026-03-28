import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { formsApi } from '@/api/forms';
import type { ApplicableForm, FormInstance, FormFieldValue } from '@/api/forms';
import { toast } from '@/store/toastStore';
import {
  FileText,
  CheckCircle2,
  Circle,
  Clock,
  AlertTriangle,
  Send,
  Save,
  ChevronLeft,
  Loader2,
  ExternalLink,
  Shield,
  Info,
} from 'lucide-react';

interface FormsWorkspaceProps {
  buildingId: string;
}

const FORM_TYPE_LABELS: Record<string, string> = {
  suva_notification: 'SUVA',
  cantonal_declaration: 'Cantonal',
  waste_plan: 'Dechets',
  pollutant_declaration: 'Polluants',
  work_permit: 'Permis',
  demolition_permit: 'Demolition',
  insurance_declaration: 'Assurance',
  subvention_request: 'Subvention',
  other: 'Autre',
};

const STATUS_CONFIG: Record<string, { label: string; color: string; icon: typeof CheckCircle2 }> = {
  draft: { label: 'Brouillon', color: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300', icon: Circle },
  prefilled: {
    label: 'Pre-rempli',
    color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300',
    icon: FileText,
  },
  reviewed: {
    label: 'Verifie',
    color: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-300',
    icon: CheckCircle2,
  },
  submitted: {
    label: 'Soumis',
    color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    icon: Send,
  },
  complement_requested: {
    label: 'Complement demande',
    color: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-300',
    icon: AlertTriangle,
  },
  resubmitted: {
    label: 'Resoumis',
    color: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-300',
    icon: Send,
  },
  acknowledged: {
    label: 'Accepte',
    color: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-300',
    icon: CheckCircle2,
  },
  rejected: {
    label: 'Refuse',
    color: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-300',
    icon: AlertTriangle,
  },
};

function ConfidenceDot({ confidence }: { confidence: string }) {
  const colors: Record<string, string> = {
    high: 'bg-green-500',
    medium: 'bg-amber-500',
    low: 'bg-red-400',
  };
  const labels: Record<string, string> = {
    high: 'Automatique',
    medium: 'Partiel',
    low: 'Manuel requis',
  };
  return (
    <span className="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
      <span className={cn('w-2 h-2 rounded-full', colors[confidence] || 'bg-gray-400')} />
      {labels[confidence] || confidence}
    </span>
  );
}

function ConfidenceBar({ value }: { value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-500' : 'bg-red-400';
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full transition-all', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-medium text-gray-600 dark:text-gray-400">{pct}%</span>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.draft;
  const Icon = cfg.icon;
  return (
    <span className={cn('inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium', cfg.color)}>
      <Icon className="w-3 h-3" />
      {cfg.label}
    </span>
  );
}

function JurisdictionBadge({ canton, formType }: { canton: string | null; formType: string }) {
  const label = canton ? `Canton ${canton}` : 'Federal';
  const typeLabel = FORM_TYPE_LABELS[formType] || formType;
  return (
    <div className="flex items-center gap-1.5">
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300">
        <Shield className="w-3 h-3 mr-1" />
        {label}
      </span>
      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-300">
        {typeLabel}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Applicable Forms List
// ---------------------------------------------------------------------------

function ApplicableFormsList({
  buildingId,
  onPrefill,
}: {
  buildingId: string;
  onPrefill: (form: FormInstance) => void;
}) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const { data: applicable = [], isLoading } = useQuery({
    queryKey: ['forms-applicable', buildingId],
    queryFn: () => formsApi.getApplicable(buildingId),
    retry: false,
  });

  const { data: instances = [] } = useQuery({
    queryKey: ['forms-instances', buildingId],
    queryFn: () => formsApi.list(buildingId),
    retry: false,
  });

  const prefillMutation = useMutation({
    mutationFn: (templateId: string) => formsApi.prefill(buildingId, templateId),
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['forms-instances', buildingId] });
      onPrefill(data);
      toast(t('forms.prefill_success') || 'Formulaire pre-rempli avec succes');
    },
    onError: () => {
      toast(t('forms.prefill_error') || 'Erreur lors du pre-remplissage');
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Existing form instances */}
      {instances.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            {t('forms.my_forms') || 'Mes formulaires'}
          </h3>
          <div className="space-y-2">
            {instances.map((inst) => (
              <button
                key={inst.id}
                onClick={() => onPrefill(inst)}
                className="w-full text-left p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg hover:border-red-300 dark:hover:border-red-600 transition-colors"
              >
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-medium text-gray-900 dark:text-white">{inst.template_name || 'Formulaire'}</p>
                    <div className="flex items-center gap-2 mt-1">
                      <StatusBadge status={inst.status} />
                      {inst.prefill_confidence != null && (
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          Confiance: {Math.round(inst.prefill_confidence * 100)}%
                        </span>
                      )}
                    </div>
                  </div>
                  <ChevronLeft className="w-4 h-4 text-gray-400 rotate-180" />
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Applicable templates */}
      {applicable.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
            {t('forms.applicable_title') || 'Formulaires applicables'}
          </h3>
          <div className="grid gap-3">
            {applicable.map((item: ApplicableForm) => (
              <div
                key={item.template.id}
                className="p-4 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-lg"
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <FileText className="w-4 h-4 text-red-500 flex-shrink-0" />
                      <h4 className="font-medium text-gray-900 dark:text-white truncate">{item.template.name}</h4>
                    </div>
                    <JurisdictionBadge canton={item.template.canton} formType={item.template.form_type} />
                    <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">{item.reason}</p>
                    {item.template.description && (
                      <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">{item.template.description}</p>
                    )}
                    {item.template.source_url && (
                      <a
                        href={item.template.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="inline-flex items-center gap-1 text-xs text-red-600 dark:text-red-400 hover:underline mt-1"
                      >
                        <ExternalLink className="w-3 h-3" />
                        Source officielle
                      </a>
                    )}
                  </div>
                  <button
                    onClick={() => prefillMutation.mutate(item.template.id)}
                    disabled={prefillMutation.isPending}
                    className="flex-shrink-0 inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
                  >
                    {prefillMutation.isPending ? (
                      <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <FileText className="w-3.5 h-3.5" />
                    )}
                    Pre-remplir
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {applicable.length === 0 && instances.length === 0 && (
        <div className="text-center py-12">
          <FileText className="w-12 h-12 text-gray-300 dark:text-gray-600 mx-auto mb-3" />
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('forms.no_applicable') || 'Aucun formulaire applicable pour ce batiment.'}
          </p>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Form Instance Detail View
// ---------------------------------------------------------------------------

function FormInstanceView({ formId, onBack, buildingId }: { formId: string; onBack: () => void; buildingId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState('');

  const { data: form, isLoading } = useQuery({
    queryKey: ['form-instance', formId],
    queryFn: () => formsApi.get(formId),
    retry: false,
  });

  const updateMutation = useMutation({
    mutationFn: (data: { field_values?: Record<string, { value: string | null }> }) => formsApi.update(formId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['form-instance', formId] });
      queryClient.invalidateQueries({ queryKey: ['forms-instances', buildingId] });
      setEditingField(null);
      toast(t('forms.save_success') || 'Modifications enregistrees');
    },
  });

  const submitMutation = useMutation({
    mutationFn: () => formsApi.submit(formId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['form-instance', formId] });
      queryClient.invalidateQueries({ queryKey: ['forms-instances', buildingId] });
      toast(t('forms.submit_success') || 'Formulaire soumis avec succes');
    },
    onError: () => {
      toast(t('forms.submit_error') || 'Erreur lors de la soumission');
    },
  });

  if (isLoading || !form) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  const fieldValues = form.field_values || {};
  const fieldEntries = Object.entries(fieldValues);
  const canSubmit = form.status === 'prefilled' || form.status === 'reviewed' || form.status === 'complement_requested';
  const canEdit = form.status !== 'submitted' && form.status !== 'acknowledged' && form.status !== 'rejected';

  const handleFieldSave = (fieldName: string) => {
    updateMutation.mutate({
      field_values: {
        [fieldName]: { value: editValue || null },
      },
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="p-1.5 text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700"
        >
          <ChevronLeft className="w-5 h-5" />
        </button>
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{form.template_name || 'Formulaire'}</h3>
          <div className="flex items-center gap-2 mt-1">
            <StatusBadge status={form.status} />
            {form.template_form_type && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {FORM_TYPE_LABELS[form.template_form_type] || form.template_form_type}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Confidence bar */}
      {form.prefill_confidence != null && (
        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <div className="flex items-center justify-between mb-1">
            <span className="text-xs font-medium text-gray-600 dark:text-gray-400">Confiance du pre-remplissage</span>
            <span className="text-xs text-gray-500 dark:text-gray-400">
              {form.missing_fields?.length || 0} champ(s) manquant(s)
            </span>
          </div>
          <ConfidenceBar value={form.prefill_confidence} />
        </div>
      )}

      {/* Complement request banner */}
      {form.status === 'complement_requested' && form.complement_details && (
        <div className="p-3 bg-orange-50 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-800 rounded-lg">
          <div className="flex items-start gap-2">
            <AlertTriangle className="w-4 h-4 text-orange-500 mt-0.5 flex-shrink-0" />
            <div>
              <p className="text-sm font-medium text-orange-700 dark:text-orange-300">
                Complement demande par l'autorite
              </p>
              <p className="text-xs text-orange-600 dark:text-orange-400 mt-1">{form.complement_details}</p>
            </div>
          </div>
        </div>
      )}

      {/* Form fields */}
      <div className="space-y-3">
        {fieldEntries.map(([name, field]: [string, FormFieldValue]) => {
          const isEditing = editingField === name;
          const isMissing = !field.value;

          return (
            <div
              key={name}
              className={cn(
                'p-3 rounded-lg border transition-colors',
                isMissing
                  ? 'bg-red-50/50 dark:bg-red-900/10 border-red-200 dark:border-red-800/50'
                  : 'bg-white dark:bg-gray-800 border-gray-200 dark:border-gray-700',
              )}
            >
              <div className="flex items-start justify-between gap-2">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                      {name.replace(/_/g, ' ')}
                    </span>
                    <ConfidenceDot confidence={field.confidence} />
                  </div>
                  {isEditing ? (
                    <div className="flex items-center gap-2 mt-1">
                      <input
                        type="text"
                        value={editValue}
                        onChange={(e) => setEditValue(e.target.value)}
                        className="flex-1 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-1 focus:ring-red-500 focus:border-red-500"
                        autoFocus
                      />
                      <button
                        onClick={() => handleFieldSave(name)}
                        disabled={updateMutation.isPending}
                        className="px-2 py-1 text-xs font-medium text-white bg-red-600 rounded hover:bg-red-700 disabled:opacity-50"
                      >
                        <Save className="w-3 h-3" />
                      </button>
                      <button
                        onClick={() => setEditingField(null)}
                        className="px-2 py-1 text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400"
                      >
                        Annuler
                      </button>
                    </div>
                  ) : (
                    <p
                      className={cn(
                        'text-sm',
                        field.value ? 'text-gray-900 dark:text-white' : 'text-red-500 dark:text-red-400 italic',
                      )}
                    >
                      {field.value || 'A remplir manuellement'}
                    </p>
                  )}
                  {field.source !== 'manual' && !field.manual_override && (
                    <p className="text-xs text-gray-400 dark:text-gray-500 mt-0.5">
                      <Info className="w-3 h-3 inline mr-0.5" />
                      Source: {field.source}
                    </p>
                  )}
                </div>
                {canEdit && !isEditing && (
                  <button
                    onClick={() => {
                      setEditingField(name);
                      setEditValue(field.value || '');
                    }}
                    className="text-xs text-gray-400 hover:text-red-600 dark:hover:text-red-400"
                  >
                    Modifier
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Missing attachments */}
      {form.missing_attachments && form.missing_attachments.length > 0 && (
        <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
          <h4 className="text-sm font-medium text-amber-700 dark:text-amber-300 mb-2">Documents manquants</h4>
          <ul className="space-y-1">
            {form.missing_attachments.map((att) => (
              <li key={att} className="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400">
                <Circle className="w-2.5 h-2.5 flex-shrink-0" />
                {att.replace(/_/g, ' ')}
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Submission timeline */}
      {(form.submitted_at || form.acknowledged_at) && (
        <div className="p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
          <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Historique</h4>
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
              <Clock className="w-3 h-3" />
              Cree le {new Date(form.created_at).toLocaleDateString('fr-CH')}
            </div>
            {form.submitted_at && (
              <div className="flex items-center gap-2 text-xs text-gray-500 dark:text-gray-400">
                <Send className="w-3 h-3" />
                Soumis le {new Date(form.submitted_at).toLocaleDateString('fr-CH')}
                {form.submission_reference && ` (Ref: ${form.submission_reference})`}
              </div>
            )}
            {form.acknowledged_at && (
              <div className="flex items-center gap-2 text-xs text-green-600 dark:text-green-400">
                <CheckCircle2 className="w-3 h-3" />
                Accepte le {new Date(form.acknowledged_at).toLocaleDateString('fr-CH')}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action buttons */}
      {canEdit && (
        <div className="flex items-center gap-3 pt-2 border-t border-gray-200 dark:border-gray-700">
          {canSubmit && (
            <button
              onClick={() => submitMutation.mutate()}
              disabled={submitMutation.isPending}
              className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              {submitMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              Soumettre
            </button>
          )}
          <button
            onClick={onBack}
            className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
          >
            <Save className="w-4 h-4" />
            Enregistrer brouillon
          </button>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main FormsWorkspace component
// ---------------------------------------------------------------------------

export default function FormsWorkspace({ buildingId }: FormsWorkspaceProps) {
  const { t } = useTranslation();
  const [selectedFormId, setSelectedFormId] = useState<string | null>(null);

  if (selectedFormId) {
    return (
      <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
        <FormInstanceView formId={selectedFormId} buildingId={buildingId} onBack={() => setSelectedFormId(null)} />
      </div>
    );
  }

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
      <div className="flex items-center gap-2 mb-4">
        <FileText className="w-5 h-5 text-red-500" />
        <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
          {t('forms.title') || 'Formulaires reglementaires'}
        </h2>
      </div>
      <p className="text-sm text-gray-500 dark:text-gray-400 mb-6">
        {t('forms.description') ||
          'Identifiez les formulaires applicables, pre-remplissez-les depuis les donnees du batiment, et suivez leur soumission.'}
      </p>
      <ApplicableFormsList buildingId={buildingId} onPrefill={(form) => setSelectedFormId(form.id)} />
    </div>
  );
}
