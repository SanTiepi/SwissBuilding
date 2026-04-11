import { useState, useEffect, useMemo } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import { Search, Building2, Stethoscope, FileText, Loader2, ArrowRight, Filter } from 'lucide-react';
import { useTranslation } from '@/i18n';
import { searchApi } from '@/api/search';
import { cn } from '@/utils/formatters';
import type { SearchResult } from '@/types';

type TabKey = 'all' | 'buildings' | 'diagnostics' | 'documents';

const TABS: { key: TabKey; labelKey: string; icon: typeof Building2 }[] = [
  { key: 'all', labelKey: 'search.filter_all', icon: Search },
  { key: 'buildings', labelKey: 'search.filter_buildings', icon: Building2 },
  { key: 'diagnostics', labelKey: 'search.filter_diagnostics', icon: Stethoscope },
  { key: 'documents', labelKey: 'search.filter_documents', icon: FileText },
];

const ICON_MAP: Record<string, typeof Building2> = {
  buildings: Building2,
  diagnostics: Stethoscope,
  documents: FileText,
};

const ICON_BG: Record<string, string> = {
  buildings: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400',
  diagnostics: 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
  documents: 'bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400',
};

export default function SearchResults() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  const initialQuery = searchParams.get('q') || '';
  const initialTab = (searchParams.get('tab') as TabKey) || 'all';

  const [query, setQuery] = useState(initialQuery);
  const [activeTab, setActiveTab] = useState<TabKey>(initialTab);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);

  // Search when query or tab changes
  useEffect(() => {
    if (!query || query.length < 2) {
      setResults([]);
      return;
    }

    let cancelled = false;
    const doSearch = async () => {
      setIsSearching(true);
      setSearchError(null);
      try {
        const apiType = activeTab === 'all' ? undefined : activeTab;
        const data = await searchApi.search(query, apiType, 50);
        if (!cancelled) {
          setResults(data.results);
        }
      } catch {
        if (!cancelled) {
          setResults([]);
          setSearchError(t('search.load_error') || 'Search failed');
        }
      } finally {
        if (!cancelled) setIsSearching(false);
      }
    };
    doSearch();
    return () => {
      cancelled = true;
    };
  }, [query, activeTab, t]);

  // Sync URL params
  useEffect(() => {
    const params: Record<string, string> = {};
    if (query) params.q = query;
    if (activeTab !== 'all') params.tab = activeTab;
    setSearchParams(params, { replace: true });
  }, [query, activeTab, setSearchParams]);

  // Count per tab
  const tabCounts = useMemo(() => {
    const counts: Record<string, number> = { all: results.length, buildings: 0, diagnostics: 0, documents: 0 };
    for (const r of results) {
      counts[r.index] = (counts[r.index] || 0) + 1;
    }
    return counts;
  }, [results]);

  // Filtered results for current tab
  const filteredResults = useMemo(
    () => (activeTab === 'all' ? results : results.filter((r) => r.index === activeTab)),
    [results, activeTab],
  );

  const handleResultClick = (result: SearchResult) => {
    navigate(result.url);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // trigger re-search by updating the same query (already reactive)
  };

  return (
    <div className="max-w-4xl mx-auto">
      {/* Search header */}
      <form onSubmit={handleSubmit} className="mb-6">
        <div className="flex items-center gap-3 px-4 py-3 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 shadow-sm focus-within:ring-2 focus-within:ring-red-500/30">
          <Search className="w-5 h-5 text-slate-400 dark:text-slate-500 flex-shrink-0" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('nav.search') || 'Search buildings, diagnostics, documents...'}
            className="flex-1 bg-transparent text-base text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 outline-none"
            autoFocus
          />
          {isSearching && <Loader2 className="w-5 h-5 text-slate-400 animate-spin" />}
        </div>
      </form>

      {/* Tabs */}
      <div className="flex items-center gap-1 mb-4 border-b border-slate-200 dark:border-slate-700">
        {TABS.map((tab) => {
          const TabIcon = tab.icon;
          const count = tabCounts[tab.key] ?? 0;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key)}
              className={cn(
                'flex items-center gap-1.5 px-3 py-2.5 text-sm font-medium border-b-2 transition-colors -mb-px',
                activeTab === tab.key
                  ? 'border-red-500 text-red-600 dark:text-red-400'
                  : 'border-transparent text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-300',
              )}
            >
              <TabIcon className="w-4 h-4" />
              <span>{t(tab.labelKey) || tab.key}</span>
              {query.length >= 2 && (
                <span
                  className={cn(
                    'ml-1 px-1.5 py-0.5 text-xs rounded-full',
                    activeTab === tab.key
                      ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400'
                      : 'bg-slate-100 dark:bg-slate-700 text-slate-500 dark:text-slate-400',
                  )}
                >
                  {count}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Results */}
      {isSearching && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-6 h-6 text-slate-400 animate-spin" />
        </div>
      )}

      {!isSearching && searchError && (
        <div className="py-12 text-center">
          <p className="text-sm text-red-600 dark:text-red-400">{searchError}</p>
        </div>
      )}

      {!isSearching && !searchError && query.length >= 2 && filteredResults.length === 0 && (
        <div className="py-12 text-center">
          <Filter className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('search.no_results') || 'No results found'}
          </p>
        </div>
      )}

      {!isSearching && filteredResults.length > 0 && (
        <div className="space-y-2">
          {filteredResults.map((result) => {
            const Icon = ICON_MAP[result.index] ?? FileText;
            const iconBg = ICON_BG[result.index] ?? 'bg-slate-100 dark:bg-slate-700 text-slate-500';
            return (
              <div
                key={`${result.index}-${result.id}`}
                onClick={() => handleResultClick(result)}
                className="flex items-center gap-4 p-4 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 cursor-pointer transition-all hover:shadow-sm group"
              >
                <div className={cn('w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0', iconBg)}>
                  <Icon className="w-5 h-5" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{result.title}</p>
                  <p className="text-xs text-slate-500 dark:text-slate-400 truncate mt-0.5">{result.subtitle}</p>
                </div>
                <span className="text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-wide flex-shrink-0">
                  {result.index}
                </span>
                <ArrowRight className="w-4 h-4 text-slate-300 dark:text-slate-600 group-hover:text-slate-400 dark:group-hover:text-slate-500 flex-shrink-0 transition-colors" />
              </div>
            );
          })}
        </div>
      )}

      {/* Hint when no query */}
      {query.length < 2 && !isSearching && (
        <div className="py-12 text-center">
          <Search className="w-8 h-8 text-slate-300 dark:text-slate-600 mx-auto mb-3" />
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {t('form.search') || 'Type at least 2 characters to search'}
          </p>
        </div>
      )}
    </div>
  );
}
