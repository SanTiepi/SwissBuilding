import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { cn, formatDate } from '@/utils/formatters';
import { exchangeApi, type Publication, type ImportReceipt } from '@/api/exchange';
import { ArrowUpRight, ArrowDownLeft, FileText, Package, Hash, GitCompare, Shield } from 'lucide-react';
import PublicationDiffView from './PublicationDiffView';

interface ExchangeHistoryPanelProps {
  buildingId: string;
}

const DELIVERY_STATE_STYLE: Record<string, string> = {
  published: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
  superseded: 'bg-gray-100 text-gray-500 dark:bg-gray-700 dark:text-gray-400',
  revoked: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
};

const IMPORT_STATUS_STYLE: Record<string, string> = {
  received: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400',
  accepted: 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400',
  rejected: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400',
  pending: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/40 dark:text-yellow-400',
};

export default function ExchangeHistoryPanel({ buildingId }: ExchangeHistoryPanelProps) {
  const { t } = useTranslation();

  const { data: publications, isLoading: loadingPubs } = useQuery({
    queryKey: ['exchange-publications', buildingId],
    queryFn: () => exchangeApi.listPublications(buildingId),
    staleTime: 60_000,
  });

  const { data: imports, isLoading: loadingImports } = useQuery({
    queryKey: ['exchange-imports', buildingId],
    queryFn: () => exchangeApi.listImportReceipts(buildingId),
    staleTime: 60_000,
  });

  const isLoading = loadingPubs || loadingImports;

  if (isLoading) {
    return (
      <div
        className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6"
        data-testid="exchange-history-loading"
      >
        <div className="animate-pulse space-y-3">
          <div className="h-5 bg-gray-200 dark:bg-gray-700 rounded w-44" />
          <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
          <div className="h-12 bg-gray-200 dark:bg-gray-700 rounded" />
        </div>
      </div>
    );
  }

  const pubs = publications ?? [];
  const imps = imports ?? [];
  const isEmpty = pubs.length === 0 && imps.length === 0;

  return (
    <div
      className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6"
      data-testid="exchange-history-panel"
    >
      <h3 className="text-base font-semibold text-gray-900 dark:text-white mb-4 flex items-center gap-2">
        <Package className="w-5 h-5 text-gray-500 dark:text-gray-400" />
        {t('exchange.title')}
      </h3>

      {isEmpty ? (
        <div className="text-center py-8" data-testid="exchange-empty">
          <FileText className="w-8 h-8 text-gray-300 dark:text-gray-600 mx-auto mb-2" />
          <p className="text-sm text-gray-500 dark:text-gray-400">{t('exchange.empty')}</p>
        </div>
      ) : (
        <div className="space-y-5" data-testid="exchange-list">
          {/* Outbound publications */}
          {pubs.length > 0 && (
            <div data-testid="publications-section">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1.5">
                <ArrowUpRight className="w-3.5 h-3.5 text-blue-500" />
                {t('exchange.outbound')} ({pubs.length})
              </h4>
              <div className="space-y-2">
                {pubs.map((pub) => (
                  <PublicationRow key={pub.id} pub={pub} />
                ))}
              </div>
            </div>
          )}

          {/* Inbound import receipts */}
          {imps.length > 0 && (
            <div data-testid="imports-section">
              <h4 className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2 flex items-center gap-1.5">
                <ArrowDownLeft className="w-3.5 h-3.5 text-green-500" />
                {t('exchange.inbound')} ({imps.length})
              </h4>
              <div className="space-y-2">
                {imps.map((imp) => (
                  <ImportRow key={imp.id} receipt={imp} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function PublicationRow({ pub }: { pub: Publication }) {
  const [showDiff, setShowDiff] = useState(false);
  const stateStyle =
    DELIVERY_STATE_STYLE[pub.delivery_state] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';

  return (
    <div>
      <div
        className="flex items-center gap-3 py-2 px-3 rounded-lg bg-gray-50 dark:bg-gray-900/30"
        data-testid={`pub-row-${pub.id}`}
      >
        <ArrowUpRight className="w-4 h-4 text-blue-500 flex-shrink-0" />
        <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{pub.audience_type}</span>
        <span
          className={cn('inline-block px-2 py-0.5 rounded text-xs font-medium', stateStyle)}
          data-testid={`pub-state-${pub.id}`}
        >
          {pub.delivery_state}
        </span>
        <span className="text-xs text-gray-500 dark:text-gray-400 flex-1">{formatDate(pub.published_at)}</span>
        <button
          onClick={() => setShowDiff(!showDiff)}
          className="flex items-center gap-1 text-xs text-indigo-500 hover:text-indigo-700 dark:text-indigo-400"
          title="View diff"
          data-testid={`pub-diff-toggle-${pub.id}`}
        >
          <GitCompare className="w-3 h-3" />
        </button>
        <div className="hidden sm:flex items-center gap-2 text-xs text-gray-400 dark:text-gray-500">
          <Hash className="w-3 h-3" />
          <span title={pub.content_hash} data-testid={`pub-hash-${pub.id}`}>
            {pub.content_hash.slice(0, 8)}
          </span>
        </div>
        {pub.superseded_by_id && (
          <span className="text-xs text-gray-400 dark:text-gray-500 italic" data-testid={`pub-superseded-${pub.id}`}>
            superseded
          </span>
        )}
      </div>
      {showDiff && (
        <div className="mt-1 ml-6">
          <PublicationDiffView publicationId={pub.id} />
        </div>
      )}
    </div>
  );
}

function ImportRow({ receipt }: { receipt: ImportReceipt }) {
  const statusStyle =
    IMPORT_STATUS_STYLE[receipt.status] ?? 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-400';
  const isValidated = receipt.status === 'validated' || receipt.status === 'integrated';

  return (
    <div
      className="flex items-center gap-3 py-2 px-3 rounded-lg bg-gray-50 dark:bg-gray-900/30"
      data-testid={`import-row-${receipt.id}`}
    >
      <ArrowDownLeft className="w-4 h-4 text-green-500 flex-shrink-0" />
      <span className="text-xs font-medium text-gray-700 dark:text-gray-300">{receipt.source_system}</span>
      <span className="text-xs text-gray-500 dark:text-gray-400">
        {receipt.contract_code} v{receipt.contract_version}
      </span>
      <span
        className={cn('inline-block px-2 py-0.5 rounded text-xs font-medium', statusStyle)}
        data-testid={`import-status-${receipt.id}`}
      >
        {receipt.status}
      </span>
      {isValidated && <Shield className="w-3 h-3 text-green-500" data-testid={`import-validated-${receipt.id}`} />}
      <span className="text-xs text-gray-500 dark:text-gray-400 flex-1">{formatDate(receipt.imported_at)}</span>
    </div>
  );
}
