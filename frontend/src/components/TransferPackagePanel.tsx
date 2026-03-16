import { useState, useEffect, useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import {
  transferPackageApi,
  TRANSFER_SECTIONS,
  getSectionData,
  type TransferPackageResponse,
  type TransferSection,
} from '@/api/transferPackage';
import { formatDate, formatDateTime, cn } from '@/utils/formatters';
import { toast } from '@/store/toastStore';
import {
  Package,
  Loader2,
  Download,
  CheckSquare,
  Square,
  AlertTriangle,
  Eye,
  ChevronDown,
  ChevronUp,
  FileJson,
  FileText,
  Clock,
  User,
  Mail,
  Target,
} from 'lucide-react';

interface TransferPackagePanelProps {
  buildingId: string;
}

type ExportFormat = 'json' | 'pdf';

type TransferPurpose = 'sale' | 'audit' | 'renovation' | 'insurance' | 'other';

interface RecipientInfo {
  name: string;
  email: string;
  purpose: TransferPurpose;
}

interface PackageHistoryEntry {
  id: string;
  generated_at: string;
  format: ExportFormat;
  sections: TransferSection[];
  size_bytes: number;
  recipient?: RecipientInfo;
  data: TransferPackageResponse;
}

const SECTION_ICONS: Record<TransferSection, string> = {
  passport: 'ID',
  diagnostics: 'Dx',
  documents: 'Doc',
  interventions: 'Iv',
  actions: 'Ac',
  evidence: 'Ev',
  contradictions: 'Ct',
  unknowns: 'Un',
  snapshots: 'Sn',
  completeness: 'Cp',
  readiness: 'Rd',
};

function sectionItemCount(data: Record<string, unknown> | Record<string, unknown>[] | null): string {
  if (data == null) return '--';
  if (Array.isArray(data)) return String(data.length);
  for (const key of ['total', 'count', 'total_open', 'total_count']) {
    if (typeof data[key] === 'number') return String(data[key]);
  }
  return String(Object.keys(data).length) + ' keys';
}

function estimateSize(data: unknown): number {
  return new Blob([JSON.stringify(data)]).size;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

const PROGRESS_STEPS = ['transfer.progress_building', 'transfer.progress_sections', 'transfer.progress_packaging'];

export function TransferPackagePanel({ buildingId }: TransferPackagePanelProps) {
  const { t } = useTranslation();
  const [selected, setSelected] = useState<Set<TransferSection>>(new Set(TRANSFER_SECTIONS));
  const [result, setResult] = useState<TransferPackageResponse | null>(null);
  const [exportFormat, setExportFormat] = useState<ExportFormat>('json');
  const [showRecipient, setShowRecipient] = useState(false);
  const [recipient, setRecipient] = useState<RecipientInfo>({ name: '', email: '', purpose: 'other' });
  const [history, setHistory] = useState<PackageHistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const [progressStep, setProgressStep] = useState(0);
  const [showPreview, setShowPreview] = useState(false);

  const generateMutation = useMutation({
    mutationFn: () => {
      setProgressStep(0);
      const sections = selected.size === TRANSFER_SECTIONS.length ? undefined : [...selected];
      return transferPackageApi.generate(buildingId, sections);
    },
    onSuccess: (data) => {
      setResult(data);
      toast(t('transfer.success') || 'Package generated successfully', 'success');

      const entry: PackageHistoryEntry = {
        id: data.package_id,
        generated_at: data.generated_at,
        format: exportFormat,
        sections: [...selected],
        size_bytes: estimateSize(data),
        recipient: recipient.name || recipient.email ? { ...recipient } : undefined,
        data,
      };
      setHistory((prev) => [entry, ...prev]);
    },
    onError: (err: any) => {
      toast(err?.response?.data?.detail || err?.message || t('transfer.error') || 'An error occurred');
    },
  });

  const isPending = generateMutation.isPending;
  useEffect(() => {
    if (!isPending) return;
    const timer = setInterval(() => {
      setProgressStep((prev) => Math.min(prev + 1, PROGRESS_STEPS.length - 1));
    }, 800);
    return () => clearInterval(timer);
  }, [isPending]);

  const toggleSection = useCallback((section: TransferSection) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  }, []);

  const toggleAll = useCallback(() => {
    setSelected((prev) => (prev.size === TRANSFER_SECTIONS.length ? new Set() : new Set(TRANSFER_SECTIONS)));
  }, []);

  const handleDownload = useCallback(
    (data: TransferPackageResponse, format: ExportFormat) => {
      if (format === 'json') {
        const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transfer-package-${buildingId}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      } else {
        // PDF: generate a text-based representation as a downloadable file
        const lines = [
          `Transfer Package - ${buildingId}`,
          `Generated: ${data.generated_at}`,
          `Schema version: ${data.schema_version}`,
          '',
          '--- Building Summary ---',
          JSON.stringify(data.building_summary, null, 2),
          '',
        ];
        for (const section of TRANSFER_SECTIONS) {
          const sectionData = getSectionData(data, section);
          if (sectionData != null) {
            lines.push(`--- ${section.charAt(0).toUpperCase() + section.slice(1)} ---`);
            lines.push(JSON.stringify(sectionData, null, 2));
            lines.push('');
          }
        }
        const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `transfer-package-${buildingId}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    },
    [buildingId],
  );

  const purposes: TransferPurpose[] = ['sale', 'audit', 'renovation', 'insurance', 'other'];

  return (
    <div className="space-y-6">
      {/* Main panel */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 space-y-5">
        {/* Header */}
        <div className="flex items-center justify-between flex-wrap gap-2">
          <div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Package className="w-5 h-5 text-red-600" />
              {t('transfer.title') || 'Transfer Package'}
            </h3>
            <p className="text-sm text-gray-500 dark:text-slate-400 mt-0.5">
              {t('transfer.subtitle') || 'Assemble and export the building transfer dossier'}
            </p>
          </div>
          <div className="flex items-center gap-2">
            {/* Format selector */}
            <div className="flex items-center rounded-lg border border-gray-300 dark:border-slate-600 overflow-hidden">
              <button
                onClick={() => setExportFormat('json')}
                className={cn(
                  'inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium transition-colors',
                  exportFormat === 'json'
                    ? 'bg-red-600 text-white'
                    : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700',
                )}
              >
                <FileJson className="w-3 h-3" />
                {t('transfer.format_json') || 'JSON'}
              </button>
              <button
                onClick={() => setExportFormat('pdf')}
                className={cn(
                  'inline-flex items-center gap-1 px-2.5 py-1.5 text-xs font-medium transition-colors border-l border-gray-300 dark:border-slate-600',
                  exportFormat === 'pdf'
                    ? 'bg-red-600 text-white'
                    : 'bg-white dark:bg-slate-800 text-gray-600 dark:text-slate-300 hover:bg-gray-50 dark:hover:bg-slate-700',
                )}
              >
                <FileText className="w-3 h-3" />
                {t('transfer.format_pdf') || 'PDF'}
              </button>
            </div>
            <button
              onClick={() => generateMutation.mutate()}
              disabled={generateMutation.isPending || selected.size === 0}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 transition-colors"
            >
              {generateMutation.isPending ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Package className="w-3.5 h-3.5" />
              )}
              {generateMutation.isPending
                ? t('transfer.generating') || 'Generating...'
                : t('transfer.generate') || 'Generate'}
            </button>
          </div>
        </div>

        {/* Progress indicator */}
        {generateMutation.isPending && (
          <div className="space-y-2">
            <div className="flex items-center gap-3">
              {PROGRESS_STEPS.map((step, i) => (
                <div key={step} className="flex items-center gap-1.5">
                  <div
                    className={cn(
                      'w-2 h-2 rounded-full transition-colors',
                      i <= progressStep ? 'bg-red-600' : 'bg-gray-300 dark:bg-slate-600',
                    )}
                  />
                  <span
                    className={cn(
                      'text-xs transition-colors',
                      i <= progressStep ? 'text-gray-700 dark:text-slate-200' : 'text-gray-400 dark:text-slate-500',
                    )}
                  >
                    {t(step) || step}
                  </span>
                </div>
              ))}
            </div>
            <div className="w-full bg-gray-200 dark:bg-slate-700 rounded-full h-1.5">
              <div
                className="bg-red-600 h-1.5 rounded-full transition-all duration-500"
                style={{ width: `${((progressStep + 1) / PROGRESS_STEPS.length) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Section selector with descriptions */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-500 dark:text-slate-400">
              {t('transfer.select_sections') || 'Select sections to include'}
            </p>
            <span className="text-xs text-gray-500 dark:text-slate-400">
              {selected.size}/{TRANSFER_SECTIONS.length} {t('transfer.sections_selected') || 'sections selected'}
            </span>
          </div>

          {/* Toggle all */}
          <button
            onClick={toggleAll}
            className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            {selected.size === TRANSFER_SECTIONS.length ? (
              <CheckSquare className="w-4 h-4 text-red-600" />
            ) : (
              <Square className="w-4 h-4" />
            )}
            {t('transfer.all_sections') || 'All sections'}
          </button>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {TRANSFER_SECTIONS.map((section) => (
              <button
                key={section}
                onClick={() => toggleSection(section)}
                className={cn(
                  'flex items-start gap-2.5 px-3 py-2.5 rounded-lg text-left transition-colors',
                  selected.has(section)
                    ? 'bg-red-50 dark:bg-red-900/20 ring-1 ring-red-200 dark:ring-red-800'
                    : 'bg-gray-50 dark:bg-slate-700/50 hover:bg-gray-100 dark:hover:bg-slate-700',
                )}
              >
                <div className="mt-0.5">
                  {selected.has(section) ? (
                    <CheckSquare className="w-4 h-4 text-red-600 shrink-0" />
                  ) : (
                    <Square className="w-4 h-4 text-gray-400 dark:text-slate-500 shrink-0" />
                  )}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2">
                    <span
                      className={cn(
                        'inline-flex items-center justify-center w-6 h-6 rounded text-[10px] font-bold',
                        selected.has(section)
                          ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
                          : 'bg-gray-200 text-gray-500 dark:bg-slate-600 dark:text-slate-400',
                      )}
                    >
                      {SECTION_ICONS[section]}
                    </span>
                    <span
                      className={cn(
                        'text-sm font-medium',
                        selected.has(section) ? 'text-red-800 dark:text-red-300' : 'text-gray-600 dark:text-slate-400',
                      )}
                    >
                      {t(`transfer.section_${section}`) || section}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 dark:text-slate-400 mt-0.5 line-clamp-2">
                    {t(`transfer.desc_${section}`) || ''}
                  </p>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Recipient form (collapsible) */}
        <div className="border-t border-gray-200 dark:border-slate-700 pt-4">
          <button
            onClick={() => setShowRecipient(!showRecipient)}
            className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white transition-colors"
          >
            <User className="w-4 h-4" />
            {showRecipient
              ? t('transfer.collapse_recipient') || 'Hide recipient form'
              : t('transfer.expand_recipient') || 'Add a recipient'}
            {showRecipient ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {showRecipient && (
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1">
                  <span className="flex items-center gap-1">
                    <User className="w-3 h-3" />
                    {t('transfer.recipient_name') || 'Recipient name'}
                  </span>
                </label>
                <input
                  type="text"
                  value={recipient.name}
                  onChange={(e) => setRecipient((r) => ({ ...r, name: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="Jean Dupont"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1">
                  <span className="flex items-center gap-1">
                    <Mail className="w-3 h-3" />
                    {t('transfer.recipient_email') || 'Recipient email'}
                  </span>
                </label>
                <input
                  type="email"
                  value={recipient.email}
                  onChange={(e) => setRecipient((r) => ({ ...r, email: e.target.value }))}
                  className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-slate-500 focus:ring-2 focus:ring-red-500 focus:border-transparent"
                  placeholder="jean@example.com"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-600 dark:text-slate-400 mb-1">
                  <span className="flex items-center gap-1">
                    <Target className="w-3 h-3" />
                    {t('transfer.recipient_purpose') || 'Transfer purpose'}
                  </span>
                </label>
                <select
                  value={recipient.purpose}
                  onChange={(e) => setRecipient((r) => ({ ...r, purpose: e.target.value as TransferPurpose }))}
                  className="w-full rounded-lg border border-gray-300 dark:border-slate-600 bg-white dark:bg-slate-700 px-3 py-1.5 text-sm text-gray-900 dark:text-white focus:ring-2 focus:ring-red-500 focus:border-transparent"
                >
                  {purposes.map((p) => (
                    <option key={p} value={p}>
                      {t(`transfer.purpose_${p}`) || p}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Package preview */}
        {selected.size > 0 && !result && !generateMutation.isPending && (
          <div className="border-t border-gray-200 dark:border-slate-700 pt-4">
            <button
              onClick={() => setShowPreview(!showPreview)}
              className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-slate-300 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              <Eye className="w-4 h-4" />
              {t('transfer.preview') || 'Package preview'}
              {showPreview ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
            </button>

            {showPreview && (
              <div className="mt-3 bg-gray-50 dark:bg-slate-900/50 rounded-lg p-4 space-y-3">
                <p className="text-xs text-gray-500 dark:text-slate-400">
                  {t('transfer.preview_desc') || 'Summary of what will be included in the package'}
                </p>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {TRANSFER_SECTIONS.map((section) => {
                    const isIncluded = selected.has(section);
                    return (
                      <div
                        key={section}
                        className={cn(
                          'rounded-lg border p-2.5',
                          isIncluded
                            ? 'border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/10'
                            : 'border-gray-200 dark:border-slate-700 bg-white dark:bg-slate-800 opacity-50',
                        )}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs font-medium text-gray-700 dark:text-slate-300">
                            {t(`transfer.section_${section}`) || section}
                          </span>
                          <span
                            className={cn(
                              'text-[10px] font-medium px-1.5 py-0.5 rounded-full',
                              isIncluded
                                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                : 'bg-gray-100 text-gray-500 dark:bg-slate-700 dark:text-slate-500',
                            )}
                          >
                            {isIncluded ? t('transfer.included') || 'Included' : t('transfer.excluded') || 'Excluded'}
                          </span>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="flex items-center gap-4 text-xs text-gray-500 dark:text-slate-400 pt-1">
                  <span>
                    {selected.size} {t('transfer.sections_selected') || 'sections selected'}
                  </span>
                  <span>
                    {t('transfer.format') || 'Format'}: {exportFormat.toUpperCase()}
                  </span>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Error state */}
        {generateMutation.isError && (
          <div className="flex items-center gap-2 p-3 bg-red-50 dark:bg-red-900/20 rounded-lg border border-red-200 dark:border-red-800">
            <AlertTriangle className="w-4 h-4 text-red-600 dark:text-red-400 shrink-0" />
            <p className="text-sm text-red-700 dark:text-red-300">{t('transfer.error') || 'An error occurred'}</p>
          </div>
        )}

        {/* Result display */}
        {result && (
          <div className="border border-gray-200 dark:border-slate-700 rounded-lg p-4 space-y-3 bg-gray-50 dark:bg-slate-900/50">
            {/* Meta info + download */}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-3 text-sm">
                <span className="text-gray-500 dark:text-slate-400">
                  {t('transfer.generated_at') || 'Generated'}: {formatDate(result.generated_at)}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400">
                  {t('transfer.version') || 'Version'} {result.schema_version}
                </span>
                <button
                  onClick={() => handleDownload(result, exportFormat)}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium rounded-lg border border-gray-300 dark:border-slate-600 text-gray-700 dark:text-slate-200 hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
                >
                  <Download className="w-3.5 h-3.5" />
                  {t('transfer.download') || 'Download'} {exportFormat.toUpperCase()}
                </button>
              </div>
            </div>

            {/* Section summary cards */}
            <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
              {TRANSFER_SECTIONS.map((section) => {
                const data = getSectionData(result, section);
                if (data == null) return null;
                return (
                  <div
                    key={section}
                    className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-3"
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <span className="inline-flex items-center justify-center w-5 h-5 rounded text-[9px] font-bold bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300">
                        {SECTION_ICONS[section]}
                      </span>
                      <p className="text-xs text-gray-500 dark:text-slate-400">
                        {t(`transfer.section_${section}`) || section}
                      </p>
                    </div>
                    <p className="text-sm font-semibold text-gray-900 dark:text-white">{sectionItemCount(data)}</p>
                  </div>
                );
              })}
            </div>

            {/* Estimated size */}
            <p className="text-xs text-gray-400 dark:text-slate-500 text-right">~{formatBytes(estimateSize(result))}</p>
          </div>
        )}

        {/* Empty state */}
        {!result && !generateMutation.isPending && !generateMutation.isError && !showPreview && (
          <p className="text-sm text-gray-500 dark:text-slate-400">
            {t('transfer.empty') || 'No transfer package generated yet'}
          </p>
        )}
      </div>

      {/* Package history */}
      {history.length > 0 && (
        <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-700 p-6 space-y-4">
          <button onClick={() => setShowHistory(!showHistory)} className="flex items-center justify-between w-full">
            <h3 className="text-sm font-semibold text-gray-900 dark:text-white flex items-center gap-2">
              <Clock className="w-4 h-4 text-gray-500 dark:text-slate-400" />
              {t('transfer.history') || 'Package history'}
              <span className="text-xs font-normal text-gray-500 dark:text-slate-400">({history.length})</span>
            </h3>
            {showHistory ? (
              <ChevronUp className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            )}
          </button>

          {showHistory && (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-gray-200 dark:border-slate-700">
                    <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                      {t('transfer.history_date') || 'Date'}
                    </th>
                    <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                      {t('transfer.history_format') || 'Format'}
                    </th>
                    <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                      {t('transfer.history_sections') || 'Sections'}
                    </th>
                    <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                      {t('transfer.history_size') || 'Size'}
                    </th>
                    <th className="text-left py-2 px-2 text-xs font-medium text-gray-500 dark:text-slate-400">
                      {t('transfer.history_recipient') || 'Recipient'}
                    </th>
                    <th className="py-2 px-2" />
                  </tr>
                </thead>
                <tbody>
                  {history.map((entry) => (
                    <tr
                      key={entry.id}
                      className="border-b border-gray-100 dark:border-slate-700/50 hover:bg-gray-50 dark:hover:bg-slate-700/30"
                    >
                      <td className="py-2 px-2 text-gray-700 dark:text-slate-300">
                        {formatDateTime(entry.generated_at)}
                      </td>
                      <td className="py-2 px-2">
                        <span className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300">
                          {entry.format.toUpperCase()}
                        </span>
                      </td>
                      <td className="py-2 px-2 text-gray-600 dark:text-slate-400">
                        {entry.sections.length}/{TRANSFER_SECTIONS.length}
                      </td>
                      <td className="py-2 px-2 text-gray-600 dark:text-slate-400">{formatBytes(entry.size_bytes)}</td>
                      <td className="py-2 px-2 text-gray-600 dark:text-slate-400">
                        {entry.recipient?.name || entry.recipient?.email || '-'}
                      </td>
                      <td className="py-2 px-2">
                        <button
                          onClick={() => handleDownload(entry.data, entry.format)}
                          className="p-1 rounded hover:bg-gray-100 dark:hover:bg-slate-600 transition-colors"
                          title={t('transfer.download') || 'Download'}
                        >
                          <Download className="w-3.5 h-3.5 text-gray-500 dark:text-slate-400" />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
