import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cn } from '@/utils/formatters';
import {
  rfqApi,
  type TenderRequest,
  type TenderCreatePayload,
  type TenderComparison,
  type TenderQuote,
} from '@/api/rfq';
import QuoteComparison from '@/components/rfq/QuoteComparison';
import QuoteCard from '@/components/rfq/QuoteCard';
import {
  Plus,
  Loader2,
  X,
  FileText,
  ChevronRight,
  ChevronDown,
  Send,
  Clock,
  ArrowLeft,
  Sparkles,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const TENDER_STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
  sent: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  collecting: 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400',
  closed: 'bg-slate-100 text-slate-600 dark:bg-slate-700 dark:text-slate-300',
  attributed: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  cancelled: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
};

const TENDER_STATUS_LABELS: Record<string, string> = {
  draft: 'Brouillon',
  sent: 'Envoye',
  collecting: 'En collecte',
  closed: 'Cloture',
  attributed: 'Attribue',
  cancelled: 'Annule',
};

const WORK_TYPES = [
  { value: 'asbestos_removal', label: 'Desamiantage' },
  { value: 'pcb_removal', label: 'Elimination PCB' },
  { value: 'lead_removal', label: 'Elimination plomb' },
  { value: 'hap_removal', label: 'Elimination HAP' },
  { value: 'radon_mitigation', label: 'Assainissement radon' },
  { value: 'pfas_remediation', label: 'Remediation PFAS' },
  { value: 'multi_pollutant', label: 'Multi-polluants' },
  { value: 'other', label: 'Autre' },
] as const;

const WORK_TYPE_COLORS: Record<string, string> = {
  asbestos_removal: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  pcb_removal: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  lead_removal: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  hap_removal: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
  radon_mitigation: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  pfas_remediation: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  multi_pollutant: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  other: 'bg-gray-100 text-gray-600 dark:bg-slate-700 dark:text-slate-300',
};

function getWorkTypeLabel(value: string): string {
  return WORK_TYPES.find((wt) => wt.value === value)?.label ?? value;
}

function formatDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '-';
  try {
    return new Date(dateStr).toLocaleDateString('fr-CH');
  } catch {
    return dateStr;
  }
}

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={cn(
        'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
        TENDER_STATUS_COLORS[status] || TENDER_STATUS_COLORS.draft,
      )}
    >
      {TENDER_STATUS_LABELS[status] || status}
    </span>
  );
}

function WorkTypeBadge({ workType }: { workType: string }) {
  return (
    <span
      className={cn(
        'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
        WORK_TYPE_COLORS[workType] || WORK_TYPE_COLORS.other,
      )}
    >
      {getWorkTypeLabel(workType)}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Creation form
// ---------------------------------------------------------------------------

interface TenderFormProps {
  buildingId: string;
  onClose: () => void;
  onCreated: (tender: TenderRequest) => void;
}

function TenderCreateForm({ buildingId, onClose, onCreated }: TenderFormProps) {
  const [formState, setFormState] = useState({
    work_type: 'asbestos_removal',
    title: '',
    description: '',
    deadline_submission: '',
    planned_start_date: '',
    planned_end_date: '',
  });
  const [generating, setGenerating] = useState(false);
  const [scopeSummary, setScopeSummary] = useState<string | null>(null);
  const [autoAttachments, setAutoAttachments] = useState<string[]>([]);

  const queryClient = useQueryClient();

  const createMutation = useMutation({
    mutationFn: (payload: TenderCreatePayload) => rfqApi.generateDraft(payload),
    onSuccess: (tender) => {
      queryClient.invalidateQueries({ queryKey: ['building-tenders', buildingId] });
      onCreated(tender);
    },
  });

  const handleGenerateFromDossier = async () => {
    setGenerating(true);
    try {
      const draft = await rfqApi.generateDraft({
        building_id: buildingId,
        title: formState.title || `Appel d'offres - ${getWorkTypeLabel(formState.work_type)}`,
        work_type: formState.work_type,
        description: formState.description || undefined,
        deadline_submission: formState.deadline_submission || undefined,
        planned_start_date: formState.planned_start_date || undefined,
        planned_end_date: formState.planned_end_date || undefined,
      });
      // Pre-fill from generated draft
      setFormState((s) => ({
        ...s,
        title: draft.title,
        description: draft.description ?? s.description,
      }));
      setScopeSummary(draft.scope_summary);
      setAutoAttachments(draft.attachments_auto ?? []);
      queryClient.invalidateQueries({ queryKey: ['building-tenders', buildingId] });
      onCreated(draft);
    } catch {
      // Error handled by axios interceptors
    } finally {
      setGenerating(false);
    }
  };

  const handleSaveDraft = () => {
    createMutation.mutate({
      building_id: buildingId,
      title: formState.title || `Appel d'offres - ${getWorkTypeLabel(formState.work_type)}`,
      work_type: formState.work_type,
      description: formState.description || undefined,
      deadline_submission: formState.deadline_submission || undefined,
      planned_start_date: formState.planned_start_date || undefined,
      planned_end_date: formState.planned_end_date || undefined,
    });
  };

  const isSubmitting = createMutation.isPending || generating;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white">Nouvel appel d'offres</h3>
        <button
          onClick={onClose}
          className="p-1.5 text-gray-400 hover:text-gray-600 dark:hover:text-slate-200 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Work type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
          Type de travaux
        </label>
        <select
          value={formState.work_type}
          onChange={(e) => setFormState((s) => ({ ...s, work_type: e.target.value }))}
          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent"
        >
          {WORK_TYPES.map((wt) => (
            <option key={wt.value} value={wt.value}>
              {wt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Title */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Titre</label>
        <input
          type="text"
          value={formState.title}
          onChange={(e) => setFormState((s) => ({ ...s, title: e.target.value }))}
          placeholder={`Appel d'offres - ${getWorkTypeLabel(formState.work_type)}`}
          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent"
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Description</label>
        <textarea
          rows={3}
          value={formState.description}
          onChange={(e) => setFormState((s) => ({ ...s, description: e.target.value }))}
          placeholder="Description des travaux..."
          className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent"
        />
      </div>

      {/* Dates */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            Deadline de soumission
          </label>
          <input
            type="date"
            value={formState.deadline_submission}
            onChange={(e) => setFormState((s) => ({ ...s, deadline_submission: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            Debut prevu
          </label>
          <input
            type="date"
            value={formState.planned_start_date}
            onChange={(e) => setFormState((s) => ({ ...s, planned_start_date: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            Fin prevue
          </label>
          <input
            type="date"
            value={formState.planned_end_date}
            onChange={(e) => setFormState((s) => ({ ...s, planned_end_date: e.target.value }))}
            className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-red-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Scope summary (read-only, shown after generation) */}
      {scopeSummary && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            Resume du perimetre (genere)
          </label>
          <div className="p-3 bg-gray-50 dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg text-sm text-gray-700 dark:text-slate-300 whitespace-pre-wrap">
            {scopeSummary}
          </div>
        </div>
      )}

      {/* Auto-attached documents */}
      {autoAttachments.length > 0 && (
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            Documents attaches automatiquement
          </label>
          <ul className="space-y-1">
            {autoAttachments.map((doc, idx) => (
              <li
                key={idx}
                className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-400"
              >
                <FileText className="w-4 h-4 shrink-0" />
                <span className="truncate">{doc}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Actions */}
      <div className="flex flex-col sm:flex-row gap-3 pt-2">
        <button
          onClick={handleGenerateFromDossier}
          disabled={isSubmitting}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
          Generer depuis le dossier
        </button>
        <button
          onClick={handleSaveDraft}
          disabled={isSubmitting}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-gray-700 dark:text-slate-200 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {createMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
          Enregistrer comme brouillon
        </button>
        <button
          onClick={onClose}
          disabled={isSubmitting}
          className="inline-flex items-center justify-center gap-2 px-4 py-2 text-sm font-medium text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
        >
          Annuler
        </button>
      </div>

      {createMutation.isError && (
        <p className="text-sm text-red-600 dark:text-red-400">
          Erreur lors de la creation. Veuillez reessayer.
        </p>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tender detail view
// ---------------------------------------------------------------------------

interface TenderDetailProps {
  tender: TenderRequest;
  buildingId: string;
  onBack: () => void;
}

function TenderDetailView({ tender, buildingId, onBack }: TenderDetailProps) {
  const queryClient = useQueryClient();
  const [showSendInput, setShowSendInput] = useState(false);
  const [contractorOrgIds, setContractorOrgIds] = useState('');
  const [comparison, setComparison] = useState<TenderComparison | null>(null);

  const sendMutation = useMutation({
    mutationFn: () => {
      const ids = contractorOrgIds
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean);
      return rfqApi.send(tender.id, ids);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-tenders', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['tender-detail', tender.id] });
      queryClient.invalidateQueries({ queryKey: ['tender-quotes', tender.id] });
      setShowSendInput(false);
      setContractorOrgIds('');
    },
  });

  const compareMutation = useMutation({
    mutationFn: () => rfqApi.generateComparison(tender.id),
    onSuccess: (data) => {
      setComparison(data);
      queryClient.invalidateQueries({ queryKey: ['building-tenders', buildingId] });
    },
  });

  const attributeMutation = useMutation({
    mutationFn: ({ quoteId, reason }: { quoteId: string; reason: string }) =>
      rfqApi.attribute(tender.id, quoteId, reason),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['building-tenders', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['tender-detail', tender.id] });
      queryClient.invalidateQueries({ queryKey: ['tender-quotes', tender.id] });
    },
  });

  const extractMutation = useMutation({
    mutationFn: (quoteId: string) => rfqApi.extractQuoteData(tender.id, quoteId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tender-quotes', tender.id] });
    },
  });

  // Fetch full tender details
  const { data: fullTender } = useQuery({
    queryKey: ['tender-detail', tender.id],
    queryFn: () => rfqApi.get(tender.id),
    initialData: tender,
  });

  // Fetch quotes for this tender
  const { data: quotes = [] } = useQuery<TenderQuote[]>({
    queryKey: ['tender-quotes', tender.id],
    queryFn: () => rfqApi.listQuotes(tender.id),
    enabled: !!tender.id,
  });

  const currentTender = fullTender ?? tender;

  return (
    <div className="space-y-6">
      {/* Back button + header */}
      <div>
        <button
          onClick={onBack}
          className="inline-flex items-center gap-1 text-sm text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200 mb-4"
        >
          <ArrowLeft className="w-4 h-4" />
          Retour a la liste
        </button>

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{currentTender.title}</h3>
            <div className="flex items-center gap-2 mt-1">
              <StatusBadge status={currentTender.status} />
              <WorkTypeBadge workType={currentTender.work_type} />
            </div>
          </div>
          <div className="text-sm text-gray-500 dark:text-slate-400 space-y-1">
            {currentTender.deadline_submission && (
              <div className="flex items-center gap-1">
                <Clock className="w-3.5 h-3.5" />
                Deadline: {formatDate(currentTender.deadline_submission)}
              </div>
            )}
            {currentTender.planned_start_date && (
              <div>Debut: {formatDate(currentTender.planned_start_date)}</div>
            )}
            {currentTender.planned_end_date && (
              <div>Fin: {formatDate(currentTender.planned_end_date)}</div>
            )}
          </div>
        </div>
      </div>

      {/* Scope summary */}
      {currentTender.scope_summary && (
        <div className="bg-gray-50 dark:bg-slate-900 border border-gray-200 dark:border-slate-700 rounded-lg p-4">
          <h4 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">Resume du perimetre</h4>
          <p className="text-sm text-gray-600 dark:text-slate-400 whitespace-pre-wrap">
            {currentTender.scope_summary}
          </p>
        </div>
      )}

      {/* Description */}
      {currentTender.description && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Description</h4>
          <p className="text-sm text-gray-600 dark:text-slate-400">{currentTender.description}</p>
        </div>
      )}

      {/* Attached documents */}
      {((currentTender.attachments_auto && currentTender.attachments_auto.length > 0) ||
        (currentTender.attachments_manual && currentTender.attachments_manual.length > 0)) && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-2">Documents attaches</h4>
          <ul className="space-y-1">
            {(currentTender.attachments_auto ?? []).map((doc, idx) => (
              <li key={`auto-${idx}`} className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-400">
                <FileText className="w-4 h-4 shrink-0 text-blue-500" />
                <span className="truncate">{doc}</span>
                <span className="text-xs text-gray-400">(auto)</span>
              </li>
            ))}
            {(currentTender.attachments_manual ?? []).map((doc, idx) => (
              <li key={`manual-${idx}`} className="flex items-center gap-2 text-sm text-gray-600 dark:text-slate-400">
                <FileText className="w-4 h-4 shrink-0" />
                <span className="truncate">{doc}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Received quotes (QuoteCard list) */}
      {quotes.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-700 dark:text-slate-300 mb-3">
            {quotes.length} devis recu{quotes.length > 1 ? 's' : ''}
          </h4>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {quotes.map((quote) => (
              <QuoteCard
                key={quote.id}
                quote={quote}
                onExtract={(quoteId) => extractMutation.mutate(quoteId)}
                isExtracting={extractMutation.isPending}
              />
            ))}
          </div>
        </div>
      )}

      {/* Comparison (QuoteComparison component) */}
      {(quotes.length > 0 || comparison) && (
        <QuoteComparison
          tenderId={currentTender.id}
          quotes={quotes}
          comparison={comparison}
          onAttribute={(quoteId, reason) => attributeMutation.mutate({ quoteId, reason })}
          onGenerateComparison={() => compareMutation.mutate()}
          isGenerating={compareMutation.isPending}
          isAttributing={attributeMutation.isPending}
        />
      )}

      {/* Actions */}
      <div className="flex flex-wrap gap-3 pt-2 border-t border-gray-200 dark:border-slate-700">
        {currentTender.status === 'draft' && (
          <>
            {!showSendInput ? (
              <button
                onClick={() => setShowSendInput(true)}
                className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700"
              >
                <Send className="w-4 h-4" />
                Envoyer aux prestataires
              </button>
            ) : (
              <div className="w-full space-y-3">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
                    IDs des organisations prestataires (separes par des virgules)
                  </label>
                  <input
                    type="text"
                    value={contractorOrgIds}
                    onChange={(e) => setContractorOrgIds(e.target.value)}
                    placeholder="uuid1, uuid2, ..."
                    className="w-full px-3 py-2 border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => sendMutation.mutate()}
                    disabled={sendMutation.isPending || !contractorOrgIds.trim()}
                    className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50"
                  >
                    {sendMutation.isPending && <Loader2 className="w-4 h-4 animate-spin" />}
                    Confirmer l'envoi
                  </button>
                  <button
                    onClick={() => setShowSendInput(false)}
                    className="px-4 py-2 text-sm font-medium text-gray-500 dark:text-slate-400 hover:text-gray-700 dark:hover:text-slate-200"
                  >
                    Annuler
                  </button>
                </div>
                {sendMutation.isError && (
                  <p className="text-sm text-red-600 dark:text-red-400">Erreur lors de l'envoi.</p>
                )}
              </div>
            )}
          </>
        )}
      </div>

      <div className="text-xs text-gray-400 dark:text-slate-500 pt-2">
        Cree le {formatDate(currentTender.created_at)}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tender list item
// ---------------------------------------------------------------------------

interface TenderListItemProps {
  tender: TenderRequest;
  isExpanded: boolean;
  onToggle: () => void;
}

function TenderListItem({ tender, isExpanded, onToggle }: TenderListItemProps) {
  return (
    <button
      onClick={onToggle}
      className={cn(
        'w-full text-left px-4 py-3 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors',
        isExpanded && 'bg-gray-50 dark:bg-slate-700/50',
      )}
    >
      {isExpanded ? (
        <ChevronDown className="w-4 h-4 text-gray-400 shrink-0" />
      ) : (
        <ChevronRight className="w-4 h-4 text-gray-400 shrink-0" />
      )}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-sm font-medium text-gray-900 dark:text-white truncate">{tender.title}</span>
          <WorkTypeBadge workType={tender.work_type} />
          <StatusBadge status={tender.status} />
        </div>
        <div className="flex items-center gap-4 mt-1 text-xs text-gray-500 dark:text-slate-400">
          {tender.deadline_submission && (
            <span className="flex items-center gap-1">
              <Clock className="w-3 h-3" />
              {formatDate(tender.deadline_submission)}
            </span>
          )}
          <span>Cree le {formatDate(tender.created_at)}</span>
        </div>
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Main TenderTab
// ---------------------------------------------------------------------------

interface TenderTabProps {
  buildingId: string;
}

export default function TenderTab({ buildingId }: TenderTabProps) {
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [selectedTenderId, setSelectedTenderId] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const {
    data: tenders = [],
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['building-tenders', buildingId],
    queryFn: () => rfqApi.listByBuilding(buildingId),
    enabled: !!buildingId,
  });

  // If viewing a specific tender detail
  const selectedTender = tenders.find((t) => t.id === selectedTenderId);
  if (selectedTender) {
    return (
      <TenderDetailView
        tender={selectedTender}
        buildingId={buildingId}
        onBack={() => setSelectedTenderId(null)}
      />
    );
  }

  // If creating a new tender
  if (showCreateForm) {
    return (
      <TenderCreateForm
        buildingId={buildingId}
        onClose={() => setShowCreateForm(false)}
        onCreated={(tender) => {
          setShowCreateForm(false);
          setSelectedTenderId(tender.id);
        }}
      />
    );
  }

  // Loading state
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-8 h-8 animate-spin text-red-600" />
      </div>
    );
  }

  // Error state
  if (isError) {
    return (
      <div className="text-center py-12">
        <p className="text-sm text-red-600 dark:text-red-400">
          Erreur lors du chargement des appels d'offres.
        </p>
      </div>
    );
  }

  // Empty state
  if (tenders.length === 0) {
    return (
      <div className="text-center py-12 space-y-4">
        <FileText className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto" />
        <div>
          <p className="text-gray-500 dark:text-slate-400 text-sm">
            Aucun appel d'offres pour ce batiment
          </p>
          <p className="text-gray-400 dark:text-slate-500 text-xs mt-1">
            Creez un appel d'offres pour lancer une mise en concurrence encadree
          </p>
        </div>
        <button
          onClick={() => setShowCreateForm(true)}
          className="inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
        >
          <Plus className="w-4 h-4" />
          Creer un appel d'offres
        </button>
      </div>
    );
  }

  // List view
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium text-gray-700 dark:text-slate-300">
          {tenders.length} appel{tenders.length > 1 ? 's' : ''} d'offres
        </h3>
        <button
          onClick={() => setShowCreateForm(true)}
          className="inline-flex items-center gap-2 px-3 py-1.5 text-sm font-medium text-white bg-red-600 rounded-lg hover:bg-red-700"
        >
          <Plus className="w-4 h-4" />
          Nouveau
        </button>
      </div>

      <div className="border border-gray-200 dark:border-slate-700 rounded-lg divide-y divide-gray-200 dark:divide-slate-700 overflow-hidden">
        {tenders.map((tender) => (
          <div key={tender.id}>
            <TenderListItem
              tender={tender}
              isExpanded={expandedId === tender.id}
              onToggle={() => setExpandedId(expandedId === tender.id ? null : tender.id)}
            />
            {expandedId === tender.id && (
              <div className="px-4 pb-4 bg-gray-50 dark:bg-slate-700/30">
                <div className="pt-2 space-y-3">
                  {tender.description && (
                    <p className="text-sm text-gray-600 dark:text-slate-400">{tender.description}</p>
                  )}
                  {tender.scope_summary && (
                    <div>
                      <span className="text-xs font-medium text-gray-500 dark:text-slate-400">Perimetre: </span>
                      <span className="text-xs text-gray-600 dark:text-slate-400">{tender.scope_summary}</span>
                    </div>
                  )}
                  <div className="flex items-center gap-3 text-xs text-gray-500 dark:text-slate-400">
                    {tender.planned_start_date && <span>Debut: {formatDate(tender.planned_start_date)}</span>}
                    {tender.planned_end_date && <span>Fin: {formatDate(tender.planned_end_date)}</span>}
                  </div>
                  <button
                    onClick={() => setSelectedTenderId(tender.id)}
                    className="inline-flex items-center gap-1 text-sm text-red-600 dark:text-red-400 hover:text-red-700 dark:hover:text-red-300 font-medium"
                  >
                    Voir le detail
                    <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
