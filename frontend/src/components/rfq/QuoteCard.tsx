import { useState } from 'react';
import type { TenderQuote } from '@/api/rfq';
import { useTranslation } from '@/i18n';
import { cn, formatDate } from '@/utils/formatters';
import { ChevronDown, ChevronUp, FileText, Loader2, AlertCircle } from 'lucide-react';

// ---------------------------------------------------------------------------
// Status badge config
// ---------------------------------------------------------------------------

const QUOTE_STATUS: Record<string, { label: string; color: string; bg: string }> = {
  received: { label: 'Recu', color: 'text-blue-700 dark:text-blue-300', bg: 'bg-blue-100 dark:bg-blue-900/30' },
  under_review: {
    label: 'En revue',
    color: 'text-amber-700 dark:text-amber-300',
    bg: 'bg-amber-100 dark:bg-amber-900/30',
  },
  selected: {
    label: 'Selectionne',
    color: 'text-green-700 dark:text-green-300',
    bg: 'bg-green-100 dark:bg-green-900/30',
  },
  rejected: { label: 'Rejete', color: 'text-red-700 dark:text-red-300', bg: 'bg-red-100 dark:bg-red-900/30' },
};

function QuoteStatusBadge({ status }: { status: string }) {
  const config = QUOTE_STATUS[status] ?? QUOTE_STATUS.received;
  return (
    <span
      className={cn('inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium', config.bg, config.color)}
    >
      {config.label}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface QuoteCardProps {
  quote: TenderQuote;
  contractorName?: string;
  onExtract?: (quoteId: string) => void;
  isExtracting?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export default function QuoteCard({ quote, contractorName, onExtract, isExtracting }: QuoteCardProps) {
  const { t } = useTranslation();
  const [expanded, setExpanded] = useState(false);

  const exclusionLines = quote.exclusions?.split('\n').filter(Boolean) ?? [];
  const needsExtraction = quote.extracted_data === null && quote.document_id !== null;

  return (
    <div
      className={cn(
        'bg-white dark:bg-slate-800 rounded-lg border p-4 transition-shadow',
        quote.status === 'selected'
          ? 'border-green-300 dark:border-green-700 shadow-md'
          : quote.status === 'rejected'
            ? 'border-gray-200 dark:border-slate-700 opacity-60'
            : 'border-gray-200 dark:border-slate-700 hover:shadow-md',
      )}
    >
      {/* Header row */}
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <p className="font-semibold text-gray-900 dark:text-white truncate">
            {contractorName || quote.contractor_org_id.slice(0, 8)}
          </p>
          <p className="text-2xl font-bold text-gray-900 dark:text-white mt-1">
            {quote.total_amount_chf != null
              ? `CHF ${Number(quote.total_amount_chf).toLocaleString('fr-CH', { minimumFractionDigits: 2 })}`
              : t('rfq.amount_not_specified') || 'Montant non specifie'}
          </p>
        </div>
        <QuoteStatusBadge status={quote.status} />
      </div>

      {/* Key metrics */}
      <div className="mt-3 flex flex-wrap gap-x-6 gap-y-1 text-sm text-gray-600 dark:text-slate-400">
        {quote.estimated_duration_days != null && (
          <span>
            {quote.estimated_duration_days} {t('rfq.days') || 'jours'}
          </span>
        )}
        {exclusionLines.length > 0 && (
          <span>
            {exclusionLines.length} {t('rfq.exclusions_count') || 'exclusion(s)'}
          </span>
        )}
        {quote.validity_date && (
          <span>
            {t('rfq.valid_until') || "Valide jusqu'au"} {formatDate(quote.validity_date)}
          </span>
        )}
      </div>

      {/* Scope summary (truncated) */}
      {quote.scope_description && (
        <p className="mt-2 text-sm text-gray-500 dark:text-slate-400 line-clamp-2">{quote.scope_description}</p>
      )}

      {/* Action buttons */}
      <div className="mt-3 flex items-center gap-2">
        <button
          onClick={() => setExpanded(!expanded)}
          className="inline-flex items-center gap-1 text-xs font-medium text-gray-600 dark:text-slate-400 hover:text-gray-900 dark:hover:text-white"
        >
          {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          {expanded ? t('rfq.hide_detail') || 'Masquer le detail' : t('rfq.show_detail') || 'Voir le detail'}
        </button>

        {needsExtraction && onExtract && (
          <button
            onClick={() => onExtract(quote.id)}
            disabled={isExtracting}
            className="inline-flex items-center gap-1 text-xs font-medium px-2.5 py-1 rounded-md bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50 disabled:opacity-50"
          >
            {isExtracting ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
            {t('rfq.extract_data') || 'Extraire les donnees'}
          </button>
        )}

        {quote.extracted_data && (quote.extracted_data as Record<string, unknown>).status === 'pending_extraction' && (
          <span className="inline-flex items-center gap-1 text-xs text-amber-600 dark:text-amber-400">
            <AlertCircle className="w-3.5 h-3.5" />
            {t('rfq.extraction_pending') || 'Extraction en cours'}
          </span>
        )}
      </div>

      {/* Expanded detail */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-gray-100 dark:border-slate-700 space-y-3 text-sm">
          {quote.scope_description && (
            <div>
              <p className="font-medium text-gray-700 dark:text-slate-300">
                {t('rfq.scope_covered') || 'Perimetre couvert'}
              </p>
              <p className="text-gray-600 dark:text-slate-400 whitespace-pre-line">{quote.scope_description}</p>
            </div>
          )}

          {quote.exclusions && (
            <div>
              <p className="font-medium text-gray-700 dark:text-slate-300">{t('rfq.exclusions') || 'Exclusions'}</p>
              <p className="text-gray-600 dark:text-slate-400 whitespace-pre-line">{quote.exclusions}</p>
            </div>
          )}

          {quote.inclusions && (
            <div>
              <p className="font-medium text-gray-700 dark:text-slate-300">{t('rfq.inclusions') || 'Inclusions'}</p>
              <p className="text-gray-600 dark:text-slate-400 whitespace-pre-line">{quote.inclusions}</p>
            </div>
          )}

          {quote.submitted_at && (
            <div>
              <p className="font-medium text-gray-700 dark:text-slate-300">
                {t('rfq.submitted_at') || 'Date de soumission'}
              </p>
              <p className="text-gray-600 dark:text-slate-400">{formatDate(quote.submitted_at)}</p>
            </div>
          )}

          {quote.document_id && (
            <div>
              <p className="font-medium text-gray-700 dark:text-slate-300">{t('rfq.document') || 'Document'}</p>
              <p className="text-gray-600 dark:text-slate-400">
                {t('rfq.document_attached') || 'Document joint'} ({quote.document_id.slice(0, 8)}...)
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
