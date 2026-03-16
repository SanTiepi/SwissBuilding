import { useState, useMemo, memo, type ReactNode } from 'react';
import {
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
} from 'lucide-react';
import { useTranslation } from '@/i18n';
import { cn } from '@/utils/formatters';

export interface Column<T> {
  key: string;
  header: string;
  sortable?: boolean;
  render?: (row: T) => ReactNode;
}

interface PaginationConfig {
  page: number;
  size: number;
  total: number;
  onChange: (page: number) => void;
}

interface DataTableProps<T> {
  columns: Column<T>[];
  data: T[];
  pagination?: PaginationConfig;
  onSort?: (key: string, dir: 'asc' | 'desc') => void;
  isLoading?: boolean;
  onRowClick?: (row: T, index: number) => void;
}

function DataTableInner<T extends object>({
  columns,
  data,
  pagination,
  onSort,
  isLoading = false,
  onRowClick,
}: DataTableProps<T>) {
  const { t } = useTranslation();
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('asc');
  // Reset focusedRow when data changes by deriving a stable identity token
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const dataToken = useMemo(() => ({}), [data]);
  const [focusState, setFocusState] = useState<{ token: object; index: number }>({ token: dataToken, index: -1 });
  const focusedRow = focusState.token === dataToken ? focusState.index : -1;
  const setFocusedRow = (indexOrFn: number | ((prev: number) => number)) => {
    setFocusState((prev) => {
      const prevIndex = prev.token === dataToken ? prev.index : -1;
      const newIndex = typeof indexOrFn === 'function' ? indexOrFn(prevIndex) : indexOrFn;
      return { token: dataToken, index: newIndex };
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!data.length) return;
    switch (e.key) {
      case 'ArrowDown':
        e.preventDefault();
        setFocusedRow((prev) => Math.min(prev + 1, data.length - 1));
        break;
      case 'ArrowUp':
        e.preventDefault();
        setFocusedRow((prev) => Math.max(prev - 1, 0));
        break;
      case 'Enter':
        if (focusedRow >= 0 && onRowClick) {
          onRowClick(data[focusedRow], focusedRow);
        }
        break;
    }
  };

  const handleSort = (key: string) => {
    const newDir = sortKey === key && sortDir === 'asc' ? 'desc' : 'asc';
    setSortKey(key);
    setSortDir(newDir);
    onSort?.(key, newDir);
  };

  const totalPages = pagination ? Math.max(1, Math.ceil(pagination.total / pagination.size)) : 1;

  // Skeleton rows for loading state
  const skeletonRows = Array.from({ length: 5 });

  return (
    <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full min-w-[600px] text-sm">
          {/* Header */}
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-700">
              {columns.map((col) => (
                <th
                  key={col.key}
                  role="columnheader"
                  className={cn(
                    'px-4 py-3 text-left text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider',
                    col.sortable && 'cursor-pointer select-none hover:text-slate-700 dark:hover:text-slate-200',
                  )}
                  onClick={() => col.sortable && handleSort(col.key)}
                  aria-sort={
                    col.sortable && sortKey === col.key
                      ? sortDir === 'asc'
                        ? 'ascending'
                        : 'descending'
                      : col.sortable
                        ? 'none'
                        : undefined
                  }
                >
                  <div className="flex items-center gap-1.5">
                    <span>{col.header}</span>
                    {col.sortable && (
                      <span className="flex-shrink-0" aria-label={`${t('form.sort')} ${col.header}`}>
                        {sortKey === col.key ? (
                          sortDir === 'asc' ? (
                            <ChevronUp className="w-3.5 h-3.5" />
                          ) : (
                            <ChevronDown className="w-3.5 h-3.5" />
                          )
                        ) : (
                          <ChevronsUpDown className="w-3.5 h-3.5 text-slate-300 dark:text-slate-600" />
                        )}
                      </span>
                    )}
                  </div>
                </th>
              ))}
            </tr>
          </thead>

          {/* Body */}
          <tbody
            className="divide-y divide-slate-100 dark:divide-slate-700"
            tabIndex={0}
            role="grid"
            onKeyDown={handleKeyDown}
          >
            {isLoading ? (
              // Loading skeleton
              skeletonRows.map((_, rowIdx) => (
                <tr key={`skeleton-${rowIdx}`}>
                  {columns.map((col) => (
                    <td key={col.key} className="px-4 py-3.5">
                      <div className="h-4 bg-slate-200 dark:bg-slate-600 rounded animate-pulse w-3/4" />
                    </td>
                  ))}
                </tr>
              ))
            ) : data.length === 0 ? (
              // Empty state
              <tr>
                <td colSpan={columns.length} className="px-4 py-16 text-center text-slate-500 dark:text-slate-400">
                  <p className="text-sm">{t('form.no_results')}</p>
                </td>
              </tr>
            ) : (
              // Data rows
              data.map((row, rowIdx) => (
                <tr
                  key={rowIdx}
                  className={cn(
                    'hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors',
                    onRowClick && 'cursor-pointer',
                    focusedRow === rowIdx && 'bg-slate-100 dark:bg-slate-700 outline outline-2 outline-red-500/50',
                  )}
                  onClick={() => onRowClick?.(row, rowIdx)}
                  role="row"
                  aria-selected={focusedRow === rowIdx}
                >
                  {columns.map((col) => (
                    <td
                      key={col.key}
                      role="gridcell"
                      className="px-4 py-3.5 text-slate-700 dark:text-slate-200 whitespace-nowrap"
                    >
                      {col.render ? col.render(row) : (((row as Record<string, unknown>)[col.key] as ReactNode) ?? '-')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {pagination && pagination.total > 0 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-slate-200 dark:border-slate-700 bg-slate-50/50 dark:bg-slate-700/50">
          {/* Info */}
          <p className="text-xs text-slate-500 dark:text-slate-400">
            {t('form.showing', {
              from: String((pagination.page - 1) * pagination.size + 1),
              to: String(Math.min(pagination.page * pagination.size, pagination.total)),
              total: String(pagination.total),
            })}
          </p>

          {/* Controls */}
          <div className="flex items-center gap-1">
            {/* First */}
            <button
              onClick={() => pagination.onChange(1)}
              disabled={pagination.page <= 1}
              className="p-1.5 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title={t('pagination.first')}
              aria-label={t('pagination.first')}
            >
              <ChevronsLeft className="w-4 h-4" />
            </button>

            {/* Previous */}
            <button
              onClick={() => pagination.onChange(pagination.page - 1)}
              disabled={pagination.page <= 1}
              className="p-1.5 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title={t('pagination.previous')}
              aria-label={t('pagination.previous')}
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            {/* Page indicator */}
            <span className="px-3 py-1 text-xs font-medium text-slate-600 dark:text-slate-300">
              {t('pagination.page', {
                page: String(pagination.page),
                pages: String(totalPages),
              })}
            </span>

            {/* Next */}
            <button
              onClick={() => pagination.onChange(pagination.page + 1)}
              disabled={pagination.page >= totalPages}
              className="p-1.5 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title={t('pagination.next')}
              aria-label={t('pagination.next')}
            >
              <ChevronRight className="w-4 h-4" />
            </button>

            {/* Last */}
            <button
              onClick={() => pagination.onChange(totalPages)}
              disabled={pagination.page >= totalPages}
              className="p-1.5 min-w-[44px] min-h-[44px] flex items-center justify-center rounded-lg text-slate-500 dark:text-slate-400 hover:bg-slate-200 dark:hover:bg-slate-600 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title={t('pagination.last')}
              aria-label={t('pagination.last')}
            >
              <ChevronsRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export const DataTable = memo(DataTableInner) as typeof DataTableInner;
