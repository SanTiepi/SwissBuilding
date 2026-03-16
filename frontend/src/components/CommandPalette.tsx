import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Search,
  Building2,
  FileText,
  X,
  ArrowRight,
  Loader2,
  Stethoscope,
  Clock,
  Eye,
  CheckCircle2,
  CalendarClock,
  Map,
  ScanEye,
} from 'lucide-react';
import { useTranslation } from '@/i18n';
import { buildingsApi } from '@/api/buildings';
import { searchApi } from '@/api/search';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { cn } from '@/utils/formatters';
import { SearchEvidencePreview } from '@/components/SearchEvidencePreview';
import type { Building } from '@/types';

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
}

interface SearchResult {
  id: string;
  type: 'building' | 'document' | 'diagnostic';
  title: string;
  subtitle: string;
  path: string;
}

interface RecentBuilding {
  id: string;
  title: string;
  subtitle: string;
}

type TypeFilter = 'all' | 'buildings' | 'diagnostics' | 'documents';

const GROUP_ORDER = ['buildings', 'diagnostics', 'documents'] as const;

const GROUP_CONFIG = {
  buildings: {
    icon: Building2,
    labelKey: 'search.filter_buildings' as const,
    iconBg: 'bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400',
    headerColor: 'text-emerald-700 dark:text-emerald-400',
  },
  diagnostics: {
    icon: Stethoscope,
    labelKey: 'search.filter_diagnostics' as const,
    iconBg: 'bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400',
    headerColor: 'text-blue-700 dark:text-blue-400',
  },
  documents: {
    icon: FileText,
    labelKey: 'search.filter_documents' as const,
    iconBg: 'bg-amber-50 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400',
    headerColor: 'text-amber-700 dark:text-amber-400',
  },
} as const;

const TYPE_TO_GROUP: Record<SearchResult['type'], (typeof GROUP_ORDER)[number]> = {
  building: 'buildings',
  diagnostic: 'diagnostics',
  document: 'documents',
};

const RECENT_BUILDINGS_KEY = 'swissbuildingos-recent-buildings';
const MAX_RECENT = 5;

function getRecentBuildings(): RecentBuilding[] {
  try {
    const raw = localStorage.getItem(RECENT_BUILDINGS_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as RecentBuilding[];
      return parsed.slice(0, MAX_RECENT);
    }
  } catch {
    // ignore
  }
  return [];
}

function addRecentBuilding(building: RecentBuilding): void {
  try {
    const existing = getRecentBuildings().filter((b) => b.id !== building.id);
    const updated = [building, ...existing].slice(0, MAX_RECENT);
    localStorage.setItem(RECENT_BUILDINGS_KEY, JSON.stringify(updated));
  } catch {
    // ignore
  }
}

const QUICK_ACTIONS = [
  { key: 'dossier', labelKey: 'search.view_dossier', icon: Eye, path: (id: string) => `/buildings/${id}` },
  {
    key: 'readiness',
    labelKey: 'search.view_readiness',
    icon: CheckCircle2,
    path: (id: string) => `/buildings/${id}/readiness`,
  },
  {
    key: 'timeline',
    labelKey: 'search.view_timeline',
    icon: CalendarClock,
    path: (id: string) => `/buildings/${id}/timeline`,
  },
  { key: 'plans', labelKey: 'search.view_plans', icon: Map, path: (id: string) => `/buildings/${id}/plans` },
  {
    key: 'field_observations',
    labelKey: 'search.view_field_observations',
    icon: ScanEye,
    path: (id: string) => `/buildings/${id}/field-observations`,
  },
] as const;

export function CommandPalette({ open, onClose }: CommandPaletteProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);

  const [query, setQuery] = useState('');
  const debouncedQuery = useDebouncedValue(query, 250);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [typeFilter, setTypeFilter] = useState<TypeFilter>('all');
  const [quickActionsOpen, setQuickActionsOpen] = useState(false);
  const [quickActionIndex, setQuickActionIndex] = useState(0);

  const recentBuildings = useMemo(() => (open ? getRecentBuildings() : []), [open]);
  const showRecents = debouncedQuery.length < 2 && recentBuildings.length > 0;

  // Group results by entity type
  const grouped = useMemo(() => {
    const groups: Record<string, SearchResult[]> = {
      buildings: [],
      diagnostics: [],
      documents: [],
    };
    for (const r of results) {
      const group = TYPE_TO_GROUP[r.type];
      groups[group].push(r);
    }
    return groups;
  }, [results]);

  // Build flat list for keyboard navigation across groups
  const flatItems = useMemo(() => {
    const items: SearchResult[] = [];
    for (const key of GROUP_ORDER) {
      const group = grouped[key];
      if (group.length > 0) {
        items.push(...group);
      }
    }
    return items;
  }, [grouped]);

  // Selected result for evidence preview and quick actions
  const selectedResult = flatItems[selectedIndex] ?? null;
  const selectedIsBuilding = selectedResult?.type === 'building';

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setQuery('');
      setResults([]);
      setSearchError(null);
      setSelectedIndex(0);
      setTypeFilter('all');
      setQuickActionsOpen(false);
      setQuickActionIndex(0);
      requestAnimationFrame(() => inputRef.current?.focus());
    }
  }, [open]);

  // Search when debounced query or filter changes
  useEffect(() => {
    if (!debouncedQuery || debouncedQuery.length < 2) {
      setResults([]);
      setSearchError(null);
      return;
    }

    let cancelled = false;
    const doSearch = async () => {
      setIsSearching(true);
      setSearchError(null);
      try {
        const apiType = typeFilter === 'all' ? undefined : typeFilter;
        const searchData = await searchApi.search(debouncedQuery, apiType, 10);
        if (cancelled) return;

        const crossResults: SearchResult[] = searchData.results.map((r) => ({
          id: r.id,
          type:
            r.index === 'buildings'
              ? ('building' as const)
              : r.index === 'diagnostics'
                ? ('diagnostic' as const)
                : ('document' as const),
          title: r.title,
          subtitle: r.subtitle,
          path: r.url,
        }));

        setResults(crossResults);
        setSearchError(null);
        setSelectedIndex(0);
        setQuickActionsOpen(false);
      } catch {
        // Fallback to buildings-only search if Meilisearch is unavailable
        try {
          const buildingsData = await buildingsApi.list({ search: debouncedQuery, size: 8 });
          if (cancelled) return;

          const buildingResults: SearchResult[] = (buildingsData.items ?? []).map((b: Building) => ({
            id: b.id,
            type: 'building' as const,
            title: b.address,
            subtitle: `${b.postal_code} ${b.city} (${b.canton})`,
            path: `/buildings/${b.id}`,
          }));

          setResults(buildingResults);
          setSearchError(null);
          setSelectedIndex(0);
          setQuickActionsOpen(false);
        } catch {
          if (!cancelled) {
            setResults([]);
            setSearchError(t('search.load_error') || t('app.loading_error') || 'Unable to load search right now.');
          }
        }
      } finally {
        if (!cancelled) setIsSearching(false);
      }
    };

    doSearch();
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery, t, typeFilter]);

  // Navigate to result
  const goToResult = useCallback(
    (result: SearchResult) => {
      if (result.type === 'building') {
        addRecentBuilding({ id: result.id, title: result.title, subtitle: result.subtitle });
      }
      onClose();
      navigate(result.path);
    },
    [navigate, onClose],
  );

  const goToRecentBuilding = useCallback(
    (building: RecentBuilding) => {
      addRecentBuilding(building);
      onClose();
      navigate(`/buildings/${building.id}`);
    },
    [navigate, onClose],
  );

  const goToQuickAction = useCallback(
    (buildingId: string, actionPath: (id: string) => string) => {
      onClose();
      navigate(actionPath(buildingId));
    },
    [navigate, onClose],
  );

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (quickActionsOpen && selectedIsBuilding && selectedResult) {
        switch (e.key) {
          case 'ArrowDown':
            e.preventDefault();
            setQuickActionIndex((prev) => Math.min(prev + 1, QUICK_ACTIONS.length - 1));
            return;
          case 'ArrowUp':
            e.preventDefault();
            setQuickActionIndex((prev) => Math.max(prev - 1, 0));
            return;
          case 'Enter':
            e.preventDefault();
            goToQuickAction(selectedResult.id, QUICK_ACTIONS[quickActionIndex].path);
            return;
          case 'Tab':
            // Exit quick-actions sub-mode; allow normal Tab to proceed
            setQuickActionsOpen(false);
            setQuickActionIndex(0);
            return;
          case 'Escape':
            e.preventDefault();
            setQuickActionsOpen(false);
            setQuickActionIndex(0);
            onClose();
            return;
        }
        return;
      }

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          if (showRecents) {
            setSelectedIndex((prev) => Math.min(prev + 1, recentBuildings.length - 1));
          } else {
            setSelectedIndex((prev) => Math.min(prev + 1, flatItems.length - 1));
          }
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (showRecents && recentBuildings[selectedIndex]) {
            goToRecentBuilding(recentBuildings[selectedIndex]);
          } else if (flatItems[selectedIndex]) {
            goToResult(flatItems[selectedIndex]);
          }
          break;
        case 'Tab':
          if (selectedIsBuilding && flatItems.length > 0) {
            e.preventDefault();
            setQuickActionsOpen(true);
            setQuickActionIndex(0);
          }
          // When no building is selected, allow default Tab behavior
          // so keyboard users can reach close button and filter pills
          break;
        case 'Escape':
          e.preventDefault();
          onClose();
          break;
      }
    },
    [
      flatItems,
      selectedIndex,
      goToResult,
      onClose,
      quickActionsOpen,
      quickActionIndex,
      selectedIsBuilding,
      selectedResult,
      goToQuickAction,
      showRecents,
      recentBuildings,
      goToRecentBuilding,
    ],
  );

  if (!open) return null;

  // Compute flat index offset for each group
  let runningIndex = 0;

  const filterPills: { key: TypeFilter; labelKey: string }[] = [
    { key: 'all', labelKey: 'search.filter_all' },
    { key: 'buildings', labelKey: 'search.filter_buildings' },
    { key: 'diagnostics', labelKey: 'search.filter_diagnostics' },
    { key: 'documents', labelKey: 'search.filter_documents' },
  ];

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh]">
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" onClick={onClose} aria-hidden="true" />

      {/* Palette container — wider when quick actions / preview shown */}
      <div className="relative flex mx-4 max-w-3xl w-full">
        {/* Main palette */}
        <div
          className={cn(
            'bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden',
            selectedIsBuilding && flatItems.length > 0 ? 'w-[60%]' : 'w-full max-w-lg mx-auto',
          )}
          role="dialog"
          aria-modal="true"
          aria-label={t('nav.search')}
        >
          {/* Search input */}
          <div className="flex items-center px-4 border-b border-slate-200 dark:border-slate-700">
            <Search className="w-5 h-5 text-slate-400 dark:text-slate-500 flex-shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={t('nav.search')}
              className="flex-1 px-3 py-4 text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 bg-transparent border-0 outline-none"
              aria-label={t('nav.search')}
            />
            {isSearching && <Loader2 className="w-4 h-4 text-slate-400 dark:text-slate-500 animate-spin" />}
            <button
              onClick={onClose}
              className="ml-2 p-1 text-slate-400 dark:text-slate-500 hover:text-slate-600 dark:hover:text-slate-300"
              aria-label={t('form.close')}
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Filter pills */}
          {debouncedQuery.length >= 2 && (
            <div className="flex items-center gap-1.5 px-4 py-2 border-b border-slate-100 dark:border-slate-700">
              {filterPills.map((pill) => (
                <button
                  key={pill.key}
                  onClick={() => setTypeFilter(pill.key)}
                  className={cn(
                    'px-2.5 py-1 text-xs font-medium rounded-full transition-colors',
                    typeFilter === pill.key
                      ? 'bg-slate-900 dark:bg-white text-white dark:text-slate-900'
                      : 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600',
                  )}
                >
                  {t(pill.labelKey) || pill.key}
                </button>
              ))}
            </div>
          )}

          {/* Result count */}
          {debouncedQuery.length >= 2 && !isSearching && !searchError && (
            <div className="px-4 py-1.5 text-xs text-slate-400 dark:text-slate-500">
              {results.length > 0
                ? `${results.length} ${t('search.results') || 'results'}`
                : t('search.no_results') || 'No results'}
            </div>
          )}

          {/* Recent buildings (empty query) */}
          {showRecents && (
            <div className="py-1">
              <div className="flex items-center gap-2 px-4 py-1.5 mt-1">
                <Clock className="w-3.5 h-3.5 text-slate-400 dark:text-slate-500" />
                <span className="text-xs font-semibold uppercase tracking-wide text-slate-400 dark:text-slate-500">
                  {t('search.recent_buildings')}
                </span>
              </div>
              <ul>
                {recentBuildings.map((building, idx) => (
                  <li
                    key={building.id}
                    role="option"
                    aria-selected={idx === selectedIndex}
                    className={cn(
                      'flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors',
                      idx === selectedIndex
                        ? 'bg-slate-100 dark:bg-slate-700'
                        : 'hover:bg-slate-50 dark:hover:bg-slate-700/50',
                    )}
                    onClick={() => goToRecentBuilding(building)}
                    onMouseEnter={() => setSelectedIndex(idx)}
                  >
                    <div className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400">
                      <Building2 className="w-4 h-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{building.title}</p>
                      <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{building.subtitle}</p>
                    </div>
                    <ArrowRight className="w-4 h-4 text-slate-300 dark:text-slate-600 flex-shrink-0" />
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Grouped results */}
          {flatItems.length > 0 && (
            <ul className="max-h-80 overflow-y-auto py-1" role="listbox">
              {GROUP_ORDER.map((groupKey) => {
                const items = grouped[groupKey];
                if (items.length === 0) return null;

                const config = GROUP_CONFIG[groupKey];
                const GroupIcon = config.icon;
                const groupStartIndex = runningIndex;
                runningIndex += items.length;

                return (
                  <li key={groupKey} role="group" aria-label={t(config.labelKey) || groupKey}>
                    {/* Section header */}
                    <div className="flex items-center gap-2 px-4 py-1.5 mt-1">
                      <GroupIcon className={cn('w-3.5 h-3.5', config.headerColor)} />
                      <span className={cn('text-xs font-semibold uppercase tracking-wide', config.headerColor)}>
                        {t(config.labelKey) || groupKey}
                      </span>
                      <span className="text-xs text-slate-400 dark:text-slate-500">({items.length})</span>
                    </div>

                    {/* Items */}
                    <ul>
                      {items.map((result, idx) => {
                        const flatIdx = groupStartIndex + idx;
                        const Icon = config.icon;
                        return (
                          <li
                            key={result.id}
                            role="option"
                            aria-selected={flatIdx === selectedIndex}
                            className={cn(
                              'flex items-center gap-3 px-4 py-2.5 cursor-pointer transition-colors',
                              flatIdx === selectedIndex
                                ? 'bg-slate-100 dark:bg-slate-700'
                                : 'hover:bg-slate-50 dark:hover:bg-slate-700/50',
                            )}
                            onClick={() => goToResult(result)}
                            onMouseEnter={() => {
                              setSelectedIndex(flatIdx);
                              setQuickActionsOpen(false);
                            }}
                          >
                            <div
                              className={cn(
                                'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
                                config.iconBg,
                              )}
                            >
                              <Icon className="w-4 h-4" />
                            </div>
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium text-slate-900 dark:text-white truncate">
                                {result.title}
                              </p>
                              <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{result.subtitle}</p>
                            </div>
                            <ArrowRight className="w-4 h-4 text-slate-300 dark:text-slate-600 flex-shrink-0" />
                          </li>
                        );
                      })}
                    </ul>
                  </li>
                );
              })}
            </ul>
          )}

          {/* Empty state */}
          {query.length >= 2 && !isSearching && !searchError && results.length === 0 && (
            <div className="py-8 text-center">
              <p className="text-sm text-slate-500 dark:text-slate-400">
                {t('search.no_results') || t('form.no_results')}
              </p>
            </div>
          )}

          {query.length >= 2 && !isSearching && searchError && (
            <div className="py-8 text-center px-6">
              <p className="text-sm text-red-600 dark:text-red-400">{searchError}</p>
            </div>
          )}

          {/* Hint (no query, no recents) */}
          {query.length < 2 && !showRecents && (
            <div className="py-8 text-center">
              <p className="text-sm text-slate-400 dark:text-slate-500">{t('form.search')}</p>
            </div>
          )}

          {/* Footer with keyboard hints */}
          <div className="flex items-center justify-between px-4 py-2 border-t border-slate-100 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-700/50">
            <div className="flex items-center gap-3 text-xs text-slate-400 dark:text-slate-500">
              <span>
                <kbd className="px-1.5 py-0.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded text-[10px] font-mono">
                  Esc
                </kbd>{' '}
                {t('search.press_esc')}
              </span>
              <span>
                <kbd className="px-1.5 py-0.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded text-[10px] font-mono">
                  ↵
                </kbd>{' '}
                {t('search.press_enter')}
              </span>
              <span>
                <kbd className="px-1.5 py-0.5 bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded text-[10px] font-mono">
                  Tab
                </kbd>{' '}
                {t('search.press_tab')}
              </span>
            </div>
          </div>
        </div>

        {/* Right side panel: quick actions + evidence preview */}
        {selectedIsBuilding && flatItems.length > 0 && selectedResult && (
          <div className="w-[40%] ml-2 bg-white dark:bg-slate-800 rounded-2xl shadow-2xl border border-slate-200 dark:border-slate-700 overflow-hidden flex flex-col">
            {/* Quick actions */}
            <div className="p-3 border-b border-slate-100 dark:border-slate-700">
              <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wide mb-2">
                {t('search.quick_actions')}
              </p>
              <ul className="space-y-0.5">
                {QUICK_ACTIONS.map((action, idx) => {
                  const ActionIcon = action.icon;
                  return (
                    <li
                      key={action.key}
                      className={cn(
                        'flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition-colors text-sm',
                        quickActionsOpen && idx === quickActionIndex
                          ? 'bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white'
                          : 'text-slate-600 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700/50',
                      )}
                      onClick={() => goToQuickAction(selectedResult.id, action.path)}
                      onMouseEnter={() => {
                        setQuickActionsOpen(true);
                        setQuickActionIndex(idx);
                      }}
                    >
                      <ActionIcon className="w-3.5 h-3.5 flex-shrink-0" />
                      <span className="text-xs">{t(action.labelKey)}</span>
                    </li>
                  );
                })}
              </ul>
            </div>

            {/* Evidence preview */}
            <SearchEvidencePreview buildingId={selectedResult.id} />
          </div>
        )}
      </div>
    </div>
  );
}
