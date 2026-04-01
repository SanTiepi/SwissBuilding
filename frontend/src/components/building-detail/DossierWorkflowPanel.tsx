import { useState, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { cn, formatDateTime } from '@/utils/formatters';
import { dossierWorkflowApi, type DossierStatus, type DossierStepProgress } from '@/api/dossierWorkflow';
import { packExportApi } from '@/api/packExport';
import {
  FileStack,
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Package,
  Send,
  RotateCcw,
  ShieldCheck,
  CircleDot,
  Circle,
  Clock,
  X,
  ArrowRight,
  AlertOctagon,
  Info,
  Download,
  Share2,
  Copy,
  Check,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const WORK_TYPES = [
  { value: 'asbestos_removal', label: 'Desamiantage' },
  { value: 'pcb_removal', label: 'Elimination PCB' },
  { value: 'lead_removal', label: 'Elimination plomb' },
  { value: 'hap_removal', label: 'Elimination HAP' },
  { value: 'radon_mitigation', label: 'Assainissement radon' },
  { value: 'pfas_treatment', label: 'Traitement PFAS' },
  { value: 'full_renovation', label: 'Renovation complete' },
] as const;

type LifecycleStage = DossierStatus['lifecycle_stage'];

const VERDICT_CONFIG: Record<string, { label: string; color: string; bg: string; icon: typeof CheckCircle2 }> = {
  ready: {
    label: 'Pret',
    color: 'text-green-700 dark:text-green-300',
    bg: 'bg-green-100 dark:bg-green-900/30',
    icon: CheckCircle2,
  },
  partially_ready: {
    label: 'Partiellement pret',
    color: 'text-amber-700 dark:text-amber-300',
    bg: 'bg-amber-100 dark:bg-amber-900/30',
    icon: AlertTriangle,
  },
  not_ready: {
    label: 'Non pret',
    color: 'text-red-700 dark:text-red-300',
    bg: 'bg-red-100 dark:bg-red-900/30',
    icon: XCircle,
  },
  not_assessed: {
    label: 'Non evalue',
    color: 'text-gray-500 dark:text-slate-400',
    bg: 'bg-gray-100 dark:bg-slate-700',
    icon: Circle,
  },
};

/* ------------------------------------------------------------------ */
/*  Props                                                              */
/* ------------------------------------------------------------------ */

interface DossierWorkflowPanelProps {
  buildingId: string;
  onNavigateTab?: (tab: string) => void;
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

/** Horizontal progress stepper */
function ProgressTracker({ steps }: { steps: DossierStepProgress[] }) {
  return (
    <div className="flex items-center w-full py-3">
      {steps.map((step, i) => {
        const isDone = step.status === 'done';
        const isActive = step.status === 'in_progress';
        const isPending = step.status === 'pending';

        return (
          <div key={step.name} className="flex items-center flex-1 min-w-0 last:flex-none">
            {/* Connector line (before) */}
            {i > 0 && (
              <div
                className={cn(
                  'h-0.5 flex-1 min-w-3 transition-colors',
                  isDone || isActive ? 'bg-green-400 dark:bg-green-500' : 'bg-gray-200 dark:bg-slate-600',
                )}
              />
            )}

            {/* Step dot + label */}
            <div className="flex flex-col items-center gap-1 relative group">
              <div
                className={cn(
                  'w-3.5 h-3.5 rounded-full border-2 flex items-center justify-center transition-all',
                  isDone && 'bg-green-500 border-green-500',
                  isActive && 'bg-white dark:bg-slate-800 border-blue-500 ring-2 ring-blue-200 dark:ring-blue-800',
                  isPending && 'bg-white dark:bg-slate-800 border-gray-300 dark:border-slate-500',
                )}
              >
                {isDone && <CheckCircle2 className="w-2.5 h-2.5 text-white" />}
                {isActive && <CircleDot className="w-2 h-2 text-blue-500" />}
              </div>
              <span
                className={cn(
                  'text-[9px] leading-tight text-center max-w-[60px] truncate',
                  isDone && 'text-green-600 dark:text-green-400 font-medium',
                  isActive && 'text-blue-600 dark:text-blue-400 font-semibold',
                  isPending && 'text-gray-400 dark:text-slate-500',
                )}
                title={step.name}
              >
                {step.name}
              </span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

/** Readiness verdict hero badge */
function ReadinessVerdict({
  stage,
  blockerCount,
  onExpandBlockers,
  blockersExpanded,
}: {
  stage: LifecycleStage;
  blockerCount: number;
  onExpandBlockers: () => void;
  blockersExpanded: boolean;
}) {
  const verdictKey =
    stage === 'ready' ||
    stage === 'pack_generated' ||
    stage === 'submitted' ||
    stage === 'resubmitted' ||
    stage === 'acknowledged'
      ? 'ready'
      : stage === 'partially_ready'
        ? 'partially_ready'
        : stage === 'not_assessed'
          ? 'not_assessed'
          : 'not_ready';

  const config = VERDICT_CONFIG[verdictKey];
  const Icon = config.icon;

  return (
    <div className="flex items-center justify-between">
      <div
        className={cn(
          'inline-flex items-center gap-2 px-4 py-2.5 rounded-xl text-base font-bold',
          config.bg,
          config.color,
        )}
      >
        <Icon className="w-5 h-5" />
        {config.label}
      </div>
      {blockerCount > 0 && (
        <button
          onClick={onExpandBlockers}
          className="inline-flex items-center gap-1.5 text-xs font-medium text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 transition-colors"
        >
          <AlertTriangle className="w-3.5 h-3.5" />
          {blockerCount} blocage{blockerCount > 1 ? 's' : ''}
          {blockersExpanded ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
        </button>
      )}
    </div>
  );
}

/** Completeness progress bar */
function CompletenessSection({
  completeness,
  expanded,
  onToggle,
}: {
  completeness: DossierStatus['completeness'];
  expanded: boolean;
  onToggle: () => void;
}) {
  const { score_pct, documented, missing, expired } = completeness;
  const barColor = score_pct >= 80 ? 'bg-green-500' : score_pct >= 50 ? 'bg-amber-500' : 'bg-red-500';

  return (
    <div>
      <button onClick={onToggle} className="w-full text-left group">
        <div className="flex items-center justify-between mb-1.5">
          <span className="text-xs font-medium text-gray-600 dark:text-slate-400">Completude</span>
          <span className="text-xs text-gray-500 dark:text-slate-400">
            {documented.length} documente{documented.length > 1 ? 's' : ''}, {missing.length} manquant
            {missing.length > 1 ? 's' : ''}
            {expired.length > 0 && `, ${expired.length} perime${expired.length > 1 ? 's' : ''}`}
          </span>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2.5 bg-gray-200 dark:bg-slate-600 rounded-full overflow-hidden">
            <div
              className={cn('h-full rounded-full transition-all duration-500', barColor)}
              style={{ width: `${score_pct}%` }}
            />
          </div>
          <span className="text-xs font-semibold text-gray-700 dark:text-slate-200 w-10 text-right">{score_pct}%</span>
          {expanded ? (
            <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
          ) : (
            <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
          )}
        </div>
      </button>

      {expanded && (
        <div className="mt-3 grid grid-cols-2 gap-3">
          {/* Documented */}
          <div>
            <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Documente
            </p>
            {documented.length > 0 ? (
              <ul className="space-y-0.5">
                {documented.map((item, i) => (
                  <li key={i} className="flex items-center gap-1 text-[11px] text-gray-600 dark:text-slate-300">
                    <CheckCircle2 className="w-3 h-3 text-green-500 flex-shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[11px] text-gray-400 dark:text-slate-500 italic">Aucun</p>
            )}
          </div>
          {/* Missing + Expired */}
          <div>
            <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider mb-1">
              Manquant
            </p>
            {missing.length > 0 || expired.length > 0 ? (
              <ul className="space-y-0.5">
                {missing.map((item, i) => (
                  <li key={`m-${i}`} className="flex items-center gap-1 text-[11px] text-red-600 dark:text-red-400">
                    <XCircle className="w-3 h-3 flex-shrink-0" />
                    {item}
                  </li>
                ))}
                {expired.map((item, i) => (
                  <li key={`e-${i}`} className="flex items-center gap-1 text-[11px] text-amber-600 dark:text-amber-400">
                    <Clock className="w-3 h-3 flex-shrink-0" />
                    {item} (perime)
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[11px] text-green-600 dark:text-green-400">Tout est documente</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

/** PDF download + share buttons shown after pack generation */
function PackExportButtons({ buildingId }: { buildingId: string }) {
  const [downloading, setDownloading] = useState(false);
  const [sharing, setSharing] = useState(false);
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [shareExpiry, setShareExpiry] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleDownloadPdf = async () => {
    setDownloading(true);
    try {
      const blob = await packExportApi.generateAuthorityPdf(buildingId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `pack-autorite-${buildingId.slice(0, 8)}.pdf`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      // silent — button resets
    } finally {
      setDownloading(false);
    }
  };

  const handleShare = async () => {
    setSharing(true);
    try {
      const result = await packExportApi.createShareLink(buildingId, 'authority');
      setShareLink(result.share_url);
      setShareExpiry(result.expires_at);
    } catch {
      // silent
    } finally {
      setSharing(false);
    }
  };

  const handleCopy = async () => {
    if (!shareLink) return;
    try {
      await navigator.clipboard.writeText(shareLink);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
    }
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2">
        <button
          onClick={handleDownloadPdf}
          disabled={downloading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors"
        >
          {downloading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Download className="w-3.5 h-3.5" />}
          Telecharger PDF
        </button>
        <button
          onClick={handleShare}
          disabled={sharing}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-600 disabled:opacity-50 transition-colors"
        >
          {sharing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Share2 className="w-3.5 h-3.5" />}
          Partager
        </button>
      </div>
      {shareLink && (
        <div className="flex items-center gap-2 p-2.5 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg">
          <input
            type="text"
            value={shareLink}
            readOnly
            className="flex-1 text-xs text-blue-700 dark:text-blue-300 bg-transparent outline-none truncate font-mono"
          />
          <button
            onClick={handleCopy}
            className="flex-shrink-0 inline-flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium bg-blue-100 dark:bg-blue-800/50 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-800 transition-colors"
          >
            {copied ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
            {copied ? 'Copie' : 'Copier'}
          </button>
          {shareExpiry && (
            <span className="flex-shrink-0 text-[10px] text-blue-500 dark:text-blue-400">
              Expire le {new Date(shareExpiry).toLocaleDateString('fr-CH')}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

/** Pack status display and actions */
function PackSection({
  status,
  onGeneratePack,
  onSubmit,
  onResubmit,
  onAcknowledge,
  generating,
  submitting,
  resubmitting,
  acknowledging,
}: {
  status: DossierStatus;
  onGeneratePack: () => void;
  onSubmit: (reference?: string) => void;
  onResubmit: () => void;
  onAcknowledge: () => void;
  generating: boolean;
  submitting: boolean;
  resubmitting: boolean;
  acknowledging: boolean;
}) {
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const [showComplementModal, setShowComplementModal] = useState(false);
  const [submissionRef, setSubmissionRef] = useState('');
  const { pack, lifecycle_stage: stage } = status;

  const canGenerate = stage === 'ready' || stage === 'partially_ready';
  const isReady = stage === 'ready';

  // Not ready — show disabled button with reason
  if (stage === 'not_assessed' || stage === 'not_ready') {
    return (
      <div className="pt-3 border-t border-gray-100 dark:border-slate-700">
        <button
          disabled
          className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold text-gray-400 dark:text-slate-500 bg-gray-100 dark:bg-slate-700 rounded-lg cursor-not-allowed"
          title="Le dossier doit etre pret avant de generer le pack"
        >
          <Package className="w-4 h-4" />
          Generer le pack autorite
        </button>
        <p className="mt-1.5 text-[11px] text-gray-400 dark:text-slate-500 text-center">
          Resolvez les manques pour debloquer la generation
        </p>
      </div>
    );
  }

  // Ready / Partially ready — can generate
  if (canGenerate && pack.status !== 'generated') {
    return (
      <div className="pt-3 border-t border-gray-100 dark:border-slate-700">
        <button
          onClick={onGeneratePack}
          disabled={generating}
          className={cn(
            'w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold rounded-lg transition-colors',
            isReady
              ? 'text-white bg-green-600 hover:bg-green-700 disabled:opacity-50'
              : 'text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50',
          )}
        >
          {generating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin" />
              Generation en cours...
            </>
          ) : (
            <>
              <Package className="w-4 h-4" />
              Generer le pack autorite
            </>
          )}
        </button>
        {!isReady && (
          <p className="mt-1.5 text-[11px] text-amber-600 dark:text-amber-400 text-center">
            Le dossier est partiellement pret — le pack sera genere avec reserves
          </p>
        )}
      </div>
    );
  }

  // Pack generated — show submit
  if (stage === 'pack_generated' && pack.pack_id) {
    return (
      <div className="pt-3 border-t border-gray-100 dark:border-slate-700 space-y-3">
        <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <Package className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          <span className="text-sm font-medium text-blue-700 dark:text-blue-300">Pack genere</span>
          {pack.conformance && (
            <span className="ml-auto text-xs text-blue-600 dark:text-blue-400">
              Conformite: {typeof pack.conformance === 'object' ? 'OK' : pack.conformance}
            </span>
          )}
        </div>

        {/* PDF download + share */}
        <PackExportButtons buildingId={status.building_id} />

        {/* Submit button */}
        {!showSubmitModal ? (
          <button
            onClick={() => setShowSubmitModal(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 rounded-lg transition-colors"
          >
            <Send className="w-4 h-4" />
            Soumettre a l&apos;autorite
          </button>
        ) : (
          <div className="p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg space-y-3">
            <p className="text-xs font-medium text-gray-700 dark:text-slate-200">Reference de soumission (optionnel)</p>
            <input
              type="text"
              value={submissionRef}
              onChange={(e) => setSubmissionRef(e.target.value)}
              placeholder="Ex: REF-2026-001"
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-500 bg-white dark:bg-slate-700 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <div className="flex gap-2">
              <button
                onClick={() => {
                  onSubmit(submissionRef || undefined);
                  setShowSubmitModal(false);
                  setSubmissionRef('');
                }}
                disabled={submitting}
                className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded-lg transition-colors"
              >
                {submitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                Confirmer
              </button>
              <button
                onClick={() => {
                  setShowSubmitModal(false);
                  setSubmissionRef('');
                }}
                className="px-3 py-2 text-sm text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg transition-colors"
              >
                Annuler
              </button>
            </div>
          </div>
        )}
      </div>
    );
  }

  // Submitted
  if (stage === 'submitted') {
    return (
      <div className="pt-3 border-t border-gray-100 dark:border-slate-700 space-y-3">
        <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <Send className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          <div className="flex-1">
            <span className="text-sm font-medium text-blue-700 dark:text-blue-300">Soumis a l&apos;autorite</span>
            {pack.submitted_at && (
              <p className="text-[11px] text-blue-600 dark:text-blue-400">le {formatDateTime(pack.submitted_at)}</p>
            )}
          </div>
        </div>

        {/* PDF download + share */}
        <PackExportButtons buildingId={status.building_id} />

        {!showComplementModal ? (
          <button
            onClick={() => setShowComplementModal(true)}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-medium text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-900/20 hover:bg-amber-100 dark:hover:bg-amber-900/30 border border-amber-200 dark:border-amber-800 rounded-lg transition-colors"
          >
            <AlertTriangle className="w-4 h-4" />
            Signaler un complement demande
          </button>
        ) : (
          <ComplementModal
            packId={pack.pack_id || ''}
            buildingId={status.building_id}
            workType={status.work_type}
            onClose={() => setShowComplementModal(false)}
          />
        )}

        <button
          onClick={onAcknowledge}
          disabled={acknowledging}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded-lg transition-colors"
        >
          {acknowledging ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
          Enregistrer l&apos;accuse de reception
        </button>
      </div>
    );
  }

  // Complement requested
  if (stage === 'complement_requested') {
    return (
      <div className="pt-3 border-t border-gray-100 dark:border-slate-700 space-y-3">
        <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg border border-amber-200 dark:border-amber-800">
          <div className="flex items-center gap-2 mb-1.5">
            <AlertOctagon className="w-4 h-4 text-amber-600 dark:text-amber-400" />
            <span className="text-sm font-semibold text-amber-700 dark:text-amber-300">Complement demande</span>
          </div>
          {pack.complement_details && (
            <p className="text-xs text-amber-700 dark:text-amber-300 bg-amber-100/50 dark:bg-amber-900/30 rounded p-2">
              {pack.complement_details}
            </p>
          )}
        </div>
        <button
          onClick={onResubmit}
          disabled={resubmitting}
          className="w-full flex items-center justify-center gap-2 px-4 py-3 text-sm font-semibold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 rounded-lg transition-colors"
        >
          {resubmitting ? <Loader2 className="w-4 h-4 animate-spin" /> : <RotateCcw className="w-4 h-4" />}
          Corriger et re-soumettre
        </button>
      </div>
    );
  }

  // Resubmitted
  if (stage === 'resubmitted') {
    return (
      <div className="pt-3 border-t border-gray-100 dark:border-slate-700 space-y-3">
        <div className="flex items-center gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
          <RotateCcw className="w-4 h-4 text-blue-600 dark:text-blue-400" />
          <span className="text-sm font-medium text-blue-700 dark:text-blue-300">
            Re-soumis — en attente de reponse
          </span>
        </div>
        <button
          onClick={onAcknowledge}
          disabled={acknowledging}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 text-sm font-semibold text-white bg-green-600 hover:bg-green-700 disabled:opacity-50 rounded-lg transition-colors"
        >
          {acknowledging ? <Loader2 className="w-4 h-4 animate-spin" /> : <ShieldCheck className="w-4 h-4" />}
          Enregistrer l&apos;accuse de reception
        </button>
      </div>
    );
  }

  // Acknowledged
  if (stage === 'acknowledged') {
    return (
      <div className="pt-3 border-t border-gray-100 dark:border-slate-700">
        <div className="flex items-center gap-2 p-4 bg-green-50 dark:bg-green-900/20 rounded-lg border border-green-200 dark:border-green-800">
          <ShieldCheck className="w-5 h-5 text-green-600 dark:text-green-400" />
          <div>
            <p className="text-sm font-semibold text-green-700 dark:text-green-300">Dossier accepte</p>
            {pack.submitted_at && (
              <p className="text-[11px] text-green-600 dark:text-green-400">
                Soumis le {formatDateTime(pack.submitted_at)}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  return null;
}

/** Inline complement reporting form */
function ComplementModal({
  packId,
  buildingId,
  workType,
  onClose,
}: {
  packId: string;
  buildingId: string;
  workType: string;
  onClose: () => void;
}) {
  const [details, setDetails] = useState('');
  const queryClient = useQueryClient();

  const mutation = useMutation({
    mutationFn: () =>
      dossierWorkflowApi.handleComplement(buildingId, workType, {
        pack_id: packId,
        complement_details: details,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dossier-workflow', buildingId] });
      onClose();
    },
  });

  return (
    <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg space-y-3">
      <div className="flex items-center justify-between">
        <p className="text-xs font-semibold text-amber-700 dark:text-amber-300">Signaler un complement</p>
        <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300">
          <X className="w-3.5 h-3.5" />
        </button>
      </div>
      <textarea
        value={details}
        onChange={(e) => setDetails(e.target.value)}
        placeholder="Decrivez les informations complementaires demandees par l'autorite..."
        rows={3}
        className="w-full px-3 py-2 rounded-lg border border-amber-300 dark:border-amber-700 bg-white dark:bg-slate-700 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-amber-500 focus:border-amber-500 resize-none"
      />
      <div className="flex gap-2">
        <button
          onClick={() => mutation.mutate()}
          disabled={!details.trim() || mutation.isPending}
          className="flex-1 flex items-center justify-center gap-2 px-3 py-2 text-sm font-semibold text-white bg-amber-600 hover:bg-amber-700 disabled:opacity-50 rounded-lg transition-colors"
        >
          {mutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <AlertTriangle className="w-4 h-4" />}
          Confirmer
        </button>
        <button
          onClick={onClose}
          className="px-3 py-2 text-sm text-gray-600 dark:text-slate-300 hover:bg-gray-100 dark:hover:bg-slate-600 rounded-lg transition-colors"
        >
          Annuler
        </button>
      </div>
      {mutation.isError && (
        <p className="text-xs text-red-600 dark:text-red-400">Erreur lors de l&apos;enregistrement.</p>
      )}
    </div>
  );
}

/** Next action banner */
function NextActionBanner({
  nextAction,
  stage,
  blockersRef,
}: {
  nextAction: DossierStatus['next_action'];
  stage: LifecycleStage;
  blockersRef: React.RefObject<HTMLDivElement | null>;
}) {
  if (stage === 'acknowledged') return null;

  const handleClick = () => {
    if (stage === 'not_ready' || stage === 'not_assessed') {
      // Scroll to blockers section
      blockersRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  };

  return (
    <button
      onClick={handleClick}
      className="w-full flex items-center gap-3 p-3 bg-blue-50 dark:bg-blue-900/15 border border-blue-100 dark:border-blue-800/50 rounded-lg hover:bg-blue-100 dark:hover:bg-blue-900/25 transition-colors text-left group"
    >
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-800/50 flex items-center justify-center">
        <ArrowRight className="w-4 h-4 text-blue-600 dark:text-blue-400 group-hover:translate-x-0.5 transition-transform" />
      </div>
      <div className="min-w-0 flex-1">
        <p className="text-xs font-semibold text-blue-700 dark:text-blue-300">{nextAction.title}</p>
        <p className="text-[11px] text-blue-600 dark:text-blue-400 mt-0.5 truncate">{nextAction.description}</p>
      </div>
    </button>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export default function DossierWorkflowPanel({ buildingId, onNavigateTab }: DossierWorkflowPanelProps) {
  const queryClient = useQueryClient();
  const [workType, setWorkType] = useState('asbestos_removal');
  const [expanded, setExpanded] = useState(true);
  const [blockersExpanded, setBlockersExpanded] = useState(false);
  const [completenessExpanded, setCompletenessExpanded] = useState(false);
  const blockersRef = useRef<HTMLDivElement>(null);

  // Fetch dossier status
  const {
    data: status,
    isLoading,
    error,
  } = useQuery({
    queryKey: ['dossier-workflow', buildingId, workType],
    queryFn: () => dossierWorkflowApi.getStatus(buildingId, workType),
    staleTime: 30_000,
    retry: 1,
  });

  // Mutations
  const generateMutation = useMutation({
    mutationFn: () => dossierWorkflowApi.generatePack(buildingId, workType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dossier-workflow', buildingId] });
    },
  });

  const submitMutation = useMutation({
    mutationFn: (reference?: string) =>
      dossierWorkflowApi.submit(buildingId, workType, {
        pack_id: status?.pack.pack_id || '',
        submission_reference: reference,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dossier-workflow', buildingId] });
    },
  });

  const resubmitMutation = useMutation({
    mutationFn: () => dossierWorkflowApi.resubmit(buildingId, workType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dossier-workflow', buildingId] });
    },
  });

  const acknowledgeMutation = useMutation({
    mutationFn: () =>
      dossierWorkflowApi.acknowledge(buildingId, workType, {
        pack_id: status?.pack.pack_id || '',
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['dossier-workflow', buildingId] });
    },
  });

  // Derive collapsed quick status
  const quickStage = status?.lifecycle_stage ?? 'not_assessed';
  const quickLabel =
    quickStage === 'acknowledged'
      ? 'Dossier accepte'
      : quickStage === 'submitted' || quickStage === 'resubmitted'
        ? 'En attente de reponse'
        : quickStage === 'complement_requested'
          ? 'Complement demande'
          : quickStage === 'pack_generated'
            ? 'Pack genere'
            : quickStage === 'ready'
              ? 'Pret a soumettre'
              : quickStage === 'partially_ready'
                ? 'Partiellement pret'
                : quickStage === 'not_ready'
                  ? 'Actions requises'
                  : 'Non evalue';

  const quickDot =
    quickStage === 'acknowledged'
      ? 'bg-green-500'
      : quickStage === 'submitted' || quickStage === 'resubmitted' || quickStage === 'pack_generated'
        ? 'bg-blue-500'
        : quickStage === 'complement_requested'
          ? 'bg-amber-500'
          : quickStage === 'ready'
            ? 'bg-green-500'
            : quickStage === 'partially_ready'
              ? 'bg-amber-500'
              : quickStage === 'not_ready'
                ? 'bg-red-500'
                : 'bg-gray-400';

  // Border highlight based on stage
  const borderClass =
    quickStage === 'acknowledged'
      ? 'border-green-300 dark:border-green-700'
      : quickStage === 'ready' || quickStage === 'pack_generated'
        ? 'border-green-200 dark:border-green-800'
        : quickStage === 'submitted' || quickStage === 'resubmitted'
          ? 'border-blue-200 dark:border-blue-800'
          : quickStage === 'complement_requested'
            ? 'border-amber-200 dark:border-amber-700'
            : 'border-gray-200 dark:border-slate-600';

  return (
    <div
      className={cn('bg-white dark:bg-slate-800 rounded-xl border-2 overflow-hidden transition-colors', borderClass)}
      data-testid="dossier-workflow-panel"
    >
      {/* Collapsed header — always visible */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-5 py-4 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-slate-700/50 transition-colors"
      >
        <div className="flex items-center gap-3">
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-red-100 dark:bg-red-900/40 flex items-center justify-center">
            <FileStack className="w-5 h-5 text-red-600 dark:text-red-400" />
          </div>
          <div className="text-left">
            <p className="text-sm font-bold text-gray-900 dark:text-white">Dossier pre-travaux</p>
            <p className="text-xs text-gray-500 dark:text-slate-400">{quickLabel}</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {status?.progress && (
            <span className="text-xs text-gray-400 dark:text-slate-500">
              {status.progress.steps_completed}/{status.progress.steps_total}
            </span>
          )}
          <span className={cn('w-2.5 h-2.5 rounded-full', quickDot)} />
          {expanded ? (
            <ChevronDown className="w-5 h-5 text-gray-400" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-400" />
          )}
        </div>
      </button>

      {/* Expanded content */}
      {expanded && (
        <div className="px-5 pb-5 space-y-4 border-t border-gray-100 dark:border-slate-700">
          {/* Work type selector */}
          <div className="pt-4">
            <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1.5">
              Type de travaux
            </label>
            <select
              value={workType}
              onChange={(e) => setWorkType(e.target.value)}
              className="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-slate-500 bg-white dark:bg-slate-700 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-red-500"
            >
              {WORK_TYPES.map((wt) => (
                <option key={wt.value} value={wt.value}>
                  {wt.label}
                </option>
              ))}
            </select>
          </div>

          {/* Loading */}
          {isLoading && (
            <div className="flex items-center justify-center py-8 text-gray-400 dark:text-slate-500">
              <Loader2 className="w-5 h-5 animate-spin mr-2" />
              <span className="text-sm">Evaluation en cours...</span>
            </div>
          )}

          {/* Error */}
          {error && !isLoading && (
            <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-sm text-red-600 dark:text-red-400">
              <AlertTriangle className="w-4 h-4 flex-shrink-0" />
              <span>Impossible de charger le statut du dossier.</span>
            </div>
          )}

          {/* Status content */}
          {status && !isLoading && (
            <>
              {/* Progress tracker */}
              {status.progress.steps.length > 0 && <ProgressTracker steps={status.progress.steps} />}

              {/* Readiness verdict */}
              <ReadinessVerdict
                stage={status.lifecycle_stage}
                blockerCount={status.readiness.blockers.length}
                onExpandBlockers={() => setBlockersExpanded(!blockersExpanded)}
                blockersExpanded={blockersExpanded}
              />

              {/* Completeness bar */}
              <CompletenessSection
                completeness={status.completeness}
                expanded={completenessExpanded}
                onToggle={() => setCompletenessExpanded(!completenessExpanded)}
              />

              {/* Blockers & high-priority actions */}
              <div ref={blockersRef}>
                {blockersExpanded && status.readiness.blockers.length > 0 && (
                  <div className="space-y-2">
                    <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                      Blocages
                    </p>
                    {status.readiness.blockers.slice(0, 5).map((blocker: any, i: number) => {
                      const label = blocker.label || blocker.description || String(blocker);
                      return (
                        <div
                          key={i}
                          className="flex items-center gap-2 rounded-lg bg-red-50 dark:bg-red-900/15 border border-red-100 dark:border-red-800/50 px-3 py-2"
                        >
                          <XCircle className="w-3.5 h-3.5 text-red-500 flex-shrink-0" />
                          <span className="text-xs text-red-700 dark:text-red-300 flex-1">{label}</span>
                          {onNavigateTab && (
                            <button
                              onClick={() => {
                                const tab = blockerToTab(label);
                                if (tab) onNavigateTab(tab);
                              }}
                              className="flex-shrink-0 inline-flex items-center gap-0.5 text-[10px] font-medium text-red-600 dark:text-red-400 hover:text-red-800 dark:hover:text-red-300 transition-colors"
                            >
                              Resoudre
                              <ChevronRight className="w-3 h-3" />
                            </button>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>

              {/* High-priority actions */}
              {status.actions.high_priority.length > 0 && (
                <div className="space-y-2">
                  <p className="text-[10px] font-medium text-gray-500 dark:text-slate-400 uppercase tracking-wider">
                    Actions prioritaires ({status.actions.total_open} ouvertes)
                  </p>
                  {status.actions.high_priority.slice(0, 5).map((action: any, i: number) => {
                    const title = action.title || action.description || String(action);
                    const priority = action.priority || 'medium';
                    return (
                      <div
                        key={i}
                        className="flex items-center gap-2 rounded-lg bg-white dark:bg-slate-800 border border-gray-200 dark:border-slate-600 px-3 py-2"
                      >
                        <span
                          className={cn(
                            'w-2 h-2 rounded-full flex-shrink-0',
                            priority === 'critical'
                              ? 'bg-red-500'
                              : priority === 'high'
                                ? 'bg-orange-500'
                                : 'bg-amber-500',
                          )}
                        />
                        <span className="text-xs text-gray-700 dark:text-slate-200 flex-1 truncate">{title}</span>
                        {onNavigateTab && (
                          <button
                            onClick={() => {
                              const tab = actionToTab(action.source_type);
                              if (tab) onNavigateTab(tab);
                            }}
                            className="flex-shrink-0 inline-flex items-center gap-0.5 text-[10px] font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
                          >
                            Resoudre
                            <ChevronRight className="w-3 h-3" />
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              {/* Unknowns summary */}
              {status.unknowns.count > 0 && (
                <div className="flex items-center gap-2 p-2.5 bg-amber-50 dark:bg-amber-900/15 border border-amber-100 dark:border-amber-800/50 rounded-lg">
                  <Info className="w-3.5 h-3.5 text-amber-500 flex-shrink-0" />
                  <span className="text-xs text-amber-700 dark:text-amber-300">
                    {status.unknowns.count} inconnue{status.unknowns.count > 1 ? 's' : ''} detectee
                    {status.unknowns.count > 1 ? 's' : ''}
                    {status.unknowns.critical.length > 0 &&
                      ` dont ${status.unknowns.critical.length} critique${status.unknowns.critical.length > 1 ? 's' : ''}`}
                  </span>
                </div>
              )}

              {/* Pack status + action buttons */}
              <PackSection
                status={status}
                onGeneratePack={() => generateMutation.mutate()}
                onSubmit={(ref) => submitMutation.mutate(ref)}
                onResubmit={() => resubmitMutation.mutate()}
                onAcknowledge={() => acknowledgeMutation.mutate()}
                generating={generateMutation.isPending}
                submitting={submitMutation.isPending}
                resubmitting={resubmitMutation.isPending}
                acknowledging={acknowledgeMutation.isPending}
              />

              {/* Mutation errors */}
              {(generateMutation.isError ||
                submitMutation.isError ||
                resubmitMutation.isError ||
                acknowledgeMutation.isError) && (
                <div className="flex items-center gap-2 p-2.5 bg-red-50 dark:bg-red-900/20 rounded-lg text-xs text-red-600 dark:text-red-400">
                  <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
                  Une erreur est survenue. Veuillez reessayer.
                </div>
              )}

              {/* Next action nudge */}
              {status.next_action && status.lifecycle_stage !== 'acknowledged' && (
                <NextActionBanner
                  nextAction={status.next_action}
                  stage={status.lifecycle_stage}
                  blockersRef={blockersRef}
                />
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Helpers (shared with DossierJourney)                               */
/* ------------------------------------------------------------------ */

function blockerToTab(label: string): string | null {
  const lower = label.toLowerCase();
  if (lower.includes('diagnostic') || lower.includes('sample') || lower.includes('pollutant')) return 'diagnostics';
  if (lower.includes('document') || lower.includes('evidence') || lower.includes('report') || lower.includes('proof'))
    return 'documents';
  if (lower.includes('ownership') || lower.includes('owner')) return 'ownership';
  if (lower.includes('lease') || lower.includes('tenant')) return 'leases';
  if (lower.includes('contract')) return 'contracts';
  if (lower.includes('procedure') || lower.includes('compliance') || lower.includes('regulatory')) return 'procedures';
  return null;
}

function actionToTab(sourceType: string | undefined): string | null {
  if (!sourceType) return null;
  if (sourceType === 'diagnostic' || sourceType === 'risk') return 'diagnostics';
  if (sourceType === 'document') return 'documents';
  if (sourceType === 'compliance') return 'procedures';
  return null;
}
