import { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { complianceArtefactsApi } from '@/api/complianceArtefacts';
import type { ComplianceSummaryResponse } from '@/api/complianceArtefacts';
import { buildingsApi } from '@/api/buildings';
import { useAuth } from '@/hooks/useAuth';
import { useTranslation } from '@/i18n';
import { formatDateTime, cn } from '@/utils/formatters';
import type { Building, ComplianceArtefact, ComplianceArtefactCreate, ComplianceRequiredArtefact } from '@/types';
import {
  Shield,
  Loader2,
  AlertTriangle,
  FileCheck,
  ChevronDown,
  Plus,
  Eye,
  CheckCircle2,
  Clock,
  Send,
  FileText,
  X,
  Trash2,
  ArrowUpCircle,
  BookOpen,
  Link2,
  Calendar,
  Hash,
  Building2,
  Scale,
} from 'lucide-react';

// ---------- Constants ----------

const ARTEFACT_TYPES = [
  'suva_notification',
  'post_remediation_report',
  'disposal_record',
  'authority_submission',
  'compliance_certificate',
  'canton_notification',
  'air_measurement_report',
  'other',
] as const;

const STATUS_CONFIG: Record<string, { icon: typeof Clock; color: string; bgColor: string }> = {
  draft: { icon: FileText, color: 'text-gray-500 dark:text-slate-400', bgColor: 'bg-gray-100 dark:bg-slate-700' },
  submitted: { icon: Send, color: 'text-blue-500', bgColor: 'bg-blue-100 dark:bg-blue-900/30' },
  acknowledged: {
    icon: CheckCircle2,
    color: 'text-green-500',
    bgColor: 'bg-green-100 dark:bg-green-900/30',
  },
  rejected: {
    icon: AlertTriangle,
    color: 'text-red-500',
    bgColor: 'bg-red-100 dark:bg-red-900/30',
  },
};

type SortField = 'created_at' | 'status' | 'artefact_type';
type SortDir = 'asc' | 'desc';

// ---------- Status Badge ----------

function StatusBadge({ status, t }: { status: string; t: (key: string) => string }) {
  const config = STATUS_CONFIG[status] ?? STATUS_CONFIG.draft;
  const Icon = config.icon;
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 px-2 py-1 rounded-full text-xs font-medium',
        config.bgColor,
        config.color,
      )}
    >
      <Icon className="w-3 h-3" />
      {t(`compliance_artefacts.status_${status}`) || status}
    </span>
  );
}

// ---------- Type Badge ----------

function TypeBadge({ artefactType, t }: { artefactType: string; t: (key: string) => string }) {
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300">
      {t(`compliance_artefacts.type_${artefactType}`) || artefactType.replace(/_/g, ' ')}
    </span>
  );
}

// ---------- Summary Cards ----------

function SummaryCards({ summary, t }: { summary: ComplianceSummaryResponse; t: (key: string) => string }) {
  const acknowledgedCount = summary.by_status['acknowledged'] ?? 0;
  const acknowledgedRate = summary.total > 0 ? Math.round((acknowledgedCount / summary.total) * 100) : 0;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4">
        <div className="flex items-center gap-2 mb-1">
          <FileCheck className="w-4 h-4 text-gray-400" />
          <span className="text-xs text-gray-500 dark:text-slate-400">
            {t('compliance_artefacts.total') || 'Total'}
          </span>
        </div>
        <p className="text-2xl font-bold text-gray-900 dark:text-white">{summary.total}</p>
      </div>
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4">
        <div className="flex items-center gap-2 mb-1">
          <Clock className="w-4 h-4 text-amber-400" />
          <span className="text-xs text-gray-500 dark:text-slate-400">
            {t('compliance_artefacts.pending') || 'Pending'}
          </span>
        </div>
        <p className="text-2xl font-bold text-amber-600 dark:text-amber-400">{summary.pending_submissions}</p>
      </div>
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4">
        <div className="flex items-center gap-2 mb-1">
          <CheckCircle2 className="w-4 h-4 text-green-400" />
          <span className="text-xs text-gray-500 dark:text-slate-400">
            {t('compliance_artefacts.acknowledged_rate') || 'Acknowledged Rate'}
          </span>
        </div>
        <p className="text-2xl font-bold text-green-600 dark:text-green-400">{acknowledgedRate}%</p>
      </div>
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-4">
        <div className="flex items-center gap-2 mb-1">
          <AlertTriangle className="w-4 h-4 text-red-400" />
          <span className="text-xs text-gray-500 dark:text-slate-400">
            {t('compliance_artefacts.expired') || 'Expired'}
          </span>
        </div>
        <p className="text-2xl font-bold text-red-600 dark:text-red-400">{summary.expired}</p>
      </div>
    </div>
  );
}

// ---------- Required Artefacts Alert ----------

function RequiredArtefactsAlert({
  required,
  t,
}: {
  required: ComplianceRequiredArtefact[];
  t: (key: string) => string;
}) {
  if (required.length === 0) return null;
  return (
    <div className="bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-xl p-4">
      <div className="flex items-center gap-2 mb-2">
        <AlertTriangle className="w-4 h-4 text-amber-500" />
        <span className="text-sm font-medium text-amber-700 dark:text-amber-300">
          {t('compliance_artefacts.required_missing') || 'Required artefacts missing'}
        </span>
      </div>
      <ul className="space-y-2">
        {required.map((r, i) => (
          <li key={i} className="text-sm text-amber-600 dark:text-amber-400 flex items-start gap-2">
            <Scale className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
            <div>
              <span className="font-medium">
                {t(`compliance_artefacts.type_${r.artefact_type}`) || r.artefact_type.replace(/_/g, ' ')}
              </span>
              {' — '}
              {r.reason}
              {r.legal_basis && (
                <span className="ml-1 text-xs text-amber-500 dark:text-amber-500">({r.legal_basis})</span>
              )}
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}

// ---------- Create Modal ----------

function CreateArtefactModal({
  buildingId,
  onClose,
  t,
}: {
  buildingId: string;
  onClose: () => void;
  t: (key: string) => string;
}) {
  const queryClient = useQueryClient();
  const [formData, setFormData] = useState<ComplianceArtefactCreate>({
    artefact_type: 'authority_submission',
    title: '',
    description: '',
    authority_name: '',
    authority_type: '',
    legal_basis: '',
    reference_number: '',
  });

  const createMutation = useMutation({
    mutationFn: (data: ComplianceArtefactCreate) => complianceArtefactsApi.create(buildingId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-artefacts', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['compliance-summary', buildingId] });
      onClose();
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title.trim()) return;
    const cleaned: ComplianceArtefactCreate = {
      artefact_type: formData.artefact_type,
      title: formData.title.trim(),
    };
    if (formData.description?.trim()) cleaned.description = formData.description.trim();
    if (formData.authority_name?.trim()) cleaned.authority_name = formData.authority_name.trim();
    if (formData.authority_type?.trim()) cleaned.authority_type = formData.authority_type.trim();
    if (formData.legal_basis?.trim()) cleaned.legal_basis = formData.legal_basis.trim();
    if (formData.reference_number?.trim()) cleaned.reference_number = formData.reference_number.trim();
    createMutation.mutate(cleaned);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-xl bg-white dark:bg-slate-800 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 z-10 bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('compliance_artefacts.create') || 'Create Artefact'}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-slate-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('compliance_artefacts.artefact_type') || 'Type'} *
            </label>
            <div className="relative">
              <select
                value={formData.artefact_type}
                onChange={(e) => setFormData((p) => ({ ...p, artefact_type: e.target.value }))}
                className={cn(
                  'w-full appearance-none rounded-lg border px-3 py-2 pr-10 text-sm',
                  'bg-white dark:bg-slate-900 text-gray-700 dark:text-slate-200',
                  'border-gray-300 dark:border-slate-600',
                  'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
                )}
              >
                {ARTEFACT_TYPES.map((type) => (
                  <option key={type} value={type}>
                    {t(`compliance_artefacts.type_${type}`) || type.replace(/_/g, ' ')}
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
            </div>
          </div>

          {/* Title */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('compliance_artefacts.title_field') || 'Title'} *
            </label>
            <input
              type="text"
              value={formData.title}
              onChange={(e) => setFormData((p) => ({ ...p, title: e.target.value }))}
              required
              className={cn(
                'w-full rounded-lg border px-3 py-2 text-sm',
                'bg-white dark:bg-slate-900 text-gray-700 dark:text-slate-200',
                'border-gray-300 dark:border-slate-600',
                'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
              )}
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('compliance_artefacts.description') || 'Description'}
            </label>
            <textarea
              value={formData.description ?? ''}
              onChange={(e) => setFormData((p) => ({ ...p, description: e.target.value }))}
              rows={3}
              className={cn(
                'w-full rounded-lg border px-3 py-2 text-sm',
                'bg-white dark:bg-slate-900 text-gray-700 dark:text-slate-200',
                'border-gray-300 dark:border-slate-600',
                'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
              )}
            />
          </div>

          {/* Authority name */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('compliance_artefacts.authority_name') || 'Authority Name'}
            </label>
            <input
              type="text"
              value={formData.authority_name ?? ''}
              onChange={(e) => setFormData((p) => ({ ...p, authority_name: e.target.value }))}
              placeholder="SUVA, Canton VD, etc."
              className={cn(
                'w-full rounded-lg border px-3 py-2 text-sm',
                'bg-white dark:bg-slate-900 text-gray-700 dark:text-slate-200',
                'border-gray-300 dark:border-slate-600',
                'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
              )}
            />
          </div>

          {/* Authority type */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('compliance_artefacts.authority_type') || 'Authority Type'}
            </label>
            <input
              type="text"
              value={formData.authority_type ?? ''}
              onChange={(e) => setFormData((p) => ({ ...p, authority_type: e.target.value }))}
              placeholder="cantonal, federal, municipal"
              className={cn(
                'w-full rounded-lg border px-3 py-2 text-sm',
                'bg-white dark:bg-slate-900 text-gray-700 dark:text-slate-200',
                'border-gray-300 dark:border-slate-600',
                'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
              )}
            />
          </div>

          {/* Legal basis */}
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('compliance_artefacts.legal_basis') || 'Legal Basis'}
            </label>
            <input
              type="text"
              value={formData.legal_basis ?? ''}
              onChange={(e) => setFormData((p) => ({ ...p, legal_basis: e.target.value }))}
              placeholder="OTConst Art. 82-86"
              className={cn(
                'w-full rounded-lg border px-3 py-2 text-sm',
                'bg-white dark:bg-slate-900 text-gray-700 dark:text-slate-200',
                'border-gray-300 dark:border-slate-600',
                'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
              )}
            />
          </div>

          {/* Error */}
          {createMutation.isError && (
            <div className="text-sm text-red-600 dark:text-red-400">{t('app.error') || 'An error occurred'}</div>
          )}

          {/* Footer */}
          <div className="flex justify-end gap-3 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
            >
              {t('compliance_artefacts.cancel') || 'Cancel'}
            </button>
            <button
              type="submit"
              disabled={createMutation.isPending || !formData.title.trim()}
              className={cn(
                'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                'bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed',
              )}
            >
              {createMutation.isPending ? <Loader2 className="w-4 h-4 animate-spin" /> : <Plus className="w-4 h-4" />}
              {t('compliance_artefacts.create') || 'Create'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------- Acknowledge Modal ----------

function AcknowledgeModal({
  artefact,
  buildingId,
  onClose,
  t,
}: {
  artefact: ComplianceArtefact;
  buildingId: string;
  onClose: () => void;
  t: (key: string) => string;
}) {
  const queryClient = useQueryClient();
  const [refNumber, setRefNumber] = useState('');
  const acknowledgeMutation = useMutation({
    mutationFn: () => complianceArtefactsApi.acknowledge(buildingId, artefact.id, refNumber.trim() || undefined),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-artefacts', buildingId] });
      queryClient.invalidateQueries({ queryKey: ['compliance-summary', buildingId] });
      onClose();
    },
  });

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-md rounded-xl bg-white dark:bg-slate-800 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="border-b border-gray-200 dark:border-slate-700 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('compliance_artefacts.record_acknowledgment') || 'Record Acknowledgment'}
          </h2>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-slate-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6 space-y-4">
          <p className="text-sm text-gray-600 dark:text-slate-300">
            {t('compliance_artefacts.acknowledge_confirm') ||
              'Confirm that this artefact has been acknowledged by the authority.'}
          </p>
          <div className="bg-gray-50 dark:bg-slate-900/50 rounded-lg p-3">
            <p className="text-sm font-medium text-gray-900 dark:text-white">{artefact.title}</p>
            {artefact.authority_name && (
              <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{artefact.authority_name}</p>
            )}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">
              {t('compliance_artefacts.reference_number') || 'Authority Reference Number'}
            </label>
            <input
              type="text"
              value={refNumber}
              onChange={(e) => setRefNumber(e.target.value)}
              placeholder="REF-2026-001"
              className={cn(
                'w-full rounded-lg border px-3 py-2 text-sm',
                'bg-white dark:bg-slate-900 text-gray-700 dark:text-slate-200',
                'border-gray-300 dark:border-slate-600',
                'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
              )}
            />
          </div>
          {acknowledgeMutation.isError && (
            <div className="text-sm text-red-600 dark:text-red-400">{t('app.error') || 'An error occurred'}</div>
          )}
        </div>
        <div className="border-t border-gray-200 dark:border-slate-700 px-6 py-3 flex justify-end gap-3">
          <button
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
          >
            {t('compliance_artefacts.cancel') || 'Cancel'}
          </button>
          <button
            onClick={() => acknowledgeMutation.mutate()}
            disabled={acknowledgeMutation.isPending}
            className={cn(
              'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
              'bg-green-600 text-white hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed',
            )}
          >
            {acknowledgeMutation.isPending ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <CheckCircle2 className="w-4 h-4" />
            )}
            {t('compliance_artefacts.confirm_acknowledge') || 'Confirm'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ---------- Detail Panel ----------

function ArtefactDetailPanel({
  artefact,
  onClose,
  onSubmit,
  onAcknowledge,
  onDelete,
  t,
}: {
  artefact: ComplianceArtefact;
  onClose: () => void;
  onSubmit: () => void;
  onAcknowledge: () => void;
  onDelete: () => void;
  t: (key: string) => string;
}) {
  // Build timeline entries from artefact data
  const timeline = useMemo(() => {
    const entries: { date: string; label: string; icon: typeof Clock; color: string }[] = [];
    entries.push({
      date: artefact.created_at,
      label: t('compliance_artefacts.event_created') || 'Created as draft',
      icon: FileText,
      color: 'text-gray-400',
    });
    if (artefact.submitted_at) {
      entries.push({
        date: artefact.submitted_at,
        label: t('compliance_artefacts.event_submitted') || 'Submitted to authority',
        icon: Send,
        color: 'text-blue-500',
      });
    }
    if (artefact.acknowledged_at) {
      entries.push({
        date: artefact.acknowledged_at,
        label: t('compliance_artefacts.event_acknowledged') || 'Acknowledged by authority',
        icon: CheckCircle2,
        color: 'text-green-500',
      });
    }
    return entries;
  }, [artefact, t]);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
      <div
        className="w-full max-w-2xl max-h-[85vh] overflow-y-auto rounded-xl bg-white dark:bg-slate-800 shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white dark:bg-slate-800 border-b border-gray-200 dark:border-slate-700 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3 min-w-0">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white truncate">{artefact.title}</h2>
            <StatusBadge status={artefact.status} t={t} />
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-gray-100 dark:hover:bg-slate-700 text-gray-500 dark:text-slate-400"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Metadata grid */}
          <div className="grid grid-cols-2 gap-4">
            <div className="flex items-start gap-2">
              <FileCheck className="w-4 h-4 text-gray-400 mt-0.5" />
              <div>
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  {t('compliance_artefacts.artefact_type') || 'Type'}
                </p>
                <TypeBadge artefactType={artefact.artefact_type} t={t} />
              </div>
            </div>
            {artefact.authority_name && (
              <div className="flex items-start gap-2">
                <Building2 className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {t('compliance_artefacts.authority_name') || 'Authority'}
                  </p>
                  <p className="text-sm text-gray-900 dark:text-white">{artefact.authority_name}</p>
                  {artefact.authority_type && (
                    <p className="text-xs text-gray-500 dark:text-slate-400">{artefact.authority_type}</p>
                  )}
                </div>
              </div>
            )}
            {artefact.reference_number && (
              <div className="flex items-start gap-2">
                <Hash className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {t('compliance_artefacts.reference_number') || 'Reference'}
                  </p>
                  <p className="text-sm font-mono text-gray-900 dark:text-white">{artefact.reference_number}</p>
                </div>
              </div>
            )}
            {artefact.legal_basis && (
              <div className="flex items-start gap-2">
                <Scale className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {t('compliance_artefacts.legal_basis') || 'Legal Basis'}
                  </p>
                  <p className="text-sm text-gray-900 dark:text-white">{artefact.legal_basis}</p>
                </div>
              </div>
            )}
            {artefact.expires_at && (
              <div className="flex items-start gap-2">
                <Calendar className="w-4 h-4 text-gray-400 mt-0.5" />
                <div>
                  <p className="text-xs text-gray-500 dark:text-slate-400">
                    {t('compliance_artefacts.expires_at') || 'Expires'}
                  </p>
                  <p className="text-sm text-gray-900 dark:text-white">{formatDateTime(artefact.expires_at)}</p>
                </div>
              </div>
            )}
          </div>

          {/* Description */}
          {artefact.description && (
            <div>
              <p className="text-xs text-gray-500 dark:text-slate-400 mb-1">
                {t('compliance_artefacts.description') || 'Description'}
              </p>
              <p className="text-sm text-gray-700 dark:text-slate-300 whitespace-pre-wrap">{artefact.description}</p>
            </div>
          )}

          {/* Linked evidence */}
          {(artefact.diagnostic_id || artefact.intervention_id || artefact.document_id) && (
            <div>
              <p className="text-xs text-gray-500 dark:text-slate-400 mb-2">
                {t('compliance_artefacts.linked_evidence') || 'Linked Evidence'}
              </p>
              <div className="space-y-1.5">
                {artefact.diagnostic_id && (
                  <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300 bg-gray-50 dark:bg-slate-900/50 rounded-lg px-3 py-2">
                    <Link2 className="w-3.5 h-3.5 text-gray-400" />
                    <span>{t('compliance_artefacts.linked_diagnostic') || 'Diagnostic'}</span>
                    <span className="font-mono text-xs text-gray-500 dark:text-slate-400">
                      {artefact.diagnostic_id.slice(0, 8)}...
                    </span>
                  </div>
                )}
                {artefact.intervention_id && (
                  <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300 bg-gray-50 dark:bg-slate-900/50 rounded-lg px-3 py-2">
                    <Link2 className="w-3.5 h-3.5 text-gray-400" />
                    <span>{t('compliance_artefacts.linked_intervention') || 'Intervention'}</span>
                    <span className="font-mono text-xs text-gray-500 dark:text-slate-400">
                      {artefact.intervention_id.slice(0, 8)}...
                    </span>
                  </div>
                )}
                {artefact.document_id && (
                  <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300 bg-gray-50 dark:bg-slate-900/50 rounded-lg px-3 py-2">
                    <Link2 className="w-3.5 h-3.5 text-gray-400" />
                    <span>{t('compliance_artefacts.linked_document') || 'Document'}</span>
                    <span className="font-mono text-xs text-gray-500 dark:text-slate-400">
                      {artefact.document_id.slice(0, 8)}...
                    </span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Status Timeline */}
          <div>
            <p className="text-xs text-gray-500 dark:text-slate-400 mb-3">
              {t('compliance_artefacts.submission_history') || 'Submission History'}
            </p>
            <div className="relative pl-6 space-y-4">
              <div className="absolute left-2.5 top-1 bottom-1 w-px bg-gray-200 dark:bg-slate-700" />
              {timeline.map((entry, idx) => {
                const EntryIcon = entry.icon;
                return (
                  <div key={idx} className="relative flex items-start gap-3">
                    <div
                      className={cn(
                        'absolute -left-6 w-5 h-5 rounded-full bg-white dark:bg-slate-800 flex items-center justify-center',
                        'ring-2 ring-gray-200 dark:ring-slate-700',
                      )}
                    >
                      <EntryIcon className={cn('w-3 h-3', entry.color)} />
                    </div>
                    <div>
                      <p className="text-sm text-gray-900 dark:text-white">{entry.label}</p>
                      <p className="text-xs text-gray-500 dark:text-slate-400">{formatDateTime(entry.date)}</p>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Footer actions */}
        <div className="sticky bottom-0 bg-white dark:bg-slate-800 border-t border-gray-200 dark:border-slate-700 px-6 py-3 flex items-center justify-between">
          <button
            onClick={onDelete}
            className="inline-flex items-center gap-1.5 px-3 py-2 text-sm font-medium text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
          >
            <Trash2 className="w-4 h-4" />
            {t('compliance_artefacts.delete') || 'Delete'}
          </button>
          <div className="flex items-center gap-2">
            {artefact.status === 'draft' && (
              <button
                onClick={onSubmit}
                className={cn(
                  'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  'bg-blue-600 text-white hover:bg-blue-700',
                )}
              >
                <Send className="w-4 h-4" />
                {t('compliance_artefacts.submit_to_authority') || 'Submit'}
              </button>
            )}
            {artefact.status === 'submitted' && (
              <button
                onClick={onAcknowledge}
                className={cn(
                  'inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors',
                  'bg-green-600 text-white hover:bg-green-700',
                )}
              >
                <CheckCircle2 className="w-4 h-4" />
                {t('compliance_artefacts.record_acknowledgment') || 'Record Acknowledgment'}
              </button>
            )}
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm font-medium rounded-lg bg-gray-100 dark:bg-slate-700 text-gray-700 dark:text-slate-200 hover:bg-gray-200 dark:hover:bg-slate-600 transition-colors"
            >
              {t('compliance_artefacts.close') || 'Close'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

// ---------- Main Page ----------

export default function ComplianceArtefacts() {
  const { t } = useTranslation();
  useAuth();
  const queryClient = useQueryClient();

  const [selectedBuildingId, setSelectedBuildingId] = useState<string>('');
  const [showCreate, setShowCreate] = useState(false);
  const [detailArtefact, setDetailArtefact] = useState<ComplianceArtefact | null>(null);
  const [acknowledgeArtefact, setAcknowledgeArtefact] = useState<ComplianceArtefact | null>(null);
  const [filterStatus, setFilterStatus] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('');
  const [sortField, setSortField] = useState<SortField>('created_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  // Buildings
  const { data: buildingsData, isLoading: buildingsLoading } = useQuery({
    queryKey: ['buildings-for-compliance'],
    queryFn: () => buildingsApi.list({ size: 200 }),
  });
  const buildings: Building[] = buildingsData?.items ?? [];

  // Artefacts
  const {
    data: artefactsData,
    isLoading: artefactsLoading,
    isError: artefactsError,
  } = useQuery({
    queryKey: ['compliance-artefacts', selectedBuildingId, filterStatus, filterType],
    queryFn: () =>
      complianceArtefactsApi.list(selectedBuildingId, {
        size: 100,
        status: filterStatus || undefined,
        artefact_type: filterType || undefined,
      }),
    enabled: !!selectedBuildingId,
  });
  const artefacts: ComplianceArtefact[] = useMemo(() => artefactsData?.items ?? [], [artefactsData]);

  // Summary
  const { data: summary } = useQuery({
    queryKey: ['compliance-summary', selectedBuildingId],
    queryFn: () => complianceArtefactsApi.summary(selectedBuildingId),
    enabled: !!selectedBuildingId,
  });

  // Required artefacts
  const { data: required } = useQuery({
    queryKey: ['compliance-required', selectedBuildingId],
    queryFn: () => complianceArtefactsApi.required(selectedBuildingId),
    enabled: !!selectedBuildingId,
  });

  // Submit mutation
  const submitMutation = useMutation({
    mutationFn: (artefactId: string) => complianceArtefactsApi.submit(selectedBuildingId, artefactId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-artefacts', selectedBuildingId] });
      queryClient.invalidateQueries({ queryKey: ['compliance-summary', selectedBuildingId] });
      setDetailArtefact(null);
    },
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (artefactId: string) => complianceArtefactsApi.delete(selectedBuildingId, artefactId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['compliance-artefacts', selectedBuildingId] });
      queryClient.invalidateQueries({ queryKey: ['compliance-summary', selectedBuildingId] });
      setDetailArtefact(null);
    },
  });

  // Client-side sorting
  const sortedArtefacts = useMemo(() => {
    const sorted = [...artefacts];
    sorted.sort((a, b) => {
      let cmp = 0;
      if (sortField === 'created_at') {
        cmp = new Date(a.created_at).getTime() - new Date(b.created_at).getTime();
      } else if (sortField === 'status') {
        cmp = a.status.localeCompare(b.status);
      } else if (sortField === 'artefact_type') {
        cmp = a.artefact_type.localeCompare(b.artefact_type);
      }
      return sortDir === 'desc' ? -cmp : cmp;
    });
    return sorted;
  }, [artefacts, sortField, sortDir]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('desc');
    }
  };

  const isLoading = buildingsLoading || (!!selectedBuildingId && artefactsLoading);

  const renderSortIndicator = (field: SortField) =>
    sortField === field ? <span className="ml-1 text-xs">{sortDir === 'asc' ? '\u25B2' : '\u25BC'}</span> : null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('compliance_artefacts.page_title') || 'Compliance Artefacts'}
          </h1>
          <p className="text-sm text-gray-500 dark:text-slate-400 mt-1">
            {t('compliance_artefacts.page_description') || 'Manage authority submissions and compliance documents'}
          </p>
        </div>
        <Shield className="w-8 h-8 text-gray-300 dark:text-slate-600" />
      </div>

      {/* Building selector + create button */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="relative flex-1 min-w-[240px] max-w-md">
          <select
            value={selectedBuildingId}
            onChange={(e) => {
              setSelectedBuildingId(e.target.value);
              setDetailArtefact(null);
            }}
            className={cn(
              'w-full appearance-none rounded-lg border px-4 py-2.5 pr-10 text-sm',
              'bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200',
              'border-gray-300 dark:border-slate-600',
              'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
            )}
          >
            <option value="">{t('compliance_artefacts.select_building') || 'Select a building...'}</option>
            {buildings.map((b) => (
              <option key={b.id} value={b.id}>
                {b.address}, {b.postal_code} {b.city}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
        <button
          onClick={() => setShowCreate(true)}
          disabled={!selectedBuildingId}
          className={cn(
            'inline-flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
            'bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed',
          )}
        >
          <Plus className="w-4 h-4" />
          {t('compliance_artefacts.create') || 'Create Artefact'}
        </button>
      </div>

      {/* Summary cards */}
      {summary && <SummaryCards summary={summary} t={t} />}

      {/* Required artefacts alert */}
      {required && required.length > 0 && <RequiredArtefactsAlert required={required} t={t} />}

      {/* Filters */}
      {selectedBuildingId && !isLoading && (
        <div className="flex flex-wrap items-center gap-3">
          <div className="relative">
            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
              className={cn(
                'appearance-none rounded-lg border px-3 py-2 pr-8 text-sm',
                'bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200',
                'border-gray-300 dark:border-slate-600',
                'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
              )}
            >
              <option value="">{t('compliance_artefacts.all_statuses') || 'All statuses'}</option>
              {['draft', 'submitted', 'acknowledged', 'rejected'].map((s) => (
                <option key={s} value={s}>
                  {t(`compliance_artefacts.status_${s}`) || s}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
          </div>
          <div className="relative">
            <select
              value={filterType}
              onChange={(e) => setFilterType(e.target.value)}
              className={cn(
                'appearance-none rounded-lg border px-3 py-2 pr-8 text-sm',
                'bg-white dark:bg-slate-800 text-gray-700 dark:text-slate-200',
                'border-gray-300 dark:border-slate-600',
                'focus:outline-none focus:ring-2 focus:ring-red-500 focus:border-red-500',
              )}
            >
              <option value="">{t('compliance_artefacts.all_types') || 'All types'}</option>
              {ARTEFACT_TYPES.map((type) => (
                <option key={type} value={type}>
                  {t(`compliance_artefacts.type_${type}`) || type.replace(/_/g, ' ')}
                </option>
              ))}
            </select>
            <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400 pointer-events-none" />
          </div>
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-gray-400" />
        </div>
      )}

      {/* Error */}
      {artefactsError && (
        <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
          <AlertTriangle className="w-8 h-8 text-red-400 mx-auto mb-2" />
          <p className="text-red-700 dark:text-red-300">{t('app.error') || 'Error loading data'}</p>
        </div>
      )}

      {/* No building selected */}
      {!selectedBuildingId && !isLoading && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-12 text-center">
          <BookOpen className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400">
            {t('compliance_artefacts.select_building_hint') || 'Select a building to manage compliance artefacts'}
          </p>
        </div>
      )}

      {/* Empty */}
      {selectedBuildingId && !isLoading && !artefactsError && sortedArtefacts.length === 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-12 text-center">
          <FileCheck className="w-12 h-12 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-gray-500 dark:text-slate-400">
            {t('compliance_artefacts.empty') || 'No compliance artefacts yet'}
          </p>
        </div>
      )}

      {/* Artefacts table */}
      {!isLoading && sortedArtefacts.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200 dark:border-slate-700 bg-gray-50 dark:bg-slate-900/50">
                  <th
                    className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400 cursor-pointer select-none"
                    onClick={() => toggleSort('status')}
                  >
                    {t('compliance_artefacts.status_col') || 'Status'}
                    {renderSortIndicator('status')}
                  </th>
                  <th
                    className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400 cursor-pointer select-none"
                    onClick={() => toggleSort('artefact_type')}
                  >
                    {t('compliance_artefacts.artefact_type') || 'Type'}
                    {renderSortIndicator('artefact_type')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('compliance_artefacts.title_field') || 'Title'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('compliance_artefacts.authority_name') || 'Authority'}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('compliance_artefacts.reference_number') || 'Reference'}
                  </th>
                  <th
                    className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400 cursor-pointer select-none"
                    onClick={() => toggleSort('created_at')}
                  >
                    {t('compliance_artefacts.date') || 'Date'}
                    {renderSortIndicator('created_at')}
                  </th>
                  <th className="text-left px-4 py-3 font-medium text-gray-500 dark:text-slate-400">
                    {t('compliance_artefacts.actions') || 'Actions'}
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
                {sortedArtefacts.map((artefact) => (
                  <tr
                    key={artefact.id}
                    className="hover:bg-gray-50 dark:hover:bg-slate-700/50 cursor-pointer transition-colors"
                    onClick={() => setDetailArtefact(artefact)}
                  >
                    <td className="px-4 py-3">
                      <StatusBadge status={artefact.status} t={t} />
                    </td>
                    <td className="px-4 py-3">
                      <TypeBadge artefactType={artefact.artefact_type} t={t} />
                    </td>
                    <td className="px-4 py-3 text-gray-900 dark:text-white font-medium max-w-[200px] truncate">
                      {artefact.title}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-slate-300">{artefact.authority_name || '—'}</td>
                    <td className="px-4 py-3 text-gray-500 dark:text-slate-400 font-mono text-xs">
                      {artefact.reference_number || '—'}
                    </td>
                    <td className="px-4 py-3 text-gray-500 dark:text-slate-400">
                      {formatDateTime(artefact.submitted_at ?? artefact.created_at)}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
                        <button
                          onClick={() => setDetailArtefact(artefact)}
                          className="inline-flex items-center gap-1 text-xs text-red-600 hover:text-red-700 dark:text-red-400 dark:hover:text-red-300 font-medium"
                          title={t('compliance_artefacts.view') || 'View'}
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>
                        {artefact.status === 'draft' && (
                          <button
                            onClick={() => submitMutation.mutate(artefact.id)}
                            disabled={submitMutation.isPending}
                            className="inline-flex items-center gap-1 text-xs text-blue-600 hover:text-blue-700 dark:text-blue-400 dark:hover:text-blue-300 font-medium"
                            title={t('compliance_artefacts.submit_to_authority') || 'Submit'}
                          >
                            <ArrowUpCircle className="w-3.5 h-3.5" />
                          </button>
                        )}
                        {artefact.status === 'submitted' && (
                          <button
                            onClick={() => setAcknowledgeArtefact(artefact)}
                            className="inline-flex items-center gap-1 text-xs text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-300 font-medium"
                            title={t('compliance_artefacts.record_acknowledgment') || 'Acknowledge'}
                          >
                            <CheckCircle2 className="w-3.5 h-3.5" />
                          </button>
                        )}
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modals */}
      {showCreate && selectedBuildingId && (
        <CreateArtefactModal buildingId={selectedBuildingId} onClose={() => setShowCreate(false)} t={t} />
      )}

      {detailArtefact && (
        <ArtefactDetailPanel
          artefact={detailArtefact}
          onClose={() => setDetailArtefact(null)}
          onSubmit={() => submitMutation.mutate(detailArtefact.id)}
          onAcknowledge={() => {
            setAcknowledgeArtefact(detailArtefact);
            setDetailArtefact(null);
          }}
          onDelete={() => {
            if (window.confirm(t('compliance_artefacts.delete_confirm') || 'Delete this artefact?')) {
              deleteMutation.mutate(detailArtefact.id);
            }
          }}
          t={t}
        />
      )}

      {acknowledgeArtefact && (
        <AcknowledgeModal
          artefact={acknowledgeArtefact}
          buildingId={selectedBuildingId}
          onClose={() => setAcknowledgeArtefact(null)}
          t={t}
        />
      )}
    </div>
  );
}
