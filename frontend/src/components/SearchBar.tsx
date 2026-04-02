import { useState, useRef, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Loader2, Building2, Stethoscope, FileText, X } from 'lucide-react';
import { useTranslation } from '@/i18n';
import { searchApi } from '@/api/search';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { cn } from '@/utils/formatters';
import type { SearchResult } from '@/types';

interface SearchBarProps {
  className?: string;
  onOpenFullSearch?: () => void;
}

const ICON_MAP: Record<string, typeof Building2> = {
  buildings: Building2,
  diagnostics: Stethoscope,
  documents: FileText,
};

const ICON_COLORS: Record<string, string> = {
  buildings: 'text-emerald-500',
  diagnostics: 'text-blue-500',
  documents: 'text-amber-500',
};

export function SearchBar({ className, onOpenFullSearch }: SearchBarProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  const [query, setQuery] = useState('');
  const debouncedQuery = useDebouncedValue(query, 250);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setShowDropdown(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Search on debounced query
  useEffect(() => {
    if (!debouncedQuery || debouncedQuery.length < 2) {
      setResults([]);
      return;
    }

    let cancelled = false;
    const doSearch = async () => {
      setIsSearching(true);
      try {
        const data = await searchApi.search(debouncedQuery, undefined, 6);
        if (!cancelled) {
          setResults(data.results);
          setSelectedIndex(0);
          setShowDropdown(true);
        }
      } catch {
        if (!cancelled) setResults([]);
      } finally {
        if (!cancelled) setIsSearching(false);
      }
    };
    doSearch();
    return () => {
      cancelled = true;
    };
  }, [debouncedQuery]);

  const goToResult = useCallback(
    (result: SearchResult) => {
      setShowDropdown(false);
      setQuery('');
      navigate(result.url);
    },
    [navigate],
  );

  const goToFullSearch = useCallback(() => {
    if (onOpenFullSearch) {
      onOpenFullSearch();
    } else {
      navigate(`/search?q=${encodeURIComponent(query)}`);
    }
    setShowDropdown(false);
  }, [navigate, query, onOpenFullSearch]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (!showDropdown || results.length === 0) {
        if (e.key === 'Enter' && query.length >= 2) {
          e.preventDefault();
          goToFullSearch();
        }
        return;
      }
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          e.preventDefault();
          if (results[selectedIndex]) {
            goToResult(results[selectedIndex]);
          }
          break;
        case 'Escape':
          e.preventDefault();
          setShowDropdown(false);
          break;
      }
    },
    [showDropdown, results, selectedIndex, goToResult, goToFullSearch, query],
  );

  return (
    <div ref={containerRef} className={cn('relative', className)}>
      <div className="flex items-center gap-2 px-3 py-2 bg-slate-100 dark:bg-slate-700 rounded-lg border border-slate-200 dark:border-slate-600 focus-within:ring-2 focus-within:ring-red-500/30 focus-within:border-red-400 dark:focus-within:border-red-500 transition-all">
        <Search className="w-4 h-4 text-slate-400 dark:text-slate-500 flex-shrink-0" />
        <input
          ref={inputRef}
          type="text"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            if (e.target.value.length >= 2) setShowDropdown(true);
          }}
          onFocus={() => {
            if (results.length > 0) setShowDropdown(true);
          }}
          onKeyDown={handleKeyDown}
          placeholder={t('nav.search') || 'Search...'}
          className="flex-1 bg-transparent text-sm text-slate-900 dark:text-white placeholder-slate-400 dark:placeholder-slate-500 outline-none min-w-0"
          aria-label={t('nav.search') || 'Search'}
        />
        {isSearching && <Loader2 className="w-4 h-4 text-slate-400 animate-spin flex-shrink-0" />}
        {query && !isSearching && (
          <button
            onClick={() => {
              setQuery('');
              setResults([]);
              setShowDropdown(false);
            }}
            className="p-0.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300"
            aria-label={t('form.clear') || 'Clear'}
          >
            <X className="w-3.5 h-3.5" />
          </button>
        )}
        <kbd className="hidden sm:inline-block px-1.5 py-0.5 text-[10px] font-mono text-slate-400 dark:text-slate-500 bg-white dark:bg-slate-600 border border-slate-200 dark:border-slate-500 rounded">
          ⌘K
        </kbd>
      </div>

      {/* Autocomplete dropdown */}
      {showDropdown && results.length > 0 && (
        <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-slate-800 rounded-lg shadow-xl border border-slate-200 dark:border-slate-700 overflow-hidden z-50">
          <ul role="listbox" className="py-1">
            {results.map((result, idx) => {
              const Icon = ICON_MAP[result.index] ?? FileText;
              const iconColor = ICON_COLORS[result.index] ?? 'text-slate-400';
              return (
                <li
                  key={`${result.index}-${result.id}`}
                  role="option"
                  aria-selected={idx === selectedIndex}
                  className={cn(
                    'flex items-center gap-3 px-3 py-2 cursor-pointer transition-colors',
                    idx === selectedIndex
                      ? 'bg-slate-100 dark:bg-slate-700'
                      : 'hover:bg-slate-50 dark:hover:bg-slate-700/50',
                  )}
                  onClick={() => goToResult(result)}
                  onMouseEnter={() => setSelectedIndex(idx)}
                >
                  <Icon className={cn('w-4 h-4 flex-shrink-0', iconColor)} />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-slate-900 dark:text-white truncate">{result.title}</p>
                    <p className="text-xs text-slate-500 dark:text-slate-400 truncate">{result.subtitle}</p>
                  </div>
                  <span className="text-[10px] text-slate-400 dark:text-slate-500 uppercase tracking-wide flex-shrink-0">
                    {result.index}
                  </span>
                </li>
              );
            })}
          </ul>
          {results.length >= 6 && (
            <button
              onClick={goToFullSearch}
              className="w-full px-3 py-2 text-xs text-center text-red-600 dark:text-red-400 border-t border-slate-100 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-700/50 transition-colors"
            >
              {t('search.view_all_results') || 'View all results →'}
            </button>
          )}
        </div>
      )}
    </div>
  );
}
