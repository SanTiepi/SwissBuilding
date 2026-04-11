import { useState } from 'react';
import type { TenderQuote, TenderComparison, TenderComparisonEntry } from '@/api/rfq';
import { useTranslation } from '@/i18n';
import { cn, formatDate } from '@/utils/formatters';
import { AlertTriangle, CheckCircle2, Loader2, BarChart3, Info } from 'lucide-react';

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

export interface QuoteComparisonProps {
  tenderId: string;
  quotes: TenderQuote[];
  comparison: TenderComparison | null;
  onAttribute: (quoteId: string, reason: string) => void;
  onGenerateComparison: () => void;
  isGenerating?: boolean;
  isAttributing?: boolean;
  contractorNames?: Record<string, string>;
}

// ---------------------------------------------------------------------------
// Status badge (inline, small)
// ---------------------------------------------------------------------------

const STATUS_LABELS: Record<string, { label: string; cls: string }> = {
  received: { label: 'Recu', cls: 'text-blue-700 dark:text-blue-300 bg-blue-100 dark:bg-blue-900/30' },
  under_review: { label: 'En revue', cls: 'text-amber-700 dark:text-amber-300 bg-amber-100 dark:bg-amber-900/30' },
  selected: { label: 'Selectionne', cls: 'text-green-700 dark:text-green-300 bg-green-100 dark:bg-green-900/30' },
  rejected: { label: 'Rejete', cls: 'text-red-700 dark:text-red-300 bg-red-100 dark:bg-red-900/30' },
};

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_LABELS[status] ?? STATUS_LABELS.received;
  return <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium', cfg.cls)}>{cfg.label}</span>;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function formatCHF(value: number | null): string {
  if (value == null) return '-';
  return `CHF ${value.toLocaleString('fr-CH', { minimumFractionDigits: 2 })}`;
}

function formatDuration(days: number | null, t: (k: string) => string): string {
  if (days == null) return '-';
  return `${days} ${t('rfq.days') || 'jours'}`;
}

function truncate(text: string | null, max: number): string {
  if (!text) return '-';
  return text.length > max ? text.slice(0, max) + '...' : text;
}

// ---------------------------------------------------------------------------
// Comparison Table
// ---------------------------------------------------------------------------

interface RowDef {
  label: string;
  render: (
    entry: TenderComparisonEntry,
    stats: { minAmount: number | null; maxDuration: number | null },
  ) => {
    text: string;
    className?: string;
  };
}

function ComparisonTable({
  comparison,
  contractorNames,
  t,
}: {
  comparison: TenderComparison;
  contractorNames: Record<string, string>;
  t: (k: string) => string;
}) {
  const data = comparison.comparison_data;
  if (!data) return null;

  const entries = data.entries;
  const stats = data.statistics;
  const minAmount = stats.amount_range_chf.min;
  const maxDuration = stats.duration_range_days.max;

  const rows: RowDef[] = [
    {
      label: t('rfq.compare_amount') || 'Montant total (CHF)',
      render: (e, s) => ({
        text: formatCHF(e.total_amount_chf),
        className:
          e.total_amount_chf != null && s.minAmount != null && e.total_amount_chf === s.minAmount
            ? 'text-green-700 dark:text-green-400 font-semibold'
            : undefined,
      }),
    },
    {
      label: t('rfq.compare_duration') || 'Duree estimee (jours)',
      render: (e, s) => ({
        text: formatDuration(e.estimated_duration_days, t),
        className:
          e.estimated_duration_days != null && s.maxDuration != null && e.estimated_duration_days === s.maxDuration
            ? 'text-amber-700 dark:text-amber-400 font-semibold'
            : undefined,
      }),
    },
    {
      label: t('rfq.compare_scope') || 'Perimetre couvert',
      render: (e) => ({ text: truncate(e.scope_description, 120) }),
    },
    {
      label: t('rfq.compare_exclusions') || 'Exclusions',
      render: (e) => ({ text: truncate(e.exclusions, 120) }),
    },
    {
      label: t('rfq.compare_inclusions') || 'Inclusions',
      render: (e) => ({ text: truncate(e.inclusions, 120) }),
    },
    {
      label: t('rfq.compare_validity') || "Validite de l'offre",
      render: (e) => ({ text: e.validity_date ? formatDate(e.validity_date) : '-' }),
    },
    {
      label: t('rfq.compare_submitted') || 'Date de soumission',
      render: (e) => ({ text: e.submitted_at ? formatDate(e.submitted_at) : '-' }),
    },
    {
      label: t('rfq.compare_status') || 'Statut',
      render: () => ({ text: '' }), // rendered as badge below
    },
    {
      label: t('rfq.compare_document') || 'Documents',
      render: () => ({ text: '' }), // handled inline
    },
  ];

  return (
    <div className="overflow-x-auto -mx-4 sm:mx-0">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 dark:border-slate-700">
            <th className="text-left py-3 px-4 font-medium text-gray-500 dark:text-slate-400 sticky left-0 bg-white dark:bg-slate-800 z-10 min-w-[160px]">
              &nbsp;
            </th>
            {entries.map((e) => (
              <th
                key={e.quote_id}
                className={cn(
                  'text-left py-3 px-4 font-semibold text-gray-900 dark:text-white min-w-[200px]',
                  comparison.selected_quote_id === e.quote_id && 'bg-green-50 dark:bg-green-900/10',
                )}
              >
                {contractorNames[e.contractor_org_id] || e.contractor_org_id.slice(0, 8)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, ri) => (
            <tr
              key={ri}
              className={cn(
                'border-b border-gray-100 dark:border-slate-700/50',
                ri % 2 === 0 ? 'bg-gray-50/50 dark:bg-slate-800/50' : '',
              )}
            >
              <td className="py-2.5 px-4 font-medium text-gray-700 dark:text-slate-300 sticky left-0 bg-inherit z-10">
                {row.label}
              </td>
              {entries.map((entry) => {
                const isSelected = comparison.selected_quote_id === entry.quote_id;

                // Special rendering for status row
                if (ri === rows.length - 2) {
                  return (
                    <td
                      key={entry.quote_id}
                      className={cn('py-2.5 px-4', isSelected && 'bg-green-50 dark:bg-green-900/10')}
                    >
                      <StatusBadge status={entry.status} />
                    </td>
                  );
                }

                // Special rendering for documents row
                if (ri === rows.length - 1) {
                  const quoteObj = entries.find((q) => q.quote_id === entry.quote_id);
                  return (
                    <td
                      key={entry.quote_id}
                      className={cn(
                        'py-2.5 px-4 text-gray-600 dark:text-slate-400',
                        isSelected && 'bg-green-50 dark:bg-green-900/10',
                      )}
                    >
                      {quoteObj ? t('rfq.quote_document_link') || 'Voir document' : '-'}
                    </td>
                  );
                }

                const { text, className } = row.render(entry, { minAmount, maxDuration });
                return (
                  <td
                    key={entry.quote_id}
                    className={cn(
                      'py-2.5 px-4 text-gray-600 dark:text-slate-400',
                      className,
                      isSelected && 'bg-green-50 dark:bg-green-900/10',
                    )}
                  >
                    {text}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Attribution Section
// ---------------------------------------------------------------------------

function AttributionSection({
  comparison,
  entries,
  contractorNames,
  onAttribute,
  isAttributing,
  t,
}: {
  comparison: TenderComparison;
  entries: TenderComparisonEntry[];
  contractorNames: Record<string, string>;
  onAttribute: (quoteId: string, reason: string) => void;
  isAttributing: boolean;
  t: (k: string) => string;
}) {
  const [selectedQuoteId, setSelectedQuoteId] = useState('');
  const [reason, setReason] = useState('');

  // Already attributed
  if (comparison.selected_quote_id) {
    const selectedEntry = entries.find((e) => e.quote_id === comparison.selected_quote_id);
    return (
      <div className="bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg p-5">
        <div className="flex items-start gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400 mt-0.5 shrink-0" />
          <div>
            <p className="font-semibold text-green-800 dark:text-green-300">
              {t('rfq.tender_attributed') || 'Marche attribue'}
            </p>
            {selectedEntry && (
              <p className="text-sm text-green-700 dark:text-green-400 mt-1">
                {contractorNames[selectedEntry.contractor_org_id] || selectedEntry.contractor_org_id.slice(0, 8)}
                {selectedEntry.total_amount_chf != null && ` - ${formatCHF(selectedEntry.total_amount_chf)}`}
              </p>
            )}
            {comparison.selection_reason && (
              <p className="text-sm text-green-600 dark:text-green-400/80 mt-2 italic">
                {t('rfq.reason') || 'Raison'}: {comparison.selection_reason}
              </p>
            )}
            {comparison.attributed_at && (
              <p className="text-xs text-green-500 dark:text-green-500 mt-2">
                {t('rfq.attributed_on') || 'Attribue le'} {formatDate(comparison.attributed_at)}
              </p>
            )}
          </div>
        </div>
      </div>
    );
  }

  // Attribution form
  return (
    <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-5">
      <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-1">
        {t('rfq.attribute_tender') || 'Attribuer le marche'}
      </h3>

      <div className="flex items-start gap-2 mb-4">
        <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
        <p className="text-xs text-amber-700 dark:text-amber-400">
          {t('rfq.attribution_warning') || "L'attribution est definitive et sera tracee dans le dossier du batiment."}
        </p>
      </div>

      <div className="space-y-4">
        {/* Quote selector */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            {t('rfq.select_quote') || 'Selectionner un devis'}
          </label>
          <select
            value={selectedQuoteId}
            onChange={(e) => setSelectedQuoteId(e.target.value)}
            className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm text-gray-900 dark:text-white"
          >
            <option value="">{t('rfq.choose_quote') || '-- Choisir un devis --'}</option>
            {entries
              .filter((e) => e.status !== 'rejected')
              .map((e) => (
                <option key={e.quote_id} value={e.quote_id}>
                  {contractorNames[e.contractor_org_id] || e.contractor_org_id.slice(0, 8)}
                  {e.total_amount_chf != null ? ` - ${formatCHF(e.total_amount_chf)}` : ''}
                </option>
              ))}
          </select>
        </div>

        {/* Reason */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-slate-300 mb-1">
            {t('rfq.attribution_reason') || "Raison de l'attribution"} *
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            placeholder={t('rfq.attribution_reason_placeholder') || 'Indiquer la raison du choix...'}
            className="w-full px-3 py-2 rounded-lg border border-gray-200 dark:border-slate-600 bg-white dark:bg-slate-700 text-sm text-gray-900 dark:text-white placeholder:text-gray-400 dark:placeholder:text-slate-500"
          />
        </div>

        {/* Confirm button */}
        <button
          onClick={() => onAttribute(selectedQuoteId, reason)}
          disabled={!selectedQuoteId || !reason.trim() || isAttributing}
          className="px-4 py-2 text-sm font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isAttributing && <Loader2 className="w-4 h-4 animate-spin inline mr-1.5" />}
          {t('rfq.confirm_attribution') || "Confirmer l'attribution"}
        </button>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main Component
// ---------------------------------------------------------------------------

export default function QuoteComparison({
  tenderId: _tenderId,
  quotes,
  comparison,
  onAttribute,
  onGenerateComparison,
  isGenerating,
  isAttributing,
  contractorNames = {},
}: QuoteComparisonProps) {
  const { t } = useTranslation();

  // No comparison generated yet
  if (!comparison) {
    return (
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 p-8 text-center">
        <BarChart3 className="w-10 h-10 text-gray-300 dark:text-slate-600 mx-auto mb-3" />
        <p className="text-gray-600 dark:text-slate-400 mb-1">
          {quotes.length} {t('rfq.quotes_available') || 'devis disponible(s)'}
        </p>
        <p className="text-sm text-gray-500 dark:text-slate-500 mb-4">
          {t('rfq.generate_comparison_hint') || 'Generez la comparaison pour voir les devis cote a cote.'}
        </p>
        <button
          onClick={onGenerateComparison}
          disabled={isGenerating || quotes.length === 0}
          className="px-5 py-2.5 text-sm font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
        >
          {isGenerating ? (
            <>
              <Loader2 className="w-4 h-4 animate-spin inline mr-1.5" />
              {t('rfq.generating') || 'Generation...'}
            </>
          ) : (
            <>
              <BarChart3 className="w-4 h-4 inline mr-1.5" />
              {t('rfq.generate_comparison') || 'Generer la comparaison'}
            </>
          )}
        </button>
      </div>
    );
  }

  const entries = comparison.comparison_data?.entries ?? [];

  return (
    <div className="space-y-4">
      {/* Disclaimer */}
      <div className="flex items-start gap-2 bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-3">
        <Info className="w-4 h-4 text-blue-500 mt-0.5 shrink-0" />
        <p className="text-xs text-blue-700 dark:text-blue-300">
          {t('rfq.comparison_disclaimer') ||
            "Comparaison factuelle. Aucun classement ni recommandation. Le choix revient au maitre d'ouvrage."}
        </p>
      </div>

      {/* Comparison table */}
      <div className="bg-white dark:bg-slate-800 rounded-lg border border-gray-200 dark:border-slate-700 overflow-hidden">
        <ComparisonTable comparison={comparison} contractorNames={contractorNames} t={t} />
      </div>

      {/* Attribution section */}
      <AttributionSection
        comparison={comparison}
        entries={entries}
        contractorNames={contractorNames}
        onAttribute={onAttribute}
        isAttributing={isAttributing ?? false}
        t={t}
      />
    </div>
  );
}
