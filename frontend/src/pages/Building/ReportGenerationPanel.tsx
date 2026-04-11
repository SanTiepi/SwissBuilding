import { useState } from 'react';
import { useMutation } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { useTranslation } from '@/i18n';
import { cn, formatDateTime } from '@/utils/formatters';
import ReportDownloadButton from '@/components/ReportDownloadButton';
import {
  FileText,
  CheckCircle2,
  AlertTriangle,
  Shield,
  ChevronDown,
  ChevronRight,
  Hash,
  Clock,
  Download,
} from 'lucide-react';

interface ReportGenerationPanelProps {
  buildingId: string;
}

interface ReportResult {
  building_id: string;
  status: string;
  report_type: string;
  html_payload: string;
  html_payload_length: number;
  sha256: string;
  generated_at: string;
  version: string;
  language: string;
  sections_count: number;
  include_photos: boolean;
  include_plans: boolean;
  metadata: {
    address: string;
    egid: string;
    canton: string;
    completeness_pct: number;
    diagnostics_count: number;
    samples_count: number;
    documents_count: number;
    disclaimer: string;
    emitter: string;
  };
}

type PanelState = 'idle' | 'generating' | 'ready' | 'error';

async function generateReport(
  buildingId: string,
  options: { includePhotos: boolean; includePlans: boolean; language: string },
): Promise<ReportResult> {
  const params = new URLSearchParams({
    type: 'authority',
    include_photos: String(options.includePhotos),
    include_plans: String(options.includePlans),
    language: options.language,
  });
  const response = await apiClient.post<ReportResult>(`/buildings/${buildingId}/generate-report?${params.toString()}`);
  return response.data;
}

function downloadHtmlAsPdf(html: string, filename: string) {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export default function ReportGenerationPanel({ buildingId }: ReportGenerationPanelProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);
  const [includePhotos, setIncludePhotos] = useState(true);
  const [includePlans, setIncludePlans] = useState(true);

  const mutation = useMutation({
    mutationFn: () =>
      generateReport(buildingId, {
        includePhotos,
        includePlans,
        language: 'fr',
      }),
  });

  const panelState: PanelState = mutation.isPending
    ? 'generating'
    : mutation.isSuccess
      ? 'ready'
      : mutation.isError
        ? 'error'
        : 'idle';

  const report = mutation.data;

  const handleDownload = () => {
    if (!report) return;
    const filename = `rapport-autorite-${report.metadata.egid || buildingId}.html`;
    downloadHtmlAsPdf(report.html_payload, filename);
  };

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-gray-200 dark:border-slate-600 p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <FileText className="h-5 w-5 text-red-600 dark:text-red-400" />
          <h3 className="font-semibold text-gray-900 dark:text-white">
            {t('building.authority_report') || 'Rapport autorite (20+ pages)'}
          </h3>
        </div>
        <button
          onClick={() => setExpanded(!expanded)}
          className="text-gray-400 hover:text-gray-600 dark:hover:text-slate-300"
        >
          {expanded ? <ChevronDown className="h-5 w-5" /> : <ChevronRight className="h-5 w-5" />}
        </button>
      </div>

      <p className="text-sm text-gray-500 dark:text-slate-400 mb-4">
        {t('building.authority_report_desc') ||
          "Generez un dossier complet de 20+ pages pour soumission a l'autorite. Diagnostics, risques, recommandations, preuves — en 1 clic."}
      </p>

      {/* Options */}
      {expanded && (
        <div className="mb-4 space-y-2 p-3 bg-gray-50 dark:bg-slate-700/50 rounded-lg">
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={includePhotos}
              onChange={(e) => setIncludePhotos(e.target.checked)}
              className="rounded border-gray-300 dark:border-slate-500"
            />
            Inclure les photos terrain
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={includePlans}
              onChange={(e) => setIncludePlans(e.target.checked)}
              className="rounded border-gray-300 dark:border-slate-500"
            />
            Inclure les plans techniques
          </label>
        </div>
      )}

      {/* Generate button */}
      <ReportDownloadButton
        onClick={() => mutation.mutate()}
        loading={panelState === 'generating'}
        disabled={panelState === 'generating'}
        label={panelState === 'ready' ? 'Regenerer le rapport' : 'Generer le rapport PDF'}
      />

      {/* Error */}
      {panelState === 'error' && (
        <div className="mt-3 p-3 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-red-500 mt-0.5 shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-300">
            {t('building.report_error') || 'Erreur lors de la generation du rapport.'}
          </p>
        </div>
      )}

      {/* Result */}
      {panelState === 'ready' && report && (
        <div className="mt-4 space-y-3">
          {/* Success badge */}
          <div className="p-3 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg flex items-start gap-2">
            <CheckCircle2 className="h-4 w-4 text-green-500 mt-0.5 shrink-0" />
            <div className="text-sm text-green-700 dark:text-green-300">
              <p className="font-medium">Rapport genere avec succes</p>
              <p className="text-xs mt-1">
                {report.sections_count} sections | {Math.round(report.html_payload_length / 1024)} KB |{' '}
                {report.metadata.diagnostics_count} diagnostics | {report.metadata.samples_count} echantillons |{' '}
                {report.metadata.documents_count} documents
              </p>
            </div>
          </div>

          {/* Metadata grid */}
          <div className="grid grid-cols-2 gap-2 text-xs text-gray-600 dark:text-slate-400">
            <div className="flex items-center gap-1">
              <Clock className="h-3 w-3" />
              {formatDateTime(report.generated_at)}
            </div>
            <div className="flex items-center gap-1">
              <Shield className="h-3 w-3" />
              Completude: {report.metadata.completeness_pct}%
            </div>
            <div className="flex items-center gap-1 col-span-2">
              <Hash className="h-3 w-3" />
              <span className="font-mono truncate">{report.sha256.slice(0, 16)}...</span>
            </div>
          </div>

          {/* Download button */}
          <button
            onClick={handleDownload}
            className={cn(
              'inline-flex items-center gap-2 px-4 py-2 rounded-lg font-medium text-sm transition-all w-full justify-center',
              'bg-blue-600 text-white hover:bg-blue-700',
              'dark:bg-blue-700 dark:hover:bg-blue-600',
            )}
          >
            <Download className="h-4 w-4" />
            Telecharger le rapport HTML
          </button>
        </div>
      )}
    </div>
  );
}
