import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { financialEntriesApi } from '@/api/financialEntries';
import type { FinancialEntryRead } from '@/api/financialEntries';
import { buildingsApi } from '@/api/buildings';
import type { Building } from '@/types';
import {
  Wallet,
  Loader2,
  TrendingUp,
  TrendingDown,
  DollarSign,
  FileText,
  Inbox,
  ChevronDown,
} from 'lucide-react';
import { cn } from '@/utils/formatters';

const ENTRY_TYPE_COLORS: Record<string, string> = {
  expense: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  income: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
};

const STATUS_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  recorded: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  validated: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  cancelled: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500',
};

function formatCHF(amount: number): string {
  return new Intl.NumberFormat('fr-CH', { style: 'currency', currency: 'CHF' }).format(amount);
}

function formatDate(d: string | null): string {
  if (!d) return '-';
  try {
    return new Date(d).toLocaleDateString('fr-CH');
  } catch {
    return '-';
  }
}

export default function Finance() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const currentYear = new Date().getFullYear();

  const [filterEntryType, setFilterEntryType] = useState<string>('');
  const [filterCategory, setFilterCategory] = useState<string>('');

  const { data: summary, isLoading: summaryLoading } = useQuery({
    queryKey: ['financial-summary', currentYear],
    queryFn: () => financialEntriesApi.summary({ fiscal_year: currentYear }),
  });

  const { data: entries, isLoading: entriesLoading } = useQuery({
    queryKey: ['financial-entries', filterEntryType, filterCategory],
    queryFn: () =>
      financialEntriesApi.list({
        entry_type: filterEntryType || undefined,
        category: filterCategory || undefined,
        limit: 100,
      }),
  });

  const { data: buildingsData } = useQuery({
    queryKey: ['buildings-list-mini'],
    queryFn: () => buildingsApi.list({ size: 500 }),
  });

  const buildingMap = useMemo(() => {
    const map = new Map<string, Building>();
    if (buildingsData?.items) {
      for (const b of buildingsData.items) {
        map.set(b.id, b);
      }
    }
    return map;
  }, [buildingsData]);

  const categories = useMemo(() => {
    if (!entries) return [];
    const set = new Set(entries.map((e) => e.category));
    return Array.from(set).sort();
  }, [entries]);

  const isLoading = summaryLoading || entriesLoading;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
          <Wallet className="w-6 h-6 text-red-600 dark:text-red-400" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            {t('finance.title') || 'Finance'}
          </h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            {t('finance.subtitle') || 'Vue consolidee des ecritures financieres'}
          </p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <SummaryCard
          icon={<DollarSign className="w-5 h-5" />}
          label={t('finance.total_expenses') || 'Depenses totales'}
          value={summary ? formatCHF(summary.total_expenses) : '-'}
          color="text-red-600 dark:text-red-400"
          bgColor="bg-red-50 dark:bg-red-900/20"
          loading={summaryLoading}
        />
        <SummaryCard
          icon={<TrendingUp className="w-5 h-5" />}
          label={t('finance.total_income') || 'Revenus totaux'}
          value={summary ? formatCHF(summary.total_income) : '-'}
          color="text-green-600 dark:text-green-400"
          bgColor="bg-green-50 dark:bg-green-900/20"
          loading={summaryLoading}
        />
        <SummaryCard
          icon={<TrendingDown className="w-5 h-5" />}
          label={t('finance.net') || 'Solde net'}
          value={summary ? formatCHF(summary.net) : '-'}
          color={summary && summary.net >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'}
          bgColor="bg-gray-50 dark:bg-gray-800/50"
          loading={summaryLoading}
        />
        <SummaryCard
          icon={<FileText className="w-5 h-5" />}
          label={t('finance.entry_count') || 'Ecritures'}
          value={summary ? String(summary.entry_count) : '-'}
          color="text-blue-600 dark:text-blue-400"
          bgColor="bg-blue-50 dark:bg-blue-900/20"
          loading={summaryLoading}
        />
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <select
            value={filterEntryType}
            onChange={(e) => setFilterEntryType(e.target.value)}
            className="appearance-none pl-3 pr-8 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-red-500 focus:border-red-500"
          >
            <option value="">{t('finance.all_types') || 'Tous les types'}</option>
            <option value="expense">{t('finance.expense') || 'Depense'}</option>
            <option value="income">{t('finance.income') || 'Revenu'}</option>
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
        <div className="relative">
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="appearance-none pl-3 pr-8 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-red-500 focus:border-red-500"
          >
            <option value="">{t('finance.all_categories') || 'Toutes les categories'}</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>
                {cat.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
        {(filterEntryType || filterCategory) && (
          <button
            onClick={() => {
              setFilterEntryType('');
              setFilterCategory('');
            }}
            className="px-3 py-2 text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
          >
            {t('form.clear') || 'Effacer'}
          </button>
        )}
      </div>

      {/* Table */}
      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="w-8 h-8 animate-spin text-red-600" />
        </div>
      ) : !entries || entries.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
          <Inbox className="w-12 h-12 mb-3 opacity-50" />
          <p className="text-lg font-medium">{t('finance.empty') || 'Aucune ecriture financiere'}</p>
          <p className="text-sm mt-1">
            {t('finance.empty_hint') || 'Les ecritures apparaitront ici une fois creees'}
          </p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('finance.col_date') || 'Date'}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('finance.col_type') || 'Type'}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('finance.col_category') || 'Categorie'}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('finance.col_building') || 'Batiment'}
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('finance.col_amount') || 'Montant'}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('finance.col_status') || 'Statut'}
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('finance.col_description') || 'Description'}
                </th>
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
              {entries.map((entry: FinancialEntryRead) => {
                const building = buildingMap.get(entry.building_id);
                return (
                  <tr
                    key={entry.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/buildings/${entry.building_id}`)}
                  >
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 whitespace-nowrap">
                      {formatDate(entry.entry_date)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={cn(
                          'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                          ENTRY_TYPE_COLORS[entry.entry_type] || '',
                        )}
                      >
                        {entry.entry_type === 'expense'
                          ? t('finance.expense') || 'Depense'
                          : t('finance.income') || 'Revenu'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 whitespace-nowrap">
                      {entry.category.replace(/_/g, ' ')}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 whitespace-nowrap">
                      {building ? building.address || '-' : '-'}
                    </td>
                    <td
                      className={cn(
                        'px-4 py-3 text-sm font-medium whitespace-nowrap text-right',
                        entry.entry_type === 'expense'
                          ? 'text-red-600 dark:text-red-400'
                          : 'text-green-600 dark:text-green-400',
                      )}
                    >
                      {entry.entry_type === 'expense' ? '-' : '+'}
                      {formatCHF(entry.amount_chf)}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={cn(
                          'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                          STATUS_COLORS[entry.status] || STATUS_COLORS.recorded,
                        )}
                      >
                        {entry.status}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 max-w-xs truncate">
                      {entry.description || '-'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function SummaryCard({
  icon,
  label,
  value,
  color,
  bgColor,
  loading,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  color: string;
  bgColor: string;
  loading: boolean;
}) {
  return (
    <div className={cn('rounded-xl p-4 border border-gray-200 dark:border-gray-700', bgColor)}>
      <div className="flex items-center gap-2 mb-2">
        <span className={color}>{icon}</span>
        <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          {label}
        </span>
      </div>
      {loading ? (
        <div className="h-8 flex items-center">
          <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
        </div>
      ) : (
        <p className={cn('text-xl font-bold', color)}>{value}</p>
      )}
    </div>
  );
}
