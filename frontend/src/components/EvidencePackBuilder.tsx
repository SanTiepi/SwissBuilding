import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { evidencePacksApi } from '@/api/evidencePacks';
import type {
  EvidencePack,
  EvidencePackCreate,
  EvidencePackPurpose,
  IncludedArtefact,
  IncludedDocument,
  RequiredSection,
} from '@/api/evidencePacks';
import { documentsApi } from '@/api/documents';
import { diagnosticsApi } from '@/api/diagnostics';
import { evidenceSummaryApi } from '@/api/evidenceSummary';
import type { Sample } from '@/types';
import { formatDateTime } from '@/utils/formatters';
import {
  Package,
  Search,
  CheckSquare,
  Square,
  ChevronDown,
  ChevronUp,
  FileText,
  FlaskConical,
  Stethoscope,
  Image,
  Shield,
  Loader2,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  Trash2,
  Eye,
  Plus,
  X,
} from 'lucide-react';

// ---------------------------------------------------------------------------
// Types for the internal item model
// ---------------------------------------------------------------------------

type EvidenceItemType = 'document' | 'sample' | 'diagnostic' | 'photo' | 'artefact';

interface EvidenceItem {
  id: string;
  type: EvidenceItemType;
  title: string;
  subtitle: string;
  date: string;
}

// Purpose-based required evidence types
const PURPOSE_REQUIREMENTS: Record<EvidencePackPurpose, EvidenceItemType[]> = {
  authority_submission: ['diagnostic', 'sample', 'document', 'artefact'],
  internal_audit: ['diagnostic', 'document', 'sample'],
  handoff: ['diagnostic', 'document', 'sample', 'photo'],
  insurance: ['diagnostic', 'document', 'photo'],
};

const GROUP_ICONS: Record<EvidenceItemType, typeof FileText> = {
  document: FileText,
  sample: FlaskConical,
  diagnostic: Stethoscope,
  photo: Image,
  artefact: Shield,
};

const PURPOSES: EvidencePackPurpose[] = ['authority_submission', 'internal_audit', 'handoff', 'insurance'];

// ---------------------------------------------------------------------------
// Sub-components
// ---------------------------------------------------------------------------

interface ItemGroupProps {
  type: EvidenceItemType;
  items: EvidenceItem[];
  selected: Set<string>;
  onToggle: (id: string) => void;
  onToggleAll: (type: EvidenceItemType) => void;
  searchQuery: string;
  t: (key: string, params?: Record<string, string | number>) => string;
}

function ItemGroup({ type, items, selected, onToggle, onToggleAll, searchQuery, t }: ItemGroupProps) {
  const [expanded, setExpanded] = useState(true);
  const Icon = GROUP_ICONS[type];

  const filtered = useMemo(() => {
    if (!searchQuery) return items;
    const q = searchQuery.toLowerCase();
    return items.filter((item) => item.title.toLowerCase().includes(q) || item.subtitle.toLowerCase().includes(q));
  }, [items, searchQuery]);

  const selectedCount = filtered.filter((i) => selected.has(i.id)).length;
  const allSelected = filtered.length > 0 && selectedCount === filtered.length;

  return (
    <div className="rounded-lg border border-gray-200 dark:border-slate-700">
      <button
        type="button"
        className="flex w-full items-center justify-between px-4 py-3 text-left hover:bg-gray-50 dark:hover:bg-slate-800"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2">
          <Icon className="h-4 w-4 text-gray-500 dark:text-gray-400" />
          <span className="text-sm font-medium text-gray-900 dark:text-white">{t(`evidence_pack.group_${type}`)}</span>
          <span className="rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-slate-700 dark:text-gray-300">
            {filtered.length}
          </span>
          {selectedCount > 0 && (
            <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700 dark:bg-blue-900/30 dark:text-blue-400">
              {selectedCount} {t('evidence_pack.selected_short')}
            </span>
          )}
        </div>
        {expanded ? <ChevronUp className="h-4 w-4 text-gray-400" /> : <ChevronDown className="h-4 w-4 text-gray-400" />}
      </button>

      {expanded && (
        <div className="border-t border-gray-200 dark:border-slate-700">
          {filtered.length > 0 && (
            <button
              type="button"
              className="flex w-full items-center gap-2 px-4 py-2 text-xs text-blue-600 hover:bg-blue-50 dark:text-blue-400 dark:hover:bg-slate-800"
              onClick={() => onToggleAll(type)}
            >
              {allSelected ? <CheckSquare className="h-3.5 w-3.5" /> : <Square className="h-3.5 w-3.5" />}
              {allSelected ? t('evidence_pack.deselect_all') : t('evidence_pack.select_all')}
            </button>
          )}
          <div className="max-h-48 overflow-y-auto">
            {filtered.length === 0 ? (
              <p className="px-4 py-3 text-xs italic text-gray-400 dark:text-gray-500">
                {t('evidence_pack.no_items_in_group')}
              </p>
            ) : (
              filtered.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  className="flex w-full items-center gap-3 px-4 py-2 text-left hover:bg-gray-50 dark:hover:bg-slate-800"
                  onClick={() => onToggle(item.id)}
                >
                  {selected.has(item.id) ? (
                    <CheckSquare className="h-4 w-4 flex-shrink-0 text-blue-600 dark:text-blue-400" />
                  ) : (
                    <Square className="h-4 w-4 flex-shrink-0 text-gray-400 dark:text-gray-500" />
                  )}
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm text-gray-900 dark:text-white">{item.title}</p>
                    <p className="truncate text-xs text-gray-500 dark:text-gray-400">{item.subtitle}</p>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Pack detail view
// ---------------------------------------------------------------------------

interface PackDetailProps {
  pack: EvidencePack;
  onClose: () => void;
  t: (key: string, params?: Record<string, string | number>) => string;
}

function PackDetail({ pack, onClose, t }: PackDetailProps) {
  const artefacts = pack.included_artefacts_json ?? [];
  const documents = pack.included_documents_json ?? [];
  const sections = pack.required_sections_json ?? [];

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 dark:border-slate-700 dark:bg-slate-800">
      <div className="mb-3 flex items-center justify-between">
        <h4 className="text-sm font-semibold text-gray-900 dark:text-white">{pack.title}</h4>
        <button type="button" onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
          <X className="h-4 w-4" />
        </button>
      </div>

      {pack.description && <p className="mb-3 text-xs text-gray-500 dark:text-gray-400">{pack.description}</p>}

      {sections.length > 0 && (
        <div className="mb-3">
          <h5 className="mb-1 text-xs font-medium text-gray-700 dark:text-gray-300">
            {t('evidence_pack.required_sections')}
          </h5>
          <div className="space-y-1">
            {sections.map((s, i) => (
              <div key={i} className="flex items-center gap-2 text-xs">
                {s.included ? (
                  <CheckCircle2 className="h-3.5 w-3.5 text-green-500" />
                ) : (
                  <XCircle className="h-3.5 w-3.5 text-red-400" />
                )}
                <span className="text-gray-700 dark:text-gray-300">{s.label}</span>
                {s.required && <span className="text-[10px] text-red-500">*</span>}
              </div>
            ))}
          </div>
        </div>
      )}

      {artefacts.length > 0 && (
        <div className="mb-3">
          <h5 className="mb-1 text-xs font-medium text-gray-700 dark:text-gray-300">
            {t('evidence_pack.artefacts')} ({artefacts.length})
          </h5>
          <ul className="space-y-0.5">
            {artefacts.map((a, i) => (
              <li key={i} className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                <Shield className="h-3 w-3 flex-shrink-0" />
                <span className="truncate">{a.title || a.artefact_type}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {documents.length > 0 && (
        <div>
          <h5 className="mb-1 text-xs font-medium text-gray-700 dark:text-gray-300">
            {t('evidence_pack.documents')} ({documents.length})
          </h5>
          <ul className="space-y-0.5">
            {documents.map((d, i) => (
              <li key={i} className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
                <FileText className="h-3 w-3 flex-shrink-0" />
                <span className="truncate">{d.title || d.document_type}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {pack.notes && (
        <div className="mt-3 rounded bg-gray-50 p-2 text-xs text-gray-600 dark:bg-slate-900 dark:text-gray-400">
          {pack.notes}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main builder component
// ---------------------------------------------------------------------------

interface EvidencePackBuilderProps {
  buildingId: string;
}

export function EvidencePackBuilder({ buildingId }: EvidencePackBuilderProps) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  // Local state
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [packName, setPackName] = useState('');
  const [purpose, setPurpose] = useState<EvidencePackPurpose>('authority_submission');
  const [targetAudience, setTargetAudience] = useState('');
  const [notes, setNotes] = useState('');
  const [expandedPackId, setExpandedPackId] = useState<string | null>(null);
  const [showBuilder, setShowBuilder] = useState(false);

  // Data fetching
  const { data: documents = [], isLoading: docsLoading } = useQuery({
    queryKey: ['documents', buildingId],
    queryFn: () => documentsApi.listByBuilding(buildingId),
  });

  const { data: diagnostics = [], isLoading: diagLoading } = useQuery({
    queryKey: ['diagnostics', buildingId],
    queryFn: () => diagnosticsApi.listByBuilding(buildingId),
  });

  // Pre-fetch evidence summary for potential future use
  useQuery({
    queryKey: ['evidenceSummary', buildingId],
    queryFn: () => evidenceSummaryApi.get(buildingId),
  });

  const { data: packsData, isLoading: packsLoading } = useQuery({
    queryKey: ['evidencePacks', buildingId],
    queryFn: () => evidencePacksApi.list(buildingId, { size: 50 }),
  });

  const packs = packsData?.items ?? [];

  // Fetch all samples from diagnostics
  const allSamples = useMemo(() => {
    const samples: (Sample & { diagnostic_type?: string })[] = [];
    for (const diag of diagnostics) {
      if (diag.samples) {
        for (const s of diag.samples) {
          samples.push({ ...s, diagnostic_type: diag.diagnostic_type });
        }
      }
    }
    return samples;
  }, [diagnostics]);

  // Build evidence items grouped by type
  const itemsByType = useMemo(() => {
    const groups: Record<EvidenceItemType, EvidenceItem[]> = {
      document: [],
      sample: [],
      diagnostic: [],
      photo: [],
      artefact: [],
    };

    // Documents
    for (const doc of documents) {
      const isPhoto = doc.mime_type?.startsWith('image/') || doc.document_type === 'photo';
      const type: EvidenceItemType = isPhoto ? 'photo' : 'document';
      groups[type].push({
        id: `doc-${doc.id}`,
        type,
        title: doc.file_name,
        subtitle: doc.document_type + (doc.description ? ` - ${doc.description}` : ''),
        date: doc.created_at,
      });
    }

    // Diagnostics
    for (const diag of diagnostics) {
      groups.diagnostic.push({
        id: `diag-${diag.id}`,
        type: 'diagnostic',
        title: `${diag.diagnostic_type} - ${diag.status}`,
        subtitle: diag.summary || diag.date_inspection,
        date: diag.date_inspection,
      });
    }

    // Samples
    for (const s of allSamples) {
      groups.sample.push({
        id: `sample-${s.id}`,
        type: 'sample',
        title: `${s.sample_number} - ${s.pollutant_type}`,
        subtitle: [s.location_floor, s.location_room, s.material_category].filter(Boolean).join(' / '),
        date: s.created_at,
      });
    }

    return groups;
  }, [documents, diagnostics, allSamples]);

  const allItems = useMemo(() => Object.values(itemsByType).flat(), [itemsByType]);

  // Toggle selection
  const toggleItem = useCallback((id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleAllInGroup = useCallback(
    (type: EvidenceItemType) => {
      const items = itemsByType[type];
      const q = searchQuery.toLowerCase();
      const filtered = q
        ? items.filter((i) => i.title.toLowerCase().includes(q) || i.subtitle.toLowerCase().includes(q))
        : items;
      const allSelected = filtered.every((i) => selected.has(i.id));
      setSelected((prev) => {
        const next = new Set(prev);
        for (const item of filtered) {
          if (allSelected) next.delete(item.id);
          else next.add(item.id);
        }
        return next;
      });
    },
    [itemsByType, selected, searchQuery],
  );

  // Completeness check based on purpose
  const completenessInfo = useMemo(() => {
    const required = PURPOSE_REQUIREMENTS[purpose];
    const included: EvidenceItemType[] = [];
    const missing: EvidenceItemType[] = [];

    for (const reqType of required) {
      const hasSelected = itemsByType[reqType].some((i) => selected.has(i.id));
      if (hasSelected) included.push(reqType);
      else missing.push(reqType);
    }

    const ratio = required.length > 0 ? included.length / required.length : 1;
    return { included, missing, ratio, required };
  }, [purpose, itemsByType, selected]);

  // Count selected by type
  const selectedByType = useMemo(() => {
    const counts: Record<EvidenceItemType, number> = { document: 0, sample: 0, diagnostic: 0, photo: 0, artefact: 0 };
    for (const id of selected) {
      const item = allItems.find((i) => i.id === id);
      if (item) counts[item.type]++;
    }
    return counts;
  }, [selected, allItems]);

  // Create pack mutation
  const createMutation = useMutation({
    mutationFn: (data: EvidencePackCreate) => evidencePacksApi.create(buildingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidencePacks', buildingId] });
      // Reset form
      setSelected(new Set());
      setPackName('');
      setPurpose('authority_submission');
      setTargetAudience('');
      setNotes('');
      setShowBuilder(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (packId: string) => evidencePacksApi.delete(buildingId, packId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['evidencePacks', buildingId] });
      setExpandedPackId(null);
    },
  });

  // Generate handler
  const handleGenerate = useCallback(() => {
    const includedDocs: IncludedDocument[] = [];
    const includedArtefacts: IncludedArtefact[] = [];
    const sections: RequiredSection[] = [];

    for (const id of selected) {
      const item = allItems.find((i) => i.id === id);
      if (!item) continue;

      if (item.type === 'document' || item.type === 'photo') {
        const realId = item.id.replace('doc-', '');
        includedDocs.push({ document_id: realId, document_type: item.type, title: item.title });
      } else {
        const realId = item.id.replace(/^(diag|sample)-/, '');
        includedArtefacts.push({
          artefact_type: item.type,
          artefact_id: realId,
          status: 'included',
          title: item.title,
        });
      }
    }

    // Build required sections from purpose
    for (const reqType of completenessInfo.required) {
      sections.push({
        section_type: reqType,
        label: t(`evidence_pack.group_${reqType}`),
        required: true,
        included: completenessInfo.included.includes(reqType),
      });
    }

    const packTypeMap: Record<EvidencePackPurpose, string> = {
      authority_submission: 'authority_pack',
      internal_audit: 'owner_pack',
      handoff: 'contractor_pack',
      insurance: 'owner_pack',
    };

    const data: EvidencePackCreate = {
      pack_type: packTypeMap[purpose],
      title: packName || t('evidence_pack.default_title'),
      description: `${t(`evidence_pack.purpose_${purpose}`)} - ${targetAudience || ''}`.trim(),
      status: 'complete',
      required_sections_json: sections,
      included_artefacts_json: includedArtefacts.length > 0 ? includedArtefacts : undefined,
      included_documents_json: includedDocs.length > 0 ? includedDocs : undefined,
      recipient_name: targetAudience || undefined,
      recipient_type:
        purpose === 'authority_submission'
          ? 'authority'
          : purpose === 'insurance'
            ? 'insurer'
            : purpose === 'handoff'
              ? 'contractor'
              : 'owner',
      notes: notes || undefined,
    };

    createMutation.mutate(data);
  }, [selected, allItems, completenessInfo, purpose, packName, targetAudience, notes, t, createMutation]);

  // Status badge
  function statusBadge(status: string) {
    const colors: Record<string, string> = {
      draft: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
      assembling: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
      complete: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
      submitted: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
      expired: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
    };
    return (
      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[status] || colors.draft}`}>
        {t(`evidence_pack.status_${status}`) || status}
      </span>
    );
  }

  function purposeBadge(desc: string | null) {
    if (!desc) return null;
    const purposeKey = PURPOSES.find((p) => desc.includes(t(`evidence_pack.purpose_${p}`)));
    if (!purposeKey) return null;
    const colors: Record<string, string> = {
      authority_submission: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
      internal_audit: 'bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-300',
      handoff: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
      insurance: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
    };
    return (
      <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${colors[purposeKey] || ''}`}>
        {t(`evidence_pack.purpose_${purposeKey}`)}
      </span>
    );
  }

  const isLoading = docsLoading || diagLoading;

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Package className="h-5 w-5 text-gray-700 dark:text-gray-300" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white">{t('evidence_pack.title')}</h3>
        </div>
        {!showBuilder && (
          <button
            type="button"
            className="inline-flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 dark:bg-blue-500 dark:hover:bg-blue-600"
            onClick={() => setShowBuilder(true)}
          >
            <Plus className="h-4 w-4" />
            {t('evidence_pack.new_pack')}
          </button>
        )}
      </div>

      {/* Builder panel */}
      {showBuilder && (
        <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm dark:border-slate-700 dark:bg-slate-800">
          <div className="mb-4 flex items-center justify-between">
            <h4 className="text-base font-semibold text-gray-900 dark:text-white">
              {t('evidence_pack.builder_title')}
            </h4>
            <button
              type="button"
              onClick={() => setShowBuilder(false)}
              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              <X className="h-5 w-5" />
            </button>
          </div>

          <div className="grid gap-6 lg:grid-cols-2">
            {/* Left column: Item selector */}
            <div className="space-y-4">
              <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300">
                {t('evidence_pack.select_items')}
              </h5>

              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder={t('evidence_pack.search_placeholder')}
                  className="w-full rounded-lg border border-gray-300 py-2 pl-9 pr-3 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white dark:placeholder-gray-500"
                />
              </div>

              {isLoading ? (
                <div className="flex items-center justify-center py-8">
                  <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
                </div>
              ) : (
                <div className="space-y-3">
                  {(Object.keys(itemsByType) as EvidenceItemType[]).map((type) => (
                    <ItemGroup
                      key={type}
                      type={type}
                      items={itemsByType[type]}
                      selected={selected}
                      onToggle={toggleItem}
                      onToggleAll={toggleAllInGroup}
                      searchQuery={searchQuery}
                      t={t}
                    />
                  ))}
                </div>
              )}
            </div>

            {/* Right column: Metadata form + preview */}
            <div className="space-y-4">
              {/* Metadata form */}
              <h5 className="text-sm font-medium text-gray-700 dark:text-gray-300">{t('evidence_pack.metadata')}</h5>

              <div className="space-y-3">
                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                    {t('evidence_pack.pack_name')}
                  </label>
                  <input
                    type="text"
                    value={packName}
                    onChange={(e) => setPackName(e.target.value)}
                    placeholder={t('evidence_pack.pack_name_placeholder')}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white dark:placeholder-gray-500"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                    {t('evidence_pack.purpose')}
                  </label>
                  <select
                    value={purpose}
                    onChange={(e) => setPurpose(e.target.value as EvidencePackPurpose)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white"
                  >
                    {PURPOSES.map((p) => (
                      <option key={p} value={p}>
                        {t(`evidence_pack.purpose_${p}`)}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                    {t('evidence_pack.target_audience')}
                  </label>
                  <input
                    type="text"
                    value={targetAudience}
                    onChange={(e) => setTargetAudience(e.target.value)}
                    placeholder={t('evidence_pack.target_audience_placeholder')}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white dark:placeholder-gray-500"
                  />
                </div>

                <div>
                  <label className="mb-1 block text-xs font-medium text-gray-600 dark:text-gray-400">
                    {t('evidence_pack.notes')}
                  </label>
                  <textarea
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    rows={2}
                    placeholder={t('evidence_pack.notes_placeholder')}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-slate-600 dark:bg-slate-900 dark:text-white dark:placeholder-gray-500"
                  />
                </div>
              </div>

              {/* Pack preview */}
              <div className="rounded-lg border border-gray-200 bg-gray-50 p-4 dark:border-slate-700 dark:bg-slate-900">
                <h5 className="mb-3 text-sm font-medium text-gray-700 dark:text-gray-300">
                  {t('evidence_pack.preview')}
                </h5>

                {/* Selected counts */}
                <div className="mb-3 grid grid-cols-3 gap-2">
                  {(Object.keys(selectedByType) as EvidenceItemType[]).map((type) => {
                    const count = selectedByType[type];
                    if (count === 0 && itemsByType[type].length === 0) return null;
                    const Icon = GROUP_ICONS[type];
                    return (
                      <div
                        key={type}
                        className="flex items-center gap-1.5 rounded bg-white px-2 py-1.5 text-xs dark:bg-slate-800"
                      >
                        <Icon className="h-3.5 w-3.5 text-gray-400" />
                        <span className="font-medium text-gray-900 dark:text-white">{count}</span>
                        <span className="truncate text-gray-500 dark:text-gray-400">
                          {t(`evidence_pack.group_${type}`)}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {/* Completeness indicator */}
                <div className="mb-3">
                  <div className="mb-1 flex items-center justify-between text-xs">
                    <span className="text-gray-600 dark:text-gray-400">{t('evidence_pack.completeness')}</span>
                    <span className="font-medium text-gray-900 dark:text-white">
                      {Math.round(completenessInfo.ratio * 100)}%
                    </span>
                  </div>
                  <div className="h-2 overflow-hidden rounded-full bg-gray-200 dark:bg-slate-700">
                    <div
                      className={`h-full rounded-full transition-all ${
                        completenessInfo.ratio >= 1
                          ? 'bg-green-500'
                          : completenessInfo.ratio >= 0.5
                            ? 'bg-yellow-500'
                            : 'bg-red-500'
                      }`}
                      style={{ width: `${completenessInfo.ratio * 100}%` }}
                    />
                  </div>
                </div>

                {/* Missing critical items warning */}
                {completenessInfo.missing.length > 0 && (
                  <div className="rounded-lg border border-yellow-200 bg-yellow-50 p-3 dark:border-yellow-800 dark:bg-yellow-900/20">
                    <div className="mb-1 flex items-center gap-1.5">
                      <AlertTriangle className="h-3.5 w-3.5 text-yellow-600 dark:text-yellow-400" />
                      <span className="text-xs font-medium text-yellow-800 dark:text-yellow-300">
                        {t('evidence_pack.missing_warning')}
                      </span>
                    </div>
                    <ul className="space-y-0.5">
                      {completenessInfo.missing.map((type) => (
                        <li
                          key={type}
                          className="flex items-center gap-1.5 text-xs text-yellow-700 dark:text-yellow-400"
                        >
                          <XCircle className="h-3 w-3 flex-shrink-0" />
                          {t(`evidence_pack.group_${type}`)}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {completenessInfo.ratio >= 1 && selected.size > 0 && (
                  <div className="rounded-lg border border-green-200 bg-green-50 p-3 dark:border-green-800 dark:bg-green-900/20">
                    <div className="flex items-center gap-1.5">
                      <CheckCircle2 className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
                      <span className="text-xs font-medium text-green-800 dark:text-green-300">
                        {t('evidence_pack.complete_message')}
                      </span>
                    </div>
                  </div>
                )}

                {/* Total selected */}
                <p className="mt-2 text-xs text-gray-500 dark:text-gray-400">
                  {t('evidence_pack.total_selected', { count: selected.size })}
                </p>
              </div>

              {/* Generate button */}
              <button
                type="button"
                disabled={selected.size === 0 || createMutation.isPending}
                onClick={handleGenerate}
                className="inline-flex w-full items-center justify-center gap-2 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:cursor-not-allowed disabled:opacity-50 dark:bg-blue-500 dark:hover:bg-blue-600"
              >
                {createMutation.isPending ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Package className="h-4 w-4" />
                )}
                {createMutation.isPending ? t('evidence_pack.generating') : t('evidence_pack.generate')}
              </button>

              {createMutation.isError && (
                <p className="text-xs text-red-600 dark:text-red-400">{t('evidence_pack.generate_error')}</p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Pack history */}
      <div>
        <h4 className="mb-3 text-sm font-semibold text-gray-900 dark:text-white">{t('evidence_pack.history')}</h4>

        {packsLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-gray-400" />
          </div>
        ) : packs.length === 0 ? (
          <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center dark:border-slate-600">
            <Package className="mx-auto mb-2 h-8 w-8 text-gray-300 dark:text-gray-600" />
            <p className="text-sm text-gray-500 dark:text-gray-400">{t('evidence_pack.no_packs')}</p>
          </div>
        ) : (
          <div className="space-y-3">
            {packs.map((pack) => {
              const itemCount =
                (pack.included_artefacts_json?.length ?? 0) + (pack.included_documents_json?.length ?? 0);
              const isExpanded = expandedPackId === pack.id;

              return (
                <div key={pack.id}>
                  <div
                    className={`rounded-lg border bg-white p-4 transition-colors dark:bg-slate-800 ${
                      isExpanded ? 'border-blue-300 dark:border-blue-700' : 'border-gray-200 dark:border-slate-700'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2">
                          <h5 className="truncate text-sm font-medium text-gray-900 dark:text-white">{pack.title}</h5>
                          {statusBadge(pack.status)}
                          {purposeBadge(pack.description)}
                        </div>
                        <div className="mt-1 flex items-center gap-3 text-xs text-gray-500 dark:text-gray-400">
                          <span>{formatDateTime(pack.created_at)}</span>
                          <span>
                            {itemCount} {t('evidence_pack.items_count')}
                          </span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          type="button"
                          onClick={() => setExpandedPackId(isExpanded ? null : pack.id)}
                          className="rounded p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600 dark:hover:bg-slate-700 dark:hover:text-gray-300"
                          title={t('evidence_pack.view_details')}
                        >
                          {isExpanded ? <ChevronUp className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                        </button>
                        <button
                          type="button"
                          onClick={() => {
                            if (window.confirm(t('evidence_pack.delete_confirm'))) {
                              deleteMutation.mutate(pack.id);
                            }
                          }}
                          className="rounded p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400"
                          title={t('evidence_pack.delete')}
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </div>
                  </div>

                  {isExpanded && (
                    <div className="mt-2">
                      <PackDetail pack={pack} onClose={() => setExpandedPackId(null)} t={t} />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
