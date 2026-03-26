import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { diagnosticIntegrationApi, type ImportedDiagnosticSummaryDto } from '@/api/diagnosticIntegration';
import { ChevronDown, ChevronUp, AlertTriangle, Info, XCircle } from 'lucide-react';

interface ImportedDiagnosticSummaryProps {
  buildingId: string;
}

function ReadinessBadge({ status }: { status: string | null }) {
  const { t } = useTranslation();
  const colors: Record<string, string> = {
    ready: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    blocked: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    partial: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    unknown: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
  };
  const colorClass = (status && colors[status]) || colors.unknown;
  const label = status
    ? t(`imported_diagnostic.readiness_${status}`) || status
    : t('imported_diagnostic.readiness_unknown') || 'Unknown';
  return (
    <span
      data-testid="readiness-badge"
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  );
}

function ConsumerStateBadge({ state }: { state: string | null }) {
  const { t } = useTranslation();
  const colors: Record<string, string> = {
    imported: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    ingested: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    fetched: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
    matched: 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
    review_required: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    rejected_source: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
    duplicate: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
  };
  const colorClass = (state && colors[state]) || 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300';
  const label = state
    ? t(`imported_diagnostic.consumer_${state}`) || state
    : t('imported_diagnostic.consumer_unknown') || 'Unknown';
  return (
    <span
      data-testid="consumer-state-badge"
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${colorClass}`}
    >
      {label}
    </span>
  );
}

function FlagBadge({ flag }: { flag: string }) {
  const { t } = useTranslation();
  const styles: Record<string, string> = {
    no_ai: 'bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200',
    no_remediation: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300',
    partial_package: 'bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200',
    rejected_source: 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200',
  };
  return (
    <span
      data-testid={`flag-${flag}`}
      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles[flag] || styles.no_remediation}`}
    >
      {t(`imported_diagnostic.flag_${flag}`) || flag}
    </span>
  );
}

function SummaryCard({ summary }: { summary: ImportedDiagnosticSummaryDto }) {
  const { t } = useTranslation();
  const [showAi, setShowAi] = useState(false);
  const [showDetails, setShowDetails] = useState(false);

  return (
    <div data-testid="imported-diagnostic-card" className="space-y-3">
      {/* Warning banners */}
      {summary.match_state === 'needs_review' && (
        <div
          data-testid="banner-review-required"
          className="flex items-center gap-2 px-3 py-2 rounded-md bg-orange-50 dark:bg-orange-900/30 border border-orange-200 dark:border-orange-800 text-orange-800 dark:text-orange-200 text-sm"
        >
          <AlertTriangle className="w-4 h-4 shrink-0" />
          {t('imported_diagnostic.banner_review_required')}
        </div>
      )}
      {summary.match_state === 'unmatched' && (
        <div
          data-testid="banner-unmatched"
          className="flex items-center gap-2 px-3 py-2 rounded-md bg-gray-50 dark:bg-gray-800 border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 text-sm"
        >
          <XCircle className="w-4 h-4 shrink-0" />
          {t('imported_diagnostic.banner_unmatched')}
        </div>
      )}
      {summary.is_partial && (
        <div
          data-testid="banner-partial"
          className="flex items-center gap-2 px-3 py-2 rounded-md bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-200 text-sm"
        >
          <Info className="w-4 h-4 shrink-0" />
          {t('imported_diagnostic.banner_partial')}
        </div>
      )}

      {/* Source V4 zone */}
      <div className="border border-indigo-200 dark:border-indigo-700 rounded-lg p-4 bg-indigo-50/50 dark:bg-indigo-900/20">
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-semibold uppercase tracking-wide text-indigo-600 dark:text-indigo-400">
            {t('imported_diagnostic.source_label')}
          </span>
          <div className="flex items-center gap-1.5 flex-wrap justify-end">
            {summary.flags.map((flag) => (
              <FlagBadge key={flag} flag={flag} />
            ))}
          </div>
        </div>

        <div className="flex items-center justify-between mb-1">
          <span data-testid="mission-ref" className="text-sm font-medium text-gray-900 dark:text-white">
            {summary.mission_ref}
          </span>
          <ReadinessBadge status={summary.report_readiness_status} />
        </div>

        <p className="text-xs text-gray-500 dark:text-gray-400 mb-2">
          {t('imported_diagnostic.published_at')} {new Date(summary.published_at).toLocaleDateString()}
        </p>

        {summary.sample_count != null && (
          <p data-testid="sample-summary" className="text-sm text-gray-700 dark:text-gray-300">
            {t('imported_diagnostic.sample_summary', {
              count: summary.sample_count,
              positive: summary.positive_count ?? 0,
            })}
          </p>
        )}

        {/* AI summary (collapsible) */}
        {summary.has_ai && summary.ai_summary_text && (
          <div className="mt-2">
            <button
              onClick={() => setShowAi(!showAi)}
              className="flex items-center gap-1 text-xs text-indigo-600 dark:text-indigo-400 hover:underline"
            >
              {showAi ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
              {t('imported_diagnostic.ai_summary')}
            </button>
            {showAi && (
              <p
                data-testid="ai-summary-text"
                className="mt-1 text-sm text-gray-600 dark:text-gray-300 bg-white dark:bg-gray-800 rounded p-2 border border-gray-200 dark:border-gray-700"
              >
                {summary.ai_summary_text}
              </p>
            )}
          </div>
        )}

        {/* Source details (collapsible) */}
        <div className="mt-2">
          <button
            onClick={() => setShowDetails(!showDetails)}
            className="flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400 hover:underline"
          >
            {showDetails ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            {t('imported_diagnostic.source_details')}
          </button>
          {showDetails && (
            <div className="mt-1 text-xs text-gray-500 dark:text-gray-400 space-y-0.5">
              <p>
                {t('imported_diagnostic.snapshot_version')}: {summary.snapshot_version}
              </p>
              <p className="font-mono truncate">
                {t('imported_diagnostic.payload_hash')}: {summary.payload_hash}
              </p>
            </div>
          )}
        </div>
      </div>

      {/* BatiConnect state zone */}
      <div className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 bg-white dark:bg-gray-800">
        <span className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-2 block">
          {t('imported_diagnostic.baticonnect_state')}
        </span>
        <div className="flex items-center gap-2 mb-1">
          <ConsumerStateBadge state={summary.consumer_state} />
          {summary.match_key_type && summary.match_state.includes('matched') && (
            <span data-testid="match-info" className="text-xs text-gray-500 dark:text-gray-400">
              {t('imported_diagnostic.matched_by', { key_type: summary.match_key_type })}
            </span>
          )}
        </div>
        {summary.contract_version && (
          <p className="text-xs text-gray-400 dark:text-gray-500">
            {t('imported_diagnostic.contract_version')}: {summary.contract_version}
          </p>
        )}
      </div>
    </div>
  );
}

export function ImportedDiagnosticSummary({ buildingId }: ImportedDiagnosticSummaryProps) {
  const { data: summaries = [], isLoading } = useQuery({
    queryKey: ['imported-diagnostic-summaries', buildingId],
    queryFn: () => diagnosticIntegrationApi.getImportedDiagnosticSummaries(buildingId),
    enabled: !!buildingId,
  });

  if (isLoading || summaries.length === 0) {
    return null;
  }

  return (
    <div data-testid="imported-diagnostic-summaries" className="space-y-4">
      {summaries.map((summary, idx) => (
        <SummaryCard key={`${summary.mission_ref}-${idx}`} summary={summary} />
      ))}
    </div>
  );
}

export default ImportedDiagnosticSummary;
