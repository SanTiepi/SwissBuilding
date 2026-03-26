import { useState, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { useAuthStore } from '@/store/authStore';
import { diagnosticReviewApi } from '@/api/diagnosticReview';
import { buildingsApi } from '@/api/buildings';
import { cn } from '@/utils/formatters';
import type { Building } from '@/types';
import type { DiagnosticPublication } from '@/components/building-detail/DiagnosticPublicationCard';
import {
  Loader2,
  AlertTriangle,
  ClipboardCheck,
  Search,
  X,
  Building2,
  Link2,
  CheckCircle2,
  MapPin,
  FileText,
  RefreshCw,
} from 'lucide-react';

/* ------------------------------------------------------------------ */
/*  Style maps                                                         */
/* ------------------------------------------------------------------ */

const MATCH_STATE_STYLES: Record<string, string> = {
  needs_review: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  unmatched: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  auto_matched: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  manual_matched: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
};

const MISSION_TYPE_STYLES: Record<string, string> = {
  asbestos_full: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  pcb: 'bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400',
  lead: 'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400',
  hap: 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400',
  radon: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
  multi: 'bg-indigo-100 text-indigo-800 dark:bg-indigo-900/30 dark:text-indigo-400',
};

const DEFAULT_BADGE = 'bg-gray-100 text-gray-700 dark:bg-slate-700 dark:text-slate-300';

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export default function AdminDiagnosticReview() {
  const { t } = useTranslation();
  const user = useAuthStore((s) => s.user);
  const queryClient = useQueryClient();

  /* ---- access guard ---- */
  if (user?.role !== 'admin') {
    return (
      <div className="flex items-center justify-center min-h-[60vh]" data-testid="diag-review-access-denied">
        <div className="text-center">
          <AlertTriangle className="w-12 h-12 text-amber-500 mx-auto mb-4" />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
            {t('common.access_denied') || 'Access denied'}
          </h2>
        </div>
      </div>
    );
  }

  return <DiagnosticReviewContent t={t} queryClient={queryClient} />;
}

/* ------------------------------------------------------------------ */
/*  Main content (only rendered for admins)                             */
/* ------------------------------------------------------------------ */

function DiagnosticReviewContent({
  t,
  queryClient,
}: {
  t: (key: string) => string;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const {
    data: publications,
    isLoading,
    isError,
    refetch,
  } = useQuery({
    queryKey: ['diagnostic-publications', 'unmatched'],
    queryFn: diagnosticReviewApi.getUnmatched,
  });

  return (
    <div className="max-w-5xl mx-auto px-4 py-8 space-y-6" data-testid="admin-diag-review-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ClipboardCheck className="w-6 h-6 text-indigo-500" />
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('diag_review.title') || 'Diagnostic Publication Review'}
          </h1>
          {publications && publications.length > 0 && (
            <span
              className="inline-flex items-center justify-center min-w-[1.5rem] h-6 px-2 text-xs font-medium rounded-full bg-orange-100 text-orange-800 dark:bg-orange-900/30 dark:text-orange-400"
              data-testid="diag-review-count"
            >
              {publications.length}
            </span>
          )}
        </div>
        <button
          onClick={() => refetch()}
          className="flex items-center gap-2 px-3 py-2 text-sm font-medium text-gray-700 dark:text-slate-300 bg-white dark:bg-slate-800 border border-gray-300 dark:border-slate-600 rounded-lg hover:bg-gray-50 dark:hover:bg-slate-700 transition-colors"
          data-testid="diag-review-refresh"
        >
          <RefreshCw className="w-4 h-4" />
          {t('common.refresh') || 'Refresh'}
        </button>
      </div>

      <p className="text-sm text-gray-500 dark:text-slate-400">
        {t('diag_review.description') ||
          'Review diagnostic publications that could not be automatically matched to a building. Match them manually to integrate the diagnostic data.'}
      </p>

      {/* Loading */}
      {isLoading && (
        <div className="flex items-center justify-center py-16" data-testid="diag-review-loading">
          <Loader2 className="w-8 h-8 animate-spin text-indigo-500" />
        </div>
      )}

      {/* Error */}
      {isError && (
        <div
          className="flex items-center gap-3 p-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg"
          data-testid="diag-review-error"
        >
          <AlertTriangle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <p className="text-sm text-red-700 dark:text-red-400">
            {t('diag_review.error') || 'Failed to load unmatched publications.'}
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && publications && publications.length === 0 && (
        <div className="flex flex-col items-center justify-center py-16 text-center" data-testid="diag-review-empty">
          <CheckCircle2 className="w-12 h-12 text-green-500 mb-4" />
          <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
            {t('diag_review.empty_title') || 'All caught up!'}
          </h3>
          <p className="text-sm text-gray-500 dark:text-slate-400 max-w-md">
            {t('diag_review.empty_description') || 'All diagnostic publications have been matched to buildings.'}
          </p>
        </div>
      )}

      {/* Publication cards */}
      {!isLoading && !isError && publications && publications.length > 0 && (
        <div className="space-y-4" data-testid="diag-review-list">
          {publications.map((pub) => (
            <UnmatchedPublicationCard key={pub.id} publication={pub} t={t} queryClient={queryClient} />
          ))}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Single publication card with matching UI                            */
/* ------------------------------------------------------------------ */

function UnmatchedPublicationCard({
  publication: pub,
  t,
  queryClient,
}: {
  publication: DiagnosticPublication;
  t: (key: string) => string;
  queryClient: ReturnType<typeof useQueryClient>;
}) {
  const [matchMode, setMatchMode] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedBuilding, setSelectedBuilding] = useState<Building | null>(null);
  const [matchSuccess, setMatchSuccess] = useState(false);

  const formattedDate = new Date(pub.published_at).toLocaleDateString();

  /* ---- building search ---- */
  const { data: searchResults, isFetching: isSearching } = useQuery({
    queryKey: ['buildings', 'search', searchTerm],
    queryFn: () => buildingsApi.list({ search: searchTerm, size: 8 }),
    enabled: matchMode && searchTerm.length >= 2,
  });

  /* ---- match mutation ---- */
  const matchMutation = useMutation({
    mutationFn: (buildingId: string) => diagnosticReviewApi.matchToBuilding(pub.id, buildingId),
    onSuccess: () => {
      setMatchSuccess(true);
      setMatchMode(false);
      setSelectedBuilding(null);
      setSearchTerm('');
      queryClient.invalidateQueries({ queryKey: ['diagnostic-publications', 'unmatched'] });
    },
  });

  const handleMatch = useCallback(() => {
    if (selectedBuilding) {
      matchMutation.mutate(selectedBuilding.id);
    }
  }, [selectedBuilding, matchMutation]);

  if (matchSuccess) {
    return (
      <div
        className="border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/20 rounded-xl p-6"
        data-testid={`diag-review-card-${pub.id}`}
      >
        <div className="flex items-center gap-3">
          <CheckCircle2 className="w-5 h-5 text-green-600 dark:text-green-400" />
          <span className="text-sm font-medium text-green-700 dark:text-green-400">
            {t('diag_review.match_success') || 'Successfully matched to building'}
          </span>
        </div>
      </div>
    );
  }

  return (
    <div
      className="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-gray-200 dark:border-slate-700 p-6 space-y-4"
      data-testid={`diag-review-card-${pub.id}`}
    >
      {/* Top row: badges + date */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span
            className={cn(
              'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
              MISSION_TYPE_STYLES[pub.mission_type] || DEFAULT_BADGE,
            )}
            data-testid="diag-review-mission-type"
          >
            {t(`diag_pub.mission_${pub.mission_type}`) || pub.mission_type}
          </span>
          <span
            className="inline-block px-2 py-0.5 text-xs font-medium rounded-full bg-slate-100 text-slate-700 dark:bg-slate-600 dark:text-slate-200"
            data-testid="diag-review-source"
          >
            {pub.source_system}
          </span>
          <span
            className={cn(
              'inline-block px-2 py-0.5 text-xs font-medium rounded-full',
              MATCH_STATE_STYLES[pub.match_state] || DEFAULT_BADGE,
            )}
            data-testid="diag-review-match-state"
          >
            {t(`diag_pub.match_${pub.match_state}`) || pub.match_state}
          </span>
        </div>
        <span className="text-xs text-gray-500 dark:text-slate-400">{formattedDate}</span>
      </div>

      {/* Building identifiers */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3" data-testid="diag-review-identifiers">
        {pub.match_key && (
          <div className="flex items-center gap-2 text-sm text-gray-700 dark:text-slate-300">
            <Building2 className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span className="font-medium">{pub.match_key_type || 'Key'}:</span>
            <span className="font-mono text-xs">{pub.match_key}</span>
          </div>
        )}
      </div>

      {/* Structured summary preview */}
      {pub.structured_summary && (
        <div className="text-sm text-gray-700 dark:text-slate-300 space-y-1" data-testid="diag-review-summary">
          {pub.structured_summary.pollutants_found != null && (
            <p>
              <span className="font-medium">{t('diag_pub.pollutants_found') || 'Pollutants found'}:</span>{' '}
              {String(pub.structured_summary.pollutants_found)}
            </p>
          )}
          {pub.structured_summary.fach_urgency != null && (
            <p>
              <span className="font-medium">{t('diag_pub.fach_urgency') || 'FACH urgency'}:</span>{' '}
              {String(pub.structured_summary.fach_urgency)}
            </p>
          )}
          {pub.structured_summary.zones != null && (
            <p>
              <span className="font-medium">{t('diag_pub.zones') || 'Zones'}:</span>{' '}
              {String(pub.structured_summary.zones)}
            </p>
          )}
        </div>
      )}

      {/* PDF link */}
      {pub.report_pdf_url && (
        <a
          href={pub.report_pdf_url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-sm text-indigo-600 dark:text-indigo-400 hover:underline"
          data-testid="diag-review-pdf-link"
        >
          <FileText className="w-4 h-4" />
          {t('diag_pub.download_pdf') || 'Download PDF'}
        </a>
      )}

      {/* Match action area */}
      {!matchMode ? (
        <button
          onClick={() => setMatchMode(true)}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 dark:bg-indigo-500 dark:hover:bg-indigo-600 rounded-lg transition-colors"
          data-testid="diag-review-match-btn"
        >
          <Link2 className="w-4 h-4" />
          {t('diag_review.match_to_building') || 'Match to building'}
        </button>
      ) : (
        <div
          className="border border-indigo-200 dark:border-indigo-800 bg-indigo-50 dark:bg-indigo-900/20 rounded-lg p-4 space-y-3"
          data-testid="diag-review-match-panel"
        >
          <div className="flex items-center justify-between">
            <h4 className="text-sm font-medium text-gray-900 dark:text-white">
              {t('diag_review.select_building') || 'Select a building'}
            </h4>
            <button
              onClick={() => {
                setMatchMode(false);
                setSearchTerm('');
                setSelectedBuilding(null);
              }}
              className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-slate-300"
              data-testid="diag-review-match-cancel"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Search input */}
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setSelectedBuilding(null);
              }}
              placeholder={t('diag_review.search_placeholder') || 'Search by address, EGID, or city...'}
              className="w-full pl-10 pr-4 py-2 text-sm border border-gray-300 dark:border-slate-600 rounded-lg bg-white dark:bg-slate-700 text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              data-testid="diag-review-building-search"
            />
            {isSearching && (
              <Loader2 className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 animate-spin text-indigo-500" />
            )}
          </div>

          {/* Search results */}
          {searchResults && searchResults.items && searchResults.items.length > 0 && !selectedBuilding && (
            <ul
              className="max-h-48 overflow-y-auto space-y-1 border border-gray-200 dark:border-slate-600 rounded-lg"
              data-testid="diag-review-search-results"
            >
              {searchResults.items.map((b) => (
                <li key={b.id}>
                  <button
                    onClick={() => setSelectedBuilding(b)}
                    className="w-full text-left px-3 py-2 text-sm hover:bg-indigo-50 dark:hover:bg-indigo-900/30 transition-colors flex items-center gap-2"
                    data-testid={`diag-review-building-option-${b.id}`}
                  >
                    <MapPin className="w-4 h-4 text-gray-400 flex-shrink-0" />
                    <div>
                      <span className="font-medium text-gray-900 dark:text-white">{b.address}</span>
                      <span className="ml-2 text-xs text-gray-500 dark:text-slate-400">
                        {b.postal_code} {b.city}
                      </span>
                      {b.egid && (
                        <span className="ml-2 text-xs font-mono text-gray-400 dark:text-slate-500">EGID: {b.egid}</span>
                      )}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {/* No results */}
          {searchResults && searchResults.items && searchResults.items.length === 0 && searchTerm.length >= 2 && (
            <p className="text-sm text-gray-500 dark:text-slate-400" data-testid="diag-review-no-results">
              {t('diag_review.no_buildings_found') || 'No buildings found.'}
            </p>
          )}

          {/* Selected building */}
          {selectedBuilding && (
            <div
              className="flex items-center justify-between p-3 bg-white dark:bg-slate-700 border border-gray-200 dark:border-slate-600 rounded-lg"
              data-testid="diag-review-selected-building"
            >
              <div className="flex items-center gap-2">
                <Building2 className="w-4 h-4 text-indigo-500" />
                <span className="text-sm font-medium text-gray-900 dark:text-white">{selectedBuilding.address}</span>
                <span className="text-xs text-gray-500 dark:text-slate-400">
                  {selectedBuilding.postal_code} {selectedBuilding.city}
                </span>
              </div>
              <button
                onClick={() => setSelectedBuilding(null)}
                className="p-1 text-gray-400 hover:text-gray-600 dark:hover:text-slate-300"
                data-testid="diag-review-clear-selection"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Confirm match */}
          <div className="flex items-center gap-3">
            <button
              onClick={handleMatch}
              disabled={!selectedBuilding || matchMutation.isPending}
              className="flex items-center gap-2 px-4 py-2 text-sm font-medium text-white bg-green-600 hover:bg-green-700 dark:bg-green-500 dark:hover:bg-green-600 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              data-testid="diag-review-confirm-match"
            >
              {matchMutation.isPending ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <CheckCircle2 className="w-4 h-4" />
              )}
              {t('diag_review.confirm_match') || 'Confirm match'}
            </button>
            {matchMutation.isError && (
              <span className="text-sm text-red-600 dark:text-red-400" data-testid="diag-review-match-error">
                {t('diag_review.match_error') || 'Match failed. Please try again.'}
              </span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
