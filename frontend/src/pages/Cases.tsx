import { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { useTranslation } from '@/i18n';
import { buildingCasesApi } from '@/api/buildingCases';
import type { BuildingCaseRead } from '@/api/buildingCases';
import { buildingsApi } from '@/api/buildings';
import type { Building } from '@/types';
import {
  Briefcase,
  Loader2,
  Plus,
  ArrowUpDown,
  Inbox,
  ChevronDown,
} from 'lucide-react';
import { cn } from '@/utils/formatters';

const CASE_TYPES = [
  'works',
  'permit',
  'authority_submission',
  'tender',
  'insurance_claim',
  'incident',
  'maintenance',
  'funding',
  'transaction',
  'due_diligence',
  'transfer',
  'handoff',
  'control',
  'other',
] as const;

const CASE_STATES = [
  'draft',
  'in_preparation',
  'ready',
  'in_progress',
  'blocked',
  'completed',
  'cancelled',
] as const;

type SortField = 'title' | 'case_type' | 'state' | 'priority' | 'planned_start' | 'updated_at';
type SortDir = 'asc' | 'desc';

const STATE_COLORS: Record<string, string> = {
  draft: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
  in_preparation: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  ready: 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
  in_progress: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
  blocked: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  completed: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400',
  cancelled: 'bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-500',
};

const TYPE_COLORS: Record<string, string> = {
  works: 'bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400',
  permit: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  authority_submission: 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400',
  tender: 'bg-cyan-100 text-cyan-700 dark:bg-cyan-900/30 dark:text-cyan-400',
  insurance_claim: 'bg-pink-100 text-pink-700 dark:bg-pink-900/30 dark:text-pink-400',
  incident: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  maintenance: 'bg-teal-100 text-teal-700 dark:bg-teal-900/30 dark:text-teal-400',
  other: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300',
};

const PRIORITY_COLORS: Record<string, string> = {
  low: 'text-green-600 dark:text-green-400',
  medium: 'text-yellow-600 dark:text-yellow-400',
  high: 'text-orange-600 dark:text-orange-400',
  critical: 'text-red-600 dark:text-red-400',
};

const PRIORITY_ORDER: Record<string, number> = { critical: 0, high: 1, medium: 2, low: 3 };

function SortHeader({
  field,
  label,
  sortField,
  onToggle,
}: {
  field: SortField;
  label: string;
  sortField: SortField;
  sortDir?: SortDir;
  onToggle: (f: SortField) => void;
}) {
  return (
    <th
      className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider cursor-pointer hover:text-gray-700 dark:hover:text-gray-200 select-none"
      onClick={() => onToggle(field)}
    >
      <span className="inline-flex items-center gap-1">
        {label}
        <ArrowUpDown className={cn('w-3 h-3', sortField === field ? 'text-red-500' : '')} />
      </span>
    </th>
  );
}

function formatDate(d: string | null): string {
  if (!d) return '-';
  try {
    return new Date(d).toLocaleDateString('fr-CH');
  } catch {
    return '-';
  }
}

export default function Cases() {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const [filterState, setFilterState] = useState<string>('');
  const [filterType, setFilterType] = useState<string>('');
  const [sortField, setSortField] = useState<SortField>('updated_at');
  const [sortDir, setSortDir] = useState<SortDir>('desc');

  const { data: cases, isLoading } = useQuery({
    queryKey: ['org-cases', filterState, filterType],
    queryFn: () =>
      buildingCasesApi.listForOrg({
        state: filterState || undefined,
        case_type: filterType || undefined,
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

  const sorted = useMemo(() => {
    if (!cases) return [];
    const arr = [...cases];
    arr.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'title':
          cmp = a.title.localeCompare(b.title);
          break;
        case 'case_type':
          cmp = a.case_type.localeCompare(b.case_type);
          break;
        case 'state':
          cmp = a.state.localeCompare(b.state);
          break;
        case 'priority':
          cmp = (PRIORITY_ORDER[a.priority ?? 'medium'] ?? 9) - (PRIORITY_ORDER[b.priority ?? 'medium'] ?? 9);
          break;
        case 'planned_start':
          cmp = (a.planned_start ?? '').localeCompare(b.planned_start ?? '');
          break;
        case 'updated_at':
          cmp = (a.updated_at ?? a.created_at).localeCompare(b.updated_at ?? b.created_at);
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return arr;
  }, [cases, sortField, sortDir]);

  const toggleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
            <Briefcase className="w-6 h-6 text-red-600 dark:text-red-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              {t('cases.title') || 'Dossiers'}
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {t('cases.subtitle') || 'Episodes operationnels de vos batiments'}
            </p>
          </div>
        </div>
        <button
          className="inline-flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors text-sm font-medium"
          onClick={() => {
            /* TODO: open create dialog */
          }}
        >
          <Plus className="w-4 h-4" />
          {t('cases.new') || 'Nouveau dossier'}
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative">
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="appearance-none pl-3 pr-8 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-red-500 focus:border-red-500"
          >
            <option value="">{t('cases.all_types') || 'Tous les types'}</option>
            {CASE_TYPES.map((ct) => (
              <option key={ct} value={ct}>
                {ct.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
        <div className="relative">
          <select
            value={filterState}
            onChange={(e) => setFilterState(e.target.value)}
            className="appearance-none pl-3 pr-8 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-800 text-sm text-gray-700 dark:text-gray-300 focus:ring-2 focus:ring-red-500 focus:border-red-500"
          >
            <option value="">{t('cases.all_states') || 'Tous les etats'}</option>
            {CASE_STATES.map((s) => (
              <option key={s} value={s}>
                {s.replace(/_/g, ' ')}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
        </div>
        {(filterType || filterState) && (
          <button
            onClick={() => {
              setFilterType('');
              setFilterState('');
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
      ) : sorted.length === 0 ? (
        <div className="flex flex-col items-center justify-center h-64 text-gray-500 dark:text-gray-400">
          <Inbox className="w-12 h-12 mb-3 opacity-50" />
          <p className="text-lg font-medium">{t('cases.empty') || 'Aucun dossier en cours'}</p>
          <p className="text-sm mt-1">{t('cases.empty_hint') || 'Creez un dossier pour demarrer'}</p>
        </div>
      ) : (
        <div className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700">
          <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
            <thead className="bg-gray-50 dark:bg-gray-800/50">
              <tr>
                <SortHeader field="title" label={t('cases.col_title') || 'Titre'} sortField={sortField} sortDir={sortDir} onToggle={toggleSort} />
                <SortHeader field="case_type" label={t('cases.col_type') || 'Type'} sortField={sortField} sortDir={sortDir} onToggle={toggleSort} />
                <th className="px-4 py-3 text-left text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                  {t('cases.col_building') || 'Batiment'}
                </th>
                <SortHeader field="state" label={t('cases.col_state') || 'Etat'} sortField={sortField} sortDir={sortDir} onToggle={toggleSort} />
                <SortHeader field="priority" label={t('cases.col_priority') || 'Priorite'} sortField={sortField} sortDir={sortDir} onToggle={toggleSort} />
                <SortHeader field="planned_start" label={t('cases.col_planned_start') || 'Debut prevu'} sortField={sortField} sortDir={sortDir} onToggle={toggleSort} />
                <SortHeader field="updated_at" label={t('cases.col_updated') || 'Mis a jour'} sortField={sortField} sortDir={sortDir} onToggle={toggleSort} />
              </tr>
            </thead>
            <tbody className="bg-white dark:bg-gray-900 divide-y divide-gray-200 dark:divide-gray-700">
              {sorted.map((c: BuildingCaseRead) => {
                const building = buildingMap.get(c.building_id);
                return (
                  <tr
                    key={c.id}
                    className="hover:bg-gray-50 dark:hover:bg-gray-800/50 cursor-pointer transition-colors"
                    onClick={() => navigate(`/cases/${c.id}`)}
                  >
                    <td className="px-4 py-3 text-sm font-medium text-gray-900 dark:text-white whitespace-nowrap">
                      {c.title}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={cn(
                          'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                          TYPE_COLORS[c.case_type] || TYPE_COLORS.other,
                        )}
                      >
                        {c.case_type.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 whitespace-nowrap">
                      {building ? building.address || '-' : '-'}
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={cn(
                          'inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium',
                          STATE_COLORS[c.state] || STATE_COLORS.draft,
                        )}
                      >
                        {c.state.replace(/_/g, ' ')}
                      </span>
                    </td>
                    <td className="px-4 py-3 whitespace-nowrap">
                      <span
                        className={cn('text-sm font-medium', PRIORITY_COLORS[c.priority ?? 'medium'] || '')}
                      >
                        {c.priority ?? 'medium'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-600 dark:text-gray-300 whitespace-nowrap">
                      {formatDate(c.planned_start)}
                    </td>
                    <td className="px-4 py-3 text-sm text-gray-500 dark:text-gray-400 whitespace-nowrap">
                      {formatDate(c.updated_at ?? c.created_at)}
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
