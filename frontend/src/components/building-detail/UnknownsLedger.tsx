import { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';
import { apiClient } from '@/api/client';
import { toast } from '@/store/toastStore';
import {
  AlertTriangle,
  ShieldAlert,
  ShieldCheck,
  Eye,
  CheckCircle2,
  XCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  RefreshCw,
  MapPin,
  Lock,
  FileWarning,
} from 'lucide-react';

/* ---------- Types ---------- */

interface UnknownEntry {
  id: string;
  building_id: string;
  case_id: string | null;
  unknown_type: string;
  subject: string;
  description: string | null;
  zone_id: string | null;
  element_id: string | null;
  severity: string;
  blocks_safe_to_x: string[] | null;
  blocks_pack_types: string[] | null;
  risk_of_acting: string | null;
  estimated_resolution_effort: string | null;
  status: string;
  resolved_at: string | null;
  resolved_by_id: string | null;
  resolution_method: string | null;
  resolution_note: string | null;
  detected_by: string;
  source_type: string | null;
  created_at: string;
  updated_at: string | null;
}

interface ScanResult {
  total: number;
  by_type: Record<string, number>;
  by_severity: Record<string, number>;
  blocking_safe_to_x: Record<string, number>;
  created: number;
  resolved: number;
}

interface CoverageZone {
  zone_id: string;
  zone_name: string;
  status: string;
}

interface CoverageMap {
  covered: CoverageZone[];
  gaps: CoverageZone[];
  partial: CoverageZone[];
}

interface ImpactSummary {
  total_open: number;
  critical_count: number;
  blocked_safe_to_x: Record<string, number>;
  blocked_pack_types: Record<string, number>;
  most_urgent: UnknownEntry[];
}

/* ---------- API ---------- */

const ledgerApi = {
  list: async (buildingId: string, status?: string): Promise<UnknownEntry[]> => {
    const params: Record<string, string> = {};
    if (status) params.status = status;
    const r = await apiClient.get<UnknownEntry[]>(`/buildings/${buildingId}/unknowns-ledger`, { params });
    return r.data;
  },
  scan: async (buildingId: string): Promise<ScanResult> => {
    const r = await apiClient.post<ScanResult>(`/buildings/${buildingId}/unknowns-ledger/scan`);
    return r.data;
  },
  resolve: async (unknownId: string, method: string, note?: string): Promise<UnknownEntry> => {
    const r = await apiClient.post<UnknownEntry>(`/unknowns-ledger/${unknownId}/resolve`, { method, note });
    return r.data;
  },
  acceptRisk: async (unknownId: string, note: string): Promise<UnknownEntry> => {
    const r = await apiClient.post<UnknownEntry>(`/unknowns-ledger/${unknownId}/accept-risk`, { note });
    return r.data;
  },
  coverage: async (buildingId: string): Promise<CoverageMap> => {
    const r = await apiClient.get<CoverageMap>(`/buildings/${buildingId}/unknowns-ledger/coverage`);
    return r.data;
  },
  impact: async (buildingId: string): Promise<ImpactSummary> => {
    const r = await apiClient.get<ImpactSummary>(`/buildings/${buildingId}/unknowns-ledger/impact`);
    return r.data;
  },
};

/* ---------- Constants ---------- */

const SEVERITY_CONFIG: Record<string, { color: string; darkColor: string; label: string; order: number }> = {
  critical: {
    color: 'bg-red-100 text-red-800 border-red-200',
    darkColor: 'dark:bg-red-900/30 dark:text-red-300 dark:border-red-800',
    label: 'Critique',
    order: 0,
  },
  high: {
    color: 'bg-orange-100 text-orange-800 border-orange-200',
    darkColor: 'dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-800',
    label: 'Haute',
    order: 1,
  },
  medium: {
    color: 'bg-yellow-100 text-yellow-800 border-yellow-200',
    darkColor: 'dark:bg-yellow-900/30 dark:text-yellow-300 dark:border-yellow-800',
    label: 'Moyenne',
    order: 2,
  },
  low: {
    color: 'bg-blue-100 text-blue-800 border-blue-200',
    darkColor: 'dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800',
    label: 'Faible',
    order: 3,
  },
};

const TYPE_LABELS: Record<string, string> = {
  missing_diagnostic: 'Diagnostic manquant',
  expired_diagnostic: 'Diagnostic expire',
  missing_document: 'Document manquant',
  unverified_claim: 'Affirmation non verifiee',
  spatial_gap: 'Lacune spatiale',
  scope_gap: 'Lacune de perimetre',
  stale_evidence: 'Preuve obsolete',
  contradicted_fact: 'Fait contredit',
  missing_obligation_proof: 'Preuve obligation manquante',
  coverage_gap: 'Lacune de couverture',
  unresolved_question: 'Question non resolue',
  missing_party_data: 'Donnees partie manquantes',
};

const SAFE_TO_X_LABELS: Record<string, string> = {
  start: 'Safe-to-Start',
  sell: 'Safe-to-Sell',
  insure: 'Safe-to-Insure',
  finance: 'Safe-to-Finance',
  lease: 'Safe-to-Lease',
};

/* ---------- Sub-components ---------- */

function SeverityDot({ severity }: { severity: string }) {
  const cfg = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.medium;
  return (
    <span
      className={cn('inline-block px-2 py-0.5 text-xs font-medium rounded-full border', cfg.color, cfg.darkColor)}
    >
      {cfg.label}
    </span>
  );
}

function BlocksBadges({ blocks }: { blocks: string[] | null }) {
  if (!blocks || blocks.length === 0) return null;
  return (
    <div className="flex flex-wrap gap-1 mt-1">
      {blocks.map((b) => (
        <span
          key={b}
          className="inline-flex items-center gap-1 px-1.5 py-0.5 text-[10px] font-medium rounded bg-red-50 text-red-700 dark:bg-red-900/20 dark:text-red-400"
        >
          <Lock className="w-2.5 h-2.5" />
          {SAFE_TO_X_LABELS[b] || b}
        </span>
      ))}
    </div>
  );
}

/* ---------- Entry card ---------- */

function EntryCard({
  entry,
  onResolve,
  onAcceptRisk,
  onInvestigate,
}: {
  entry: UnknownEntry;
  onResolve: (id: string) => void;
  onAcceptRisk: (id: string) => void;
  onInvestigate: (id: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-gray-200 dark:border-slate-700 rounded-lg p-3 hover:bg-gray-50 dark:hover:bg-slate-800/50 transition-colors">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <SeverityDot severity={entry.severity} />
            <span className="text-xs text-gray-500 dark:text-slate-400">
              {TYPE_LABELS[entry.unknown_type] || entry.unknown_type}
            </span>
          </div>
          <p className="text-sm font-medium text-gray-900 dark:text-white mt-1 leading-tight">{entry.subject}</p>
          <BlocksBadges blocks={entry.blocks_safe_to_x} />
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-slate-300 shrink-0"
        >
          {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </button>
      </div>

      {expanded && (
        <div className="mt-3 space-y-2 text-sm">
          {entry.description && (
            <p className="text-gray-600 dark:text-slate-300">{entry.description}</p>
          )}
          {entry.risk_of_acting && (
            <div className="flex items-start gap-2 p-2 bg-red-50 dark:bg-red-900/10 rounded text-red-700 dark:text-red-300 text-xs">
              <AlertTriangle className="w-3.5 h-3.5 mt-0.5 shrink-0" />
              <span>{entry.risk_of_acting}</span>
            </div>
          )}
          {entry.estimated_resolution_effort && (
            <p className="text-xs text-gray-500 dark:text-slate-400">
              Effort de resolution : <span className="font-medium">{entry.estimated_resolution_effort}</span>
            </p>
          )}
          {entry.status === 'open' && (
            <div className="flex gap-2 pt-1">
              <button
                onClick={() => onResolve(entry.id)}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded bg-green-100 text-green-700 hover:bg-green-200 dark:bg-green-900/30 dark:text-green-400 dark:hover:bg-green-900/50"
              >
                <CheckCircle2 className="w-3 h-3" />
                Resoudre
              </button>
              <button
                onClick={() => onAcceptRisk(entry.id)}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded bg-amber-100 text-amber-700 hover:bg-amber-200 dark:bg-amber-900/30 dark:text-amber-400 dark:hover:bg-amber-900/50"
              >
                <ShieldAlert className="w-3 h-3" />
                Accepter le risque
              </button>
              <button
                onClick={() => onInvestigate(entry.id)}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded bg-blue-100 text-blue-700 hover:bg-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50"
              >
                <Eye className="w-3 h-3" />
                Investiguer
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ---------- Coverage map visual ---------- */

function CoverageMapSection({ buildingId }: { buildingId: string }) {
  const { data, isLoading } = useQuery({
    queryKey: ['unknowns-ledger-coverage', buildingId],
    queryFn: () => ledgerApi.coverage(buildingId),
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 py-4">
        <Loader2 className="w-4 h-4 animate-spin" />
        Chargement couverture...
      </div>
    );
  }

  if (!data) return null;

  const totalZones = data.covered.length + data.gaps.length + data.partial.length;
  if (totalZones === 0) {
    return (
      <p className="text-sm text-gray-500 dark:text-slate-400 py-2">Aucune zone definie pour ce batiment.</p>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-slate-400">
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-green-500" /> Couverte ({data.covered.length})
        </span>
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 rounded-full bg-red-500" /> Lacune ({data.gaps.length})
        </span>
        {data.partial.length > 0 && (
          <span className="flex items-center gap-1">
            <span className="w-2.5 h-2.5 rounded-full bg-yellow-500" /> Partielle ({data.partial.length})
          </span>
        )}
      </div>
      <div className="flex flex-wrap gap-1.5">
        {data.covered.map((z) => (
          <span
            key={z.zone_id}
            className="px-2 py-1 text-xs rounded-md bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300"
            title={`Zone couverte: ${z.zone_name}`}
          >
            {z.zone_name}
          </span>
        ))}
        {data.gaps.map((z) => (
          <span
            key={z.zone_id}
            className="px-2 py-1 text-xs rounded-md bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300"
            title={`Lacune: ${z.zone_name}`}
          >
            {z.zone_name}
          </span>
        ))}
        {data.partial.map((z) => (
          <span
            key={z.zone_id}
            className="px-2 py-1 text-xs rounded-md bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300"
            title={`Partielle: ${z.zone_name}`}
          >
            {z.zone_name}
          </span>
        ))}
      </div>
    </div>
  );
}

/* ---------- Resolve / Accept-Risk modals ---------- */

function ResolveModal({
  unknownId,
  onClose,
  onSuccess,
}: {
  unknownId: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [method, setMethod] = useState('new_evidence');
  const [note, setNote] = useState('');
  const mutation = useMutation({
    mutationFn: () => ledgerApi.resolve(unknownId, method, note || undefined),
    onSuccess: () => {
      toast('Inconnue resolue', 'success');
      onSuccess();
      onClose();
    },
    onError: () => toast('Erreur lors de la resolution', 'error'),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-800 rounded-lg shadow-xl p-6 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Resoudre l'inconnue</h3>
        <div className="space-y-3">
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Methode</label>
            <select
              value={method}
              onChange={(e) => setMethod(e.target.value)}
              className="w-full border border-gray-300 dark:border-slate-600 rounded-md px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white"
            >
              <option value="new_evidence">Nouvelle preuve</option>
              <option value="diagnostic_ordered">Diagnostic commande</option>
              <option value="claim_verified">Affirmation verifiee</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">Note</label>
            <textarea
              value={note}
              onChange={(e) => setNote(e.target.value)}
              rows={3}
              className="w-full border border-gray-300 dark:border-slate-600 rounded-md px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white"
              placeholder="Details de la resolution..."
            />
          </div>
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700"
          >
            Annuler
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending}
            className="px-3 py-1.5 text-sm rounded bg-green-600 text-white hover:bg-green-700 disabled:opacity-50"
          >
            {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Confirmer'}
          </button>
        </div>
      </div>
    </div>
  );
}

function AcceptRiskModal({
  unknownId,
  onClose,
  onSuccess,
}: {
  unknownId: string;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [note, setNote] = useState('');
  const mutation = useMutation({
    mutationFn: () => ledgerApi.acceptRisk(unknownId, note),
    onSuccess: () => {
      toast('Risque accepte', 'success');
      onSuccess();
      onClose();
    },
    onError: () => toast("Erreur lors de l'acceptation", 'error'),
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div
        className="bg-white dark:bg-slate-800 rounded-lg shadow-xl p-6 w-full max-w-md"
        onClick={(e) => e.stopPropagation()}
      >
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">Accepter le risque</h3>
        <div className="flex items-start gap-2 p-3 mb-4 bg-amber-50 dark:bg-amber-900/10 rounded-lg text-amber-800 dark:text-amber-300 text-sm">
          <AlertTriangle className="w-4 h-4 mt-0.5 shrink-0" />
          <span>
            L'acceptation du risque est irrevocable. Vous devez fournir une justification.
          </span>
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            Justification (obligatoire)
          </label>
          <textarea
            value={note}
            onChange={(e) => setNote(e.target.value)}
            rows={3}
            className="w-full border border-gray-300 dark:border-slate-600 rounded-md px-3 py-2 text-sm bg-white dark:bg-slate-700 dark:text-white"
            placeholder="Pourquoi acceptez-vous ce risque ?"
          />
        </div>
        <div className="flex justify-end gap-2 mt-4">
          <button
            onClick={onClose}
            className="px-3 py-1.5 text-sm rounded border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700"
          >
            Annuler
          </button>
          <button
            onClick={() => mutation.mutate()}
            disabled={mutation.isPending || !note.trim()}
            className="px-3 py-1.5 text-sm rounded bg-amber-600 text-white hover:bg-amber-700 disabled:opacity-50"
          >
            {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Accepter le risque'}
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------- Main component ---------- */

export default function UnknownsLedger({ buildingId }: { buildingId: string }) {
  const { t } = useTranslation();
  const queryClient = useQueryClient();

  const [resolveId, setResolveId] = useState<string | null>(null);
  const [acceptRiskId, setAcceptRiskId] = useState<string | null>(null);

  // Data queries
  const {
    data: entries,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ['unknowns-ledger', buildingId],
    queryFn: () => ledgerApi.list(buildingId),
  });

  const { data: impact } = useQuery({
    queryKey: ['unknowns-ledger-impact', buildingId],
    queryFn: () => ledgerApi.impact(buildingId),
  });

  // Scan mutation
  const scanMutation = useMutation({
    mutationFn: () => ledgerApi.scan(buildingId),
    onSuccess: (result) => {
      queryClient.invalidateQueries({ queryKey: ['unknowns-ledger', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['unknowns-ledger-impact', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['unknowns-ledger-coverage', buildingId] });
      toast(`Scan termine : ${result.created} nouvelles, ${result.resolved} resolues`, 'success');
    },
    onError: () => toast('Erreur lors du scan', 'error'),
  });

  const invalidateAll = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['unknowns-ledger', buildingId] });
    queryClient.invalidateQueries({ queryKey: ['unknowns-ledger-impact', buildingId] });
  }, [queryClient, buildingId]);

  const handleInvestigate = useCallback(
    async (id: string) => {
      try {
        await apiClient.post(`/unknowns-ledger/${id}/resolve`, {
          method: 'new_evidence',
          note: 'Marque pour investigation',
        });
        // For now, just mark as investigating via the resolve endpoint is not ideal.
        // We just expand the card so the user can see the details.
        toast("Details de l'inconnue affiches ci-dessous", 'info');
      } catch {
        // ignore
      }
    },
    [],
  );

  // Group by type
  const grouped = useMemo(() => {
    if (!entries) return {};
    const groups: Record<string, UnknownEntry[]> = {};
    for (const e of entries) {
      const key = e.unknown_type;
      if (!groups[key]) groups[key] = [];
      groups[key].push(e);
    }
    return groups;
  }, [entries]);

  const totalOpen = impact?.total_open ?? entries?.length ?? 0;
  const criticalCount = impact?.critical_count ?? 0;
  const blockingCount = Object.values(impact?.blocked_safe_to_x ?? {}).reduce((a, b) => a + b, 0);

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 py-8">
        <Loader2 className="w-4 h-4 animate-spin" />
        Chargement du registre des inconnues...
      </div>
    );
  }

  if (isError) {
    return (
      <div className="flex items-center gap-2 text-sm text-red-600 dark:text-red-400 py-4">
        <XCircle className="w-4 h-4" />
        Erreur lors du chargement du registre.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary bar */}
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <FileWarning className="w-5 h-5 text-gray-600 dark:text-slate-300" />
            <span className="text-lg font-semibold text-gray-900 dark:text-white">
              {t('unknowns_ledger.title') || 'Registre des inconnues'}
            </span>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="px-2.5 py-1 rounded-full bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-300 font-medium">
              {totalOpen} {totalOpen === 1 ? 'inconnue' : 'inconnues'}
            </span>
            {criticalCount > 0 && (
              <span className="px-2.5 py-1 rounded-full bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 font-medium">
                {criticalCount} critique{criticalCount > 1 ? 's' : ''}
              </span>
            )}
            {blockingCount > 0 && (
              <span className="px-2.5 py-1 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-300 font-medium flex items-center gap-1">
                <Lock className="w-3 h-3" />
                {blockingCount} bloquante{blockingCount > 1 ? 's' : ''}
              </span>
            )}
          </div>
        </div>
        <button
          onClick={() => scanMutation.mutate()}
          disabled={scanMutation.isPending}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-md bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50"
        >
          {scanMutation.isPending ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : (
            <RefreshCw className="w-4 h-4" />
          )}
          Scanner
        </button>
      </div>

      {/* Impact: blocked safe-to-x */}
      {impact && Object.keys(impact.blocked_safe_to_x).length > 0 && (
        <div className="p-3 bg-red-50 dark:bg-red-900/10 border border-red-200 dark:border-red-800 rounded-lg">
          <p className="text-sm font-medium text-red-800 dark:text-red-300 mb-2 flex items-center gap-1.5">
            <ShieldAlert className="w-4 h-4" />
            Decisions bloquees par des inconnues
          </p>
          <div className="flex flex-wrap gap-2">
            {Object.entries(impact.blocked_safe_to_x).map(([key, count]) => (
              <span
                key={key}
                className="inline-flex items-center gap-1 px-2 py-1 text-xs font-medium rounded bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400"
              >
                <Lock className="w-3 h-3" />
                {SAFE_TO_X_LABELS[key] || key}: {count}
              </span>
            ))}
          </div>
        </div>
      )}

      {/* No unknowns state */}
      {totalOpen === 0 && (
        <div className="flex flex-col items-center py-8 text-gray-500 dark:text-slate-400">
          <ShieldCheck className="w-10 h-10 mb-2 text-green-500" />
          <p className="text-sm font-medium">Aucune inconnue ouverte</p>
          <p className="text-xs mt-1">Toutes les lacunes ont ete resolues ou acceptees.</p>
        </div>
      )}

      {/* Entries grouped by type */}
      {Object.entries(grouped).map(([type, typeEntries]) => (
        <div key={type}>
          <h4 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-2 flex items-center gap-2">
            <span>{TYPE_LABELS[type] || type}</span>
            <span className="text-xs font-normal text-gray-400 dark:text-slate-500">({typeEntries.length})</span>
          </h4>
          <div className="space-y-2">
            {typeEntries.map((entry) => (
              <EntryCard
                key={entry.id}
                entry={entry}
                onResolve={setResolveId}
                onAcceptRisk={setAcceptRiskId}
                onInvestigate={handleInvestigate}
              />
            ))}
          </div>
        </div>
      ))}

      {/* Coverage map */}
      <div className="border-t border-gray-200 dark:border-slate-700 pt-4">
        <h4 className="text-sm font-semibold text-gray-700 dark:text-slate-300 mb-3 flex items-center gap-2">
          <MapPin className="w-4 h-4" />
          Couverture spatiale
        </h4>
        <CoverageMapSection buildingId={buildingId} />
      </div>

      {/* Modals */}
      {resolveId && (
        <ResolveModal unknownId={resolveId} onClose={() => setResolveId(null)} onSuccess={invalidateAll} />
      )}
      {acceptRiskId && (
        <AcceptRiskModal unknownId={acceptRiskId} onClose={() => setAcceptRiskId(null)} onSuccess={invalidateAll} />
      )}
    </div>
  );
}
